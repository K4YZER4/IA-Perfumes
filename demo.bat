@echo off
chcp 65001 >nul
title Perfume Advisor - Demostracion del modelo
setlocal

cd /d "%~dp0"

set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python. Instala Python 3.12.
    pause
    exit /b 1
)

if not exist "model\vectorizer.joblib" (
    echo No hay modelo entrenado. Entrenando por primera vez...
    "%PY%" train.py
    if errorlevel 1 ( pause & exit /b 1 )
)

echo Ejecutando demostracion...
echo.
"%PY%" demo.py

echo.
pause
