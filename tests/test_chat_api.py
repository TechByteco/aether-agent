import urllib.request
import json

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/chat",
    data=json.dumps({"message": "Hello AETHER, report your status, active model, and memory count in one crisp sentence."}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        print("[RESPONSE]:", data.get("response"))
        print("[TOOLS EXECUTED]:", data.get("tools_executed"))
except Exception as e:
    print("[ERROR]:", e)
