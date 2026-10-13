"""对比 photo 与 document 模式二 map_box 空间分配。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)


def debug(key):
    app.show(key)
    root.update_idletasks()
    root.update()
    page = app.pages[key]
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
    for _ in range(8):
        root.update_idletasks()
        root.update()

    def fmb(w):
        if isinstance(w, tk.Frame):
            for c in w.winfo_children():
                if isinstance(c, SelectableText) and "第1列" in c.get("1.0", "end-1c"):
                    return w
        for c in w.winfo_children():
            r = fmb(c)
            if r:
                return r
        return None

    mb = fmb(page)
    print(f"===== {key} =====")
    print(f"map_box 实际 {mb.winfo_height()} 请求 {mb.winfo_reqheight()}")
    for c in mb.winfo_children():
        print(f"  {type(c).__name__:14s} 实际高 {c.winfo_height():4d}  请求高 {c.winfo_reqheight():4d}")


debug("photo")
debug("document")
root.destroy()
