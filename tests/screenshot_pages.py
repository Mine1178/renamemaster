"""截图脚本：渲染每个页面并保存截图，用于检查布局问题。"""
import sys
import tkinter as tk
from pathlib import Path

# 加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rename_master.ui.pages import photo, document, spreadsheet, pdf

# 模拟 app 对象
class MockApp:
    def __init__(self, root):
        self.root = root
        self.content = root
        self.pages = {}
        self.cfg = MockConfig()
        self.action_host = tk.Frame(root)

    def set_status(self, msg, kind=None):
        pass

    def safe_after(self, ms, func):
        func()

    def set_action_bar(self, bar):
        pass

class MockConfig:
    def __init__(self):
        self.data = {}
    def get(self, key, default=None):
        return self.data.get(key, default)
    def set(self, key, value):
        self.data[key] = value
    def save(self):
        pass

# 截图目录
out_dir = Path(__file__).parent / "screenshots"
out_dir.mkdir(exist_ok=True)

pages = {
    "photo": photo,
    "document": document,
    "spreadsheet": spreadsheet,
    "pdf": pdf,
}

for name, page_mod in pages.items():
    root = tk.Tk()
    root.title(name)
    root.geometry("1200x900")
    root.configure(bg="#f5f6fa")

    mock_app = MockApp(root)
    page_frame = tk.Frame(root, bg="#f5f6fa")
    page_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    mock_app.pages[name] = page_frame

    page_mod.build(page_frame, mock_app)

    # 强制更新并等待渲染
    root.update_idletasks()
    root.update()

    # 等待1秒让界面完全渲染
    root.after(1000)

    def take_screenshot():
        root.update_idletasks()
        root.update()
        root.lift()
        root.attributes('-topmost', True)
        root.update()
        root.attributes('-topmost', False)

        from PIL import ImageGrab
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()
        print(f"窗口位置: ({x}, {y}), 大小: ({w}, {h})")

        # 扩展一点边框
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        img.save(str(out_dir / f"{name}_模式一.png"))
        print(f"{name} 模式一截图已保存")

    root.after(1500, take_screenshot)

    # 运行主循环一段时间
    root.after(3000, root.destroy)
    root.mainloop()

print("完成")
