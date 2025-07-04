from elasticsearch import Elasticsearch

# Configuration based on your docker-compose.yml
# If Elasticsearch is running on the default port 9200 on localhost
ELASTICSEARCH_HOST = "esibackup.ohze.net"
ELASTICSEARCH_PORT = 80

# You might need to disable SSL verification if using self-signed certs
# or if you don't have HTTPS configured properly (especially in development)
# For production, always use HTTPS and proper certificate validation.
URL = f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"
print(f"Connecting to Elasticsearch at {URL}")
es_client = Elasticsearch(
    [URL],
    verify_certs=False # Set to True in production with proper certs
)

# docker run -d --name kibana-con -p 5601:5601 -e ELASTICSEARCH_HOSTS=http://esibackup.ohze.net:80 kibana:9.0.2

# 1. Check connection
if es_client.ping():
    print("Successfully connected to Elasticsearch!")
else:
    print("Could not connect to Elasticsearch.")
    exit()

def test_index():
    # 2. Create an index
    index_name = "my_test_index"
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name)
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")

    # 3. Index a document
    doc_id = "1"
    document = {
        "title": "My first document",
        "content": "This is some content for testing Elasticsearch.",
        "timestamp": "2025-07-02T14:00:00Z"
    }
    response = es.index(index=index_name, id=doc_id, document=document)
    print(f"Document indexed: {response['result']}")

    # 4. Get a document
    get_response = es.get(index=index_name, id=doc_id)
    print(f"Retrieved document: {get_response['_source']}")

    # 5. Search for documents
    search_query = {
        "query": {
            "match": {
                "content": "random"
            }
        }
    }
    search_results = es.search(index=index_name, body=search_query)
    print("\nSearch results:")
    for hit in search_results['hits']['hits']:
        print(f"  ID: {hit['_id']}, Source: {hit['_source']}")

    # 6. Delete the index (optional)
    es.indices.delete(index=index_name)
    print(f"Index '{index_name}' deleted.")

def get_member_hoi_quan_by_uid(member_uids: list[int], acc_index: str = "chan_acc"):
    try:
        # Construct the terms query
        query = {
            "terms": {
                "memhq.uid": member_uids
            }
        }

        response = es_client.search(
            index=acc_index,
            query=query,
            _source_includes=["memhq.uid", "memhq.un", "memhq.fa"],
            from_=0, # 'from' is a keyword in Python, so use from_
            size=50
        )

        data_arr = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            memhq_data = source.get("memhq")
            if memhq_data:
                try:
                    data_arr.append(memhq_data)
                except Exception as e:
                    print(f"Failed to parse memhq data for hit {hit.get('_id')}: {e}")

        # Map to the desired output format

        return {
            "success": True,
            "data": data_arr
        }

    except Exception as e:
        print("Error retrieving member information:", e)

uids = [int(i) for i in open("p1.txt").readlines()]
uids = [707853412, 707845097]
result = get_member_hoi_quan_by_uid(uids)
for ele in result["data"]:
    print(ele["uid"], ele["un"], sep=",")
# test_index()

# termsQuery
