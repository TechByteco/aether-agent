import sys, os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(str(ROOT_DIR))

from aether.tools.npu_accelerator import get_npu_status, hardware_accelerated_screen_ocr

print("Testing NPU Hardware Status...")
status = get_npu_status(refresh=True)
print("NPU Status:", status)

print("\nTesting Instant Screen OCR via Snapdragon Accelerator...")
ocr = hardware_accelerated_screen_ocr()
print("OCR Result Preview:\n", ocr[:200] + "...")
