; WiFiBond 简体中文语言包（自包含，随仓库分发）
; 说明：Inno Setup 官方发行版默认不含 ChineseSimplified.isl。
;       本文件为项目内置的最小中文消息集（纯 [Messages] 覆盖），
;       叠加在 compiler:Default.isl 之上，未覆盖的条目自动回退英文，
;       保证 iscc 在任意 Inno Setup 6.x 上均可编译，不依赖外部语言包。
;
; 用法（wifibond.iss）：
;   [Languages]
;   Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl,ChineseSimplified.isl"

[LangOptions]
LanguageName=简体中文
LanguageID=$0804
LanguageCodePage=936

[Messages]
SetupAppTitle=安装
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallAppFullTitle=卸载 %1
SetupLdrStartupMessage=即将安装 %1。是否继续？
ExitSetupTitle=退出安装
ExitSetupMessage=安装尚未完成。现在退出将不会安装 %1。%n%n你可以稍后再次运行安装程序以完成安装。%n%n现在退出吗？
AboutSetupMenuItem=关于安装程序(&A)...
AboutSetupTitle=关于安装程序
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonNo=否(&N)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonNewFolder=新建文件夹(&M)
WelcomeLabel1=欢迎使用 %1 安装向导
WelcomeLabel2=安装程序将引导你完成 %1 的安装。%n%n建议关闭其他应用程序后再继续。
WizardSelectDir=选择目标位置
SelectDirDesc=将要安装 %1 到何处？
SelectDirLabel3=安装程序将安装 %1 到以下文件夹。
SelectDirBrowseLabel=点击“下一步”继续。如需更改文件夹，点击“浏览”。
DiskSpaceGBLabel=至少需要 %1 GB 的可用磁盘空间。
DiskSpaceMBLabel=至少需要 %1 MB 的可用磁盘空间。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序至少需要 %1 KB 的可用空间，所选驱动器仅有 %2 KB 可用。%n%n是否仍要继续？
DirExistsTitle=文件夹已存在
DirExists=文件夹：%n%n%1%n%n已存在。是否仍安装到该文件夹？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹：%n%n%1%n%n不存在。是否创建该文件夹？
WizardSelectTasks=选择附加任务
SelectTasksDesc=需要执行哪些附加任务？
SelectTasksLabel2=安装程序可在 %1 的同时执行以下附加任务，请选择要执行的任务，然后点击“下一步”。
WizardSelectProgramGroup=选择开始菜单文件夹
SelectStartMenuFolderDesc=在何处放置程序的快捷方式？
SelectStartMenuFolderLabel3=安装程序将在以下开始菜单文件夹创建程序快捷方式。
SelectStartMenuFolderBrowseLabel=点击“下一步”继续。如需更改文件夹，点击“浏览”。
MustEnterGroupName=必须输入文件夹名。
GroupNameTooLong=文件夹名过长。
InvalidGroupName=文件夹名包含无效字符。
ReadyLabel1=安装程序已准备就绪，即将开始安装 %1 到你的计算机。
ReadyLabel2a=点击“安装”开始安装，或点击“上一步”检查或更改设置。
ReadyLabel2b=点击“安装”开始安装。
ReadyMemoDir=目标位置：
ReadyMemoGroup=开始菜单文件夹：
ReadyMemoTasks=附加任务：
PreparingDesc=正在准备安装 %1。
PreviousInstallNotCompleted=先前的安装未完成，请重启计算机后重新运行本安装程序。
InstallingLabel=正在安装 %1，请稍候...
FinishedHeadingLabel=完成 %1 安装向导
FinishedLabelNoIcons=安装程序已完成 %1 的安装。
FinishedLabel=安装程序已完成 %1 的安装，可通过桌面图标启动。
ClickFinish=点击“完成”退出安装向导。
RunEntryExec=运行 %1
RunEntryShellExec=打开 %1
ErrorTitle=错误
ErrorCopying=复制文件时出错：%n%n%1%n%n点击“重试”重试，点击“跳过”跳过该文件，或点击“取消”中止安装。
ErrorCreatingDir=创建文件夹失败：%n%n%1%n%n点击“重试”重试。
ErrorTooManyFilesInDir=文件夹内文件过多，无法复制：%n%n%1
ErrorRestartReplace=重命名文件失败：%n%n%1
WinVersionTooLowError=本程序需要 %1 版本 %2 或更高。
UninstallNotFound=文件不存在，无法卸载。
UninstallOpenError=无法打开文件，卸载失败。
UninstallUnsupportedVer=本卸载程序无法识别该版本安装信息，卸载失败。
UninstallUnknownEntry=卸载信息中存在未知条目 (%1)，卸载失败。
ConfirmUninstall=确定要完全卸载 %1 及其全部组件吗？
UninstallOnlyOnWin64=本卸载程序仅适用于 64 位 Windows。
OnlyAdminCanUninstall=仅管理员可卸载本程序。
UninstallStatusLabel=正在卸载 %1，请稍候...
UninstalledAll=%1 已成功卸载。
UninstalledMost=%1 卸载完成。%n%n部分文件未能删除，可手动删除。
UninstalledAndNeedsRestart=卸载 %1 需要重启计算机。%n%n现在重启吗？
UninstallDataCorrupted=“%1”文件损坏或不存在，卸载失败。
ConfirmDeleteSharedFileTitle=删除共享文件？
ConfirmDeleteSharedFile2=以下共享文件已无程序使用，是否删除？%n%n%1%n%n选择“否”将保留该文件；如不确定，建议选择“否”。
