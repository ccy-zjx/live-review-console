@echo off
cd /d "%~dp0"

echo =====================================
echo   Live Stream Control Panel v1.0
echo   http://localhost:5000
echo =====================================
echo.

:: Find Python
set PY=
where python >nul 2>&1
if %errorlevel%==0 set PY=python
if not defined PY (
    if exist "C:\Users\16892\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
        set PY=C:\Users\16892\AppData\Local\Python\pythoncore-3.14-64\python.exe
    )
)
if not defined PY (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo [OK] Python: %PY%

:: Check app.py
if not exist "app.py" (
    echo [ERROR] app.py not found!
    pause
    exit /b 1
)
echo [OK] app.py found
echo.
echo Starting server... DO NOT close this window!
echo Open http://localhost:5000 in your browser
echo =====================================
echo.

start http://localhost:5000
%PY% app.py
pause
