@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title Audiera

echo Starting Audiera...
python "%~dp0song_agent.py" --no-menu

echo.
echo Stopped.
pause