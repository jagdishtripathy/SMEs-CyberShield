from flask_cors import CORS
from flask import Flask, jsonify, request
from elasticsearch import Elasticsearch
import time
import threading
import os
import json

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for all routes

# ✅ Connect to Elasticsearch with authentication
es = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=("elastic", "123456")  # Replace with actual password
)

log_file = "/var/log/auth.log"

def collect_logs():
    """Read logs in real-time and send to Elasticsearch."""
    with open(log_file, "r") as file:
        file.seek(0, os.SEEK_END)  # Move to the end of the file
        while True:
            line = file.readline()
            if line:
                log_entry = {"timestamp": time.time(), "log": line.strip()}
                es.index(index="siem-logs", document=log_entry)  # ✅ Using `document` parameter
            time.sleep(1)

@app.route('/logs', methods=['GET'])
def get_logs():
    """Retrieve the latest logs from Elasticsearch."""
    query = {"size": 50, "sort": [{"timestamp": "desc"}]}
    
    try:
        result = es.search(index="siem-logs", body=query)
        logs = [hit["_source"] for hit in result["hits"]["hits"]]
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start log collection in a background thread
    threading.Thread(target=collect_logs, daemon=True).start()
    
    print("🚀 SIEM API running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
