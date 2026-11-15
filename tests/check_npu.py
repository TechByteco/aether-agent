import subprocess
import sys

print("Checking Windows NPU / Compute Accelerators via PowerShell...")
ps_code = """
Get-CimInstance Win32_PnPEntity | Where-Object { 
    $_.Name -like '*NPU*' -or 
    $_.Name -like '*Neural*' -or 
    $_.Name -like '*Hexagon*' -or 
    $_.Name -like '*Qualcomm*' 
} | Select-Object Name, DeviceID, Status | Format-Table -AutoSize
"""
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True)
print(res.stdout.strip() or "No matching PnP entities found.")

print("\nChecking Python packages related to NPU / ONNX / DirectML...")
pip_res = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
installed = [line for line in pip_res.stdout.splitlines() if any(k in line.lower() for k in ["onnx", "directml", "torch", "qnn", "qualcomm"])]
print("\n".join(installed) if installed else "None of onnx/directml/torch/qnn installed yet.")
