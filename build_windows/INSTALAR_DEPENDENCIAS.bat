@echo off
title NERVECHECK - Instalar dependencias
color 0C
cd /d "%~dp0\.."
set PYTHON_CMD=
where py >nul 2>nul
if %errorlevel%==0 set PYTHON_CMD=py -3
if "%PYTHON_CMD%"=="" (
    where python >nul 2>nul
    if %errorlevel%==0 set PYTHON_CMD=python
)
if "%PYTHON_CMD%"=="" (
    echo No se encontro Python.
    pause
    exit /b
)
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt
echo Dependencias instaladas.
pause
