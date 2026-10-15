"""最终冒烟：无头构建所有页面 + 多次切页 + 操作栏复用，确认无 TclError。"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

# 让脚本在项目根直接跑
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import os
os.environ.setdefault("DISPLAY", "")  # Windows 下 Tk 不需要

import tkinter as tk
from rename_master.ui.app import App, NAV_ITEMS


def main() -> int:
    errors: list[str] = []
    try:
        root = tk.Tk()
        root.withdraw()  # 不弹窗
        app = App(root)
    except Exception:
        traceback.print_exc()
        print("FAIL: App 初始化崩溃")
        return 1

    # 依次构建并切到每个页面 2 次（重点验证切回时操作栏不崩）
    for round_no in (1, 2):
        for key, _icon, _label in NAV_ITEMS:
            try:
                app.show(key)
                root.update_idletasks()
                root.update()
            except Exception as exc:
                errors.append(f"round{round_no} show({key}): {exc}")
                traceback.print_exc()

    # 验证操作栏都还活着（没被 destroy）
    bars = getattr(app, "_action_bars", {}) or {}
    dead = []
    for k, bar in bars.items():
        try:
            bar.winfo_exists()
        except tk.TclError:
            dead.append(k)
    if dead:
        errors.append(f"操作栏已销毁: {dead}")

    # 验证水印页状态变量存在
    try:
        app.show("watermark")
        root.update_idletasks()
        wm_page = app.pages["watermark"]
        st = getattr(wm_page, "st", None)
        if st is None:
            errors.append("水印页 st 未挂载")
        else:
            print("水印页 st keys:", sorted(st.keys())[:5], "...")
    except Exception as exc:
        errors.append(f"水印页检查: {exc}")
        traceback.print_exc()

    root.destroy()

    if errors:
        print("\n=== 冒烟发现问题 ===")
        for e in errors:
            print(" -", e)
        return 1
    print("\nSMOKE OK: 全部页面两轮切换无异常，操作栏存活")
    return 0


if __name__ == "__main__":
    sys.exit(main())
