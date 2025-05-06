import requests
import time
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:8080/your-api-endpoint"
NUM_REQUESTS = 100
MAX_WORKERS = 10

def send_request(i):
    try:
        response = requests.get(URL)
        return f"Request {i}: {response.status_code}"
    except Exception as e:
        return f"Request {i} failed: {e}"

start = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    results = list(executor.map(send_request, range(NUM_REQUESTS)))

end = time.time()

for result in results:
    print(result)

print(f"Completed {NUM_REQUESTS} requests in {end - start:.2f} seconds")
