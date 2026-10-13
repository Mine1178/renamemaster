"""检查各页面控件的实际布局尺寸，找出换行/截断问题。"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rename_master.ui.app import App
from rename_master.config.manager import ConfigManager

root = tk.Tk()
root.withdraw()

cfg = ConfigManager()
app = App(root, cfg)

def measure_widget(w, indent=0):
    """递归测量控件的需求尺寸。"""
    try:
        w.update_idletasks()
        rw = w.winfo_reqwidth()
        rh = w.winfo_reqheight()
        cls = w.winfo_class()
        name = w.winfo_name()
        text = ""
        if cls in ("Label", "Button", "Checkbutton", "Radiobutton"):
            try:
                text = w.cget("text")[:20]
            except:
                pass
        print(" " * indent + f"{cls} ({name}) req={rw}x{rh} {text}")
    except tk.TclError:
        return
    for child in w.winfo_children():
        measure_widget(child, indent + 2)

for page_key in ["photo", "spreadsheet", "document", "pdf"]:
    print(f"\n{'='*60}")
    print(f"页面: {page_key}")
    print('='*60)
    app.show(page_key)
    root.update_idletasks()
    root.update()

    page = app.pages[page_key]
    # 只测量卡片2（命名规则）
    # 遍历找到所有Card
    def find_cards(w):
        cards = []
        if w.winfo_class() == "Frame":
            # 检查是否有Card样式（通过子控件判断）
            pass
        for child in w.winfo_children():
            cards.extend(find_cards(child))
        return cards

    # 简单打印整个页面
    measure_widget(page)

root.destroy()
