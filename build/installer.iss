; Inno Setup script for the Windows installer (plan §9).
; 1) Build the app:  pyinstaller build/main.spec --noconfirm
; 2) Compile this script with Inno Setup (iscc build/installer.iss)
; Produces: build/Output/AIMusicContractAnalyzer-Setup.exe

#define MyAppName "MasterClause - Music Contract Analyzer"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "MasterClause"
#define MyAppExeName "MasterClause.exe"

[Setup]
AppId={{B2E6B7C2-4A4E-4C7E-9A1E-AICONTRACT2026}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MasterClause
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=MasterClause-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Bundle the PyInstaller onedir output produced in dist\MasterClause
Source: "..\dist\MasterClause\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
