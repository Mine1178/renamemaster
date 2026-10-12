"""表格批量命名页：选文件 → 命名规则 → 输出 → 预览 / 执行（任务书 §4.6.3）。

体验与照片页对齐：执行前弹预览窗，确认后才落盘；执行期间底部进度条走量。
"""
from __future__ import annotations

import threading
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
PREVIEW_COLS = [("old", "原文件名", 260, "w"), ("new", "新文件名", 260, "w"),
                ("size", "大小", 90, tk.CENTER), ("status", "状态", 80, tk.CENTER)]
STATUS_COLOR = {"ok": T.C_SUCCESS, "warn": T.C_WARNING, "error": T.C_DANGER}


def _check(master, text: str, variable: tk.Variable, command=None) -> tk.Checkbutton:
    return tk.Checkbutton(master, text=text, variable=variable, command=command,
                          bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                          activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                          highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                          anchor="w", cursor="hand2")


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "表格批量命名",
               "Excel / CSV 按统一前缀 + 序号改名，输出到独立目录，原文件零改动")

    st = {
        "files": [],
        "base": tk.StringVar(value=app.cfg.get("sheet.base_name", "台账")),
        "digits": tk.StringVar(value=str(app.cfg.get("sheet.digits", 3))),
        "start": tk.StringVar(value=str(app.cfg.get("sheet.start", 1))),
        "sep": tk.StringVar(value=app.cfg.get("sheet.sep", "_")),
        "keep_ext": tk.BooleanVar(value=bool(app.cfg.get("sheet.keep_ext", True))),
        "out_dir": tk.StringVar(value=""),
        "cancel": None,
    }

    # ---------- ① 选择文件 ----------
    card1 = Card(page, "① 选择文件", "添加要改名的表格文件（.xlsx / .xls / .csv）",
                 accent=T.C_ACCENT)
    card1.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))
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
        added = 0
        for p in new_files:
            key = str(p.resolve()).lower()
            if key not in known:
                known.add(key)
                st["files"].append(p)
                added += 1
        _refresh_tree()
        if added:
            app.set_status(f"已添加 {added} 个文件", "ok")

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
        app.set_status("已清空文件列表")

    # ---------- ② 命名规则 ----------
    card2 = Card(page, "② 命名规则", "统一前缀 + 序号，可设位数 / 起始号 / 分隔符",
                 accent=T.C_ACCENT)
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
    _check(row2, "保留扩展名", st["keep_ext"]).pack(side=tk.LEFT)

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

    # ---------- 规则 / 预览 / 执行 ----------
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

    def _make_plans():
        return renamer.plan_rename(st["files"], renamer.MODE_PREFIX, _rule())

    def _validate() -> bool:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个文件。")
            return False
        if not st["out_dir"].get().strip():
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return False
        return True

    def _open_preview(on_confirm=None) -> None:
        if not _validate():
            return
        plans = _make_plans()
        win = tk.Toplevel(app.root)
        win.title("改名结果预览")
        win.geometry("760x440")
        win.configure(bg=T.C_BG)
        tk.Label(win, text=f"共 {len(plans)} 个文件 → {st['out_dir'].get()}",
                 font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                 bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                          padx=T.S_LG,
                                                          pady=(T.S_MD, T.S_SM))
        tv = styled_tree(win, PREVIEW_COLS, height=14)
        pvsb = ttk.Scrollbar(win, orient="vertical",
                             style="RenameMaster.Vertical.TScrollbar", command=tv.yview)
        tv.configure(yscrollcommand=pvsb.set)
        pvsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, T.S_LG))
        tv.pack(fill=tk.BOTH, expand=True, padx=(T.S_LG, 0), pady=(0, T.S_SM))
        tv.tag_configure("ok", foreground=STATUS_COLOR["ok"])
        tv.tag_configure("warn", foreground=STATUS_COLOR["warn"])
        tv.tag_configure("error", foreground=STATUS_COLOR["error"])
        for plan in plans:
            mark = {"ok": "✓ 正常", "warn": "⚠ 注意", "error": "✗ 禁止"}[plan.status]
            tv.insert("", "end",
                      values=(plan.src.name, plan.dst_name,
                              scanner.fmt_size(scanner.file_size(plan.src)), mark),
                      tags=(plan.status,))
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
                           command=lambda: (win.destroy(), on_confirm(plans))
                           ).pack(side=tk.RIGHT, padx=(0, T.S_SM))

    def _run(plans) -> None:
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
                plans, out_dir, move=False,
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

    # ---------- 底部操作栏 ----------
    bar = tk.Frame(app.content, bg=T.C_BG)
    left = tk.Frame(bar, bg=T.C_BG)
    left.pack(side=tk.LEFT)
    secondary_button(left, "👁 预览", command=lambda: _open_preview()).pack(side=tk.LEFT)
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
