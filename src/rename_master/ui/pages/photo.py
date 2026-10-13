"""照片批量命名页：选文件 → 命名模式 → 压缩 → 输出 → 预览 / 执行（任务书 §4.6.2）。"""
from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rename_master.core import compressor, mapper, renamer, scanner, watermark
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree)

IMAGE_FILETYPES = [("图片文件", "*.jpg *.jpeg *.png *.bmp *.heic"),
                   ("所有文件", "*.*")]
MAP_FILETYPES = [("对照表", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]

# (显示文案, target 取值) —— 取值是 KB 字符串，"0" 表示不压缩
TARGET_OPTIONS = [
    ("不压缩", "0"),
    ("1 MB", "1024"),
    ("500 KB", "500"),
    ("200 KB", "200"),
    ("100 KB", "100"),
    ("自定义", "custom"),
]

WM_PLACEHOLDER = "如：曲靖联通 2026-10-12（回车换行可多行）"
WM_TEXT_ROWS = 3                                     # 多行输入框高度（行）
# (下拉显示文案, 传给 watermark.add_watermark 的 position)：与 watermark.POSITIONS 对齐
WM_POSITIONS = [("右下角", "bottom_right"), ("左下角", "bottom_left"),
                ("右上角", "top_right"), ("左上角", "top_left"),
                ("底部居中", "bottom_center"), ("顶部居中", "top_center"),
                ("左中", "center_left"), ("右中", "center_right"),
                ("居中", "center")]
WM_POS_VALUE = dict(WM_POSITIONS)
# (下拉显示文案, color)：对应 watermark.COLORS
WM_COLORS = [("白色", "white"), ("黑色", "black"), ("黄色", "yellow"),
             ("红色", "red"), ("青色", "cyan")]
WM_COLOR_VALUE = dict(WM_COLORS)
WM_COLOR_DEFAULT = "白色"
# (下拉显示文案, opacity)
WM_OPACITIES = [("10%", 0.1), ("20%", 0.2), ("40%", 0.4), ("60%", 0.6),
                ("80%", 0.8)]
WM_OPACITY_VALUE = dict(WM_OPACITIES)
WM_OPACITY_DEFAULT = "40%"
# (下拉显示文案, watermark.TEMPLATES 的 key)：none = 不自动填
WM_TEMPLATES = [("不使用模板", "none"), ("运营商巡检", "operator"),
                ("现场勘查", "survey")]
WM_TEMPLATE_DEFAULT = "不使用模板"
WM_TEMPLATE_LOCATION = "曲靖市"
WM_LOGO_FILETYPES = [("LOGO 图片", "*.png *.jpg *.jpeg *.bmp"),
                     ("所有文件", "*.*")]
WM_LOGO_POSITION = "top_left"                        # LOGO 固定贴左上角
# (下拉显示文案, font_size_ratio)：字号 = 图片短边 × 比例
WM_SIZE_OPTIONS = [("小", 0.012), ("中", 0.020), ("大", 0.035)]
WM_SIZE_VALUE = dict(WM_SIZE_OPTIONS)
WM_SIZE_DEFAULT = "中"
WM_RATIO_DEFAULT = WM_SIZE_VALUE[WM_SIZE_DEFAULT]

FILE_COLS = [("sel", "☑", 40, tk.CENTER), ("name", "文件名", 280, "w"),
             ("size", "大小", 90, tk.CENTER), ("dim", "尺寸", 120, tk.CENTER)]
PREVIEW_COLS = [("old", "原文件名", 220, "w"), ("new", "新文件名", 220, "w"),
                ("old_size", "原大小", 90, tk.CENTER),
                ("new_size", "预计新大小", 100, tk.CENTER),
                ("status", "状态", 80, tk.CENTER)]
STATUS_COLOR = {"ok": T.C_SUCCESS, "warn": T.C_WARNING, "error": T.C_DANGER}


def _radio(master, text: str, variable: tk.Variable, value: str, command=None) -> tk.Radiobutton:
    """卡片内统一风格的单选钮（白底，避免 ttk 主题在 Win 上的灰块）。"""
    return tk.Radiobutton(master, text=text, variable=variable, value=value,
                          command=command, bg=T.C_CARD, fg=T.C_TEXT,
                          activebackground=T.C_CARD, activeforeground=T.C_ACCENT,
                          selectcolor=T.C_CARD, highlightthickness=0,
                          font=(T.FONT_FAMILY, T.F_BODY), anchor="w", cursor="hand2")


def _check(master, text: str, variable: tk.Variable, command=None) -> tk.Checkbutton:
    return tk.Checkbutton(master, text=text, variable=variable, command=command,
                          bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                          activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                          highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                          anchor="w", cursor="hand2")


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "照片批量命名",
               "支持统一前缀+序号 / Excel 对照表，自动压缩到指定大小")

    # ---------- 页面状态 ----------
    st = {
        "files": [],          # List[Path]
        "src_dir": tk.StringVar(value=""),   # 源目录（浏览 / 拖入共用）
        "mapping": {},        # {原文件名: 新文件名}
        "mode": tk.StringVar(value=app.cfg.get("photo.mode", "prefix")),
        "base": tk.StringVar(value=app.cfg.get("photo.base_name", "照片")),
        "digits": tk.StringVar(value=str(app.cfg.get("photo.digits", 3))),
        "start": tk.StringVar(value=str(app.cfg.get("photo.start", 1))),
        "sep": tk.StringVar(value=app.cfg.get("photo.sep", "_")),
        "keep_ext": tk.BooleanVar(value=bool(app.cfg.get("photo.keep_ext", True))),
        "target": tk.StringVar(value=app.cfg.get("photo.compress", "500")),
        "custom_kb": tk.StringVar(value=str(app.cfg.get("photo.custom_kb", 300))),
        "keep_exif": tk.BooleanVar(value=bool(app.cfg.get("photo.keep_exif", True))),
        "wm_on": tk.BooleanVar(value=bool(app.cfg.get("photo.wm_on", False))),
        "wm_text": tk.StringVar(value=str(app.cfg.get("photo.wm_text", ""))),
        "wm_pos": tk.StringVar(value=app.cfg.get("photo.wm_pos", "右下角")),
        "wm_size": tk.StringVar(value=app.cfg.get("photo.wm_size", WM_SIZE_DEFAULT)),
        "wm_color": tk.StringVar(value=app.cfg.get("photo.wm_color", WM_COLOR_DEFAULT)),
        "wm_opacity": tk.StringVar(
            value=app.cfg.get("photo.wm_opacity", WM_OPACITY_DEFAULT)),
        "wm_template": tk.StringVar(
            value=app.cfg.get("photo.wm_template", WM_TEMPLATE_DEFAULT)),
        "wm_logo": tk.StringVar(value=str(app.cfg.get("photo.wm_logo", ""))),
        "out_dir": tk.StringVar(value=""),
        "src_dir": tk.StringVar(value=""),   # 源文件夹（点「添加文件夹」或拖入时记录）
        "cancel": None,       # threading.Event，执行中非 None
    }
    app.selected_files = st["files"]      # 供其它页 / 调试读取
    app.mapping = st["mapping"]

    # ---------- ① 选择文件 ----------
    card1 = Card(page, "① 选择文件", "添加要改名的照片，支持多选与整个文件夹导入",
                 accent=T.C_ACCENT)
    card1.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))

    # 源目录输入框：既可用「选择文件夹」浏览，也可从资源管理器拖入文件夹自动填
    src_row = tk.Frame(card1.body, bg=T.C_CARD)
    src_row.pack(fill=tk.X, pady=(0, T.S_SM))
    tk.Label(src_row, text="源目录", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    src_entry = tk.Entry(src_row, textvariable=st["src_dir"], relief=tk.FLAT,
                         bg=T.C_CARD, fg=T.C_TEXT,
                         highlightbackground=T.C_BORDER, highlightthickness=1)
    src_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=T.S_SM)
    secondary_button(src_row, "📂 选择文件夹",
                     command=lambda: _add_dir()).pack(side=tk.LEFT)

    bar = tk.Frame(card1.body, bg=T.C_CARD)
    bar.pack(fill=tk.X, pady=(0, T.S_SM))
    secondary_button(bar, "➕ 添加文件", command=lambda: _add_files()).pack(side=tk.LEFT)
    secondary_button(bar, "🗑 清空", command=lambda: _clear()).pack(side=tk.LEFT)

    drow = tk.Frame(card1.body, bg=T.C_CARD)
    drow.pack(fill=tk.X, pady=(T.S_XS, 0))
    tk.Label(drow, text="选择文件夹", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(drow, textvariable=st["src_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    tree = styled_tree(card1.body, FILE_COLS, height=8)
    vsb = ttk.Scrollbar(card1.body, orient="vertical",
                        style="RenameMaster.Vertical.TScrollbar",
                        command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.X)

    count_label = hint_label(card1.body, "已选择 0 个文件")
    count_label.pack(fill=tk.X, pady=(T.S_XS, 0))

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        for p in st["files"]:
            tree.insert("", "end", values=("☑", p.name,
                                           scanner.fmt_size(scanner.file_size(p)),
                                           scanner.image_size(p)))
        count_label.config(text=f"已选择 {len(st['files'])} 个文件")
        if st["files"] and not st["out_dir"].get().strip():
            st["out_dir"].set(str(renamer.default_output_dir(st["files"])))

    def _add_files() -> None:
        picked = filedialog.askopenfilenames(title="选择照片", filetypes=IMAGE_FILETYPES)
        _extend(scanner.scan_files(picked, scanner.IMAGE_EXTS))

    def _add_dir() -> None:
        d = filedialog.askdirectory(title="选择照片文件夹")
        if d:
            set_source_dir(d)

    def set_source_dir(path: str) -> None:
        """统一入口：填源目录输入框 + 扫描该目录（拖入 / 浏览共用）。

        用法见 app.apply_drop_path：在首页拖入时先暂存到 app.pending_drop_path，
        切到本页后由 app 再回调这里。
        """
        raw = str(path or "").strip()
        if not raw:
            return
        st["src_dir"].set(raw)
        _extend(scanner.scan_files([raw], scanner.IMAGE_EXTS))
        if not st["files"]:
            app.set_status(f"源目录下没有可用的图片文件：{raw}", "warn")

    def _extend(new_files) -> None:
        known = {str(p.resolve()).lower() for p in st["files"]}
        added = 0
        for p in new_files:
            key = str(p.resolve()).lower()
            if key not in known:
                known.add(key)
                st["files"].append(p)
                added += 1
        _refresh_tree()
        app.set_status(f"已添加 {added} 个文件", "ok")

    def _clear() -> None:
        st["files"].clear()
        st["src_dir"].set("")
        _refresh_tree()
        app.set_status("已清空文件列表")

    # ---------- ② 命名模式 / ③ 压缩：并排两列（缩短页面纵向长度） ----------
    mid = tk.Frame(page, bg=T.C_BG)
    mid.pack(fill=tk.X, pady=(0, T.S_MD))
    mid.grid_columnconfigure(0, weight=1, uniform="mid")
    mid.grid_columnconfigure(1, weight=1, uniform="mid")

    card2 = Card(mid, "② 命名模式", "统一前缀 + 序号，或按 Excel 对照表一一改名",
                 accent=T.C_ACCENT)
    card2.grid(row=0, column=0, sticky="nsew", padx=(0, T.S_SM))

    mode_row = tk.Frame(card2.body, bg=T.C_CARD)
    mode_row.pack(fill=tk.X)
    _radio(mode_row, "模式一：统一前缀+序号", st["mode"], "prefix",
           command=lambda: _sync_mode()).pack(side=tk.LEFT)
    _radio(mode_row, "模式二：一一对照（Excel）", st["mode"], "map",
           command=lambda: _sync_mode()).pack(side=tk.LEFT, padx=T.S_MD)

    # 模式一控件（并排后卡片变窄：基础名称独占一行，其余横向排）
    prefix_box = tk.Frame(card2.body, bg=T.C_CARD)
    prow = tk.Frame(prefix_box, bg=T.C_CARD)
    prow.pack(fill=tk.X, pady=(T.S_SM, 0))
    tk.Label(prow, text="基础名称", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(prow, textvariable=st["base"], relief=tk.FLAT,
             bg=T.C_CARD, fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    prow2 = tk.Frame(prefix_box, bg=T.C_CARD)
    prow2.pack(fill=tk.X, pady=(T.S_SM, 0))
    tk.Label(prow2, text="位数", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    digits_menu = tk.OptionMenu(prow2, st["digits"], "3", "4", "5")
    digits_menu.config(width=2)
    digits_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    tk.Label(prow2, text="起始", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Spinbox(prow2, from_=0, to=99999, textvariable=st["start"],
               width=4).pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    tk.Label(prow2, text="分隔符", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    sep_menu = tk.OptionMenu(prow2, st["sep"], "_", "-", " ", "")
    sep_menu.config(width=2)
    sep_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    _check(prow2, "保留扩展名", st["keep_ext"]).pack(side=tk.LEFT)
    _hl = hint_label(prefix_box, "示例：照片_001.jpg")
    _hl.pack(fill=tk.X, pady=(T.S_XS, 0))

    # 模式二控件
    map_box = tk.Frame(card2.body, bg=T.C_CARD)
    mrow = tk.Frame(map_box, bg=T.C_CARD)
    mrow.pack(fill=tk.X, pady=(T.S_SM, 0))
    secondary_button(mrow, "📥 从 Excel 导入", command=lambda: _import_map()).pack(side=tk.LEFT)
    secondary_button(mrow, "🔍 一键提取文件名", command=lambda: _extract_names()).pack(side=tk.LEFT, padx=(T.S_XS, 0))
    secondary_button(mrow, "💾 导出 Excel", command=lambda: _export_map()).pack(side=tk.LEFT, padx=(T.S_XS, 0))
    map_label = hint_label(mrow, "尚未导入对照表")
    map_label.pack(side=tk.LEFT, padx=T.S_SM)

    map_tree = styled_tree(map_box, [("src", "原文件名", 150, "w"),
                                     ("dst", "新文件名", 150, "w")], height=6)
    map_vsb = ttk.Scrollbar(map_box, orient="vertical",
                            style="RenameMaster.Vertical.TScrollbar",
                            command=map_tree.yview)
    map_tree.configure(yscrollcommand=map_vsb.set)
    map_vsb.pack(side=tk.RIGHT, fill=tk.Y)
    map_tree.pack(fill=tk.X, pady=(T.S_SM, 0))
    hint_label(map_box,
               "第1列原文件名，第2列新文件名，未匹配保持原名"
               ).pack(fill=tk.X)

    def _import_map() -> None:
        path = filedialog.askopenfilename(title="选择对照表", filetypes=MAP_FILETYPES)
        if not path:
            return
        try:
            mapping = mapper.load_mapping(path)
        except Exception as exc:                       # noqa: BLE001 解析失败只提示
            messagebox.showerror("导入失败", f"对照表解析失败：{exc}")
            app.set_status("对照表解析失败", "err")
            return
        if not mapping:
            messagebox.showwarning("导入结果", "对照表为空，请检查列内容。")
            return
        st["mapping"].clear()
        st["mapping"].update(mapping)
        map_tree.delete(*map_tree.get_children())
        for k, v in mapper.mapping_rows(mapping):
            map_tree.insert("", "end", values=(k, v))
        map_label.config(text=f"已导入 {len(mapping)} 条对照（{Path(path).name}）")
        app.set_status(f"对照表已导入 {len(mapping)} 条", "ok")

    def _extract_names() -> None:
        """一键把当前文件列表的文件名填进对照表（新文件名留空，用户再编辑）。"""
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先在上方选择文件夹或添加文件。")
            return
        st["mapping"].clear()
        map_tree.delete(*map_tree.get_children())
        for p in st["files"]:
            st["mapping"][p.name] = ""     # 新文件名留空
            map_tree.insert("", "end", values=(p.name, ""))
        map_label.config(text=f"已提取 {len(st['files'])} 个文件名（新文件名待填写）")
        app.set_status(f"已提取 {len(st['files'])} 个文件名到对照表", "ok")

    def _export_map() -> None:
        """把当前对照表导出成 xlsx，供用户在 Excel 里二次编辑后再导入。"""
        if not st["mapping"]:
            messagebox.showwarning("对照表为空", "请先「从 Excel 导入」或「一键提取文件名」。")
            return
        path = filedialog.asksaveasfilename(
            title="导出对照表", defaultextension=".xlsx",
            initialfile="对照表.xlsx",
            filetypes=[("Excel 文件", "*.xlsx")])
        if not path:
            return
        try:
            n = mapper.export_mapping(st["mapping"], path)
        except Exception as exc:                       # noqa: BLE001
            messagebox.showerror("导出失败", f"Excel 写入失败：{exc}")
            return
        map_label.config(text=f"已导出 {n} 条对照 → {Path(path).name}")
        app.set_status(f"对照表已导出：{path}", "ok")
        if messagebox.askyesno("导出成功",
                               f"已导出 {n} 条对照到：\n{path}\n\n"
                               "是否现在打开所在文件夹？"):
            import os
            os.startfile(str(Path(path).parent))

    def _sync_mode() -> None:
        if st["mode"].get() == "map":
            map_box.pack(fill=tk.X)
            prefix_box.pack_forget()
        else:
            prefix_box.pack(fill=tk.X)
            map_box.pack_forget()

    # ---------- ③ 压缩 ----------
    card3 = Card(mid, "③ 压缩到指定大小", "二分法调 JPEG 质量，压不到再等比缩分辨率",
                 accent=T.C_INFO)
    card3.grid(row=0, column=1, sticky="nsew", padx=(T.S_SM, 0))

    trow = tk.Frame(card3.body, bg=T.C_CARD)
    trow.pack(fill=tk.X)
    for i, (text, value) in enumerate(TARGET_OPTIONS):
        _radio(trow, text, st["target"], value,
               command=lambda: _sync_target()).grid(row=i // 3, column=i % 3,
                                                    sticky="w", padx=(0, T.S_SM))
    for col in range(3):
        trow.grid_columnconfigure(col, weight=1, uniform="target")

    crow = tk.Frame(card3.body, bg=T.C_CARD)
    crow.pack(fill=tk.X, pady=(T.S_SM, 0))
    tk.Entry(crow, textvariable=st["custom_kb"], width=6,
             relief=tk.FLAT, bg=T.C_CARD, fg=T.C_TEXT,
             highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT)
    tk.Label(crow, text="KB", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M).pack(side=tk.LEFT, padx=(T.S_XS, T.S_SM))
    _hl = hint_label(crow, "选中「自定义」时按此值压缩")
    _hl.pack(side=tk.LEFT)
    _check(card3.body, "保留 EXIF", st["keep_exif"]).pack(fill=tk.X, pady=(T.S_SM, 0))

    def _sync_target() -> None:
        pass  # 自定义 Entry 常显，取值时再判断；保留钩子便于后续禁用态扩展

    # ---------- ④ 水印（可选，默认关闭 + 默认折叠） ----------
    card_wm = Card(page, "④ 水印（可选）",
                   "默认关闭并折叠；勾选后可叠加多行文字水印（颜色 / 透明度 / 9 种位置）"
                   "，还能再贴一张 LOGO",
                   accent=T.C_WARNING, collapsible=True, start_collapsed=True)
    card_wm.pack(fill=tk.X, pady=(0, T.S_MD))

    # 第一行：开关 + 快速模板
    r1 = tk.Frame(card_wm.body, bg=T.C_CARD)
    r1.pack(fill=tk.X)
    _check(r1, "☑ 添加水印文字", st["wm_on"],
           command=lambda: _sync_watermark()).pack(side=tk.LEFT)
    wm_tpl_label = tk.Label(r1, text="📋 快速模板", font=(T.FONT_FAMILY, T.F_BODY),
                            bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
    wm_tpl_label.pack(side=tk.LEFT, padx=(T.S_LG, 0))
    wm_tpl_menu = tk.OptionMenu(r1, st["wm_template"], *[d for d, _ in WM_TEMPLATES],
                                command=lambda _v: _apply_template())
    wm_tpl_menu.config(width=10)
    wm_tpl_menu.pack(side=tk.LEFT, padx=(T.S_XS, 0))

    # 第二行：多行水印文字
    r2 = tk.Frame(card_wm.body, bg=T.C_CARD)
    r2.pack(fill=tk.X, pady=(T.S_SM, 0))
    wm_text_label = tk.Label(r2, text="水印文字", font=(T.FONT_FAMILY, T.F_BODY),
                             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
    wm_text_label.pack(side=tk.LEFT, anchor="n")
    wm_text_box = tk.Text(r2, height=WM_TEXT_ROWS, wrap=tk.WORD, relief=tk.FLAT,
                          bg=T.C_CARD, fg=T.C_TEXT_FADE,
                          highlightbackground=T.C_BORDER, highlightthickness=1,
                          font=(T.FONT_FAMILY, T.F_BODY))
    wm_text_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(T.S_SM, 0))
    _hl = hint_label(r2, "回车换行可写多行")
    _hl.pack(side=tk.LEFT, padx=(T.S_SM, 0), anchor="n")

    # 第三行：颜色 / 透明度 / 位置 / 字号
    r3 = tk.Frame(card_wm.body, bg=T.C_CARD)
    r3.pack(fill=tk.X, pady=(T.S_SM, 0))
    wm_color_label = tk.Label(r3, text="颜色", font=(T.FONT_FAMILY, T.F_BODY),
                              bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
    wm_color_label.pack(side=tk.LEFT)
    wm_color_menu = tk.OptionMenu(r3, st["wm_color"], *[d for d, _ in WM_COLORS])
    wm_color_menu.config(width=5)
    wm_color_menu.pack(side=tk.LEFT, padx=(T.S_XS, 0))
    wm_opacity_label = tk.Label(r3, text="透明度", font=(T.FONT_FAMILY, T.F_BODY),
                                bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
    wm_opacity_label.pack(side=tk.LEFT, padx=(T.S_MD, 0))
    wm_opacity_menu = tk.OptionMenu(r3, st["wm_opacity"], *[d for d, _ in WM_OPACITIES])
    wm_opacity_menu.config(width=4)
    wm_opacity_menu.pack(side=tk.LEFT, padx=(T.S_XS, 0))
    wm_pos_label = tk.Label(r3, text="位置", font=(T.FONT_FAMILY, T.F_BODY),
                            bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
    wm_pos_label.pack(side=tk.LEFT, padx=(T.S_MD, 0))
    wm_pos_menu = tk.OptionMenu(r3, st["wm_pos"], *[d for d, _ in WM_POSITIONS])
    wm_pos_menu.config(width=8)
    wm_pos_menu.pack(side=tk.LEFT, padx=(T.S_XS, 0))
    wm_size_label = tk.Label(r3, text="字号", font=(T.FONT_FAMILY, T.F_BODY),
                             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
    wm_size_label.pack(side=tk.LEFT, padx=(T.S_MD, 0))
    wm_size_menu = tk.OptionMenu(r3, st["wm_size"], *[d for d, _ in WM_SIZE_OPTIONS])
    wm_size_menu.config(width=3)
    wm_size_menu.pack(side=tk.LEFT, padx=(T.S_XS, 0))

    # 第四行：LOGO
    r4 = tk.Frame(card_wm.body, bg=T.C_CARD)
    r4.pack(fill=tk.X, pady=(T.S_SM, 0))
    wm_logo_btn = secondary_button(r4, "🖼 选择 LOGO 图片",
                                   command=lambda: _pick_logo())
    wm_logo_btn.pack(side=tk.LEFT)
    wm_logo_label = hint_label(r4, "未选择 LOGO")
    wm_logo_label.pack(side=tk.LEFT, padx=T.S_SM)

    def _wm_raw() -> str:
        return wm_text_box.get("1.0", "end-1c")

    def _wm_set_text(value: str) -> None:
        wm_text_box.delete("1.0", tk.END)
        wm_text_box.insert("1.0", value)
        wm_text_box.config(fg=T.C_TEXT if value.strip() else T.C_TEXT_FADE)

    def _apply_template() -> None:
        """选模板 → 用当前日期时间渲染文案并填进多行框。"""
        name = dict(WM_TEMPLATES).get(st["wm_template"].get(), "none")
        if name == "none":
            return
        text = watermark.render_template(
            name, date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            location=WM_TEMPLATE_LOCATION)
        _wm_set_text(text)
        app.set_status(f"已填入「{st['wm_template'].get()}」模板文案", "ok")

    def _pick_logo() -> None:
        path = filedialog.askopenfilename(title="选择 LOGO 图片",
                                          filetypes=WM_LOGO_FILETYPES)
        if path:
            st["wm_logo"].set(path)
            wm_logo_label.config(text=f"LOGO：{path}")
            app.set_status(f"已选择 LOGO：{path}", "ok")

    def _wm_focus_in(_event=None) -> None:
        if _wm_raw() == WM_PLACEHOLDER:
            wm_text_box.delete("1.0", tk.END)
        wm_text_box.config(fg=T.C_TEXT)

    def _wm_focus_out(_event=None) -> None:
        if not _wm_raw().strip():
            _wm_set_text(WM_PLACEHOLDER)

    wm_text_box.bind("<FocusIn>", _wm_focus_in)
    wm_text_box.bind("<FocusOut>", _wm_focus_out)
    if st["wm_text"].get().strip():
        _wm_set_text(st["wm_text"].get())       # 读上次配置
    else:
        _wm_focus_out()                        # 初始显示 placeholder
    if st["wm_logo"].get().strip():
        wm_logo_label.config(text=f"LOGO：{st['wm_logo'].get()}")

    def _wm_text_value() -> str:
        raw = _wm_raw().strip()
        return "" if raw == WM_PLACEHOLDER else raw

    def _sync_watermark() -> None:
        on = st["wm_on"].get()
        state = tk.NORMAL if on else tk.DISABLED
        wm_text_box.config(state=state)
        for menu in (wm_tpl_menu, wm_color_menu, wm_opacity_menu, wm_pos_menu,
                     wm_size_menu):
            menu.config(state=state)
        wm_logo_btn.config(state=state)
        fg = T.C_TEXT_M if on else T.C_TEXT_FADE
        for label in (wm_tpl_label, wm_text_label, wm_color_label,
                      wm_opacity_label, wm_pos_label, wm_size_label):
            label.config(fg=fg)
        wm_logo_label.config(fg=fg)

    # ---------- ⑤ 输出位置 ----------
    card4 = Card(page, "⑤ 输出位置", "默认输出到「<源目录>_重命名输出」，绝不原地覆盖",
                 accent=T.C_SUCCESS)
    card4.pack(fill=tk.X, pady=(0, T.S_MD))

    orow = tk.Frame(card4.body, bg=T.C_CARD)
    orow.pack(fill=tk.X)
    tk.Entry(orow, textvariable=st["out_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True)
    secondary_button(orow, "📁 浏览", command=lambda: _pick_out()).pack(side=tk.LEFT,
                                                                    padx=(T.S_SM, 0))

    def _pick_out() -> None:
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            st["out_dir"].set(d)

    # ---------- 规则 / 执行 ----------
    def _target_kb() -> int:
        raw = st["target"].get()
        if raw == "custom":
            raw = st["custom_kb"].get()
        try:
            return max(0, int(str(raw).strip()))
        except ValueError:
            return 0

    def _build_rule() -> dict:
        if st["mode"].get() == "map":
            return {"mapping": dict(st["mapping"]),
                    "keep_ext": st["keep_ext"].get()}
        try:
            start = int(str(st["start"].get()).strip())
        except ValueError:
            start = 1
        try:
            digits = int(str(st["digits"].get()).strip())
        except ValueError:
            digits = 3
        return {"base_name": st["base"].get().strip(), "digits": digits,
                "start": start, "sep": st["sep"].get(),
                "keep_ext": st["keep_ext"].get()}

    def _make_plans():
        mode = renamer.MODE_MAP if st["mode"].get() == "map" else renamer.MODE_PREFIX
        return renamer.plan_rename(st["files"], mode, _build_rule())

    def _transform(target_kb: int):
        # 水印是最后一步：先压缩到目标大小，再叠水印（避免水印被二次压缩糊掉）
        wm_text = _wm_text_value() if st["wm_on"].get() else ""
        wm_pos = WM_POS_VALUE.get(st["wm_pos"].get(), watermark.DEFAULT_POSITION)
        wm_ratio = WM_SIZE_VALUE.get(st["wm_size"].get(), WM_RATIO_DEFAULT)
        wm_color = WM_COLOR_VALUE.get(st["wm_color"].get(), watermark.DEFAULT_COLOR)
        wm_opacity = WM_OPACITY_VALUE.get(st["wm_opacity"].get(),
                                          watermark.DEFAULT_OPACITY)
        wm_logo = st["wm_logo"].get().strip() if st["wm_on"].get() else ""
        if target_kb <= 0 and not wm_text and not wm_logo:
            return None

        def _fn(src: Path, dst_name: str):
            if Path(src).suffix.lower() not in scanner.IMAGE_EXTS:
                return None
            data = Path(src).read_bytes()
            if target_kb > 0:
                data = compressor.compress_to_target(data, target_kb,
                                                     keep_exif=st["keep_exif"].get())
            if wm_text:
                data = watermark.add_watermark(data, wm_text, position=wm_pos,
                                               font_size_ratio=wm_ratio,
                                               color=wm_color, opacity=wm_opacity)
            if wm_logo:
                data = watermark.add_logo_watermark(data, wm_logo,
                                                    position=WM_LOGO_POSITION)
            return data
        return _fn

    def _validate() -> bool:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个文件。")
            return False
        if not st["out_dir"].get().strip():
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return False
        if st["mode"].get() == "map" and not st["mapping"]:
            messagebox.showwarning("缺少对照表", "模式二需要先导入 Excel 对照表。")
            return False
        return True

    def _estimate(plan, target_kb: int) -> int:
        if target_kb <= 0:
            return scanner.file_size(plan.src)
        if Path(plan.src).suffix.lower() not in scanner.IMAGE_EXTS:
            return scanner.file_size(plan.src)
        return compressor.estimate_size(plan.src, target_kb,
                                        keep_exif=st["keep_exif"].get())

    def _open_preview(on_confirm=None) -> None:
        if not _validate():
            return
        target_kb = _target_kb()
        plans = _make_plans()
        win = tk.Toplevel(app.root)
        win.title("改名结果预览")
        win.geometry("820x460")
        win.configure(bg=T.C_BG)
        tk.Label(win, text=f"共 {len(plans)} 个文件 → {st['out_dir'].get()}"
                           f"（压缩目标：{target_kb or '不压缩'}"
                           f"{' KB' if target_kb else ''}）",
                 font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                 bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                          padx=T.S_LG, pady=(T.S_MD, T.S_SM))
        tv = styled_tree(win, PREVIEW_COLS, height=14)
        pvsb = ttk.Scrollbar(win, orient="vertical",
                             style="RenameMaster.Vertical.TScrollbar", command=tv.yview)
        tv.configure(yscrollcommand=pvsb.set)
        pvsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, T.S_LG))
        tv.pack(fill=tk.BOTH, expand=True, padx=(T.S_LG, 0), pady=(0, T.S_SM))
        tv.tag_configure("ok", foreground=STATUS_COLOR["ok"])
        tv.tag_configure("warn", foreground=STATUS_COLOR["warn"])
        tv.tag_configure("error", foreground=STATUS_COLOR["error"])

        def _fill() -> None:
            for plan in plans:
                mark = {"ok": "✓ 正常", "warn": "⚠ 注意", "error": "✗ 禁止"}[plan.status]
                tv.insert("", "end",
                          values=(plan.src.name, plan.dst_name,
                                  scanner.fmt_size(scanner.file_size(plan.src)),
                                  scanner.fmt_size(_estimate(plan, target_kb)),
                                  mark),
                          tags=(plan.status,))

        _fill()
        blocked = [p for p in plans if p.blocked]
        if blocked:
            tk.Label(win, text=f"⚠ {len(blocked)} 条存在冲突，执行时会被跳过（红色行）。",
                     font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_DANGER,
                     anchor="w").pack(fill=tk.X, padx=T.S_LG, pady=(0, T.S_SM))

        btm = tk.Frame(win, bg=T.C_BG)
        btm.pack(fill=tk.X, padx=T.S_LG, pady=(0, T.S_MD))
        secondary_button(btm, "关闭", command=win.destroy).pack(side=tk.RIGHT)
        if on_confirm is not None:
            primary_button(btm, "▶ 确认执行",
                           command=lambda: (win.destroy(), on_confirm(plans, target_kb))
                           ).pack(side=tk.RIGHT, padx=(0, T.S_SM))

    def _run(plans, target_kb: int) -> None:
        out_dir = Path(st["out_dir"].get().strip())
        cancel_event = threading.Event()
        st["cancel"] = cancel_event
        bar_btn_cancel.config(state=tk.NORMAL)
        bar_btn_run.config(state=tk.DISABLED)
        progress.pack(fill=tk.X, pady=(T.S_SM, 0))
        progress["value"] = 0
        progress["maximum"] = max(1, len(plans))
        app.set_status("正在执行…")

        def _ui(done: int, total: int, name: str) -> None:
            progress["value"] = done
            bar_state.config(text=f"{done}/{total} {name}")
            app.set_status(f"执行中 {done}/{total}")

        def _worker() -> None:
            result = renamer.execute_plan(
                plans, out_dir, move=False, transform=_transform(target_kb),
                progress=lambda d, t, n: app.safe_after(0, lambda: _ui(d, t, n)),
                cancel=cancel_event.is_set)
            app.safe_after(0, lambda: _finish(result))

        def _finish(result: dict) -> None:
            st["cancel"] = None
            progress.pack_forget()
            bar_btn_cancel.config(state=tk.DISABLED)
            bar_btn_run.config(state=tk.NORMAL)
            app.cfg.set("output.last_dir", str(out_dir))
            app.cfg.set("output.last_count", result["done"])
            app.cfg.save()
            bar_state.config(text=f"完成 {result['done']}/{result['total']}"
                                  f"（失败 {result['failed']}）")
            kind = "ok" if not result["failed"] else "warn"
            app.set_status(f"完成 {result['done']} 个，失败 {result['failed']} 个", kind)
            msg = (f"完成 {result['done']} 个，失败 {result['failed']} 个\n"
                   f"输出目录：{out_dir}")
            if result["errors"]:
                msg += "\n\n" + "\n".join(result["errors"][:10])
            messagebox.showinfo("执行完成", msg)

        threading.Thread(target=_worker, daemon=True).start()

    # ---------- 底部操作栏（不随内容滚动） ----------
    # 操作栏最终被 set_action_bar 重挂到 action_host（不随内容滚动）。
    # master 必须是 content：否则 clear_action_bar 会先把它销毁，且 pack -in 也会失败。
    bar = tk.Frame(app.content, bg=T.C_BG)
    left = tk.Frame(bar, bg=T.C_BG)
    left.pack(side=tk.LEFT)
    secondary_button(left, "👁 预览改名结果",
                     command=lambda: _open_preview()).pack(side=tk.LEFT)
    bar_state = tk.Label(left, text="", font=(T.FONT_FAMILY, T.F_SM),
                         bg=T.C_BG, fg=T.C_TEXT_L)
    bar_state.pack(side=tk.LEFT, padx=T.S_SM)
    right = tk.Frame(bar, bg=T.C_BG)
    right.pack(side=tk.RIGHT)
    bar_btn_cancel = secondary_button(right, "✖ 取消", state=tk.DISABLED,
                                      command=lambda: st["cancel"].set()
                                      if st["cancel"] else None)
    bar_btn_cancel.pack(side=tk.LEFT, padx=(0, T.S_SM))
    bar_btn_run = primary_button(right, "▶ 开始执行",
                                 command=lambda: _open_preview(on_confirm=_run))
    bar_btn_run.pack(side=tk.LEFT)
    progress = ttk.Progressbar(bar, style="RenameMaster.Horizontal.TProgressbar",
                               mode="determinate", maximum=1, value=0)

    # 切页时只显示本页操作栏：pack(in_=) 只改布局不改父子关系，
    # 故已在 app._action_bars 里登记、靠 <Map> 事件互斥显示。
    key = next((k for k, v in app.pages.items() if v is page), "photo")
    page.set_source_dir = set_source_dir      # 供 app.apply_drop_path 派发拖入
    bars = getattr(app, "_action_bars", None)
    if bars is None:
        bars = {}
        app._action_bars = bars
    bars[key] = bar

    def _activate(_event=None) -> None:
        for k, other in bars.items():
            if k != key:
                try:
                    other.pack_forget()
                except tk.TclError:
                    pass
        app.set_action_bar(bar)
        app.action_host.pack(fill=tk.X, side=tk.BOTTOM)

    page.bind("<Map>", _activate)
    _activate()
    _sync_mode()
    _sync_watermark()
    _refresh_tree()
    app.set_status("就绪")
