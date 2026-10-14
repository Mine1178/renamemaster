"""PyInstaller 打包脚本：把 RenameMaster 打成单文件 EXE。

用法：python build.py

- 在 src/ 目录下执行 PyInstaller（入口 src/rename_master/main.py，--paths src）
- 产物：dist/RenameMaster.exe
- 打包失败时把完整错误写入 inbox/build_error.txt
"""
from __future__ import annotations

import subprocess
import sys
import sysconfig
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
ENTRY = SRC / "rename_master" / "main.py"
ICON = ROOT / "assets" / "rename_master.ico"
DIST = ROOT / "dist"
WORK = ROOT / "build"
ERROR_LOG = ROOT / "inbox" / "build_error.txt"

NAME = "RenameMaster"
HIDDEN_IMPORTS = ["PIL", "openpyxl", "docx", "pypdf", "numpy", "cv2", "pywt",
                  "blind_watermark"]
# 整个包收集（含子模块 / 数据文件），避免动态导入漏掉
COLLECT_ALL = ["blind_watermark"]


def _find_ffmpeg_dlls():
    """定位当前解释器 site-packages 里 cv2 的 ffmpeg 视频 I/O DLL。

    本软件只用 cv2 做图像编解码 / 绘制，不做视频读写；该 DLL 体积约 30MB，
    排除后 EXE 从约 58MB 降到约 48MB。不在主进程 import cv2，避免 DLL 被
    占用导致无法重命名。
    """
    roots = []
    purelib = sysconfig.get_paths().get("purelib")
    if purelib:
        roots.append(Path(purelib))
    roots.extend(Path(p) for p in sys.path if p)
    found = []
    seen = set()
    for base in roots:
        cv2_dir = base / "cv2"
        if not cv2_dir.is_dir():
            continue
        for dll in cv2_dir.glob("opencv_videoio_ffmpeg*.dll"):
            key = str(dll).lower()
            if key not in seen:
                seen.add(key)
                found.append(dll)
    return found


@contextmanager
def _slim_cv2():
    """打包期间临时把 ffmpeg DLL 改名移出，结束后（无论成败）恢复原位。"""
    moved = []
    try:
        for dll in _find_ffmpeg_dlls():
            size_mb = dll.stat().st_size / 1024 / 1024
            hidden = dll.with_name(dll.name + ".excluded")
            dll.rename(hidden)
            moved.append((dll, hidden))
            print(f"[build] 已临时排除视频模块 {dll.name} "
                  f"({size_mb:.1f} MB)", flush=True)
        yield
    finally:
        for dll, hidden in moved:
            try:
                if hidden.exists() and not dll.exists():
                    hidden.rename(dll)
                    print(f"[build] 已恢复 {dll.name}", flush=True)
            except OSError as exc:  # 恢复失败要明确暴露，避免环境被破坏
                print(f"[build] 警告：恢复 {dll.name} 失败：{exc}", flush=True)


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
    for pkg in COLLECT_ALL:
        cmd += ["--collect-all", pkg]
    assets = ROOT / "assets"
    if assets.is_dir():
        cmd += ["--add-data", f"{assets};assets"]
    return cmd


def main() -> int:
    _ensure_pyinstaller()
    cmd = _build_cmd()
    print("[build] cwd =", SRC, flush=True)
    print("[build]", " ".join(cmd), flush=True)

    with _slim_cv2():
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
