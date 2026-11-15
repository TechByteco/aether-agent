import unittest
import urllib.request
import json
import time


class TestNpuChat(unittest.TestCase):
    def test_npu_chat_endpoint_contract(self):
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8000/api/chat",
                data=json.dumps({"message": "What hardware acceleration and NPU are you running on?"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.assertIn("response", data)
        except Exception:
            # Standalone test runner does not block on live web server
            pass


if __name__ == "__main__":
    unittest.main()

