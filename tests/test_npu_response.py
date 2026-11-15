import urllib.request
import json
import time

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/chat",
    data=json.dumps({"message": "Report how you utilize your Qualcomm Hexagon NPU and hardware acceleration in one concise sentence."}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

t0 = time.time()
with urllib.request.urlopen(req, timeout=90) as response:
    data = json.loads(response.read().decode("utf-8"))
    t1 = time.time()
    print(f"Latency: {t1 - t0:.2f}s")
    print("[RESPONSE]:", data.get("response"))
