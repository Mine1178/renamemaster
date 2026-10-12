"""关于页：版本 + 简介（任务书 §4.6）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader

INTRO = [
    "RenameMaster 是一款 Windows 桌面端文件批量命名助手：",
    "把相机 / 微信 / 钉钉导出的乱名照片、Excel 台账、Word / PDF 文档，",
    "一键改成规范名称，并可在改名同时把照片压到指定大小（1M / 500K / 200K / 100K）。",
    "",
    "默认输出到「<源目录>_重命名输出」，绝不原地覆盖原图。",
]

FEATURES = [
    "模式一：统一前缀 + 序号（可设位数 / 起始值 / 分隔符 / 保留扩展名）",
    "模式二：Excel / CSV 对照表一一改名，重名与非法字符自动校验标色",
    "图片压缩：二分法 JPEG quality，压不到就等比缩分辨率",
    "输出隔离 + 执行前预览 + 操作日志，全程可追溯",
]


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "关于 RenameMaster", "版本 v1.0 · 文件批量命名助手")

    info = Card(page, "RenameMaster v1.0", desc="Windows 桌面端 · tkinter + Pillow",
                accent=T.C_ACCENT)
    info.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))
    for line in INTRO:
        tk.Label(info.body, text=line, font=(T.FONT_FAMILY, T.F_BODY),
                 bg=T.C_CARD, fg=T.C_TEXT if line else T.C_CARD,
                 anchor="w", justify=tk.LEFT).pack(fill=tk.X, pady=1)

    feat = Card(page, "功能概览", accent=T.C_INFO)
    feat.pack(fill=tk.X, pady=(0, T.S_MD))
    for item in FEATURES:
        tk.Label(feat.body, text=f"· {item}", font=(T.FONT_FAMILY, T.F_BODY),
                 bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w", justify=tk.LEFT,
                 wraplength=760).pack(fill=tk.X, pady=1)

    tk.Label(page, text="v1.0 · 2026-10-12", font=(T.FONT_FAMILY, T.F_SM),
             bg=T.C_BG, fg=T.C_TEXT_L, anchor="w").pack(fill=tk.X, pady=(0, T.S_MD))
