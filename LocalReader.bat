@echo off
:: Ensures the script runs from the current directory
cd /d "%~dp0"

:: "start" launches the app in a separate process
:: "pythonw" runs python without a visible console window
start "" pythonw main.py

:: Closes this command prompt immediately
exit