"""表格批量命名页（v1.0 最简版）：前缀 + 序号，不压缩（任务书 §4.6.3）。"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rename_master.core import renamer, scanner
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree)

FILETYPES = [("表格文件", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
FILE_COLS = [("name", "文件名", 360, "w"), ("size", "大小", 90, tk.CENTER)]


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "表格批量命名", "Excel / CSV 批量改名（复用模式一/二规则）")

    hint = Card(page, "使用说明", accent=T.C_INFO)
    hint.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))
    hint_label(hint.body, "本页筛选 .xlsx / .xls / .csv 文件，命名规则与照片页一致。"
                          "v1.0 仅支持统一前缀+序号。").pack(fill=tk.X)

    st = {
        "files": [],
        "base": tk.StringVar(value="台账"),
        "digits": tk.StringVar(value="3"),
        "start": tk.StringVar(value="1"),
        "sep": tk.StringVar(value="_"),
        "keep_ext": tk.BooleanVar(value=True),
        "out_dir": tk.StringVar(value=""),
        "cancel": None,
    }

    # ---------- ① 选择文件 ----------
    card1 = Card(page, "① 选择文件", "添加要改名的表格文件", accent=T.C_ACCENT)
    card1.pack(fill=tk.X, pady=(0, T.S_MD))
    bar = tk.Frame(card1.body, bg=T.C_CARD)
    bar.pack(fill=tk.X, pady=(0, T.S_SM))
    secondary_button(bar, "➕ 添加文件", command=lambda: _add_files()).pack(side=tk.LEFT)
    secondary_button(bar, "📂 添加文件夹", command=lambda: _add_dir()).pack(side=tk.LEFT,
                                                                       padx=T.S_SM)
    secondary_button(bar, "🗑 清空", command=lambda: _clear()).pack(side=tk.LEFT)

    tree = styled_tree(card1.body, FILE_COLS, height=8)
    vsb = ttk.Scrollbar(card1.body, orient="vertical",
                        style="RenameMaster.Vertical.TScrollbar", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.X)
    count_label = hint_label(card1.body, "已选择 0 个文件")
    count_label.pack(fill=tk.X, pady=(T.S_XS, 0))

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        for p in st["files"]:
            tree.insert("", "end", values=(p.name, scanner.fmt_size(scanner.file_size(p))))
        count_label.config(text=f"已选择 {len(st['files'])} 个文件")
        if st["files"] and not st["out_dir"].get().strip():
            st["out_dir"].set(str(renamer.default_output_dir(st["files"])))

    def _extend(new_files) -> None:
        known = {str(p.resolve()).lower() for p in st["files"]}
        for p in new_files:
            key = str(p.resolve()).lower()
            if key not in known:
                known.add(key)
                st["files"].append(p)
        _refresh_tree()

    def _add_files() -> None:
        picked = filedialog.askopenfilenames(title="选择表格文件", filetypes=FILETYPES)
        _extend(scanner.scan_files(picked, scanner.SPREADSHEET_EXTS))

    def _add_dir() -> None:
        d = filedialog.askdirectory(title="选择文件夹")
        if d:
            _extend(scanner.scan_files([d], scanner.SPREADSHEET_EXTS))

    def _clear() -> None:
        st["files"].clear()
        _refresh_tree()

    # ---------- ② 命名模式一 ----------
    card2 = Card(page, "② 命名规则（统一前缀+序号）", accent=T.C_ACCENT)
    card2.pack(fill=tk.X, pady=(0, T.S_MD))
    row = tk.Frame(card2.body, bg=T.C_CARD)
    row.pack(fill=tk.X)
    tk.Label(row, text="基础名称", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row, textvariable=st["base"], width=22, relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, padx=(T.S_SM, T.S_MD))
    tk.Label(row, text="序号位数", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.OptionMenu(row, st["digits"], "3", "4", "5").pack(side=tk.LEFT, padx=(T.S_SM, T.S_MD))
    tk.Label(row, text="起始序号", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Spinbox(row, from_=0, to=99999, textvariable=st["start"],
               width=6).pack(side=tk.LEFT, padx=(T.S_SM, 0))
    row2 = tk.Frame(card2.body, bg=T.C_CARD)
    row2.pack(fill=tk.X, pady=(T.S_SM, 0))
    tk.Label(row2, text="分隔符", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.OptionMenu(row2, st["sep"], "_", "-", " ", "").pack(side=tk.LEFT, padx=(T.S_SM, T.S_MD))
    tk.Checkbutton(row2, text="保留扩展名", variable=st["keep_ext"], bg=T.C_CARD,
                   fg=T.C_TEXT, activebackground=T.C_CARD, selectcolor=T.C_CARD,
                   font=(T.FONT_FAMILY, T.F_BODY), anchor="w").pack(side=tk.LEFT)

    # ---------- ③ 输出位置 ----------
    card3 = Card(page, "③ 输出位置", "输出到独立目录，源文件零改动", accent=T.C_SUCCESS)
    card3.pack(fill=tk.X, pady=(0, T.S_MD))
    orow = tk.Frame(card3.body, bg=T.C_CARD)
    orow.pack(fill=tk.X)
    tk.Entry(orow, textvariable=st["out_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True)
    def _pick_out() -> None:
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            st["out_dir"].set(d)

    secondary_button(orow, "📁 浏览", command=_pick_out).pack(side=tk.LEFT,
                                                          padx=(T.S_SM, 0))

    # ---------- 执行 ----------
    def _rule() -> dict:
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

    def _run() -> None:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个文件。")
            return
        out_dir = st["out_dir"].get().strip()
        if not out_dir:
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return
        plans = renamer.plan_rename(st["files"], renamer.MODE_PREFIX, _rule())
        if not messagebox.askyesno("确认执行",
                                   f"共 {len(plans)} 个文件，输出到：\n{out_dir}"):
            return
        result = renamer.execute_plan(plans, Path(out_dir), move=False)
        app.cfg.set("output.last_dir", out_dir)
        app.cfg.set("output.last_count", result["done"])
        app.cfg.save()
        app.set_status(f"完成 {result['done']} 个，失败 {result['failed']} 个",
                       "ok" if not result["failed"] else "warn")
        messagebox.showinfo("执行完成",
                            f"完成 {result['done']} 个，失败 {result['failed']} 个\n"
                            f"输出目录：{out_dir}")

    # 操作栏最终被 set_action_bar 重挂到 action_host；master 必须是 content
    bar = tk.Frame(app.content, bg=T.C_BG)
    tk.Label(bar, text="v1.0 不做压缩，仅改名后复制到输出目录。",
             font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG,
             fg=T.C_TEXT_L).pack(side=tk.LEFT)
    primary_button(bar, "▶ 开始执行", command=_run).pack(side=tk.RIGHT)
    key = next((k for k, v in app.pages.items() if v is page), "spreadsheet")
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
    _refresh_tree()
    app.set_status("就绪")
