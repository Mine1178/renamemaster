"""帮助页：应用内使用说明（与 README 内容对应，风格统一）。"""
from __future__ import annotations

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader, vlabel


_SECTIONS = [
    ("🚀 快速上手", T.C_ACCENT,
     "1. 在左侧选择要处理的功能页（照片 / PDF / 表格 / 文档）。\n"
     "2. 选择源文件夹，工具会自动扫描里面的文件。\n"
     "3. 设定命名规则（前缀 + 序号、按 Excel 对照表等）。\n"
     "4. 点「预览」核对新旧文件名，确认无误再「开始执行」。\n"
     "5. 输出默认隔离到新文件夹，绝不原地覆盖，可随时撤销。"),

    ("📷 照片命名", T.C_ACCENT,
     "支持「统一前缀 + 序号」与「按 Excel 对照表一一改名」两种模式；\n"
     "可选顺带压缩图片（1M / 500K / 200K），压不到再等比缩小分辨率；\n"
     "可保留 EXIF、自动备份原图。"),

    ("📕 PDF 命名", T.C_PURPLE,
     "按正文开头、统一前缀序号或 Excel 对照表批量改名；\n"
     "正文提取基于 pypdf，自动跳过加密 / 空文本文件并提示。"),

    ("📊 表格命名", T.C_INFO,
     "把一堆「新建 XLS 表.xlsx」按规则统一取名；\n"
     "支持 .xlsx / .xlsm / .xls / .csv，对照表同样支持这些格式。"),

    ("📄 文档命名", T.C_SUCCESS,
     "Word / PDF / TXT 取正文开头自动取名，再叠加前缀与序号规则。"),

    ("🏪 门店管理", T.C_TEXT_M,
     "本地 SQLite 维护门店档案（编号 / 名称 / 城市 / 地址 / 负责人 / 电话 / 备注）。\n"
     "· 新增 / 双击编辑 / 选中后删除；\n"
     "· 顶部搜索框按任意字段模糊筛选；\n"
     "· 「导入 Excel」批量录入（按门店编号查重，存在则更新）；\n"
     "· 「导出 Excel」备份全部档案。数据存于本机，不上传。"),

    ("☕ 赞助与支持", T.C_ACCENT,
     "如果这套工具帮到了你，欢迎在「赞助」页用微信 / 支付宝请作者喝杯咖啡。\n"
     "工具完全本地运行，您的文件与门店数据不会离开本机。"),
]


def _para(master: tk.Widget, text: str) -> None:
    vlabel(master, text, font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
           fg=T.C_TEXT_SUB, wrap="word").pack(fill=tk.X, pady=(0, T.S_SM))


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "使用帮助", "覆盖各功能页与门店管理的操作要点")

    for title, accent, text in _SECTIONS:
        card = Card(page, title, accent=accent)
        card.pack(fill=tk.X, pady=(0, T.S_MD))
        _para(card.body, text)
