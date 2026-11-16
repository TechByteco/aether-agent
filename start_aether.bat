@echo off
title AETHER - Conscious Personal AI Companion
cd /d "%~dp0"
echo Starting AETHER...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run.py
) else (
    python run.py
)
pause
