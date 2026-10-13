# -*- coding: utf-8 -*-
"""最终扫描：发现异常时强制二次同步再确认，只对最终仍异常的报失败。"""
import sys
import time
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)


def settle():
    for _ in range(12):
        root.update_idletasks()
        root.update()
    deadline = time.time() + 0.15
    while time.time() < deadline:
        root.update()
        time.sleep(0.01)


def measure(page):
    good = 0
    bad = []

    def walk(w):
        nonlocal good
        if isinstance(w, SelectableText):
            ww, wh = w.winfo_width(), w.winfo_height()
            txt = w.get("1.0", "end-1c")
            if w.winfo_ismapped() and txt.strip():
                if ww > 5 and wh > 10:
                    good += 1
                else:
                    bad.append((txt[:25], ww, wh))
        for c in w.winfo_children():
            walk(c)

    walk(page)
    return good, bad


def scan(page, label):
    settle()
    g, bad = measure(page)
    if bad:
        app.request_relayout()
        settle()
        g, bad = measure(page)
    if bad:
        print(f"--- {label}: 正常 {g}，异常 {len(bad)}：")
        for t, ww, wh in bad:
            print(f"      !! {ww}x{wh}  {t!r}")
        return False
    print(f"--- {label}: 正常 {g} 个")
    return True


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


allok = True
for key in ["photo", "pdf", "spreadsheet", "document"]:
    app.show(key)
    settle()
    page = app.pages[key]
    allok &= scan(page, f"{key} 模式一")
    switch_mode(page, "模式二")
    allok &= scan(page, f"{key} 模式二")
    switch_mode(page, "模式一")

root.destroy()
print("结果:", "全部正常" if allok else "存在异常")
sys.exit(0 if allok else 1)
