@echo off
title AETHER Autonomous Heartbeat Daemon
cd /d "%~dp0"
echo Starting AETHER Autonomous Heartbeat Daemon...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m aether.daemon.heartbeat
) else (
    python -m aether.daemon.heartbeat
)
pause
