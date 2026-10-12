"""关于页：品牌头 + 功能特性 / 技术栈两列。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader

FEATURES = [
    ("统一前缀 + 序号", "位数 / 起始值 / 分隔符 / 保留扩展名均可自定义"),
    ("Excel 对照表一一改名", "重名与非法字符自动校验标色"),
    ("图片自动压缩", "二分法调 JPEG 质量，压不到再等比缩分辨率"),
    ("文档正文提取", "Word / PDF / TXT 取开头文字自动取名"),
    ("安全可追溯", "输出隔离 + 执行前预览 + 操作日志，绝不原地覆盖"),
]

STACK = [
    "Python 3.11",
    "tkinter（标准库）",
    "Pillow（图片）",
    "openpyxl（Excel）",
    "python-docx（Word）",
    "pypdf（PDF）",
]


def _feature_row(master: tk.Widget, title: str, desc: str) -> None:
    """一行功能：粗体标题 + 灰色说明（两行，不挤）。"""
    row = tk.Frame(master, bg=T.C_CARD)
    row.pack(fill=tk.X, pady=(T.S_XS, 0))
    tk.Label(row, text=f"· {title}", font=(T.FONT_FAMILY, T.F_BODY, "bold"),
             bg=T.C_CARD, fg=T.C_TEXT, anchor="w", justify=tk.LEFT).pack(fill=tk.X)
    tk.Label(row, text=f"    {desc}", font=(T.FONT_FAMILY, T.F_SM),
             bg=T.C_CARD, fg=T.C_TEXT_SUB, anchor="w", justify=tk.LEFT,
             wraplength=520).pack(fill=tk.X, pady=(0, T.S_XS))


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "关于 RenameMaster", "版本 v1.0 · 本地运行，数据不出本机")

    # ---------- 品牌头 ----------
    head = tk.Frame(page, bg=T.C_BG)
    head.pack(fill=tk.X, pady=(T.S_MD, T.S_LG))
    tk.Label(head, text="◉", font=(T.FONT_FAMILY, 44),
             bg=T.C_BG, fg=T.C_ACCENT, anchor="center").pack(fill=tk.X)
    tk.Label(head, text="RenameMaster v1.0",
             font=(T.FONT_FAMILY, T.F_H1, "bold"),
             bg=T.C_BG, fg=T.C_TEXT, anchor="center").pack(fill=tk.X,
                                                           pady=(T.S_SM, 0))
    tk.Label(head, text="文件批量命名助手", font=(T.FONT_FAMILY, T.F_SECTION),
             bg=T.C_BG, fg=T.C_TEXT_L, anchor="center").pack(fill=tk.X,
                                                             pady=(T.S_XS, 0))

    # ---------- 两列卡片 ----------
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

    tk.Label(page, text="© 2026 · 本地工具，数据不出本机",
             font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_TEXT_L,
             anchor="center").pack(fill=tk.X, pady=(T.S_MD, T.S_MD))
