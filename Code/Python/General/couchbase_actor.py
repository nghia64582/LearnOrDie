from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from couchbase.auth import PasswordAuthenticator
from couchbase.exceptions import CouchbaseException

cluster_host = f"128.199.246.136:8091/pools/default/"
username = "vinhbt"
password = "nguyenthelinh"
bucket_name = "acc"

try:
    # Authenticator object for username and password
    authenticator = PasswordAuthenticator(username, password)

    # Connect to the cluster
    cluster = Cluster(f"couchbase://{cluster_host}", ClusterOptions(authenticator=authenticator))

    # Get a reference to the bucket
    bucket = cluster.bucket(bucket_name)

    # Get a reference to the default collection (or a named collection)
    default_collection = bucket.default_collection()
    # If you have a named collection:
    # my_collection = bucket.collection("your_collection_name")

    # ------------------- Example Interactions -------------------
    key = "ca2tcb7"
    # Get a document
    get_result = default_collection.get(key)
    if get_result.exists():
        print(f"Retrieved document: {get_result.content()}")
    else:
        print(f"Document with key '{key}' not found.")

    # Query with N1QL
    # query = f"SELECT RAW name FROM `{bucket_name}` WHERE age > $age"
    # try:
    #     query_result = cluster.query(query, query_params={"age": 25})
    #     print("Users older than 25:")
    #     for row in query_result.rows():
    #         print(row)
    # except CouchbaseException as ex:
    #     print(f"N1QL query failed: {ex}")

    # ------------------- End of Examples -------------------

except CouchbaseException as ex:
    print(f"Error connecting or interacting with Couchbase: {ex}")
finally:
    if 'cluster' in locals() and cluster:
        cluster.disconnect()
        print("Disconnected from Couchbase.")