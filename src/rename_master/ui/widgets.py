"""通用 UI 组件（Card / PageHeader / 按钮工厂）——照搬 Wifibond widgets.py。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from rename_master.ui import theme as T


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
            self._title = tk.Label(head, text=title,
                                   font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                                   bg=T.C_CARD, fg=T.C_TEXT, anchor="w",
                                   justify=tk.LEFT)
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
            self._title = tk.Label(self, text=title,
                                   font=(T.FONT_FAMILY, T.F_SECTION, "bold"),
                                   bg=T.C_CARD, fg=T.C_TEXT, anchor="w",
                                   justify=tk.LEFT)
            self._title.pack(fill=tk.X, padx=T.CARD_BODY_PAD, pady=(T.S_MD, T.S_XS))
        self._desc = None
        if desc:
            self._desc = tk.Label(self, text=desc, font=(T.FONT_FAMILY, T.F_BODY),
                                  bg=T.C_CARD, fg=T.C_TEXT_SUB, justify=tk.LEFT,
                                  anchor="w", wraplength=200)
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
        if self._desc is None:
            return
        wl = max(80, self.winfo_width() - 2 * T.CARD_BODY_PAD)
        if self._desc.cget("wraplength") != wl:
            self._desc.config(wraplength=wl)

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
        self._title = tk.Label(self, text=title, font=(T.FONT_FAMILY, T.F_H1, "bold"),
                               bg=T.C_BG, fg=T.C_TEXT, anchor="w", justify=tk.LEFT,
                               wraplength=600)
        self._title.pack(fill=tk.X)
        self._sub = None
        if subtitle:
            self._sub = tk.Label(self, text=subtitle, font=(T.FONT_FAMILY, T.F_SECTION),
                                 bg=T.C_BG, fg=T.C_TEXT_L, anchor="w", justify=tk.LEFT,
                                 wraplength=600)
            self._sub.pack(fill=tk.X, pady=(T.S_XS, 0))
        tk.Frame(self, bg=T.C_ACCENT, height=2).pack(fill=tk.X, pady=(T.S_SM, 0))
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        wl = max(120, self.winfo_width() - 2 * T.S_LG)
        try:
            if self._title.cget("wraplength") != wl:
                self._title.config(wraplength=wl)
            if self._sub is not None and self._sub.cget("wraplength") != wl:
                self._sub.config(wraplength=wl)
        except tk.TclError:
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


def hint_label(master, text: str) -> tk.Label:
    """卡片内辅助说明（F_SM 次级色）。"""
    return tk.Label(master, text=text, font=(T.FONT_FAMILY, T.F_SM),
                    bg=T.C_CARD, fg=T.C_TEXT_L, anchor="w", justify=tk.LEFT)


def styled_tree(master, columns, height=8, show="headings") -> ttk.Treeview:
    """统一风格的 Treeview（样式由 App._apply_treeview_style 注册）。

    columns: [(列 id, 标题, 宽度, 对齐), ...]
    """
    tv = ttk.Treeview(master, columns=[c[0] for c in columns], show=show,
                      height=height, style="RenameMaster.Treeview",
                      selectmode="extended")
    for cid, heading, width, anchor in columns:
        tv.heading(cid, text=heading, anchor=anchor)
        tv.column(cid, width=width, anchor=anchor, stretch=(width == 0))
    return tv
