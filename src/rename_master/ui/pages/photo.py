"""照片批量命名页：选文件 → 命名模式 → 压缩 → 输出 → 预览 / 执行（任务书 §4.6.2）。"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rename_master.core import (compressor, history, mapper, renamer, scanner)
from rename_master.ui import advanced, theme as T
from rename_master.ui.widgets import (Card, PageHeader, dialog_buttons,
                                      dialog_tree, fit_dialog, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree, vlabel, enable_label_copy)

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

FILE_COLS = [("sel", "☑", 40, tk.CENTER), ("name", "文件名", 280, "w"),
             ("size", "大小", 90, tk.CENTER), ("dim", "尺寸", 120, tk.CENTER)]
PREVIEW_COLS = [("old", "原文件名", 220, "w"), ("new", "新文件名", 220, "w"),
                ("old_size", "原大小", 90, tk.CENTER),
                ("new_size", "预计新大小", 100, tk.CENTER),
                ("status", "状态", 80, tk.CENTER)]
STATUS_COLOR = {"ok": T.C_SUCCESS, "warn": T.C_WARNING, "error": T.C_DANGER}


def _radio(master, text: str, variable: tk.Variable, value: str, command=None) -> tk.Radiobutton:
    """卡片内统一风格的单选钮（白底，避免 ttk 主题在 Win 上的灰块）。"""
    w = tk.Radiobutton(master, text=text, variable=variable, value=value,
                          command=command, bg=T.C_CARD, fg=T.C_TEXT,
                          activebackground=T.C_CARD, activeforeground=T.C_ACCENT,
                          selectcolor=T.C_CARD, highlightthickness=0,
                          font=(T.FONT_FAMILY, T.F_BODY), anchor="w", cursor="hand2")
    return w


def _check(master, text: str, variable: tk.Variable, command=None):
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
        "out_dir": tk.StringVar(value=""),
        "cancel": None,       # threading.Event，执行中非 None
        "adv": advanced.create_vars(app, "photo"),
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
    vlabel(src_row, text="源目录", font=(T.FONT_FAMILY, T.F_BODY),
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
    vlabel(drow, text="选择文件夹", font=(T.FONT_FAMILY, T.F_BODY),
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
    vlabel(prow, text="基础名称", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(prow, textvariable=st["base"], relief=tk.FLAT,
             bg=T.C_CARD, fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    prow2 = tk.Frame(prefix_box, bg=T.C_CARD)
    prow2.pack(fill=tk.X, pady=(T.S_SM, 0))
    vlabel(prow2, text="位数", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    digits_menu = tk.OptionMenu(prow2, st["digits"], "3", "4", "5")
    digits_menu.config(width=2)
    digits_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    vlabel(prow2, text="起始", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Spinbox(prow2, from_=0, to=99999, textvariable=st["start"],
               width=4).pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    vlabel(prow2, text="分隔符", font=(T.FONT_FAMILY, T.F_BODY),
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
        app.request_relayout()

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
    vlabel(crow, text="KB", font=(T.FONT_FAMILY, T.F_BODY),
             bg=T.C_CARD, fg=T.C_TEXT_M).pack(side=tk.LEFT, padx=(T.S_XS, T.S_SM))
    _hl = hint_label(crow, "选中「自定义」时按此值压缩")
    _hl.pack(side=tk.LEFT)
    _check(card3.body, "保留 EXIF", st["keep_exif"]).pack(fill=tk.X, pady=(T.S_SM, 0))

    def _sync_target() -> None:
        pass  # 自定义 Entry 常显，取值时再判断；保留钩子便于后续禁用态扩展

    advanced.build_card(page, app, st["adv"])

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
            rule = {"mapping": dict(st["mapping"]),
                    "keep_ext": st["keep_ext"].get()}
        else:
            try:
                start = int(str(st["start"].get()).strip())
            except ValueError:
                start = 1
            try:
                digits = int(str(st["digits"].get()).strip())
            except ValueError:
                digits = 3
            rule = {"base_name": st["base"].get().strip(), "digits": digits,
                    "start": start, "sep": st["sep"].get(),
                    "keep_ext": st["keep_ext"].get()}
        return advanced.apply_to_rule(rule, st["adv"])

    def _make_plans():
        mode = renamer.MODE_MAP if st["mode"].get() == "map" else renamer.MODE_PREFIX
        return renamer.plan_rename(st["files"], mode, _build_rule())

    def _transform(target_kb: int):
        """照片页只做压缩（水印已独立到「水印」页）。target_kb<=0 不做变换。"""
        if target_kb <= 0:
            return None

        def _fn(src: Path, dst_name: str):
            if Path(src).suffix.lower() not in scanner.IMAGE_EXTS:
                return None
            data = Path(src).read_bytes()
            return compressor.compress_to_target(data, target_kb,
                                                 keep_exif=st["keep_exif"].get())
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

    _est_cache = {}

    def _estimate(plan, target_kb: int) -> int:
        if target_kb <= 0:
            return scanner.file_size(plan.src)
        if Path(plan.src).suffix.lower() not in scanner.IMAGE_EXTS:
            return scanner.file_size(plan.src)
        try:
            ckey = (str(plan.src.resolve()), scanner.file_size(plan.src),
                    target_kb, st["keep_exif"].get())
        except OSError:
            ckey = None
        if ckey is not None and ckey in _est_cache:
            return _est_cache[ckey]
        val = compressor.estimate_size(plan.src, target_kb,
                                       keep_exif=st["keep_exif"].get())
        if ckey is not None:
            _est_cache[ckey] = val
        return val

    def _open_preview(on_confirm=None) -> None:
        if not _validate():
            return
        target_kb = _target_kb()
        plans = _make_plans()
        win = tk.Toplevel(app.root)
        win.title("改名结果预览")
        win.configure(bg=T.C_BG)
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w, h = 1100, 700
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        win.minsize(800, 500)
        win.geometry(f'{w}x{h}+{x}+{y}')
        vlabel(win, text=f"共 {len(plans)} 个文件 → {st['out_dir'].get()}"
                           f"（压缩目标：{target_kb or '不压缩'}"
                           f"{' KB' if target_kb else ''}）",
                 font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                 bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                          padx=T.S_LG, pady=(T.S_MD, T.S_SM))
        # 预估进度提示（后台异步计算，不冻结界面）
        calc_status = vlabel(win, text="", font=(T.FONT_FAMILY, T.F_SM),
                             bg=T.C_BG, fg=T.C_TEXT_M, anchor="w")
        calc_status.pack(fill=tk.X, padx=T.S_LG, pady=(0, T.S_XS))
        tv, _tbox = dialog_tree(win, PREVIEW_COLS, T.C_BG)
        tv.tag_configure("ok", foreground=STATUS_COLOR["ok"])
        tv.tag_configure("warn", foreground=STATUS_COLOR["warn"])
        tv.tag_configure("error", foreground=STATUS_COLOR["error"])

        # 先一次性插入所有行（预计列占位"计算中"），拿到 iid 供后台回填
        row_ids = []
        for plan in plans:
            mark = {"ok": "✓ 正常", "warn": "⚠ 注意", "error": "✗ 禁止"}[plan.status]
            iid = tv.insert("", "end",
                            values=(plan.src.name, plan.dst_name,
                                    scanner.fmt_size(scanner.file_size(plan.src)),
                                    "计算中…", mark),
                            tags=(plan.status,))
            row_ids.append(iid)

        blocked = [p for p in plans if p.blocked]
        if blocked:
            vlabel(win, text=f"⚠ {len(blocked)} 条存在冲突，执行时会被跳过（红色行）。",
                     font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_DANGER,
                     anchor="w").pack(fill=tk.X, padx=T.S_LG, pady=(0, T.S_SM))

        stop_est = threading.Event()

        def _close():
            stop_est.set()
            win.destroy()

        def _confirm():
            stop_est.set()
            win.destroy()
            on_confirm(plans, target_kb)

        dialog_buttons(win, T.C_BG, _close,
                       on_confirm=_confirm if on_confirm is not None else None)
        win.protocol("WM_DELETE_WINDOW", _close)

        def _update_row(iid, est_bytes, done_i, total):
            try:
                cur = tv.item(iid, "values")
                tv.item(iid, values=(cur[0], cur[1], cur[2],
                                     scanner.fmt_size(est_bytes), cur[4]))
                calc_status.config(
                    text=f"正在计算压缩后大小… {done_i + 1}/{total}")
            except tk.TclError:
                pass

        def _done_status():
            try:
                calc_status.config(text="✓ 压缩后大小已全部计算完成")
            except tk.TclError:
                pass

        def _est_worker():
            total = len(plans)
            for i, (plan, iid) in enumerate(zip(plans, row_ids)):
                if stop_est.is_set():
                    return
                est_bytes = _estimate(plan, target_kb)
                app.safe_after(0, lambda iid=iid, e=est_bytes, i=i:
                               _update_row(iid, e, i, total))
            if not stop_est.is_set():
                app.safe_after(0, _done_status)

        if target_kb <= 0:
            # 不压缩：预计大小 = 原大小，无需后台计算
            for iid, plan in zip(row_ids, plans):
                _update_row(iid, scanner.file_size(plan.src), row_ids.index(iid),
                            len(plans))
            _done_status()
        else:
            threading.Thread(target=_est_worker, daemon=True).start()

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
            advanced.save_prefs(app, "photo", st["adv"])
            if result["done"]:
                history.record_batch("photo", out_dir, plans, result)
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
    secondary_button(left, "👁 预览",
                     command=lambda: _open_preview()).pack(side=tk.LEFT)
    secondary_button(left, "↩ 撤销", command=app.undo_last_batch
                     ).pack(side=tk.LEFT, padx=(T.S_SM, 0))
    bar_state = vlabel(left, text="", font=(T.FONT_FAMILY, T.F_SM),
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
    page.st = st                             # 页面状态（供测试 / 调试直接读写）
    page.adv = st["adv"]                     # 高级选项（供测试 / 调试读取）
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
    _refresh_tree()
    app.set_status("就绪")
