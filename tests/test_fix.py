"""验证：切换模式二后调用 _sync_canvas，SelectableText 是否恢复。"""
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

def fr(w):
    if isinstance(w, tk.Radiobutton):
        radios.append(w)
    for c in w.winfo_children():
        fr(c)

fr(page)
for r in radios:
    if "模式二" in r.cget("text") or "对照" in r.cget("text"):
        r.invoke()

for _ in range(5):
    root.update_idletasks()
    root.update()

def hint_h(w):
    if isinstance(w, SelectableText) and "第1列" in w.get("1.0", "end-1c"):
        return w
    for c in w.winfo_children():
        r = hint_h(c)
        if r:
            return r
    return None

h = hint_h(page)
print("调用 _sync_canvas 前高度:", h.winfo_height())

# 手动同步
app._sync_canvas()
root.update_idletasks()
root.update()
print("第一次 _sync_canvas 后高度:", h.winfo_height())

app._sync_canvas()
root.update_idletasks()
root.update()
print("第二次 _sync_canvas 后高度:", h.winfo_height())

root.destroy()
