@echo off
:: ═══════════════════════════════════════════════════════
::  AETHER + LEON — Auto-Start on Windows Login
::  Place this file in the Windows Startup folder:
::  Win+R → shell:startup → paste shortcut here
:: ═══════════════════════════════════════════════════════

title AETHER Autonomous Operator
echo.
echo  ██████╗  █████╗ ███████╗███████╗ ████████╗ ██╗     ███████╗ ██████╗ ███╗   ██╗
echo     AETHER + LEON Autonomous Operator v1.0
echo     Starting all systems...
echo.

:: ── Wait 15 seconds for network to stabilise after login ──
timeout /t 15 /nobreak >nul

:: ── Set workspace ──
set WORKSPACE=c:\Users\saali\Documents\antigravity\charming-lovelace
set PYTHONPATH=%WORKSPACE%\src

:: ── Start AETHER web server (FastAPI + uvicorn) ──
echo [AETHER] Starting local server on http://localhost:8000 ...
start "AETHER Server" /min cmd /c "cd /d %WORKSPACE% && python -m uvicorn aether.web.server:app --host 0.0.0.0 --port 8000 --reload >> %WORKSPACE%\data\logs\server.log 2>&1"

:: ── Optional: open HUD in browser after 8 seconds ──
timeout /t 8 /nobreak >nul
start "" "http://localhost:8000"

echo [AETHER] Server started. HUD opening in browser.
echo [LEON]   Autonomous scheduler will start automatically with the server.
echo.
echo  To stop: close the 'AETHER Server' window in taskbar.
