; ============================================================
; FolderSyncPro 安裝程式腳本
; 需要先安裝 Inno Setup（免費）：https://jrsoftware.org/isinfo.php
;
; 使用方式：
;   1. 先用 PyInstaller 產生 dist_alpha2\FolderSyncPro.exe
;   2. 用 Inno Setup 開啟這個檔案（installer.iss）
;   3. 按 Build > Compile，會在 Output 資料夾產生
;      FolderSyncPro_Setup_v0.2.0-alpha.2.exe，這就是可以直接發送給使用者、
;      雙擊安裝的安裝檔（含開始功能表捷徑、解除安裝程式）
; ============================================================

#define MyAppName "FolderSyncPro"
#define MyAppVersion "0.2.0-alpha.2"
#define MyAppVersionInfo "0.2.0.2"
#define MyAppPublisher "FolderSyncPro"
#define MyAppExeName "FolderSyncPro.exe"

[Setup]
AppId={{A6E9D9B0-6F3B-4B1E-9C2B-FOLDERSYNCPRO}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=FolderSyncPro_Setup_v0.2.0-alpha.2
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoTextVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersionInfo}
Compression=lzma
SolidCompression=yes
; 如需自訂安裝畫面圖示，取消下一行註解並提供 .ico 檔
; SetupIconFile=app_icon.ico
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist_alpha2\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
