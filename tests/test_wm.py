# -*- coding: utf-8 -*-
"""展开水印卡片后验证 r2/r4 布局。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)
app.show("photo")
for _ in range(3):
    root.update_idletasks()
    root.update()

page = app.pages["photo"]

# 找到水印卡片并展开
card_wm = None

def find_card(w):
    global card_wm
    if type(w).__name__ == "Card" and w.cget("bg") is not None:
        try:
            t = w._title.cget("text")
            if "水印" in t:
                card_wm = w
        except Exception:
            pass
    for c in w.winfo_children():
        find_card(c)

find_card(page)
print("水印卡片折叠状态:", card_wm.collapsed)
card_wm.set_collapsed(False)
for _ in range(5):
    root.update_idletasks()
    root.update()


def find_parent(text):
    result = []

    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, SelectableText) and text in c.get("1.0", "end-1c"):
                result.append(w)
            walk(c)

    walk(page)
    return result[0] if result else None


for label, key in [("r2", "回车换行可写多行"), ("r4", "未选择 LOGO")]:
    r = find_parent(key)
    print(f"--- {label} 展开后 {r.winfo_width()}x{r.winfo_height()}")
    for c in r.winfo_children():
        print(f"    {type(c).__name__:14s} 实际 {c.winfo_width()}x{c.winfo_height()}")

root.destroy()
