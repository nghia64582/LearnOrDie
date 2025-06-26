import random as rd
import json
# sample 
# "37": {
#   "c": 37,
#   "e": 370,
#   "s": [
#     {
#       "q": 100000,
#       "t": 0
#     }
#   ],
#   "l": [
#     {
#       "q": 1500000,
#       "t": 0
#     }
#   ]
# }
lines = open("data.txt", "r", encoding="utf-8").readlines()
result = {}
for line in lines:
    eles = line.strip().split()
    for i in range(len(eles)):
        eles[i] = eles[i].replace(",", "")
    result[eles[0]] = {
        "c": int(eles[0]),
        "e": int(eles[1]),
        "s": [
            {
                "q": int(eles[2]),
                "t": 8
            }
        ],
        "l": [
            {
                "q": int(eles[3]),
                "t": 0
            }
        ]
    }

file = open("result.json", "w", encoding="utf-8")
file.write(json.dumps(result, indent=2, ensure_ascii=False))
file.close()