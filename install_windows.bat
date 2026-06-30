@echo off
title Canary Islands Car Hire Optimiser - Install
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
echo.
echo Install complete.
pause
