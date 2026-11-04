
#define MyAppName "Chad Civil Registry"
#define MyAppVersion "1.0.0"
#define MyAppExeName "ChadCivilRegistry.exe"

[Setup]
AppId={{B3C1A87D-7A21-4E8C-9B62-4D3F5A7C1E90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Chad Civil Registry
DefaultDirName={localappdata}\Programs\Chad Civil Registry
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=ChadCivilRegistry-Setup
SetupIconFile=..\app\static\images\chad-civil-registry.ico
UninstallDisplayIcon={app}\ChadCivilRegistry.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
Uninstallable=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\ChadCivilRegistry\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent
