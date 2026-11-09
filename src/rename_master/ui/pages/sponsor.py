"""赞助页：独立的「请作者喝杯咖啡」页面（与全局视觉风格统一）。

复用 sponsor_common 的双码内联布局；关于页的赞助按钮也跳转本页，避免两套实现。
"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import PageHeader, vlabel
from rename_master.ui.sponsor_common import show_sponsor_codes


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "☕ 赞助作者", "如果这套工具帮到了你，请作者喝杯咖啡")

    head = tk.Frame(page, bg=T.C_BG)
    head.pack(fill=tk.X, pady=(T.S_MD, T.S_LG))
    vlabel(head, "☕", font=(T.FONT_FAMILY, T.F_DISPLAY),
           bg=T.C_BG, fg=T.C_ACCENT, justify=tk.CENTER).pack(fill=tk.X)
    vlabel(head, "你的支持是持续更新最大的动力",
           font=(T.FONT_FAMILY, T.F_TITLE, "bold"),
           bg=T.C_BG, fg=T.C_TEXT, justify=tk.CENTER).pack(pady=(T.S_XS, 0))
    vlabel(head, "微信 / 支付宝 长按或点击可放大保存",
           font=(T.FONT_FAMILY, T.F_LEAD), bg=T.C_BG, fg=T.C_TEXT_M,
           justify=tk.CENTER).pack(pady=(0, T.S_SM))

    show_sponsor_codes(page, big=True)

    vlabel(page, "© 2026 · 本地工具，数据不出本机",
           font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_TEXT_L,
           justify=tk.CENTER).pack(pady=(T.S_MD, T.S_MD))
