"""文档批量命名页：选文件 → 命名规则（可叠加正文开头）→ 输出 → 预览 / 执行。

体验与照片页对齐：执行前弹预览窗（含正文预览列），确认后才落盘。
"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rename_master.core import (doc_extract, history, mapper, naming_vars,
                                renamer, scanner)
from rename_master.ui import advanced, theme as T
from rename_master.ui.widgets import (Card, PageHeader, dialog_buttons,
                                      dialog_tree, fit_dialog, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree, vlabel, enable_label_copy)

FILETYPES = [("文档文件", "*.docx *.pdf *.txt *.md"), ("所有文件", "*.*")]
MAP_FILETYPES = [("对照表", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
FILE_COLS = [("name", "文件名", 360, "w"), ("size", "大小", 90, tk.CENTER)]
PREVIEW_COLS = [("old", "原文件名", 230, "w"), ("new", "新文件名", 230, "w"),
                ("body", "正文预览", 220, "w"), ("status", "状态", 80, tk.CENTER)]
STATUS_COLOR = {"ok": T.C_SUCCESS, "warn": T.C_WARNING, "error": T.C_DANGER}
BODY_CHARS = 30


def _radio(master, text: str, variable: tk.Variable, value: str, command=None) -> tk.Radiobutton:
    """卡片内统一风格的单选钮（白底，避免 ttk 主题在 Win 上的灰块）。"""
    w = tk.Radiobutton(master, text=text, variable=variable, value=value,
                          command=command, bg=T.C_CARD, fg=T.C_TEXT,
                          activebackground=T.C_CARD, activeforeground=T.C_ACCENT,
                          selectcolor=T.C_CARD, highlightthickness=0,
                          font=(T.FONT_FAMILY, T.F_BODY), anchor="w", cursor="hand2")
    enable_label_copy(w)
    return w


def _check(master, text: str, variable: tk.Variable, command=None) -> tk.Checkbutton:
    w = tk.Checkbutton(master, text=text, variable=variable, command=command,
                          bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                          activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                          highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                          anchor="w", cursor="hand2")
    enable_label_copy(w)
    return w


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "文档批量命名",
               "Word / PDF / TXT 可按正文开头自动取名，再叠加前缀与序号")

    st = {
        "files": [],
        "src_dir": tk.StringVar(value=""),   # 源目录（浏览 / 拖入共用）
        "mode": tk.StringVar(value="prefix"),
        "mapping": {},
        "base": tk.StringVar(value=app.cfg.get("doc.base_name", "文档")),
        "digits": tk.StringVar(value=str(app.cfg.get("doc.digits", 3))),
        "start": tk.StringVar(value=str(app.cfg.get("doc.start", 1))),
        "sep": tk.StringVar(value=app.cfg.get("doc.sep", "_")),
        "keep_ext": tk.BooleanVar(value=bool(app.cfg.get("doc.keep_ext", True))),
        "use_content": tk.BooleanVar(value=bool(app.cfg.get("doc.use_content", True))),
        "titles": {},          # {文件绝对路径: 正文前 30 字}
        "out_dir": tk.StringVar(value=""),
        "cancel": None,
        "adv": advanced.create_vars(app, "doc"),
    }

    # ---------- ① 选择文件 ----------
    card1 = Card(page, "① 选择文件",
                 "添加要改名的文档（.docx / .pdf / .txt / .md）", accent=T.C_ACCENT)
    card1.pack(fill=tk.X, pady=(T.S_XS, T.S_MD))
    # 源目录输入框：既可用「选择文件夹」浏览，也可拖入文件夹自动填
    src_row = tk.Frame(card1.body, bg=T.C_CARD)
    src_row.pack(fill=tk.X, pady=(0, T.S_SM))
    vlabel(src_row, text="源目录", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(src_row, textvariable=st["src_dir"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=T.S_SM)
    secondary_button(src_row, "📂 选择文件夹",
                     command=lambda: _add_dir()).pack(side=tk.LEFT)

    bar = tk.Frame(card1.body, bg=T.C_CARD)
    bar.pack(fill=tk.X, pady=(0, T.S_SM))
    secondary_button(bar, "➕ 添加文件", command=lambda: _add_files()).pack(side=tk.LEFT)
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
        _extend(scanner.scan_files([raw], scanner.DOCUMENT_EXTS))
        if not st["files"]:
            app.set_status(f"源目录下没有可用的文档文件：{raw}", "warn")

    def _clear() -> None:
        st["files"].clear()
        st["titles"].clear()
        st["src_dir"].set("")
        _refresh_tree()
        app.set_status("已清空文件列表")

    # ---------- ② 命名规则 ----------
    card2 = Card(page, "② 命名规则", "统一前缀+序号（可叠加正文开头），或按 Excel 对照表一一改名",
                 accent=T.C_ACCENT)
    card2.pack(fill=tk.X, pady=(0, T.S_MD))

    mode_row = tk.Frame(card2.body, bg=T.C_CARD)
    mode_row.pack(fill=tk.X)
    _radio(mode_row, "模式一：统一前缀+序号", st["mode"], "prefix",
           command=lambda: _sync_mode()).pack(side=tk.LEFT)
    _radio(mode_row, "模式二：一一对照（Excel）", st["mode"], "map",
           command=lambda: _sync_mode()).pack(side=tk.LEFT, padx=T.S_MD)

    # 模式一控件（与照片页对齐：基础名称独占一行，其余横向排）
    prefix_box = tk.Frame(card2.body, bg=T.C_CARD)
    _check(prefix_box, f"☑ 用正文前 {BODY_CHARS} 字作为文件名（叠加前缀）",
           st["use_content"]).pack(fill=tk.X, pady=(T.S_SM, 0))

    prow = tk.Frame(prefix_box, bg=T.C_CARD)
    prow.pack(fill=tk.X, pady=(T.S_SM, 0))
    vlabel(prow, text="基础名称", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(prow, textvariable=st["base"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    prow2 = tk.Frame(prefix_box, bg=T.C_CARD)
    prow2.pack(fill=tk.X, pady=(T.S_SM, 0))
    vlabel(prow2, text="位数", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    digits_menu = tk.OptionMenu(prow2, st["digits"], "3", "4", "5")
    digits_menu.config(width=2)
    digits_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    vlabel(prow2, text="起始", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Spinbox(prow2, from_=0, to=99999, textvariable=st["start"],
               width=4).pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    vlabel(prow2, text="分隔符", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    sep_menu = tk.OptionMenu(prow2, st["sep"], "_", "-", " ", "")
    sep_menu.config(width=2)
    sep_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    _check(prow2, "保留扩展名", st["keep_ext"]).pack(side=tk.LEFT)
    _hl = hint_label(prefix_box, "勾选正文提取时：前缀 + 正文开头 + 序号；"
                                 "提取失败的文件自动退化为前缀 + 序号。示例：文档_001.docx")
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
        except Exception as exc:                       # noqa: BLE001
            messagebox.showerror("导入失败", f"对照表解析失败：{exc}")
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
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先在上方选择文件夹或添加文件。")
            return
        st["mapping"].clear()
        map_tree.delete(*map_tree.get_children())
        for p in st["files"]:
            st["mapping"][p.name] = ""
            map_tree.insert("", "end", values=(p.name, ""))
        map_label.config(text=f"已提取 {len(st['files'])} 个文件名（新文件名待填写）")
        app.set_status(f"已提取 {len(st['files'])} 个文件名到对照表", "ok")

    def _export_map() -> None:
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

    advanced.build_card(page, app, st["adv"])

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
        rule = {"base_name": st["base"].get().strip(), "digits": digits,
                "start": start, "sep": st["sep"].get(),
                "keep_ext": st["keep_ext"].get()}
        return advanced.apply_to_rule(rule, st["adv"])

    def _make_plans():
        """模式二走对照表；模式一按是否勾选正文提取走对照或纯前缀。"""
        if st["mode"].get() == "map":
            rule = {"mapping": dict(st["mapping"]),
                    "keep_ext": st["keep_ext"].get()}
            return renamer.plan_rename(
                st["files"], renamer.MODE_MAP,
                advanced.apply_to_rule(rule, st["adv"]))
        start, digits = _nums()
        if not st["use_content"].get():
            return renamer.plan_rename(st["files"], renamer.MODE_PREFIX, _rule())
        # 正文组装：先按排序设置决定序号顺序（与引擎排序保持一致）
        sr: dict = {}
        advanced.apply_to_rule(sr, st["adv"])
        ordered = renamer._sort_paths(st["files"], sr.get("sort_by", ""),
                                      bool(sr.get("sort_desc", False)))
        sep = st["sep"].get()
        mapping = {}
        for i, p in enumerate(ordered):
            body = st["titles"].get(str(p), "")
            number = f"{start + i:0{digits}d}"
            pref = naming_vars.render_template(p, st["base"].get().strip())
            mapping[p.name] = sep.join(x for x in (pref, body, number) if x)
        rule = {"mapping": mapping, "keep_ext": st["keep_ext"].get()}
        return renamer.plan_rename(st["files"], renamer.MODE_MAP,
                                   advanced.apply_to_rule(rule, st["adv"]))

    def _validate() -> bool:
        if not st["files"]:
            messagebox.showwarning("缺少文件", "请先添加至少一个文件。")
            return False
        if not st["out_dir"].get().strip():
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return False
        if st["mode"].get() == "map" and not st["mapping"]:
            messagebox.showwarning("缺少对照表", "模式二需要先导入 Excel 对照表或一键提取文件名。")
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
        if st["mode"].get() == "prefix" and st["use_content"].get():
            _extract_then(lambda: (_reset_bar(), _show_preview(on_confirm)))
        else:
            _show_preview(on_confirm)

    def _show_preview(on_confirm=None) -> None:
        plans = _make_plans()
        win = tk.Toplevel(app.root)
        win.title("改名结果预览")
        win.configure(bg=T.C_BG)
        fit_dialog(win, 1000, 600)
        head = "共 %d 个文件 → %s" % (len(plans), st["out_dir"].get())
        if st["use_content"].get():
            head += f"（正文前 {BODY_CHARS} 字）"
        vlabel(win, text=head, font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                 bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(fill=tk.X,
                                                          padx=T.S_LG,
                                                          pady=(T.S_MD, T.S_SM))
        tv, _tbox = dialog_tree(win, PREVIEW_COLS, T.C_BG)
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
            vlabel(win, text=f"⚠ {len(blocked)} 条存在冲突，执行时会被跳过（红色行）。",
                     font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_DANGER,
                     anchor="w").pack(fill=tk.X, padx=T.S_LG, pady=(0, T.S_SM))

        def _confirm():
            win.destroy()
            on_confirm(plans)

        dialog_buttons(win, T.C_BG, win.destroy,
                       on_confirm=_confirm if on_confirm is not None else None)

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
            advanced.save_prefs(app, "doc", st["adv"])
            if result["done"]:
                history.record_batch("document", out_dir, plans, result)
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

    key = next((k for k, v in app.pages.items() if v is page), "document")
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
