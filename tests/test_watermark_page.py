# -*- coding: utf-8 -*-
"""水印独立页端到端回归（v1.6 重构：多行 / 4 风格 / 预览按钮 / 暗黄默认）。

主线程 root.mainloop() + after 轮询驱动；worker 线程通过 safe_after 投递
_finish（包含 showinfo）回主线程，mainloop 中可正常 fire。

覆盖：
  ① 可见斜向平铺（暗黄 0.15 默认值）→ 3 JPG，尺寸正确
  ② 仅盲水印                       → 3 PNG，提取正确
  ③ 双保险（多行文字）              → 3 JPG，Q95 后仍可提取盲水印
  ④ UI 提取弹窗                    → 从双保险 JPG 提取，结果窗列出
  ⑤ v1.6 新增：4 风格 / 多行 / 预览按钮 / 默认暗黄 / 引擎端 4 风格 + 印章 + 密度
"""
import os
import sys
import shutil
import tempfile
import threading
import tkinter as tk

sys.path.insert(0, "src")

# ---------- 工作目录 + 环境隔离 ----------
# 必须在 import rename_master 之前改写 %APPDATA%：config.manager / core.history
# 都是在 import 期用 %APPDATA% 算出 config.json / history.json 路径的。
# 不改的话，用例会读到用户真实 config.json ——「默认颜色=暗黄」这类断言会被
# 用户保存过的配置污染（假失败），执行时又会把测试批次写进用户真实 history.json。
WORK = os.path.join(tempfile.gettempdir(), "rm_wm_regress_v16")
SRC = os.path.join(WORK, "src")
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(SRC, exist_ok=True)
os.environ["APPDATA"] = os.path.join(WORK, "appdata")
os.makedirs(os.environ["APPDATA"], exist_ok=True)

from PIL import Image, ImageDraw                                     # noqa: E402

from rename_master.ui.app import App                                 # noqa: E402
from rename_master.ui.pages import watermark as wm_mod               # noqa: E402
from rename_master.core import blind_wm, watermark as wm_core        # noqa: E402

# ---------- 测试图片 ----------

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


# 模块级常驻 spy：页面里所有 tk.Toplevel(...) 都记进 extract_win。
# 少了这一行，_spy 永不被调用，场景 ④ 的提取窗抓不到 →
# poll_extract 空转到硬超时（旧版正因此「超时也算过」造成假绿）。
tk.Toplevel = _spy


def _set_vis_text(t: str) -> None:
    page.vis_text_box.delete("1.0", "end")
    page.vis_text_box.insert("1.0", t)


def _vis_text() -> str:
    return page.vis_text_box.get("1.0", "end").strip()


page.set_source_dir(SRC)
for _ in range(6):
    root.update()

results = {"pass": 0, "fail": 0}


def check(name, cond, extra=""):
    results["pass" if cond else "fail"] += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  {extra}"))


def find_btn(w, text):
    """按按钮文字查找（含 emoji 前缀）。"""
    if type(w).__name__ == "Button" and text in str(w.cget("text")):
        return w
    for child in w.winfo_children():
        r = find_btn(child, text)
        if r is not None:
            return r
    return None


def click_confirm_in_dialog(dialog):
    """在确认弹窗里点「确认执行」按钮。"""
    btn = find_btn(dialog, "确认执行")
    if btn is not None:
        btn.invoke()


def click_run():
    """点「开始执行」→ 自动点确认弹窗中的「确认执行」。

    栈式 spy：把当前外层 spy 保存为外层，先用 click_run 自己的 spy 抓 confirm 弹窗；
    结束后还原为外层 spy（而非原始 tk.Toplevel），以便 worker 后续弹窗仍可被外层 spy 抓到。

    注意：页面是「先 tk.Toplevel(...) 再 win.title("水印结果预览")」，构造那一刻标题还是空的，
    所以 spy 只负责收集新建窗口，等 root.update() 之后再按标题匹配 —— 否则永远匹配不到，
    确认弹窗不会被点，worker 不会启动，finished 永不置位，整个用例只能靠硬超时退出（假绿）。
    """
    finished.clear()
    confirm_win = {"w": None}
    made = []
    outer_spy = tk.Toplevel

    def _spy(*a, **k):
        w = outer_spy(*a, **k)
        made.append(w)
        return w

    tk.Toplevel = _spy
    btn_run = find_btn(app._action_bars["watermark"], "开始执行")
    if btn_run is None:
        print("[ERROR] 找不到「开始执行」按钮")
        tk.Toplevel = outer_spy
        return
    btn_run.invoke()
    for _ in range(20):
        root.update()
        for w in made:
            try:
                if w.winfo_exists() and w.title() == "水印结果预览":
                    confirm_win["w"] = w
                    break
            except tk.TclError:
                continue
        if confirm_win["w"] is not None:
            break
    if confirm_win["w"] is not None:
        click_confirm_in_dialog(confirm_win["w"])
    else:
        print("[ERROR] 未捕获「水印结果预览」确认弹窗（校验未通过？）")
    tk.Toplevel = outer_spy                # 还原为外层 spy（栈式），worker 后续弹窗仍可被外层 spy 抓到


