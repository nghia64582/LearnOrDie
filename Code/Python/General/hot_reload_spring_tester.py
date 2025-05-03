#  - Small tool to measure speed of hot reload in spring with dev tool
#  - Instructions:
#     + Change response in an endpoint of spring rest controller (but do not save)
#     + Run this script
#     + Switch to the tab of rest controller, then result will show

import pyautogui as pa
import requests as req
from time import *

pa.PAUSE = 0.1
URL = "http://localhost:8080/first/hello"
sleep(2)
first_response = req.get(URL)
print("First response: " + first_response.text)
pa.hotkey('ctrl', 's')
start = time()
while True:
    new_response = req.get(URL)
    if new_response.text != first_response.text:
        print("Hot reload detected")
        print("New response: " + new_response.text)
        break
    if time() - start > 5:
        print("Hot reload timed out")
        break
    sleep(0.1)
print("Hot reload finished after " + str(time() - start) + " seconds")