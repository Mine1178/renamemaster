"""首页：功能入口卡片 + 最近使用（任务书 §4.6.1）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader, vlabel

# 窗口宽度 → 卡片列数（<1100px 收成 1 列，任务书 §4.6.1）
_WIDE_MIN = 1100
_MID_MIN = 760
_GAP = T.S_MD            # 卡片之间固定间距 12px

# (emoji, 标题, 顶条色, 描述, 页面 key)
ENTRIES = [
    ("📷", "照片批量命名", T.C_ACCENT,
     "统一前缀 + 序号，或按 Excel 对照表一一改名；可顺带压到 1M / 500K / 200K。",
     "photo"),
    ("💧", "添加水印", T.C_CYAN,
     "斜向平铺（裁不掉）或角落单处，任意颜色 + 描边；支持隐形盲水印版权溯源。",
     "watermark"),
    ("📕", "PDF 批量命名", T.C_PURPLE,
     "按正文开头、统一前缀序号或 Excel 对照表，给一堆 PDF 快速规范取名。",
     "pdf"),
    ("📊", "表格批量命名", T.C_INFO,
     "一堆「新建 XLS 表.xlsx」按规则统一取名，支持 .xlsx / .xlsm / .xls / .csv；"
     "对照表用 .xlsx / .xlsm / .csv。",
     "spreadsheet"),
    ("📄", "文档批量命名", T.C_SUCCESS,
     "Word / PDF / TXT 取正文开头自动取名，再叠加前缀与序号规则。",
     "document"),
]

# 入口卡片底部留白：描述下垫一个空 Frame，保证卡片等高且「进入 →」不贴描述
_SPACER_H = 24
# 网格最多用到的列（3 卡片列 + 2 间隔列 = 0..4）
_MAX_GRID_COL = 5


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
               "批量改名 · 图片压缩 · 添加水印 · 文档 / 表格 / PDF 一键处理")

    grid = tk.Frame(page, bg=T.C_BG)
    grid.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))

    cards = []
    descs = []
    for emoji, title, accent, desc, key in ENTRIES:
        card = Card(grid, title="", accent=accent,
                    on_click=lambda k=key: app.show(k))
        # body 自上而下：大号 emoji → 标题 → 描述（全部居中）
        vlabel(card.body, emoji, font=(T.FONT_FAMILY, 30),
               bg=T.C_CARD, fg=accent, wrap="word", compact=True,
               justify=tk.CENTER).pack(fill=tk.X, pady=(T.S_SM, 0))
        vlabel(card.body, title, font=(T.FONT_FAMILY, T.F_METRIC, "bold"),
               bg=T.C_CARD, fg=T.C_TEXT, wrap="word", compact=True,
               justify=tk.CENTER).pack(fill=tk.X, pady=(T.S_SM, 0))
        d = vlabel(card.body, desc, font=(T.FONT_FAMILY, T.F_BODY),
                   bg=T.C_CARD, fg=T.C_TEXT_SUB, wrap="word", compact=True,
                   justify=tk.CENTER)
        d.pack(fill=tk.X, pady=(T.S_SM, 0))
        descs.append(d)
        tk.Frame(card.body, bg=T.C_CARD, height=_SPACER_H).pack(fill=tk.X)
        cards.append(card)

    def _fit_descs() -> None:
        for card, d in zip(cards, descs):
            if hasattr(d, "_auto_height"):
                d._auto_height()

    def _configure_columns(ncols: int) -> None:
        """卡片列(偶数列, weight=1 uniform) + 固定间隔列(奇数列, minsize=_GAP)。"""
        for c in range(ncols):
            grid.grid_columnconfigure(c * 2, weight=1, uniform="home_card")
            if c < ncols - 1:
                grid.grid_columnconfigure(c * 2 + 1, weight=0, minsize=_GAP,
                                          uniform="")
        # 响应式收列时，关掉不再使用的旧列（否则残留权重 / 宽度）
        for old in range(ncols * 2 - 1, _MAX_GRID_COL + 1):
            grid.grid_columnconfigure(old, weight=0, minsize=0, uniform="")

    def _relayout(cols: int) -> None:
        for c in cards:
            c.grid_forget()
        _configure_columns(cols)
        total_rows = -(-len(cards) // cols)
        for i, c in enumerate(cards):
            r, cc = i // cols, i % cols
            pady = (0, _GAP) if r < total_rows - 1 else (0, 0)
            c.grid(row=r, column=cc * 2, sticky="nsew", pady=pady)
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
    row = tk.Frame(recent.body, bg=T.C_CARD)
    row.pack(fill=tk.X)
    vlabel(row, text="上次输出目录：", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    dir_label = vlabel(row, text="（尚无记录）", font=(T.FONT_FAMILY, T.F_BODY),
                       bg=T.C_CARD, fg=T.C_TEXT, anchor="w")
    dir_label.pack(side=tk.LEFT)
    row2 = tk.Frame(recent.body, bg=T.C_CARD)
    row2.pack(fill=tk.X, pady=(T.S_XS, 0))
    vlabel(row2, text="上次批次数量：", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    count_label = vlabel(row2, text="0 个文件",
                         font=(T.FONT_FAMILY, T.F_METRIC, "bold"),
                         bg=T.C_CARD, fg=T.C_ACCENT, anchor="w")
    count_label.pack(side=tk.LEFT)

    def refresh() -> None:
        """重读「上次输出」配置。

        首页只 build 一次，执行完一批后 cfg 已更新但标签还是旧值，
        用户切回首页看到的是过期数据（v1.9 修复：App.show 会调用本钩子）。
        """
        dir_label.set_text(
            _shorten(app.cfg.get("output.last_dir", "") or "（尚无记录）"))
        count_label.set_text(f"{app.cfg.get('output.last_count', 0) or 0} 个文件")

    page.refresh = refresh       # 供 app.show() 在切回本页时回调
    refresh()
