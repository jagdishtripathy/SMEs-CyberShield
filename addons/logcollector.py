import os
import time
import json
from elasticsearch import Elasticsearch

# ✅ Connect to Elasticsearch with authentication
es = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=("elastic", "123456")  # Replace with actual password
)

# Log file location
log_file = "/var/log/auth.log"  # Modify if needed

def read_logs():
    """Read logs in real-time from the system log file."""
    with open(log_file, "r") as file:
        file.seek(0, os.SEEK_END)  # Move to end of file
        while True:
            line = file.readline()
            if line:
                log_entry = {"timestamp": time.time(), "log": line.strip()}
                send_to_elasticsearch(log_entry)
            time.sleep(1)

def send_to_elasticsearch(log_entry):
    """Send parsed logs to Elasticsearch with authentication."""
    try:
        response = es.index(index="siem-logs", document=log_entry)  # ✅ Use `document` parameter
        print(f"✅ Log sent: {log_entry}")
    except Exception as e:
        print(f"❌ Error sending log: {e}")

if __name__ == "__main__":
    print("🚀 Starting log collection...")
    read_logs()
