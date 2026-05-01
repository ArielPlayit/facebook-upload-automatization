@echo off
chcp 65001 > nul
set SCRIPT_DIR=C:\Users\ArielPlayit\Documents\Proyectos\facebook-upload-automatization
cd /d "%SCRIPT_DIR%"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
if "%~1"=="" (
	powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\run_post_parallel.ps1"
) else (
	"C:\Users\ArielPlayit\AppData\Local\Programs\Python\Python312\python.exe" -u "%SCRIPT_DIR%\post_to_groups_selenium.py" --config "%SCRIPT_DIR%\config.json" %*
)
set EXITCODE=%errorlevel%
exit /b %EXITCODE%
