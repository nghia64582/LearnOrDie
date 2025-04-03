import base64

# Input string
text = "nghiavt@sandinh.net:nghia123456"

# Convert to bytes and encode
encoded = base64.b64encode(text.encode()).decode()
print(encoded)  # Output: dXNlcm5hbWU6cGFzc3dvcmQ=

decoded = base64.b64decode("bmdoaWF2dEBzYW5kaW5oLm5ldDpuZ2hpYTEyMzQ1Ng==").decode()
print(decoded)  # Output: username:password