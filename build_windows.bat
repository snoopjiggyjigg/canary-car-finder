@echo off
title Canary Islands Car Hire Optimiser - Build
chcp 65001 >nul
cd /d "%~dp0"
echo Running Canary Islands Car Hire Optimiser release build...
echo Provider validation will run before packaging.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
