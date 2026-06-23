@echo off
title NERVECHECK
color 0C
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 src\nervecheck.py & exit /b)
where python >nul 2>nul
if %errorlevel%==0 (python src\nervecheck.py & exit /b)
echo No se encontro Python.
pause
