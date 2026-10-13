"""通用 UI 组件（Card / PageHeader / 按钮工厂）——照搬 Wifibond widgets.py。"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from rename_master.ui import theme as T


# ---------- 文字复制辅助 ----------
def copy_to_clipboard(widget, text: str) -> None:
    """把文字写入系统剪贴板。"""
    widget.clipboard_clear()
    widget.clipboard_append(text)
    widget.update()  # 剪贴板内容在程序退出后仍保留


def enable_label_copy(widget) -> None:
    """给 Label/Button 类控件加右键菜单，可一键复制其文字。"""
    menu = tk.Menu(widget, tearoff=0)

    def _do_copy():
        try:
            copy_to_clipboard(widget, str(widget.cget("text")))
        except tk.TclError:
            pass

    menu.add_command(label="复制文字", command=_do_copy)

    def _popup(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", _popup)


def _tree_selected_text(tv: ttk.Treeview, col_idx=None, all_rows=False) -> str:
    """把 Treeview 选中内容转成制表符/换行分隔的文本。

    col_idx: 指定列号（1 起）→ 只复制该列；None → 复制整行；
    all_rows: True → 复制全部行（含表头）。
    """
    cols = list(tv.cget("columns"))

    if all_rows:
        items = [tv.item(iid) for iid in tv.get_children("")]
        heads = [tv.heading(c)["text"] or "" for c in cols]
        lines = ["\t".join(heads)]
    else:
        sel = tv.selection()
        if not sel:
            return ""
        items = [tv.item(iid) for iid in sel]
        lines = []

    for it in items:
        vals = list(it["values"])
        if col_idx is not None:
            idx = col_idx - 1
            lines.append(str(vals[idx]) if idx < len(vals) else "")
        else:
            lines.append("\t".join(str(v) for v in vals))
    return "\n".join(lines)


def enable_tree_copy(tv: ttk.Treeview) -> None:
    """给 Treeview 加右键菜单 + Ctrl+C：复制单元格/整行/全部。"""
    menu = tk.Menu(tv, tearoff=0)
    state = {"col": None}  # 右键所在列

    def _copy_cell():
        text = _tree_selected_text(tv, col_idx=state["col"])
        if text:
            copy_to_clipboard(tv, text)

    def _copy_row():
        text = _tree_selected_text(tv)
        if text:
            copy_to_clipboard(tv, text)

    def _copy_all():
        copy_to_clipboard(tv, _tree_selected_text(tv, all_rows=True))

    menu.add_command(label="复制此单元格", command=_copy_cell)
    menu.add_command(label="复制选中行", command=_copy_row)
    menu.add_separator()
    menu.add_command(label="复制全部（含表头）", command=_copy_all)

    def _popup(event):
        row_id = tv.identify_row(event.y)
        col_str = tv.identify_column(event.x)  # 形如 "#1"
        if row_id:
            # 若按住 Ctrl 则保留多选，否则只选中右键行
            if not (event.state & 0x0004):
                tv.selection_set(row_id)
            tv.focus(row_id)
        try:
            state["col"] = int(col_str.lstrip("#"))
        except ValueError:
            state["col"] = None
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_current(event=None):
        # 快捷键：有焦点格/明确列时复制单元格，否则复制整行
        col = state.get("col")
        text = _tree_selected_text(tv, col_idx=col)
        if not text:
            text = _tree_selected_text(tv)
        if text:
            copy_to_clipboard(tv, text)
        return "break"

    tv.bind("<Button-3>", _popup)
    tv.bind("<Control-c>", _copy_current)
    tv.bind("<Control-C>", _copy_current)
    # 左键点击时记住所在列，便于 Ctrl+C 复制单元格
    tv.bind("<Button-1>",
            lambda e: state.__setitem__("col",
                                        (lambda s: int(s.lstrip("#"))
                                         if s.lstrip("#").isdigit() else None)
                                        (tv.identify_column(e.x))),
            add="+")


class Card(tk.Frame):
    """白底卡片：1px 边框 + 顶部 4px 强调色条 + hover 变色 + 描述自适应换行。

    - 顶部色条颜色由 accent 决定（橙 C_ACCENT / 蓝 C_INFO / 绿 C_SUCCESS）；
    - desc 的 wraplength 按卡片实际宽度自适应，窄窗口不溢出；
    - hover 递归重染所有子孙，避免 body 内控件底色不一致；
    - body 是唯一的内容挂载点，内边距统一 S_MD；
    - collapsible=True 时标题栏右侧出现 ▶/▼ 按钮，可折叠到只剩标题栏一行
      （start_collapsed=True 即初始折叠）。
    """

    def __init__(self, master, title: str, desc: str = "", accent: str = T.C_ACCENT,
                 on_click=None, collapsible: bool = False,
                 start_collapsed: bool = False, **kw):
        super().__init__(master, bg=T.C_CARD,
                         highlightbackground=T.C_BORDER, highlightthickness=1, **kw)
        tk.Frame(self, bg=accent, height=4).pack(fill=tk.X)
        self.collapsible = collapsible
        self.collapsed = False
        self.toggle_btn = None
        if collapsible:
            head = tk.Frame(self, bg=T.C_CARD)
            head.pack(fill=tk.X, padx=T.CARD_BODY_PAD, pady=(T.S_MD, T.S_XS))
            self._title = SelectableText(head, title,
                                         font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                                         bg=T.C_CARD, fg=T.C_TEXT)
            self._title.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.toggle_btn = tk.Button(head, text="▼", command=self.toggle,
                                        font=(T.FONT_FAMILY, T.F_BODY),
                                        bg=T.C_CARD, fg=T.C_TEXT_M,
                                        activebackground=T.C_HOVER,
                                        activeforeground=T.C_ACCENT,
                                        bd=0, relief=tk.FLAT, width=2,
                                        cursor="hand2")
            self.toggle_btn.pack(side=tk.RIGHT)
        else:
            self._title = SelectableText(self, title,
                                         font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                                         bg=T.C_CARD, fg=T.C_TEXT)
            self._title.pack(fill=tk.X, padx=T.CARD_BODY_PAD, pady=(T.S_MD, T.S_XS))
        self._desc = None
        if desc:
            self._desc = SelectableText(self, desc, font=(T.FONT_FAMILY, T.F_BODY),
                                        bg=T.C_CARD, fg=T.C_TEXT_SUB, wrap="word")
            self._desc.pack(fill=tk.X, padx=T.CARD_BODY_PAD, pady=(0, T.S_SM))
        body = tk.Frame(self, bg=T.C_CARD)
        body.pack(fill=tk.BOTH, expand=True,
                  padx=T.CARD_BODY_PAD, pady=(0, T.CARD_BODY_PAD))
        self.body = body
        if collapsible and start_collapsed:
            self.set_collapsed(True)
        if on_click:
            tk.Label(self, text="进入 →", font=(T.FONT_FAMILY, T.F_SM, "bold"),
                     bg=T.C_CARD, fg=accent).pack(anchor="e", padx=T.CARD_BODY_PAD,
                                                  pady=(0, T.S_SM))
            self.bind("<Button-1>", lambda e: on_click())
            self.bind("<Enter>", lambda e: self._hover(True, accent))
            self.bind("<Leave>", lambda e: self._hover(False, accent))
            self._bind_tree(self, on_click, accent)   # 子孙也要响应，否则"挡住"父事件
        self.bind("<Configure>", self._on_resize)

    # ---------- 折叠 ----------
    def toggle(self) -> None:
        """▶ / ▼ 切换折叠态。"""
        self.set_collapsed(not self.collapsed)

    def set_collapsed(self, on: bool) -> None:
        """折叠 → 只留标题栏一行；展开 → 描述 + body 按原顺序恢复。"""
        self.collapsed = bool(on)
        if self.toggle_btn is not None:
            self.toggle_btn.config(text="▶" if self.collapsed else "▼")
        if self.collapsed:
            if self._desc is not None:
                self._desc.pack_forget()
            self.body.pack_forget()
        else:
            self.body.pack(fill=tk.BOTH, expand=True,
                           padx=T.CARD_BODY_PAD, pady=(0, T.CARD_BODY_PAD))
            if self._desc is not None:
                self._desc.pack(fill=tk.X, padx=T.CARD_BODY_PAD,
                                pady=(0, T.S_SM), before=self.body)

    # ---------- 自适应 ----------
    def _on_resize(self, event) -> None:
        # 描述是 SelectableText，宽度变化由其自身 Configure 自动换行/调整高度
        if self._desc is not None and hasattr(self._desc, "_auto_height"):
            self._desc._auto_height()

    def _bind_tree(self, widget, on_click, accent) -> None:
        for w in widget.winfo_children():
            if isinstance(w, (tk.Frame, tk.Label)):
                w.bind("<Button-1>", lambda e: on_click())
                w.bind("<Enter>", lambda e: self._hover(True, accent))
                w.bind("<Leave>", lambda e: self._hover(False, accent))
                self._bind_tree(w, on_click, accent)

    def _hover(self, on: bool, accent: str) -> None:
        bg = T.C_HOVER if on else T.C_CARD
        border = accent if on else T.C_BORDER
        self.config(bg=bg, highlightbackground=border, cursor="hand2" if on else "")
        self._recolor(self, bg)

    def _recolor(self, widget, bg: str) -> None:
        """递归重染卡片底色子件，保留强调条 / 强调文字等彩色件。"""
        for w in widget.winfo_children():
            try:
                if w.cget("bg") in (T.C_CARD, T.C_HOVER):
                    w.config(bg=bg)
            except tk.TclError:
                pass
            if w.winfo_children():
                self._recolor(w, bg)


class PageHeader(tk.Frame):
    """页面头：大标题 + 副标题 + 2px 强调色分隔线（换行宽度自适应页面宽度）。"""

    def __init__(self, master, title: str, subtitle: str = "", **kw):
        super().__init__(master, bg=T.C_BG, **kw)
        self.pack(fill=tk.X, pady=(0, T.S_SM))
        self._title = SelectableText(self, title, font=(T.FONT_FAMILY, T.F_H1, "bold"),
                                     bg=T.C_BG, fg=T.C_TEXT, wrap="word")
        self._title.pack(fill=tk.X)
        self._sub = None
        if subtitle:
            self._sub = SelectableText(self, subtitle, font=(T.FONT_FAMILY, T.F_SECTION),
                                       bg=T.C_BG, fg=T.C_TEXT_L, wrap="word")
            self._sub.pack(fill=tk.X, pady=(T.S_XS, 0))
        tk.Frame(self, bg=T.C_ACCENT, height=2).pack(fill=tk.X, pady=(T.S_SM, 0))
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        # SelectableText 宽度变化时自动换行/调整高度
        try:
            self._title._auto_height()
            if self._sub is not None:
                self._sub._auto_height()
        except (tk.TclError, AttributeError):
            pass


# ---------- 按钮工厂（任务书 §4.5：主按钮橙底白字 / 次按钮白底灰边 / 危险红底）----------
def primary_button(master, text: str, command=None, **kw) -> tk.Button:
    """主按钮：橙底白字，hover 深橙，flat、padx=12 pady=8、cursor=hand2。"""
    padx = kw.pop("padx", T.S_MD)
    pady = kw.pop("pady", T.S_SM)
    return tk.Button(master, text=text, command=command,
                     font=(T.FONT_FAMILY, T.F_BODY, "bold"),
                     bg=T.C_ACCENT, fg=T.C_WHITE,
                     activebackground=T.C_ACCENT_HOVER, activeforeground=T.C_WHITE,
                     bd=0, relief=tk.FLAT, padx=padx, pady=pady, cursor="hand2", **kw)


def secondary_button(master, text: str, command=None, **kw) -> tk.Button:
    """次按钮：白底灰边黑字。"""
    padx = kw.pop("padx", T.S_MD)
    pady = kw.pop("pady", T.S_SM)
    return tk.Button(master, text=text, command=command,
                     font=(T.FONT_FAMILY, T.F_BODY),
                     bg=T.C_CARD, fg=T.C_TEXT,
                     activebackground=T.C_HOVER, activeforeground=T.C_TEXT,
                     bd=0, relief=tk.FLAT,
                     highlightbackground=T.C_BORDER, highlightthickness=1,
                     padx=padx, pady=pady, cursor="hand2", **kw)


def danger_button(master, text: str, command=None, **kw) -> tk.Button:
    """危险按钮（原地覆盖类二次确认用）：红底白字。"""
    padx = kw.pop("padx", T.S_MD)
    pady = kw.pop("pady", T.S_SM)
    return tk.Button(master, text=text, command=command,
                     font=(T.FONT_FAMILY, T.F_BODY, "bold"),
                     bg=T.C_DANGER, fg=T.C_WHITE,
                     activebackground=T.C_DANGER, activeforeground=T.C_WHITE,
                     bd=0, relief=tk.FLAT, padx=padx, pady=pady, cursor="hand2", **kw)


def section_label(master, text: str) -> tk.Label:
    """卡片内分区小标题（粗体 F_SECTION）。"""
    return tk.Label(master, text=text, font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                    bg=T.C_CARD, fg=T.C_TEXT, anchor="w")


class SelectableText(tk.Text):
    """可鼠标拖选复制的文字块（基于 Text，无边框只读）。

    - wrap="none"（默认）：单行，宽度按内容自适应，强制不换行；
    - wrap="word"：多行，宽度跟随容器，高度按显示行数自动撑开；
    - 鼠标拖选高亮、Ctrl+C 复制；禁止键入编辑。
    """

    def __init__(self, master, text: str = "", *, bg=T.C_CARD, fg=T.C_TEXT_L,
                 font=None, wrap="none", **kw):
        # 兼容 Label 常见但 Text 不支持的布局参数
        kw.pop("anchor", None)
        justify = kw.pop("justify", tk.LEFT)
        kw.pop("wraplength", None)
        font = font or (T.FONT_FAMILY, T.F_SM)
        self._font_tuple = font
        self._font_obj = _build_font(font)
        self._raw_text = text
        self._wrap_word = (wrap == "word")
        if self._wrap_word:
            width_chars, height_lines = 80, 1
        else:
            width_chars = self._fit_width(text)
            height_lines = max(1, text.count("\n") + 1)
        super().__init__(master, height=height_lines, width=width_chars,
                         borderwidth=0, relief="flat",
                         background=bg, foreground=fg, font=font,
                         cursor="xterm", wrap=wrap, padx=0, pady=0,
                         highlightthickness=0, takefocus=1, **kw)
        self.insert("1.0", text)
        if justify != tk.LEFT:
            self.tag_configure("_j", justify=justify)
            self.tag_add("_j", "1.0", "end-1c")
        self._bg = bg
        self.bind("<KeyPress>", self._on_key)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", lambda e: self.tag_remove("sel", "1.0", "end"))
        if self._wrap_word:
            self.bind("<Configure>", self._auto_height)
            self.after_idle(self._auto_height)

    def _fit_width(self, text: str) -> int:
        """返回刚好容纳最长一行文本的 Text width（字符数）。"""
        try:
            lines = text.split("\n")
            longest = max(lines, key=lambda s: self._font_obj.measure(s))
            pixel = self._font_obj.measure(longest)
            avg = self._font_obj.measure("0")
            return max(1, -(-pixel // avg))
        except (tk.TclError, ValueError):
            return max(1, len(text))

    def _auto_height(self, _event=None):
        """wrap=word 模式：按实际显示行数（含自动换行）撑开高度。"""
        self.update_idletasks()
        try:
            res = self.count("1.0", "end-1c", "displaylines")
            lines = (res[0] if res else 1) + 1
        except tk.TclError:
            lines = 1
        if int(self.cget("height")) != lines:
            self.config(height=lines)

    def _on_key(self, event):
        """只拦截可打印字符；Ctrl 组合键、功能键、方向键放行。"""
        if event.state & 0x0004:
            return None
        nav_keys = {"Shift_L", "Shift_R", "Control_L", "Control_R",
                    "Alt_L", "Alt_R", "Return", "BackSpace", "Delete",
                    "Escape", "Tab", "Home", "End", "Left", "Right",
                    "Up", "Down", "Prior", "Next", "Insert", "Caps_Lock",
                    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8",
                    "F9", "F10", "F11", "F12"}
        if event.keysym in nav_keys:
            return None
        return "break"

    def _on_focus(self, _event=None):
        # 聚焦时改浅底色提示"这里可选中"，失焦自动还原
        self.config(bg=T.C_HOVER)

    def set_text(self, text: str) -> None:
        self._raw_text = text
        self.delete("1.0", "end")
        self.insert("1.0", text)
        if self._wrap_word:
            self._auto_height()
        else:
            self.config(height=max(1, text.count("\n") + 1),
                        width=self._fit_width(text))

    def configure(self, **kw):
        """兼容 .config(text=...) 写法：Text 本身不认 text 参数。"""
        if "text" in kw:
            self.set_text(kw.pop("text"))
        return super().configure(**kw)

    def cget(self, key):
        """兼容 .cget('text') 写法：返回当前文本（Label 语义）。"""
        if key == "text":
            return self._raw_text
        return super().cget(key)

    config = configure


def _build_font(font):
    """把 Label 风格的 font tuple 转成 tkfont.Font，用于测量。"""
    try:
        if isinstance(font, (tuple, list)):
            kwf = {"family": font[0], "size": font[1]}
            if len(font) >= 3 and str(font[2]) == "bold":
                kwf["weight"] = "bold"
            return tkfont.Font(**kwf)
        if isinstance(font, tkfont.Font):
            return font
        return tkfont.Font(font=font)
    except tk.TclError:
        return tkfont.Font(family=T.FONT_FAMILY, size=T.F_SM)


def vlabel(master, text: str = "", **kw) -> SelectableText:
    """tk.Label 的可选中替代：鼠标拖选 + Ctrl+C；参数与 tk.Label 一致。"""
    return SelectableText(master, text, **kw)


def hint_label(master, text: str, *, selectable: bool = True) -> tk.Widget:
    """卡片内辅助说明；默认可鼠标拖选复制。"""
    if selectable:
        return SelectableText(master, text)
    return tk.Label(master, text=text, font=(T.FONT_FAMILY, T.F_SM),
                    bg=T.C_CARD, fg=T.C_TEXT_L, anchor="w", justify=tk.LEFT)


def styled_tree(master, columns, height=8, show="headings") -> ttk.Treeview:
    """统一风格的 Treeview（样式由 App._apply_treeview_style 注册）。

    columns: [(列 id, 标题, 宽度, 对齐), ...]
    自动带右键菜单 + Ctrl+C 复制。
    """
    tv = ttk.Treeview(master, columns=[c[0] for c in columns], show=show,
                      height=height, style="RenameMaster.Treeview",
                      selectmode="extended")
    for cid, heading, width, anchor in columns:
        tv.heading(cid, text=heading, anchor=anchor)
        tv.column(cid, width=width, anchor=anchor, stretch=(width == 0))
    enable_tree_copy(tv)
    return tv
