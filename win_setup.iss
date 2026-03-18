; ---------------------------------------
; NiziPOS Installer Script
; Requires Inno Setup Compiler
; ---------------------------------------

[Setup]
AppName=NiziPOS
AppVersion=1.0.0
DefaultDirName={localappdata}\NiziPOS
DefaultGroupName=NiziPOS
OutputDir=dist
OutputBaseFilename=NiziPOS_Installer
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes

; ---------------------------------------
[Files]
; Copy the whole PyInstaller onedir folder
Source: "dist\NiziPOS\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

; Include updater if any
; Source: "dist\NiziPOS\updater.exe"; DestDir: "{app}"; Flags: ignoreversion

; Optional: add icon
; Source: "assets\NiziPOS.ico"; DestDir: "{app}"; Flags: ignoreversion

; ---------------------------------------
[Icons]
; Start Menu shortcut
Name: "{group}\NiziPOS"; Filename: "{app}\NiziPOS.exe"; WorkingDir: "{app}"; IconFilename: "{app}\NiziPOS.ico"

; Desktop shortcut
Name: "{userdesktop}\NiziPOS"; Filename: "{app}\NiziPOS.exe"; IconFilename: "{app}\NiziPOS.ico"; Tasks: desktopicon

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