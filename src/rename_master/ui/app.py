"""主窗口框架：左侧深色导航 + 右侧内容区（照抄 Wifibond app.py 布局思路）。

任务书 §4.1 / §4.2：
- 左导航 112 逻辑 px、底色 #1e293b，高 DPI 下按 `winfo_fpixels("1i")/72` 放大；
- 右内容区 #f1f5f9，Canvas + Scrollbar 包裹，窗口缩小可纵向滚动；
- 窗口默认最大化，`minsize(960, 640)`。
"""
from __future__ import annotations

import logging
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Callable, Dict, Optional

from rename_master.config.manager import ConfigManager
from rename_master.ui import theme as T

logger = logging.getLogger(__name__)

APP_TITLE = "RenameMaster"
APP_SUBTITLE = "文件批量命名助手"
VERSION = "1.0"

# 导航字号（按钮创建 / 激活态统用同一档位，避免切页时字宽跳变）
_NAV_FONT_SIZE = 10

NAV_ITEMS = [
    ("home", "🏠", "首页"),
    ("photo", "📷", "照片命名"),
    ("pdf", "📄", "PDF 命名"),
    ("spreadsheet", "📊", "表格命名"),
    ("document", "📄", "文档命名"),
    ("about", "ℹ️", "关于"),
]


