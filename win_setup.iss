; ---------------------------------------
; NiziPOS Installer Script
; Requires Inno Setup Compiler
; ---------------------------------------

; Build-time version extraction from `version.json`
#define VersionFileHandle FileOpen("version.json")
#if VersionFileHandle
  #define VersionJsonLine FileRead(VersionFileHandle)
  #expr FileClose(VersionFileHandle)

  ; Extract version value from minified JSON: {"version":"1.2.3"}
  ; We assume the file line contains the substring: "version":"<value>"
  #define KeyPos Pos('"version":"', VersionJsonLine)
  #if KeyPos
    #define VersionValueStart KeyPos + 11
    #define VersionValueEnd Pos('"', Copy(VersionJsonLine, VersionValueStart))
    #define AppVer Copy(Copy(VersionJsonLine, VersionValueStart), 1, VersionValueEnd - 1)
  #else
    #define AppVer "1.0.0"
  #endif
#else
  #define AppVer "1.0.0"
#endif

[Setup]
AppName=NiziPOS
AppVersion={#AppVer}
AppPublisher=Nizi Store
AppPublisherURL=https://nizistore.com
DefaultDirName={localappdata}\NiziPOS
DefaultGroupName=NiziPOS
OutputDir=dist
OutputBaseFilename=NiziPOS_Installer
SetupIconFile=setup_icon.ico
UninstallDisplayIcon={app}\NiziPOS.exe
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

; ---------------------------------------
[Files]
; Copy the whole PyInstaller onedir folder
Source: "dist\NiziPOS\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

; Include updater if any
Source: "dist\NiziPOS\ota_updater.exe"; DestDir: "{app}"; Flags: ignoreversion

; (Icon is embedded in NiziPOS.exe)

; ---------------------------------------
[Icons]
; Start Menu shortcut
Name: "{group}\NiziPOS"; Filename: "{app}\NiziPOS.exe"; WorkingDir: "{app}"

; Desktop shortcut
Name: "{userdesktop}\NiziPOS"; Filename: "{app}\NiziPOS.exe"; Tasks: desktopicon

; ---------------------------------------
[Tasks]
Name: desktopicon; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

; Auto-start task
Name: autostart; Description: "Start NiziPOS automatically at login"

; ---------------------------------------
[Run]
Filename: "{app}\NiziPOS.exe"; Description: "Launch NiziPOS"; Flags: nowait postinstall skipifsilent

; ---------------------------------------
[Registry]
; Auto-start registry key for current user
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
ValueType: string; ValueName: "NiziPOS"; ValueData: "{app}\NiziPOS.exe"; Flags: uninsdeletevalue; Tasks: autostart

; ---------------------------------------
[UninstallDelete]
; Remove installed folder on uninstall
Type: filesandordirs; Name: "{app}"