# ==============================================================================
# AETHER Portable Drive Builder (Dual-Architecture: ARM64 + x86_64)
# Packages Ollama + Models + AETHER HUD into a 100% plug-and-play USB/SSD suite.
# ==============================================================================

[CmdletBinding()]
param (
    [string]$TargetDrive = "G:",
    [string]$FolderName = "AETHER_Portable",
    [switch]$IncludeX64Ollama = $true,
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

function Invoke-FastCopy {
    param (
        [string]$Source,
        [string]$Destination,
        [string[]]$Options = @()
    )
    if (-not (Test-Path $Destination)) {
        New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    }
    $allArgs = @($Source, $Destination, "/E", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS") + $Options
    & robocopy.exe @allArgs | Out-Null
    if ($LASTEXITCODE -le 7) {
        $global:LASTEXITCODE = 0
    } else {
        throw "Robocopy failed copying from '$Source' to '$Destination' (Exit code: $LASTEXITCODE)"
    }
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   AETHER PORTABLE DRIVE BUILDER - Zero-Install AI Suite         " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Validate Target Drive & Path
$CleanDrive = $TargetDrive.TrimEnd('\').TrimEnd(':') + ":"
$DriveLetter = $CleanDrive.TrimEnd(':')
$DriveInfo = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Name -ieq $DriveLetter }

if (-not $DriveInfo) {
    Write-Error "Drive '$CleanDrive' was not found. Please connect your external drive and verify the drive letter."
    return
}

$FreeGB = [Math]::Round($DriveInfo.Free / 1GB, 2)
Write-Host "[+] Target Drive: $CleanDrive ($FreeGB GB Free Space Available)" -ForegroundColor Green

if ($FreeGB -lt 10) {
    Write-Warning "Target drive has less than 10 GB free space ($FreeGB GB). AETHER models require ~8 GB."
}

$TargetPath = Join-Path "$CleanDrive\" $FolderName
Write-Host "[+] Target Directory: $TargetPath" -ForegroundColor Green

if ($DryRun) {
    Write-Host "[!] Dry-run mode enabled. No files will be copied." -ForegroundColor Yellow
} else {
    New-Item -ItemType Directory -Force -Path $TargetPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\bin\arm64" | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\bin\x64" | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\models" | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\aether" | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\data" | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\python\arm64" | Out-Null
    New-Item -ItemType Directory -Force -Path "$TargetPath\python\x64" | Out-Null
}

# 2. Copy Local Native ARM64 Ollama
$LocalOllamaDir = "C:\Users\saali\AppData\Local\Programs\Ollama"
if (Test-Path "$LocalOllamaDir\ollama.exe") {
    Write-Host "`n[+] Step 1/6: Copying Native ARM64 Ollama binaries..." -ForegroundColor Cyan
    if (-not $DryRun) {
        Invoke-FastCopy -Source $LocalOllamaDir -Destination "$TargetPath\bin\arm64" -Options @("/XD", "*cache*", "/XF", "unins*")
        Write-Host "    -> ARM64 Ollama binaries copied successfully." -ForegroundColor Green
    }
} else {
    Write-Warning "Local Ollama installation not found at '$LocalOllamaDir'."
}

# 3. Setup x64 Ollama (for Intel Core / AMD PCs like Dell laptop)
if ($IncludeX64Ollama) {
    Write-Host "`n[+] Step 2/6: Setting up x64 Ollama (for Intel/AMD PCs like Dell laptops)..." -ForegroundColor Cyan
    $X64ZipUrl = "https://github.com/ollama/ollama/releases/download/v0.34.2/ollama-windows-amd64.zip"
    $TempZip = Join-Path $env:TEMP "ollama-windows-amd64.zip"
    
    if (-not (Test-Path "$TargetPath\bin\x64\ollama.exe")) {
        Write-Host "    -> Downloading official x64 Ollama standalone zip..." -ForegroundColor Yellow
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $X64ZipUrl -OutFile $TempZip -UseBasicParsing
            Write-Host "    -> Extracting x64 Ollama to bin\x64..." -ForegroundColor Yellow
            Expand-Archive -Path $TempZip -DestinationPath "$TargetPath\bin\x64" -Force
            Remove-Item $TempZip -Force -ErrorAction SilentlyContinue
            Write-Host "    -> x64 Ollama installed successfully." -ForegroundColor Green
        } catch {
            Write-Warning "Failed to auto-download x64 Ollama: $_. You can manually place x64 ollama.exe into bin\x64."
        }
    } else {
        Write-Host "    -> x64 Ollama already present in bin\x64." -ForegroundColor Green
    }
} else {
    Write-Host "`n[+] Step 2/6: Skipping x64 Ollama download (use -IncludeX64Ollama to enable)." -ForegroundColor DarkGray
}

# 4. Copy Installed Model Blobs & Manifests
$LocalModelsDir = "C:\Users\saali\.ollama\models"
if (Test-Path $LocalModelsDir) {
    Write-Host "`n[+] Step 3/6: Transferring AI Model weights (~7.1 GB)..." -ForegroundColor Cyan
    Write-Host "    (Includes: aether:autonomous, llama3.2:3b, moondream, openclaw)" -ForegroundColor DarkGray
    if (-not $DryRun) {
        Invoke-FastCopy -Source $LocalModelsDir -Destination "$TargetPath\models" -Options @("/MT:8")
        Write-Host "    -> Models transferred successfully." -ForegroundColor Green
    }
} else {
    Write-Error "Local models directory '$LocalModelsDir' not found!"
}

# 5. Copy AETHER Application Source & Web UI
$WorkspaceDir = (Get-Item $PSScriptRoot).Parent.FullName
Write-Host "`n[+] Step 4/6: Packaging AETHER source code and Antigravity Web UI..." -ForegroundColor Cyan
if (-not $DryRun) {
    Invoke-FastCopy -Source "$WorkspaceDir\src" -Destination "$TargetPath\aether\src"
    if (Test-Path "$WorkspaceDir\Modelfile.aether") {
        Copy-Item "$WorkspaceDir\Modelfile*" -Destination "$TargetPath\aether\" -Force
    }
    if (Test-Path "$WorkspaceDir\pyproject.toml") {
        Copy-Item "$WorkspaceDir\pyproject.toml" -Destination "$TargetPath\aether\" -Force
    }
    Write-Host "    -> AETHER codebase packaged successfully." -ForegroundColor Green
}

# 6. Package Portable Python Environment (ARM64 & x64)
Write-Host "`n[+] Step 5/6: Setting up Portable Python Runtimes..." -ForegroundColor Cyan
$LocalArmPython = "C:\Users\saali\AppData\Local\Programs\Python\Python313"
$LocalX64Python = "C:\Users\saali\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none"
$LocalSitePackages = "$WorkspaceDir\.venv\Lib\site-packages"

# ARM64 Python
if (Test-Path $LocalArmPython) {
    Write-Host "    -> Copying ARM64 Python runtime for Snapdragon..." -ForegroundColor Yellow
    if (-not $DryRun) {
        Invoke-FastCopy -Source $LocalArmPython -Destination "$TargetPath\python\arm64" -Options @("/XD", "*tcl*", "*test*", "*Doc*")
        if (Test-Path $LocalSitePackages) {
            Invoke-FastCopy -Source $LocalSitePackages -Destination "$TargetPath\python\arm64\Lib\site-packages" -Options @("/MT:8")
        }
        Write-Host "    -> Portable ARM64 Python runtime ready." -ForegroundColor Green
    }
}

# x64 Python (for Dell Intel PC)
if (Test-Path $LocalX64Python) {
    Write-Host "    -> Copying x86_64 Python runtime for Intel/AMD PCs..." -ForegroundColor Yellow
    if (-not $DryRun) {
        Invoke-FastCopy -Source $LocalX64Python -Destination "$TargetPath\python\x64" -Options @("/XD", "*tcl*", "*test*", "*Doc*")
        Write-Host "    -> Portable x64 Python runtime ready." -ForegroundColor Green
    }
}

# 7. Create 1-Click Launchers on Drive Root
Write-Host "`n[+] Step 6/6: Creating 1-Click Launchers and Documentation..." -ForegroundColor Cyan

$LaunchBatLines = @(
    '@echo off',
    'setlocal enabledelayedexpansion',
    'title AETHER Autonomous AI - Portable Suite',
    'cd /d "%~dp0"',
    '',
    'echo ============================================================',
    'echo   AETHER PORTABLE PLUG-AND-PLAY SUITE',
    'echo   Zero-Installation Local AI for Any Windows PC',
    'echo ============================================================',
    'echo.',
    '',
    ':: 1. Detect Architecture',
    'echo [*] Detecting Host Hardware Architecture...',
    'if "%PROCESSOR_ARCHITECTURE%"=="ARM64" (',
    '    echo [OK] Qualcomm Snapdragon / ARM64 Detected.',
    '    set "OLLAMA_BIN=%~dp0bin\arm64\ollama.exe"',
    '    set "PYTHON_DIR=%~dp0python\arm64"',
    ') else (',
    '    echo [OK] Intel Core / AMD x86_64 Detected.',
    '    set "OLLAMA_BIN=%~dp0bin\x64\ollama.exe"',
    '    set "PYTHON_DIR=%~dp0python\x64"',
    ')',
    '',
    'if not exist "!OLLAMA_BIN!" (',
    '    echo [!] Architecture binary not found at: !OLLAMA_BIN!',
    '    echo [*] Checking for fallback binary...',
    '    if exist "%~dp0bin\arm64\ollama.exe" set "OLLAMA_BIN=%~dp0bin\arm64\ollama.exe"',
    '    if exist "%~dp0bin\x64\ollama.exe" set "OLLAMA_BIN=%~dp0bin\x64\ollama.exe"',
    ')',
    '',
    ':: 2. Set Portable Environment Variables',
    'set "OLLAMA_MODELS=%~dp0models"',
    'set "OLLAMA_HOST=127.0.0.1:11434"',
    'set "OLLAMA_KEEP_ALIVE=24h"',
    'set "AETHER_DATA_DIR=%~dp0data"',
    'set "PYTHONPATH=%~dp0aether\src;!PYTHON_DIR!\Lib\site-packages"',
    '',
    'echo [OK] Portable Models Path: !OLLAMA_MODELS!',
    'echo.',
    '',
    ':: 3. Start Portable Ollama Daemon',
    'echo [*] Starting Portable Ollama Daemon...',
    'tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul',
    'if errorlevel 1 (',
    '    start "Ollama Portable Service" /B "!OLLAMA_BIN!" serve',
    '    timeout /t 3 /nobreak >nul',
    ') else (',
    '    echo [OK] Ollama is already active.',
    ')',
    '',
    ':: 4. Verify Model Registry',
    'echo.',
    'echo Available Portable Models:',
    '"!OLLAMA_BIN!" list',
    'echo.',
    '',
    ':: 5. Launch AETHER Web HUD',
    'echo [*] Checking web interface prerequisites...',
    'if exist "!PYTHON_DIR!\python.exe" (',
    '    echo [*] Starting AETHER Cognitive Backend on http://127.0.0.1:8000 ...',
    '    start "" "http://127.0.0.1:8000"',
    '    set "PYTHONPATH=%~dp0aether\src;!PYTHON_DIR!\Lib\site-packages"',
    '    cd /d "%~dp0aether"',
    '    "!PYTHON_DIR!\python.exe" -m uvicorn aether.web.server:app --host 127.0.0.1 --port 8000',
    ') else (',
    '    echo [!] Standalone Python runtime not detected in !PYTHON_DIR!.',
    '    echo [*] Starting direct terminal chat with aether:autonomous...',
    '    echo.',
    '    "!OLLAMA_BIN!" run aether:autonomous',
    ')',
    '',
    'pause'
)

$ChatCliLines = @(
    '@echo off',
    'title AETHER Instant Terminal Chat',
    'cd /d "%~dp0"',
    '',
    'set "OLLAMA_MODELS=%~dp0models"',
    'set "OLLAMA_HOST=127.0.0.1:11434"',
    '',
    'if "%PROCESSOR_ARCHITECTURE%"=="ARM64" (',
    '    set "OLLAMA_BIN=%~dp0bin\arm64\ollama.exe"',
    ') else (',
    '    set "OLLAMA_BIN=%~dp0bin\x64\ollama.exe"',
    ')',
    '',
    'if not exist "%OLLAMA_BIN%" (',
    '    if exist "%~dp0bin\arm64\ollama.exe" set "OLLAMA_BIN=%~dp0bin\arm64\ollama.exe"',
    '    if exist "%~dp0bin\x64\ollama.exe" set "OLLAMA_BIN=%~dp0bin\x64\ollama.exe"',
    ')',
    '',
    'tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul',
    'if errorlevel 1 (',
    '    start "Ollama Daemon" /B "%OLLAMA_BIN%" serve',
    '    timeout /t 2 /nobreak >nul',
    ')',
    '',
    'echo ============================================================',
    'echo   AETHER INSTANT TERMINAL CHAT (Zero Dependencies)',
    'echo ============================================================',
    'echo Running: aether:autonomous',
    'echo (Press Ctrl+C or type /bye to exit)',
    'echo.',
    '',
    '"%OLLAMA_BIN%" run aether:autonomous',
    'pause'
)

$ReadmeLines = @(
    '==============================================================================',
    ' AETHER PORTABLE PLUG-AND-PLAY AI SUITE',
    ' Zero-Installation Autonomous AI Companion for Windows (ARM64 & x86_64)',
    '==============================================================================',
    '',
    'HOW TO USE THIS DRIVE ON ANY COMPUTER:',
    '-------------------------------------',
    '1. Plug this external USB/SSD into any Windows laptop or desktop PC.',
    '2. Open the drive folder in Windows File Explorer.',
    '3. Choose how you want to interact:',
    '',
    '   Option A (Recommended): Double-click "LAUNCH_AETHER.bat"',
    '   - Automatically detects whether the computer is Intel/AMD (x64) or Snapdragon (ARM64).',
    '   - Starts the local Ollama engine directly from the drive.',
    '   - Launches the modern Antigravity Glass Web Interface in your default web browser.',
    '   - Loads your persistent memory and conversation history from this drive.',
    '',
    '   Option B (Instant Terminal): Double-click "CHAT_CLI.bat"',
    '   - Launches a blazing-fast interactive terminal chat with "aether:autonomous".',
    '   - Requires zero Python and zero configuration.',
    '',
    'KEY FEATURES:',
    '-------------',
    '- 100% Offline & Private: No internet connection is required. Everything runs locally from this drive.',
    '- No Administrative Privileges Required: Runs cleanly in user space without modifying the host system.',
    '- Shared Model Storage: GGUF weights in \models are shared between Intel, AMD, and Snapdragon PCs.',
    '- Persistent Memory: Learned facts and chat history are saved in \data\aether.db directly on this drive.',
    '',
    'INSTALLED MODELS INCLUDED:',
    '--------------------------',
    '- aether:autonomous   (Custom fast tool-calling AGI assistant)',
    '- llama3.2:3b         (High-speed general reasoning)',
    '- moondream:latest    (Local computer vision & image inspection)',
    '- openclaw:latest     (Autonomous system execution agent)',
    '=============================================================================='
)

if (-not $DryRun) {
    [System.IO.File]::WriteAllLines("$TargetPath\LAUNCH_AETHER.bat", $LaunchBatLines)
    [System.IO.File]::WriteAllLines("$TargetPath\CHAT_CLI.bat", $ChatCliLines)
    [System.IO.File]::WriteAllLines("$TargetPath\README_PORTABLE.txt", $ReadmeLines)
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "   AETHER PORTABLE SUITE BUILD COMPLETE!                         " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "Target location: $TargetPath" -ForegroundColor Cyan
Write-Host "You can now plug this drive into any PC and run LAUNCH_AETHER.bat!" -ForegroundColor Green
