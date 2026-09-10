@echo off
chcp 65001 >nul
title DBI Patcher Automation Tool

:: ============================================================================
:: DBI Patcher Automation Tool
::
:: USAGE:
::   1. Double-click run.bat (or run without arguments):
::      Launches the interactive TUI menu (menu.py).
::
::   2. Run with arguments from command line / terminal:
::      run.bat <command> [options]
::      Forwards arguments directly to: python -m src.main %*
::
:: EXAMPLES:
::   run.bat shadok -f               - Force re-translate all Shadok fables via AI
::   run.bat shadok --langs de,tr -f - Force re-translate Shadok for German and Turkish
::   run.bat translate -f            - Force re-translate all dictionary strings
::   run.bat all                     - Run complete pipeline (skipping already complete Shadok)
::   run.bat build                   - Re-compile all binary translation files
::   run.bat test                    - Run test suite in parallel (pytest -n auto)
::   run.bat check                   - Verify source integrity and binary sizes
::   run.bat help                    - Show all available commands and options
:: ============================================================================

:: Check if Python is installed and available in PATH
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10+ or add python.exe to system PATH.
    echo.
    pause
    exit /b 1
)

:: If CLI arguments are provided, forward them directly to python -m src.main
if not "%~1"=="" (
    python -m src.main %*
    goto :end
)

:: Otherwise, run the interactive Python menu
python "%~dp0menu.py"

:end
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Program exited with error code %errorlevel%.
    pause
)
