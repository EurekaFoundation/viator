; Installatore di Viator per Windows (Inno Setup 6: https://jrsoftware.org/isinfo.php)
; Si compila con build_windows.bat dopo aver creato dist\Viator con PyInstaller.

#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif
#define AppName "Viator"
#define AppExe "Viator.exe"
#define AppPublisher "Eureka Foundation"
#define AppURL "https://github.com/EurekaFoundation/viator"

[Setup]
AppId={{8C5E2F2A-6B1D-4C8E-9A57-3E7B1F0D4A21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; chi non è amministratore può installarlo solo per sé
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist\installer
OutputBaseFilename=Viator-{#AppVersion}-Windows-setup
SetupIconFile=..\..\assets\viator.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\Viator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; --- Viator compare tra i browser in Impostazioni > App > App predefinite
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator"; ValueType: string; ValueName: ""; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"""
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Browser web libero e open source"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities\URLAssociations"; ValueType: string; ValueName: "http"; ValueData: "ViatorURL"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities\URLAssociations"; ValueType: string; ValueName: "https"; ValueData: "ViatorURL"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities\FileAssociations"; ValueType: string; ValueName: ".html"; ValueData: "ViatorHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities\FileAssociations"; ValueType: string; ValueName: ".htm"; ValueData: "ViatorHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "ViatorHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Viator\Capabilities\StartMenu"; ValueType: string; ValueName: "StartMenuInternet"; ValueData: "Viator"
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "Viator"; ValueData: "Software\Clients\StartMenuInternet\Viator\Capabilities"; Flags: uninsdeletevalue
; --- tipi registrati per link e file
Root: HKA; Subkey: "Software\Classes\ViatorURL"; ValueType: string; ValueName: ""; ValueData: "Viator URL"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ViatorURL"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\ViatorURL\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\ViatorURL\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\ViatorHTML"; ValueType: string; ValueName: ""; ValueData: "Documento web Viator"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ViatorHTML\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\ViatorHTML\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
