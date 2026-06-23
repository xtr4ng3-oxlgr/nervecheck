@echo off
title NERVECHECK - Probar sin compilar
color 0C
cd /d "%~dp0\.."
where py >nul 2>nul
if %errorlevel%==0 (py -3 src\nervecheck.py & pause & exit /b)
where python >nul 2>nul
if %errorlevel%==0 (python src\nervecheck.py & pause & exit /b)
echo No se encontro Python.
pause
