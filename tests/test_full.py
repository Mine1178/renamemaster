# -*- coding: utf-8 -*-
"""全面扫描：每个页面在各模式下所有可见 SelectableText 的尺寸。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)


def settle(n=10):
    for _ in range(n):
        root.update_idletasks()
        root.update()


def scan(page, label):
    bad = []
    good = 0

    def walk(w):
        nonlocal good
        if isinstance(w, SelectableText):
            ww, wh = w.winfo_width(), w.winfo_height()
            txt = w.get("1.0", "end-1c")
            # 可见判定：宽 > 5 且高 > 10（有文字的控件）
            mapped = w.winfo_ismapped()
            if mapped and txt.strip():
                if ww > 5 and wh > 10:
                    good += 1
                else:
                    bad.append((txt[:25], ww, wh))
        for c in w.winfo_children():
            walk(c)

    settle()
    walk(page)
    print(f"--- {label}: 正常 {good} 个", end="")
    if bad:
        print(f"，异常 {len(bad)} 个：")
        for t, ww, wh in bad:
            print(f"      !! {ww}x{wh}  {t!r}")
    else:
        print("")


def switch_mode(page, mode_text):
    radios = []

    def fr(w):
        if isinstance(w, tk.Radiobutton):
            radios.append(w)
        for c in w.winfo_children():
            fr(c)

    fr(page)
    for r in radios:
        if mode_text in r.cget("text"):
            r.invoke()
    settle()


for key in ["photo", "pdf", "spreadsheet", "document"]:
    app.show(key)
    settle()
    page = app.pages[key]
    scan(page, f"{key} 模式一")
    switch_mode(page, "模式二")
    scan(page, f"{key} 模式二")
    switch_mode(page, "模式一")

root.destroy()
print("检查完成")

