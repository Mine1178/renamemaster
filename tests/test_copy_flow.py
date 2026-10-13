# -*- coding: utf-8 -*-
"""验证真实鼠标拖选 + Ctrl+C：对各页静态文字执行，核对剪贴板。"""
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
    deadline = time.time() + 0.1
    while time.time() < deadline:
        root.update()
        time.sleep(0.01)


def collect(page):
    out = []

    def fr(w):
        if isinstance(w, SelectableText):
            txt = w.get("1.0", "end-1c")
            if w.winfo_ismapped() and txt.strip() and w.winfo_width() > 40:
                out.append((w, txt))
        for c in w.winfo_children():
            fr(c)

    fr(page)
    return out


def mouse_select(w):
    """模拟鼠标在文字上按下→拖动到末尾，产生 sel。"""
    w.focus_set()
    root.update()
    endx = max(20, w.winfo_width() - 4)
    y = min(10, w.winfo_height() - 4)
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
for key in ["photo", "pdf", "spreadsheet", "document"]:
    app.show(key)
    settle()
    # 每页抽前 3 个可见文字控件验证
    samples = collect(app.pages[key])[:3]
    for w, txt in samples:
        total += 1
        sel = mouse_select(w)
        if sel:
            w.event_generate("<<Copy>>")
            root.update()
            clip = root.clipboard_get()
            core = clip.strip()
            if core and (core in txt or txt in core):
                copied += 1
                print(f"OK  {key}: {core[:28]!r}")
            else:
                print(f"!!  {key}: 剪贴板 {core[:20]!r} 不属于 {txt[:20]!r}")
        else:
            print(f"!!  {key}: 未选中 {txt[:20]!r}")

root.destroy()
print(f"复制验证：{copied}/{total} 成功")
sys.exit(0 if copied == total else 1)
