# -*- coding: utf-8 -*-
"""水印独立页端到端回归（v1.2）。

必须用主线程 root.mainloop() 驱动：worker 线程经 safe_after 投递的 _finish
（内含 showinfo）只有在 mainloop 中才能被跨线程注册（手动 update 循环会抛
"main thread is not in main loop"）。mainloop 下用 after 轮询完成事件。

覆盖：
  ① 可见斜向平铺 → 3 JPG，尺寸正确
  ② 仅盲水印     → 3 PNG，提取正确
  ③ 双保险       → 3 JPG，Q95 后仍可提取盲水印
  ④ UI 提取弹窗  → 从双保险 JPG 提取，结果窗列出
"""
import os
import sys
import shutil
import tempfile
import threading
import tkinter as tk

sys.path.insert(0, "src")

from PIL import Image, ImageDraw

from rename_master.ui.app import App
from rename_master.ui.pages import watermark as wm_mod
from rename_master.core import blind_wm

# ---------- 测试图片 ----------
WORK = os.path.join(tempfile.gettempdir(), "rm_wm_regress")
SRC = os.path.join(WORK, "src")
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(SRC, exist_ok=True)


def make_img(path, base):
    img = Image.new("RGB", (900, 650))
    d = ImageDraw.Draw(img)
    for y in range(650):
        d.line([(0, y), (900, y)],
               fill=((base[0] + y // 4) % 256, (base[1] + y // 6) % 256,
                     (base[2] + y // 3) % 256))
    for x in range(0, 900, 60):
        d.rectangle([x, 120, x + 40, 300], fill=(255 - base[0], 200, 120))
    img.save(path)


for i, base in enumerate([(40, 90, 200), (200, 60, 90), (60, 170, 120)]):
    make_img(os.path.join(SRC, f"IMG_{i+1}.jpg"), base)

OUT = [os.path.join(WORK, f"out_{n}") for n in ("visible", "blind", "double")]

# ---------- App ----------
root = tk.Tk()
app = App(root)
app.show("watermark")
for _ in range(12):
    root.update_idletasks()
    root.update()
page = app.pages["watermark"]
st = page.st

# patch 弹窗
finished = threading.Event()
wm_mod.messagebox.showinfo = lambda *a, **k: (finished.set(), "ok")[1]
wm_mod.messagebox.showwarning = lambda *a, **k: (print("[WARNING]", a), "ok")[1]
wm_mod.messagebox.showerror = lambda *a, **k: (print("[ERROR]", a), "ok")[1]

# 提取窗 spy
extract_win = {"w": None}
_orig_toplevel = tk.Toplevel


def _spy(*a, **k):
    w = _orig_toplevel(*a, **k)
    extract_win["w"] = w
    return w


page.set_source_dir(SRC)
for _ in range(6):
    root.update()

results = {"pass": 0, "fail": 0}


def check(name, cond, extra=""):
    results["pass" if cond else "fail"] += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  {extra}"))


def find_btn(w):
    for c in w.winfo_children():
        if type(c).__name__ == "Button" and "开始处理" in str(c.cget("text")):
            return c
        r = find_btn(c)
        if r:
            return r
    return None


def click_run():
    finished.clear()
    find_btn(app._action_bars["watermark"]).invoke()


def configure(i):
    if i == 0:
        st["vis_on"].set(True)
        st["blind_on"].set(False)
        st["vis_layout"].set("tile")
        st["vis_text"].set("曲靖联通 陈琼")
        st["out_dir"].set(OUT[0])
    elif i == 1:
        st["vis_on"].set(False)
        st["blind_on"].set(True)
        st["blind_action"].set("embed")
        st["blind_text"].set("曲靖联通陈琼20261013")
        st["out_dir"].set(OUT[1])
    elif i == 2:
        st["vis_on"].set(True)
        st["blind_on"].set(True)
        st["blind_action"].set("embed")
        st["vis_layout"].set("tile")
        st["vis_text"].set("曲靖联通 陈琼")
        st["blind_text"].set("曲靖联通陈琼20261013")
        st["out_dir"].set(OUT[2])
    elif i == 3:
        st["files"].clear()                       # 切源前先清空，避免追加成 6 个
        st["blind_on"].set(True)
        st["blind_action"].set("extract")
        page.set_source_dir(OUT[2])


def verify(i):
    print(f"=== 验证场景{['①','②','③','④'][i]} ===")
    if i == 0:
        fs = sorted(os.listdir(OUT[0])) if os.path.isdir(OUT[0]) else []
        check("输出 3 JPG", len(fs) == 3 and all(f.endswith(".jpg") for f in fs), str(fs))
        if fs:
            check("尺寸 900x650",
                  Image.open(os.path.join(OUT[0], fs[0])).size == (900, 650))
    elif i == 1:
        fs = sorted(os.listdir(OUT[1])) if os.path.isdir(OUT[1]) else []
        check("输出 3 PNG", len(fs) == 3 and all(f.endswith(".png") for f in fs), str(fs))
        if fs:
            txt = blind_wm.extract_watermark(os.path.join(OUT[1], fs[0]), 208)
            check("PNG 提取正确", "曲靖联通陈琼20261013" in txt, repr(txt))
    elif i == 2:
        fs = sorted(os.listdir(OUT[2])) if os.path.isdir(OUT[2]) else []
        check("双保险输出 3 JPG", len(fs) == 3 and all(f.endswith(".jpg") for f in fs),
              str(fs))
        if fs:
            txt = blind_wm.extract_watermark(os.path.join(OUT[2], fs[0]), 208)
            check("Q95 仍可提取盲水印", "曲靖联通陈琼20261013" in txt, repr(txt))
    elif i == 3:
        w = extract_win["w"]
        check("提取窗已弹出", w is not None and w.winfo_exists())
        if w is not None and w.winfo_exists():
            vals = []

            def walk(x):
                for c in x.winfo_children():
                    if type(c).__name__ == "Treeview":
                        for iid in c.get_children():
                            vals.append(c.item(iid, "values"))
                    walk(c)

            walk(w)
            check("结果窗 3 行", len(vals) == 3, str(len(vals)))
            check("弹窗提取文字正确",
                  any("曲靖联通陈琼20261013" in str(v) for v in vals), str(vals))


cur = [0]
N = 4


def start_cur():
    i = cur[0]
    print(f"=== 配置场景{['①','②','③','④'][i]} ===")
    configure(i)
    if i == 3:
        tk.Toplevel = _spy
        extract_win["w"] = None
        click_run()
        root.after(100, poll_extract)
    else:
        click_run()
        root.after(100, poll_normal)


def poll_normal():
    if finished.is_set():
        verify(cur[0])
        cur[0] += 1
        if cur[0] < N:
            root.after(60, start_cur)
        else:
            root.after(60, finish_all)
    else:
        root.after(80, poll_normal)


def poll_extract():
    w = extract_win["w"]
    if w is not None and w.winfo_exists():
        for _ in range(8):
            root.update()
        verify(cur[0])
        root.after(60, finish_all)
    else:
        root.after(80, poll_extract)


def finish_all():
    tk.Toplevel = _orig_toplevel
    root.destroy()


root.after(150, start_cur)
root.after(120000, finish_all)   # 兜底超时
root.mainloop()

print(f"\n=== 结果：{results['pass']} 通过，{results['fail']} 失败 ===")
sys.exit(0 if results["fail"] == 0 else 1)
