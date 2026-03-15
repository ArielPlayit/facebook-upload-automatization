@echo off
chcp 65001 > nul
set SCRIPT_DIR=C:\Users\ArielPlayit\Documents\Proyectos\facebook-upload-automatization
set LOG_FILE=%SCRIPT_DIR%\task_log.txt
cd /d "%SCRIPT_DIR%"
echo [%date% %time%] Iniciando script... >> "%LOG_FILE%"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"C:\Users\ArielPlayit\AppData\Local\Programs\Python\Python312\python.exe" -u "%SCRIPT_DIR%\post_to_groups_selenium.py" --config "%SCRIPT_DIR%\config.json" >> "%LOG_FILE%" 2>&1
set EXITCODE=%errorlevel%
echo [%date% %time%] Script finalizado con codigo: %EXITCODE% >> "%LOG_FILE%"
exit /b %EXITCODE%
