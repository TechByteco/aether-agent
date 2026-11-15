import urllib.request
import json

# 1. Test Code Sandbox on Vercel Serverless
code_payload = json.dumps({
    "code": "const items = ['AETHER', 'Sovereign', 'Cloud']; console.log('Items processed:', items.join(' -> ')); items.length * 42;"
}).encode("utf-8")

req1 = urllib.request.Request(
    "https://aether-sovereign-os.vercel.app/api/code",
    data=code_payload,
    headers={"Content-Type": "application/json", "User-Agent": "AetherVerification/1.0"}
)

with urllib.request.urlopen(req1, timeout=10) as resp:
    data1 = json.loads(resp.read().decode("utf-8"))
    print("=== LIVE SERVERLESS CODE RUNNER ===")
    print(data1.get("output"))
    print("Metrics:", data1.get("metrics"))

# 2. Test AI Chat & Reasoning on Free Cloud Compute
chat_payload = json.dumps({
    "message": "Confirm AETHER 100% online cloud sovereign status on Vercel.",
    "model": "Qwen/Qwen2.5-Coder-32B-Instruct"
}).encode("utf-8")

req2 = urllib.request.Request(
    "https://aether-sovereign-os.vercel.app/api/chat",
    data=chat_payload,
    headers={"Content-Type": "application/json", "User-Agent": "AetherVerification/1.0"}
)

with urllib.request.urlopen(req2, timeout=20) as resp:
    data2 = json.loads(resp.read().decode("utf-8"))
    print("\n=== LIVE SERVERLESS AI REASONING ===")
    print("Active Model :", data2.get("model"))
    print("Provider     :", data2.get("provider"))
    print("Compute Tier :", data2.get("compute"))
    print("Latency      :", data2.get("latency_ms"), "ms")
    print("Response     :\n", data2.get("response"))
