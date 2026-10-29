# Firma digital de los ejecutables de MOSTRADOR (hallazgo AppSec #2).
#
# Requiere:
#   1. Un certificado OV/EV de una CA (DigiCert, Sectigo, SSL.com…)
#      instalado en el almacén personal del usuario O en un token/clave.
#   2. Las herramientas de Windows SDK (signtool) en el PATH.
#
# Uso:
#   .\firmar.ps1                                  # firma con el cert del almacén
#   .\firmar.ps1 -Thumbprint "ABC123..."          # elige cert por huella
#   .\firmar.ps1 -Fx true                         # firma con FxServerCert (firmware)
#
# Después de firmar, CORRER SIEMPRE tools\pe_check.py: tiene que decir
# "Firma Authenticode presente: SÍ" y el programa tiene que abrirse bien.
#
# El timestamp (/tr) es importante: sin él, al vencer el certificado la
# firma deja de ser válida aunque el .exe no cambie. Con él, la fecha de
# firma queda sellada por el servidor de la CA.

param(
    [string]$Thumbprint = "",
    [string]$Dir = "dist"
)

$ErrorActionPreference = "Stop"

$signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signTool) {
    # Suele estar en C:\Program Files (x86)\Windows Kits\10\bin\<ver>\x64
    $candidatos = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if ($candidatos) { $signTool = $candidatos[0] }
}
if (-not $signTool) {
    Write-Error "No encontré signtool.exe. Instalá las Windows 10/11 SDK (marca 'Windows SDK Sign Tools')."
}
$exe = $signTool.Source
Write-Output "signtool: $exe"

$archivos = @("MOSTRADOR.exe", "Actualizador.exe") | ForEach-Object { Join-Path $Dir $_ }
foreach ($f in $archivos) {
    if (-not (Test-Path $f)) { Write-Error "Falta $f: compilá antes de firmar." }
}

# URL del servidor de tiempo de la CA (cambiar si la CA es otra).
# DigiCert:   http://timestamp.digicert.com
# Sectigo:    http://timestamp.sectigo.com
# SSL.com:    http://timestamp.ssl.com
$timestamp = "http://timestamp.digicert.com"

foreach ($f in $archivos) {
    Write-Output "`nFirmando $f ..."
    $args = @("sign", "/fd", "SHA256", "/td", "SHA256", "/tr", $timestamp)
    if ($Thumbprint) {
        $args += @("/sha1", $Thumbprint)
    }
    $args += $f
    & $exe @args
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falló la firma de $f (código $LASTEXITCODE)."
    }
}

Write-Output "`nVerificando..."
& $exe verify /pa /v $archivos[0]
& $exe verify /pa /v $archivos[1]

Write-Output "`nListo. Revisá también las mitigaciones PE:"
& (Join-Path $PSScriptRoot "tools\pe_check.py") @archivos
