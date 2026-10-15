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
        self._title = None
        if collapsible:
            head = tk.Frame(self, bg=T.C_CARD)
            head.pack(fill=tk.X, padx=T.CARD_BODY_PAD, pady=(T.S_MD, T.S_XS))
            if title:
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
        elif title:
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
            self._click = (on_click, accent)
            self._bind_tree(self, on_click, accent)   # 子孙也要响应，否则"挡住"父事件
            # 调用方是 `Card(...)` 之后再往 card.body 里塞内容的（见 home.py），
            # 上面这次只能绑到已存在的子件；等一轮 idle 后补绑一次，把后加的
            # emoji / 标题 / 描述也纳入点击区。_bind_tree 是幂等的，重复不叠加。
            self.after_idle(self.refresh_click)
        else:
            self._click = None
        self.bind("<Configure>", self._on_resize)

    # ---------- 点击 / hover ----------
    def refresh_click(self) -> None:
        """给「本次新增的」子孙补上点击跳转与 hover 高亮（可重复调用）。"""
        if self._click is not None:
            self._bind_tree(self, *self._click)

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
        """递归绑定子孙的点击 / hover，幂等：同一控件只绑一次，不会叠加。"""
        for w in widget.winfo_children():
            if not getattr(w, "_card_click_bound", False):
                w._card_click_bound = True
                # tk.Text 也要带上：入口卡片的 emoji / 标题 / 描述都是
                # SelectableText(=tk.Text)，漏掉它们就会出现
                # "点字没反应、只有点卡片空白才跳转"。
                if isinstance(w, (tk.Frame, tk.Label, tk.Text)):
                    # add="+" 而不是覆盖：子孙里可能已经有自己的 <Button-1>
                    # （复选框切换、链接按钮…），覆盖式绑定会把它们悄悄吃掉。
                    w.bind("<Button-1>", lambda e: on_click(), add="+")
                    w.bind("<Enter>", lambda e: self._hover(True, accent), add="+")
                    w.bind("<Leave>", lambda e: self._hover(False, accent), add="+")
            if w.winfo_children():
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
                 font=None, wrap="none", compact: bool = False, **kw):
        # 兼容 Label 常见但 Text 不支持的布局参数
        kw.pop("anchor", None)
        justify = kw.pop("justify", tk.LEFT)
        kw.pop("wraplength", None)
        font = font or (T.FONT_FAMILY, T.F_SM)
        self._font_tuple = font
        self._font_obj = _build_font(font)
        self._raw_text = text
        self._compact = compact       # True：高度紧贴显示行数，不留底部空行
        self._wrap_word = (wrap == "word")
        if self._wrap_word:
            # wrap=word 的文本块宽度交给容器（外面统一 fill=X 拉伸），
            # 这里必须给一个"最小"的 width 字符数。旧值 80 会让 Text 向
            # 布局管理器索要 80 字符（≈500px）的宽度，5 张首页卡片直接撑出
            # 5654px 的网格需求 → 右侧卡片被裁（v1.9 修复）。
            width_chars, height_lines = 1, 1
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
        """wrap=word 模式：按实际显示行数（含自动换行）撑开高度。

        compact：高度=显示行数，紧贴内容（用于单行居中的装饰元素）；
        否则多留一行，避免多行段落末行被裁。
        """
        # 首次布局前 Text 只有 width=1 字符（≈10px），此时按它算行数会得到
        # 上百行、把父容器请求高度撑爆（随后虽会收敛，但中间会闪一屏空白）。
        # 宽度还没真正铺开时直接跳过，等真正拿到宽度后的 Configure 再算。
        try:
            if self.winfo_width() < 60:
                return
        except tk.TclError:
            return
        self.update_idletasks()
        try:
            res = self.count("1.0", "end-1c", "displaylines")
            shown = res[0] if res else 1
        except tk.TclError:
            shown = 1
        lines = shown if self._compact else shown + 1
        if int(self.cget("height")) != lines:
            self.config(height=lines)

    # 只读白名单：允许的光标移动 / 选择键（可带 Ctrl/Shift，均不改内容）
    _MOVE_KEYS = {"Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next",
                  "KP_Left", "KP_Right", "KP_Up", "KP_Down", "KP_Home",
                  "KP_End", "KP_Prior", "KP_Next"}
    _MODIFIER_KEYS = {"Shift_L", "Shift_R", "Control_L", "Control_R",
                      "Alt_L", "Alt_R", "Caps_Lock", "Alt_Pro"}

    def _on_key(self, event):
        """只读白名单：默认拦截一切按键，仅放行导航 / 选择 / 复制 / 全选。

        必须拦截：BackSpace / Delete / Return / Tab / 空格 / 可打印字符，
        以及 Ctrl+V（粘贴）、Ctrl+X（剪切）、Ctrl+Z / Y（撤销重做）等。
        """
        ks = event.keysym
        ctrl = bool(event.state & 0x0004)

        # ① 纯修饰键（单独按下，无动作）
        if ks in self._MODIFIER_KEYS:
            return None
        # ② 光标移动 / 选择（Shift 扩展选区、Ctrl 跳词，均无害）
        if ks in self._MOVE_KEYS:
            return None
        # ③ 功能键 F1–F12 / Escape（默认无编辑动作）
        if ks == "Escape" or (len(ks) > 1 and ks[0] == "F" and ks[1:].isdigit()):
            return None
        # ④ Ctrl 组合：仅放行 Ctrl+C 复制 / Ctrl+Insert 复制 / Ctrl+A 全选
        if ctrl:
            if ks in ("c", "C", "a", "A", "Insert"):
                return None
            return "break"
        # ⑤ 其余一律拦截（BackSpace/Delete/Return/Tab/Insert/空格/可打印字符…）
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


