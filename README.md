# SMEs-CyberShield

Lightweight SIEM + User Dashboard for small/medium enterprises. This repository contains a Flask-based dashboard, a simple alert manager, Suricata EVE log parsing utilities, and optional Elasticsearch indexing for logs.

This README explains how to set up the project locally (Windows PowerShell), configure Elasticsearch, and run the application.

---

## Prerequisites

- Python 3.10+ (3.11/3.12/3.13 also supported) installed and on PATH
- Git
- Elasticsearch (optional but recommended) — default expected at `http://localhost:9200`
- (Optional) Suricata if you plan to use Suricata EVE JSON logs

## Quick setup (Windows PowerShell)

1. Clone the repository and change directory:

```powershell
git clone <repo-url> d:\project_SMEs
cd d:\project_SMEs
```

2. Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .\myvenv
. .\myvenv\Scripts\Activate.ps1
```

3. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

4. Create a `.env` file in the project root (optional) to override defaults. Example `.env` content:

```text
# Flask
FLASK_SECRET_KEY=change_this_to_a_secure_random_value

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_SCHEME=http
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=

# Log files
AUTH_LOG_FILE=C:\path\to\auth.log          # adjust for your environment
SURICATA_EVE_LOG_FILE=C:\path\to\eve.json
PDF_SAVE_PATH=C:\temp\save_reports
```

5. Make sure the `AUTH_LOG_FILE` and `SURICATA_EVE_LOG_FILE` paths exist (or update the env vars to valid paths).

## Elasticsearch notes

The app expects an index named `siem-logs` for storing and querying logs. If you use Elasticsearch, create the index mapping so `timestamp` is a `date` field. If mapping is missing, the app will fallback gracefully, but sorting/time-range queries will be more reliable with a mapping.

Example curl to create the mapping (Linux/macOS/curl; on Windows use equivalent PowerShell curl):

```bash
curl -X PUT "http://localhost:9200/siem-logs" -H 'Content-Type: application/json' -d'
{
  "mappings": {
    "properties": {
      "timestamp": { "type": "date", "format": "strict_date_optional_time||epoch_millis" },
      "message": { "type": "text" }
    }
  }
}'
```

Or using Python Elasticsearch client (example):

```python
from elasticsearch import Elasticsearch
es = Elasticsearch(["http://localhost:9200"])  # add auth if required
mapping = {
  "mappings": {
    "properties": {
      "timestamp": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
      "message": {"type": "text"}
    }
  }
}
es.indices.create(index='siem-logs', body=mapping, ignore=400)
```

If you don't create a mapping, the application code includes `unmapped_type` in sort clauses to avoid a BadRequest error; however it's recommended to create the mapping for best results.

## Run the application

Start the Flask app (PowerShell):

```powershell
# Activate venv (if not already active)
. .\myvenv\Scripts\Activate.ps1
# Run app
python d:\project_SMEs\mainback.py
```

Open your browser and go to `http://127.0.0.1:5000`.

Notes:
- The app registers a user blueprint; check `users/` for login/register pages. Use the DB at `users/cybersecurity.db` for user accounts.
- The SSE endpoint for live logs is `/stream-realtime-logs` (requires admin access in the UI).

## Troubleshooting

- Elasticsearch errors about `timestamp` mapping: Create the index mapping shown above. The app will otherwise set `unmapped_type` when sorting to avoid immediate failures.
- If `stream-realtime-logs` raises an AttributeError about `get_wsgi_app`, ensure you are running the repository version that includes the streaming fallback fix (the Response is iterated via `.response`).
- If logs are not appearing, confirm `AUTH_LOG_FILE` and `SURICATA_EVE_LOG_FILE` paths are correct and readable by the process.

## Development notes

- Background log collector (`collect_logs`) will tail `AUTH_LOG_FILE` and index lines into `siem-logs` if Elasticsearch is available.
- Suricata EVE JSON parsing lives in `get_suricata_alerts` and Suricata report generation routes.

## Contributing

Please open issues or pull requests. Follow repository style and include tests for non-trivial logic where possible.
