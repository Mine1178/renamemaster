"""统一测试入口（CODEX 测评团队 v1.9 起）。

用法（项目根目录下）：
    python tests/run_all.py              # 跑全部用例
    python tests/run_all.py rename ui    # 只跑文件名含 rename / ui 的用例
    python tests/run_all.py --list       # 只列用例

约定
----
- 新用例文件统一命名 ``tests/t_*.py``，内部提供 ``main() -> int``（0 = 通过），
  并以 ``sys.exit(main())`` 收尾。
- 每个用例在**独立子进程**中运行，避免 Tk 解释器 / matplotlib 等全局状态互相污染；
  子进程超时（默认 300 秒）视为失败。
- 统一把 `PYTHONIOENCODING` 设成 utf-8，避免 GBK 控制台因 ✓ / 中文符号崩溃。
- 子进程 cwd 默认项目根；`tests/smoke.py` 这类要求 cwd=src 的旧脚本走 LEGACY 表。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"

# 沙箱 / 精简环境下 Tk 找不到自带的 tcl/tk 脚本目录，会报
# "Can't find a usable init.tcl"。仓库内 .cache/tcl_lib 是标准库同版本
# 目录的副本，显式指过去后 Tk 用例才起得来；缺失时保持原环境不变。
TCL_FALLBACK = ROOT / ".cache" / "tcl_lib"
TKDND_FALLBACK = ROOT / ".cache" / "tkdnd"
# 用例统一隔离「用户数据目录」：被测代码把 config.json / history.json 写在
# %APPDATA%\RenameMaster 下。若让用例直接用真实目录，会同时踩两个坑：
#   1) 断言「默认值」时读到用户保存过的值 → 假失败，甚至反过来掩盖缺陷；
#   2) 用例执行本身会改写用户真实配置与撤销历史。
# 统一指到仓库内 .cache/test_appdata（t_pkg_exe.py 自己还会覆盖成
# .cache/smoke_appdata，互不影响）。
TEST_APPDATA = ROOT / ".cache" / "test_appdata"


def _ensure_tkdnd_copy() -> bool:
    """受限环境里 Tcl 读不到 site-packages 下的 tkdnd，把扩展复制进仓库再指过去。

    只用 Python 复制（Python 侧能读，Tcl 侧不能），失败就算了——拖放不可用时
    应用会自己降级，相关用例会报出真实原因。
    """
    dest = TKDND_FALLBACK / "windows"
    if (dest / "pkgIndex.tcl").is_file():
        return True
    try:
        import tkinterdnd2
    except Exception:                                    # noqa: BLE001
        return False
    src = Path(tkinterdnd2.__file__).parent / "tkdnd"
    tcl_major = 8
    try:                                                 # Tcl 9 要用 -tcl9 那份
        import tkinter
        tcl_major = int(tkinter.Tcl().eval("info tclversion").split(".")[0])
    except Exception:                                    # noqa: BLE001
        pass
    pick = (src / ("win-x64-tcl9" if tcl_major >= 9 else "win-x64"))
    if not pick.is_dir():
        pick = src / "win-x64"
    if not pick.is_dir():
        return False
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    # 逐文件覆盖：目录整体替换会在 DLL 被占用时整片失败（Windows 上很常见）
    for f in pick.iterdir():
        if f.is_file():
            try:
                shutil.copy2(f, dest / f.name)
            except OSError:
                pass
    return (dest / "pkgIndex.tcl").is_file()

# 控制台可能是 GBK（Windows 中文默认），统一改成 UTF-8，避免打报告时崩在 ✓ / emoji 上
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):  # 被重定向到不支持 reconfigure 的对象
        pass

# 历史用例（v1.4~v1.8 遗留）：名字 -> 运行时的 cwd
LEGACY: dict[str, Path] = {
    "smoke.py": SRC,
    "smoke_final.py": ROOT,
    "test_features4.py": ROOT,
    "test_ui_features4.py": ROOT,
    "test_watermark_page.py": ROOT,
    "test_dnd.py": ROOT,
    "check_layout.py": ROOT,
}


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        TEST_APPDATA.mkdir(parents=True, exist_ok=True)
        env["APPDATA"] = str(TEST_APPDATA)
    except OSError:
        pass
    if (TCL_FALLBACK / "tcl8.6" / "init.tcl").is_file():
        cur_tcl = env.get("TCL_LIBRARY", "")
        if not (cur_tcl and (Path(cur_tcl) / "init.tcl").is_file()):
            env["TCL_LIBRARY"] = str(TCL_FALLBACK / "tcl8.6")
        if not env.get("TK_LIBRARY"):
            env["TK_LIBRARY"] = str(TCL_FALLBACK / "tk8.6")
        # TCLLIBPATH 是 Tcl 启动时**前置**进 auto_path 的，所以 tkdnd 要放在这，
        # 不能用 tkinterdnd2 自己的追加（那份路径在受限环境读不到）。
        # 必须用正斜杠：TCLLIBPATH 按 Tcl 列表解析，反斜杠会被当转义符吃掉。
        if _ensure_tkdnd_copy():
            env["TCLLIBPATH"] = (TKDND_FALLBACK / "windows").as_posix()
    old = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SRC) + (os.pathsep + old if old else "")
    return env


def _collect() -> list[tuple[str, Path, Path]]:
    """返回 [(显示名, 脚本路径, cwd), ...]，新用例在前。"""
    cases: list[tuple[str, Path, Path]] = []
    for path in sorted(TESTS.glob("t_*.py")):
        cases.append((path.name, path, ROOT))
    for name, cwd in LEGACY.items():
        path = TESTS / name
        if path.is_file():
            cases.append((f"[legacy] {name}", path, cwd))
    return cases


def _run(name: str, path: Path, cwd: Path, timeout: int) -> tuple[bool, float, str]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(cwd),
            env=_child_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, time.perf_counter() - start, f"超时（>{timeout}s）"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, time.perf_counter() - start, out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RenameMaster 统一测试入口")
    parser.add_argument("filters", nargs="*", help="按名字过滤（子串匹配，忽略大小写）")
    parser.add_argument("--list", action="store_true", help="只列出用例")
    parser.add_argument("--timeout", type=int, default=300, help="单用例超时秒数")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出全部用例日志")
    args = parser.parse_args(argv)

    cases = _collect()
    if args.filters:
        wanted = [f.lower() for f in args.filters]
        cases = [c for c in cases if any(w in c[0].lower() for w in wanted)]
    if not cases:
        print("没有匹配的用例。")
        return 1
    if args.list:
        for name, path, cwd in cases:
            print(f"{name:<32} {path}")
        return 0

    results: list[tuple[str, bool, float, str]] = []
    for name, path, cwd in cases:
        print(f"=== {name} " + "=" * max(4, 60 - len(name)), flush=True)
        ok, secs, out = _run(name, path, cwd, args.timeout)
        results.append((name, ok, secs, out))
        if args.verbose or not ok:
            print(out.rstrip())
        else:
            tail = [ln for ln in out.splitlines() if ln.strip()][-3:]
            print("\n".join(tail))
        print(f"--> {'PASS' if ok else 'FAIL'} ({secs:.1f}s)", flush=True)

    failed = [r for r in results if not r[1]]
    print("\n" + "=" * 68)
    print(f"合计 {len(results)} 个用例：通过 {len(results) - len(failed)}，失败 {len(failed)}")
    for name, _ok, secs, _out in failed:
        print(f"  FAIL  {name}  ({secs:.1f}s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
