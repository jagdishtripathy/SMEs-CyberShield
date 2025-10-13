from flask import Flask, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)

# ✅ Connect to Elasticsearch with authentication
es = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=("elastic", "123456")  # Replace with actual password
)

@app.route('/logs', methods=['GET'])
def get_logs():
    """Retrieve the latest logs from Elasticsearch with authentication."""
    query = {
        "size": 10,
        "sort": [{"timestamp": "desc"}]
    }
    
    try:
        result = es.search(index="siem-logs", body=query)
        logs = [hit["_source"] for hit in result["hits"]["hits"]]
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
