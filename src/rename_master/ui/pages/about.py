"""关于页：品牌头 + 功能特性 / 技术栈两列 + 赞助按钮（d2w v1.5.4 规范）。"""
from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader

FEATURES = [
    ("统一前缀 + 序号", "位数 / 起始值 / 分隔符 / 保留扩展名均可自定义"),
    ("Excel 对照表一一改名", "重名与非法字符自动校验标色"),
    ("图片自动压缩", "二分法调 JPEG 质量，压不到再等比缩分辨率"),
    ("照片水印", "半透明白色文字，5 位置 × 3 档字号，默认关闭"),
    ("拖拽支持", "拖文件夹进窗口自动填路径"),
    ("安全可追溯", "输出隔离 + 执行前预览 + 操作日志，绝不原地覆盖"),
]

STACK = [
    "Python 3.11",
    "tkinter（标准库）",
    "Pillow（图片/水印）",
    "openpyxl（Excel）",
    "python-docx（Word）",
    "pypdf（PDF）",
    "tkinterdnd2（拖拽）",
]


def _resource_path(rel: str) -> Path:
    """PyInstaller 打包后资源在 _MEIPASS 下，开发时在项目根。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel  # type: ignore[attr-defined]
    # 开发态：从 src/rename_master/ui/pages/ 上溯到项目根
    return Path(__file__).resolve().parents[3] / rel


def _feature_row(master: tk.Widget, title: str, desc: str) -> None:
    row = tk.Frame(master, bg=T.C_CARD)
    row.pack(fill=tk.X, pady=(T.S_XS, 0))
    tk.Label(row, text=f"· {title}", font=(T.FONT_FAMILY, T.F_BODY, "bold"),
             bg=T.C_CARD, fg=T.C_TEXT, anchor="w", justify=tk.LEFT).pack(fill=tk.X)
    tk.Label(row, text=f"    {desc}", font=(T.FONT_FAMILY, T.F_SM),
             bg=T.C_CARD, fg=T.C_TEXT_SUB, anchor="w", justify=tk.LEFT,
             wraplength=520).pack(fill=tk.X, pady=(0, T.S_XS))


def _show_sponsor_dialog(parent: tk.Misc, anchor: tk.Widget | None = None) -> None:
    """弹赞助窗：文案 + 支付宝/微信收款码。

    anchor: 赞助按钮本身，弹窗定位在按钮附近。
    """
    dlg = tk.Toplevel(parent)
    dlg.title("赞助作者")
    W, H = 860, 640
    dlg.geometry(f"{W}x{H}")
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    # 定位：在 anchor（按钮）右下方，超出屏幕时回退居中
    if anchor is not None:
        parent.update_idletasks()
        ax = anchor.winfo_rootx()
        ay = anchor.winfo_rooty()
        aw = anchor.winfo_width()
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        x = ax + aw - W // 2
        y = ay + anchor.winfo_height() + 10
        if x < 10: x = 10
        if y + H > sh - 10: y = sh - H - 10
        if x + W > sw - 10: x = sw - W - 10
        dlg.geometry(f"+{max(0,x)}+{max(0,y)}")

    tk.Label(dlg, text="☕", font=(T.FONT_FAMILY, 32),
             bg=T.C_BG, fg=T.C_ACCENT).pack(pady=(T.S_MD, T.S_XS))
    tk.Label(dlg, text="如果你喜欢这个工具",
             font=(T.FONT_FAMILY, T.F_SECTION + 2, "bold"),
             bg=T.C_BG, fg=T.C_TEXT).pack()
    tk.Label(dlg, text="可以请作者喝杯咖啡，感谢赞助",
             font=(T.FONT_FAMILY, T.F_BODY + 1),
             bg=T.C_BG, fg=T.C_TEXT_M).pack(pady=(0, T.S_MD))

    codes = tk.Frame(dlg, bg=T.C_BG)
    codes.pack(pady=(0, T.S_MD), expand=True, fill=tk.BOTH)

    alipay = _resource_path("assets/alipay.jpg")
    wechat = _resource_path("assets/wechatpay.jpg")

    def _load_code(path: Path, label: str) -> None:
        cell = tk.Frame(codes, bg=T.C_BG)
        cell.pack(side=tk.LEFT, padx=T.S_LG, expand=True)
        if path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(path)
                # 按原图比例缩到 320x320 内，不拉伸不变形
                img.thumbnail((320, 320), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(cell, image=photo, bg="#ffffff",
                               relief=tk.SOLID, bd=1)
                lbl.image = photo  # type: ignore[attr-defined]
                lbl.pack()
            except Exception as e:
                tk.Label(cell, text=f"[{label}加载失败: {e}]",
                         font=(T.FONT_FAMILY, T.F_SM),
                         bg=T.C_BG, fg=T.C_DANGER).pack()
        else:
            tk.Label(cell, text=f"[{label}\n待添加]",
                     font=(T.FONT_FAMILY, T.F_SM), width=14, height=9,
                     bg="#e2e8f0", fg=T.C_TEXT_L, relief=tk.SOLID, bd=1).pack()
        tk.Label(cell, text=label, font=(T.FONT_FAMILY, T.F_BODY, "bold"),
                 bg=T.C_BG, fg=T.C_TEXT_M).pack(pady=(T.S_SM, 0))

    _load_code(alipay, "支付宝")
    _load_code(wechat, "微信")

    tk.Button(dlg, text="关闭", command=dlg.destroy,
              font=(T.FONT_FAMILY, T.F_BODY),
              bg=T.C_PRIMARY, fg="#ffffff", relief=tk.FLAT, padx=24, pady=6
              ).pack(pady=(0, T.S_MD))


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "关于 RenameMaster", "版本 v1.1 · 本地运行，数据不出本机")

    head = tk.Frame(page, bg=T.C_BG)
    head.pack(fill=tk.X, pady=(T.S_MD, T.S_LG))
    tk.Label(head, text="◉", font=(T.FONT_FAMILY, 44),
             bg=T.C_BG, fg=T.C_ACCENT, anchor="center").pack(fill=tk.X)
    tk.Label(head, text="RenameMaster v1.1",
             font=(T.FONT_FAMILY, T.F_H1, "bold"),
             bg=T.C_BG, fg=T.C_TEXT, anchor="center").pack(fill=tk.X,
                                                           pady=(T.S_SM, 0))
    tk.Label(head, text="文件批量命名助手", font=(T.FONT_FAMILY, T.F_SECTION),
             bg=T.C_BG, fg=T.C_TEXT_L, anchor="center").pack(fill=tk.X,
                                                             pady=(T.S_XS, 0))

    cols = tk.Frame(page, bg=T.C_BG)
    cols.pack(fill=tk.X, pady=(0, T.S_MD))
    cols.grid_columnconfigure(0, weight=1, uniform="about_col")
    cols.grid_columnconfigure(1, weight=1, uniform="about_col")

    feat = Card(cols, "功能特性", accent=T.C_SUCCESS)
    feat.grid(row=0, column=0, sticky="nsew", padx=(0, T.S_SM))
    for title, desc in FEATURES:
        _feature_row(feat.body, title, desc)

    stack = Card(cols, "技术栈", accent=T.C_INFO)
    stack.grid(row=0, column=1, sticky="nsew", padx=(T.S_SM, 0))
    for item in STACK:
        tk.Label(stack.body, text=f"· {item}", font=(T.FONT_FAMILY, T.F_BODY),
                 bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(fill=tk.X, pady=2)

    # ---------- 赞助按钮（d2w v1.5.4 规范，secondary 浅底深字） ----------
    btn_row = tk.Frame(page, bg=T.C_BG)
    btn_row.pack(pady=(T.S_SM, 0))
    sponsor_btn = tk.Button(btn_row, text="☕ 赞助作者",
              font=(T.FONT_FAMILY, T.F_BODY),
              bg="#f1f5f9", fg=T.C_TEXT, relief=tk.SOLID, bd=1,
              activebackground="#e2e8f0", activeforeground=T.C_TEXT,
              padx=16, pady=6, cursor="hand2")
    sponsor_btn.pack()
    sponsor_btn.configure(command=lambda: _show_sponsor_dialog(page, sponsor_btn))

    tk.Label(page, text="© 2026 · 本地工具，数据不出本机",
             font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_TEXT_L,
             anchor="center").pack(fill=tk.X, pady=(T.S_MD, T.S_MD))
