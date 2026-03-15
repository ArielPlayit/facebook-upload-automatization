@echo off
chcp 65001 > nul
set SCRIPT_DIR=C:\Users\ArielPlayit\Documents\Proyectos\facebook-upload-automatization
cd /d "%SCRIPT_DIR%"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"C:\Users\ArielPlayit\AppData\Local\Programs\Python\Python312\python.exe" "%SCRIPT_DIR%\setup_session.py" --profile edge_profile2
pause
