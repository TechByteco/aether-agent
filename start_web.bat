@echo off
title AETHER v0.7.0 — Streaming Glass HUD
cd /d "%~dp0"
echo ============================================================
echo  AETHER v0.7.0 — Streaming Cognitive Glass HUD
echo  http://127.0.0.1:8000
echo ============================================================
echo.

REM Ensure Ollama is running with optimised env vars
echo Checking Ollama daemon...
tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
if errorlevel 1 (
    echo Starting Ollama in background...
    start "" /B "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
) else (
    echo Ollama already running.
)

echo Opening browser...
start "" "http://127.0.0.1:8000"

echo Starting AETHER server...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m uvicorn aether.web.server:app --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn aether.web.server:app --host 127.0.0.1 --port 8000
)
pause
