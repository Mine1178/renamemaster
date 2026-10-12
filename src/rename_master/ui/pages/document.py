"""文档批量命名页：选文件 → 命名规则（可叠加正文开头）→ 输出 → 预览 / 执行。

体验与照片页对齐：执行前弹预览窗（含正文预览列），确认后才落盘。
"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rename_master.core import doc_extract, renamer, scanner
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree)

FILETYPES = [("文档文件", "*.docx *.pdf *.txt *.md"), ("所有文件", "*.*")]
FILE_COLS = [("name", "文件名", 360, "w"), ("size", "大小", 90, tk.CENTER)]
PREVIEW_COLS = [("old", "原文件名", 230, "w"), ("new", "新文件名", 230, "w"),
                ("body", "正文预览", 220, "w"), ("status", "状态", 80, tk.CENTER)]
STATUS_COLOR = {"ok": T.C_SUCCESS, "warn": T.C_WARNING, "error": T.C_DANGER}
BODY_CHARS = 30


def _check(master, text: str, variable: tk.Variable, command=None) -> tk.Checkbutton:
    return tk.Checkbutton(master, text=text, variable=variable, command=command,
                          bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                          activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                          highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                          anchor="w", cursor="hand2")


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "文档批量命名",
               "Word / PDF / TXT 可按正文开头自动取名，再叠加前缀与序号")

    st = {
        "files": [],
        "base": tk.StringVar(value=app.cfg.get("doc.base_name", "文档")),
        "digits": tk.StringVar(value=str(app.cfg.get("doc.digits", 3))),
        "start": tk.StringVar(value=str(app.cfg.get("doc.start", 1))),
        "sep": tk.StringVar(value=app.cfg.get("doc.sep", "_")),
        "keep_ext": tk.BooleanVar(value=bool(app.cfg.get("doc.keep_ext", True))),
        "use_content": tk.BooleanVar(value=bool(app.cfg.get("doc.use_content", True))),
        "titles": {},          # {文件绝对路径: 正文前 30 字}
        "out_dir": tk.StringVar(value=""),
        "cancel": None,
    }

    # ---------- ① 选择文件 ----------
    card1 = Card(page, "① 选择文件",
                 "添加要改名的文档（.docx / .pdf / .txt / .md）", accent=T.C_ACCENT)
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
        st["titles"].clear()          # 文件列表变了，缓存的正文失效
        _refresh_tree()
        if added:
            app.set_status(f"已添加 {added} 个文件", "ok")

    def _add_files() -> None:
        picked = filedialog.askopenfilenames(title="选择文档", filetypes=FILETYPES)
        _extend(scanner.scan_files(picked, scanner.DOCUMENT_EXTS))

    def _add_dir() -> None:
        d = filedialog.askdirectory(title="选择文件夹")
        if d:
            _extend(scanner.scan_files([d], scanner.DOCUMENT_EXTS))

    def _clear() -> None:
        st["files"].clear()
        st["titles"].clear()
        _refresh_tree()
        app.set_status("已清空文件列表")

    # ---------- ② 命名规则 ----------
    card2 = Card(page, "② 命名规则", "前缀 + 正文开头 + 序号，三项可自由叠加",
                 accent=T.C_ACCENT)
    card2.pack(fill=tk.X, pady=(0, T.S_MD))
    _check(card2.body, f"☑ 用正文前 {BODY_CHARS} 字作为文件名（叠加前缀）",
           st["use_content"]).pack(fill=tk.X)

    row = tk.Frame(card2.body, bg=T.C_CARD)
    row.pack(fill=tk.X, pady=(T.S_SM, 0))
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
    hint_label(card2.body, "勾选正文提取时：前缀 + 正文开头 + 序号；"
                           "提取失败的文件自动退化为前缀 + 序号。").pack(fill=tk.X,
                                                              pady=(T.S_XS, 0))

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
    def _nums() -> tuple:
        try:
            start = int(str(st["start"].get()).strip())
        except ValueError:
            start = 1
        try:
            digits = int(str(st["digits"].get()).strip())
        except ValueError:
            digits = 3
        return start, max(1, digits)

    def _rule() -> dict:
        start, digits = _nums()
        return {"base_name": st["base"].get().strip(), "digits": digits,
                "start": start, "sep": st["sep"].get(),
                "keep_ext": st["keep_ext"].get()}

    def _make_plans():
        """勾选正文提取时按「逐文件新名」走对照模式（仍复用 renamer 的校验与去重）。"""
        start, digits = _nums()
        prefix = st["base"].get().strip()
        sep = st["sep"].get()
        if not st["use_content"].get():
            return renamer.plan_rename(st["files"], renamer.MODE_PREFIX, _rule())
        mapping = {}
        for i, p in enumerate(st["files"]):
            body = st["titles"].get(str(p), "")
            number = f"{start + i:0{digits}d}"
            mapping[p.name] = sep.join(x for x in (prefix, body, number) if x)
        return renamer.plan_rename(st["files"], renamer.MODE_MAP,
                                   {"mapping": mapping,
                                    "keep_ext": st["keep_ext"].get()})

    def _validate() -> bool:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个文件。")
            return False
        if not st["out_dir"].get().strip():
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return False
        return True

    def _extract_then(on_done) -> None:
        """后台线程批量提取正文（文件多时不能卡住界面）。"""
        files = list(st["files"])
        cancel_event = threading.Event()
        st["cancel"] = cancel_event
        bar_btn_cancel.config(state=tk.NORMAL)
        bar_btn_run.config(state=tk.DISABLED)
        bar_btn_preview.config(state=tk.DISABLED)
        progress.pack(fill=tk.X, pady=(T.S_SM, 0))
        progress["value"] = 0
        progress["maximum"] = max(1, len(files))
        app.set_status("正在提取正文…")

        def _worker() -> None:
            titles = {}
            for i, p in enumerate(files):
                if cancel_event.is_set():
                    break
                titles[str(p)] = doc_extract.extract_title(p, BODY_CHARS)
                app.safe_after(0, lambda i=i, n=p.name: _tick(i + 1, len(files), n))
            st["titles"] = titles
            if cancel_event.is_set():
                app.safe_after(0, _reset_bar)     # 用户中途取消，不弹预览
            else:
                app.safe_after(0, on_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _tick(done: int, total: int, name: str) -> None:
        progress["value"] = done
        bar_state.config(text=f"{done}/{total} {name}")
        app.set_status(f"提取正文 {done}/{total}")

    def _reset_bar() -> None:
        st["cancel"] = None
        progress.pack_forget()
        bar_btn_cancel.config(state=tk.DISABLED)
        bar_btn_run.config(state=tk.NORMAL)
        bar_btn_preview.config(state=tk.NORMAL)

    def _open_preview(on_confirm=None) -> None:
        if not _validate():
            return
        if st["use_content"].get():
            _extract_then(lambda: (_reset_bar(), _show_preview(on_confirm)))
        else:
            _show_preview(on_confirm)

    def _show_preview(on_confirm=None) -> None:
        plans = _make_plans()
        win = tk.Toplevel(app.root)
        win.title("改名结果预览")
        win.geometry("840x460")
        win.configure(bg=T.C_BG)
        head = "共 %d 个文件 → %s" % (len(plans), st["out_dir"].get())
        if st["use_content"].get():
            head += f"（正文前 {BODY_CHARS} 字）"
        tk.Label(win, text=head, font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
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
            body = st["titles"].get(str(plan.src), "") or "—"
            tv.insert("", "end",
                      values=(plan.src.name, plan.dst_name, body, mark),
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
        bar_btn_preview.config(state=tk.DISABLED)
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
            _reset_bar()
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
    bar_btn_preview = secondary_button(left, "👁 预览",
                                       command=lambda: _open_preview())
    bar_btn_preview.pack(side=tk.LEFT)
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

    key = next((k for k, v in app.pages.items() if v is page), "document")
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
