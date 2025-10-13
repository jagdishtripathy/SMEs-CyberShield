from flask_cors import CORS
from flask import Flask, jsonify, request, redirect, url_for, session, send_from_directory, Response
from elasticsearch import Elasticsearch
import time
import threading
import os
import json
import logging
import datetime
import subprocess
import pdfkit  # For PDF report generation
import tempfile # For temporary file handling
from datetime import datetime, timezone


app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
app.secret_key = os.urandom(24)

logging.basicConfig(level=logging.DEBUG)

# --- Elasticsearch Configuration ---
try:
    es = Elasticsearch(
        ["http://localhost:9200"],
        basic_auth=("elastic", "123456"),
        request_timeout=30
    )
    if not es.ping():
        logging.error("Elasticsearch connection failed!")
except Exception as e:
    logging.error(f"Error connecting to Elasticsearch: {e}")
    es = None

# --- Log File Configuration ---
log_file = "/var/log/auth.log"
snort_log_file = "/var/log/snort/alert"
pdf_save_path = "/tmp/save_reports"  # Change this to your desired save path
os.makedirs(pdf_save_path, exist_ok=True) #creates the folder if it does not exist.

# --- Background Thread for Indexing Logs to Elasticsearch ---
def collect_logs():
    if not es:
        logging.error("Elasticsearch client not available. Log collection thread exiting.")
        return

    logging.info(f"Starting log collection thread for {log_file}")
    try:
        with open(log_file, "r") as file:
            file.seek(0, os.SEEK_END)
            logging.info(f"Tailing log file: {log_file}")
            while True:
                line = file.readline()
                if line:
                    log_entry = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message": line.strip()
                    }
                    try:
                        res = es.index(index="siem-logs", document=log_entry)
                    except Exception as e:
                        logging.error(f"Error indexing log: {e}")
                else:
                    time.sleep(0.5)
    except FileNotFoundError:
        logging.error(f"Log file not found: {log_file}. Log collection thread exiting.")
    except Exception as e:
        logging.error(f"Error in log collection thread: {e}")

# --- NEW: Real-time Log Streaming Function (SSE Generator) ---
def get_log_stream():
    logging.info(f"Starting SSE log stream for {log_file}")
    try:
        with open(log_file, "r") as file:
            file.seek(0, os.SEEK_END)
            while True:
                line = file.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(0.1)
    except FileNotFoundError:
        logging.error(f"Log file not found for streaming: {log_file}")
        yield f"data: ERROR: Log file not found: {log_file}\n\n"
    except Exception as e:
        logging.error(f"Error in log streaming generator: {e}")
        yield f"data: ERROR: Could not read log file - {e}\n\n"

# --- NEW: SSE Route ---
@app.route('/stream-realtime-logs')
def stream_realtime_logs():
    if 'logged_in' not in session or not session['logged_in']:
        logging.warning("Unauthorized attempt to access log stream.")
        return Response("data: ERROR: Unauthorized\n\n", mimetype='text/event-stream'), 401
    return Response(get_log_stream(), mimetype='text/event-stream')

