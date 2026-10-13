"""UI 集成验证：4 个功能页的高级选项卡片、撤销按钮、变量交互。"""
import os
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rename_master.config.manager import ConfigManager  # noqa: E402
from rename_master.core import renamer                 # noqa: E402
from rename_master.ui import advanced                 # noqa: E402
from rename_master.ui.app import App                  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def walk_widgets(root):
    out = []
    def walk(w):
        for c in w.winfo_children():
            out.append(c)
            walk(c)
    walk(root)
    return out


def button_texts(root):
    return [str(b.cget("text")) for b in walk_widgets(root)
            if isinstance(b, tk.Button)]


root = tk.Tk()
root.withdraw()
app = App(root, ConfigManager())

# 真实临时文件
tmp = tempfile.mkdtemp(prefix="rm_ui_")
files = []
for i, nm in enumerate(["alpha.jpg", "beta.jpg", "gamma.jpg"]):
    p = Path(tmp) / nm
    p.write_bytes(b"x" * (100 + i * 30))
    ts = time.time() - (3 - i) * 1000
    os.utime(p, (ts, ts))
    files.append(p)

for key in ["photo", "pdf", "spreadsheet", "document"]:
    print(f"\n=== {key} ===")
    app.show(key)
    root.update_idletasks()
    root.update()
    page = app.pages[key]

    # adv 挂载
    adv = getattr(page, "adv", None)
    check("高级选项变量已挂载", adv is not None)
    if adv:
        for k in ("sort_by", "sort_desc", "find", "repl", "use_regex"):
            check(f"变量 {k} 存在", k in adv)

    # 排序 Combobox
    combos = [w for w in walk_widgets(page) if isinstance(w, ttk.Combobox)]
    check("排序下拉存在", len(combos) >= 1, len(combos))

    # 撤销按钮（在 action bar 里，master 是 app.content，不在 page 子树）
    bar = app._action_bars.get(key)
    btexts = button_texts(bar) if bar is not None else []
    check("撤销按钮存在", any("撤销" in t for t in btexts), btexts)

    # 交互：改 adv → 生成 rule → plan 反映
    if adv:
        adv["sort_by"].set("name")
        adv["sort_desc"].set(True)
        adv["find"].set("a")
        adv["repl"].set("X")
        adv["use_regex"].set(False)
        rule = {"base_name": "P", "digits": 3, "start": 1, "sep": "_",
                "keep_ext": True}
        advanced.apply_to_rule(rule, adv)
        check("rule 含排序", rule["sort_by"] == "name" and rule["sort_desc"])
        check("rule 含查找替换", rule["find"] == "a" and rule["repl"] == "X")
        plans = renamer.plan_rename(files, renamer.MODE_PREFIX, rule)
        check("降序首文件为 gamma", plans[0].src.name == "gamma.jpg",
              [p.src.name for p in plans])

# 撤销方法存在
check("App 提供 undo_last_batch", hasattr(app, "undo_last_batch"))

root.destroy()
print()
print(f"=== 结果：{PASS} 通过，{FAIL} 失败 ===")
sys.exit(1 if FAIL else 0)
