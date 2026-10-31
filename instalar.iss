; =========================================================================
;  Instalador de MOSTRADOR para Windows (Inno Setup).
;
;  Compilar con Inno Setup 6 o 7 (https://jrsoftware.org/isinfo.php):
;    abrir este archivo y presionar F9 (o Build > Compile).
;  Sale un Setup.exe listo para mandarle a la clientela.
;
;  IMPORTANTE sobre los datos del cliente:
;    el instalador solo copia los .exe en "Program Files". La base de
;    datos, los respaldos y las fotos viven en %LOCALAPPDATA%\Garrafas,
;    FUERA de la instalación, así que al desinstalar o actualizar NO se
;    borra nada de lo que el cliente cargó.
; =========================================================================

#define AppName "MOSTRADOR"
#define AppVersion "1.3.6"
#define AppPublisher "DOBLE G SRL"
#define AppExeName "Actualizador.exe"

[Setup]
AppId={{8C3A4E21-5F7B-4C6D-9E1A-2B8D7F0C6A44}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
OutputDir=instalador
OutputBaseFilename=MOSTRADOR-{#AppVersion}-instalador
Compression=lzma2/max
SolidCompression=yes
; El .exe pide permisos solo cuando WINDOWS lo requiere (asInvoker),
; así que el instalador tampoco necesita elevar por defecto.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
WizardStyle=modern
SetupIconFile=icono.ico
UninstallDisplayIcon={app}\MOSTRADOR.exe
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; El acceso directo apunta al ACTUALIZADOR (no al programa): así cada
; apertura chequea si hay versión nueva antes de abrir.
Source: "dist\MOSTRADOR.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Actualizador.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\version.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
    Flags: nowait postinstall skipifsilent

; NOTA: no hay sección [UninstallDelete] para %LOCALAPPDATA%\Garrafas
; a propósito. Los datos del cliente (base, respaldos, fotos) son SUYOS
; y deben sobrevivir a un desinstalar.
