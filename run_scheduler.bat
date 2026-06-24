@echo off
REM Start the daily auto-refresh scheduler (keep this window open, or use Task Scheduler).
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
"C:\Users\RohitAgrawal\AppData\Local\Programs\Python\Python314\python.exe" scheduler.py
pause