# --- Existing Routes (Modified slightly for clarity/robustness) ---
@app.route('/logs', methods=['GET'])
def get_logs():
    if not es:
        return jsonify({"error": "Elasticsearch not available"}), 503
    if 'logged_in' not in session or not session['logged_in']:
        logging.warning("Unauthorized attempt to access /logs.")
        return jsonify({"error": "Unauthorized"}), 401
    query = {"size": 100, "sort": [{"timestamp": "desc"}], "query": {"bool": {"must": []}}}
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    log_level = request.args.get('logLevel')
    try:
        range_filter = {}
        if start_date:
            range_filter["gte"] = f"{start_date}T00:00:00.000Z"
        if end_date:
            range_filter["lte"] = f"{end_date}T23:59:59.999Z"
        if range_filter:
            query["query"]["bool"]["must"].append({"range": {"timestamp": range_filter}})
        if log_level and log_level.lower() != 'all':
            query["query"]["bool"]["must"].append({"match": {"message": log_level}})
        logging.debug(f"Elasticsearch query: {json.dumps(query)}")
        result = es.search(index="siem-logs", body=query)
        logs = [{"timestamp": hit["_source"].get("timestamp"), "message": hit["_source"].get("message")}
                for hit in result["hits"]["hits"]]
        logging.debug(f"Elasticsearch result count: {len(logs)}")
        return jsonify(logs)
    except Exception as e:
        logging.error(f"Error fetching logs from Elasticsearch: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    logging.debug(f"Login attempt: username={username}")
    if username == "admin" and password == "password":
        session['logged_in'] = True
        logging.debug("Login successful, session set.")
        return jsonify({"success": True})
    else:
        logging.debug("Login failed.")
        session.pop('logged_in', None)
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    logging.debug("User logged out.")
    return jsonify({"success": True})

@app.route('/dashboard')
def dashboard():
    logging.debug(f"Dashboard route accessed, session logged_in: {session.get('logged_in')}")
    if 'logged_in' in session and session['logged_in']:
        logging.debug("Serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    else:
        logging.debug("User not logged in, redirecting to login.")
        return redirect(url_for('login_page'))

@app.route('/')
def login_page():
    logging.debug("Serving login.html")
    return send_from_directory(app.static_folder, 'login.html')
    
# --- NEW: Snort Alerts Route ---
@app.route('/snort-alerts')
def get_snort_alerts():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        with open(snort_log_file, "r") as file:
            lines = file.readlines()
            alerts = [{"message": line.strip()} for line in lines[-10:]]
            return jsonify(alerts)
    except FileNotFoundError:
        return jsonify({"error": "Snort alert log file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#--- System Health Route ---
@app.route('/system-health')
def get_system_health():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        cpu_usage = float(subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/'", shell=True))
        memory_usage = float(subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True))
        return jsonify({"cpu_usage": 100-cpu_usage,"memory_usage": memory_usage})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW: Refresh Logs Route ---
@app.route('/refresh-logs')
def refresh_logs():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        query = {"size": 100, "sort": [{"timestamp": "desc"}]}
        result = es.search(index="siem-logs", body=query)
        logs = [{"timestamp": hit["_source"].get("timestamp"), "message": hit["_source"].get("message")}
                for hit in result["hits"]["hits"]]
        return jsonify(logs)
    except Exception as e:
        logging.error(f"Error refreshing logs: {e}")
        return jsonify({"error": str(e)}), 500

# --- NEW: Generate Snort Report Routes ---
@app.route('/generate-report/snort/html', methods=['GET'])
def generate_snort_html_report():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401

    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    try:
        with open(snort_log_file, "r") as file:
            lines = file.readlines()

        filtered_alerts = []
        for line in lines:
            if start_date and end_date:
                try:
                    line_date = datetime.datetime.strptime(line.split('[**]')[0].strip(), "%m/%d/%y-%H:%M:%S.%f")
                    if datetime.datetime.strptime(start_date, "%Y-%m-%d").date() <= line_date.date() <= datetime.datetime.strptime(end_date, "%Y-%m-%d").date():
                        filtered_alerts.append(line)
                except ValueError:
                    filtered_alerts.append(line)
            else:
                filtered_alerts.append(line)

        html_content = "<h1>Snort Alert Report</h1>"
        if start_date and end_date:
            html_content += f"<p>Date Range: {start_date} to {end_date}</p>"
        html_content += "<ul>"
        for alert in filtered_alerts:
            html_content += f"<li>{alert.strip()}</li>"
        html_content += "</ul>"

        return Response(html_content, mimetype='text/html')

    except FileNotFoundError:
        return jsonify({"error": "Snort alert log file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate-report/snort/pdf', methods=['GET'])
def generate_snort_pdf_report():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401

    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    try:
        html_response = generate_snort_html_report()
        if html_response.status_code != 200:
            return html_response

        html_content = html_response.data.decode('utf-8')

        pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
        }
        pdf = pdfkit.from_string(html_content, False, options=pdf_options)

        # Save the PDF to the server
        filename = "snort_report_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".pdf"
        filepath = os.path.join(pdf_save_path, filename)

        with open(filepath, "wb") as f:
            f.write(pdf)

        return Response(pdf, mimetype='application/pdf', headers={"Content-Disposition": "attachment; filename=snort_report.pdf"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    log_collector_thread = threading.Thread(target=collect_logs, daemon=True)
    log_collector_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
