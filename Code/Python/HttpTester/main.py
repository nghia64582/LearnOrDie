import requests

res = 0
for i in range(100):
    res = requests.post("http://localhost:8080//create-items/10000")
print(res.text)