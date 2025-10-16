# app.py — corrected version
from flask_cors import CORS
from flask import Flask, jsonify, request, redirect, url_for, session, send_from_directory, Response
from elasticsearch import Elasticsearch
import time
import threading
import os
import json
import logging
from datetime import datetime, timezone
import subprocess
import pdfkit  # For PDF report generation
import tempfile  # For temporary file handling
from chatbot import init_app as init_chatbot  # Import chatbot initialization

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
app.secret_key = os.urandom(24)

logging.basicConfig(level=logging.DEBUG)

# --- Elasticsearch Configuration ---
es = None
try:
    es = Elasticsearch(
        ["http://localhost:9200"],
        basic_auth=("elastic", "123456"),
        request_timeout=30
    )
    # ping returns boolean; if it fails treat as unavailable
    if not es.ping():
        logging.error("Elasticsearch ping failed — elasticsearch may be down or credentials/URL wrong.")
        es = None
    else:
        logging.info("Connected to Elasticsearch")
except Exception as e:
    logging.error(f"Error connecting to Elasticsearch: {e}")
    es = None

# Ensure index exists (optional)
def ensure_index(index_name="siem-logs"):
    if not es:
        return
    try:
        if not es.indices.exists(index=index_name):
            logging.info(f"Creating index: {index_name}")
            es.indices.create(index=index_name)
    except Exception as e:
        logging.error(f"Error ensuring index {index_name}: {e}")

if es:
    ensure_index("siem-logs")

# --- Log File Configuration ---
log_file = "/var/log/auth.log"
snort_log_file = "/var/log/snort/alert"  # ensure this path is correct and readable
pdf_save_path = "/tmp/save_reports"
os.makedirs(pdf_save_path, exist_ok=True)

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
                        es.index(index="siem-logs", document=log_entry)
                    except Exception as e:
                        logging.error(f"Error indexing log: {e}")
                else:
                    time.sleep(0.5)
    except FileNotFoundError:
        logging.error(f"Log file not found: {log_file}. Log collection thread exiting.")
    except Exception as e:
        logging.error(f"Error in log collection thread: {e}")

# --- Real-time Log Streaming Function (SSE Generator) ---
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

# --- SSE Route ---
@app.route('/stream-realtime-logs')
def stream_realtime_logs():
    if 'logged_in' not in session or not session.get('logged_in'):
        logging.warning("Unauthorized attempt to access log stream.")
        return Response("data: ERROR: Unauthorized\n\n", mimetype='text/event-stream'), 401
    return Response(get_log_stream(), mimetype='text/event-stream')

# --- Existing Routes ---
@app.route('/logs', methods=['GET'])
def get_logs():
    if not es:
        return jsonify({"error": "Elasticsearch not available"}), 503
    if 'logged_in' not in session or not session.get('logged_in'):
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
    # TODO: replace with secure auth / hashed passwords
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

# Route to serve chatbot static files
@app.route('/chatbot/static/<path:filename>')
def chatbot_static(filename):
    return send_from_directory('chatbot/static', filename)

@app.route('/dashboard')
def dashboard():
    logging.debug(f"Dashboard route accessed, session logged_in: {session.get('logged_in')}")
    if session.get('logged_in'):
        logging.debug("Serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    else:
        logging.debug("User not logged in, redirecting to login.")
        return redirect(url_for('login_page'))

@app.route('/')
def login_page():
    logging.debug("Serving login.html")
    return send_from_directory(app.static_folder, 'login.html')

# --- Snort Alerts Route ---
@app.route('/snort-alerts')
def get_snort_alerts():
    if 'logged_in' not in session or not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        logging.info(f"Reading Snort log file from: {snort_log_file}")

        if not os.path.exists(snort_log_file):
            logging.error(f"Snort log file does not exist: {snort_log_file}")
            return jsonify({"error": f"Log file not found at {snort_log_file}"}), 404

        with open(snort_log_file, "r") as file:
            lines = file.readlines()

        logging.info(f"Found {len(lines)} lines in Snort log")

        if not lines:
            return jsonify({"message": "No alerts found in Snort log."})

        alerts = [{"message": line.strip()} for line in lines[-50:]]
        logging.info(f"Returning {len(alerts)} alerts to client.")
        return jsonify(alerts)

    except PermissionError:
        logging.error("Permission denied reading snort log.")
        return jsonify({"error": "Permission denied to read snort log file"}), 403
    except Exception as e:
        logging.error(f"Unexpected error reading snort log: {e}")
        return jsonify({"error": str(e)}), 500


# --- System Health Route ---
@app.route('/system-health')
def get_system_health():
    if 'logged_in' not in session or not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        # Note: these commands are Linux-specific
        cpu_idle = float(subprocess.check_output("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/'", shell=True))
        cpu_usage = 100.0 - cpu_idle
        memory_usage = float(subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True))
        return jsonify({"cpu_usage": cpu_usage, "memory_usage": memory_usage})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Refresh Logs Route ---
@app.route('/refresh-logs')
def refresh_logs():
    if not es:
        return jsonify({"error": "Elasticsearch not available"}), 503
    if 'logged_in' not in session or not session.get('logged_in'):
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

# --- Generate Snort Report Routes ---
@app.route('/generate-report/snort/html', methods=['GET'])
def generate_snort_html_report():
    if 'logged_in' not in session or not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    try:
        with open(snort_log_file, "r") as file:
            lines = file.readlines()

        filtered_alerts = []
        for line in lines:
            if start_date and end_date:
                # Try to parse date from format at start of line. Adjust format if your snort format differs.
                try:
                    # Example parse — adjust to match your alert format
                    # e.g., "10/16/25-12:34:56.123456 [**] ..." => "%m/%d/%y-%H:%M:%S.%f"
                    token = line.split('[**]')[0].strip()
                    line_date = datetime.strptime(token, "%m/%d/%y-%H:%M:%S.%f")
                    if datetime.strptime(start_date, "%Y-%m-%d").date() <= line_date.date() <= datetime.strptime(end_date, "%Y-%m-%d").date():
                        filtered_alerts.append(line)
                except Exception:
                    # If parsing fails, include line (safer fallback)
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
    except PermissionError:
        return jsonify({"error": "Permission denied reading snort log file"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate-report/snort/pdf', methods=['GET'])
def generate_snort_pdf_report():
    if 'logged_in' not in session or not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        html_response = generate_snort_html_report()
        # If html_response is a JSON error response (tuple), return it
        if isinstance(html_response, tuple):
            return html_response
        if html_response.status_code != 200:
            return html_response

        html_content = html_response.get_data(as_text=True)

        pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
        }
        pdf = pdfkit.from_string(html_content, False, options=pdf_options)

        filename = "snort_report_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".pdf"
        filepath = os.path.join(pdf_save_path, filename)

        with open(filepath, "wb") as f:
            f.write(pdf)

        return Response(pdf, mimetype='application/pdf', headers={"Content-Disposition": f"attachment; filename={filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # initialize chatbot 
    try:
        init_chatbot(app)
    except Exception as e:
        logging.error(f"Chatbot initialization failed: {e}")

    # start background log collector thread (daemon)
    log_collector_thread = threading.Thread(target=collect_logs, daemon=True)
    log_collector_thread.start()

    # run flask app
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
