"""RenameMaster 应用入口：建 Tk root 并启动 App。

运行：cd src && python -m rename_master.main
"""
from __future__ import annotations

import sys
from pathlib import Path

# 入口自举：支持从任意目录直接运行（python main.py）——把 src 根加入模块搜索路径
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import logging
import tkinter as tk

from rename_master.ui.app import App

logger = logging.getLogger("rename_master.main")


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


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _enable_high_dpi()
    root = tk.Tk()
    _apply_app_icon(root)
    try:
        App(root)
    except Exception:
        logger.exception("App 初始化失败")
        raise
    root.mainloop()


def _apply_app_icon(root: tk.Tk) -> None:
    """设置窗口图标（资源缺失时静默跳过）。"""
    try:
        import os
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "rename_master.ico")
        if os.path.isfile(ico):
            root.iconbitmap(ico)
    except Exception:                        # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
