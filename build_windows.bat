@echo off
title Canary Islands Car Hire Optimiser - Build
cd /d "%~dp0"
python -m PyInstaller --clean --noconfirm --distpath release --workpath build CanaryCarFinder.spec
echo.
echo Build complete. Release files are in:
echo release\CanaryCarFinder
pause
