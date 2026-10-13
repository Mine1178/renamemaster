"""测试所有页面是否能正常构建。"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rename_master.ui.app import App
from rename_master.config.manager import ConfigManager

root = tk.Tk()
root.withdraw()  # 不显示主窗口

cfg = ConfigManager()
app = App(root, cfg)

pages_to_test = ["photo", "spreadsheet", "document", "pdf"]

for page_key in pages_to_test:
    print(f"\n=== 测试 {page_key} 页面 ===")
    try:
        app.show(page_key)
        root.update_idletasks()
        root.update()
        print(f"✓ {page_key} 页面构建成功")

        # 测试切换模式
        page = app.pages.get(page_key)
        if page:
            # 找到模式变量并切换
            # 直接检查页面上有多少控件
            children = page.winfo_children()
            print(f"  顶层子控件数: {len(children)}")

    except Exception as e:
        print(f"✗ {page_key} 页面构建失败: {e}")
        import traceback
        traceback.print_exc()

root.destroy()
print("\n=== 测试完成 ===")
