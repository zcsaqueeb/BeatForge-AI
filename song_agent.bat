@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title Audiera AI Song Agent v3.2.0

cls
echo.
echo   +----------------------------------------------------------+
echo   ^|  Audiera - AI Song Agent                 v3.2.0         ^|
echo   ^|  Autonomous song generation for Telegram                ^|
echo   +----------------------------------------------------------+
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found.
    echo.
    echo         Install Python 3.8+ from https://python.org
    echo         During install, tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo   OK  %PY_VER% detected
echo.

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo   Installing requests...
    pip install requests
    echo.
)

python -c "import web3" >nul 2>&1
if errorlevel 1 (
    echo   NOTE: web3 not installed - wallet features disabled
    echo         Run:  pip install web3
    echo.
)

echo   OK  Dependencies ready
echo.

echo   +----------------------------------------------------------+
echo   ^|  Choose a launch mode:                                  ^|
echo   ^|                                                         ^|
echo   ^|  1  Interactive menu  (recommended)                     ^|
echo   ^|  2  Start bot         (standard polling loop)           ^|
echo   ^|  3  Auto Mode         (zero-input autonomous loop)      ^|
echo   ^|  4  Generate one song (run once and exit)               ^|
echo   ^|  5  Exit                                                ^|
echo   +----------------------------------------------------------+
echo.

set /p CHOICE=   Your choice [1-5]: 

if "%CHOICE%"=="1" goto MENU
if "%CHOICE%"=="2" goto BOT
if "%CHOICE%"=="3" goto AUTO
if "%CHOICE%"=="4" goto ONCE
if "%CHOICE%"=="5" goto END

echo.
echo   Invalid choice - defaulting to interactive menu.
echo.
goto MENU

:MENU
echo.
echo   Starting interactive menu...
echo.
python "%~dp0song_agent.py" --menu
goto DONE

:BOT
echo.
echo   Starting bot (Ctrl+C to stop)...
echo.
python "%~dp0song_agent.py"
goto DONE

:AUTO
echo.
echo   Starting Auto Mode (Ctrl+C to stop)...
echo   Songs will be generated automatically with no input needed.
echo.
python "%~dp0song_agent.py" --loop
goto DONE

:ONCE
echo.
echo   Generating one song then exiting...
echo.
python "%~dp0song_agent.py" --once
goto DONE

:DONE
echo.
echo   +----------------------------------------------------------+
echo   ^|  Session ended.                                         ^|
echo   +----------------------------------------------------------+
echo.
pause

:END
exit /b 0
