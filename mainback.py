import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# mainback.py — unified SIEM + User Dashboard system (fixed routing + blueprint integration)
from flask_cors import CORS
from flask import Flask, jsonify, request, redirect, url_for, send_from_directory, Response, render_template
from elasticsearch import Elasticsearch
import time, threading, os, json, logging, subprocess, pdfkit, sqlite3
from datetime import datetime, timezone
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from chatbot import init_app as init_chatbot
import google.generativeai as genai
# Import system health utilities from users package
from users.utils.system_collector import collect_system_snapshot
from users.utils.scoring import compute_score
from users.utils.alert_manager import AlertManager

import json


# ---------------------------------------------------------------------
# FLASK INITIALIZATION
# ---------------------------------------------------------------------
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
# Use secret key from environment variable if set, otherwise generate a new one
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '')
app.secret_key = FLASK_SECRET_KEY if FLASK_SECRET_KEY else os.urandom(24)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------
# FLASK-LOGIN SETUP
# ---------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
# We will use the user blueprint login endpoint name (set after blueprint registered),
# but default to simple 'user_bp.login' — if blueprint registers with that name, it will work.
login_manager.login_view = 'user_bp.login'

# ---------------------------------------------------------------------
# DATABASE CONNECTION (users/cybersecurity.db)
# ---------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "users", "cybersecurity.db")
SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "users", "data", "system_snapshot.json")
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "users", "data", "sme_securecheck.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_db_connection():
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class User(UserMixin):
    def __init__(self, id, username, email, role='user', badges="[]", score=0):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        # Parse badges JSON string to list
        try:
            if isinstance(badges, str):
                self.badges = json.loads(badges) if badges else []
            else:
                self.badges = badges
        except:
            self.badges = []
        self.score = score

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db_connection()
        user_data = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if user_data:
        # sqlite3.Row supports dict-like access, not .get()
        role = user_data['role'] if 'role' in user_data.keys() else 'user'
        badges = user_data['badges'] if 'badges' in user_data.keys() else "[]"
        score = user_data['score'] if 'score' in user_data.keys() else 0
        return User(user_data['id'], user_data['username'], user_data['email'], role, badges, score)
    return None

# ---------------------------------------------------------------------
# ELASTICSEARCH CONFIGURATION (tolerant to ES being down)
# ---------------------------------------------------------------------
# Load Elasticsearch configuration from environment variables
ES_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ES_PORT = os.getenv('ELASTICSEARCH_PORT', '9200')
ES_SCHEME = os.getenv('ELASTICSEARCH_SCHEME', 'http')
ES_USERNAME = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', '')

es = None
try:
    es = Elasticsearch(
        [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        request_timeout=30
    )
    # ping might raise — wrap and handle
    try:
        if not es.ping():
            logging.error("Elasticsearch ping failed — elasticsearch may be down or credentials/URL wrong.")
            es = None
        else:
            logging.info("✅ Connected to Elasticsearch")
    except Exception as e:
        logging.error(f"Elasticsearch ping error: {e}")
        es = None
except Exception as e:
    logging.error(f"Error connecting to Elasticsearch: {e}")
    es = None

def ensure_index(index_name="siem-logs"):
    if not es:
        return
    try:
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name)
            logging.info(f"Index created: {index_name}")
    except Exception as e:
        logging.error(f"Error ensuring index: {e}")

if es:
    ensure_index()

# =====================================================================
# ALERT MANAGER INITIALIZATION
# =====================================================================
alert_manager = AlertManager(DB_PATH)
alert_manager.init_tables()  # Initialize alert tables

# =====================================================================
# LOG / SURICATA / PDF CONFIG
# =====================================================================
# Load file paths from environment variables with defaults
log_file = os.getenv('AUTH_LOG_FILE', '/var/log/auth.log')
suricata_eve_log_file = os.getenv('SURICATA_EVE_LOG_FILE', '/var/log/suricata/eve.json')
pdf_save_path = os.getenv('PDF_SAVE_PATH', '/tmp/save_reports')
os.makedirs(pdf_save_path, exist_ok=True)

