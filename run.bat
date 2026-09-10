@echo off
chcp 65001 >nul
title DBI Patcher Automation Tool

:: Check if Python is installed and available in PATH
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10+ or add python.exe to system PATH.
    echo.
    pause
    exit /b 1
)

:: Run the interactive Python menu
python "%~dp0menu.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Program exited with error code %errorlevel%.
    pause
)
