@echo off
title Publicar actualizacion de MOSTRADOR
cd /d "%~dp0"

echo.
echo  Compilando y publicando una version nueva de MOSTRADOR...
echo.
python publicar.py

echo.
pause
