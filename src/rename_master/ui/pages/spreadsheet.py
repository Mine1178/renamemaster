"""表格批量命名页：选文件 → 命名规则 → 输出 → 预览 / 执行（任务书 §4.6.3）。

体验与照片页对齐：执行前弹预览窗，确认后才落盘；执行期间底部进度条走量。
"""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rename_master.core import mapper, renamer, scanner
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, hint_label,
                                      primary_button, secondary_button,
                                      styled_tree)

FILETYPES = [("表格文件", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
MAP_FILETYPES = [("对照表", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
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
        "src_dir": tk.StringVar(value=""),   # 源目录（浏览 / 拖入共用）
        "mode": tk.StringVar(value="prefix"),
        "mapping": {},
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
    # 源目录输入框：既可用「选择文件夹」浏览，也可拖入文件夹自动填
    src_row = tk.Frame(card1.body, bg=T.C_CARD)
    src_row.pack(fill=tk.X, pady=(0, T.S_SM))
    tk.Label(src_row, text="源目录", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
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
        _refresh_tree()
        if added:
            app.set_status(f"已添加 {added} 个文件", "ok")

    def _add_files() -> None:
        picked = filedialog.askopenfilenames(title="选择表格文件", filetypes=FILETYPES)
        _extend(scanner.scan_files(picked, scanner.SPREADSHEET_EXTS))

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
        _extend(scanner.scan_files([raw], scanner.SPREADSHEET_EXTS))
        if not st["files"]:
            app.set_status(f"源目录下没有可用的表格文件：{raw}", "warn")

    def _clear() -> None:
        st["files"].clear()
        st["src_dir"].set("")
        _refresh_tree()
        app.set_status("已清空文件列表")

    # ---------- ② 命名规则 ----------
    card2 = Card(page, "② 命名规则", "统一前缀 + 序号，或按 Excel 对照表一一改名",
                 accent=T.C_ACCENT)
    card2.pack(fill=tk.X, pady=(0, T.S_MD))

    mode_row = tk.Frame(card2.body, bg=T.C_CARD)
    mode_row.pack(fill=tk.X)
    tk.Radiobutton(mode_row, text="模式一：统一前缀+序号", variable=st["mode"],
                   value="prefix", command=lambda: _sync_mode(),
                   bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                   activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                   highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                   anchor="w", cursor="hand2").pack(side=tk.LEFT)
    tk.Radiobutton(mode_row, text="模式二：一一对照（Excel）", variable=st["mode"],
                   value="map", command=lambda: _sync_mode(),
                   bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                   activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                   highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                   anchor="w", cursor="hand2").pack(side=tk.LEFT, padx=T.S_MD)

    # 模式一控件（与照片页对齐：基础名称独占一行，其余横向排）
    prefix_box = tk.Frame(card2.body, bg=T.C_CARD)
    prow = tk.Frame(prefix_box, bg=T.C_CARD)
    prow.pack(fill=tk.X, pady=(T.S_SM, 0))
    tk.Label(prow, text="基础名称", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(prow, textvariable=st["base"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER,
             highlightthickness=1).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                        padx=(T.S_SM, 0))

    prow2 = tk.Frame(prefix_box, bg=T.C_CARD)
    prow2.pack(fill=tk.X, pady=(T.S_SM, 0))
    tk.Label(prow2, text="位数", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    digits_menu = tk.OptionMenu(prow2, st["digits"], "3", "4", "5")
    digits_menu.config(width=2)
    digits_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    tk.Label(prow2, text="起始", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Spinbox(prow2, from_=0, to=99999, textvariable=st["start"],
               width=4).pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    tk.Label(prow2, text="分隔符", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
             fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    sep_menu = tk.OptionMenu(prow2, st["sep"], "_", "-", " ", "")
    sep_menu.config(width=2)
    sep_menu.pack(side=tk.LEFT, padx=(T.S_XS, T.S_XS))
    _check(prow2, "保留扩展名", st["keep_ext"]).pack(side=tk.LEFT)
    hint_label(prefix_box, "示例：台账_001.xlsx").pack(fill=tk.X, pady=(T.S_XS, 0))

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
               "第 1 列原文件名、第 2 列新文件名；未匹配的文件保持原名。"
               ).config(wraplength=500).pack(fill=tk.X)

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
        return renamer.plan_rename(st["files"], mode, _rule())

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
    _refresh_tree()
    app.set_status("就绪")