def click_preview():
    """点「👁 预览」按钮并等待弹窗出现。"""
    pre_win = {"w": None}
    _orig = tk.Toplevel

    def _spy_pre(*a, **k):
        w = _orig(*a, **k)
        pre_win["w"] = w
        return w

    tk.Toplevel = _spy_pre
    try:
        find_btn(app._action_bars["watermark"], "预览").invoke()
        for _ in range(20):
            root.update()
            if pre_win["w"] is not None and pre_win["w"].winfo_exists():
                break
        return pre_win["w"]
    finally:
        tk.Toplevel = _orig


def configure(i):
    if i == 0:
        st["vis_on"].set(True)
        st["blind_on"].set(False)
        st["vis_layout"].set("tile")
        _set_vis_text("曲靖联通 陈琼")
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
        _set_vis_text("曲靖联通\n陈琼")
        st["blind_text"].set("曲靖联通陈琼20261013")
        st["out_dir"].set(OUT[2])
    elif i == 3:
        st["files"].clear()
        st["vis_on"].set(False)                    # 场景 ④ 只测盲水印提取
        st["blind_on"].set(True)
        st["blind_action"].set("extract")
        page.set_source_dir(OUT[0])                # 用场景 ① 的输出作 extract 源
    elif i == 4:
        # 场景 ⑤ 断言的是「4 风格 / 多行 / 预览按钮」，但也得先真实跑通一次执行，
        # 否则 messagebox.showinfo 不会被调用、finished 不置位、poll_normal 空转到硬超时。
        # 场景 ④ 曾清空 files 并切到 extract，这里恢复成合法的可见水印配置。
        st["files"].clear()
        st["vis_on"].set(True)
        st["blind_on"].set(False)
        st["blind_action"].set("embed")
        st["vis_layout"].set("tile")
        _set_vis_text("预览测试")
        st["out_dir"].set(OUT[0])
        page.set_source_dir(SRC)


