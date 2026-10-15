"""RenameMaster 应用入口：建 Tk root 并启动 App。

运行：cd src && python -m rename_master.main

v1.9 起入口自带兜底：
- 依赖缺失 / 初始化异常不再静默闪退，而是弹中文错误框 + 写崩溃日志；
- 控制台（开发态）与文件（`%APPDATA%\\RenameMaster\\logs\\run_YYYYMMDD.log`）双写日志，
  EXE 是 noconsole 打包，没有文件日志的话问题完全无法追溯；
- tkinterdnd2 缺失时降级为普通窗口（拖放不可用），不影响其它功能。
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# 入口自举：支持从任意目录直接运行（python main.py）——把 src 根加入模块搜索路径
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import tkinter as tk

logger = logging.getLogger("rename_master.main")

APP_DIR_NAME = "RenameMaster"

# 日志本身出错绝不能拖垮 GUI：logging 默认在 handleError 里重新抛出 I/O 异常，
# 只要日志目录不可写，第一条日志就会把整个程序带崩（实测：只读配置下 EXE 弹
# "Unhandled exception in script" 后闪退）。这里降级为“记不下来就算了”。
logging.raiseExceptions = False


def app_data_dir() -> Path:
    """用户数据目录：优先 %APPDATA%\\RenameMaster（与 config 同源）。"""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home()
    return root / APP_DIR_NAME


def _setup_logging() -> None:
    """控制台 + 文件双写日志；任何一步失败都不能影响启动。

    要点：FileHandler 必须**立即打开**（不能用 delay=True）。延迟打开会把
    “日志目录不可写”这个错误推迟到第一条日志调用，那时已经在 logging 内部，
    异常会越过 try 直接冒到顶层。
    """
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:                     # 仅首次配置，避免重复 handler
        if sys.stderr is not None:            # noconsole EXE 下 stderr 可能是 None
            sh = logging.StreamHandler()
            sh.setFormatter(logging.Formatter(fmt))
            root.addHandler(sh)
    try:
        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(
            log_dir / f"run_{datetime.now():%Y%m%d}.log",
            encoding="utf-8", delay=False)
        fh.setFormatter(logging.Formatter(fmt))
        root.addHandler(fh)
    except OSError as exc:                     # 只读盘 / 无权限：退回控制台日志
        logger.warning("无法创建文件日志：%s", exc)


def _write_crash_log(text: str) -> Path | None:
    """把崩溃栈写到文件，返回路径（失败返回 None）。"""
    try:
        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"crash_{datetime.now():%Y%m%d_%H%M%S}.log"
        path.write_text(text, encoding="utf-8")
        return path
    except OSError:
        return None


def _show_fatal(title: str, message: str) -> None:
    """尽力弹一个用户看得懂的中文错误框；全失败则退到控制台输出。"""
    try:
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(title, message)
        r.destroy()
        return
    except Exception:                         # noqa: BLE001 Tk 建不起来时继续兜底
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:                         # noqa: BLE001 非 Windows：忽略
        pass
    if sys.stderr is not None:
        print(f"{title}: {message}", file=sys.stderr)


def _enable_high_dpi() -> None:
    """进程级 DPI 感知（任务书 §4.1）：高分屏文字不再模糊。"""
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:                        # noqa: BLE001 旧系统回退 user32
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:                        # noqa: BLE001 非 Windows：静默跳过
        pass


def _load_dnd():
    """延迟导入拖放支持：tkinterdnd2 缺失 / 损坏时降级为普通窗口。"""
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        return DND_FILES, TkinterDnD
    except Exception as exc:                  # noqa: BLE001
        logger.warning("拖放支持不可用（tkinterdnd2 导入失败）：%s", exc)
        return None, None


def main() -> int:
    _setup_logging()
    logger.info("RenameMaster 启动")

    try:
        from rename_master.ui.app import VERSION
    except Exception:                         # noqa: BLE001 版本仅为日志，失败不影响启动
        VERSION = "?"
    logger.info("版本 %s，Python %s", VERSION, sys.version.split()[0])

    _enable_high_dpi()

    dnd_files, tkinterdnd = _load_dnd()
    try:
        # TkinterDnD.Tk 是 tk.Tk 的子类：换成它整个窗口（含子孙）才支持接收拖入
        root = tkinterdnd.Tk() if tkinterdnd is not None else tk.Tk()
    except Exception as exc:                  # noqa: BLE001 Tk 都建不起来：直接给用户看原因
        _report_fatal("图形界面初始化失败（Tk 不可用）", exc)
        return 1

    _apply_app_icon(root)
    try:
        from rename_master.ui.app import App
        from rename_master.ui.dnd import make_drop_handler

        app = App(root)
        if dnd_files is not None:
            root.drop_target_register(dnd_files)
            root.dnd_bind("<<Drop>>", make_drop_handler(app))
        else:
            app.set_status("拖放功能不可用（缺 tkinterdnd2），可用「添加文件」按钮", "warn")
    except Exception as exc:                  # noqa: BLE001 初始化失败：中文提示 + 崩溃日志
        _report_fatal("软件初始化失败", exc)
        try:
            root.destroy()
        except Exception:                     # noqa: BLE001
            pass
        return 1

    try:
        root.mainloop()
    except Exception as exc:                  # noqa: BLE001 主循环内未捕获异常
        _report_fatal("程序运行中发生异常", exc)
        return 1
    logger.info("RenameMaster 正常退出")
    return 0


def _report_fatal(title: str, exc: BaseException) -> None:
    """统一兜底：写崩溃日志 + 弹中文提示，带上日志路径方便用户反馈。"""
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("%s：%s", title, exc, exc_info=True)
    path = _write_crash_log(f"{title}\n\n{detail}")
    hint = f"\n\n详细堆栈已写入：\n{path}" if path else ""
    _show_fatal(
        f"RenameMaster - {title}",
        f"{title}：{exc}\n\n"
        f"请把上面这行信息（或下面的日志文件）反馈给开发者。{hint}",
    )


def _apply_app_icon(root: tk.Tk) -> None:
    """设置窗口图标（资源缺失时静默跳过）。"""
    try:
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "rename_master.ico")
        if os.path.isfile(ico):
            root.iconbitmap(ico)
    except Exception:                        # noqa: BLE001
        pass


if __name__ == "__main__":
    sys.exit(main())
