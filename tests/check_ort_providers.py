import onnxruntime as ort

print("ONNX Runtime Version:", ort.__version__)
providers = ort.get_available_providers()
print("Available Execution Providers:")
for p in providers:
    print(f"  - {p}")
