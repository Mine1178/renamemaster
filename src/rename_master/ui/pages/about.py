"""关于页：品牌头 + 功能特性 / 技术栈两列 + 赞助入口（跳转到独立赞助页）。"""
from __future__ import annotations

import sys

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader, vlabel

FEATURES = [
    ("统一前缀 + 序号", "位数 / 起始值 / 分隔符 / 保留扩展名均可自定义"),
    ("Excel 对照表一一改名", "重名与非法字符自动校验标色"),
    ("图片自动压缩", "二分法调 JPEG 质量，压不到再等比缩分辨率"),
    ("拖拽支持", "拖文件夹进窗口自动填路径"),
    ("安全可追溯", "输出隔离 + 执行前预览 + 操作日志，绝不原地覆盖"),
    ("门店档案管理", "本地 SQLite 存储，支持 Excel 批量导入 / 导出"),
]

STACK = [
    # 运行期实测版本，避免写死（打包用哪个解释器就显示哪个）
    f"Python {sys.version_info.major}.{sys.version_info.minor}"
    f".{sys.version_info.micro}",
    "tkinter（标准库）",
    "Pillow（图片）",
    "openpyxl（Excel）",
    "python-docx（Word）",
    "pypdf（PDF）",
    "tkinterdnd2（拖拽）",
    "sqlite3（门店档案）",
]


def _feature_row(master: tk.Widget, title: str, desc: str) -> None:
    row = tk.Frame(master, bg=T.C_CARD)
    row.pack(fill=tk.X, pady=(T.S_XS, 0))
    vlabel(row, f"· {title}", font=(T.FONT_FAMILY, T.F_BODY, "bold"),
           bg=T.C_CARD, fg=T.C_TEXT, justify=tk.LEFT).pack(fill=tk.X)
    vlabel(row, f"    {desc}", font=(T.FONT_FAMILY, T.F_SM),
           bg=T.C_CARD, fg=T.C_TEXT_SUB, justify=tk.LEFT,
           wrap="word").pack(fill=tk.X, pady=(0, T.S_XS))


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "关于 重命名大师", f"版本 v{app.VERSION} · 本地运行，数据不出本机")

    head = tk.Frame(page, bg=T.C_BG)
    head.pack(fill=tk.X, pady=(T.S_MD, T.S_LG))
    vlabel(head, "◉", font=(T.FONT_FAMILY, T.F_HERO),
           bg=T.C_BG, fg=T.C_ACCENT, justify=tk.CENTER).pack(fill=tk.X)
    vlabel(head, f"重命名大师 v{app.VERSION}",
           font=(T.FONT_FAMILY, T.F_H1, "bold"),
           bg=T.C_BG, fg=T.C_TEXT, justify=tk.CENTER).pack(fill=tk.X,
                                                           pady=(T.S_SM, 0))
    vlabel(head, "文件批量命名助手", font=(T.FONT_FAMILY, T.F_SECTION),
           bg=T.C_BG, fg=T.C_TEXT_L, justify=tk.CENTER).pack(fill=tk.X,
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
        vlabel(stack.body, f"· {item}", font=(T.FONT_FAMILY, T.F_BODY),
               bg=T.C_CARD, fg=T.C_TEXT_M).pack(fill=tk.X, pady=T.S_XS)

    # ---------- 赞助按钮（无边框，与页面底色融合，hover 微亮） ----------
    btn_row = tk.Frame(page, bg=T.C_BG)
    btn_row.pack(pady=(T.S_SM, 0))
    sponsor_btn = tk.Button(btn_row, text="☕ 赞助作者",
              font=(T.FONT_FAMILY, T.F_BODY),
              bg=T.C_BG, fg=T.C_TEXT_M,
              activebackground=T.C_HOVER, activeforeground=T.C_TEXT,
              relief=tk.FLAT, bd=0, highlightthickness=0,
              padx=T.S_LG, pady=T.S_XS, cursor="hand2")
    sponsor_btn.pack()
    sponsor_btn.bind("<Enter>", lambda e: sponsor_btn.config(bg=T.C_HOVER))
    sponsor_btn.bind("<Leave>", lambda e: sponsor_btn.config(bg=T.C_BG))
    sponsor_btn.configure(command=lambda: app.show("sponsor"))

    vlabel(page, "© 2026 · 本地工具，数据不出本机",
           font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_TEXT_L,
           justify=tk.CENTER).pack(fill=tk.X, pady=(T.S_MD, T.S_MD))
