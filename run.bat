@echo off
chcp 65001 >nul
cd /d "%~dp0"
py alarm_bot.py
pause
