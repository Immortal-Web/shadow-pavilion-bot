@echo off
REM Start from this file's directory so the SQLite database is found correctly.
cd /d "%~dp0"

REM Uses this bot's isolated Python environment.
".venv\Scripts\python.exe" bot.py

REM Keep errors visible when started by double-clicking or at logon.
if errorlevel 1 pause
