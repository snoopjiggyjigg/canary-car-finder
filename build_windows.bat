@echo off
title Canary Islands Car Hire Optimiser - Build
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
