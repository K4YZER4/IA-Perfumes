@echo off
chcp 65001 >nul
title Perfume Advisor - Servidor de IA
setlocal

rem --- Ir a la carpeta del script (funciona con doble clic) ---
cd /d "%~dp0"

echo ============================================================
echo   PERFUME ADVISOR - Servidor de IA
echo ============================================================
echo.

rem --- Localizar Python (ruta de instalacion conocida, si no, el PATH) ---
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python.
    echo         Instala Python 3.12 o revisa tu PATH.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python encontrado:
"%PY%" --version

rem --- Entrenar solo si no hay artefactos ---
if not exist "model\vectorizer.joblib" (
    echo.
    echo [2/3] No hay modelo entrenado. Entrenando por primera vez...
    "%PY%" train.py
    if errorlevel 1 (
        echo.
        echo [ERROR] El entrenamiento fallo.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Modelo entrenado encontrado en model\
)

rem --- Abrir Swagger en el navegador cuando el servidor este listo ---
start "" cmd /c "timeout /t 6 >nul & start http://127.0.0.1:8000/docs"

echo [3/3] Arrancando servidor en http://127.0.0.1:8000
echo.
echo   API:      http://127.0.0.1:8000/health
echo   Swagger:  http://127.0.0.1:8000/docs
echo.
echo   Para detener el servidor: CTRL + C
echo.
echo ============================================================
echo.

"%PY%" -m uvicorn predict:app --host 127.0.0.1 --port 8000

echo.
echo Servidor detenido.
pause
