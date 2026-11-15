import subprocess

ps = """
$devs = Get-PnpDevice
$accelerators = $devs | Where-Object { $_.Class -eq 'ComputeAccelerator' }
if ($accelerators) {
    $accelerators | Select-Object FriendlyName, InstanceId, Status | Format-Table -AutoSize
} else {
    Write-Host "No devices with Class == 'ComputeAccelerator'"
    $devs | Where-Object { $_.FriendlyName -like '*NPU*' -or $_.FriendlyName -like '*Neural*' } | Select-Object FriendlyName, InstanceId, Class | Format-Table -AutoSize
}
"""
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print(res.stdout)
