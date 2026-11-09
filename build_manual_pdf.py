# -*- coding: utf-8 -*-
"""按 USER_MANUAL_PDF_SPEC.md 规范，由 USER_MANUAL.md 内容生成正式 PDF 使用手册。

路径 A：python-docx 生成 USER_MANUAL.docx -> Word COM(FileFormat=17) 转 PDF。
目录页码用 Word TOC 域，导出前调用 Fields.Update() 保证页码真实。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
DOCX = ROOT / "USER_MANUAL.docx"
PDF = DIST / "RenameMaster_使用手册.pdf"
HTML = ROOT / "USER_MANUAL.html"

DEEP_BLUE = "1F3864"
BLUE_LINE = "4472C4"
GRAY = "595959"
BLACK = "000000"
CN_FONT = "微软雅黑"
EN_FONT = "Arial"

PRODUCT = "重命名大师"
VERSION = "V1.11.0"
DATE_CN = "2026 年 11 月"
CONTENT_W = Cm(21 - 3 - 3)          # A4 宽 21cm - 左右各 3cm 页边距


# ---------------------------------------------------------------- 基础工具
def rgb(hex_color: str) -> RGBColor:
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16))


def _rfonts(rpr, ascii_font: str = EN_FONT, east_font: str = CN_FONT):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    rf.set(qn("w:ascii"), ascii_font)
    rf.set(qn("w:hAnsi"), ascii_font)
    rf.set(qn("w:eastAsia"), east_font)
    rf.set(qn("w:cs"), ascii_font)


def style_run(run, size=12, bold=False, color=BLACK, name=EN_FONT,
              east=CN_FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)
    run.font.name = name
    _rfonts(run._element.get_or_add_rPr(), name, east)
    return run


def set_style(doc, style_name, size, bold=False, color=BLACK):
    st = doc.styles[style_name]
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.color.rgb = rgb(color)
    st.font.name = EN_FONT
    _rfonts(st.element.get_or_add_rPr())


def para(doc, text="", size=12, bold=False, color=BLACK,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, space_before=0,
         line=1.5, indent=None, style=None):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = line
    if indent is not None:
        pf.left_indent = indent
    if text:
        style_run(p.add_run(text), size=size, bold=bold, color=color)
    return p


def heading(doc, text, level):
    """level: 1=章 16pt / 2=节 14pt / 3=小节 12pt（均为深蓝加粗）。"""
    conf = {1: ("Heading 1", 16, 18, 8), 2: ("Heading 2", 14, 14, 6),
            3: ("Heading 3", 12, 12, 4)}[level]
    style_name, size, before, after = conf
    p = doc.add_paragraph(style=style_name)
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.25
    pf.keep_with_next = True
    style_run(p.add_run(text), size=size, bold=True, color=DEEP_BLUE)
    return p


def bottom_line(p, width_cm=None, color=DEEP_BLUE, sz=12, space=2):
    """给段落加下边框当分隔线；width_cm 为空则整页宽。"""
    ppr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(sz))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    ppr.append(pbdr)
    if width_cm is not None:
        side = (15 - width_cm) / 2
        p.paragraph_format.left_indent = Cm(side)
        p.paragraph_format.right_indent = Cm(side)


def steps(doc, items, size=12):
    """数字编号操作步骤。"""
    for i, text in enumerate(items, 1):
        p = para(doc, f"{i}. {text}", size=size, space_after=4,
                 indent=Cm(0.6))
        p.paragraph_format.line_spacing = 1.5
    return doc


def bullets(doc, items, size=12):
    for text in items:
        p = para(doc, f"· {text}", size=size, space_after=4, indent=Cm(0.6))
        p.paragraph_format.line_spacing = 1.5
    return doc


# ---------------------------------------------------------------- 表格
def shade(cell, hex_color):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcpr.append(shd)


def grid_borders(table, color="9DB3D5", sz=6):
    tblpr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblpr.append(borders)


def add_table(doc, caption, header, rows, widths):
    """表上方居中标「表 N 表题」，表头蓝底白字，正文行白底黑字。"""
    cap = para(doc, caption, size=10.5, bold=True, color=DEEP_BLUE,
               align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4,
               space_before=6, line=1.0)
    cap.paragraph_format.keep_with_next = True

    table = doc.add_table(rows=1, cols=len(header))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tblpr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)
    grid_borders(table)

    hdr = table.rows[0]
    trpr = hdr._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trpr.append(th)
    for i, text in enumerate(header):
        cell = hdr.cells[i]
        cell.width = Cm(widths[i])
        shade(cell, DEEP_BLUE)
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        style_run(p.add_run(text), size=10.5, bold=True, color="FFFFFF")

    for row_data in rows:
        row = table.add_row()
        trpr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        for i, text in enumerate(row_data):
            cell = row.cells[i]
            cell.width = Cm(widths[i])
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.line_spacing = 1.0
            style_run(p.add_run(str(text)), size=10.5)
    return table


# ---------------------------------------------------------------- 页面
def setup_section(sec):
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(3)
    sec.right_margin = Cm(3)
    sec.header_distance = Cm(1.5)
    sec.footer_distance = Cm(1.5)


def build_cover(doc):
    sec = doc.sections[0]
    setup_section(sec)
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False      # 封面无页码

    # 顶部留白约 1/3 页高（内容区 24.7cm）
    spacer = para(doc, "", size=12, space_after=0, line=1.0)
    spacer.paragraph_format.space_before = Pt(0)
    spacer.add_run().add_break()
    for _ in range(6):
        para(doc, "", size=26, space_after=0, line=1.0)

    para(doc, "使 用 手 册", size=13, color=GRAY,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14, line=1.0)
    para(doc, f"{PRODUCT} 使用手册", size=26, bold=True, color=DEEP_BLUE,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10, line=1.0)
    para(doc, "本地运行的文件批量命名助手 · 照片 / PDF / 表格 / 文档一键整理",
         size=12, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER,
         space_after=16, line=1.0)

    line = para(doc, "", size=6, space_after=18, line=1.0)
    bottom_line(line, width_cm=6.0, color=DEEP_BLUE, sz=18)

    for text in (f"文档版本：{VERSION}",
                 "适用平台：Windows 10 / 11（64 位）",
                 f"编制日期：{DATE_CN}"):
        para(doc, text, size=12, color=GRAY,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6, line=1.0)


def build_toc(doc):
    para(doc, "目 录", size=16, bold=True, color=DEEP_BLUE,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8, line=1.0)
    line = para(doc, "", size=6, space_after=12, line=1.0)
    bottom_line(line, width_cm=3.0, color=DEEP_BLUE, sz=12)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    add_toc_field(p)


def add_toc_field(p, code=r' TOC \o "1-2" \h \z \u '):
    r = p.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "begin")
    r._r.append(fc)

    r = p.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = code
    r._r.append(it)

    r = p.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "separate")
    r._r.append(fc)

    r = p.add_run("（目录将在打开或打印时自动生成，请确保“更新域”已执行）")
    style_run(r, size=10.5, color=GRAY)

    r = p.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    r._r.append(fc)
    return p


def add_page_field(p):
    r = p.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "begin")
    r._r.append(fc)
    r = p.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " PAGE "
    r._r.append(it)
    r = p.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    r._r.append(fc)


def build_header_footer(sec):
    sec.header.is_linked_to_previous = False
    sec.footer.is_linked_to_previous = False

    hp = sec.header.paragraphs[0]
    hp.text = ""
    hp.paragraph_format.tab_stops.add_tab_stop(CONTENT_W,
                                               WD_TAB_ALIGNMENT.RIGHT)
    hp.paragraph_format.space_after = Pt(4)
    style_run(hp.add_run(f"{PRODUCT} 使用手册"), size=9, color=GRAY)
    style_run(hp.add_run("\t"), size=9, color=GRAY)
    style_run(hp.add_run(VERSION), size=9, color=GRAY)
    bottom_line(hp, color=BLUE_LINE, sz=6)

    fp = sec.footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(2)
    add_page_field(fp)
    for run in fp.runs:
        style_run(run, size=9, color=GRAY)


# ---------------------------------------------------------------- 正文
def build_body(doc):
    # ===== 第一章 软件简介 =====
    heading(doc, "第一章  软件简介", 1)
    heading(doc, "1.1  产品定位", 2)
    para(doc, "RenameMaster 是一款完全在本机运行的 Windows 桌面端「文件批量命名助手」，"
              "面向通信勘察、工程台账、日常办公等场景，解决照片、PDF、表格、文档批量改名、"
              "照片压缩到指定大小的问题。软件不联网、不上传、不收集数据，"
              "所有处理均在本机完成，可断网使用。")
    para(doc, "命名前先在预览表中列出「原文件名 → 新文件名 / 原大小 → 预计新大小 / 状态」，"
              "确认无误后才真正写盘；输出结果一律写入独立目录，源文件零改动。")

    heading(doc, "1.2  核心功能一览", 2)
    para(doc, "本版本提供的核心功能如表 1 所示。")
    add_table(doc, "表 1  核心功能一览",
              ["功能", "说明"],
              [["照片批量命名", "统一前缀 + 序号、Excel 对照表两种模式"],
               ["PDF 批量命名", "独立页，统一前缀 + 序号，可提取正文开头"],
               ["表格批量命名", ".xlsx / .xls / .csv，模式一 / 模式二"],
               ["文档批量命名", ".docx / .pdf / .txt，可提取正文开头作为文件名"],
               ["图片压缩", "1 MB / 500 KB / 200 KB / 100 KB / 自定义 KB"],
               ["命名高级功能", "命名变量、自定义排序、查找替换、撤销"],
               ["文字可复制", "界面文字可鼠标选中、Ctrl+C 或右键复制"]],
              [3.8, 11.2])

    heading(doc, "1.3  运行环境", 2)
    para(doc, "软件对硬件无特殊要求，运行环境如表 2 所示。")
    add_table(doc, "表 2  运行环境要求",
              ["项目", "要求"],
              [["操作系统", "Windows 10 / 11（64 位）"],
               ["内存", "4 GB 及以上"],
               ["运行依赖", "免安装 EXE 或安装包，双击即用，无需 Python"],
               ["源码运行依赖", "Python 3.11+，Pillow、openpyxl、python-docx、pypdf、"
                "tkinterdnd2"],
               ["显示", "建议 1366×768 及以上，支持 100%~200% DPI"]],
              [3.8, 11.2])

    # ===== 第二章 安装与启动 =====
    heading(doc, "第二章  安装与启动", 1)
    heading(doc, "2.1  安装包方式（推荐）", 2)
    steps(doc, [
        "双击 RenameMaster_Setup.exe，按向导安装，可勾选「创建桌面快捷方式」。",
        "从开始菜单或桌面双击「重命名大师」启动。",
        "卸载：设置 → 应用 → 重命名大师 → 卸载，会一并清理 %APPDATA%\\RenameMaster。",
    ])

    heading(doc, "2.2  免安装版", 2)
    steps(doc, [
        "把 RenameMaster.exe 复制到任意目录，双击即可启动；也可解压带版本号的 "
        "RenameMaster_*_Portable.zip 免安装压缩包（内含使用说明）。",
        "首次若被 SmartScreen 拦截，点「更多信息」→「仍要运行」（未做代码签名，属正常）。",
        "杀毒软件若提示风险，为 PyInstaller 单文件 EXE 常见误报，加入信任即可。",
    ])

    heading(doc, "2.3  源码方式运行", 2)
    para(doc, "需要二次开发时，可用源码方式启动：")
    code_lines = ["cd D:\\Desktop\\SD\\13.Rename\\src",
                  "pip install -r ..\\requirements.txt",
                  "python -m rename_master.main",
                  "python ..\\tests\\smoke.py        :: 输出 SMOKE OK 即通过"]
    for text in code_lines:
        p = para(doc, text, size=11, space_after=2, indent=Cm(0.8), line=1.2)
        style_run(p.runs[0], size=11, color="1F3864")

    heading(doc, "2.4  界面总览", 2)
    para(doc, "启动后为主窗口布局，左侧导航各功能页如表 3 所示。")
    add_table(doc, "表 3  左侧导航说明",
              ["导航项", "功能"],
              [["首页", "产品介绍 + 4 个功能入口"],
               ["照片命名", "照片批量改名 + 压缩"],
               ["PDF 命名", "PDF 批量改名"],
               ["表格命名", "表格批量改名"],
               ["文档命名", "文档批量改名"],
               ["关于", "版本号、技术栈、赞助"]],
              [3.8, 11.2])

    heading(doc, "2.5  配置文件", 2)
    bullets(doc, [
        "配置文件：%APPDATA%\\RenameMaster\\config.json，保存最近目录、压缩档位等；"
        "删除该文件即可恢复默认。",
    ])

    # ===== 第三章 快速上手 =====
    heading(doc, "第三章  快速上手", 1)
    heading(doc, "3.1  五步跑通照片批量改名", 2)
    steps(doc, [
        "左侧导航点「照片命名」。",
        "① 选择文件：点「选择文件夹」或「添加文件」，也可直接拖入文件夹。",
        "② 命名模式：选模式一，填基础名称（如 曲靖巡检），调整位数、起始、分隔符。",
        "③ 压缩档位：选 500 KB（或 1M / 200K / 100K / 自定义）。",
        "④ 输出位置：点「开始执行」，预览表核对无误后确认执行。",
    ])
    para(doc, "执行过程中可随时点「取消」中断；完成后弹窗提示成功与失败数量。")

    heading(doc, "3.2  输入输出示例", 2)
    para(doc, "常见文件的改名效果示例如表 4 所示。")
    add_table(doc, "表 4  改名效果示例",
              ["类型", "原文件名", "新文件名", "处理"],
              [["照片", "IMG_20260101.jpg", "曲靖巡检_001.jpg", "改名 + 压缩 500 KB"],
               ["PDF", "scan01.pdf", "巡检报告_001.pdf", "仅改名"],
               ["表格", "新建 XLS 工作表.xlsx", "台账_001.xlsx", "仅改名"],
               ["文档", "文档1.docx", "2026年10月巡检现场情况说明.docx", "仅改名"]],
              [1.8, 4.4, 6.0, 2.8])

    # ===== 第四章 功能详解 =====
    heading(doc, "第四章  功能详解", 1)
    heading(doc, "4.1  照片批量命名", 2)
    para(doc, "支持格式：jpg / jpeg / png / bmp / heic（HEIC 的压缩与尺寸读取"
              "取决于本机解码支持）。")

    heading(doc, "4.1.1  模式一：统一前缀 + 序号", 3)
    add_table(doc, "表 5  模式一参数说明",
              ["参数", "说明", "默认值"],
              [["基础名称", "新文件名的公共前缀，如「曲靖巡检」", "照片"],
               ["位数", "序号位数：3 / 4 / 5", "3"],
               ["起始", "第一个文件的序号起始值", "1"],
               ["分隔符", "前缀与序号之间：_ / - / 空格 / 空", "_"],
               ["扩展名", "始终跟随源文件的扩展名；压缩导致格式变化时自动同步",
                "自动"]],
              [3.0, 9.0, 3.0])

    heading(doc, "4.1.2  模式二：Excel 对照表", 3)
    steps(doc, [
        "选模式二后，点「一键提取文件名」导出当前文件清单为 Excel 模板。",
        "在模板「新文件名」列填好新名，再点「导入对照表」。",
        "也可直接导入现成 Excel / CSV，或导出当前对照表。",
        "重名 / 未匹配行自动标色，确认后预览执行。",
    ])
    para(doc, "重复判定基于最终完整文件名：新名不带扩展名也不会误判；"
              "真正重复的行会被标红禁止。")

    heading(doc, "4.1.3  压缩到指定大小", 3)
    add_table(doc, "表 6  压缩档位与适用场景",
              ["档位", "适用场景"],
              [["不压缩", "只改名，原样复制"],
               ["1 MB", "存档、原始留底"],
               ["500 KB", "OA / 监理系统上传"],
               ["200 KB", "微信、钉钉发送"],
               ["100 KB", "极小体积、批量预览"],
               ["自定义", "填写具体 KB"]],
              [3.6, 11.4])
    para(doc, "二分法调整 JPEG quality，压不到再等比缩分辨率；PNG 压缩后若实际变为 "
              "JPEG，扩展名会自动同步。")

    heading(doc, "4.1.4  预览与执行", 3)
    add_table(doc, "表 7  预览状态说明",
              ["状态", "含义", "处理"],
              [["√ 正常", "可正常改名 / 压缩", "正常执行"],
               ["△ 注意", "含非法字符、格式变更等已自动处理", "标黄后执行"],
               ["× 禁止", "目标文件名重复、超长等", "标红，执行时跳过"]],
              [2.8, 8.2, 4.0])
    para(doc, "文件名超 255 字符或含非法字符时，预览阶段即提示，不会等到写盘才报错。")

    heading(doc, "4.2  PDF 批量命名", 2)
    bullets(doc, [
        "模式一：统一前缀 + 序号；勾选「提取正文开头」可按第 1 页内容命名。",
        "模式二：Excel 对照表，支持一键提取文件名、导入、导出。",
    ])

    heading(doc, "4.3  表格批量命名", 2)
    bullets(doc, [
        "支持 .xlsx / .xls / .csv，模式一 / 模式二操作同照片页。",
        "仅改名，不做压缩、不改动内容。",
    ])

    heading(doc, "4.4  文档批量命名", 2)
    bullets(doc, [
        "支持 .docx / .pdf / .txt，提取正文开头作为新文件名，可配字数。",
        "可叠加固定前缀 + 序号；扫描件（无文字层）会保留原名并标注。",
    ])

    heading(doc, "4.5  高级选项（折叠，默认收起）", 2)
    bullets(doc, [
        "命名变量：{date} 今天、{mtime} 修改时间、{exif} 拍摄时间、"
        "{parent} 父文件夹、{stem} 原名。",
        "自定义排序：按文件名 / 大小 / 修改时间，升序 / 降序，决定序号顺序。",
        "查找替换：普通文本或正则批量替换，非法正则安全降级。",
        "排序与查找替换合并在同一行，展开卡片即可一次性设置。",
    ])

    heading(doc, "4.6  撤销", 2)
    para(doc, "每次执行记录产物，可点「撤销上次操作」（跨重启），删除生成物并清理空目录。")

    heading(doc, "4.7  文字复制", 2)
    para(doc, "界面标题、说明、标签、表格表头均可鼠标拖选，Ctrl+C 复制或右键复制；"
              "只读文字采用白名单，不会被键盘误删、粘贴或修改。")

    heading(doc, "4.8  文件列表右键删除", 2)
    bullets(doc, [
        "在「① 选择文件」列表里右键某一行，会自动选中该行；点菜单里的"
        "「删除此文件」即可把它移出待改名列表。",
        "按住 Ctrl 右键可多选，菜单显示「删除选中文件（N）」批量移除；"
        "右键空白处时删除项不可用。",
        "删除只移出列表，不删除磁盘上的原文件，也不影响其它已加入的文件。",
    ])

    # ===== 第五章 FAQ =====
    heading(doc, "第五章  常见问题（FAQ）", 1)
    para(doc, "使用过程中最常见的问题、成因与解决办法如表 8 所示。")
    add_table(doc, "表 8  常见问题排查表",
              ["问题", "原因", "解决办法"],
              [["原文件会被覆盖吗？", "输出目录隔离",
                "不会，输出到新目录，源文件零改动；同名自动加后缀。"],
               ["文件名过长报错？", "Windows 上限 255 字符",
                "缩短基础名即可，预览阶段即提示。"],
               ["压缩后图片模糊吗？", "优先调 JPEG 质量",
                "先调质量（肉眼几乎无差），压不到才缩分辨率。"],
               ["界面文字能复制吗？", "文字控件支持选中",
                "鼠标拖选 + Ctrl+C 或右键复制；只读文字不会被误改。"],
               ["杀毒软件报毒？", "未做代码签名",
                "PyInstaller EXE 偶被误报，加入信任即可。"],
               ["配置在哪？如何恢复？", "配置写在应用数据目录",
                "%APPDATA%\\RenameMaster\\config.json，删除即恢复默认。"],
               ["执行中途想停止？", "后台线程支持取消",
                "点「取消」；已写入的保留，未处理的不再继续。"],
               ["右键删除会删掉原文件吗？", "仅移除列表项",
                "不会，只把该行移出待改名列表，磁盘文件保持原样。"]],
              [3.8, 4.2, 7.0])

    # ===== 第六章 数据与隐私 =====
    heading(doc, "第六章  数据与隐私", 1)
    bullets(doc, [
        "纯本地运行：不联网、不上传、不收集任何数据，可断网使用。",
        "所有文件处理都在本机内存与磁盘完成，无任何外部通信。",
        "原文件零改动：输出统一写入「<源目录>_重命名输出」，绝不原地覆盖。",
        "本机配置：仅 %APPDATA%\\RenameMaster\\config.json 一处，"
        "记录目录与选项偏好，删除即恢复默认。",
        "运行日志：仅记录文件名与处理结果，不含文件内容。",
    ])

    # ===== 第七章 版本与支持 =====
    heading(doc, "第七章  版本与支持", 1)
    heading(doc, "7.1  版本记录", 2)
    add_table(doc, "表 9  版本记录",
              ["版本", "日期", "变更内容"],
              [["V1.0", "2026-10-12", "照片 / 表格 / 文档命名、图片压缩、预览、输出隔离"],
               ["V1.1", "2026-10-12", "命名变量、自定义排序、查找替换、撤销"],
               ["V1.2", "2026-10-13", "独立水印页：可见水印 + 盲水印"],
               ["V1.3", "2026-10-13", "高级选项折叠、首页 5 入口、文字可复制"],
               ["V1.4", "2026-10-14", "独立测试修复 10 项缺陷，平铺水印约 200 倍性能提升、预览异步"],
               ["V1.5", "2026-10-14", "统一修复全部预览/执行弹窗：加大居中、水平滚动看全长文件名、按钮栏固定不挤压，按钮统一改名预览"],
               ["V1.6", "2026-10-14", "双 AI 协作复核：水印引擎与预览弹窗缺陷修复"],
               ["V1.7", "2026-10-14", "水印页 4 布局卡片 / 9 位置九宫格 / 真色块色板，弹窗统一尺寸，表格撑满窗口"],
               ["V1.8", "2026-10-15", "平铺密度走错分支、切页操作栏销毁崩溃、盲水印提取多余建目录三项修复"],
               ["V1.9", "2026-10-15", "全维度深度测试：重名与保留名保护、输出不再覆盖源文件、竖拍照片按 EXIF 转正、日志不可写不闪退、界面布局与交互优化"],
               ["V1.10", "2026-10-15", "「添加水印」功能整体剥离至独立软件「水印助手」，清理相关依赖与界面入口；同步回归命名与压缩全部用例"],
               ["V1.10.1", "2026-10-15", "表格列宽改为按内容自适应并铺满界面：勾选列不再被拉伸留白，文件名列吸收多余宽度"],
               ["V1.10.1", "2026-10-18", "软件名中文化（窗口/关于页/快捷方式统一显示「重命名大师」）；图标重做为苹果风格透明底无白边；体积优化为 EXE 27.9 MB / Setup 29.6 MB"],
               ["V1.10.2", "2026-11-05",
                "文件列表支持右键删除单条 / 多选（仅移除列表）；高级选项排序与查找替换"
                "合并为一行；界面视觉规范统一与孤行控制；修复查找替换路径越界、非图片"
                "扩展名被误改、预览输出目录快照、后台线程异常卡死等缺陷；剥离 numpy / "
                "fontTools 等可选依赖，EXE 29.5 MB 降至 18.3 MB、安装包 31.2 MB 降至 20.0 MB"]],
              [2.0, 2.4, 10.6])
    para(doc, "说明：V1.2~V1.9 中的「添加水印」功能已在 V1.10 整体剥离，"
              "后续由独立软件「水印助手」提供，RenameMaster 不再包含水印相关功能。",
         size=10.5, color=GRAY)
    heading(doc, "7.2  交付物", 2)
    bullets(doc, [
        "dist\\RenameMaster.exe：免安装单文件（约 18.3 MB）。",
        "dist\\RenameMaster_*_Portable.zip：免安装压缩包（约 18.0 MB，内含使用说明）。",
        "dist\\RenameMaster_Setup.exe：Inno 安装包（约 20.0 MB）。",
        "dist\\RenameMaster_使用手册.pdf：本手册。",
        "更新方式：替换 dist 目录下对应文件即可。",
    ])


# ---------------------------------------------------------------- 生成
def build_docx() -> Path:
    doc = Document()

    normal = doc.styles["Normal"]
    normal.font.size = Pt(12)
    normal.font.name = EN_FONT
    normal.font.color.rgb = rgb(BLACK)
    _rfonts(normal.element.get_or_add_rPr())
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    set_style(doc, "Heading 1", 16, True, DEEP_BLUE)
    set_style(doc, "Heading 2", 14, True, DEEP_BLUE)
    set_style(doc, "Heading 3", 12, True, DEEP_BLUE)

    build_cover(doc)
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(sec)
    build_header_footer(sec)
    build_toc(doc)

    doc.add_section(WD_SECTION.NEW_PAGE)
    build_body(doc)

    doc.save(str(DOCX))
    return DOCX


def docx_to_pdf_com(docx_path: Path, pdf_path: Path) -> bool:
    """路径 A：Word COM 转 PDF（FileFormat=17 = wdFormatPDF）。"""
    try:
        import win32com.client as win32
    except Exception:                              # noqa: BLE001
        return False
    word = None
    try:
        word = win32.DispatchEx("Word.Application")   # 新实例，避免复用僵死进程
        word.Visible = False
        doc = word.Documents.Open(str(docx_path), ReadOnly=True)
        # 目录域必须先更新，页码才与正文真实对应
        try:
            if doc.TablesOfContents.Count:
                doc.TablesOfContents(1).Update()
        except Exception:                          # noqa: BLE001
            pass
        try:
            doc.Fields.Update()
        except Exception:                          # noqa: BLE001
            pass
        doc.SaveAs(str(pdf_path), FileFormat=17)
        doc.Close(False)
        return pdf_path.exists()
    except Exception as exc:                       # noqa: BLE001
        print(f"[warn] Word COM 转换失败：{exc}")
        return False
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:                      # noqa: BLE001
                pass


def docx_to_pdf_edge(docx_path: Path, pdf_path: Path) -> bool:
    """路径 B：docx → HTML → Edge headless 打印 PDF（win32com 不可用时的备选）。"""
    HTML.write_text(build_html(), encoding="utf-8")
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    tmp = pdf_path.with_name("_manual_tmp.pdf")     # 中文名走临时英文名再改名
    if tmp.exists():
        tmp.unlink()
    cmd = [edge, "--headless", "--disable-gpu",
           f"--print-to-pdf={tmp}", "--no-pdf-header-footer", str(HTML)]
    subprocess.run(cmd, check=False, timeout=180)
    if tmp.exists():
        if pdf_path.exists():
            pdf_path.unlink()
        tmp.replace(pdf_path)
    return pdf_path.exists()


CSS = """
@page { size: A4 portrait; margin: 25mm 30mm; }
body { font-family: "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
       font-size: 12pt; color: #000; line-height: 1.5; }
h1 { font-size: 16pt; font-weight: bold; color: #1F3864;
     margin: 18pt 0 8pt; }
h2 { font-size: 14pt; font-weight: bold; color: #1F3864;
     margin: 14pt 0 6pt; }
h3 { font-size: 12pt; font-weight: bold; color: #1F3864;
     margin: 12pt 0 4pt; }
p { margin: 0 0 6pt; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 12pt;
        font-size: 10.5pt; }
th { background: #1F3864; color: #fff; font-weight: bold; }
th, td { border: 1px solid #9DB3D5; padding: 4pt 6pt; }
.cover { text-align: center; padding-top: 33%; page-break-after: always; }
.cover .label { font-size: 13pt; color: #595959; letter-spacing: 4px; }
.cover h1 { font-size: 26pt; }
.cover .rule { width: 40%; margin: 16pt auto; border-bottom: 2.25pt solid
               #1F3864; }
.cover .info { font-size: 12pt; color: #595959; }
"""


def build_html() -> str:
    doc = Document(str(DOCX))
    parts = [f"<!doctype html><html><head><meta charset='utf-8'>"
             f"<style>{CSS}</style></head><body>"]
    parts.append("<div class='cover'><div class='label'>使 用 手 册</div>"
                 f"<h1>{PRODUCT} 使用手册</h1>"
                 "<div class='rule'></div>"
                 f"<div class='info'>文档版本：{VERSION}<br>"
                 f"适用平台：Windows 10 / 11（64 位）<br>"
                 f"编制日期：{DATE_CN}</div></div>")
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        if p.style.name == "Heading 1":
            parts.append(f"<h1>{text}</h1>")
        elif p.style.name == "Heading 2":
            parts.append(f"<h2>{text}</h2>")
        elif p.style.name == "Heading 3":
            parts.append(f"<h3>{text}</h3>")
        else:
            parts.append(f"<p>{text}</p>")
    for table in doc.tables:
        parts.append("<table><tr>")
        for cell in table.rows[0].cells:
            parts.append(f"<th>{cell.text}</th>")
        parts.append("</tr>")
        for row in table.rows[1:]:
            parts.append("<tr>")
            for cell in row.cells:
                parts.append(f"<td>{cell.text}</td>")
            parts.append("</tr>")
        parts.append("</table>")
    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    docx_path = build_docx()
    print(f"[ok] docx -> {docx_path}")

    ok = docx_to_pdf_com(docx_path, PDF)
    if ok:
        print(f"[ok] pdf  -> {PDF}（Word COM, FileFormat=17）")
    else:
        print("[info] win32com 不可用，改用路径 B：Edge headless 打印")
        ok = docx_to_pdf_edge(docx_path, PDF)
        print(f"[ok] pdf  -> {PDF}（Edge headless）" if ok
              else f"[fail] PDF 生成失败：{PDF}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
