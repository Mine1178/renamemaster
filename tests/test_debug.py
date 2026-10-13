"""调试 document 模式二 map_box 内各控件高度。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)
app.show("document")
root.update_idletasks()
root.update()

page = app.pages["document"]

radios = []

def find_radio(w):
    if isinstance(w, tk.Radiobutton):
        radios.append(w)
    for c in w.winfo_children():
        find_radio(c)

find_radio(page)
for r in radios:
    if "模式二" in r.cget("text") or "对照" in r.cget("text"):
        r.invoke()

for _ in range(8):
    root.update_idletasks()
    root.update()

# 定位 map_box（包含 SelectableText 且文字为"第1列"的 frame）
def find_mapbox(w):
    if isinstance(w, tk.Frame):
        for c in w.winfo_children():
            if isinstance(c, SelectableText) and "第1列" in c.get("1.0", "end-1c"):
                return w
    for c in w.winfo_children():
        r = find_mapbox(c)
        if r:
            return r
    return None

mb = find_mapbox(page)
print("map_box 实际尺寸:", mb.winfo_width(), "x", mb.winfo_height())
print("map_box 请求高度:", mb.winfo_reqheight())
print("map_box 内子控件 pack 顺序：")
for c in mb.winfo_children():
    cls = type(c).__name__
    print(f"  {cls:12s} 实际 {c.winfo_width()}x{c.winfo_height()}  请求高 {c.winfo_reqheight()}")

root.destroy()
