@echo off
rem =========================================================================
rem  Compila MOSTRADOR.exe y Actualizador.exe con doble clic.
rem
rem  Requisitos (una sola vez):
rem    python -m pip install -r requirements.txt
rem    python -m pip install pyinstaller
rem
rem  Sale con un error y muestra el motivo si algo falla.
rem =========================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === MOSTRADOR - compilacion de ejecutables ===
echo.

rem ¿Hay Python?
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No encontre "python" en el PATH.
    echo         Instala Python 3.10+ y marca "Add python.exe to PATH".
    goto :fallo
)

rem ¿Está PyInstaller?
python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Falta PyInstaller. Instalalo con:
    echo         python -m pip install pyinstaller
    goto :fallo
)

rem ---------------------------------------------------------------------
rem MOSTRADOR: onefile + windowed, con el icono y el manifest embebidos.
rem   --noupx           sin comprimir: menos falsos positivos de antivirus
rem   --manifest        no pide ser administrador + texto nitido en 4K
rem   --add-data        lleva icono.ico dentro del .exe (ruta_recurso)
rem ---------------------------------------------------------------------
echo [1/3] Compilando MOSTRADOR.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --noupx ^
    --name MOSTRADOR --icon icono.ico --manifest app.manifest ^
    --add-data "icono.ico;." main.py
if errorlevel 1 (
    echo [ERROR] fallo al compilar MOSTRADOR.exe
    goto :fallo
)

echo [2/3] Compilando Actualizador.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --noupx ^
    --name Actualizador --manifest app.manifest actualizador.py
if errorlevel 1 (
    echo [ERROR] fallo al compilar Actualizador.exe
    goto :fallo
)

echo [3/3] Revisando las mitigaciones de seguridad de los .exe ...
if exist "tools\pe_check.py" (
    python "tools\pe_check.py" "dist\MOSTRADOR.exe" "dist\Actualizador.exe"
)

echo.
echo === Listo ===
echo Los ejecutables quedaron en la carpeta "dist":
dir /b dist\*.exe
echo.
echo Para publicar una version nueva usa "Publicar actualizacion.bat".
echo.
pause
exit /b 0

:fallo
echo.
echo La compilacion NO se completó. Revisá los mensajes de arriba.
pause
exit /b 1
