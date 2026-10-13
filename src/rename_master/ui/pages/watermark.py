"""水印页：批量添加可见水印（斜向平铺 / 角落单处）+ 隐形盲水印（嵌入 / 提取）。

- 可见水印：任意颜色（取色器）、旋转角度、字号、透明度、间距、描边、阴影，可叠加 LOGO；
- 盲水印：GitHub guofei9987/blind_watermark 频域方案，肉眼不可见，抗压缩 / 格式转换；
- 可同时「先嵌盲水印 + 再叠可见水印」，双保险。
"""
from __future__ import annotations

import threading
import tkinter as tk
import tempfile
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from types import SimpleNamespace

from rename_master.core import history, scanner, watermark, blind_wm
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree, vlabel, enable_label_copy)

IMAGE_FILETYPES = [("图片文件", "*.jpg *.jpeg *.png *.bmp *.heic"),
                   ("所有文件", "*.*")]
LOGO_FILETYPES = [("LOGO 图片", "*.png *.jpg *.jpeg *.bmp"),
                  ("所有文件", "*.*")]

# 可见水印位置（显示文案, position）
POSITIONS = [("右下角", "bottom_right"), ("左下角", "bottom_left"),
             ("右上角", "top_right"), ("左上角", "top_left"),
             ("底部居中", "bottom_center"), ("顶部居中", "top_center"),
             ("左中", "center_left"), ("右中", "center_right"),
             ("居中", "center")]
POS_VALUE = dict(POSITIONS)
ANGLES = [("15°", 15), ("30°", 30), ("45°", 45), ("60°", 60), ("0°", 0), ("90°", 90)]
ANGLE_VALUE = dict(ANGLES)
SIZES = [("小", 0.012), ("中", 0.020), ("大", 0.035)]
SIZE_VALUE = dict(SIZES)
OPACITIES = [("20%", 0.2), ("30%", 0.3), ("40%", 0.4), ("60%", 0.6), ("80%", 0.8)]
OPACITY_VALUE = dict(OPACITIES)
SPACINGS = [("密", 0.7), ("中", 1.0), ("疏", 1.4)]
SPACING_VALUE = dict(SPACINGS)
# 快捷颜色（显示名, hex）
QUICK_COLORS = [("白", "#FFFFFF"), ("黑", "#000000"), ("红", "#FF2D55"),
                ("黄", "#FFD60A"), ("蓝", "#1E6FFF"), ("青", "#00E5FF"),
                ("灰", "#9AA3AF")]

FILE_COLS = [("sel", "☑", 40, tk.CENTER), ("name", "文件名", 300, "w"),
             ("size", "大小", 90, tk.CENTER), ("dim", "尺寸", 130, tk.CENTER)]


def _check(master, text: str, variable: tk.Variable, command=None) -> tk.Checkbutton:
    w = tk.Checkbutton(master, text=text, variable=variable, command=command,
                       bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                       activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                       highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                       anchor="w", cursor="hand2")
    enable_label_copy(w)
    return w


def _radio(master, text: str, variable: tk.Variable, value: str, command=None) -> tk.Radiobutton:
    w = tk.Radiobutton(master, text=text, variable=variable, value=value,
                       command=command, bg=T.C_CARD, fg=T.C_TEXT,
                       activebackground=T.C_CARD, activeforeground=T.C_ACCENT,
                       selectcolor=T.C_CARD, highlightthickness=0,
                       font=(T.FONT_FAMILY, T.F_BODY), anchor="w", cursor="hand2")
    enable_label_copy(w)
    return w


