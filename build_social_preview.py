# -*- coding: utf-8 -*-
"""生成 GitHub Social preview 品牌图（1280x640），配色与 ui/theme.py 一致。

用法：python build_social_preview.py
输出：assets/social-preview.png

GitHub 社交预览推荐 1280x640（最小 640x320），上传到
仓库 Settings → Social preview。本图只做品牌排版 + 几何化界面示意，
不冒充真实软件截图；界面示意按 v1.10.2 实际功能绘制（6 项导航 / 4 张卡）。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "social-preview.png"

W, H = 1280, 640
C_BG = "#f1f5f9"
C_PRIMARY = "#1e293b"
C_SECONDARY = "#334155"
C_ACCENT = "#d97706"
C_CARD = "#ffffff"
C_TEXT = "#0f172a"
C_TEXT_M = "#475569"
C_TEXT_L = "#64748b"
C_TEXT_FADE = "#94a3b8"
C_BORDER = "#e2e8f0"
C_ROW_ALT = "#f8fafc"
C_SUCCESS = "#16a34a"
C_INFO = "#2563eb"

FONT_REG = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def main() -> None:
    img = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(img)

    # ---------------- 左侧品牌区 ----------------
    d.rounded_rectangle([70, 86, 126, 94], radius=3, fill=C_ACCENT)
    d.text((70, 116), "重命名大师", font=_font(62, True), fill=C_TEXT)
    d.text((73, 198), "RenameMaster  ·  文件批量命名助手",
           font=_font(23), fill=C_TEXT_M)

    d.text((72, 258), "照片 / PDF / 表格 / 文档", font=_font(27, True),
           fill=C_PRIMARY)
    d.text((72, 298), "一键规范改名，顺带压缩图片", font=_font(23),
           fill=C_TEXT_M)
    d.text((72, 336), "执行前预览 · 绝不原地覆盖", font=_font(23),
           fill=C_TEXT_M)

    chips = [("批量改名", C_ACCENT), ("图片压缩", C_INFO),
             ("预览核对", C_SUCCESS), ("纯本地", C_SECONDARY)]
    x = 72
    for label, color in chips:
        f = _font(19, True)
        tw = _text_w(d, label, f)
        cw = tw + 34
        d.rounded_rectangle([x, 392, x + cw, 438], radius=22,
                            fill=C_CARD, outline=C_BORDER, width=2)
        d.rounded_rectangle([x, 392, x + 6, 438], radius=3, fill=color)
        d.text((x + 18, 401), label, font=f, fill=color)
        x += cw + 12

    d.text((72, 566), "v1.10.2  ·  输出隔离 · 可撤销  ·  数据不出本机",
           font=_font(19), fill=C_TEXT_L)

    # ---------------- 右侧界面示意（v1.10.2 首页） ----------------
    wx, wy, ww, wh = 648, 66, 566, 508
    d.rounded_rectangle([wx, wy, wx + ww, wy + wh], radius=14,
                        fill=C_CARD, outline=C_BORDER, width=2)

    # 标题栏
    d.rounded_rectangle([wx + 2, wy + 2, wx + ww - 2, wy + 38], radius=12,
                        fill=C_ROW_ALT)
    d.rectangle([wx + 2, wy + 26, wx + ww - 2, wy + 38], fill=C_ROW_ALT)
    for i, c in enumerate(("#ef4444", "#f59e0b", "#22c55e")):
        d.ellipse([wx + 18 + i * 20, wy + 14, wx + 28 + i * 20, wy + 24], fill=c)
    tf = _font(13)
    title = "重命名大师 v1.10.2"
    tw = _text_w(d, title, tf)
    d.text((wx + ww - tw - 18, wy + 10), title, font=tf, fill=C_TEXT_FADE)

    # 左侧导航（6 项，与 app.py NAV_ITEMS 一致）
    sy = wy + 38
    sw = 120
    d.rectangle([wx + 2, sy, wx + sw, wy + wh - 2], fill=C_PRIMARY)
    d.ellipse([wx + 50, sy + 16, wx + 68, sy + 34], outline=C_ACCENT, width=3)
    lf = _font(12, True)
    lw = _text_w(d, "重命名大师", lf)
    d.text((wx + (sw - lw) // 2, sy + 42), "重命名大师", font=lf,
           fill=C_ACCENT)

    nav = ["首页", "照片命名", "PDF 命名", "表格命名", "文档命名", "关于"]
    nf = _font(13)
    for i, label in enumerate(nav):
        y0 = sy + 82 + i * 43
        active = i == 0
        if active:
            d.rounded_rectangle([wx + 8, y0, wx + sw - 6, y0 + 36],
                                radius=5, fill=C_SECONDARY)
        d.rounded_rectangle([wx + 16, y0 + 14, wx + 23, y0 + 21],
                            radius=2, fill=C_ACCENT if active else C_TEXT_FADE)
        d.text((wx + 30, y0 + 9), label, font=nf,
               fill=C_CARD if active else C_TEXT_FADE)

    # 内容区：首页标题 + 4 张功能卡（2x2）
    cx = wx + sw + 20
    cw = wx + ww - cx - 20
    d.text((cx, sy + 20), "首页", font=_font(23, True), fill=C_TEXT)
    d.text((cx, sy + 54), "文件批量命名助手 · 选一个功能开始",
           font=_font(13), fill=C_TEXT_L)
    d.rectangle([cx, sy + 82, cx + cw, sy + 84], fill=C_ACCENT)

    cards = [
        ("照片命名", "前缀+序号 / Excel 对照表", C_ACCENT),
        ("PDF 命名", "取正文开头自动取名", C_INFO),
        ("表格命名", "xlsx / xls / csv 规范", C_SUCCESS),
        ("文档命名", "Word / PDF / TXT 取名", C_SECONDARY),
    ]
    gap = 12
    card_w = (cw - gap) // 2
    card_h = 132
    top = sy + 104
    for i, (name, desc, color) in enumerate(cards):
        r, c = divmod(i, 2)
        x0 = cx + c * (card_w + gap)
        y0 = top + r * (card_h + gap)
        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=8,
                            fill=C_CARD, outline=C_BORDER, width=2)
        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + 5], radius=2, fill=color)
        d.rounded_rectangle([x0 + 18, y0 + 22, x0 + 42, y0 + 46],
                            radius=6, fill=color)
        d.text((x0 + 18, y0 + 58), name, font=_font(17, True), fill=C_TEXT)
        d.text((x0 + 18, y0 + 88), desc, font=_font(12), fill=C_TEXT_M)
        d.text((x0 + 18, y0 + 110), "进入 →", font=_font(12, True),
               fill=color)

    d.rectangle([0, H - 6, W, H], fill=C_ACCENT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"saved: {OUT} ({OUT.stat().st_size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
