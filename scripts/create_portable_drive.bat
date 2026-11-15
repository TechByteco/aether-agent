@echo off
title AETHER Portable Drive Builder
cd /d "%~dp0.."

echo ============================================================
echo   AETHER PORTABLE DRIVE BUILDER (Plug-and-Play AI)
echo ============================================================
echo.

set /p TARGET_DRIVE="Enter external drive letter (e.g. G: or F:) [Default: G:]: "
if "%TARGET_DRIVE%"=="" set TARGET_DRIVE=G:

echo.
echo Target Drive selected: %TARGET_DRIVE%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_portable_drive.ps1" -TargetDrive "%TARGET_DRIVE%"

echo.
pause
