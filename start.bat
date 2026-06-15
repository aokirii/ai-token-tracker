@echo off
REM AI Token Tracker — double-click launcher for Windows.
REM Runs the app with the project's virtual environment, no console window.
cd /d "%~dp0"
.venv\Scripts\pythonw tracker.py
