; ---------------------------------------
; Nizi POS Connector — Inno Setup installer
; Requires Inno Setup Compiler
; ---------------------------------------
;
; App version from repo-root config.json at compile time (file must be single-line JSON so the first line contains "version":"…").

#ifndef AppVer
#define AppVer "1.0.0"
#endif

#define InstallerVersionJsonPath AddBackslash(SourcePath) + "config.json"

#if FileExists(InstallerVersionJsonPath)
  #define InstallerVersionFileHandle FileOpen(InstallerVersionJsonPath)
  #if InstallerVersionFileHandle
    #define InstallerVersionJsonLine FileRead(InstallerVersionFileHandle)
    #expr FileClose(InstallerVersionFileHandle)

    #define InstallerVersionKeyPos Pos('"version":"', InstallerVersionJsonLine)
    #if InstallerVersionKeyPos
      #define InstallerVersionValueStart (InstallerVersionKeyPos + 11)
      #define InstallerVersionValueEnd Pos('"', Copy(InstallerVersionJsonLine, InstallerVersionValueStart))
      #undef AppVer
      #define AppVer Copy(Copy(InstallerVersionJsonLine, InstallerVersionValueStart), 1, (InstallerVersionValueEnd - 1))
    #endif
  #endif
#endif

[Setup]
AppName=Nizi POS Connector
AppVersion={#AppVer}
AppPublisher=Yarsa Tech
AppPublisherURL=https://yarsa.tech/
DefaultDirName={localappdata}\NiziPOSConnector
DefaultGroupName=Nizi POS Connector
OutputDir=dist
OutputBaseFilename=NiziPOSConnector_Installer
SetupIconFile=assets\\setup_icon.ico
UninstallDisplayIcon={app}\NiziPOSConnector.exe
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "dist\NiziPOSConnector\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "dist\NiziPOSConnector\ota_updater.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Nizi POS Connector"; Filename: "{app}\NiziPOSConnector.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Nizi POS Connector"; Filename: "{app}\NiziPOSConnector.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: autostart; Description: "Start Nizi POS Connector automatically at login"

[Run]
Filename: "{app}\NiziPOSConnector.exe"; Description: "Launch Nizi POS Connector"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
ValueType: string; ValueName: "NiziPOSConnector"; ValueData: "{app}\NiziPOSConnector.exe"; Flags: uninsdeletevalue; Tasks: autostart

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
