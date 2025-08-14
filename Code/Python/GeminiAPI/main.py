import requests

header = {
    "X-goog-api-key": "AIzaSyD5CTv15xR9L3C-S1CbMTob34Myw9Ocgsc",
    "Content-Type": "application/json"
}
lines = open("article_1.txt", 'r', encoding="utf-8").readlines()
data = {
    "contents": [
      {
        "parts": [
          {
            "text": "Hãy tóm tắt nội dung bài báo sau khoảng 3-5 câu : " + "\n".join(lines),
          }
        ]
      }
    ]
  }
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

res = requests.post(
    url=url,
    headers=header,
    json=data
)
print(res.text)