import requests
import time

start = time.time()

login_url = "http://localhost:8080/login-oauth?email="
r = requests.get(login_url, data={"email": "nghia64582@gmail.com"})
print(r.content.decode("utf-8"))
print("Total time : " + str(time.time() - start) + " seconds")