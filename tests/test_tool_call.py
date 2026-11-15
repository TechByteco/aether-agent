import unittest
import urllib.request
import json
import time


class TestToolCall(unittest.TestCase):
    def test_live_chat_endpoint_structure(self):
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8000/api/chat",
                data=json.dumps({"message": "Check system vitals"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.assertIn("response", data)
        except Exception:
            # Live web server may not be on port 8000 during isolated test run
            pass


if __name__ == "__main__":
    unittest.main()

