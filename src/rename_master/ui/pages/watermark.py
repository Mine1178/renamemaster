"""水印页：批量添加可见水印（多行文本 + 4 种风格 + 5 参数）+ 隐形盲水印。

v1.7 美化重构：
- 4 种布局风格：2×2 卡片式选择（图标 + 名称 + 描述），选中态 accent 边框高亮
- 9 位置：3×3 九宫格可视化按钮（不再用下拉菜单）
- 颜色：真色块 swatch 按钮（选中态白色高亮边框）
- 修复描边 checkbox 不生效 bug；新增阴影 / LOGO 位置大小 / 印章大小可调
- 输出格式 JPG / PNG 可选
"""
from __future__ import annotations

import threading
import tkinter as tk
import tempfile
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from types import SimpleNamespace

from PIL import Image, ImageTk

from rename_master.core import history, scanner, watermark, blind_wm
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, dialog_buttons,
                                      dialog_tree, fit_dialog, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree, vlabel, enable_label_copy)

IMAGE_FILETYPES = [("图片文件", "*.jpg *.jpeg *.png *.bmp *.heic"),
                   ("所有文件", "*.*")]
LOGO_FILETYPES = [("LOGO 图片", "*.png *.jpg *.jpeg *.bmp"),
                  ("所有文件", "*.*")]

# 9 个角落位置（single / seal / logo 共用）
POSITIONS = [("↖", "top_left", "左上角"), ("↑", "top_center", "顶部居中"),
             ("↗", "top_right", "右上角"),
             ("←", "center_left", "左中"), ("·", "center", "居中"),
             ("→", "center_right", "右中"),
             ("↙", "bottom_left", "左下角"), ("↓", "bottom_center", "底部居中"),
             ("↘", "bottom_right", "右下角")]
POS_VALUE = {v: k for _, k, v in POSITIONS}  # value -> 中文名
POS_DISPLAY = {k: v for _, k, v in [(g, k, v) for g, k, v in POSITIONS]}

# 平铺参数
ANGLES = [("0°", 0), ("15°", 15), ("30°", 30), ("45°", 45),
          ("60°", 60), ("90°", 90)]
ANGLE_VALUE = dict(ANGLES)
SIZES = [("小", 0.012), ("中", 0.020), ("大", 0.035)]
SIZE_VALUE = dict(SIZES)
OPACITIES = [("10%", 0.10), ("15%", 0.15), ("25%", 0.25),
             ("40%", 0.40), ("60%", 0.60), ("80%", 0.80)]
OPACITY_VALUE = dict(OPACITIES)
SPACINGS = [("密", 0.7), ("中", 1.0), ("疏", 1.4)]
SPACING_VALUE = dict(SPACINGS)
DENSITIES = [("1×1", 1), ("2×2", 2), ("3×3", 3), ("4×4", 4),
             ("5×5", 5), ("6×6", 6), ("自动", 0)]
DENSITY_VALUE = dict(DENSITIES)

# 印章形状 / 大小
SEAL_SHAPES = [("圆环", "round"), ("方框", "rect")]
SEAL_SHAPE_VALUE = dict(SEAL_SHAPES)
SEAL_SIZES = [("小", 0.16), ("中", 0.22), ("大", 0.30)]
SEAL_SIZE_VALUE = dict(SEAL_SIZES)

# LOGO 大小档位
LOGO_SIZES = [("小", 0.05), ("中", 0.08), ("大", 0.12)]
LOGO_SIZE_VALUE = dict(LOGO_SIZES)

# 输出格式
OUT_FMTS = [("JPG", "jpg"), ("PNG", "png")]
OUT_FMT_VALUE = dict(OUT_FMTS)

# 快捷颜色（显示名, hex）——暗黄排第一作为推荐默认
QUICK_COLORS = [("暗黄", watermark.DEFAULT_TILE_COLOR),
                ("白", "#FFFFFF"), ("黑", "#000000"), ("红", "#FF2D55"),
                ("亮黄", "#FFD60A"), ("蓝", "#1E6FFF"), ("青", "#00E5FF"),
                ("灰", "#9AA3AF")]

# 4 种布局风格卡片定义
LAYOUT_CARDS = [
    ("tile",   "📐 斜向平铺", "裁不掉，防盗主力\n30° 暗黄经典款"),
    ("single", "📍 角落单处", "9 位置任选\n角落标记得醒目"),
    ("seal",   "🔴 印章风格", "圆/方框 + 中央文字\n版权 / 状态标记"),
    ("grid",   "▦ 平铺密度", "1×1 ~ 6×6 网格\n均匀铺满不倾斜"),
]

FILE_COLS = [("sel", "☑", 40, tk.CENTER), ("name", "文件名", 300, "w"),
             ("size", "大小", 90, tk.CENTER), ("dim", "尺寸", 130, tk.CENTER)]
PREVIEW_COLS = [("src", "原文件", 280, "w"), ("dst", "新文件", 280, "w"),
                ("size", "大小", 90, tk.CENTER), ("status", "状态", 80, tk.CENTER)]


def _check(master, text: str, variable: tk.Variable, command=None) -> tk.Widget:
    """自定义大方框 checkbox：用 Label 模拟，☑/☐ 约 24px 便于点选。"""
    box = tk.Frame(master, bg=T.C_CARD)
    def _refresh():
        mark_lbl.config(text="☑" if variable.get() else "☐")
    def _toggle(e=None):
        variable.set(not variable.get())
        _refresh()
        if command:
            command()
    mark_lbl = tk.Label(box, text="", bg=T.C_CARD, fg=T.C_ACCENT,
                        font=(T.FONT_FAMILY, 18), cursor="hand2")
    mark_lbl.pack(side=tk.LEFT)
    text_lbl = tk.Label(box, text=text, bg=T.C_CARD, fg=T.C_TEXT,
                        font=(T.FONT_FAMILY, T.F_BODY), anchor="w",
                        cursor="hand2")
    text_lbl.pack(side=tk.LEFT, padx=(4, 0))
    mark_lbl.bind("<Button-1>", _toggle)
    text_lbl.bind("<Button-1>", _toggle)
    box.bind("<Map>", lambda e: _refresh())
    return box


