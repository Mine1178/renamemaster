@echo off
rem RenameMaster 开发态一键启动（任务书 §7 交付物）
rem 用法：双击本文件，或在命令行执行 run.bat
chcp 65001 >nul
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "%~dp0src"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.11+ 并加入 PATH。
    pause
    exit /b 1
)

python -c "import PIL, openpyxl, docx, pypdf, tkinterdnd2" >nul 2>nul
if errorlevel 1 (
    echo [提示] 依赖不完整，正在安装 requirements.txt ...
    python -m pip install -r "..\requirements.txt"
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重试。
        pause
        exit /b 1
    )
)

python -m rename_master.main
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo [错误] 程序异常退出（代码 %RC%），日志见 %%APPDATA%%\RenameMaster\logs\
    pause
)
endlocal & exit /b %RC%
