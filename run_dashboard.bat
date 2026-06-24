@echo off
REM Launch the Streamlit stock dashboard in your browser.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
"C:\Users\RohitAgrawal\AppData\Local\Programs\Python\Python314\python.exe" -m streamlit run app.py
pause
