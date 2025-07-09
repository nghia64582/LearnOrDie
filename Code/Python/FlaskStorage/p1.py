import json

a = "{\"name\": false}"
b = json.loads(a)
print(b)
print(type(b))