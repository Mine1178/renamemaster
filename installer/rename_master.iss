; RenameMaster 安装包脚本
; 编译：iscc installer\rename_master.iss

#define MyAppName "RenameMaster"
#define MyAppVersion "1.8.0"
#define MyAppPublisher "本地工具"
#define MyAppExeName "RenameMaster.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-RENAMEMASTER01}
AppName=RenameMaster · 文件批量命名助手
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=RenameMaster_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\rename_master.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=1.8.0.0
VersionInfoDescription=RenameMaster 文件批量命名助手
VersionInfoProductName=RenameMaster
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl,ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\RenameMaster"
