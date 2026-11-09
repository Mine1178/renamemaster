"""关于页：品牌头 + 功能特性 / 技术栈两列 + 赞助弹窗。"""
from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, PageHeader, vlabel

FEATURES = [
    ("统一前缀 + 序号", "位数 / 起始值 / 分隔符 / 保留扩展名均可自定义"),
    ("Excel 对照表一一改名", "重名与非法字符自动校验标色"),
    ("图片自动压缩", "二分法调 JPEG 质量，压不到再等比缩分辨率"),
    ("拖拽支持", "拖文件夹进窗口自动填路径"),
    ("安全可追溯", "输出隔离 + 执行前预览 + 操作日志，绝不原地覆盖"),
]

STACK = [
    # 运行期实测版本，避免写死（打包用哪个解释器就显示哪个）
    f"Python {sys.version_info.major}.{sys.version_info.minor}"
    f".{sys.version_info.micro}",
    "tkinter（标准库）",
    "Pillow（图片）",
    "openpyxl（Excel）",
    "python-docx（Word）",
    "pypdf（PDF）",
    "tkinterdnd2（拖拽）",
]


def _resource_path(rel: str) -> Path:
    """PyInstaller 打包后资源在 _MEIPASS 下，开发时在项目根。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel  # type: ignore[attr-defined]
    # 开发态：about.py 在 src/rename_master/ui/pages/，上溯 4 级到项目根
    return Path(__file__).resolve().parents[4] / rel


def _feature_row(master: tk.Widget, title: str, desc: str) -> None:
    row = tk.Frame(master, bg=T.C_CARD)
    row.pack(fill=tk.X, pady=(T.S_XS, 0))
    vlabel(row, f"· {title}", font=(T.FONT_FAMILY, T.F_BODY, "bold"),
           bg=T.C_CARD, fg=T.C_TEXT, justify=tk.LEFT).pack(fill=tk.X)
    vlabel(row, f"    {desc}", font=(T.FONT_FAMILY, T.F_SM),
           bg=T.C_CARD, fg=T.C_TEXT_SUB, justify=tk.LEFT,
           wrap="word").pack(fill=tk.X, pady=(0, T.S_XS))


def _show_sponsor_dialog(parent: tk.Misc, anchor: tk.Widget | None = None) -> None:
    """弹赞助窗：文案 + 支付宝/微信收款码。窗口居中，支持一键放大。"""
    dlg = tk.Toplevel(parent)
    dlg.title("赞助作者")
    W, H = 1060, 880
    dlg.geometry(f"{W}x{H}")
    dlg.minsize(720, 560)
    dlg.resizable(True, True)
    dlg.transient(parent)
    dlg.grab_set()

    # 屏幕居中
    dlg.update_idletasks()
    sw = dlg.winfo_screenwidth()
    sh = dlg.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    dlg.geometry(f"+{x}+{y}")

    # 一键放大/还原
    state = {"zoomed": False, "normal_geom": f"{W}x{H}+{x}+{y}"}

    def _toggle_zoom():
        if state["zoomed"]:
            dlg.geometry(state["normal_geom"])
            zoom_btn.configure(text="⤢ 放大")
        else:
            state["normal_geom"] = dlg.geometry()
            dlg.state("zoomed")
            zoom_btn.configure(text="🗗 还原")
        state["zoomed"] = not state["zoomed"]

    vlabel(dlg, "☕", font=(T.FONT_FAMILY, 36),
           bg=T.C_BG, fg=T.C_ACCENT).pack(pady=(T.S_MD, 0))
    vlabel(dlg, "如果你喜欢这个工具",
           font=(T.FONT_FAMILY, T.F_SECTION + 4, "bold"),
           bg=T.C_BG, fg=T.C_TEXT).pack(pady=(T.S_XS, 0))
    vlabel(dlg, "可以请作者喝杯咖啡，感谢赞助",
           font=(T.FONT_FAMILY, T.F_BODY + 2),
           bg=T.C_BG, fg=T.C_TEXT_M).pack(pady=(0, T.S_MD))

    # 码图区：expand=True 占满剩余空间，两张大码居中并排
    codes = tk.Frame(dlg, bg=T.C_BG)
    codes.pack(pady=(0, T.S_MD), expand=True, fill=tk.BOTH, padx=T.S_LG)
    codes.grid_columnconfigure(0, weight=1)
    codes.grid_columnconfigure(1, weight=1)
    codes.grid_rowconfigure(0, weight=1)

    alipay = _resource_path("assets/alipay.jpg")
    wechat = _resource_path("assets/wechatpay.jpg")

    def _load_code(path: Path, label: str, brand: str, col: int) -> None:
        cell = tk.Frame(codes, bg=T.C_BG)
        cell.grid(row=0, column=col, sticky="nsew", padx=T.S_LG)
        if path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(path)
                # 大码图 480x480，LANCZOS 高质量
                img.thumbnail((480, 480), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(cell, image=photo, bg="#ffffff",
                               relief=tk.SOLID, bd=2)
                lbl.image = photo  # type: ignore[attr-defined]
                lbl.pack(expand=True)
            except Exception as e:
                vlabel(cell, f"[{label}加载失败: {e}]",
                       font=(T.FONT_FAMILY, T.F_SM),
                       bg=T.C_BG, fg=T.C_DANGER).pack()
        else:
            tk.Label(cell, text=f"[{label}\n待添加]",
                     font=(T.FONT_FAMILY, T.F_SM), width=16, height=12,
                     bg="#e2e8f0", fg=T.C_TEXT_L, relief=tk.SOLID, bd=1).pack()
        vlabel(cell, brand, font=(T.FONT_FAMILY, T.F_BODY + 2, "bold"),
               bg=T.C_BG, fg=T.C_TEXT).pack(pady=(T.S_SM, 0))

    _load_code(alipay, "支付宝", "📱 支付宝扫码", 0)
    _load_code(wechat, "微信", "💬 微信扫码", 1)

    btn_row = tk.Frame(dlg, bg=T.C_BG)
    btn_row.pack(pady=(0, T.S_MD))
    zoom_btn = tk.Button(btn_row, text="⤢ 放大", command=_toggle_zoom,
              font=(T.FONT_FAMILY, T.F_BODY),
              bg="#f1f5f9", fg=T.C_TEXT, relief=tk.SOLID, bd=1,
              activebackground="#e2e8f0", activeforeground=T.C_TEXT,
              padx=20, pady=6, cursor="hand2")
    zoom_btn.pack(side=tk.LEFT, padx=T.S_SM)
    tk.Button(btn_row, text="关闭", command=dlg.destroy,
              font=(T.FONT_FAMILY, T.F_BODY + 1),
              bg=T.C_PRIMARY, fg="#ffffff", relief=tk.FLAT, padx=32, pady=6
              ).pack(side=tk.LEFT, padx=T.S_SM)


def build(page: tk.Frame, app) -> None:
    PageHeader(page, "关于 重命名大师", f"版本 v{app.VERSION} · 本地运行，数据不出本机")

    head = tk.Frame(page, bg=T.C_BG)
    head.pack(fill=tk.X, pady=(T.S_MD, T.S_LG))
    vlabel(head, "◉", font=(T.FONT_FAMILY, T.F_HERO),
           bg=T.C_BG, fg=T.C_ACCENT, justify=tk.CENTER).pack(fill=tk.X)
    vlabel(head, f"重命名大师 v{app.VERSION}",
           font=(T.FONT_FAMILY, T.F_H1, "bold"),
           bg=T.C_BG, fg=T.C_TEXT, justify=tk.CENTER).pack(fill=tk.X,
                                                           pady=(T.S_SM, 0))
    vlabel(head, "文件批量命名助手", font=(T.FONT_FAMILY, T.F_SECTION),
           bg=T.C_BG, fg=T.C_TEXT_L, justify=tk.CENTER).pack(fill=tk.X,
                                                             pady=(T.S_XS, 0))

    cols = tk.Frame(page, bg=T.C_BG)
    cols.pack(fill=tk.X, pady=(0, T.S_MD))
    cols.grid_columnconfigure(0, weight=1, uniform="about_col")
    cols.grid_columnconfigure(1, weight=1, uniform="about_col")

    feat = Card(cols, "功能特性", accent=T.C_SUCCESS)
    feat.grid(row=0, column=0, sticky="nsew", padx=(0, T.S_SM))
    for title, desc in FEATURES:
        _feature_row(feat.body, title, desc)

    stack = Card(cols, "技术栈", accent=T.C_INFO)
    stack.grid(row=0, column=1, sticky="nsew", padx=(T.S_SM, 0))
    for item in STACK:
        vlabel(stack.body, f"· {item}", font=(T.FONT_FAMILY, T.F_BODY),
               bg=T.C_CARD, fg=T.C_TEXT_M).pack(fill=tk.X, pady=T.S_XS)

    # ---------- 赞助按钮（无边框，与页面底色融合，hover 微亮） ----------
    btn_row = tk.Frame(page, bg=T.C_BG)
    btn_row.pack(pady=(T.S_SM, 0))
    sponsor_btn = tk.Button(btn_row, text="☕ 赞助作者",
              font=(T.FONT_FAMILY, T.F_BODY),
              bg=T.C_BG, fg=T.C_TEXT_M,
              activebackground=T.C_HOVER, activeforeground=T.C_TEXT,
              relief=tk.FLAT, bd=0, highlightthickness=0,
              padx=T.S_LG, pady=T.S_XS, cursor="hand2")
    sponsor_btn.pack()
    sponsor_btn.bind("<Enter>", lambda e: sponsor_btn.config(bg=T.C_HOVER))
    sponsor_btn.bind("<Leave>", lambda e: sponsor_btn.config(bg=T.C_BG))
    sponsor_btn.configure(command=lambda: _show_sponsor_dialog(page, sponsor_btn))

    vlabel(page, "© 2026 · 本地工具，数据不出本机",
           font=(T.FONT_FAMILY, T.F_SM), bg=T.C_BG, fg=T.C_TEXT_L,
           justify=tk.CENTER).pack(fill=tk.X, pady=(T.S_MD, T.S_MD))
