"""临时校验脚本：构建全部页面 + 验证切页时操作栏互斥（用完即删）。"""
import sys
from pathlib import Path

import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from rename_master.ui.app import App  # noqa: E402

root = tk.Tk()
app = App(root)


def probe(tag: str) -> None:
    root.update()
    bars = getattr(app, "_action_bars", {})
    vis = {k: bool(b.winfo_ismapped()) for k, b in bars.items()}
    print(f"{tag}: action_host={app.action_host.winfo_ismapped()} bars={vis}")


for key in ("home", "photo", "spreadsheet", "document", "about"):
    app.show(key)
    probe("build  " + key)
for key in ("photo", "home", "photo", "about", "spreadsheet", "photo"):
    app.show(key)
    probe("revisit " + key)

root.destroy()
print("GUI BUILD OK")
