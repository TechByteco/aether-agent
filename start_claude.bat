@echo off
title Claude Code Agent - AETHER High Agency System
cd /d "%~dp0"
echo ========================================================
echo   Starting AETHER in Claude Code Agent Mode...
echo   Tools: Bash, View, Edit, Write, Grep, Find, Todo, Swarm
echo ========================================================
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m aether.cli --claude
) else (
    python -m aether.cli --claude
)
pause