def _menu(master, variable, options, width=6):
    w = tk.OptionMenu(master, variable, *options)
    w.config(width=width)
    return w


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "添加水印",
               "可见水印（斜向平铺 / 角落单处，任意颜色）+ 隐形盲水印（嵌入版权信息、提取取证）")

    # ---------- 页面状态 ----------
    st = {
        "files": [],
        "src_dir": tk.StringVar(value=""),
        # 可见水印
        "vis_on": tk.BooleanVar(value=bool(app.cfg.get("watermark.vis_on", True))),
        "vis_text": tk.StringVar(value=app.cfg.get("watermark.vis_text", "曲靖联通 陈琼")),
        "vis_layout": tk.StringVar(value=app.cfg.get("watermark.vis_layout", "tile")),
        "vis_pos": tk.StringVar(value=app.cfg.get("watermark.vis_pos", "右下角")),
        "vis_angle": tk.StringVar(value=app.cfg.get("watermark.vis_angle", "30°")),
        "vis_size": tk.StringVar(value=app.cfg.get("watermark.vis_size", "中")),
        "vis_color": tk.StringVar(value=app.cfg.get("watermark.vis_color", "#1E6FFF")),
        "vis_opacity": tk.StringVar(value=app.cfg.get("watermark.vis_opacity", "40%")),
        "vis_spacing": tk.StringVar(value=app.cfg.get("watermark.vis_spacing", "中")),
        "vis_stroke": tk.BooleanVar(value=bool(app.cfg.get("watermark.vis_stroke", True))),
        "vis_shadow": tk.BooleanVar(value=bool(app.cfg.get("watermark.vis_shadow", False))),
        "vis_logo": tk.StringVar(value=str(app.cfg.get("watermark.vis_logo", ""))),
        # 盲水印
        "blind_on": tk.BooleanVar(value=bool(app.cfg.get("watermark.blind_on", False))),
        "blind_action": tk.StringVar(value="embed"),
        "blind_text": tk.StringVar(value=app.cfg.get("watermark.blind_text",
                                                     "曲靖联通陈琼20261013")),
        "blind_len": tk.StringVar(value=str(app.cfg.get("watermark.blind_len", 208))),
        "blind_pw": tk.StringVar(value=str(app.cfg.get("watermark.blind_pw", 1))),
        "out_dir": tk.StringVar(value=""),
        "cancel": None,
    }
    app.selected_files = st["files"]

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

    tree = styled_tree(card1.body, FILE_COLS, height=7)
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

    # ---------- ② 可见水印 ----------
    card2 = Card(page, "② 可见水印", "斜向平铺（推荐，裁不掉）或角落单处；任意颜色 + 描边 / 阴影",
                 accent=T.C_INFO, collapsible=True, start_collapsed=False)
    card2.pack(fill=tk.X, pady=(0, T.S_MD))

    top = tk.Frame(card2.body, bg=T.C_CARD)
    top.pack(fill=tk.X)
    _check(top, "☑ 添加可见水印", st["vis_on"],
           command=lambda: _sync_vis()).pack(side=tk.LEFT)
    lr = tk.Frame(top, bg=T.C_CARD)
    lr.pack(side=tk.LEFT, padx=T.S_LG)
    _radio(lr, "斜向平铺", st["vis_layout"], "tile",
           command=lambda: _sync_layout()).pack(side=tk.LEFT)
    _radio(lr, "角落单处", st["vis_layout"], "single",
           command=lambda: _sync_layout()).pack(side=tk.LEFT, padx=T.S_MD)

    # 水印文字
    tr = tk.Frame(card2.body, bg=T.C_CARD)
    tr.pack(fill=tk.X, pady=(T.S_SM, 0))
    vlabel(tr, text="水印文字", font=(T.FONT_FAMILY, T.F_BODY),
           bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(tr, textvariable=st["vis_text"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    # 颜色：快捷色块 + 取色器 + hex
    cr = tk.Frame(card2.body, bg=T.C_CARD)
    cr.pack(fill=tk.X, pady=(T.S_SM, 0))
    vlabel(cr, text="颜色", font=(T.FONT_FAMILY, T.F_BODY),
           bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)

    def _set_color(hexv: str) -> None:
        st["vis_color"].set(hexv)
        swatch.config(bg=hexv)

    for name, hexv in QUICK_COLORS:
        b = tk.Button(cr, text=name, width=2, relief=tk.FLAT, bd=0,
                      bg=hexv, fg=("#000000" if name in ("白", "黄", "灰") else "#FFFFFF"),
                      cursor="hand2",
                      command=lambda h=hexv: _set_color(h))
        b.pack(side=tk.LEFT, padx=1)

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

    # 平铺参数：角度 / 字号 / 间距 / 透明度 / 描边 / 阴影
    tile_box = tk.Frame(card2.body, bg=T.C_CARD)
    tile_box.pack(fill=tk.X, pady=(T.S_SM, 0))

    def _lbl(parent, text):
        return vlabel(parent, text=text, font=(T.FONT_FAMILY, T.F_BODY),
                      bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w")

    _lbl(tile_box, "角度").pack(side=tk.LEFT)
    angle_menu = _menu(tile_box, st["vis_angle"], [d for d, _ in ANGLES], 4)
    angle_menu.pack(side=tk.LEFT, padx=(2, 0))
    _lbl(tile_box, "字号").pack(side=tk.LEFT, padx=(T.S_MD, 0))
    size_menu = _menu(tile_box, st["vis_size"], [d for d, _ in SIZES], 3)
    size_menu.pack(side=tk.LEFT, padx=2)
    _lbl(tile_box, "间距").pack(side=tk.LEFT, padx=(T.S_MD, 0))
    spacing_menu = _menu(tile_box, st["vis_spacing"], [d for d, _ in SPACINGS], 3)
    spacing_menu.pack(side=tk.LEFT, padx=2)
    _lbl(tile_box, "透明度").pack(side=tk.LEFT, padx=(T.S_MD, 0))
    opacity_menu = _menu(tile_box, st["vis_opacity"], [d for d, _ in OPACITIES], 4)
    opacity_menu.pack(side=tk.LEFT, padx=2)
    _check(tile_box, "描边", st["vis_stroke"]).pack(side=tk.LEFT, padx=(T.S_MD, 0))
    _check(tile_box, "阴影", st["vis_shadow"]).pack(side=tk.LEFT)

    # 单处参数：位置
    single_box = tk.Frame(card2.body, bg=T.C_CARD)
    pos_menu = _menu(single_box, st["vis_pos"], [d for d, _ in POSITIONS], 8)
    _lbl(single_box, "位置").pack(side=tk.LEFT)
    pos_menu.pack(side=tk.LEFT, padx=(2, 0))

    # LOGO
    logo_row = tk.Frame(card2.body, bg=T.C_CARD)
    logo_row.pack(fill=tk.X, pady=(T.S_SM, 0))
    logo_btn = secondary_button(logo_row, "🖼 选择 LOGO", command=lambda: _pick_logo())
    logo_btn.pack(side=tk.LEFT)
    logo_label = hint_label(logo_row, "可选：未选择 LOGO")
    logo_label.pack(side=tk.LEFT, padx=T.S_SM)
    if st["vis_logo"].get():
        logo_label.config(text=f"LOGO：{st['vis_logo'].get()}")

    def _pick_logo() -> None:
        p = filedialog.askopenfilename(title="选择 LOGO 图片", filetypes=LOGO_FILETYPES)
        if p:
            st["vis_logo"].set(p)
            logo_label.config(text=f"LOGO：{p}")

    vis_controls = [angle_menu, size_menu, spacing_menu, opacity_menu, pos_menu, logo_btn]
    vis_labels = [w for w in card2.winfo_children()]

    def _sync_layout() -> None:
        if st["vis_layout"].get() == "tile":
            tile_box.pack(fill=tk.X, pady=(T.S_SM, 0))
            single_box.pack_forget()
        else:
            single_box.pack(fill=tk.X, pady=(T.S_SM, 0))
            single_box.winfo_children()
            tile_box.pack_forget()
        app.request_relayout()

    def _sync_vis() -> None:
        on = st["vis_on"].get()
        state = tk.NORMAL if on else tk.DISABLED
        for w in vis_controls:
            w.config(state=state)
        app.request_relayout()

    # ---------- ③ 盲水印 ----------
    card3 = Card(page, "③ 盲水印（隐形）",
                 "肉眼不可见，嵌入版权信息；可见水印被抹掉后仍可提取取证",
                 accent=T.C_WARNING, collapsible=True, start_collapsed=True)
    card3.pack(fill=tk.X, pady=(0, T.S_MD))

    bh = tk.Frame(card3.body, bg=T.C_CARD)
    bh.pack(fill=tk.X)
    _check(bh, "☑ 启用盲水印", st["blind_on"],
           command=lambda: _sync_blind()).pack(side=tk.LEFT)
    act = tk.Frame(bh, bg=T.C_CARD)
    act.pack(side=tk.LEFT, padx=T.S_LG)
    _radio(act, "嵌入", st["blind_action"], "embed",
           command=lambda: _sync_blind()).pack(side=tk.LEFT)
    _radio(act, "提取", st["blind_action"], "extract",
           command=lambda: _sync_blind()).pack(side=tk.LEFT, padx=T.S_MD)

    embed_box = tk.Frame(card3.body, bg=T.C_CARD)
    embed_box.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(embed_box, "盲水印文字").pack(side=tk.LEFT)
    tk.Entry(embed_box, textvariable=st["blind_text"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    pw_row = tk.Frame(card3.body, bg=T.C_CARD)
    pw_row.pack(fill=tk.X, pady=(T.S_SM, 0))
    _lbl(pw_row, "密码").pack(side=tk.LEFT)
    tk.Entry(pw_row, textvariable=st["blind_pw"], width=8, relief=tk.FLAT,
             bg=T.C_CARD, fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, padx=(T.S_SM, 0))
    hint_label(pw_row, "嵌入与提取必须用相同密码（整数）").pack(side=tk.LEFT, padx=T.S_SM)

    extract_box = tk.Frame(card3.body, bg=T.C_CARD)
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
        state = tk.NORMAL if on else tk.DISABLED
        app.request_relayout()

    # ---------- ④ 输出位置 ----------
    card4 = Card(page, "④ 输出位置", "输出到「<源目录>_水印输出」，绝不原地覆盖",
                 accent=T.C_SUCCESS)
    card4.pack(fill=tk.X, pady=(0, T.S_MD))
    orow = tk.Frame(card4.body, bg=T.C_CARD)
    orow.pack(fill=tk.X)
    tk.Entry(orow, textvariable=st["out_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True)
    secondary_button(orow, "📁 浏览", command=lambda: _pick_out()).pack(
        side=tk.LEFT, padx=(T.S_SM, 0))

    def _pick_out() -> None:
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            st["out_dir"].set(d)

    # ---------- 校验 / 执行 ----------
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
        if vis and not st["vis_text"].get().strip():
            messagebox.showwarning("缺少文字", "请填写可见水印文字。")
            return False
        if blind and not is_extract and not st["blind_text"].get().strip():
            messagebox.showwarning("缺少文字", "请填写盲水印文字。")
            return False
        return True

    def _run() -> None:
        if not _validate():
            return
        vis = st["vis_on"].get()
        blind = st["blind_on"].get()
        is_extract = blind and st["blind_action"].get() == "extract"
        embed = blind and not is_extract
        out_dir = Path(st["out_dir"].get().strip()) if not is_extract else None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)

        cancel_event = threading.Event()
        st["cancel"] = cancel_event
        bar_btn_run.config(state=tk.DISABLED)
        bar_btn_cancel.config(state=tk.NORMAL)
        progress.pack(fill=tk.X, pady=(T.S_SM, 0))
        progress["value"] = 0
        progress["maximum"] = len(st["files"])
        app.set_status("正在处理…")

        vis_kwargs = {
            "text": st["vis_text"].get().strip(),
            "layout": st["vis_layout"].get(),
            "position": POS_VALUE.get(st["vis_pos"].get(), watermark.DEFAULT_POSITION),
            "angle": ANGLE_VALUE.get(st["vis_angle"].get(), 30),
            "font_size_ratio": SIZE_VALUE.get(st["vis_size"].get(), 0.02),
            "color": st["vis_color"].get(),
            "opacity": OPACITY_VALUE.get(st["vis_opacity"].get(), 0.4),
            "spacing": SPACING_VALUE.get(st["vis_spacing"].get(), 1.0),
            "stroke": 1 if st["vis_stroke"].get() else 0,
            "shadow": st["vis_shadow"].get(),
            "logo_path": st["vis_logo"].get().strip(),
            "logo_position": "top_left",
        }
        pw = st["blind_pw"].get().strip() or "1"
        blind_text = st["blind_text"].get().strip()

        def _worker() -> None:
            done = failed = 0
            errors, extracted, plans, done_names = [], [], [], []
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
                            # 先嵌盲水印到临时 PNG（必须先做，保证水印完整）
                            with tempfile.NamedTemporaryFile(
                                    suffix=".png", delete=False) as tmp:
                                blind_path = tmp.name
                            blind_len = blind_wm.embed_watermark(
                                src, blind_path, blind_text, password_wm=pw)
                            data = Path(blind_path).read_bytes()
                            try:
                                Path(blind_path).unlink()
                            except OSError:
                                pass
                            if vis:
                                data = watermark.apply_watermark(data, **vis_kwargs)
                                out_name = stem + ".jpg"
                            else:
                                out_name = stem + ".png"
                        else:
                            data = watermark.apply_watermark(data, **vis_kwargs)
                            out_name = stem + ".jpg"
                        dst = _unique(out_dir / out_name)
                        dst.write_bytes(data)
                        plans.append(SimpleNamespace(src=src, dst_name=out_name))
                        done_names.append(out_name)
                        done += 1
                except Exception as exc:          # noqa: BLE001 单张失败不中断
                    import traceback
                    traceback.print_exc()
                    failed += 1
                    errors.append(f"{name}: {exc}")
                    app.safe_after(0, lambda n=name: app.set_status(
                        f"失败：{n}", "err"))

                def _ui(d=idx + 1, n=name):
                    progress["value"] = d
                    bar_state.config(text=f"{d}/{len(st['files'])} {n}")
                app.safe_after(0, _ui)

            result = {"done": done, "failed": failed, "errors": errors,
                      "done_names": done_names}
            app.safe_after(0, lambda: _finish(result, plans, extracted,
                                              out_dir, blind_len))

        def _finish(result, plans, extracted, out_dir, blind_len):
            st["cancel"] = None
            progress.pack_forget()
            bar_btn_cancel.config(state=tk.DISABLED)
            bar_btn_run.config(state=tk.NORMAL)
            # 回填盲水印长度，便于同批提取
            if blind_len is not None:
                st["blind_len"].set(str(blind_len))
                app.cfg.set("watermark.blind_len", blind_len)
            # 保存偏好
            for key in ("vis_on", "vis_text", "vis_layout", "vis_pos", "vis_angle",
                        "vis_size", "vis_color", "vis_opacity", "vis_spacing",
                        "vis_stroke", "vis_shadow", "vis_logo", "blind_on",
                        "blind_text", "blind_pw"):
                v = st[key].get()
                app.cfg.set(f"watermark.{key}", v if not isinstance(v, bool) else int(v))
            if out_dir is not None and plans:
                history.record_batch("watermark", out_dir, plans, result)
                app.cfg.set("output.last_dir", str(out_dir))
            app.cfg.save()
            kind = "ok" if not result["failed"] else "warn"
            bar_state.config(text=f"完成 {result['done']}/{len(st['files'])}")
            app.set_status(f"完成 {result['done']}，失败 {result['failed']}", kind)

            if is_extract:
                _show_extract(extracted, result)
            else:
                msg = (f"完成 {result['done']} 个，失败 {result['failed']} 个\n"
                       f"输出目录：{out_dir}")
                if blind_len is not None:
                    msg += f"\n\n盲水印长度：{blind_len}（提取时需要，已自动回填）"
                if result["errors"]:
                    msg += "\n\n" + "\n".join(result["errors"][:10])
                messagebox.showinfo("处理完成", msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _unique(dst: Path) -> Path:
        if not dst.exists():
            return dst
        for i in range(1, 1000):
            cand = dst.with_name(f"{dst.stem}_{i}{dst.suffix}")
            if not cand.exists():
                return cand
        return dst

    def _show_extract(extracted, result):
        win = tk.Toplevel(app.root)
        win.title("盲水印提取结果")
        win.geometry("640x420")
        win.configure(bg=T.C_BG)
        vlabel(win, text=f"共提取 {len(extracted)} 张图片的盲水印",
               font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
               bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                        padx=T.S_LG, pady=T.S_MD)
        tv = styled_tree(win, [("file", "文件", 260, "w"), ("wm", "提取的盲水印", 340, "w")],
                         height=14)
        sb = ttk.Scrollbar(win, orient="vertical",
                           style="RenameMaster.Vertical.TScrollbar", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, T.S_LG))
        tv.pack(fill=tk.BOTH, expand=True, padx=(T.S_LG, 0))
        for fname, txt in extracted:
            tv.insert("", "end", values=(fname, txt))
        secondary_button(win, "关闭", command=win.destroy).pack(
            anchor="e", padx=T.S_LG, pady=T.S_MD)

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
    bar_btn_run = primary_button(right, "▶ 开始处理", command=lambda: _run())
    bar_btn_run.pack(side=tk.LEFT)
    progress = ttk.Progressbar(bar, style="RenameMaster.Horizontal.TProgressbar",
                               mode="determinate", maximum=1, value=0)

    key = next((k for k, v in app.pages.items() if v is page), "watermark")
    page.set_source_dir = set_source_dir
    page.st = st                         # 暴露页面状态，供测试 / 调试直接读写
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
    _sync_vis()
    _sync_blind()
    _refresh_tree()
    app.set_status("就绪")