# ---------- Treeview 列宽：按内容自适应 + 剩余宽度铺满容器 ----------
_AUTOFIT_SAMPLE = 400      # 量列宽时最多采样多少行（超长列表避免每次 resize 全量测量）
_AUTOFIT_PAD = 22          # 单元格左右留白 + 边框 / 排序箭头余量（px）


def _style_font(widget, style_name: str, fallback: str = "TkDefaultFont") -> tkfont.Font:
    """取某个 ttk 样式实际生效的字体；查不到时退回 Tk 默认字体。"""
    spec = ""
    try:
        spec = widget.tk.call("ttk::style", "lookup", style_name, "-font") or ""
    except tk.TclError:
        pass
    for candidate in (spec, fallback):
        if not candidate:
            continue
        try:
            return tkfont.Font(root=widget, font=candidate)
        except tk.TclError:
            continue
    return tkfont.nametofont("TkDefaultFont", root=widget)


def _content_widths(tv: ttk.Treeview, cols: list[str], font, head_font) -> dict:
    """量出每列「标题 + 采样行内容」所需宽度（px，已含留白）。"""
    need = {}
    for cid in cols:
        head = str(tv.heading(cid).get("text") or "")
        need[cid] = int(head_font.measure(head)) + _AUTOFIT_PAD
    for iid in tv.get_children()[:_AUTOFIT_SAMPLE]:
        for cid in cols:
            text = tv.set(iid, cid)
            if text:
                w = int(font.measure(text)) + _AUTOFIT_PAD
                if w > need[cid]:
                    need[cid] = w
    return need


def autofit_columns(tv: ttk.Treeview, flex: str | None = None, min_w: int = 48,
                    floors: dict | None = None, content: dict | None = None,
                    fonts: tuple | None = None) -> None:
    """重算 Treeview 列宽：每列贴合内容，剩余宽度全给 flex 列。

    - 每列宽 = max(标题, 采样行内容) 的像素宽 + 留白 —— 窄内容不再占一大片空白；
    - floors：调用方给的参考最小宽度（列 id → px），保证数据少时也不至于挤成一条；
    - 容器比内容宽 → 差额全部给 flex 列，表格铺满整个区域，右侧不留空白；
    - 容器比内容窄 → 先压 flex 列，再等比压其它列，都压到 min_w 为止
      （再不够就让 Treeview 自己裁剪/滚动，不会把列压成 0）。
    content / fonts 是给 autofit_tree 复用的量宽缓存与字体对象，可直接省略。
    """
    cols = list(tv["columns"])
    if not cols:
        return
    if flex not in cols:
        flex = cols[0]
    floors = floors or {}
    if not fonts:
        fonts = (_style_font(tv, "RenameMaster.Treeview"),
                 _style_font(tv, "RenameMaster.Treeview.Heading"))
    if content is None:
        content = {}
    if not content:
        content.update(_content_widths(tv, cols, fonts[0], fonts[1]))

    need = {cid: max(int(content.get(cid, 0)), int(floors.get(cid, min_w)), min_w)
            for cid in cols}
    avail = int(tv.winfo_width())
    total = sum(need.values())
    if avail <= 1:            # 布局还没完成：先按内容给宽，<Configure> 时再补齐
        avail = total
    if avail > total:
        need[flex] += avail - total
    elif avail < total:
        over = total - avail
        cut = min(over, max(0, need[flex] - min_w))
        need[flex] -= cut
        over -= cut
        slack = {c: max(0, need[c] - min_w) for c in cols if c != flex}
        room = sum(slack.values())
        if over > 0 and room > 0:
            over = min(over, room)
            for cid, free in slack.items():
                if free:
                    need[cid] -= int(round(over * free / room))
    for cid in cols:
        tv.column(cid, width=int(need[cid]), minwidth=min_w, stretch=False)


def refit_tree(tv: ttk.Treeview) -> None:
    """数据变化后重算列宽（flex / 参考宽度由 styled_tree 记在控件上）。"""
    cfg = getattr(tv, "_rm_autofit", None)
    if not cfg:
        return
    cfg["content"] = {}          # 行内容变了，量宽缓存作废
    autofit_columns(tv, **cfg)


