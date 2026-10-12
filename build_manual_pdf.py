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

PRODUCT = "RenameMaster"
VERSION = "V1.0"
DATE_CN = "2026 年 10 月"
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
    para(doc, "本地运行的文件批量命名助手 · 照片 / 表格 / 文档一键整理",
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
              "面向通信勘察、工程台账、日常办公等场景，解决照片、表格、文档批量改名 "
              "以及照片压缩到指定大小的问题。软件不联网、不上传、不收集任何数据，"
              "所有处理均在本机完成，可断网使用。")
    para(doc, "命名前先在预览表中列出「原文件名 → 新文件名 / 原大小 → 预计新大小 / 状态」，"
              "确认无误后才真正写盘；输出结果一律写入独立目录，源文件零改动。")

    heading(doc, "1.2  核心功能一览", 2)
    para(doc, "本版本提供的核心功能如表 1 所示。")
    add_table(doc, "表 1  核心功能一览",
              ["功能", "说明"],
              [["照片批量命名", "统一前缀 + 序号、Excel 对照表一一对应两种模式"],
               ["图片压缩", "1 MB / 500 KB / 200 KB / 100 KB / 自定义 KB 五档"],
               ["照片水印", "压缩后叠加半透明白色文字，5 种位置、3 档字号（v1.0 新增）"],
               ["表格批量命名", ".xlsx / .xls / .csv 按「前缀 + 序号」规则批量改名"],
               ["文档批量命名", ".docx / .pdf / .txt / .md，可提取正文开头作为文件名"],
               ["输出隔离", "统一输出到「<源目录>_重命名输出」，绝不原地覆盖"],
               ["执行前预览", "预览表确认后才写盘，冲突行标红跳过"],
               ["后台执行", "后台线程处理，进度条 + 取消按钮，界面不冻结"]],
              [3.6, 11.4])

    heading(doc, "1.3  运行环境", 2)
    para(doc, "软件对硬件无特殊要求，运行环境如表 2 所示。")
    add_table(doc, "表 2  运行环境要求",
              ["项目", "要求"],
              [["操作系统", "Windows 10 / 11（64 位）"],
               ["内存", "4 GB 及以上"],
               ["运行依赖", "免安装 EXE，双击即用，无需 Python 环境"],
               ["源码运行依赖", "Python 3.11+ 及 Pillow、openpyxl、python-docx、pypdf"],
               ["显示", "建议 1366×768 及以上，支持 100%~200% DPI 缩放"]],
              [3.6, 11.4])

    # ===== 第二章 安装与启动 =====
    heading(doc, "第二章  安装与启动", 1)
    heading(doc, "2.1  免安装版（推荐）", 2)
    steps(doc, [
        "把 RenameMaster.exe 复制到任意目录（建议 D:\\Tools\\RenameMaster\\）。",
        "双击 RenameMaster.exe 即可启动，无需安装、无需管理员权限。",
        "首次启动若被 Windows SmartScreen 拦截，点「更多信息」→「仍要运行」即可。"
        "本软件未做代码签名，属正常现象。",
    ])
    para(doc, "若杀毒软件提示风险，亦为 PyInstaller 打包的单文件 EXE 常见误报，"
              "加入信任列表即可。")

    heading(doc, "2.2  源码方式运行", 2)
    para(doc, "需要在本地修改或二次开发时，可用源码方式启动：")
    code_lines = ["cd D:\\Desktop\\SD\\13.Rename\\src",
                  "pip install -r ..\\requirements.txt",
                  "python -m rename_master.main",
                  "python ..\\tests\\smoke.py        :: 输出 SMOKE OK 即通过"]
    for text in code_lines:
        p = para(doc, text, size=11, space_after=2, indent=Cm(0.8), line=1.2)
        style_run(p.runs[0], size=11, color="1F3864")

    heading(doc, "2.3  界面总览", 2)
    para(doc, "启动后为主窗口布局，各区域职责如表 3 所示。")
    add_table(doc, "表 3  界面区域说明",
              ["区域", "说明"],
              [["① 左侧导航", "首页 / 照片命名 / 表格命名 / 文档命名 / 关于"],
               ["② 页面标题区", "大标题 + 副标题 + 彩色分隔线"],
               ["③ 功能卡片区", "① 选择文件 → ② 命名模式 → ③ 压缩 → ④ 水印 → ⑤ 输出位置"],
               ["④ 底部操作栏", "预览改名结果 / 开始执行 / 取消 / 进度条"],
               ["⑤ 状态栏", "窗口底部实时状态与结果提示"]],
              [3.6, 11.4])

    heading(doc, "2.4  配置文件与日志", 2)
    bullets(doc, [
        "配置文件：%APPDATA%\\RenameMaster\\config.json，保存最近使用的目录、"
        "上次选择的压缩档位、水印文字等；删除该文件即可恢复默认设置。",
        "运行日志：logs\\rename_YYYYMMDD.log，按天记录每次执行的文件与结果。",
    ])

    # ===== 第三章 快速上手 =====
    heading(doc, "第三章  快速上手", 1)
    heading(doc, "3.1  五步跑通照片批量改名", 2)
    steps(doc, [
        "启动软件，在左侧导航点「照片命名」。",
        "① 选择文件：点「选择文件夹」指定源目录，或点「添加文件」多选照片；"
        "也可直接从资源管理器把文件夹拖入窗口。",
        "② 命名模式：选「模式一：统一前缀+序号」，填写「基础名称」（如 曲靖巡检），"
        "按需调整位数、起始、分隔符，并勾选「保留扩展名」。",
        "③ 压缩到指定大小：选 500 KB（或 1 MB / 200 KB / 100 KB / 自定义）；"
        "如需水印，在 ④ 卡片勾选「添加水印文字」并填写文字、位置、字号。",
        "⑤ 输出位置：确认默认输出目录后，点底部「开始执行」，"
        "在弹出的预览表中核对无误，再点「确认执行」。",
    ])
    para(doc, "执行过程中可随时点「取消」中断；完成后弹窗提示成功与失败数量，"
              "并给出输出目录路径。")

    heading(doc, "3.2  输入输出示例", 2)
    para(doc, "常见文件的改名效果示例如表 4 所示。")
    add_table(doc, "表 4  改名效果示例",
              ["类型", "原文件名", "新文件名", "处理"],
              [["照片", "IMG_20260101.jpg", "曲靖巡检_001.jpg", "改名 + 压缩 500 KB"],
               ["照片", "DSC_001.jpg", "曲靖巡检_002.jpg", "改名 + 压缩 500 KB + 水印"],
               ["表格", "新建 XLS 工作表.xlsx", "台账_001.xlsx", "仅改名"],
               ["文档", "文档1.docx", "2026年10月巡检现场情况说明.docx", "仅改名"]],
              [1.8, 4.4, 6.0, 2.8])

    # ===== 第四章 功能详解 =====
    heading(doc, "第四章  功能详解", 1)
    heading(doc, "4.1  照片批量命名", 2)
    para(doc, "支持格式：jpg / jpeg / png / bmp / heic。页面由「① 选择文件、"
              "② 命名模式、③ 压缩到指定大小、④ 水印（可选）、⑤ 输出位置」"
              "五张卡片组成。")

    heading(doc, "4.1.1  模式一：统一前缀 + 序号", 3)
    para(doc, "适用于把一堆乱名照片（IMG_20260101.jpg、DSC_001.jpg …）统一改成"
              "「曲靖巡检_001.jpg、曲靖巡检_002.jpg …」。参数说明如表 5 所示。")
    add_table(doc, "表 5  模式一参数说明",
              ["参数", "说明", "默认值"],
              [["基础名称", "新文件名的公共前缀，如「曲靖巡检」", "照片"],
               ["位数", "序号位数：3 / 4 / 5", "3"],
               ["起始", "第一个文件的序号起始值", "1"],
               ["分隔符", "前缀与序号之间的连接符：_ / - / 空格 / 空", "_"],
               ["保留扩展名", "勾选后保留原扩展名（推荐）", "勾选"]],
              [3.0, 9.0, 3.0])
    para(doc, "示例：基础名称 = 曲靖巡检、位数 = 3、起始 = 1、分隔符 = _，"
              "则输出为 曲靖巡检_001.jpg、曲靖巡检_002.jpg …，"
              "序号按文件列表顺序递增。")

    heading(doc, "4.1.2  模式二：Excel 对照表一一对应", 3)
    steps(doc, [
        "① 选择文件：指定照片源目录。",
        "② 命名模式：选「模式二：一一对照（Excel）」。",
        "点「从 Excel 导入」选择对照表文件（.xlsx / .xls / .csv）。",
        "在卡片内的对照表中核对「原文件名 → 新文件名」，"
        "确认无误后点「预览改名结果」。",
        "在预览弹窗点「确认执行」。",
    ])
    para(doc, "对照表规则：第 1 列为原文件名、第 2 列为新文件名；未匹配到的文件保持原名；"
              "解析失败会弹出错误提示，不会误改任何文件。")

    heading(doc, "4.1.3  压缩到指定大小", 3)
    para(doc, "各档位与适用场景如表 6 所示。")
    add_table(doc, "表 6  压缩档位与适用场景",
              ["档位", "适用场景"],
              [["不压缩", "原样复制到输出目录，只改名"],
               ["1 MB", "存档、原始留底"],
               ["500 KB", "OA / 监理系统等上传限制"],
               ["200 KB", "微信、钉钉发送"],
               ["100 KB", "极小体积、批量预览"],
               ["自定义", "在输入框中填写具体 KB 数值"]],
              [3.6, 11.4])
    para(doc, "压缩原理：用二分法调整 JPEG quality（1~95），压不到目标大小再等比缩小分辨率，"
              "保证最终文件不大于目标大小。勾选「保留 EXIF」可在压缩后保留拍摄参数等信息。")

    heading(doc, "4.1.4  照片水印（v1.0 新增）", 3)
    para(doc, "水印卡片默认关闭，勾选「添加水印文字」后启用；"
              "启用后会在压缩完成之后为每张照片叠加半透明白色文字，"
              "适合给现场照片标注地点、日期或班组。参数说明如表 7 所示。")
    add_table(doc, "表 7  水印参数说明",
              ["参数", "说明", "默认值"],
              [["水印文字", "叠加的文字内容，如「曲靖联通 2026-10-12」", "空（不加水印）"],
               ["位置", "右下角 / 左下角 / 右上角 / 左上角 / 底部居中", "右下角"],
               ["字号", "小（短边×1.2%）/ 中（短边×2.0%）/ 大（短边×3.5%）", "中"]],
              [2.6, 9.4, 3.0])
    bullets(doc, [
        "水印为白色半透明文字（不透明度 40%），距图片边缘的距离等于字号，"
        "字号随图片短边自适应，不同尺寸照片观感一致。",
        "执行顺序为「先压缩、后加水印」，避免水印被二次压缩糊掉；"
        "未开启压缩时也可单独加水印。",
        "水印文字为空或仅空白时，原样输出，不加水印。",
        "全程在内存中完成，不落盘、不改动原图；输出统一为 JPEG（quality=95）。",
        "若透明图（PNG）参与处理，会先合成到白底，避免转 JPEG 后透明区变黑。",
    ])

    heading(doc, "4.1.5  预览确认与执行", 3)
    para(doc, "点「开始执行」后会先弹出预览表，列出"
              "「原文件名 / 新文件名 / 原大小 / 预计新大小 / 状态」。"
              "状态含义如表 8 所示。")
    add_table(doc, "表 8  预览状态说明",
              ["状态", "含义", "处理方式"],
              [["√ 正常", "可正常改名 / 压缩", "正常执行"],
               ["△ 注意", "文件名含非法字符等，已自动处理", "标黄提示后执行"],
               ["× 禁止", "目标文件名冲突或无法写入", "标红，执行时跳过"]],
              [2.8, 8.2, 4.0])
    para(doc, "预览表中文件名若含 \\ / : * ? \" < > | 等非法字符，"
              "程序会自动替换为下划线 _，并在预览表中标黄提示。")

    heading(doc, "4.2  表格批量命名", 2)
    para(doc, "适用于把一批表格文件（.xlsx / .xls / .csv）按规则批量改名，"
              "例如把「新建 XLS 工作表.xlsx」改成「台账_001.xlsx」。")
    steps(doc, [
        "左侧导航点「表格命名」，在 ① 选择文件 中指定源目录或添加文件。",
        "在 ② 命名规则 中选择「统一前缀 + 序号」，"
        "可设置位数 / 起始号 / 分隔符。",
        "在 ③ 输出位置 中确认输出目录。",
        "点底部「预览改名结果」核对，再点「开始执行」并确认。",
    ])
    para(doc, "表格页不做压缩与水印处理，仅执行改名，源文件保持零改动。")

    heading(doc, "4.3  文档批量命名", 2)
    para(doc, "适用于把一堆无意义命名的 Word / PDF / TXT / Markdown 文档，"
              "按内容自动命名。支持格式：.docx / .pdf / .txt / .md。")
    bullets(doc, [
        "命名规则为「前缀 + 正文开头 + 序号」，三项可自由叠加，按需勾选。",
        "正文提取规则：.docx 取正文前 30 个字符，.pdf 取第 1 页前 30 个字符，"
        ".txt / .md 取前 30 个字符。",
        "提取到的正文会自动去除换行、多余空格与文件名非法字符。",
        "可在前缀框中填写固定前缀，如「巡检报告_」。",
    ])
    add_table(doc, "表 9  文档命名规则示例",
              ["规则", "原文件名", "新文件名"],
              [["仅正文开头", "文档1.docx", "2026年10月巡检现场情况说明.docx"],
               ["前缀 + 正文开头", "新建文本文档.txt", "巡检报告_会议纪要要点.txt"],
               ["前缀 + 序号", "未命名.md", "说明文档_003.md"]],
              [3.2, 4.6, 7.2])
    para(doc, "PDF 正文提取依赖 pypdf；若 PDF 为扫描件（无文字层），"
              "提取结果可能为空，此时会保留原文件名并在预览表中标注。")

    heading(doc, "4.4  首页与关于页", 2)
    bullets(doc, [
        "首页：三张功能卡片（照片命名 / 表格命名 / 文档命名），点击直接进入对应功能页；"
        "下方「最近使用」记录最近处理的目录。",
        "关于页：查看版本号、功能特性与技术栈说明。",
    ])

    # ===== 第五章 FAQ =====
    heading(doc, "第五章  常见问题（FAQ）", 1)
    para(doc, "使用过程中最常见的问题、成因与解决办法如表 10 所示。")
    add_table(doc, "表 10  常见问题排查表",
              ["问题", "原因", "解决办法"],
              [["原文件会被覆盖吗？", "程序采用输出目录隔离设计",
                "不会。所有输出写到新目录，原文件零改动。"],
               ["文件名里有非法字符（\\ / : * ? \" < > |）怎么办？",
                "Windows 文件名不允许这些字符",
                "自动替换为下划线 _，预览表中标黄提示。"],
               ["压缩后图片会模糊吗？", "二分法优先调整 JPEG 质量",
                "先调质量（肉眼几乎无差），压不到才等比缩分辨率。"],
               ["支持哪些图片格式？", "扫描器按扩展名白名单过滤",
                "jpg / jpeg / png / bmp / heic。"],
               ["压缩档位怎么选？", "不同渠道的大小限制不同",
                "微信发图选 200 KB，邮件附件选 500 KB，存档选 1 MB。"],
               ["加了水印想去掉怎么办？", "水印已直接写入输出图片",
                "取消勾选「添加水印文字」后重新执行一次；原图始终未改动。"],
               ["水印太淡或太大看不清？", "字号按图片短边比例自适应",
                "把「字号」调为「大」，或换到对比度更高的位置。"],
               ["杀毒软件报毒？", "程序未做代码签名",
                "PyInstaller 打包的 EXE 偶被误报，加入信任即可。"],
               ["配置存在哪里？如何恢复默认？", "配置写在系统应用数据目录",
                "%APPDATA%\\RenameMaster\\config.json，删除即恢复默认。"],
               ["执行中途想停止？", "后台线程支持取消",
                "点底部「取消」；已写入的文件保留，未处理的不再继续。"],
               ["想查看历史执行记录？", "日志按天写入",
                "查看 logs\\rename_YYYYMMDD.log。"]],
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
    add_table(doc, "表 11  版本记录",
              ["版本", "日期", "变更内容"],
              [["V1.0", "2026-10-12",
                "首个正式版本：照片 / 表格 / 文档批量命名、图片压缩到指定大小、"
                "照片水印、执行前预览、输出目录隔离"]],
              [2.2, 2.8, 10.0])
    heading(doc, "7.2  支持与反馈", 2)
    bullets(doc, [
        "当前版本：V1.0（2026-10-12）。",
        "交付物：dist\\RenameMaster.exe（免安装单文件）。",
        "更新渠道：关注项目仓库 Release，或替换 dist 目录下的 RenameMaster.exe。",
        "问题反馈：整理好 logs\\rename_YYYYMMDD.log 中的相关记录后提交 issue。",
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
