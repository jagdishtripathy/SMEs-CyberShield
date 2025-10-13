from elasticsearch import Elasticsearch

# Corrected Elasticsearch connection with authentication
es = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=("elastic", "123456")  # Replace with actual password
)

def detect_brute_force():
    """Detect multiple failed login attempts."""
    query = {
        "query": {
            "match_phrase": {"log": "Failed password"}
        }
    }
    
    try:
        result = es.search(index="siem-logs", body=query)
        failed_attempts = len(result["hits"]["hits"])
        
        if failed_attempts > 5:
            print("🚨 ALERT: Possible brute force attack detected!")
    except Exception as e:
        print(f"Error querying Elasticsearch: {e}")

if __name__ == "__main__":
    detect_brute_force()
