"""构建完整App，切换所有页面，统计 SelectableText 并验证可交互性。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)

# 切换到每个页面，触发延迟构建
for key in ["home", "photo", "pdf", "spreadsheet", "document", "about"]:
    app.show(key)
    root.update()
    root.update_idletasks()

found = []

def scan(widget):
    if isinstance(widget, SelectableText):
        txt = widget.get("1.0", "end-1c")
        widget.tag_add("sel", "1.0", "end-1c")
        root.update_idletasks()
        sel = widget.tag_ranges("sel")
        ok = bool(sel)
        widget.tag_remove("sel", "1.0", "end")
        found.append((txt, ok, widget.winfo_width(), widget.winfo_height()))
    for child in widget.winfo_children():
        scan(child)

scan(root)

print(f"共找到 {len(found)} 个 SelectableText：")
for i, (txt, ok, w, h) in enumerate(found, 1):
    print(f"  {i}. [{w}x{h}] 可选中={ok}  内容={txt[:40]!r}")

root.destroy()
