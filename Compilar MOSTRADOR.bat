@echo off
title Compilar MOSTRADOR.exe
cd /d "%~dp0"

echo.
echo  Compilando MOSTRADOR.exe, espera unos segundos...
echo  (Cerrá la ventana del programa si est^á abierta)
echo.

python -m PyInstaller --noconfirm --onefile --windowed --name MOSTRADOR --icon "icono.ico" --add-data "icono.ico;." main.py

if %errorlevel%==0 (
    echo.
    echo  LISTO: dist\MOSTRADOR.exe actualizado
) else (
    echo.
    echo  Hubo un error. Fij^ate si el programa est^a abierto y volv^e a intentar.
)
echo.
pause
