@echo off
title Control de Ventas de Garrafas
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw main.py
) else (
    python main.py
)
