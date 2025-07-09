from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Assume these are defined elsewhere in your application
# For demonstration purposes, let's define a mock Elasticsearch client
# You would typically initialize your Elasticsearch client like this:
# es_client = Elasticsearch(
#     hosts=['localhost:9200'], # Replace with your Elasticsearch host
#     basic_auth=('elastic', 'your_password'), # If security is enabled
#     # api_key=('id', 'api_key'), # Or API key
#     verify_certs=False, # Use only for development, not production
# )

class MockElasticsearch:
    """A mock Elasticsearch client for demonstration without a running ES instance."""
    def search(self, **kwargs):
        # Simulate a successful response
        if "memhq.uid" in kwargs.get("query", {}).get("terms", {}):
            member_uids_to_match = kwargs["query"]["terms"]["memhq.uid"]
            hits = []
            for uid in member_uids_to_match:
                # Simulate some data
                hits.append({
                    "_index": "acc_index",
                    "_id": str(uid),
                    "_source": {
                        "memhq": {
                            "uid": uid,
                            "un": f"user_{uid}",
                            "fa": f"fame_{uid}"
                        }
                    }
                })
            return {
                "hits": {
                    "hits": hits
                }
            }
        return {"hits": {"hits": []}}

es_client = MockElasticsearch() # Use the mock client for this example

# --- Define your response structure (similar to JS.OK/JS.KO) ---
class CustomResponse:
    @staticmethod
    def OK(data):
        return {"status": "ok", "data": data}

    @staticmethod
    def KO(message):
        return {"status": "error", "message": message}

# --- Python equivalent of MemberHq (dataclass is a good fit) ---
from dataclasses import dataclass, asdict

@dataclass
class MemberHq:
    uid: int
    un: str  # Corresponds to uname in Scala example output
    fa: str  # Corresponds to fame in Scala example output

    @property
    def uname(self):
        return self.un

    @property
    def fame(self):
        return self.fa

    @classmethod
    def from_dict(cls, data):
        return cls(
            uid=data.get("uid"),
            un=data.get("un"),
            fa=data.get("fa")
        )

async def get_member_hoi_quan_by_uid(member_uids: list[int], acc_index: str = "acc_index"):
    """
    Retrieves member information from Elasticsearch based on UIDs.

    Args:
        member_uids (list[int]): A list of member UIDs to search for.
        acc_index (str): The name of the Elasticsearch index.

    Returns:
        dict: A dictionary representing the success or failure response.
    """
    try:
        # Construct the terms query
        query = {
            "terms": {
                "memhq.uid": member_uids
            }
        }

        # Execute the search query
        # Note: In an async context, you'd use await es_client.search(...)
        # For the mock client, we'll call it directly.
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
                    # Directly create MemberHq from the extracted dict
                    member_hq = MemberHq.from_dict(memhq_data)
                    data_arr.append(member_hq)
                except Exception as e:
                    logger.warning(f"Failed to parse memhq data for hit {hit.get('_id')}: {e}")
        print(data_arr)
        # Map to the desired output format
        js_output = []
        for mem in data_arr:
            js_output.append({"uid": mem.uid, "name": mem.uname, "fame": mem.fame})

        return CustomResponse.OK({"ul": js_output})

    except Exception as e:
        logger.error(f"Failed to getMemberHoiQuanByUid search: {e}", exc_info=True)
        return CustomResponse.KO("Có lỗi xảy ra. Vui lòng thử lại.")

# --- Example Usage ---
async def main():
    member_uids_to_search = [123, 456, 789]
    result = await get_member_hoi_quan_by_uid(member_uids_to_search)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    member_uids_empty = []
    result_empty = await get_member_hoi_quan_by_uid(member_uids_empty)
    print(json.dumps(result_empty, indent=2, ensure_ascii=False))

    member_uids_single = [999]
    result_single = await get_member_hoi_quan_by_uid(member_uids_single)
    print(json.dumps(result_single, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())