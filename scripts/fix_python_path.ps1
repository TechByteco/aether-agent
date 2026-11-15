$pythonDir = "C:\Users\saali\AppData\Local\Programs\Python\Python313"
$scriptsDir = "C:\Users\saali\AppData\Local\Programs\Python\Python313\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($userPath -notlike "*$pythonDir*") {
    $newPath = "$pythonDir;$scriptsDir;$userPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "SUCCESS: Added Python 3.13 and Scripts to User PATH"
} else {
    Write-Host "INFO: Python is already present in User PATH"
}
