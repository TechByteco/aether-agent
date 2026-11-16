@echo off
title AETHER Hands-Free Ambient Voice Assistant
cd /d "%~dp0"
echo Starting AETHER Hands-Free Hotkey Listener...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m aether.tools.ambient_listener
) else (
    python -m aether.tools.ambient_listener
)
pause
