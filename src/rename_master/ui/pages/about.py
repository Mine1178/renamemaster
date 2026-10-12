"""关于页：品牌头 + 功能特性 / 技术栈两列（任务书 §4.6）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader

FEATURES = [
    "模式一：统一前缀 + 序号（位数 / 起始值 / 分隔符 / 保留扩展名）",
    "模式二：Excel / CSV 对照表一一改名，重名与非法字符自动校验标色",
    "图片压缩：二分法 JPEG quality，压不到就等比缩分辨率",
    "文档正文提取：取开头文字叠加前缀自动取名",
    "输出隔离 + 执行前预览 + 操作日志，全程可追溯",
]

STACK = [
    "Python 3.11",
    "tkinter",
    "Pillow",
    "openpyxl",
    "python-docx",
    "pypdf",
]


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "关于 RenameMaster", "版本 v1.0 · 本地运行，数据不出本机")

    # ---------- 品牌头 ----------
    head = tk.Frame(page, bg=T.C_BG)
    head.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))
    tk.Label(head, text="◉", font=(T.FONT_FAMILY, 40),
             bg=T.C_BG, fg=T.C_ACCENT, anchor="center").pack(fill=tk.X)
    tk.Label(head, text="RenameMaster v1.0",
             font=(T.FONT_FAMILY, T.F_H1, "bold"),
             bg=T.C_BG, fg=T.C_TEXT, anchor="center").pack(fill=tk.X,
                                                           pady=(T.S_XS, 0))
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
    for item in FEATURES:
        tk.Label(feat.body, text=f"· {item}", font=(T.FONT_FAMILY, T.F_BODY),
                 bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w", justify=tk.LEFT,
                 wraplength=300).pack(fill=tk.X, pady=1)

    stack = Card(cols, "技术栈", accent=T.C_INFO)
    stack.grid(row=0, column=1, sticky="nsew", padx=(T.S_SM, 0))
    for item in STACK:
        tk.Label(stack.body, text=f"· {item}", font=(T.FONT_FAMILY, T.F_BODY),
                 bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(fill=tk.X, pady=1)

    tk.Label(page, text="© 2026 · 本地工具，数据不出本机",
             font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_TEXT_L,
             anchor="center").pack(fill=tk.X, pady=(0, T.S_MD))
