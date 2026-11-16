import urllib.request
import json

def test_endpoint(url, data=None):
    print(f"\n--- Testing {url} ---")
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Status: {resp.status}")
            resp_body = resp.read().decode("utf-8")
            print(f"Body: {resp_body[:400]}")
            return json.loads(resp_body)
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_endpoint("https://aether-sovereign-os.vercel.app/api/swarm/execute", {
        "task": "build an auth microservice",
        "roles": ["System Architect", "Autonomous Coder"]
    })
    test_endpoint("https://aether-sovereign-os.vercel.app/api/swarm/debate", {
        "topic": "Microservices vs Monolith"
    })
    test_endpoint("https://aether-sovereign-os.vercel.app/api/chat", {
        "message": "Hello AETHER"
    })
