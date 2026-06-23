@echo off
title NERVECHECK - Debug
color 0C
cd /d "%~dp0"
if not exist logs mkdir logs
if exist "NERVECHECK\NERVECHECK.exe" (
    "NERVECHECK\NERVECHECK.exe" >> logs\debug_inicio.log 2>&1
    echo Codigo salida: %errorlevel%
    pause
    exit /b
)
echo No se encontro NERVECHECK\NERVECHECK.exe
pause
