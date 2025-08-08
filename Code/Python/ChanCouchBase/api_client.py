import requests
from requests.auth import HTTPBasicAuth
from utils import to_base36
import json

HOST = "128.199.246.136"
PORT = 8091
URL = f"{HOST}:{PORT}"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Cookie": "",
    "Host": URL,
    "Pragma": "no-cache",
    "Referer": f"http://{URL}/ui/index.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "invalid-auth-response": "on",
    "ns-server-ui": "yes"
}

COOKIE = ""

def get_data(model_key: str, user_id: int, bucket: str) -> dict:
    key = model_key + to_base36(user_id) if bucket == "acc" else model_key
    # http://{URL}/pools/default/buckets/acc/docs/qt1njw4t
    url = f"http://{URL}/pools/default/buckets/{bucket}/docs/{key}"  # Customize
    # handle utf-8
    response = requests.get(url, headers=HEADERS, auth=HTTPBasicAuth("vinhbt", "nguyenthelinh"))
    return response.json()

def put_data(model_key: str, user_id: int, data: dict, bucket: str) -> dict:
    key = model_key + to_base36(user_id) if bucket == "acc" else model_key
    url = f"http://{URL}/pools/default/buckets/{bucket}/docs/{key}"  # Customize
    payload = {
        "value": json.dumps(data),
        "flags": 33554432
    }
    response = requests.post(url, headers=HEADERS, data=payload)
    return response.json()

def delete_data(model_key: str, user_id: int, bucket: str) -> dict:
    # http://{URL}/pools/default/buckets/acc/docs/ca1njw4r
    # DELETE
    key = model_key + to_base36(user_id) if bucket == "acc" else model_key
    url = f"http://{URL}/pools/default/buckets/{bucket}/docs/{key}"  # Customize
    response = requests.delete(url, headers=HEADERS)
    return response.json()

def login():
    url = f"http://{URL}/uilogin"
    payload = {
        "user": "vinhbt",
        "password": "nguyenthelinh"
    }
    # update cookie
    response = requests.post(url, headers=HEADERS, data=payload)
    if response.status_code == 200:
        print("Login successful")
        # Update the cookie in headers
        print(response.cookies)
        for key in response.cookies.get_dict():
            if key.startswith("ui-auth-"):
                global COOKIE
                COOKIE = f"{key}={response.cookies.get(key)}"
                break
        HEADERS["Cookie"] = COOKIE
        print("Updated cookie:", COOKIE)
