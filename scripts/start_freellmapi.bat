@echo off
title AETHER -- FreeLLMAPI Online Gateway
echo ============================================================
echo   AETHER Online Cortex Bridge: FreeLLMAPI
echo   Gateway: http://localhost:3001/v1
echo   Dashboard: http://localhost:3001
echo ============================================================
echo.

set "FREELLMAPI_DIR=c:\Users\saali\Downloads\freellmapi"

if not exist "%FREELLMAPI_DIR%" (
    echo [ERROR] FreeLLMAPI repository not found at %FREELLMAPI_DIR%
    pause
    exit /b 1
)

cd /d "%FREELLMAPI_DIR%"
call start_freellmapi.bat
