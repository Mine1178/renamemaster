"""测试 Treeview 复制功能。"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rename_master.ui.widgets import styled_tree, copy_to_clipboard, enable_label_copy

root = tk.Tk()
root.geometry("500x200")

cols = [("a", "文件名", 150, "w"), ("b", "新文件名",150, "w")]
tv = styled_tree(root, cols, height=4)
tv.pack(fill=tk.BOTH, expand=True)

tv.insert("", "end", iid="1", values=("照片_001.jpg", "场景_001.jpg"))
tv.insert("", "end", iid="2", values=("照片_002.jpg", "场景_002.jpg"))
tv.selection_set("1")

# 合成键事件需组件真实 mapped 且有焦点才会派发；
# 无人值守 / 远程桌面下顶层窗口未必自动获得键盘焦点，先显式争取一次。
root.focus_force()
root.update()
tv.focus_set()
root.update()
tv.event_generate("<Control-c>")
root.update()
clip = root.clipboard_get()
print("Ctrl+C 复制内容:")
print(repr(clip))
assert "照片_001.jpg" in clip, "复制失败"

# 测试 enable_label_copy
lbl = tk.Label(root, text="这是一段可复制的文字")
lbl.pack()
root.update()
enable_label_copy(lbl)
# 模拟右键
copy_to_clipboard(lbl, lbl.cget("text"))
root.update()
clip2 = root.clipboard_get()
print("Label 复制内容:", repr(clip2))
assert clip2 == "这是一段可复制的文字"

root.destroy()
print("\n复制功能测试通过")
