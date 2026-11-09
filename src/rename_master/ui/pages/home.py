"""首页：功能入口卡片 + 最近使用（任务书 §4.6.1）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader, balanced_rows, vlabel

# 窗口宽度 → 卡片最多列数（按卡片实测最小可读宽度定，见 theme.CARD_MIN_W）
_WIDE_MIN = 1100
_MID_MIN = 760
_GAP = T.S_MD            # 卡片之间固定间距 12px

# (emoji, 标题, 顶条色, 描述, 页面 key)
ENTRIES = [
    ("📷", "照片批量命名", T.C_ACCENT,
     "统一前缀 + 序号，或按 Excel 对照表一一改名；可顺带压到 1M / 500K / 200K。",
     "photo"),
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
    ("🏪", "门店档案管理", T.C_ACCENT,
     "本地维护门店档案，支持 Excel 批量导入 / 导出与模糊搜索。",
     "store"),
]

# 入口卡片底部留白：描述下垫一个空 Frame，保证卡片等高且「进入 →」不贴描述
_SPACER_H = 24


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
               "批量改名 · 图片压缩 · 文档 / 表格 / PDF 一键处理")

    grid = tk.Frame(page, bg=T.C_BG)
    grid.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))

    cards = []
    descs = []
    for emoji, title, accent, desc, key in ENTRIES:
        card = Card(grid, title="", accent=accent,
                    on_click=lambda k=key: app.show(k))
        # body 自上而下：大号 emoji → 标题 → 描述（全部居中）
        vlabel(card.body, emoji, font=(T.FONT_FAMILY, T.F_ICON),
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

    # 每行一个容器：行内卡片 pack(expand=True) 等宽铺满，末行元素少也不会
    # 出现「左侧一张卡、右侧一大片空白」的孤行（旧实现按固定列数排 3+1）。
    row_frames: list[tk.Frame] = []

    def _relayout(counts: list[int]) -> None:
        grid.grid_columnconfigure(0, weight=1)
        for rowf in row_frames:
            for slave in rowf.pack_slaves():
                slave.pack_forget()
            # Tk 按创建顺序堆叠子窗口：行容器晚于卡片创建，若不显式压到底层，
            # 它的 C_BG 背景会把整片卡片盖住，首页看起来就是「没有内容」。
            rowf.lower()
        for r, count in enumerate(counts):
            if r >= len(row_frames):
                rowf = tk.Frame(grid, bg=T.C_BG)
                row_frames.append(rowf)
                rowf.lower()
            else:
                rowf = row_frames[r]
            rowf.grid(row=r, column=0, sticky="ew")
            first = sum(counts[:r])
            last_row = r == len(counts) - 1
            for j in range(count):
                card = cards[first + j]
                card.pack(
                    in_=rowf, side=tk.LEFT, fill=tk.BOTH, expand=True,
                    padx=(0 if j == 0 else _GAP, 0),
                    pady=(0, 0) if last_row else (0, _GAP))
                card.lift()          # 双保险：卡片始终在行容器之上
        for rowf in row_frames[len(counts):]:
            rowf.grid_forget()
        _fit_descs()

    state = {"counts": ()}

    def _on_resize(event=None) -> None:
        width = grid.winfo_width()
        if width <= 1:                    # 首次布局尚未拿到真实宽度
            width = _WIDE_MIN
        max_cols = (T.CARD_MAX_COLS if width >= _WIDE_MIN else
                    2 if width >= _MID_MIN else 1)
        counts = tuple(balanced_rows(len(cards), max_cols))
        if counts != state["counts"]:
            state["counts"] = counts
            _relayout(list(counts))
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