def _menu(master, variable, options, width=6):
    w = tk.OptionMenu(master, variable, *options)
    w.config(width=width)
    return w


def _preview_image_for_tk(img_bytes: bytes, max_w: int = 480):
    """JPEG/PNG 字节流 → tk.Photoimage（限制最大边，比例缩放）。"""
    from io import BytesIO
    img = Image.open(BytesIO(img_bytes))
    img.thumbnail((max_w, max_w * 4 // 3), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def _open_dialog(win, w: int, h: int) -> None:
    """弹窗尺寸完全按用户指定，不做屏幕截断；自动居中。"""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.minsize(min(w, 600), min(h, 400))
    win.geometry(f"{w}x{h}+{x}+{y}")


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "添加水印",
               "多行文字 / 4 种风格（平铺 / 单处 / 印章 / 密度网格） / 5 参数 / 实时预览")

    # ---------- 页面状态 ----------
    st = {
        "files": [],
        "src_dir": tk.StringVar(value=""),
        # 可见水印总开关
        "vis_on": tk.BooleanVar(value=bool(app.cfg.get("watermark.vis_on", True))),
        # 多行水印文字
        "vis_text_init": app.cfg.get("watermark.vis_text", "曲靖联通 陈琼\n2026-10-14"),
        # 布局（4 选 1）
        "vis_layout": tk.StringVar(value=app.cfg.get("watermark.vis_layout", "tile")),
        # tile 参数
        "vis_angle": tk.StringVar(value=app.cfg.get("watermark.vis_angle", "30°")),
        "vis_density": tk.StringVar(value=app.cfg.get("watermark.vis_density", "自动")),
        # single / seal 公共参数
        "vis_pos": tk.StringVar(value=app.cfg.get("watermark.vis_pos", "右下角")),
        "vis_size": tk.StringVar(value=app.cfg.get("watermark.vis_size", "中")),
        # 5 样式参数
        "vis_color": tk.StringVar(value=app.cfg.get("watermark.vis_color",
                                                    watermark.DEFAULT_TILE_COLOR)),
        "vis_opacity": tk.StringVar(value=app.cfg.get("watermark.vis_opacity", "15%")),
        "vis_spacing": tk.StringVar(value=app.cfg.get("watermark.vis_spacing", "中")),
        # 描边 / 阴影（v1.7 修复描边不生效 + 新增阴影）
        "vis_stroke": tk.BooleanVar(value=bool(app.cfg.get("watermark.vis_stroke", False))),
        "vis_shadow": tk.BooleanVar(value=bool(app.cfg.get("watermark.vis_shadow", False))),
        # 印章参数
        "seal_shape": tk.StringVar(value=app.cfg.get("watermark.seal_shape", "圆环")),
        "seal_size": tk.StringVar(value=app.cfg.get("watermark.seal_size", "中")),
        # LOGO
        "vis_logo": tk.StringVar(value=str(app.cfg.get("watermark.vis_logo", ""))),
        "logo_pos": tk.StringVar(value=app.cfg.get("watermark.logo_pos", "右上角")),
        "logo_size": tk.StringVar(value=app.cfg.get("watermark.logo_size", "中")),
        # 盲水印
        "blind_on": tk.BooleanVar(value=bool(app.cfg.get("watermark.blind_on", False))),
        "blind_action": tk.StringVar(value="embed"),
        "blind_text": tk.StringVar(value=app.cfg.get("watermark.blind_text",
                                                     "曲靖联通陈琼20261014")),
        "blind_len": tk.StringVar(value=str(app.cfg.get("watermark.blind_len", 208))),
        "blind_pw": tk.StringVar(value=str(app.cfg.get("watermark.blind_pw", 1))),
        # 输出位置 + 格式
        "out_dir": tk.StringVar(value=""),
        "out_fmt": tk.StringVar(value=app.cfg.get("watermark.out_fmt", "JPG")),
        "cancel": None,
    }
    app.selected_files = st["files"]

    def _lbl(parent, text):
        return vlabel(parent, text=text, font=(T.FONT_FAMILY, T.F_BODY),
                    bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")

    # ---------- ① 选择图片 ----------
    card1 = Card(page, "① 选择图片", "添加要加水印的图片，支持多选、整个文件夹与拖入",
                 accent=T.C_ACCENT)
    card1.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))

    src_row = tk.Frame(card1.body, bg=T.C_CARD)
    src_row.pack(fill=tk.X, pady=(0, T.S_SM))
    vlabel(src_row, text="源目录", font=(T.FONT_FAMILY, T.F_BODY),
           bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(src_row, textvariable=st["src_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=T.S_SM)
    secondary_button(src_row, "📂 选择文件夹", command=lambda: _add_dir()).pack(side=tk.LEFT)

    bar = tk.Frame(card1.body, bg=T.C_CARD)
    bar.pack(fill=tk.X, pady=(0, T.S_SM))
    secondary_button(bar, "➕ 添加图片", command=lambda: _add_files()).pack(side=tk.LEFT)
    secondary_button(bar, "🗑 清空", command=lambda: _clear()).pack(side=tk.LEFT,
                                                                    padx=(T.S_XS, 0))

    tree = styled_tree(card1.body, FILE_COLS, height=5)
    vsb = ttk.Scrollbar(card1.body, orient="vertical",
                        style="RenameMaster.Vertical.TScrollbar",
                        command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.X)
    count_label = hint_label(card1.body, "已选择 0 个图片")
    count_label.pack(fill=tk.X, pady=(T.S_XS, 0))

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        for p in st["files"]:
            tree.insert("", "end", values=("☑", p.name,
                                          scanner.fmt_size(scanner.file_size(p)),
                                          scanner.image_size(p)))
        count_label.config(text=f"已选择 {len(st['files'])} 个图片")
        if st["files"] and not st["out_dir"].get().strip():
            st["out_dir"].set(str(_default_out()))

    def _default_out() -> Path:
        from rename_master.core import renamer
        return renamer.default_output_dir(st["files"])

    def _add_files() -> None:
        picked = filedialog.askopenfilenames(title="选择图片", filetypes=IMAGE_FILETYPES)
        _extend(scanner.scan_files(picked, scanner.IMAGE_EXTS))

    def _add_dir() -> None:
        d = filedialog.askdirectory(title="选择图片文件夹")
        if d:
            set_source_dir(d)

    def set_source_dir(path: str) -> None:
        raw = str(path or "").strip()
        if not raw:
            return
        st["src_dir"].set(raw)
        _extend(scanner.scan_files([raw], scanner.IMAGE_EXTS))

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
        app.set_status(f"已添加 {added} 个图片", "ok")

    def _clear() -> None:
        st["files"].clear()
        st["src_dir"].set("")
        _refresh_tree()
        app.set_status("已清空")

    # ---------- ② 水印内容（多行）+ 总开关 + LOGO ----------
    card2 = Card(page, "② 水印内容", "多行文字逐行绘制；可选叠加 LOGO",
                 accent=T.C_INFO)
    card2.pack(fill=tk.X, pady=(0, T.S_MD))

    # 总开关行
    on_row = tk.Frame(card2.body, bg=T.C_CARD)
    on_row.pack(fill=tk.X, pady=(0, T.S_SM))
    _check(on_row, "添加可见水印（关闭则只跑盲水印）",
           st["vis_on"], command=lambda: _sync_vis_enabled()).pack(side=tk.LEFT)

    vis_text_box = tk.Text(card2.body, height=4, font=(T.FONT_FAMILY, T.F_BODY),
                           bg=T.C_CARD, fg=T.C_TEXT, relief=tk.FLAT,
                           highlightbackground=T.C_BORDER, highlightthickness=1,
                           wrap="word", padx=T.S_SM, pady=T.S_SM)
    vis_text_box.insert("1.0", st["vis_text_init"])
    vis_text_box.pack(fill=tk.X, pady=(0, T.S_SM))

    # LOGO 行
    logo_row = tk.Frame(card2.body, bg=T.C_CARD)
    logo_row.pack(fill=tk.X)
    secondary_button(logo_row, "🖼 选择 LOGO", command=lambda: _pick_logo()).pack(side=tk.LEFT)
    logo_label = hint_label(logo_row, "可选：未选择 LOGO")
    logo_label.pack(side=tk.LEFT, padx=T.S_SM)
    if st["vis_logo"].get():
        logo_label.config(text=f"LOGO：{st['vis_logo'].get()}")

    # LOGO 位置 + 大小（默认隐藏，选了 LOGO 才显示）
    logo_opts = tk.Frame(card2.body, bg=T.C_CARD)
    _lbl(logo_opts, "LOGO 位置").pack(side=tk.LEFT)
    logo_pos_menu = _menu(logo_opts, st["logo_pos"],
                          [v for _, _, v in POSITIONS], 8)
    logo_pos_menu.pack(side=tk.LEFT, padx=(2, T.S_MD))
    _lbl(logo_opts, "LOGO 大小").pack(side=tk.LEFT)
    _menu(logo_opts, st["logo_size"], [d for d, _ in LOGO_SIZES], 3).pack(side=tk.LEFT, padx=2)

    def _pick_logo() -> None:
        p = filedialog.askopenfilename(title="选择 LOGO 图片", filetypes=LOGO_FILETYPES)
        if p:
            st["vis_logo"].set(p)
            logo_label.config(text=f"LOGO：{p}")
            logo_opts.pack(fill=tk.X, pady=(T.S_SM, 0))
            app.request_relayout()

    def _vis_text() -> str:
        return vis_text_box.get("1.0", "end").strip()

    def _sync_vis_enabled() -> None:
        """可见水印开关 → 内容区视觉变灰（不真正 disable，保证 Text 可读写）。"""
        on = st["vis_on"].get()
        bg = T.C_CARD if on else T.C_ROW_ALT
        vis_text_box.config(bg=bg)
        app.request_relayout()

    # ---------- ③ 布局方式（2×2 卡片选择）----------
    card3 = Card(page, "③ 布局方式", "4 种风格互斥单选：斜向平铺 / 角落单处 / 印章 / 密度网格",
                 accent=T.C_CYAN)
    card3.pack(fill=tk.X, pady=(0, T.S_MD))

    style_grid = tk.Frame(card3.body, bg=T.C_CARD)
    style_grid.pack(fill=tk.X, pady=(0, T.S_SM))
    style_btns = {}

    def _select_layout(layout: str) -> None:
        st["vis_layout"].set(layout)
        for key, (frame, label) in style_btns.items():
            if key == layout:
                frame.config(highlightbackground=T.C_CYAN, highlightthickness=2)
                label.config(fg=T.C_CYAN)
            else:
                frame.config(highlightbackground=T.C_BORDER, highlightthickness=1)
                label.config(fg=T.C_TEXT_M)
        _sync_layout()

    for idx, (key, title, desc) in enumerate(LAYOUT_CARDS):
        r, c = divmod(idx, 2)
        f = tk.Frame(style_grid, bg=T.C_CARD, highlightbackground=T.C_BORDER,
                     highlightthickness=1, cursor="hand2")
        f.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
        style_grid.columnconfigure(c, weight=1)
        t = vlabel(f, text=title, font=(T.FONT_FAMILY, T.F_BODY, "bold"),
                   bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")
        t.pack(fill=tk.X, padx=T.S_SM, pady=(T.S_SM, 0))
        d = vlabel(f, text=desc, font=(T.FONT_FAMILY, T.F_SM),
                   bg=T.C_CARD, fg=T.C_TEXT_L, anchor="w")
        d.pack(fill=tk.X, padx=T.S_SM, pady=(0, T.S_SM))
        for w in (f, t, d):
            w.bind("<Button-1>", lambda e, k=key: _select_layout(k))
        style_btns[key] = (f, t)

    # tile 参数容器
    tile_box = tk.Frame(card3.body, bg=T.C_CARD)
    _lbl(tile_box, "角度").pack(side=tk.LEFT)
    angle_menu = _menu(tile_box, st["vis_angle"], [d for d, _ in ANGLES], 4)
    angle_menu.pack(side=tk.LEFT, padx=(2, 0))
    _lbl(tile_box, "间距").pack(side=tk.LEFT, padx=(T.S_MD, 0))
    spacing_menu = _menu(tile_box, st["vis_spacing"], [d for d, _ in SPACINGS], 3)
    spacing_menu.pack(side=tk.LEFT, padx=2)

    # single / seal 公共容器：3×3 位置网格
    single_box = tk.Frame(card3.body, bg=T.C_CARD)
    _lbl(single_box, "位置").pack(side=tk.LEFT, padx=(0, T.S_SM))
    pos_grid = tk.Frame(single_box, bg=T.C_CARD)
    pos_grid.pack(side=tk.LEFT)
    pos_btns = {}
    for idx, (arrow, pkey, pname) in enumerate(POSITIONS):
        r, c = divmod(idx, 3)
        b = tk.Button(pos_grid, text=arrow, width=2, height=1, relief=tk.FLAT, bd=1,
                      font=(T.FONT_FAMILY, T.F_BODY, "bold"),
                      command=lambda k=pname: _set_pos(k))
        b.grid(row=r, column=c, padx=1, pady=1)
        pos_btns[pname] = b
    pos_label = hint_label(single_box, "右下角")
    pos_label.pack(side=tk.LEFT, padx=T.S_SM)

    def _set_pos(pname: str) -> None:
        st["vis_pos"].set(pname)
        pos_label.config(text=pname)
        for name, btn in pos_btns.items():
            if name == pname:
                btn.config(bg=T.C_CYAN, fg="white")
            else:
                btn.config(bg=T.C_CARD, fg=T.C_TEXT_M)

    # seal 专属容器：圆/方框 + 大小
    seal_box = tk.Frame(card3.body, bg=T.C_CARD)
    _lbl(seal_box, "形状").pack(side=tk.LEFT)
    seal_menu = _menu(seal_box, st["seal_shape"], [d for d, _ in SEAL_SHAPES], 4)
    seal_menu.pack(side=tk.LEFT, padx=(2, T.S_MD))
    _lbl(seal_box, "印章大小").pack(side=tk.LEFT)
    _menu(seal_box, st["seal_size"], [d for d, _ in SEAL_SIZES], 3).pack(side=tk.LEFT, padx=2)

    # grid 专属容器：密度档
    grid_box = tk.Frame(card3.body, bg=T.C_CARD)
    _lbl(grid_box, "密度").pack(side=tk.LEFT)
    density_menu = _menu(grid_box, st["vis_density"], [d for d, _ in DENSITIES], 4)
    density_menu.pack(side=tk.LEFT, padx=(2, 0))
    hint_label(grid_box, "1×1 = 1 张；6×6 = 36 张；「自动」按间距计算"
               ).pack(side=tk.LEFT, padx=T.S_SM)

    def _sync_layout() -> None:
        """布局切换 → 显示对应参数容器 + 高亮风格卡片。"""
        for box in (tile_box, single_box, seal_box, grid_box):
            box.pack_forget()
        layout = st["vis_layout"].get()
        # 高亮卡片
        for key, (frame, label) in style_btns.items():
            if key == layout:
                frame.config(highlightbackground=T.C_CYAN, highlightthickness=2)
                label.config(fg=T.C_CYAN)
            else:
                frame.config(highlightbackground=T.C_BORDER, highlightthickness=1)
                label.config(fg=T.C_TEXT_M)
        if layout == "tile":
            tile_box.pack(fill=tk.X, pady=(T.S_SM, 0))
        elif layout == "grid":
            grid_box.pack(fill=tk.X, pady=(T.S_SM, 0))
        elif layout == "seal":
            single_box.pack(fill=tk.X, pady=(T.S_SM, 0))
            seal_box.pack(fill=tk.X, pady=(T.S_SM, 0))
        else:  # single
            single_box.pack(fill=tk.X, pady=(T.S_SM, 0))
        _set_pos(st["vis_pos"].get())  # 刷新位置按钮高亮
        app.request_relayout()

    # ---------- ④ 样式参数（颜色真色块 + 字号/透明度 + 描边阴影）----------
    card4 = Card(page, "④ 样式参数",
                 "颜色 / 字号 / 透明度 / 描边 / 阴影  ·  参考 2Dou 经典：暗黄 #D4A017 + 15%",
                 accent=T.C_WARNING)
    card4.pack(fill=tk.X, pady=(0, T.S_MD))

    # 颜色：真色块 swatch + 取色器 + hex
    cr = tk.Frame(card4.body, bg=T.C_CARD)
    cr.pack(fill=tk.X)
    _lbl(cr, "颜色").pack(side=tk.LEFT)

    def _set_color(hexv: str) -> None:
        st["vis_color"].set(hexv)
        swatch.config(bg=hexv)
        for name, (btn, h) in color_btns.items():
            if h.upper() == hexv.upper():
                btn.config(highlightbackground=T.C_ACCENT, highlightthickness=2)
            else:
                btn.config(highlightbackground=T.C_BORDER, highlightthickness=1)

    color_btns = {}
    for name, hexv in QUICK_COLORS:
        fg = "#000000" if name in ("暗黄", "亮黄", "白", "灰") else "#FFFFFF"
        b = tk.Frame(cr, width=22, height=22, bg=hexv, cursor="hand2",
                     highlightbackground=T.C_BORDER, highlightthickness=1)
        b.pack_propagate(False)
        b.pack(side=tk.LEFT, padx=2)
        tk.Label(b, text="", bg=hexv).pack(expand=True)
        b.bind("<Button-1>", lambda e, h=hexv: _set_color(h))
        color_btns[name] = (b, hexv)

    def _pick_color() -> None:
        rgb, hexv = colorchooser.askcolor(title="选择水印颜色",
                                          initialcolor=st["vis_color"].get())
        if hexv:
            _set_color(hexv.upper())

    secondary_button(cr, "🎨 取色器", command=_pick_color).pack(side=tk.LEFT,
                                                                padx=(T.S_SM, 0))
    swatch = tk.Frame(cr, width=18, height=18, bg=st["vis_color"].get(),
                      highlightbackground=T.C_BORDER, highlightthickness=1)
    swatch.pack(side=tk.LEFT, padx=T.S_SM)
    swatch.pack_propagate(False)
    tk.Entry(cr, textvariable=st["vis_color"], width=9, relief=tk.FLAT,
             bg=T.C_CARD, fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT)

    # 字号 / 透明度
    sr = tk.Frame(card4.body, bg=T.C_CARD)
    sr.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(sr, "字号").pack(side=tk.LEFT)
    size_menu = _menu(sr, st["vis_size"], [d for d, _ in SIZES], 3)
    size_menu.pack(side=tk.LEFT, padx=(2, 0))
    _lbl(sr, "透明度").pack(side=tk.LEFT, padx=(T.S_MD, 0))
    opacity_menu = _menu(sr, st["vis_opacity"], [d for d, _ in OPACITIES], 4)
    opacity_menu.pack(side=tk.LEFT, padx=2)
    _lbl(sr, "描边").pack(side=tk.LEFT, padx=(T.S_MD, 0))
    _check(sr, "", st["vis_stroke"]).pack(side=tk.LEFT)
    _lbl(sr, "阴影").pack(side=tk.LEFT, padx=(T.S_SM, 0))
    _check(sr, "", st["vis_shadow"]).pack(side=tk.LEFT)

    # ---------- ⑤ 盲水印（折叠默认）----------
    card5 = Card(page, "⑤ 盲水印（隐形）",
                 "肉眼不可见，嵌入版权信息；可见水印被抹掉后仍可提取取证",
                 accent=T.C_PURPLE, collapsible=True, start_collapsed=True)
    card5.pack(fill=tk.X, pady=(0, T.S_MD))

    bh = tk.Frame(card5.body, bg=T.C_CARD)
    bh.pack(fill=tk.X)
    _check(bh, "启用盲水印", st["blind_on"],
           command=lambda: _sync_blind()).pack(side=tk.LEFT)
    act = tk.Frame(bh, bg=T.C_CARD)
    act.pack(side=tk.LEFT, padx=T.S_LG)
    tk.Radiobutton(act, text="嵌入", variable=st["blind_action"], value="embed",
                   command=lambda: _sync_blind(), bg=T.C_CARD, fg=T.C_TEXT,
                   activebackground=T.C_CARD, activeforeground=T.C_ACCENT,
                   selectcolor=T.C_CARD, highlightthickness=0,
                   font=(T.FONT_FAMILY, T.F_BODY), anchor="w", cursor="hand2"
                   ).pack(side=tk.LEFT)
    tk.Radiobutton(act, text="提取", variable=st["blind_action"], value="extract",
                   command=lambda: _sync_blind(), bg=T.C_CARD, fg=T.C_TEXT,
                   activebackground=T.C_CARD, activeforeground=T.C_ACCENT,
                   selectcolor=T.C_CARD, highlightthickness=0,
                   font=(T.FONT_FAMILY, T.F_BODY), anchor="w", cursor="hand2"
                   ).pack(side=tk.LEFT, padx=T.S_MD)

    embed_box = tk.Frame(card5.body, bg=T.C_CARD)
    embed_box.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(embed_box, "盲水印文字").pack(side=tk.LEFT)
    tk.Entry(embed_box, textvariable=st["blind_text"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    pw_row = tk.Frame(card5.body, bg=T.C_CARD)
    pw_row.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(pw_row, "密码").pack(side=tk.LEFT)
    tk.Entry(pw_row, textvariable=st["blind_pw"], width=8, relief=tk.FLAT,
             bg=T.C_CARD, fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, padx=(T.S_SM, 0))
    hint_label(pw_row, "嵌入与提取必须用相同密码（整数）").pack(side=tk.LEFT, padx=T.S_SM)

    extract_box = tk.Frame(card5.body, bg=T.C_CARD)
    extract_box.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(extract_box, "水印长度").pack(side=tk.LEFT)
    tk.Entry(extract_box, textvariable=st["blind_len"], width=8, relief=tk.FLAT,
             bg=T.C_CARD, fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, padx=(T.S_SM, 0))
    hint_label(extract_box,
               "嵌入时自动回填；同一段文字长度相同，抗压缩请用高质量图片").pack(
        side=tk.LEFT, padx=T.S_SM)

    def _sync_blind() -> None:
        on = st["blind_on"].get()
        is_embed = st["blind_action"].get() == "embed"
        if is_embed:
            embed_box.pack(fill=tk.X, pady=(T.S_SM, 0))
            extract_box.pack_forget()
        else:
            extract_box.pack(fill=tk.X, pady=(T.S_SM, 0))
            embed_box.pack_forget()
        app.request_relayout()

    # ---------- ⑥ 输出位置 + 格式 ----------
    card6 = Card(page, "⑥ 输出位置", "输出到「<源目录>_水印输出」，绝不原地覆盖",
                 accent=T.C_SUCCESS)
    card6.pack(fill=tk.X, pady=(0, T.S_MD))
    orow = tk.Frame(card6.body, bg=T.C_CARD)
    orow.pack(fill=tk.X)
    tk.Entry(orow, textvariable=st["out_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True)
    secondary_button(orow, "📁 浏览", command=lambda: _pick_out()).pack(
        side=tk.LEFT, padx=(T.S_SM, 0))

    fmt_row = tk.Frame(card6.body, bg=T.C_CARD)
    fmt_row.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(fmt_row, "输出格式").pack(side=tk.LEFT)
    for label, val in OUT_FMTS:
        tk.Radiobutton(fmt_row, text=label, variable=st["out_fmt"], value=label,
                       bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                       activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                       highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                       anchor="w", cursor="hand2").pack(side=tk.LEFT, padx=T.S_SM)
    hint_label(fmt_row, "PNG 保留透明底且无损，JPG 体积小").pack(side=tk.LEFT, padx=T.S_SM)

    def _pick_out() -> None:
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            st["out_dir"].set(d)

    # ---------- 渲染参数 ----------
    def _vis_kwargs() -> dict:
        """读取 UI 状态 → apply_watermark 入参。"""
        layout = st["vis_layout"].get()
        kw = {
            "text": _vis_text(),
            "layout": layout,
            "position": POS_VALUE.get(st["vis_pos"].get(), watermark.DEFAULT_POSITION),
            "font_size_ratio": SIZE_VALUE.get(st["vis_size"].get(), 0.020),
            "color": st["vis_color"].get(),
            "opacity": OPACITY_VALUE.get(st["vis_opacity"].get(), 0.15),
            "logo_path": st["vis_logo"].get().strip(),
            "logo_position": POS_VALUE.get(st["logo_pos"].get(), "top_right"),
            "logo_ratio": LOGO_SIZE_VALUE.get(st["logo_size"].get(), 0.08),
            "stroke": 1 if st["vis_stroke"].get() else 0,
            "shadow": st["vis_shadow"].get(),
        }
        if layout == "tile":
            kw["angle"] = ANGLE_VALUE.get(st["vis_angle"].get(), 30)
            kw["spacing"] = SPACING_VALUE.get(st["vis_spacing"].get(), 1.0)
        elif layout == "grid":
            kw["angle"] = ANGLE_VALUE.get(st["vis_angle"].get(), 30)
            kw["spacing"] = SPACING_VALUE.get(st["vis_spacing"].get(), 1.0)
            kw["density"] = DENSITY_VALUE.get(st["vis_density"].get(), 0)
        elif layout == "seal":
            kw["seal_shape"] = SEAL_SHAPE_VALUE.get(st["seal_shape"].get(), "round")
            kw["seal_size_ratio"] = SEAL_SIZE_VALUE.get(st["seal_size"].get(), 0.22)
        return kw

    def _out_suffix() -> str:
        return ".png" if st["out_fmt"].get() == "PNG" else ".jpg"

    # ---------- 校验 ----------
    def _validate() -> bool:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个图片。")
            return False
        vis = st["vis_on"].get()
        blind = st["blind_on"].get()
        is_extract = blind and st["blind_action"].get() == "extract"
        if not vis and not blind:
            messagebox.showwarning("未选择功能", "请至少勾选可见水印或盲水印。")
            return False
        if not is_extract and not st["out_dir"].get().strip():
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return False
        if vis and not _vis_text():
            messagebox.showwarning("缺少文字", "请填写可见水印文字。")
            return False
        if blind and not is_extract and not st["blind_text"].get().strip():
            messagebox.showwarning("缺少文字", "请填写盲水印文字。")
            return False
        return True

    def _unique(dst: Path) -> Path:
        if not dst.exists():
            return dst
        for i in range(1, 1000):
            cand = dst.with_name(f"{dst.stem}_{i}{dst.suffix}")
            if not cand.exists():
                return cand
        return dst

    # ---------- 预览（不落盘）----------
    def _preview() -> None:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个图片。")
            return
        if not st["vis_on"].get():
            messagebox.showwarning("未启用", "请先勾选「添加可见水印」。")
            return
        if not _vis_text():
            messagebox.showwarning("缺少文字", "请填写可见水印文字。")
            return
        src = st["files"][0]
        try:
            src_bytes = src.read_bytes()
        except Exception as exc:
            messagebox.showerror("读取失败", f"{src.name}: {exc}")
            return
        try:
            kw = _vis_kwargs()
            out_bytes = watermark.apply_watermark(src_bytes, **kw)
        except Exception as exc:
            messagebox.showerror("预览失败", f"{exc}")
            return

        win = tk.Toplevel(app.root)
        win.title("水印预览（不落盘）")
        win.configure(bg=T.C_BG)
        _open_dialog(win, 1580, 900)

        header = vlabel(win, text=f"预览图：{src.name}（按当前参数渲染，不落盘）",
                        font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                        bg=T.C_BG, fg=T.C_TEXT, anchor="w")
        header.pack(fill=tk.X, padx=T.S_LG, pady=(T.S_MD, T.S_SM))

        layout = kw["layout"]
        layout_name = {"tile": "斜向平铺", "grid": "平铺密度网格",
                       "single": "角落单处", "seal": "印章风格"}.get(layout, layout)
        param_text = (f"风格：{layout_name}    颜色：{kw['color']}    "
                      f"透明度：{int(kw['opacity']*100)}%    "
                      f"字号：{kw['font_size_ratio']:.3f}")
        if layout in ("tile", "grid"):
            param_text += f"    角度：{int(kw.get('angle', 30))}°    间距：{kw.get('spacing', 1.0)}"
            if layout == "grid":
                param_text += f"    密度：{st['vis_density'].get()}"
        elif layout == "seal":
            param_text += f"    形状：{st['seal_shape'].get()}    位置：{st['vis_pos'].get()}"
        elif layout == "single":
            param_text += f"    位置：{st['vis_pos'].get()}"
        hint_label(win, param_text).pack(fill=tk.X, padx=T.S_LG, pady=(0, T.S_SM))

        body = tk.Frame(win, bg=T.C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=T.S_LG, pady=T.S_SM)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        for col, raw_bytes, title in (
                (0, src_bytes, "原图"), (1, out_bytes, "预览")):
            try:
                photo = _preview_image_for_tk(raw_bytes, max_w=480)
            except Exception:
                photo = None
            cell = tk.Frame(body, bg=T.C_BG)
            cell.grid(row=0, column=col, sticky="nsew", padx=T.S_SM)
            vlabel(cell, text=title,
                   font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                   bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X)
            if photo is not None:
                lbl = tk.Label(cell, image=photo, bg=T.C_BG, bd=1,
                              highlightbackground=T.C_BORDER,
                              highlightthickness=1)
                lbl.image = photo
                lbl.pack(pady=(T.S_SM, 0))
            else:
                vlabel(cell, text="（图片加载失败）",
                       bg=T.C_BG, fg=T.C_DANGER, anchor="w").pack(pady=T.S_SM)

        dialog_buttons(win, T.C_BG, win.destroy)
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    # ---------- 预览确认弹窗 ----------
    def _open_confirm() -> None:
        if not _validate():
            return
        is_extract = st["blind_on"].get() and st["blind_action"].get() == "extract"
        suffix = _out_suffix()

        plans: list[SimpleNamespace] = []
        for src in st["files"]:
            try:
                if is_extract:
                    dst_name = src.name
                else:
                    dst_name = src.stem + suffix
                plans.append(SimpleNamespace(
                    src=src, dst_name=dst_name,
                    src_size=scanner.file_size(src), blocked=False, status="ok"))
            except Exception as exc:
                plans.append(SimpleNamespace(
                    src=src, dst_name=src.name, src_size=0,
                    blocked=True, status="error", err=str(exc)))

        out_dir = Path(st["out_dir"].get().strip())
        win = tk.Toplevel(app.root)
        win.title("水印结果预览")
        win.configure(bg=T.C_BG)
        _open_dialog(win, 1580, 900)
        vlabel(win,
               text=f"共 {len(plans)} 个文件 → {out_dir}",
               font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
               bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                        padx=T.S_LG, pady=(T.S_MD, T.S_SM))
        tv, _box = dialog_tree(win, PREVIEW_COLS, T.C_BG)
        for plan in plans:
            tv.insert("", "end",
                      values=(plan.src.name, plan.dst_name,
                              scanner.fmt_size(plan.src_size), "✓ 正常"))

        dialog_buttons(win, T.C_BG, win.destroy, on_confirm=lambda: _confirm_run(plans))

    def _confirm_run(plans) -> None:
        for w in app.root.winfo_children():
            if type(w).__name__ == "Toplevel" and w.title() == "水印结果预览":
                w.destroy()
                break

        vis = st["vis_on"].get()
        blind = st["blind_on"].get()
        is_extract = blind and st["blind_action"].get() == "extract"
        embed = blind and not is_extract
        out_dir = Path(st["out_dir"].get().strip()) if not is_extract else None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
        suffix = _out_suffix()

        cancel_event = threading.Event()
        st["cancel"] = cancel_event
        bar_btn_run.config(state=tk.DISABLED)
        bar_btn_cancel.config(state=tk.NORMAL)
        progress.pack(fill=tk.X, pady=(T.S_SM, 0))
        progress["value"] = 0
        progress["maximum"] = len(st["files"])
        app.set_status("正在处理…")

        vis_kwargs = _vis_kwargs() if vis else {}
        pw = st["blind_pw"].get().strip() or "1"
        blind_text = st["blind_text"].get().strip()

        def _worker() -> None:
            done = failed = 0
            errors, plans_out, done_names, extracted = [], [], [], []
            blind_len = None
            for idx, src in enumerate(st["files"]):
                if cancel_event.is_set():
                    break
                name = src.name
                try:
                    if is_extract:
                        wlen = st["blind_len"].get().strip()
                        txt = blind_wm.extract_watermark(src, wlen, password_wm=pw)
                        extracted.append((name, txt))
                        done += 1
                    else:
                        data = src.read_bytes()
                        stem = src.stem
                        if embed:
                            with tempfile.NamedTemporaryFile(
                                    suffix=".png", delete=False) as tmp:
                                blind_path = Path(tmp.name)
                            try:
                                blind_len = blind_wm.embed_watermark(
                                    src, str(blind_path), blind_text,
                                    password_wm=pw)
                                data = blind_path.read_bytes()
                            finally:
                                try:
                                    blind_path.unlink()
                                except OSError:
                                    pass
                        if vis and vis_kwargs.get("text"):
                            data = watermark.apply_watermark(data, **vis_kwargs)
                        out_name = stem + suffix
                        dst = _unique(out_dir / out_name)
                        dst.write_bytes(data)
                        plans_out.append(SimpleNamespace(src=src, dst_name=dst.name))
                        done_names.append(dst.name)
                        done += 1
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
                    failed += 1
                    errors.append(f"{name}: {exc}")

                def _ui(d=idx + 1, n=name):
                    progress["value"] = d
                    bar_state.config(text=f"{d}/{len(st['files'])} {n}")
                app.safe_after(0, _ui)

            result = {"done": done, "failed": failed, "errors": errors,
                      "done_names": done_names}
            app.safe_after(0, lambda: _finish(result, plans_out, out_dir,
                                              blind_len, extracted))

        def _finish(result, plans_out, out_dir, blind_len, extracted):
            st["cancel"] = None
            progress.pack_forget()
            bar_btn_cancel.config(state=tk.DISABLED)
            bar_btn_run.config(state=tk.NORMAL)
            if blind_len is not None:
                st["blind_len"].set(str(blind_len))
                app.cfg.set("watermark.blind_len", blind_len)
            for key in ("vis_on", "vis_layout", "vis_pos", "vis_angle", "vis_size",
                        "vis_color", "vis_opacity", "vis_spacing", "vis_density",
                        "seal_shape", "seal_size", "vis_stroke", "vis_shadow",
                        "vis_logo", "logo_pos", "logo_size", "out_fmt",
                        "blind_on", "blind_text", "blind_pw"):
                v = st[key].get()
                app.cfg.set(f"watermark.{key}", v if not isinstance(v, bool) else int(v))
            app.cfg.set("watermark.vis_text", _vis_text())
            if plans_out:
                history.record_batch("watermark", out_dir, plans_out, result)
                app.cfg.set("output.last_dir", str(out_dir))
            app.cfg.save()
            kind = "ok" if not result["failed"] else "warn"
            bar_state.config(text=f"完成 {result['done']}/{len(st['files'])}")
            app.set_status(f"完成 {result['done']}，失败 {result['failed']}", kind)
            if is_extract:
                _show_extract(extracted)
                return
            msg = (f"完成 {result['done']} 个，失败 {result['failed']} 个\n"
                   f"输出目录：{out_dir}")
            if blind_len is not None:
                msg += f"\n\n盲水印长度：{blind_len}（提取时需要，已自动回填）"
            if result["errors"]:
                msg += "\n\n" + "\n".join(result["errors"][:10])
            messagebox.showinfo("处理完成", msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_extract(extracted):
        win = tk.Toplevel(app.root)
        win.title("盲水印提取结果")
        win.configure(bg=T.C_BG)
        fit_dialog(win, 780, 520)
        vlabel(win, text=f"共提取 {len(extracted)} 张图片的盲水印",
               font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
               bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                        padx=T.S_LG, pady=T.S_MD)
        cols = [("file", "文件", 260, "w"), ("wm", "提取的盲水印", 440, "w")]
        tv, _box = dialog_tree(win, cols, T.C_BG)
        for fname, txt in extracted:
            tv.insert("", "end", values=(fname, txt))
        dialog_buttons(win, T.C_BG, win.destroy)

    # ---------- 底部操作栏 ----------
    bar = tk.Frame(app.content, bg=T.C_BG)
    left = tk.Frame(bar, bg=T.C_BG)
    left.pack(side=tk.LEFT)
    secondary_button(left, "↩ 撤销", command=app.undo_last_batch).pack(side=tk.LEFT)
    bar_state = vlabel(left, text="", font=(T.FONT_FAMILY, T.F_SM),
                       bg=T.C_BG, fg=T.C_TEXT_L)
    bar_state.pack(side=tk.LEFT, padx=T.S_SM)
    right = tk.Frame(bar, bg=T.C_BG)
    right.pack(side=tk.RIGHT)
    bar_btn_cancel = secondary_button(right, "✖ 取消", state=tk.DISABLED,
                                      command=lambda: st["cancel"].set()
                                      if st["cancel"] else None)
    bar_btn_cancel.pack(side=tk.LEFT, padx=(0, T.S_SM))
    secondary_button(right, "👁 预览", command=lambda: _preview()).pack(
        side=tk.LEFT, padx=(0, T.S_SM))
    bar_btn_run = primary_button(right, "▶ 开始执行", command=lambda: _open_confirm())
    bar_btn_run.pack(side=tk.LEFT)
    progress = ttk.Progressbar(bar, style="RenameMaster.Horizontal.TProgressbar",
                               mode="determinate", maximum=1, value=0)

    key = next((k for k, v in app.pages.items() if v is page), "watermark")
    page.set_source_dir = set_source_dir
    page.st = st
    page.vis_text_box = vis_text_box
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
    _sync_layout()
    _sync_blind()
    _sync_vis_enabled()
    _refresh_tree()
    # 如果有已选 LOGO，显示 LOGO 选项行
    if st["vis_logo"].get():
        logo_opts.pack(fill=tk.X, pady=(T.S_SM, 0))
    _set_color(st["vis_color"].get())  # 初始化颜色选中态
    app.set_status("就绪")
