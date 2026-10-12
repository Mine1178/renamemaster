"""首页：功能入口卡片 + 最近使用（任务书 §4.6.1）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader

# 窗口宽度 → 卡片列数（<1100px 收成 1 列，任务书 §4.6.1）
_WIDE_MIN = 1100
_MID_MIN = 760

ENTRIES = [
    ("📷 照片批量命名", T.C_ACCENT,
     "统一前缀 + 序号，或按 Excel 对照表一一改名；可顺带压到 1M / 500K / 200K。",
     "photo"),
    ("📊 表格批量命名", T.C_INFO,
     "一堆「新建 XLS 表.xlsx」按规则统一取名，支持 .xlsx / .xls / .csv。",
     "spreadsheet"),
    ("📄 文档批量命名", T.C_SUCCESS,
     "Word / PDF / TXT 取正文开头自动取名，再叠加前缀与序号规则。",
     "document"),
]


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "文件批量命名助手",
               "一键批量改名 · 图片压缩 · 表格文档统一处理")

    grid = tk.Frame(page, bg=T.C_BG)
    grid.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))

    cards = []
    for idx, (title, accent, desc, key) in enumerate(ENTRIES):
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="home_card")
        card = Card(grid, title=title, desc=desc, accent=accent,
                    on_click=lambda k=key: app.show(k))
        cards.append(card)

    def _relayout(cols: int) -> None:
        for c in cards:
            c.grid_forget()
        for col in range(cols):
            grid.grid_columnconfigure(col, weight=1, uniform="home_card")
        for i, c in enumerate(cards):
            c.grid(row=i // cols, column=i % cols, sticky="nsew",
                   padx=(0, T.S_MD) if (i % cols) < cols - 1 else 0,
                   pady=(0, T.S_MD) if i < len(cards) - cols else 0)

    state = {"cols": 0}

    def _on_resize(event=None) -> None:
        width = grid.winfo_width() or _WIDE_MIN
        cols = 3 if width >= _WIDE_MIN else (2 if width >= _MID_MIN else 1)
        if cols != state["cols"]:
            state["cols"] = cols
            _relayout(cols)

    grid.bind("<Configure>", _on_resize)
    _on_resize()

    # ---------- 最近使用 ----------
    recent = Card(page, "最近使用", accent=T.C_TEXT_M)
    recent.pack(fill=tk.X, pady=(0, T.S_MD))
    last_dir = app.cfg.get("output.last_dir", "") or "（尚无记录）"
    last_count = app.cfg.get("output.last_count", 0) or 0
    row = tk.Frame(recent.body, bg=T.C_CARD)
    row.pack(fill=tk.X)
    tk.Label(row, text="上次输出目录：", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Label(row, text=str(last_dir), font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT, anchor="w").pack(side=tk.LEFT)
    row2 = tk.Frame(recent.body, bg=T.C_CARD)
    row2.pack(fill=tk.X, pady=(T.S_XS, 0))
    tk.Label(row2, text="上次批次数量：", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Label(row2, text=f"{last_count} 个文件",
             font=(T.FONT_FAMILY, T.F_METRIC, "bold"),
             bg=T.C_CARD, fg=T.C_ACCENT, anchor="w").pack(side=tk.LEFT)
