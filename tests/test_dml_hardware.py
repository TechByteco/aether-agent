"""
Test Suite for DirectML Execution Provider on Snapdragon X
"""

import unittest

class TestDMLHardware(unittest.TestCase):
    def test_directml_execution_provider(self):
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError:
            self.skipTest("onnxruntime not installed in environment")

        providers = ort.get_available_providers()
        self.assertIn("DmlExecutionProvider", providers)


if __name__ == "__main__":
    unittest.main()
