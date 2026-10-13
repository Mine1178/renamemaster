"""切换到每个页面的模式二，测量 SelectableText 尺寸并验证选中。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.app import App
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
app = App(root)


def measure(page_key):
    app.show(page_key)
    root.update()
    root.update_idletasks()
    page = app.pages[page_key]

    # 找到所有 Radiobutton，invoke 文本含"模式二"的那个
    radios = []

    def find_radio(w):
        if isinstance(w, tk.Radiobutton):
            radios.append(w)
        for c in w.winfo_children():
            find_radio(c)

    find_radio(page)
    for r in radios:
        txt = r.cget("text")
        if "模式二" in txt or "对照" in txt:
            r.invoke()
    root.update()
    root.update_idletasks()
    root.update()

    # 再扫描可见的 SelectableText
    out = []

    def scan(w):
        if isinstance(w, SelectableText):
            t = w.get("1.0", "end-1c")
            ww, wh = w.winfo_width(), w.winfo_height()
            w.tag_add("sel", "1.0", "end-1c")
            root.update_idletasks()
            ok = bool(w.tag_ranges("sel"))
            w.tag_remove("sel", "1.0", "end")
            out.append((t[:30], ww, wh, ok))
        for c in w.winfo_children():
            scan(c)

    scan(page)
    return out


for key in ["photo", "pdf", "spreadsheet", "document"]:
    print(f"===== {key} 模式二 =====")
    for t, ww, wh, ok in measure(key):
        flag = "OK " if ww > 10 and wh > 5 else "!! 1x1"
        print(f"  [{flag}] {ww}x{wh} 可选中={ok}  {t!r}")

root.destroy()
