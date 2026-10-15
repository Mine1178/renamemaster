"""PyInstaller 打包脚本：把 RenameMaster 打成单文件 EXE。

用法：python build.py

- 在 src/ 目录下执行 PyInstaller（入口 src/rename_master/main.py，--paths src）
- 产物：dist/RenameMaster.exe
- 打包失败时把完整错误写入 inbox/build_error.txt
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
ENTRY = SRC / "rename_master" / "main.py"
ICON = ROOT / "assets" / "rename_master.ico"
DIST = ROOT / "dist"
WORK = ROOT / "build"
ERROR_LOG = ROOT / "inbox" / "build_error.txt"

NAME = "RenameMaster"
HIDDEN_IMPORTS = ["PIL", "openpyxl", "docx", "pypdf"]

# 打包机必须真的具备这些运行时依赖，否则打出来的 EXE 会「能启动但功能缺失」
REQUIRED_MODULES = ["tkinter", "PIL", "openpyxl", "docx", "pypdf",
                    "tkinterdnd2", "PyInstaller"]


def _check_interpreter() -> None:
    """打包解释器自检：必须是装了全部运行依赖的正式解释器。

    历史事故：被沙箱内置运行时（...\\sandbox_runtime\\...\\python.exe）接管后打包，
    产物 Python 能跑、日志能写，但 tcl/tk 数据不全 —— 双击 EXE 后无窗口、
    无报错、进程常驻。这里在打包前直接拦死，并给出正确的解释器路径。
    可用环境变量 RM_BUILD_PYTHON 指定打包解释器。
    """
    exe = sys.executable
    print(f"[build] 打包解释器 = {exe}（Python {sys.version.split()[0]}）",
          flush=True)

    lowered = exe.lower().replace("/", "\\")
    for marker in ("sandbox_runtime", "\\windowsapps\\", "\\temp\\"):
        if marker in lowered:
            raise SystemExit(
                f"[build] 拒绝用可疑解释器打包：{exe}\n"
                f"        命中禁用路径片段 {marker!r}。\n"
                f"        请改用正式解释器，例如：\n"
                f"        $env:RM_BUILD_PYTHON='C:\\Users\\<你>\\AppData\\Local"
                f"\\Programs\\Python\\Python314\\python.exe'\n"
                f"        python build.py")

    import importlib
    missing = []
    for mod in REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:                     # noqa: BLE001
            missing.append(f"{mod}（{exc}）")
    if missing:
        raise SystemExit(
            "[build] 当前解释器缺少打包所需依赖，产物会缺功能：\n  - "
            + "\n  - ".join(missing)
            + f"\n        解释器：{exe}\n"
            "        先在该解释器下 pip install -r requirements.txt，"
            "或用 RM_BUILD_PYTHON 指向正确的解释器。")
    print("[build] 依赖自检通过：", ", ".join(REQUIRED_MODULES), flush=True)


def _python_override() -> None:
    """RM_BUILD_PYTHON 指定打包解释器时，用它重跑本脚本。"""
    want = os.environ.get("RM_BUILD_PYTHON", "").strip()
    if not want:
        return
    want_path = Path(want)
    if not want_path.is_file():
        raise SystemExit(f"[build] RM_BUILD_PYTHON 指向的文件不存在：{want}")
    if Path(sys.executable).resolve() == want_path.resolve():
        return
    print(f"[build] 按 RM_BUILD_PYTHON 切换到 {want_path}", flush=True)
    env = {k: v for k, v in os.environ.items() if k != "RM_BUILD_PYTHON"}
    proc = subprocess.run([str(want_path), str(Path(__file__).resolve()),
                           *sys.argv[1:]], env=env)
    raise SystemExit(proc.returncode)


def _ensure_pyinstaller() -> None:
    """未安装 PyInstaller 时先 pip install。"""
    try:
        import PyInstaller  # noqa: F401
        return
    except ImportError:
        pass
    print("[build] 未检测到 PyInstaller，开始安装 ...", flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                   check=True)


def _build_cmd() -> list[str]:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(ENTRY),
        "--onefile",
        "--noconsole",
        "--icon", str(ICON),
        "--clean",
        "--name", NAME,
        "--paths", str(SRC),
        "--distpath", str(DIST),
        "--workpath", str(WORK),
        "--specpath", str(ROOT),
        "--noconfirm",
    ]
    for mod in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", mod]
    assets = ROOT / "assets"
    if assets.is_dir():
        cmd += ["--add-data", f"{assets};assets"]
    return cmd


def main() -> int:
    _python_override()
    _check_interpreter()
    _ensure_pyinstaller()
    cmd = _build_cmd()
    print("[build] cwd =", SRC, flush=True)
    print("[build]", " ".join(cmd), flush=True)

    proc = subprocess.run(cmd, cwd=str(SRC), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.stdout:
        print(proc.stdout, flush=True)
    if proc.stderr:
        print(proc.stderr, flush=True)

    exe = DIST / f"{NAME}.exe"
    if proc.returncode != 0 or not exe.is_file():
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        ERROR_LOG.write_text(
            f"# PyInstaller 打包失败 (returncode={proc.returncode})\n\n"
            f"## cwd\n{SRC}\n\n"
            f"## command\n{' '.join(cmd)}\n\n"
            f"## stdout\n{proc.stdout}\n\n"
            f"## stderr\n{proc.stderr}\n",
            encoding="utf-8",
        )
        print(f"[build] 失败，错误已写入 {ERROR_LOG}", flush=True)
        return proc.returncode or 1

    print(f"[build] 成功：{exe} ({exe.stat().st_size / 1024 / 1024:.1f} MB)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
