file = open("C:/Users/NghiaVT/Desktop/Workspace/LearnOrDie/Code/Python/Draft/p1.txt", "r", encoding="utf-8")
lines = file.readlines()
count = {}
for line in lines:
    parts = line.split(" | ")
    topic = parts[4] if len(parts) > 4 else "Unknown"
    if topic not in count:
        count[topic] = 0
    count[topic] += 1
print(count)