class App:
    """左侧导航 + 右侧内容框架；页面延迟构建；底部操作栏由页面注册（不随滚动）。"""

    def __init__(self, root: tk.Tk, config: Optional[ConfigManager] = None):
        self.root = root
        self.pages: Dict[str, tk.Frame] = {}
        self._page_builders: Dict[str, Callable[[], None]] = {}
        self._closed = False
        self.cur = "home"
        self._syncing = False                         # _sync_canvas 重入保护
        self.pending_drop_path: Optional[str] = None   # 页面未 build 时先存着
        self.cfg = config or ConfigManager()

        self.root.title(f"{APP_TITLE} · {APP_SUBTITLE}")
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        # 几何值仅作兜底（state('zoomed') 失败时生效）
        self.root.geometry(f"{min(1680, int(sw * 0.92))}x{min(960, int(sh * 0.92))}")
        self.root.minsize(960, 640)
        try:
            self.root.state("zoomed")        # Windows：默认最大化
        except tk.TclError:
            pass
        self.root.configure(bg=T.C_BG)
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 布局 ----------
    def _build(self) -> None:
        self.df = tkfont.Font(family=T.FONT_FAMILY, size=10)
        self.root.option_add("*Font", self.df)
        self._apply_treeview_style()

        # 高 DPI：tkinter 的 Frame(width=...) 是物理像素，不随 tk scaling 放大，
        # 200% 屏上 112 逻辑 px 视觉只剩一半 → 按 fpixels 等比放大（逻辑尺寸不变）。
        try:
            self.ui_scale = max(1.0, self.root.winfo_fpixels("1i") / 72.0)
        except (tk.TclError, ZeroDivisionError):
            self.ui_scale = 1.0

        main = tk.Frame(self.root, bg=T.C_BG)
        main.pack(fill=tk.BOTH, expand=True)

        self.navs: Dict[str, tk.Button] = {}
        nav_w = T.NAV_WIDTH
        nav = tk.Frame(main, bg=T.C_PRIMARY, width=int(nav_w * self.ui_scale))
        nav.pack(side=tk.LEFT, fill=tk.Y)
        nav.pack_propagate(False)

        # Logo 区
        lf = tk.Frame(nav, bg=T.C_PRIMARY, height=int(T.LOGO_HEIGHT * self.ui_scale))
        lf.pack(fill=tk.X, pady=(T.S_LG, T.S_SM))
        lf.pack_propagate(False)
        tk.Label(lf, text="◉", font=(T.FONT_FAMILY, 19),
                 bg=T.C_PRIMARY, fg=T.C_ACCENT).pack(pady=(T.S_XS, 0))
        tk.Label(lf, text=APP_TITLE, font=(T.FONT_FAMILY, 14, "bold"),
                 bg=T.C_PRIMARY, fg=T.C_ACCENT).pack(pady=(T.S_XS, 0))
        tk.Label(lf, text=APP_SUBTITLE, font=(T.FONT_FAMILY, T.F_SM),
                 bg=T.C_PRIMARY, fg=T.C_LOGO_SUB,
                 wraplength=int(nav_w * self.ui_scale) - 16,
                 justify=tk.CENTER).pack(padx=T.S_XS)

        # 导航按钮：激活 #334155 + 橙字，未激活 #94a3b8
        for key, icon, text in NAV_ITEMS:
            btn = tk.Button(nav, text=f"{icon} {text}",
                            font=(T.FONT_FAMILY, _NAV_FONT_SIZE),
                            bg=T.C_PRIMARY, fg=T.C_TEXT_FADE,
                            activebackground=T.C_SECONDARY, activeforeground=T.C_ACCENT,
                            bd=0, padx=5, pady=5, anchor="w", cursor="hand2",
                            relief=tk.FLAT, command=lambda k=key: self.show(k))
            btn.pack(fill=tk.X, pady=T.S_XS, padx=T.S_XS)
            self.navs[key] = btn
        tk.Frame(nav, bg=T.C_PRIMARY).pack(fill=tk.BOTH, expand=True)

        # 状态栏 + 版本号（沉在左栏底部）
        self.status = tk.StringVar(value="就绪")
        sf = tk.Frame(nav, bg=T.C_SECONDARY, height=int(42 * self.ui_scale))
        sf.pack(fill=tk.X, padx=T.S_SM, pady=(0, T.S_XS))
        sf.pack_propagate(False)
        self.status_label = tk.Label(sf, textvariable=self.status,
                                     font=(T.FONT_FAMILY, T.F_SM),
                                     bg=T.C_SECONDARY, fg=T.C_TEXT_FADE,
                                     anchor="w", justify=tk.LEFT)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True,
                               padx=T.S_SM, pady=T.S_SM)
        tk.Label(nav, text=f"v{VERSION}", font=(T.FONT_FAMILY, T.F_SM),
                 bg=T.C_PRIMARY, fg=T.C_TEXT_L).pack(pady=(0, T.S_SM))

        # 右侧内容区：滚动画布 + 固定操作栏
        self.content = tk.Frame(main, bg=T.C_BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll_host = tk.Frame(self.content, bg=T.C_BG)
        self.scroll_host.pack(fill=tk.BOTH, expand=True)
        self.action_host = tk.Frame(self.content, bg=T.C_BG)
        self._build_scroll_area()

        self._page_builders = {
            "home": self._build_home,
            "photo": self._build_photo,
            "pdf": self._build_pdf,
            "spreadsheet": self._build_spreadsheet,
            "document": self._build_document,
            "about": self._build_about,
        }
        self.show("home")

    def _apply_treeview_style(self) -> None:
        """ttk 全局样式统一（Treeview / Combobox / Entry / Scrollbar / Progressbar）。"""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("RenameMaster.Treeview", rowheight=T.TREE_ROW_HEIGHT,
                        background=T.C_CARD, fieldbackground=T.C_CARD,
                        foreground=T.C_TEXT, borderwidth=0,
                        font=(T.FONT_FAMILY, T.F_SM))
        style.configure("RenameMaster.Treeview.Heading", background=T.C_PRIMARY,
                        foreground=T.C_WHITE,
                        font=(T.FONT_FAMILY, T.F_SM, "bold"),
                        relief="flat", padding=(6, 8))
        style.map("RenameMaster.Treeview",
                  background=[("selected", T.C_HOVER), ("active", T.C_ROW_ALT)],
                  foreground=[("selected", T.C_TEXT)])
        style.map("RenameMaster.Treeview.Heading",
                  background=[("active", T.C_SECONDARY)])

        style.configure("RenameMaster.TCombobox",
                        fieldbackground=T.C_CARD, background=T.C_CARD,
                        foreground=T.C_TEXT, bordercolor=T.C_BORDER,
                        lightcolor=T.C_CARD, darkcolor=T.C_CARD,
                        arrowcolor=T.C_TEXT_M, borderwidth=1, relief="flat",
                        padding=(6, 4), font=(T.FONT_FAMILY, T.F_BODY))
        style.map("RenameMaster.TCombobox",
                  fieldbackground=[("readonly", T.C_CARD), ("disabled", T.C_BG)],
                  foreground=[("disabled", T.C_TEXT_FADE)],
                  bordercolor=[("focus", T.C_INFO), ("hover", T.C_TEXT_FADE)])

        style.configure("RenameMaster.TEntry",
                        fieldbackground=T.C_CARD, foreground=T.C_TEXT,
                        bordercolor=T.C_BORDER, lightcolor=T.C_CARD,
                        darkcolor=T.C_CARD, borderwidth=1, relief="flat",
                        padding=(6, 4), font=(T.FONT_FAMILY, T.F_BODY))
        style.map("RenameMaster.TEntry",
                  fieldbackground=[("disabled", T.C_BG)],
                  foreground=[("disabled", T.C_TEXT_FADE)],
                  bordercolor=[("focus", T.C_INFO), ("hover", T.C_TEXT_FADE)])

        style.configure("RenameMaster.Vertical.TScrollbar",
                        background=T.C_TEXT_FADE, troughcolor=T.C_BG,
                        borderwidth=0, arrowsize=0, width=10, relief="flat")
        style.map("RenameMaster.Vertical.TScrollbar",
                  background=[("pressed", T.C_TEXT_M), ("active", T.C_TEXT_M)])
        style.configure("RenameMaster.Horizontal.TScrollbar",
                        background=T.C_TEXT_FADE, troughcolor=T.C_BG,
                        borderwidth=0, arrowsize=0, width=10, relief="flat")

        style.configure("RenameMaster.Horizontal.TProgressbar",
                        background=T.C_ACCENT, troughcolor=T.C_BORDER,
                        borderwidth=0, thickness=10)

    def _build_scroll_area(self) -> None:
        """内容区 Canvas 滚动容器（内容永不因窗口变小而丢失）。"""
        self.canvas = tk.Canvas(self.scroll_host, bg=T.C_BG,
                                highlightthickness=0, bd=0)
        self._vsb = ttk.Scrollbar(self.scroll_host, orient="vertical",
                                  style="RenameMaster.Vertical.TScrollbar",
                                  command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.page_host = tk.Frame(self.canvas, bg=T.C_BG)
        self._page_window = self.canvas.create_window((0, 0), window=self.page_host,
                                                      anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self._sync_canvas())
        # 内容高度变化（模式切换 / 动态增删控件）时同步 item 高度，否则内容被压缩
        self.page_host.bind("<Configure>", lambda e: self._sync_canvas())
        self.root.bind_all("<MouseWheel>", self._on_wheel)

    def request_relayout(self) -> None:
        """页面动态增删 / 显隐控件（如切换模式）后调用：空闲时同步滚动区高度。"""
        try:
            self.root.after_idle(self._sync_canvas)
        except tk.TclError:
            pass

    def _sync_canvas(self) -> None:
        """按当前视口重算 page_host 窗口尺寸（切页 / 缩放共用同一条路径）。"""
        if self._syncing:
            return
        self._syncing = True
        try:
            return self._do_sync_canvas()
        finally:
            self._syncing = False

    def _do_sync_canvas(self) -> None:
        try:
            view_w = self.canvas.winfo_width()
            view_h = self.canvas.winfo_height()
        except tk.TclError:
            return
        self.canvas.itemconfig(self._page_window, width=view_w)
        self.page_host.update_idletasks()
        # page_host 高度 = max(可视, 内容需求)：内容超一屏时可滚动，否则静态铺满
        try:
            need = int(self.page_host.winfo_reqheight())
        except tk.TclError:
            need = view_h
        self.canvas.itemconfig(self._page_window, height=max(view_h, need))
        self._refresh_scroll()

    def _refresh_scroll(self) -> None:
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            need = int(self.page_host.winfo_reqheight())
            vis = self.canvas.winfo_height()
            if need <= vis + 4:
                self._vsb.pack_forget()
                self.canvas.configure(yscrollcommand="")
            else:
                self.canvas.configure(yscrollcommand=self._vsb.set)
                if not self._vsb.winfo_ismapped():
                    self._vsb.pack(side=tk.RIGHT, fill=tk.Y)
        except tk.TclError:
            pass

    def _on_wheel(self, event) -> None:
        """滚轮仅在指针位于内容区时生效（避免误滚左侧导航）。"""
        if not self._is_in_content(getattr(event, "widget", None)):
            return
        if self._widget_scrolls_itself(getattr(event, "widget", None)):
            return
        try:
            delta = int(-1 * (event.delta / 120))
        except (AttributeError, TypeError):
            delta = -1 if getattr(event, "delta", 0) > 0 else 1
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def _is_in_content(self, widget) -> bool:
        """事件源是否在内容区子树内（winfo_parent 返回控件名字符串，只能按名比对）。"""
        if widget is None:
            return False
        try:
            target = self.content.winfo_name()
            cur = widget
            for _ in range(64):
                if cur.winfo_name() == target:
                    return True
                parent = cur.winfo_parent()
                if not parent or parent == cur.winfo_name():
                    return False
                name = str(parent)
                if name == ".":
                    return False
                try:
                    cur = self.root.nametowidget(name)
                except (tk.TclError, KeyError):
                    return False
        except tk.TclError:
            return False
        return False

    @staticmethod
    def _widget_scrolls_itself(widget) -> bool:
        """Text 自身内容溢出时保留原生滚动（本项目的日志框）。"""
        try:
            if widget.winfo_class() != "Text":
                return False
            first, last = widget.yview()
            return not (float(first) <= 0.0 and float(last) >= 1.0)
        except (tk.TclError, ValueError, TypeError):
            return False

    # ---------- 页面切换 ----------
    def _nav_style(self, active: str) -> None:
        for k, btn in self.navs.items():
            if k == active:
                btn.config(bg=T.C_SECONDARY, fg=T.C_ACCENT,
                           font=(T.FONT_FAMILY, _NAV_FONT_SIZE, "bold"))
            else:
                btn.config(bg=T.C_PRIMARY, fg=T.C_TEXT_FADE,
                           font=(T.FONT_FAMILY, _NAV_FONT_SIZE))

    def show(self, key: str) -> None:
        # 切页时先把所有页面注册过的操作栏全部 hide，再 build/show 新页。
        # bug 根因：各页面的 bar master=app.content、再 pack(in_=action_host)，
        # action_host.winfo_children() 找不到这些 bar（master 不是 action_host），
        # 旧 clear_action_bar 实际清不掉；导致切到 about 这种没自己 bar 的页面时，
        # 上一页的「预览/开始执行」按钮残留（用户 2026-10-12 反馈）。
        self._hide_all_action_bars()
        if key not in self.pages and key in self._page_builders:
            self._page_builders[key]()
        self._nav_style(key)
        for p in self.pages.values():
            p.pack_forget()
        self.pages[key].pack(fill=tk.BOTH, expand=True)
        self.cur = key
        self._flush_pending_drop()
        # 切页后回到顶部并按新页重算滚动区（否则沿用旧页高度/滚动位置）
        try:
            self.canvas.yview_moveto(0)
        except tk.TclError:
            pass
        self._sync_canvas()

    def _hide_all_action_bars(self) -> None:
        # 把所有页面注册过的操作栏全部 pack_forget（不 destroy，保留 bar 供下次复用）。
        bars = getattr(self, "_action_bars", None) or {}
        for other in bars.values():
            try:
                other.pack_forget()
            except tk.TclError:
                pass
        try:
            self.action_host.pack_forget()
        except tk.TclError:
            pass

    def _page(self) -> tk.Frame:
        """页面根容器：统一外边距。"""
        return tk.Frame(self.page_host, bg=T.C_BG, padx=T.S_LG, pady=T.S_MD)

    def set_action_bar(self, widget: tk.Widget) -> None:
        """页面注册底部固定操作栏（在最外层 Frame，不随内容滚动）。"""
        self.clear_action_bar()
        widget.pack(in_=self.action_host, fill=tk.X, padx=T.S_LG, pady=(0, T.S_MD))

    def clear_action_bar(self) -> None:
        for child in list(self.action_host.winfo_children()):
            child.destroy()
        try:
            self.action_host.pack_forget()      # 无操作栏时不占位
        except tk.TclError:
            pass

    def _mount_action_bar(self) -> None:
        if self.action_host.winfo_children():
            self.action_host.pack(fill=tk.X, side=tk.BOTTOM)

    # ---------- 页面构建（延迟） ----------
    def _build_home(self) -> None:
        f = self._page()
        self.pages["home"] = f
        from rename_master.ui.pages.home import build
        build(f, self)
        self._mount_action_bar()

    def _build_photo(self) -> None:
        f = self._page()
        self.pages["photo"] = f
        from rename_master.ui.pages.photo import build
        build(f, self)
        self._mount_action_bar()

    def _build_pdf(self) -> None:
        f = self._page()
        self.pages["pdf"] = f
        from rename_master.ui.pages.pdf import build
        build(f, self)
        self._mount_action_bar()

    def _build_spreadsheet(self) -> None:
        f = self._page()
        self.pages["spreadsheet"] = f
        from rename_master.ui.pages.spreadsheet import build
        build(f, self)
        self._mount_action_bar()

    def _build_document(self) -> None:
        f = self._page()
        self.pages["document"] = f
        from rename_master.ui.pages.document import build
        build(f, self)
        self._mount_action_bar()

    def _build_about(self) -> None:
        f = self._page()
        self.pages["about"] = f
        from rename_master.ui.pages.about import build
        build(f, self)
        self._mount_action_bar()

    # ---------- 拖放（drag & drop）----------
    def _source_setter(self):
        """当前页面的 set_source_dir 方法；页面未 build 或不支持拖入则 None。"""
        page = self.pages.get(self.cur)
        return getattr(page, "set_source_dir", None) if page is not None else None

    def apply_drop_path(self, path: str) -> bool:
        """把拖入的源目录交给当前页面；页面还没 build 就先暂存，等切到该页再补。

        首页（home）/ 关于（about）没有源目录输入框，此时挂到 pending_drop_path，
        用户切到 photo / spreadsheet / document 时由 _flush_pending_drop 应用。
        返回 True 表示已当场填入，False 表示已暂存。
        """
        setter = self._source_setter()
        if setter is None:
            self.pending_drop_path = path
            self.set_status("已记住拖入目录，切到功能页自动填入")
            return False
        setter(path)
        return True

    def _flush_pending_drop(self) -> None:
        """切页后把暂存的拖入目录补发给已 build 完成的页面（用完即清）。"""
        path = self.pending_drop_path
        setter = self._source_setter()
        if not path or setter is None:
            return
        self.pending_drop_path = None
        setter(path)

    # ---------- 公共小工具 ----------
    def set_status(self, text: str, kind: str = "info") -> None:
        """状态栏文案 + 语义色（info=灰 / ok=绿 / err=红）。"""
        color = {"ok": T.C_SUCCESS, "err": T.C_DANGER,
                 "warn": T.C_WARNING}.get(kind, T.C_TEXT_FADE)
        self.status.set(text)
        self.status_label.config(fg=color)

    def safe_after(self, delay_ms: int, callback) -> Optional[str]:
        """从任意线程安全投递 UI 回调；窗口已销毁则静默丢弃。"""
        if self._closed:
            return None
        try:
            return self.root.after(delay_ms, callback)
        except (tk.TclError, RuntimeError):
            return None

    def _on_close(self) -> None:
        self._closed = True
        try:
            self.root.unbind_all("<MouseWheel>")
            self.root.destroy()
        except tk.TclError:
            pass
