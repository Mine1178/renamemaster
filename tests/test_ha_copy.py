# -*- coding: utf-8 -*-
"""验证首页 / 关于页文字可选中复制。"""
import sys
import time
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)


def settle():
    for _ in range(14):
        root.update_idletasks()
        root.update()
    deadline = time.time() + 0.15
    while time.time() < deadline:
        root.update()
        time.sleep(0.01)


def collect(page):
    out = []

    def fr(w):
        if isinstance(w, SelectableText):
            txt = w.get("1.0", "end-1c")
            if w.winfo_ismapped() and txt.strip() and w.winfo_width() > 30:
                out.append((w, txt))
        for c in w.winfo_children():
            fr(c)

    fr(page)
    return out


def mouse_select(w):
    w.focus_set()
    root.update()
    endx = max(20, w.winfo_width() - 4)
    y = min(10, max(4, w.winfo_height() - 4))
    w.event_generate("<Button-1>", x=1, y=y)
    root.update()
    w.event_generate("<B1-Motion>", x=endx, y=y)
    root.update()
    w.event_generate("<ButtonRelease-1>", x=endx, y=y)
    root.update()
    try:
        return w.get("sel.first", "sel.last")
    except tk.TclError:
        return ""


total = 0
copied = 0
for key in ["home", "about"]:
    app.show(key)
    settle()
    samples = collect(app.pages[key])
    print(f"=== {key}: {len(samples)} 个可选中文字")
    for w, txt in samples:
        total += 1
        sel = mouse_select(w)
        if sel:
            w.event_generate("<<Copy>>")
            root.update()
            core = root.clipboard_get().strip()
            if core and (core in txt or txt in core):
                copied += 1
            else:
                print(f"  !! 复制不符: {core[:20]!r} vs {txt[:20]!r}")
        else:
            print(f"  !! 未选中: {txt[:20]!r}")

root.destroy()
print(f"首页/关于页复制：{copied}/{total} 成功")
sys.exit(0 if copied == total else 1)
