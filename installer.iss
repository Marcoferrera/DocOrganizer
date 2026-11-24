#define AppName "DocOrganizer 2"
#define AppVersion "2.1.1"

[Setup]
AppId={{B07CE6F3-73D6-4D7D-92B9-1FC5E5615C2A}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\DocOrganizer2
DefaultGroupName={#AppName}
OutputDir=dist\installer
OutputBaseFilename=DocOrganizer2-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\DocOrganizer2.exe
WizardStyle=modern
LicenseFile=LICENSE
SetupIconFile=assets\docorganizer.ico

[Files]
Source: "dist\DocOrganizer2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DocOrganizer 2"; Filename: "{app}\DocOrganizer2.exe"
Name: "{autodesktop}\DocOrganizer 2"; Filename: "{app}\DocOrganizer2.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Run]
Filename: "{app}\DocOrganizer2.exe"; Description: "Abrir DocOrganizer 2"; Flags: nowait postinstall skipifsilent
