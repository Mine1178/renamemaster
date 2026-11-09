"""赞助页共享组件：收款码资源定位 + 双码内联布局 + 点击放大。

about 页与独立赞助页共用，避免两套加载逻辑。
"""
from __future__ import annotations

import sys
from pathlib import Path

import tkinter as tk

from rename_master.ui import theme as T
from rename_master.ui.widgets import vlabel


def resource_path(rel: str) -> Path:
    """定位 assets 下的资源（开发态向上找到项目根，打包态在 _MEIPASS）。"""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        return base / rel
    p = Path(__file__).resolve()
    for cand in (p, *p.parents):
        if (cand / rel).exists():
            return cand / rel
    # 兜底：本文件在 src/rename_master/ui/，项目根为 parents[2]
    return p.parents[2] / rel


def _zoom(parent: tk.Misc, img_path: Path, brand: str) -> None:
    """放大查看收款码（自适应屏幕、可缩放、点击关闭）。"""
    dlg = tk.Toplevel(parent)
    dlg.title(brand)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.configure(bg=T.C_BG)
    try:
        from PIL import Image, ImageTk
        img = Image.open(img_path)
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        max_w = int(sw * 0.8)
        max_h = int(sh * 0.8)
        scale = min(max_w / img.width, max_h / img.height, 1.0)
        disp = img.resize((int(img.width * scale), int(img.height * scale)),
                          Image.LANCZOS)
        photo = ImageTk.PhotoImage(disp)
        lbl = tk.Label(dlg, image=photo, bg=T.C_WHITE, relief=tk.SOLID, bd=2)
        lbl.image = photo  # type: ignore[attr-defined]
        lbl.pack(padx=T.S_LG, pady=T.S_LG)
        lbl.bind("<Button-1>", lambda e: dlg.destroy())
        vlabel(dlg, "点击图片关闭", font=(T.FONT_FAMILY, T.F_SM),
               bg=T.C_BG, fg=T.C_TEXT_L).pack(pady=(0, T.S_MD))
        dlg.update_idletasks()
        w, h = dlg.winfo_width(), dlg.winfo_height()
        dlg.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
    except Exception as e:  # noqa: BLE001
        tk.Label(dlg, text=f"加载失败：{e}", bg=T.C_BG, fg=T.C_DANGER
                 ).pack(padx=T.S_LG, pady=T.S_LG)


def show_sponsor_codes(parent: tk.Widget, big: bool = True) -> None:
    """在 parent 内布局支付宝 / 微信两张收款码（并排、可点击放大）。"""
    codes = tk.Frame(parent, bg=T.C_BG)
    codes.pack(expand=True, fill=tk.BOTH, padx=T.S_LG, pady=T.S_MD)
    codes.grid_columnconfigure(0, weight=1)
    codes.grid_columnconfigure(1, weight=1)
    codes.grid_rowconfigure(0, weight=1)

    alipay = resource_path("assets/alipay.jpg")
    wechat = resource_path("assets/wechatpay.jpg")
    size = 360 if big else 240

    def _cell(col: int, path: Path, brand: str) -> None:
        cell = tk.Frame(codes, bg=T.C_BG)
        cell.grid(row=0, column=col, sticky="nsew", padx=T.S_LG)
        if path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(path)
                img.thumbnail((size, size), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(cell, image=photo, bg=T.C_WHITE,
                               relief=tk.SOLID, bd=2, cursor="hand2")
                lbl.image = photo  # type: ignore[attr-defined]
                lbl.pack(expand=True)
                lbl.bind("<Button-1>", lambda e: _zoom(cell, path, brand))
            except Exception as e:  # noqa: BLE001
                vlabel(cell, f"[{brand}加载失败: {e}]", font=(T.FONT_FAMILY, T.F_SM),
                       bg=T.C_BG, fg=T.C_DANGER).pack()
        else:
            tk.Label(cell, text=f"[{brand}\n待添加]", font=(T.FONT_FAMILY, T.F_SM),
                     width=16, height=12, bg=T.C_BORDER, fg=T.C_TEXT_L,
                     relief=tk.SOLID, bd=1).pack()
        vlabel(cell, brand, font=(T.FONT_FAMILY, T.F_LEAD, "bold"),
               bg=T.C_BG, fg=T.C_TEXT).pack(pady=(T.S_SM, 0))

    _cell(0, alipay, "📱 支付宝扫码")
    _cell(1, wechat, "💬 微信扫码")
