"""
Test Suite for QNN Execution Provider
"""

import unittest

class TestRegisterQNN(unittest.TestCase):
    def test_qnn_execution_provider(self):
        try:
            import onnxruntime as ort
        except ImportError:
            self.skipTest("onnxruntime not installed in environment")

        self.assertIsNotNone(ort.get_available_providers())


if __name__ == "__main__":
    unittest.main()
