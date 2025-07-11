# Cloud Hosting Tester
# Post data with key value every 5 seconds
import requests
import time

def post(key, value):
    # url: "nghia64582.online/store"
    # body {"key": "<key-string>", "value": "<value-string>"}
    url = f"https://nghia64582.online/store/{key}"
    body = {"value": value}

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CloudHostingTester/1.0"
    }
    response = requests.post(url, json=body, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to post data: {response.status_code} - {response.text}")

def get_random_string(length):
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def main():
    count = 0
    while True:
        try:
            key = "key_" + get_random_string(10)
            value = "value_" + get_random_string(1000)
            post(key, value)
            count += 1
            if count % 100 == 0:
                print(f"Posted {count} entries successfully.")
        except Exception as e:
            print(f"Error posting data: {e}")
        time.sleep(0.1)

if __name__ == "__main__":
    main()