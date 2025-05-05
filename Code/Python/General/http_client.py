import requests

res = requests.get("https://www.chotot.com/mua-ban-laptop-huyen-an-duong-hai-phong/116551807.htm#px=SR-similarad-[PO-7][PL-bottom]")
if res.status_code == 200:
    print("Request was successful.")
else:
    print("Request failed with status code:", res.status_code)
file = open("response.html", "w", encoding="utf-8")
file.write(res.text)
file.close()