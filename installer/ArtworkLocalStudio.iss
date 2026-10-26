#ifndef AppVersion
  #define AppVersion "0.2.3"
#endif
#ifndef SourceDir
  #define SourceDir "..\release\" + AppVersion + "\ArtworkLocalStudio"
#endif
#ifndef OutputDir
  #define OutputDir "..\release\" + AppVersion
#endif
[Setup]
AppId={{C69ADC52-8C70-4C13-A2A3-EC59B32D79C8}
AppName=Artwork Local Studio
AppVersion={#AppVersion}
AppPublisher=minhtuan5991
AppPublisherURL=https://github.com/minhtuan5991/artwork-local-studio
AppUpdatesURL=https://github.com/minhtuan5991/artwork-local-studio/releases
DefaultDirName={localappdata}\Programs\Artwork Local Studio
DefaultGroupName=Artwork Local Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#OutputDir}
OutputBaseFilename=ArtworkLocalStudio-Setup-{#AppVersion}
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\ArtworkLocalStudio.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=ArtworkLocalStudio.exe,ArtworkNativeHost.exe
RestartApplications=no
DisableWelcomePage=no
SetupLogging=yes
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "nativehost"; Description: "Connect Chrome / Edge to Artwork Local Studio"; Check: NormalInstallation
[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Excludes: "data\*,output\*,models\*,runtime\*,downloads\*,native-config.json,installation.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installation.json"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\Artwork Local Studio"; Filename: "{app}\ArtworkLocalStudio.exe"; Check: NormalInstallation
Name: "{autodesktop}\Artwork Local Studio"; Filename: "{app}\ArtworkLocalStudio.exe"; Tasks: desktopicon; Check: NormalInstallation
[Run]
Filename: "{app}\ArtworkNativeHost.exe"; Parameters: "--register"; Flags: runhidden waituntilterminated; Tasks: nativehost; Check: NormalInstallation
Filename: "{app}\ArtworkLocalStudio.exe"; Description: "Launch Artwork Local Studio"; Flags: nowait postinstall skipifsilent; Check: NormalInstallation
[UninstallRun]
Filename: "{app}\ArtworkNativeHost.exe"; Parameters: "--unregister"; Flags: runhidden waituntilterminated; RunOnceId: "UnregisterNativeHost"
[Code]
function NormalInstallation: Boolean;
begin
  Result := ExpandConstant('{param:TESTMODE|0}') <> '1';
end;
