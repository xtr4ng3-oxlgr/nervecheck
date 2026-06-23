@echo off
title NERVECHECK - Compilar EXE portable
color 0C
cd /d "%~dp0\.."
echo NERVECHECK BUILD LOG > BUILD_LOG.txt
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
%PYTHON_CMD% -m pip install --upgrade pip >> BUILD_LOG.txt 2>&1
%PYTHON_CMD% -m pip install -r requirements.txt >> BUILD_LOG.txt 2>&1
%PYTHON_CMD% -m pip install pyinstaller >> BUILD_LOG.txt 2>&1
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q CLIENTE_PORTABLE 2>nul
del /q NERVECHECK.spec 2>nul
%PYTHON_CMD% -m PyInstaller --onedir --windowed --clean --noconfirm --name NERVECHECK --hidden-import psutil --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.messagebox --hidden-import tkinter.filedialog "src\nervecheck.py" >> BUILD_LOG.txt 2>&1
if %errorlevel% neq 0 (
    echo Fallo compilacion. Revisar BUILD_LOG.txt
    pause
    exit /b
)
mkdir CLIENTE_PORTABLE
mkdir CLIENTE_PORTABLE\data
mkdir CLIENTE_PORTABLE\logs
mkdir CLIENTE_PORTABLE\reports
xcopy /E /I /Y "dist\NERVECHECK" "CLIENTE_PORTABLE\NERVECHECK" >> BUILD_LOG.txt 2>&1
copy /Y "build_windows\ABRIR_NERVECHECK.bat" "CLIENTE_PORTABLE\ABRIR_NERVECHECK.bat" >> BUILD_LOG.txt 2>&1
copy /Y "build_windows\ABRIR_DEBUG_SI_NO_ABRE.bat" "CLIENTE_PORTABLE\ABRIR_DEBUG_SI_NO_ABRE.bat" >> BUILD_LOG.txt 2>&1
copy /Y "README.md" "CLIENTE_PORTABLE\README.txt" >> BUILD_LOG.txt 2>&1
echo Build listo. Abrir CLIENTE_PORTABLE\ABRIR_NERVECHECK.bat
pause
