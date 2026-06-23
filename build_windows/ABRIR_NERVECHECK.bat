@echo off
title NERVECHECK
color 0C
cd /d "%~dp0"
if not exist logs mkdir logs
if not exist reports mkdir reports
if not exist data mkdir data
if exist "NERVECHECK\NERVECHECK.exe" (
    start "" "NERVECHECK\NERVECHECK.exe"
    exit /b
)
echo No se encontro NERVECHECK\NERVECHECK.exe
pause