def verify(i):
    print(f"=== 验证场景{['①','②','③','④','⑤'][i]} ===")
    if i == 0:
        fs = sorted(os.listdir(OUT[0])) if os.path.isdir(OUT[0]) else []
        check("输出 3 JPG", len(fs) == 3 and all(f.endswith(".jpg") for f in fs), str(fs))
        if fs:
            out_path = os.path.join(OUT[0], fs[0])
            check("尺寸 900x650",
                  Image.open(out_path).size == (900, 650))
            src_img = Image.open(os.path.join(SRC, "IMG_1.jpg")).convert("RGB")
            out_img = Image.open(out_path).convert("RGB")
            # 用 tobytes() 比 getdata()：后者 Pillow 12 起已弃用（Pillow 14 移除）
            src_data = src_img.tobytes()
            out_data = out_img.tobytes()
            diff_count = sum(1 for a, b in zip(src_data, out_data) if a != b)
            check("水印像素差异 > 1000（暗黄 0.15 生效）", diff_count > 1000,
                  f"diff={diff_count}")
    elif i == 1:
        fs = sorted(os.listdir(OUT[1])) if os.path.isdir(OUT[1]) else []
        # v1.5 重构后统一输出 .jpg（避免 PNG 体积浪费），只要是图片格式即可
        check("输出 3 图片", len(fs) == 3
              and all(f.lower().endswith((".jpg", ".jpeg", ".png")) for f in fs), str(fs))
        if fs:
            txt = blind_wm.extract_watermark(os.path.join(OUT[1], fs[0]), 208)
            check("盲水印提取正确", "曲靖联通陈琼20261013" in txt, repr(txt))
    elif i == 2:
        fs = sorted(os.listdir(OUT[2])) if os.path.isdir(OUT[2]) else []
        check("双保险输出 3 JPG", len(fs) == 3 and all(f.endswith(".jpg") for f in fs),
              str(fs))
        if fs:
            txt = blind_wm.extract_watermark(os.path.join(OUT[2], fs[0]), 208)
            check("Q95 仍可提取盲水印", "曲靖联通陈琼20261013" in txt, repr(txt))
    elif i == 3:
        # 提取窗 spy（worker 完成后 _finish 调 _show_extract 弹窗）
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
            # OUT[0] 是场景 ① 生成的可见水印 JPG，没有盲水印。
            # 盲水印提取在空文本/错误长度时返回的可能是空串或乱码，因此这里只能验弹窗结构 + 3 行，
            # 不能断言包含曲靖联通陈琼20261013。
            print(f"  [INFO] 提取窗内容：{vals}")
        # 引擎端兜底：对「没有盲水印的图 / 错误长度」必须降级为未检出，
        # 不能把 blind-watermark 的英文底层异常（fromhex ...）冒到界面
        vis = sorted(os.listdir(OUT[0]))
        if vis:
            try:
                bad = blind_wm.extract_watermark(os.path.join(OUT[0], vis[0]), 208)
                check("无水印图提取降级为空串（不抛异常）", bad == "", repr(bad))
            except Exception as exc:                          # noqa: BLE001
                check("无水印图提取降级为空串（不抛异常）", False,
                      f"{type(exc).__name__}: {exc}")
    elif i == 4:
        # v1.6 新增：默认值 + 4 风格 + 多行 + 预览按钮 + 引擎端印章 + 密度
        check("默认颜色 = 暗黄 #D4A017",
              st["vis_color"].get().upper() == "#D4A017",
              repr(st["vis_color"].get()))
        check("默认透明度 = 15%",
              st["vis_opacity"].get() == "15%",
              repr(st["vis_opacity"].get()))
        check("默认布局 = tile",
              st["vis_layout"].get() == "tile",
              repr(st["vis_layout"].get()))
        check("默认角度 = 30°",
              st["vis_angle"].get() == "30°",
              repr(st["vis_angle"].get()))

        # 多行 Text 控件读写
        _set_vis_text("第一行\n第二行\n第三行")
        for _ in range(3):
            root.update()
        check("多行水印可正确读取（3 行）",
              len(_vis_text().split("\n")) == 3, repr(_vis_text()))

        # 4 风格切换 → 每个渲染引擎端出图
        first_jpg = os.path.join(SRC, "IMG_1.jpg")
        with open(first_jpg, "rb") as f:
            raw = f.read()
        for layout, tf in (
                ("tile", "tile 渲染"),
                ("single", "single 渲染"),
                ("seal", "seal 渲染（圆）"),
                ("grid", "grid 渲染（密度 3）")):
            kw = dict(text="测试水印\n第二行", layout=layout, color="#D4A017",
                      opacity=0.15, font_size_ratio=0.02,
                      position="bottom_right", spacing=1.0, angle=30,
                      density=3 if layout == "grid" else 0)
            out_bytes = wm_core.apply_watermark(raw, **kw)
            check(f"{tf} 出图非空且与原图不同",
                  out_bytes and out_bytes != raw,
                  f"len={len(out_bytes)}")

        # 印章：rect 形态单独验
        out_rect = wm_core.apply_watermark(
            raw, text="印章测试\nTEST", layout="seal", position="bottom_right",
            seal_shape="rect", color="#B91C1C")
        check("印章方框形态出图",
              out_rect and out_rect != raw)

        # 「👁 预览」按钮存在且可点击出弹窗
        st["vis_on"].set(True)
        st["blind_on"].set(False)
        st["vis_layout"].set("tile")
        _set_vis_text("预览测试")
        for _ in range(3):
            root.update()
        w = click_preview()
        check("「👁 预览」按钮可弹出窗口",
              w is not None and w.winfo_exists())
        if w is not None and w.winfo_exists():
            for _ in range(5):
                root.update()
            w.destroy()


# ---------- mainloop 驱动 ----------
cur = [0]
N = 5


def start_cur():
    i = cur[0]
    print(f"=== 配置场景{['①','②','③','④','⑤'][i]} ===")
    configure(i)
    if i == 3:
        # 场景 ④：真跑提取流程，worker 完成后 _show_extract 弹窗 → poll_extract 捕获
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
            root.after(80, start_cur)
        else:
            root.after(80, finish_all)
    else:
        root.after(80, poll_normal)


def poll_extract():
    w = extract_win["w"]
    if w is not None and w.winfo_exists():
        for _ in range(8):
            root.update()
        verify(cur[0])
        cur[0] += 1
        if cur[0] < N:
            root.after(80, start_cur)
        else:
            root.after(80, finish_all)
    else:
        root.after(80, poll_extract)


def finish_all():
    tk.Toplevel = _orig_toplevel
    root.destroy()


# 硬超时兜底：真卡住就计一次失败退出，不再「超时也算通过」造成假绿
def _hard_timeout():
    print("[TIMEOUT] 硬超时兜底：某场景卡住未完成，判失败")
    results["fail"] += 1
    finish_all()

root.after(150, start_cur)
root.after(120000, _hard_timeout)
root.mainloop()

print(f"\n=== 结果：{results['pass']} 通过，{results['fail']} 失败 ===")
sys.exit(0 if results["fail"] == 0 else 1)
