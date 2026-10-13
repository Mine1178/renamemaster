"""模拟鼠标拖选，验证 SelectableText 是否真的能选中。"""
import sys
import tkinter as tk

sys.path.insert(0, "src")
from rename_master.ui.widgets import SelectableText

root = tk.Tk()
root.geometry("600x200")

t = SelectableText(root, "第1列原文件名，第2列新文件名，未匹配保持原名")
t.pack(fill=tk.X, padx=10, pady=10)
root.update()
root.update_idletasks()

print("控件类型:", type(t).__name__)
print("takefocus:", t.cget("takefocus"))
print("cursor:", t.cget("cursor"))

# 模拟鼠标点击在文字开头
t.event_generate("<ButtonPress-1>", x=5, y=5)
root.update()
print("点击后插入点:", repr(t.index("insert")))

# 模拟鼠标拖动到文字末尾
t.event_generate("<B1-Motion>", x=300, y=5)
root.update()
t.event_generate("<ButtonRelease-1>", x=300, y=5)
root.update()

# 检查选中范围
sel = t.tag_ranges("sel")
print("选中范围:", sel)
if sel:
    print("选中文字:", repr(t.get(sel[0], sel[1])))
else:
    print("!! 没有选中任何内容")

root.destroy()
