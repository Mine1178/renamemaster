"""交付物冒烟：真实启动 dist\\RenameMaster.exe（或源码态应用），确认出窗口、有标题、可截图，然后关闭。

对应验收项 A1 / A2 / A3 / K2：
- 双击 EXE 能在 20 秒内出主窗口；
- 窗口标题正确、尺寸合理（最大化后宽度 > 900）；
- 截图落盘到 inbox/exe_smoke.png，供人工目检界面。

用法：
    python tests/t_pkg_exe.py                 # auto：有 EXE 就「EXE + 源码态」都冒烟
    python tests/t_pkg_exe.py --target exe    # 只冒烟 dist\\RenameMaster.exe
    python tests/t_pkg_exe.py --target src    # 只冒烟源码态（python src/rename_master/main.py）
    python tests/t_pkg_exe.py --target both   # 两种都跑（EXE 不存在时该项 SKIP）
    python tests/t_pkg_exe.py --wait 60       # 调整等待秒数（默认 40）

【坑】PyInstaller onefile 是「引导进程 + 子进程」两层：真正建窗的是子进程，
所以查窗口必须遍历整个进程树，只看 Popen 返回的那个 pid 会永远查不到窗口。

失败时除错误清单外，还会打印进程树的全部顶层窗口（含隐藏）、CPU 时间与应用
日志 tail（%APPDATA%\\RenameMaster\\logs），用于区分「根本没建窗」和「建窗后阻塞」。

EXE 不存在时该目标打印 SKIP（源码态冒烟照跑），最后按实际跑过的目标报结论。
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "RenameMaster.exe"
SRC_ENTRY = ROOT / "src" / "rename_master" / "main.py"
SHOT = ROOT / "inbox" / "exe_smoke.png"

# 冒烟用独立的“用户数据目录”：被测程序会往 %APPDATA%\RenameMaster 写日志与配置，
# 指到仓库内既避免污染真实用户数据，也让受限环境（%APPDATA% 不可写）照样能跑完。
SMOKE_APPDATA = ROOT / ".cache" / "smoke_appdata"
APP_LOG_DIR = SMOKE_APPDATA / "RenameMaster" / "logs"

# 【坑】父进程（run_all.py）为了让 Tk 用例在受限环境里跑起来，会把
# TCL_LIBRARY / TK_LIBRARY 指向仓库内 .cache 的备用 tcl/tk 目录。这些变量一旦
# 被被测程序继承，Tcl 就会去那个路径找 init.tcl，onefile 包自带的 _tcl_data
# 反被忽略 → 界面初始化失败，表现为「进程活着但永不出窗」。
# 冒烟必须复现真实用户的双击场景（干净环境），所以启动前剔除这些变量。
_TCL_POISON = ("TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH", "TCL_LIBRARY_PATH")
_PY_POISON = ("PYTHONPATH", "PYTHONHOME", "PYTHONUTF8", "PYTHONIOENCODING",
              "PYTHONSTARTUP", "PYTHONLEGACYWINDOWSFSENCODING")


def _popen_env(target: str) -> dict[str, str]:
    """构造被测进程环境。

    - EXE 态：剥掉 TCL_* / PYTHON* 继承变量，复现真实用户双击（干净环境）；
      冻结体自带 tcl/tk 数据，外部指过去的路径反而会打乱定位。
    - 源码态：被测进程跑的是**本机解释器**，Tk 要靠解释器自带的 tcl/tk 目录。
      受限环境（沙箱里 Tcl 读不到 site-packages/AppData）下只有父进程给的
      TCL_LIBRARY / TK_LIBRARY / TCLLIBPATH 能救活它，所以这几个必须保留，
      否则源码态冒烟永远报 "Can't find a usable init.tcl"，把真实缺陷淹掉。
    """
    drop = {n.upper() for n in _PY_POISON}
    if target == "exe":                     # 冻结体不依赖外部 Python/Tcl 环境变量
        drop |= {n.upper() for n in _TCL_POISON}
    env = {k: v for k, v in os.environ.items() if k.strip().upper() not in drop}
    if target != "exe":
        _sanitize_tcl_env(env)
    env["APPDATA"] = str(SMOKE_APPDATA)
    return env


def _sanitize_tcl_env(env: dict[str, str]) -> None:
    """源码态 Tcl 变量体检：只保留真指向有效目录的，并统一成正斜杠。

    父进程给的 TCL_LIBRARY 若指错（陈旧路径 / 反斜杠被当转义符吃掉的
    TCLLIBPATH），保留下来只会让 Tk 更找不到 init.tcl，宁可清掉让它走默认探测。
    """
    for name, probe in (("TCL_LIBRARY", "init.tcl"), ("TK_LIBRARY", "tk.tcl")):
        val = env.get(name)
        if val and not (Path(val) / probe).is_file():
            env.pop(name, None)
    libpath = env.get("TCLLIBPATH")
    if libpath:
        keep = [p for p in libpath.replace("\\", "/").split() if Path(p).is_dir()]
        if keep:
            env["TCLLIBPATH"] = " ".join(keep)   # Tcl 列表语法：正斜杠，空格分隔
        else:
            env.pop("TCLLIBPATH", None)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

TH32CS_SNAPPROCESS = 0x00000002


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _enable_dpi() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:                                    # noqa: BLE001
        pass


def _process_tree(root_pid: int) -> set[int]:
    """root_pid 及其全部后代 pid（onefile 的引导进程会再拉起子进程）。"""
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pids = {root_pid}
    if not snap or snap == wintypes.HANDLE(-1).value:
        return pids
    pairs: list[tuple[int, int]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pairs.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID)))
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    grew = True
    while grew:
        grew = False
        for pid, ppid in pairs:
            if ppid in pids and pid not in pids:
                pids.add(pid)
                grew = True
    return pids


def _enum_windows(pids: set[int], only_visible: bool) -> list[tuple[int, int, str]]:
    """指定 pid 集合的顶层窗口，返回 (hwnd, visible, '类名 :: 标题')。"""
    found: list[tuple[int, int, str]] = []

    def cb(hwnd, _lparam):
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value not in pids:
            return True
        visible = bool(user32.IsWindowVisible(hwnd))
        if only_visible and not visible:
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        found.append((int(hwnd), int(visible), f"{cls.value} :: {buf.value}"))
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


# 主窗口的标题标记：真实窗口标题形如 "RenameMaster · 文件批量命名助手"。
APP_TITLE_MARK = "RenameMaster"
# 【坑】Tk 在 set_title 之前会先映射一个标题恰为 "tk" 的顶层窗，tkinterdnd2 之类的
# 扩展也可能额外产生可见的占位顶层窗。EnumWindows 的枚举顺序不保证「主窗口在前」，
# 早先「取第一个可见有标题窗口」的写法会撞上这个占位窗，把冒烟判成
# 「窗口标题不含 RenameMaster」的假失败（诊断清单里其实能看到正确窗口）。
_TK_PLACEHOLDER_TITLES = {"tk", "toplevel", "tk::toplevel", "root"}

# 【坑】启动失败时 main.py 会弹一个系统对话框（类名 #32770），标题是
# "RenameMaster - 图形界面初始化失败（Tk 不可用）"。它含 "RenameMaster"
# 三个字，也"可见、有标题"，早先的判据会把它当成主窗口 → 冒烟假通过。
# 所以：真的主窗口必须是 Tk 顶层窗（类名 TkTopLevel），对话框一律不算。
_DIALOG_CLASSES = {"#32770", "static", "button", "tooltips_class32"}
_FATAL_TITLE_MARKERS = ("初始化失败", "启动失败", "无法启动", "Tk 不可用",
                        "unhandled exception", "traceback", "exception")


def _main_window(proc_pid: int) -> tuple[int, str] | None:
    """进程树里的主窗口：优先标题含应用名，其次才退到「可见 + 有标题」的窗口。

    返回 (hwnd, title)。调用方可用 APP_TITLE_MARK 判断拿到的到底是不是真主窗口。
    死板的系统对话框（错误提示 / 崩溃框）永不作为候选。
    """
    fatal: list[str] = []
    fallback: tuple[int, str] | None = None
    for hwnd, _vis, desc in _enum_windows(_process_tree(proc_pid), True):
        cls, _, raw_title = desc.partition(" :: ")
        if cls.lower().startswith("pyinstaller"):
            continue
        title = raw_title.strip()
        if not title:
            continue
        low_title = title.lower()
        if cls.lower() in _DIALOG_CLASSES or any(
                m in low_title for m in _FATAL_TITLE_MARKERS):
            fatal.append(f"{cls} :: {title}")
            continue
        if APP_TITLE_MARK.lower() in title.lower():
            return hwnd, title                      # 真主窗口：直接返回
        if fallback is None and low_title not in _TK_PLACEHOLDER_TITLES:
            fallback = (hwnd, title)                # 可疑但不是占位窗：先记着
    if fatal:
        # 有错误对话框 = 启动就失败了，绝不能退到 fallback 假装通过
        global _FATAL_DIALOG_SEEN                      # noqa: PLW0603
        _FATAL_DIALOG_SEEN = fatal
        return None
    return fallback


# 启动过程中出现的错误对话框（供 main() 报错用）
_FATAL_DIALOG_SEEN: list[str] = []


def _rect(hwnd: int) -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


class _WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("rcNormalPosition", wintypes.RECT),
    ]


_SHOW_CMD_NAME = {0: "hidden", 1: "normal", 2: "minimized", 3: "maximized"}


def _placement(hwnd: int) -> str:
    """窗口放置状态：用于区分「从未最大化」与「最大化后又被改回小窗」。"""
    wp = _WINDOWPLACEMENT()
    wp.length = ctypes.sizeof(_WINDOWPLACEMENT)
    if not user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
        return f"<GetWindowPlacement 失败 err={ctypes.get_last_error()}>"
    n = wp.rcNormalPosition
    return (f"showCmd={wp.showCmd}"
            f"({_SHOW_CMD_NAME.get(int(wp.showCmd), '?')})"
            f" normal={n.right - n.left}x{n.bottom - n.top}@({n.left},{n.top})"
            f" flags={wp.flags}")


def _log_tail(path: Path, lines: int = 25) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"<读取失败 {exc}>"
    return "\n".join(text[-lines:])


# 受限/无交互桌面环境（会话 0、沙箱、远程无桌面）下 ImageGrab 必然失败，
# 这是「环境不具备截图能力」，不是被测软件缺陷 —— 降级为 WARN。
_ENV_GRAB_MARKERS = (
    "screen grab failed",
    "grabber not found",
    "grabber failed",
    "no screen",
    "not implemented",
    "bitblt failed",
    "cannot find window handle",
)


def _grab_shot(bbox: tuple[int, int, int, int],
               dest: Path | None = None) -> tuple[bool, str, bool]:
    """截图。返回 (是否成功, 说明, 是否属于环境不支持)。"""
    dest = dest or SHOT
    try:
        from PIL import ImageGrab
    except Exception as exc:                            # noqa: BLE001
        return False, f"截图失败（PIL 不可用）: {exc}", True
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        img = ImageGrab.grab(bbox=bbox)
        img.save(dest)
    except Exception as exc:                            # noqa: BLE001
        detail = f"{type(exc).__name__}: {exc}"
        env_blocked = any(m in detail.lower() for m in _ENV_GRAB_MARKERS)
        return False, f"截图失败: {detail}", env_blocked
    if img.width < 900:
        return False, f"截图过窄，疑似未渲染: {img.width}", False
    print(f"截图已保存: {dest} ({img.width}x{img.height})")
    return True, f"{img.width}x{img.height}", False


def _diagnose(root_pid: int) -> None:
    """失败诊断：进程树窗口清单 + CPU 时间 + 应用日志 tail。"""
    print("\n--- 诊断 ---")
    pids = _process_tree(root_pid)
    print(f"进程树 pid: {sorted(pids)}")
    wins = _enum_windows(pids, only_visible=False)
    if wins:
        print(f"顶层窗口 {len(wins)} 个（含隐藏）：")
        for hwnd, vis, desc in wins:
            print(f"  hwnd={hwnd} visible={vis} {desc}")
    else:
        print("进程树内没有任何顶层窗口：说明还没走到建窗，不是「窗口被藏起来」")
    for pid in sorted(pids):
        h = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)   # QUERY_INFO | VM_READ
        if not h:
            continue
        try:
            class _FT(ctypes.Structure):
                _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]

            creation, exit_t, kern, user = (_FT() for _ in range(4))
            if kernel32.GetProcessTimes(h, ctypes.byref(creation),
                                        ctypes.byref(exit_t), ctypes.byref(kern),
                                        ctypes.byref(user)):
                total = ((kern.hi << 32 | kern.lo) + (user.hi << 32 | user.lo)) / 1e7
                print(f"pid={pid} CPU 时间: {total:.2f}s"
                      f"（≈0 且无窗口说明卡在等待，而非死循环）")
        finally:
            kernel32.CloseHandle(h)
    today = APP_LOG_DIR / f"run_{datetime.now():%Y%m%d}.log"
    if today.is_file():
        print(f"\n应用日志 tail（{today}）：")
        print(_log_tail(today))
    else:
        print(f"\n未找到应用日志：{today}")


def _kill_tree(pid: int) -> None:
    """onefile EXE 是引导进程套子进程，必须连树一起杀，否则残留僵尸进程。"""
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                   capture_output=True, check=False)


def _smoke(target: str, wait: float) -> tuple[list[str], list[str]]:
    """冒烟单个目标（"exe" / "src"），返回 (错误清单, 警告清单)。"""
    if target == "src":
        cmd = [sys.executable, str(SRC_ENTRY)]
        label = f"源码态应用（{sys.executable}）"
    else:
        cmd = [str(EXE)]
        label = str(EXE)

    _enable_dpi()
    print(f"启动 {label} ...")
    SMOKE_APPDATA.mkdir(parents=True, exist_ok=True)
    env = _popen_env(target)
    _FATAL_DIALOG_SEEN.clear()
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)
    errors: list[str] = []
    warnings: list[str] = []
    win: tuple[int, str] | None = None
    fallback: tuple[int, str] | None = None
    started = time.time()
    try:
        deadline = started + wait
        while time.time() < deadline:
            if proc.poll() is not None:
                errors.append(f"进程提前退出，返回码 {proc.returncode}"
                              f"（存活 {time.time() - started:.1f}s）")
                break
            cand = _main_window(proc.pid)
            if cand is not None:
                if APP_TITLE_MARK.lower() in cand[1].lower():
                    win = cand
                    break
                # 只在撞到「标题不像主窗口」的窗口时继续等真正的那个；
                # 等到宽限期还没出现，则用兜底窗口给出更具体的失败信息。
                if fallback is None:
                    fallback = cand
                elif time.time() - started > 12:
                    break
            time.sleep(0.5)

        if win is None:
            win = fallback
        if win is None and not errors:
            if _FATAL_DIALOG_SEEN:
                errors.append(
                    f"{wait:.0f} 秒内未出现主窗口，但出现了启动失败对话框："
                    + "；".join(_FATAL_DIALOG_SEEN))
            else:
                errors.append(f"{wait:.0f} 秒内未出现可见主窗口")
        elif win is not None:
            print(f"出窗耗时: {time.time() - started:.1f}s")

        if win is not None:
            hwnd, title = win
            print(f"窗口标题: {title!r}")
            if "RenameMaster" not in title:
                errors.append(f"窗口标题不含 RenameMaster: {title!r}")
            # 【坑】「找到带正确标题的窗口」≠「窗口已经映射出来」。Tk 在 main.py
            # 建窗早期就会把标题挂上去，但那一刻窗口还停在 (-32000,-32000) 的默认
            # 占位位置、尺寸仍是 314x50；此时调 SW_MAXIMIZE 是无效的（窗口还没
            # 变成可最大化状态），2.5 秒后量出来就是 314x50 → 源码态冒烟随机报
            # 「窗口尺寸偏小」的假失败（v1.9 首次修复：轮询到就绪再测量）。
            # 【坑】夹具竞态（v1.10.1 修）：早先每 0.5 秒**无条件**发一次
            # ShowWindow(SW_MAXIMIZE)+SetForegroundWindow，会在窗口还没进 mainloop
            # （Tk 仍停在初始 314x50 占位几何）时反复干预，把窗口状态搅乱 ——
            # 约 1/5 概率量出 314x50 → 报「窗口尺寸偏小」假失败（EXE 态与源码态
            # 都复现过，而自然启动与新开窗口完全正常，属夹具自身的竞态）。
            # 判据：先纯被动轮询，等窗口自己长到正常量级；只有超过 4 秒仍偏小
            # 才助推一次，之后继续被动等。总预算 15 秒不变。
            settle_end = time.time() + 15
            nudge_at = time.time() + 4
            nudged = False
            while time.time() < settle_end:
                left, top, right, bottom = _rect(hwnd)
                if right - left >= 900 and bottom - top >= 600:
                    break
                if not nudged and time.time() >= nudge_at:
                    nudged = True
                    try:
                        user32.ShowWindow(hwnd, 3)      # SW_MAXIMIZE
                        user32.SetForegroundWindow(hwnd)
                    except Exception as exc:            # noqa: BLE001
                        print("置前失败（不影响判定）:", exc)
                time.sleep(0.5)
            # 尺寸就绪后再把窗口抬到前台一次：截图是抓屏幕区域，窗口若被别的
            # 窗口压住就会截到别人的画面。此时被测窗口已进 mainloop，抬前台安全。
            try:
                user32.SetForegroundWindow(hwnd)
            except Exception:                       # noqa: BLE001
                pass
            time.sleep(1.5)                         # 等首屏渲染完
            left, top, right, bottom = _rect(hwnd)
            w, h = right - left, bottom - top
            print(f"窗口尺寸: {w}x{h} @ ({left},{top})")
            if w < 900 or h < 600:
                errors.append(f"窗口尺寸偏小: {w}x{h}")
                print(f"窗口放置状态: {_placement(hwnd)}"
                      f"（nudged={nudged}）")
            shot = SHOT if target == "exe" else SHOT.with_name("src_smoke.png")
            ok, detail, env_blocked = _grab_shot((left, top, right, bottom), shot)
            if not ok:
                if env_blocked:
                    warnings.append(
                        f"跳过界面截图（当前环境无交互桌面/截图能力）：{detail}")
                else:
                    errors.append(detail)
        # 启动期写了崩溃日志 → 说明走了兜底分支（用户实际看到的是错误框）
        for crash in sorted(APP_LOG_DIR.glob("crash_*.log")):
            if crash.stat().st_mtime >= started - 1:
                errors.append(f"本次冒烟期间产生了崩溃日志 {crash.name}："
                              + _log_tail(crash, 6).replace("\n", " | "))
    finally:
        if errors and proc.poll() is None:
            _diagnose(proc.pid)
        _kill_tree(proc.pid)
        try:
            proc.wait(timeout=10)
        except Exception:                           # noqa: BLE001
            pass
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # 默认 auto：有 dist\\RenameMaster.exe 就「打包体 + 源码态」都冒烟，
    # 没有（还没打包 / 只跑单测）就退化成源码态 —— 交付前必跑打包体，日常开发
    # 也能靠源码态冒烟挡住「启动即弹错误框」这类回归。
    target, wait = "auto", 40.0
    if "--target" in argv:
        target = argv[argv.index("--target") + 1].lower()
    if "--wait" in argv:
        wait = float(argv[argv.index("--wait") + 1])

    if target in ("auto", "both"):
        targets = ["exe", "src"] if EXE.is_file() else ["src"]
        if not EXE.is_file():
            print(f"提示: {EXE} 不存在（未打包/还没构建），本机只跑源码态冒烟")
    else:
        targets = [target]

    failed = False
    for tgt in targets:
        if tgt == "exe" and not EXE.is_file():
            print(f"SKIP: {EXE} 不存在（跳过打包冒烟）")
            continue
        print(f"\n########## 冒烟目标：{tgt} ##########")
        errors, warnings = _smoke(tgt, wait)
        for w in warnings:
            print(" ~ [WARN]", w)
        if errors:
            print(f"=== [{tgt}] 冒烟失败 ===")
            for e in errors:
                print(" -", e)
            failed = True
        else:
            note = "（截图项因环境受限跳过）" if warnings else "（截图已落盘）"
            print(f"=== [{tgt}] 冒烟通过：窗口正常出现、尺寸正常 {note} ===")

    print("\n" + "=" * 60)
    if failed:
        print("冒烟结果：失败（详见上方清单）")
        return 1
    print("冒烟结果：通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