# =====================================================================
# FALLBACK LOG READING (when Elasticsearch is unavailable)
# =====================================================================
def read_logs_from_file(limit=50):
    """Read logs directly from file (fallback when ES is down)."""
    try:
        if not os.path.exists(log_file):
            return []
        
        logs = []
        with open(log_file, 'r', errors='ignore') as f:
            lines = f.readlines()[-limit:]  # Get last N lines
            for line in lines:
                if line.strip():
                    logs.append({
                        "message": line.strip(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "file"
                    })
        return logs
    except Exception as e:
        logging.error(f"Error reading logs from file: {e}")
        return []

def stream_logs_from_file():
    """Stream logs from file in real-time (fallback when ES is down)."""
    def generate():
        try:
            if not os.path.exists(log_file):
                yield f"data: {json.dumps({'error': 'Log file not found'})}\n\n"
                return
            
            # Get file size
            file_size = os.path.getsize(log_file)
            position = max(0, file_size - 5000)  # Read last 5KB
            
            with open(log_file, 'r', errors='ignore') as f:
                f.seek(position)
                lines = f.readlines()
                
                for line in lines:
                    if line.strip():
                        yield f"data: {json.dumps({'message': line.strip(), 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                
                # Continue streaming new lines
                for _ in range(60):  # Stream for up to 60 seconds
                    line = f.readline()
                    if line.strip():
                        yield f"data: {json.dumps({'message': line.strip(), 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    time.sleep(1)
        except Exception as e:
            logging.error(f"Error streaming logs from file: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })

# ---------------------------------------------------------------------
# BACKGROUND LOG COLLECTOR (indexes lines to ES if available)
# ---------------------------------------------------------------------
def collect_logs():
    if not es:
        logging.error("Elasticsearch client not available. Log collection thread exiting.")
        return
    try:
        with open(log_file, "r") as file:
            file.seek(0, os.SEEK_END)
            while True:
                line = file.readline()
                if line:
                    try:
                        es.index(index="siem-logs", document={
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "message": line.strip()
                        })
                    except Exception as e:
                        logging.error(f"Error indexing log line: {e}")
                else:
                    time.sleep(0.5)
    except FileNotFoundError:
        logging.error(f"Log file not found: {log_file}. Log collector stopped.")
    except Exception as e:
        logging.error(f"Error reading log file: {e}")

# ---------------------------------------------------------------------
# AUTHENTICATION / LOGIN ROUTE (redirect to user blueprint)
# ---------------------------------------------------------------------
# NOTE: login UI and logic live in the users blueprint (users/app.py).
# The main app simply redirects /login to the blueprint's login route.
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    # redirect to user blueprint login (should be registered as user_bp.login)
    return redirect(url_for('user_bp.login'))

# Provide a main logout endpoint (POST) that logs out and returns JSON redirect
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    logging.info("User logged out.")
    return redirect(url_for('login_page'))


@app.route('/user/syshealth')
@login_required
def user_syshealth():
    snapshot = collect_system_snapshot()
    score = compute_score(snapshot)

    # Save to JSON snapshot file (not DB)
    with open(SNAPSHOT_PATH, 'w') as f:
        json.dump(snapshot, f, indent=2)

    return render_template('sysHealth.html', snapshot=snapshot, score=score)


@app.route('/api/collect', methods=['POST'])
@login_required
def collect_snapshot():
    snapshot = collect_system_snapshot()
    score = compute_score(snapshot)
    with open(SNAPSHOT_PATH, 'w') as f:
        json.dump(snapshot, f, indent=2)
    return jsonify({"message": "Snapshot collected", "score": score})


@app.route('/api/latest_snapshot')
@login_required
def latest_snapshot():
    try:
        with open(SNAPSHOT_PATH, 'r') as f:
            snapshot = json.load(f)
        score = compute_score(snapshot)
        return jsonify({
            "data": snapshot,
            "score": score,
            "created_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# DASHBOARD / ROOT ROUTES
# ---------------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # only admin allowed
    if getattr(current_user, "role", "user") != 'admin':
        return redirect(url_for('user_bp.dashboard'))
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/')
def root():
    if current_user.is_authenticated:
        if getattr(current_user, "role", "user") == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_bp.dashboard'))
    return redirect(url_for('login_page'))

# ---------------------------------------------------------------------
# SIEM ADMIN ROUTES (examples)
# ---------------------------------------------------------------------
@app.route('/logs')
@login_required
def get_logs():
    """Fetch historical logs (with fallback to file if ES unavailable)."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Try Elasticsearch first
        if es:
            try:
                query = {"size": 100, "sort": [{"timestamp": "desc"}]}
                result = es.search(index="siem-logs", body=query)
                logs = [{"timestamp": h["_source"].get("timestamp", ""), "message": h["_source"].get("message", ""), "source": "elasticsearch"}
                        for h in result["hits"]["hits"]]
                if logs:
                    return jsonify(logs)
            except Exception as e:
                logging.warning(f"Elasticsearch query failed: {e}. Falling back to file-based logs.")
        
        # Fallback to file-based logs
        logs = read_logs_from_file(100)
        if logs:
            return jsonify(logs)
        else:
            return jsonify([])  # Return empty array instead of error
    
    except Exception as e:
        logging.error(f"Error in get_logs: {e}")
        return jsonify([])

@app.route('/refresh-logs')
@login_required
def refresh_logs():
    """Fetch recent historical logs (with fallback to file if ES unavailable)."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Try Elasticsearch first
        if es:
            try:
                query = {
                    "size": 50,
                    "sort": [{"timestamp": {"order": "desc"}}]
                }
                result = es.search(index="siem-logs", body=query)
                logs = [{"message": h["_source"].get("message", ""), "timestamp": h["_source"].get("timestamp", ""), "source": "elasticsearch"}
                        for h in result["hits"]["hits"]]
                if logs:
                    return jsonify(logs)
            except Exception as e:
                logging.warning(f"Elasticsearch query failed: {e}. Falling back to file-based logs.")
        
        # Fallback to file-based logs
        logs = read_logs_from_file(50)
        if logs:
            return jsonify(logs)
        else:
            return jsonify({"error": "No logs available (Elasticsearch down, file not accessible)", "logs": []})
    
    except Exception as e:
        logging.error(f"Error in refresh_logs: {e}")
        return jsonify({"error": str(e), "logs": []})


@app.route('/stream-realtime-logs')
@login_required
def stream_realtime_logs():
    """Server-Sent Events (SSE) endpoint for streaming real-time logs (with fallback to file)."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Try Elasticsearch first, fallback to file if unavailable
    if not es:
        logging.info("Elasticsearch unavailable. Using file-based log streaming.")
        return stream_logs_from_file()
    
    def generate():
        """Generator function to stream logs in real-time using SSE."""
        last_timestamp = datetime.now(timezone.utc)
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # Query for logs newer than the last timestamp
                query = {
                    "size": 20,
                    "sort": [{"timestamp": {"order": "asc"}}],
                    "query": {
                        "range": {
                            "timestamp": {
                                "gte": last_timestamp.isoformat()
                            }
                        }
                    }
                }
                result = es.search(index="siem-logs", body=query)
                hits = result.get("hits", {}).get("hits", [])

                if hits:
                    # Update last_timestamp to the latest log's timestamp
                    for hit in hits:
                        source = hit["_source"]
                        message = source.get("message", "")
                        timestamp = source.get("timestamp", "")
                        if timestamp:
                            last_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        # Send log via SSE
                        yield f"data: {json.dumps({'message': message, 'timestamp': timestamp, 'source': 'elasticsearch'})}\n\n"
                    retry_count = 0  # Reset retry count on successful data
                else:
                    # No new logs, wait and retry
                    retry_count += 1
                    time.sleep(1)

            except Exception as e:
                logging.error(f"Error in stream_realtime_logs (ES): {str(e)}")
                # Fallback to file streaming on error
                yield f"data: {json.dumps({'message': 'Switching to file-based streaming...', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                for line_data in stream_logs_from_file().get_wsgi_app():
                    yield line_data
                return

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })

@app.route('/suricata-alerts')
@login_required
def get_suricata_alerts():
    """Fetch Suricata alerts from EVE JSON log file - only ACTUAL THREATS."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        if not os.path.exists(suricata_eve_log_file):
            return jsonify({"error": "Suricata EVE log file not found"}), 404
        
        alerts = []
        with open(suricata_eve_log_file, "r") as file:
            # Read last 500 lines to find actual alerts
            lines = file.readlines()[-500:]
            for line in lines:
                try:
                    if line.strip():
                        event = json.loads(line)
                        
                        # ✅ ONLY process events that have actual alerts (threats)
                        if "alert" not in event:
                            continue  # Skip informational events (DNS, flow, stats, etc.)
                        
                        alert_obj = event["alert"]
                        
                        # Extract relevant threat data from EVE JSON
                        alert_data = {
                            "timestamp": event.get("timestamp", ""),
                            "event_type": event.get("event_type", "alert"),
                            "src_ip": event.get("src_ip", "N/A"),
                            "dest_ip": event.get("dest_ip", "N/A"),
                            "src_port": event.get("src_port", "N/A"),
                            "dest_port": event.get("dest_port", "N/A"),
                            "proto": event.get("proto", "N/A"),
                            "message": alert_obj.get("signature", "Unknown Threat"),
                            "severity": alert_obj.get("severity", 3),  # 1=Critical, 2=Major, 3=Minor, 4=Minor
                            "category": alert_obj.get("category", ""),
                            "signature_id": alert_obj.get("signature_id", ""),
                            "action": alert_obj.get("action", ""),
                        }
                        
                        # Map severity numbers to readable labels
                        severity_map = {1: "🔴 Critical", 2: "🟠 Major", 3: "🟡 Minor", 4: "🔵 Info"}
                        alert_data["severity_label"] = severity_map.get(alert_data["severity"], "Unknown")
                        
                        # Only include alerts with severity 1, 2, or 3 (exclude purely informational)
                        if alert_data["severity"] <= 3:
                            alerts.append(alert_data)
                            
                            # ✅ ALSO create alert in database for Alerts section
                            try:
                                alert_manager.store_alert(
                                    alert_type="Suricata Threat",
                                    severity=alert_data["severity_label"],
                                    source_ip=alert_data["src_ip"],
                                    dest_ip=alert_data["dest_ip"],
                                    message=f"{alert_data['message']} [{alert_data['action']}]",
                                    event_data=json.dumps({
                                        "src_port": str(alert_data["src_port"]),
                                        "dest_port": str(alert_data["dest_port"]),
                                        "proto": alert_data["proto"],
                                        "signature_id": str(alert_data["signature_id"]),
                                        "category": alert_data["category"],
                                        "timestamp": alert_data["timestamp"]
                                    })
                                )
                            except Exception as alert_db_error:
                                logging.warning(f"Could not store Suricata alert in database: {alert_db_error}")
                
                except json.JSONDecodeError:
                    continue
        
        # Sort by timestamp descending (newest first)
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify(alerts[:100])  # Return last 100 actual threats
    except Exception as e:
        logging.error(f"Error fetching Suricata alerts: {e}")
        return jsonify({"error": str(e)}), 500

# Backward compatibility: redirect /snort-alerts to /suricata-alerts
@app.route('/snort-alerts')
@login_required
def snort_alerts_redirect():
    """Backward compatibility redirect from Snort to Suricata alerts."""
    return get_suricata_alerts()

@app.route('/system-health')
@login_required
def system_health():
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        # Linux-only commands — wrap in try/except as they may fail on Windows
        cpu_idle = float(subprocess.check_output(
            "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/'", shell=True))
        cpu_usage = 100.0 - cpu_idle
        memory_usage = float(subprocess.check_output(
            "free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True))
        return jsonify({"cpu_usage": cpu_usage, "memory_usage": memory_usage})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------
# REPORT GENERATION (Suricata)
# -----------------------------------------------------------------------
@app.route('/generate-report/suricata/html', methods=['GET'])
@login_required
def generate_suricata_html_report():
    """Generate Suricata alerts report in HTML format."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        alerts = []
        
        # Try to read from Suricata EVE log file
        if os.path.exists(suricata_eve_log_file):
            try:
                with open(suricata_eve_log_file, "r") as file:
                    lines = file.readlines()[-100:]  # Get last 100 lines
                    for line in lines:
                        try:
                            if line.strip():
                                event = json.loads(line)
                                alerts.append(event)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logging.warning(f"Error reading Suricata log file: {e}")
        else:
            logging.warning(f"Suricata EVE log file not found at {suricata_eve_log_file}")
        
        # Generate HTML report with styling
        html_content = """<html>
<head>
<style>
body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
h1 { color: #333; border-bottom: 3px solid #dc3545; padding-bottom: 10px; }
.info { background: #e7f3ff; padding: 10px; margin: 10px 0; border-left: 4px solid #2196F3; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
th { background-color: #dc3545; color: white; font-weight: bold; }
tr:nth-child(even) { background-color: #f9f9f9; }
.high { color: #dc3545; font-weight: bold; }
.medium { color: #ff9800; font-weight: bold; }
.low { color: #17a2b8; }
.no-alerts { padding: 20px; text-align: center; color: #666; }
</style>
</head>
<body>
<h1>🚨 Suricata Alert Report</h1>
<div class="info">
<strong>Generated:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """<br>
<strong>Total Alerts:</strong> """ + str(len(alerts)) + """
</div>"""
        
        if alerts:
            html_content += """<table>
<tr>
<th>Timestamp</th>
<th>Event Type</th>
<th>Source IP:Port</th>
<th>Destination IP:Port</th>
<th>Protocol</th>
<th>Alert Message</th>
<th>Severity</th>
</tr>"""
            
            for alert in alerts:
                timestamp = alert.get("timestamp", "N/A")
                event_type = alert.get("event_type", "N/A")
                src_ip = alert.get("src_ip", "N/A")
                src_port = alert.get("src_port", "")
                dest_ip = alert.get("dest_ip", "N/A")
                dest_port = alert.get("dest_port", "")
                proto = alert.get("proto", "N/A")
                
                src_addr = f"{src_ip}:{src_port}" if src_port else src_ip
                dest_addr = f"{dest_ip}:{dest_port}" if dest_port else dest_ip
                
                alert_msg = "N/A"
                severity = "Info"
                if "alert" in alert:
                    alert_msg = alert["alert"].get("signature", "N/A")
                    severity = alert["alert"].get("severity", "Info")
                
                severity_class = "high" if severity == "1" else "medium" if severity == "2" else "low"
                
                html_content += f"""<tr>
<td>{timestamp}</td>
<td>{event_type}</td>
<td>{src_addr}</td>
<td>{dest_addr}</td>
<td>{proto}</td>
<td>{alert_msg}</td>
<td><span class="{severity_class}">{severity}</span></td>
</tr>"""
            
            html_content += """</table>"""
        else:
            html_content += """<div class="no-alerts">
<p>📊 No Suricata alerts found. The system is operating normally.</p>
<p style="color: #999; font-size: 12px;">Alerts will appear here when security events are detected.</p>
</div>"""
        
        html_content += """</body>
</html>"""
        
        return Response(html_content, mimetype='text/html')
    except Exception as e:
        logging.error(f"Error in generate_suricata_html_report: {e}")
        return Response(f"<h1>Error Generating Report</h1><p>{str(e)}</p>", mimetype='text/html', status=500)

@app.route('/generate-report/suricata/pdf', methods=['GET'])
@login_required
def generate_suricata_pdf_report():
    """Generate Suricata alerts report in PDF format."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        # Get HTML report first
        html_response = generate_suricata_html_report()
        
        # Check if HTML generation succeeded
        if html_response.status_code != 200:
            return html_response
        
        html_content = html_response.get_data(as_text=True)
        
        try:
            # Try to generate PDF using pdfkit if available
            import pdfkit
            pdf = pdfkit.from_string(html_content, False)
            filename = f"suricata_report_{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
            return Response(pdf, mimetype='application/pdf',
                            headers={"Content-Disposition": f"attachment; filename={filename}"})
        except ImportError:
            logging.warning("pdfkit not installed. Returning HTML instead.")
            return html_response
        except Exception as pdf_error:
            logging.warning(f"PDF generation failed: {pdf_error}. Returning HTML instead.")
            return html_response
            
    except Exception as e:
        logging.error(f"Error in generate_suricata_pdf_report: {e}")
        return jsonify({"error": str(e)}), 500

# Backward compatibility: redirect old Snort report routes to Suricata
@app.route('/generate-report/snort/html', methods=['GET'])
@login_required
def generate_snort_html_report():
    """Backward compatibility redirect from Snort to Suricata HTML report."""
    return generate_suricata_html_report()

@app.route('/generate-report/snort/pdf', methods=['GET'])
@login_required
def generate_snort_pdf_report():
    """Backward compatibility redirect from Snort to Suricata PDF report."""
    return generate_suricata_pdf_report()


@app.route('/chatbot/static/<path:filename>')
def chatbot_static(filename):
    chatbot_static_dir = os.path.join(os.path.dirname(__file__), 'chatbot', 'static')
    return send_from_directory(chatbot_static_dir, filename)


# =====================================================================
# ALERT SYSTEM ROUTES
# =====================================================================

# ===== Alert Configuration =====
@app.route('/api/alerts/config', methods=['GET'])
@login_required
def get_alert_config():
    """Get all alert configurations."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    configs = alert_manager.get_all_alert_configs()
    return jsonify(configs)


@app.route('/api/alerts/config', methods=['POST'])
@login_required
def create_alert_config():
    """Create new alert configuration."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    result = alert_manager.create_alert_config(
        data.get('alert_name'),
        data.get('severity', 'High'),
        data.get('cooldown', 300),
        data.get('enabled', True)
    )
    return jsonify({"success": result})


@app.route('/api/alerts/config/<alert_name>', methods=['PUT'])
@login_required
def update_alert_config(alert_name):
    """Update alert configuration."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    result = alert_manager.update_alert_config(alert_name, **data)
    return jsonify({"success": result})


# ===== Alert History =====
@app.route('/api/alerts/recent', methods=['GET'])
@login_required
def get_recent_alerts():
    """Get recent alerts."""
    limit = request.args.get('limit', 50, type=int)
    alerts = alert_manager.get_recent_alerts(limit)
    return jsonify(alerts)


@app.route('/api/alerts/unacknowledged', methods=['GET'])
@login_required
def get_unacknowledged_alerts():
    """Get unacknowledged alerts."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    alerts = alert_manager.get_unacknowledged_alerts()
    return jsonify(alerts)


@app.route('/api/alerts/statistics', methods=['GET'])
@login_required
def get_alert_statistics():
    """Get alert statistics."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    stats = alert_manager.get_alert_statistics()
    return jsonify(stats)


@app.route('/api/alerts/by-severity/<severity>', methods=['GET'])
@login_required
def get_alerts_by_severity(severity):
    """Get alerts by severity."""
    limit = request.args.get('limit', 50, type=int)
    alerts = alert_manager.get_alerts_by_severity(severity, limit)
    return jsonify(alerts)


# ===== Alert Actions =====
@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    result = alert_manager.acknowledge_alert(alert_id, current_user.id)
    return jsonify({"success": result})


# ===== Manual Alert Trigger (for SIEM internal use only) =====
@app.route('/api/alerts/trigger', methods=['POST'])
@login_required
def trigger_manual_alert():
    """Manually trigger an alert (for SIEM system only)."""
    if getattr(current_user, "role", "user") != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    
    # Store the alert in the database
    alert_id = alert_manager.store_alert(
        alert_type=data.get('alert_type', 'manual'),
        severity=data.get('severity', 'Medium'),
        source_ip=data.get('source_ip'),
        dest_ip=data.get('dest_ip'),
        message=data.get('message', 'Alert triggered'),
        event_data=json.dumps(data)
    )

    if alert_id > 0:
        return jsonify({
            "success": True,
            "message": "Alert stored successfully",
            "alert_id": alert_id
        })
    else:
        return jsonify({"success": False, "message": "Failed to create alert"}), 500


# =====================================================================
# STARTUP: register blueprint(s), start threads, print routes
# =====================================================================
if __name__ == '__main__':
    try:
        init_chatbot(app)
    except Exception as e:
        logging.error(f"Chatbot init failed: {e}")

    threading.Thread(target=collect_logs, daemon=True).start()

    # ✅ Register user dashboard blueprint
    from users.app import init_user_routes
    init_user_routes(app)

    # ✅ Debug helper
    print("\nRegistered Routes:\n" + "-" * 40)
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:30} -> {rule}")
    print("-" * 40)

    logging.info("🚀 IntruSense SIEM + User Dashboard running at http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
