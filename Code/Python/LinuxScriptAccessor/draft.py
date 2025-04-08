import re
line = "08 Apr 2025 | 13:59:59,495 | INFO  | application-akka.actor.default-dispatcher-11 | sd.free.FreeCoinActor | null | freeCoinVer,u=707855436,b=50000,type=0,isSkip=true,"
match = re.search(r'a=(\d+).*?b=([a-zA-Z0-9_]+)', line)
print(match.group(1))
print(match.group(2))