def autofit_tree(tv: ttk.Treeview, flex: str | None = None, min_w: int = 48,
                 floors: dict | None = None) -> None:
    """让 Treeview 列宽随内容自适应、并随容器宽度铺满（含窗口缩放）。"""
    cfg = {"flex": flex, "min_w": min_w, "floors": floors or {}, "content": {},
           "fonts": (_style_font(tv, "RenameMaster.Treeview"),
                     _style_font(tv, "RenameMaster.Treeview.Heading"))}
    tv._rm_autofit = cfg                     # type: ignore[attr-defined]
    last = {"w": -1}

    def _on_configure(event) -> None:
        if event.width == last["w"]:         # 同一宽度重复触发时不必重量
            return
        last["w"] = event.width
        autofit_columns(tv, **cfg)

    tv.bind("<Configure>", _on_configure, add="+")
    autofit_columns(tv, **cfg)


def styled_tree(master, columns, height=8, show="headings",
                flex: str | None = None) -> ttk.Treeview:
    """统一风格的 Treeview（样式由 App._apply_treeview_style 注册）。

    columns: [(列 id, 标题, 参考宽度, 对齐), ...]
    列宽交给 autofit_tree 动态算：内容多宽就多宽，剩余宽度全给 flex 列
    （默认第一列），因此表格始终铺满容器、不留空白大列；columns 里的宽度
    只作为该列的参考最小宽度。数据变化后调用 refit_tree(tv) 重新贴合内容。
    自动带右键菜单 + Ctrl+C 复制。
    """
    tv = ttk.Treeview(master, columns=[c[0] for c in columns], show=show,
                      height=height, style="RenameMaster.Treeview",
                      selectmode="extended")
    floors = {}
    for cid, heading, width, anchor in columns:
        tv.heading(cid, text=heading, anchor=anchor)
        tv.column(cid, width=width, anchor=anchor, stretch=False)
        floors[cid] = int(width)
    enable_tree_copy(tv)
    autofit_tree(tv, flex=flex, floors=floors)
    return tv


# ---------- 弹窗（对话框）统一布局：尺寸 / 居中 / 双向滚动 / 固定按钮栏 ----------
def fit_dialog(win, width: int = 960, height: int = 600,
               min_w: int = 760, min_h: int = 480) -> tk.Toplevel:
    """设置弹窗初始尺寸、最小尺寸并屏幕居中。

    - 初始尺寸不超过屏幕的 90%；
    - minsize 保证缩小后信息仍基本可见；
    - 在 win.configure(bg=...) 之后调用。
    """
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w = min(width, int(sw * 0.92))
    h = min(height, int(sh * 0.9))
    min_w = min(min_w, w)
    min_h = min(min_h, h)
    win.minsize(min_w, min_h)
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")
    return win


def dialog_tree(master, columns, bg: str, height: int = 14,
                flex: str | None = None):
    """带「垂直 + 水平」滚动条的 Treeview，返回 (tv, 外层容器)。

    - 纵向滚动：文件多时上下查看；
    - 横向滚动：文件名长、列总宽超过窗口时左右查看，完整显示文件名；
    - 列宽按内容自适应并铺满容器（flex 列吃掉剩余宽度，默认第一列）；
    - 外层容器已 pack(fill=BOTH, expand=True)，调用方无需再 pack tv；
    - 内容超出可视区时由 Treeview 自身滚动，高度由外层弹窗自适应，
      不会把底部按钮栏挤出窗口。
    """
    box = tk.Frame(master, bg=bg)
    box.pack(fill=tk.BOTH, expand=True, padx=T.S_LG, pady=(0, T.S_SM))

    tv = styled_tree(box, columns, height=height, flex=flex)
    vsb = ttk.Scrollbar(box, orient="vertical",
                        style="RenameMaster.Vertical.TScrollbar",
                        command=tv.yview)
    hsb = ttk.Scrollbar(box, orient="horizontal",
                        style="RenameMaster.Horizontal.TScrollbar",
                        command=tv.xview)
    tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)
    tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    return tv, box


def dialog_buttons(master, bg: str, on_close, on_confirm=None,
                   confirm_text: str = "▶ 确认执行", close_text: str = "关闭"):
    """弹窗底部固定按钮栏（不随内容滚动），始终可见。

    - 用 pack(side=BOTTOM) 固定在窗口底部：中间内容区即使请求高度很大、
      或有很多行，也只会压缩内容区（Treeview 自身滚动），按钮栏永远按
      自身请求高度完整显示，不会被挤成一条线或挤出可视区；
    - 右侧依次：确认执行（主按钮，可选）/ 关闭（次按钮）。
    返回按钮栏 Frame。
    """
    btm = tk.Frame(master, bg=bg)
    btm.pack(side=tk.BOTTOM, fill=tk.X, padx=T.S_LG, pady=(T.S_SM, T.S_MD))
    secondary_button(btm, close_text, command=on_close).pack(side=tk.RIGHT)
    if on_confirm is not None:
        primary_button(btm, confirm_text, command=on_confirm
                       ).pack(side=tk.RIGHT, padx=(0, T.S_SM))
    return btm
