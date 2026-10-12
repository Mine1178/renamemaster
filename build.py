"""PyInstaller 打包脚本：把 RenameMaster 打成单文件 EXE。

用法：python build.py

- 在 src/ 目录下执行 PyInstaller（入口 src/rename_master/main.py，--paths src）
- 产物：dist/RenameMaster.exe
- 打包失败时把完整错误写入 inbox/build_error.txt
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
ENTRY = SRC / "rename_master" / "main.py"
ICON = ROOT / "assets" / "rename_master.ico"
DIST = ROOT / "dist"
WORK = ROOT / "build"
ERROR_LOG = ROOT / "inbox" / "build_error.txt"

NAME = "RenameMaster"
HIDDEN_IMPORTS = ["PIL", "openpyxl", "docx", "pypdf"]


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
    return cmd


def main() -> int:
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
