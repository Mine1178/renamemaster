"""首页：功能入口卡片 + 最近使用（任务书 §4.6.1）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader

# 窗口宽度 → 卡片列数（<1100px 收成 1 列，任务书 §4.6.1）
_WIDE_MIN = 1100
_MID_MIN = 760

# (emoji, 标题, 顶条色, 描述, 页面 key)
ENTRIES = [
    ("📷", "照片批量命名", T.C_ACCENT,
     "统一前缀 + 序号，或按 Excel 对照表一一改名；可顺带压到 1M / 500K / 200K。",
     "photo"),
    ("📊", "表格批量命名", T.C_INFO,
     "一堆「新建 XLS 表.xlsx」按规则统一取名，支持 .xlsx / .xls / .csv。",
     "spreadsheet"),
    ("📄", "文档批量命名", T.C_SUCCESS,
     "Word / PDF / TXT 取正文开头自动取名，再叠加前缀与序号规则。",
     "document"),
]

# 入口卡片最小高度 180px：描述下面垫一个空 Frame 撑起来（列宽变化时高度不塌）
_SPACER_H = 56


def _shorten(text: str, limit: int = 56) -> str:
    """长路径中间截断：D:\\...\\重命名输出（两端保留，中间 ...）。"""
    s = str(text)
    if len(s) <= limit:
        return s
    head = max(1, limit // 2 - 1)
    tail = max(1, limit - head - 3)
    return f"{s[:head]}...{s[-tail:]}"


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "文件批量命名助手",
               "一键批量改名 · 图片压缩 · 表格文档统一处理")

    grid = tk.Frame(page, bg=T.C_BG)
    grid.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))

    cards = []
    descs = []
    for emoji, title, accent, desc, key in ENTRIES:
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="home_card")
        card = Card(grid, title="", accent=accent,
                    on_click=lambda k=key: app.show(k))
        # body 自上而下：大号 emoji → 标题 → 描述
        tk.Label(card.body, text=emoji, font=(T.FONT_FAMILY, 28),
                 bg=T.C_CARD, fg=accent, anchor="w").pack(fill=tk.X)
        tk.Label(card.body, text=title, font=(T.FONT_FAMILY, T.F_METRIC, "bold"),
                 bg=T.C_CARD, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                            pady=(T.S_XS, 0))
        d = tk.Label(card.body, text=desc, font=(T.FONT_FAMILY, T.F_BODY),
                     bg=T.C_CARD, fg=T.C_TEXT_SUB, anchor="w", justify=tk.LEFT,
                     wraplength=240)
        d.pack(fill=tk.X, pady=(T.S_XS, 0))
        descs.append(d)
        tk.Frame(card.body, bg=T.C_CARD, height=_SPACER_H).pack(fill=tk.X)
        cards.append(card)

    def _fit_descs() -> None:
        for card, d in zip(cards, descs):
            width = card.body.winfo_width() - 2
            if width > 80:
                d.config(wraplength=width)

    def _relayout(cols: int) -> None:
        for c in cards:
            c.grid_forget()
        for col in range(cols):
            grid.grid_columnconfigure(col, weight=1, uniform="home_card")
        for i, c in enumerate(cards):
            c.grid(row=i // cols, column=i % cols, sticky="nsew",
                   padx=(0, T.S_MD) if (i % cols) < cols - 1 else 0,
                   pady=(0, T.S_MD) if i < len(cards) - cols else 0)
        _fit_descs()

    state = {"cols": 0}

    def _on_resize(event=None) -> None:
        width = grid.winfo_width() or _WIDE_MIN
        cols = 3 if width >= _WIDE_MIN else (2 if width >= _MID_MIN else 1)
        if cols != state["cols"]:
            state["cols"] = cols
            _relayout(cols)
        else:
            _fit_descs()

    grid.bind("<Configure>", _on_resize)
    _on_resize()

    # ---------- 最近使用 ----------
    recent = Card(page, "最近使用", accent=T.C_TEXT_M)
    recent.pack(fill=tk.X, pady=(0, T.S_MD))
    last_dir = _shorten(app.cfg.get("output.last_dir", "") or "（尚无记录）")
    last_count = app.cfg.get("output.last_count", 0) or 0
    row = tk.Frame(recent.body, bg=T.C_CARD)
    row.pack(fill=tk.X)
    tk.Label(row, text="上次输出目录：", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Label(row, text=last_dir, font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT, anchor="w").pack(side=tk.LEFT)
    row2 = tk.Frame(recent.body, bg=T.C_CARD)
    row2.pack(fill=tk.X, pady=(T.S_XS, 0))
    tk.Label(row2, text="上次批次数量：", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Label(row2, text=f"{last_count} 个文件",
             font=(T.FONT_FAMILY, T.F_METRIC, "bold"),
             bg=T.C_CARD, fg=T.C_ACCENT, anchor="w").pack(side=tk.LEFT)
