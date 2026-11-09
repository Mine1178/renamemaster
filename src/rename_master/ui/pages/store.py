"""门店管理页：SQLite 门店档案 + Excel 批量导入 / 导出（参照 addressmap-tool 实现逻辑）。

页面结构：顶部工具栏（新增 / 导入 / 导出 / 删除 / 搜索）→ 下方门店档案表格
（Treeview，列宽自适应、右键复制、双击编辑）。所有写盘动作都走 core.store_db，
UI 层只负责呈现与交互。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from rename_master.core import store_db
from rename_master.ui import theme as T
from rename_master.ui.widgets import (Card, PageHeader, primary_button,
                                      secondary_button, danger_button, vlabel,
                                      styled_tree)

COLUMNS = [
    ("code", "门店编号", 110, "w"),
    ("name", "门店名称", 160, "w"),
    ("city", "所在城市", 100, "w"),
    ("address", "详细地址", 220, "w"),
    ("manager", "负责人", 100, "w"),
    ("phone", "联系电话", 140, "w"),
    ("remark", "备注", 170, "w"),
    ("updated_at", "更新时间", 150, "w"),
]

FIELD_LABELS = [
    ("code", "门店编号"),
    ("name", "门店名称 *"),
    ("city", "所在城市"),
    ("address", "详细地址"),
    ("manager", "负责人"),
    ("phone", "联系电话"),
    ("remark", "备注"),
]


def _reload(tv: ttk.Treeview, tv_ids: list, search: str) -> None:
    """清空并重新填充表格，同时维护「行序号 → 门店 id」映射。"""
    for iid in tv.get_children():
        tv.delete(iid)
    tv_ids.clear()
    for rec in store_db.list_stores(search):
        tv_ids.append(rec["id"])
        tv.insert("", "end", values=(
            rec["code"], rec["name"], rec["city"], rec["address"],
            rec["manager"], rec["phone"], rec["remark"], rec["updated_at"],
        ))
    try:
        from rename_master.ui.widgets import refit_tree
        refit_tree(tv)
    except Exception:
        pass


def _edit_dialog(parent: tk.Misc, app, rec: dict | None) -> None:
    """新增 / 编辑门店的弹窗。rec 为 None 表示新增。"""
    is_edit = rec is not None
    dlg = tk.Toplevel(parent)
    dlg.title("编辑门店" if is_edit else "新增门店")
    dlg.transient(parent)
    dlg.grab_set()
    dlg.configure(bg=T.C_BG)
    dlg.resizable(False, False)

    from rename_master.ui.widgets import fit_dialog
    fit_dialog(dlg, width=420, height=420, min_w=360, min_h=380)

    vlabel(dlg, "门店档案", font=(T.FONT_FAMILY, T.F_TITLE, "bold"),
           bg=T.C_BG, fg=T.C_TEXT).pack(pady=(T.S_MD, 0))
    vlabel(dlg, "带 * 为必填项（门店名称）", font=(T.FONT_FAMILY, T.F_SM),
           bg=T.C_BG, fg=T.C_TEXT_L).pack(pady=(0, T.S_MD))

    form = tk.Frame(dlg, bg=T.C_BG)
    form.pack(fill=tk.X, padx=T.S_LG)
    entries: dict[str, tk.Entry] = {}
    for field, label in FIELD_LABELS:
        row = tk.Frame(form, bg=T.C_BG)
        row.pack(fill=tk.X, pady=(0, T.S_SM))
        vlabel(row, label, font=(T.FONT_FAMILY, T.F_BODY),
               bg=T.C_BG, fg=T.C_TEXT, anchor="w").pack(side=tk.LEFT,
                                                        padx=(0, T.S_SM),
                                                        pady=T.S_XS)
        ent = tk.Entry(row, font=(T.FONT_FAMILY, T.F_BODY),
                       relief="flat", highlightbackground=T.C_BORDER,
                       highlightthickness=1, bd=0)
        ent.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        if is_edit and rec:
            ent.insert(0, rec.get(field, ""))
        entries[field] = ent

    def _save() -> None:
        data = {f: entries[f].get().strip() for f, _ in FIELD_LABELS}
        if not data["name"]:
            messagebox.showwarning("必填项", "门店名称不能为空。", parent=dlg)
            return
        if is_edit and rec:
            store_db.update_store(rec["id"], data)
            app.set_status(f"已更新门店：{data['name']}", "ok")
        else:
            store_db.add_store(data)
            app.set_status(f"已新增门店：{data['name']}", "ok")
        dlg.destroy()
        # 刷新表格（当前页或切回本页都会 reload）
        if hasattr(parent, "refresh"):
            try:
                parent.refresh()
            except tk.TclError:
                pass

    btn_row = tk.Frame(dlg, bg=T.C_BG)
    btn_row.pack(pady=(T.S_MD, T.S_MD))
    primary_button(btn_row, "保存", command=_save).pack(side=tk.LEFT, padx=T.S_SM)
    secondary_button(btn_row, "取消", command=dlg.destroy).pack(side=tk.LEFT,
                                                               padx=T.S_SM)
    entries["name"].focus_set()


def _selected_ids(tv: ttk.Treeview, tv_ids: list) -> list[int]:
    sel = tv.selection()
    ids = []
    for iid in sel:
        idx = tv.index(iid)
        if 0 <= idx < len(tv_ids):
            ids.append(tv_ids[idx])
    return ids


def _delete_selected(app, page: tk.Widget, tv: ttk.Treeview, tv_ids: list) -> None:
    ids = _selected_ids(tv, tv_ids)
    if not ids:
        messagebox.showinfo("删除", "请先在表格中选中要删除的门店。")
        return
    if not messagebox.askyesno("确认删除",
                               f"确定删除选中的 {len(ids)} 个门店吗？\n"
                               "（此操作不可撤销）", icon="warning"):
        return
    n = store_db.delete_stores(ids)
    app.set_status(f"已删除 {n} 个门店", "ok")
    if hasattr(page, "refresh"):  # 重载表格
        try:
            page.refresh()
        except tk.TclError:
            pass


def _on_double(app, page: tk.Widget, tv: ttk.Treeview, tv_ids: list) -> None:
    sel = tv.selection()
    if not sel:
        return
    idx = tv.index(sel[0])
    if not (0 <= idx < len(tv_ids)):
        return
    rec = store_db.get_store(tv_ids[idx])
    if rec:
        _edit_dialog(page, app, rec)


def _import(app, page: tk.Widget, tv: ttk.Treeview, tv_ids: list) -> None:
    path = filedialog.askopenfilename(
        title="选择门店 Excel 文件",
        filetypes=[("Excel 文件", "*.xlsx *.xlsm"), ("所有文件", "*.*")])
    if not path:
        return
    try:
        stats = store_db.import_excel(path)
    except Exception as e:
        messagebox.showerror("导入失败", f"无法读取该 Excel：\n{e}")
        return
    msg = (f"导入完成：\n新增 {stats['added']} 条\n"
           f"更新 {stats['updated']} 条\n"
           f"跳过（缺名称）{stats['skipped']} 条\n"
           f"错误 {stats['errors']} 条")
    messagebox.showinfo("导入结果", msg)
    app.set_status(f"导入：+{stats['added']} / ~{stats['updated']}", "ok")
    if hasattr(page, "refresh"):
        try:
            page.refresh()
        except tk.TclError:
            pass


def _export(app, tv: ttk.Treeview) -> None:
    path = filedialog.asksaveasfilename(
        title="导出门店档案",
        defaultextension=".xlsx",
        filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")])
    if not path:
        return
    try:
        n = store_db.export_excel(path)
    except Exception as e:
        messagebox.showerror("导出失败", f"无法写入文件：\n{e}")
        return
    messagebox.showinfo("导出完成", f"已导出 {n} 条门店到：\n{path}")
    app.set_status(f"已导出 {n} 条门店", "ok")


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "门店管理", "维护门店档案 · 支持 Excel 批量导入 / 导出")

    # ---------- 工具栏 ----------
    bar = tk.Frame(page, bg=T.C_BG)
    bar.pack(fill=tk.X, pady=(0, T.S_SM))
    tv_ids: list[int] = []

    primary_button(bar, "＋ 新增门店",
                   command=lambda: _edit_dialog(page, app, None)
                   ).pack(side=tk.LEFT, padx=(0, T.S_SM))
    secondary_button(bar, "📥 导入 Excel",
                     command=lambda: _import(app, page, tv, tv_ids)
                     ).pack(side=tk.LEFT, padx=T.S_SM)
    secondary_button(bar, "📤 导出 Excel",
                     command=lambda: _export(app, tv)
                     ).pack(side=tk.LEFT, padx=T.S_SM)
    danger_button(bar, "🗑 删除选中",
                  command=lambda: _delete_selected(app, page, tv, tv_ids)
                  ).pack(side=tk.LEFT, padx=T.S_SM)

    search_var = tk.StringVar()
    search_entry = ttk.Entry(bar, textvariable=search_var,
                             style="RenameMaster.TEntry", width=22)
    search_entry.pack(side=tk.RIGHT, padx=(T.S_SM, 0))
    vlabel(bar, "搜索：", font=(T.FONT_FAMILY, T.F_BODY),
           bg=T.C_BG, fg=T.C_TEXT_M, anchor="w").pack(side=tk.RIGHT,
                                                      padx=(T.S_SM, 0))
    search_var.trace_add("write", lambda *_a: _reload(tv, tv_ids,
                                                      search_var.get()))

    # ---------- 表格 ----------
    card = Card(page, "门店档案", accent=T.C_SUCCESS,
                desc="双击行可编辑；右键可复制单元格 / 行 / 全部，或删除选中。")
    card.pack(fill=tk.BOTH, expand=True, pady=(0, T.S_MD))
    tv = styled_tree(card.body, COLUMNS, height=18, flex="address",
                     on_delete=lambda idxs: store_db.delete_stores(
                         [tv_ids[i] for i in idxs if 0 <= i < len(tv_ids)]
                     ) or _reload(tv, tv_ids, search_var.get()))
    tv.pack(fill=tk.BOTH, expand=True)
    tv.bind("<Double-1>", lambda e: _on_double(app, page, tv, tv_ids))

    def refresh() -> None:
        _reload(tv, tv_ids, search_var.get())

    page.refresh = refresh
    refresh()
