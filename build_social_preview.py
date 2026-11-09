# -*- coding: utf-8 -*-
"""生成 GitHub Social preview 品牌图（1280x640），配色与 ui/theme.py 一致。

用法：python build_social_preview.py
输出：assets/social-preview.png

GitHub 社交预览推荐 1280x640（最小 640x320），上传到
仓库 Settings → Social preview。本图只做品牌排版 + 几何化界面示意，
不冒充真实软件截图。
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
C_PURPLE = "#7c3aed"

FONT_REG = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if path.exists():
        return ImageFont.truetype(str(path), size)
    # 非 Windows 回退（中文可能缺字，仅用于本地预览）
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
    d.text((72, 336), "还能管一份门店档案台账", font=_font(23),
           fill=C_TEXT_M)

    chips = [("批量改名", C_ACCENT), ("图片压缩", C_INFO),
             ("门店台账", C_SUCCESS), ("纯本地", C_SECONDARY)]
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

    d.text((72, 566), "v1.11.0  ·  输出隔离 · 可撤销  ·  数据不出本机",
           font=_font(19), fill=C_TEXT_L)

    # ---------------- 右侧界面示意 ----------------
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
    tw = _text_w(d, "重命名大师 v1.11.0", tf)
    d.text((wx + ww - tw - 18, wy + 10), "重命名大师 v1.11.0",
           font=tf, fill=C_TEXT_FADE)

    # 左侧导航
    sy = wy + 38
    sw = 120
    d.rectangle([wx + 2, sy, wx + sw, wy + wh - 2], fill=C_PRIMARY)
    d.ellipse([wx + 50, sy + 16, wx + 68, sy + 34], outline=C_ACCENT, width=3)
    lf = _font(12, True)
    lw = _text_w(d, "重命名大师", lf)
    d.text((wx + (sw - lw) // 2, sy + 42), "重命名大师", font=lf,
           fill=C_ACCENT)

    nav = ["首页", "照片命名", "PDF 命名", "表格命名",
           "文档命名", "门店管理", "赞助", "帮助", "关于"]
    nf = _font(13)
    for i, label in enumerate(nav):
        y0 = sy + 82 + i * 43
        active = i == 5
        if active:
            d.rounded_rectangle([wx + 8, y0, wx + sw - 6, y0 + 36],
                                radius=5, fill=C_SECONDARY)
        d.rounded_rectangle([wx + 16, y0 + 14, wx + 23, y0 + 21],
                            radius=2, fill=C_ACCENT if active else C_TEXT_FADE)
        d.text((wx + 30, y0 + 9), label, font=nf,
               fill=C_CARD if active else C_TEXT_FADE)

    # 内容区
    cx = wx + sw + 20
    cw = wx + ww - cx - 20
    d.text((cx, sy + 20), "门店管理", font=_font(23, True), fill=C_TEXT)
    d.text((cx, sy + 54), "维护门店档案 · 支持 Excel 批量导入 / 导出",
           font=_font(13), fill=C_TEXT_L)
    d.rectangle([cx, sy + 82, cx + cw, sy + 84], fill=C_ACCENT)

    # 工具栏
    tools = [("＋ 新增门店", C_ACCENT), ("导入 Excel", C_CARD),
             ("导出 Excel", C_CARD)]
    tx = cx
    for label, bg in tools:
        bf = _font(12, True)
        bw = _text_w(d, label, bf) + 24
        d.rounded_rectangle([tx, sy + 98, tx + bw, sy + 128], radius=5,
                            fill=bg, outline=C_BORDER if bg == C_CARD else bg,
                            width=1)
        d.text((tx + 12, sy + 105), label, font=bf,
               fill=C_CARD if bg == C_ACCENT else C_TEXT_M)
        tx += bw + 8

    # 表格
    ty = sy + 146
    th = 236
    d.rectangle([cx, ty, cx + cw, ty + th], fill=C_CARD,
                outline=C_BORDER, width=1)
    d.rectangle([cx + 1, ty + 1, cx + cw - 1, ty + 30], fill=C_PRIMARY)
    heads = ["门店编号", "门店名称", "城市", "负责人", "电话"]
    col_x = [cx + 12, cx + 92, cx + 212, cx + 288, cx + 366]
    hf = _font(12, True)
    for hx, h in zip(col_x, heads):
        d.text((hx, ty + 8), h, font=hf, fill=C_CARD)

    rows = [
        ("S001", "旗舰店", "昆明", "张三", "138****0001"),
        ("S002", "人民路分店", "曲靖", "李四", "139****0002"),
        ("S003", "开发区店", "昆明", "王五", "137****0003"),
        ("S004", "高铁站店", "大理", "赵六", "136****0004"),
    ]
    rf = _font(12)
    for i, row in enumerate(rows):
        ry = ty + 30 + i * 42
        if i % 2 == 1:
            d.rectangle([cx + 1, ry, cx + cw - 1, ry + 42], fill=C_ROW_ALT)
        d.rectangle([cx + 1, ry + 41, cx + cw - 1, ry + 42], fill=C_BORDER)
        for hx, val in zip(col_x, row):
            d.text((hx, ry + 12), val, font=rf, fill=C_TEXT_M)

    # 右下角强调小卡
    d.rounded_rectangle([cx + cw - 128, ty + th + 12, cx + cw, ty + th + 60],
                        radius=6, fill=C_CARD, outline=C_BORDER, width=1)
    d.text((cx + cw - 116, ty + th + 22), "数据存于本机",
           font=_font(12, True), fill=C_SUCCESS)

    d.rectangle([0, H - 6, W, H], fill=C_ACCENT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"saved: {OUT} ({OUT.stat().st_size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
