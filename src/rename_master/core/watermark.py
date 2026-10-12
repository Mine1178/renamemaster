"""照片水印：在图片上叠半透明白色文字（压缩之后的最后一步 transform）。

规格：
- 白色文字，透明度 40%（RGBA 255,255,255,102）；
- 字号 = 短边 × font_size_ratio（默认 0.02，即短边 1000px → 20px）；
- 距边缘边距 = 字号；
- position: bottom_right / bottom_left / top_right / top_left / bottom_center；
- text 为空 → 原样返回字节流（不加水印）；
- 输出 JPEG（quality=95）。

全程在内存 BytesIO 里完成，不落盘、不改原图。
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

ALPHA = 102                     # 40% 不透明度（255 * 0.4）
TEXT_FILL = (255, 255, 255, ALPHA)
QUALITY = 95

# 优先系统微软雅黑；ttc 索引 0 即 msyh 常规体
FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyh.ttf",
    "C:/Windows/Fonts/msyhl.ttc",
)

POSITIONS = ("bottom_right", "bottom_left", "top_right", "top_left",
             "bottom_center")
DEFAULT_POSITION = "bottom_right"


def _load_font(size: int):
    """依次尝试系统微软雅黑，都找不到就用 PIL 默认字体。"""
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:                       # noqa: BLE001 字体缺失属正常降级
            continue
    logger.debug("未找到微软雅黑，回退默认字体")
    return ImageFont.load_default()


def _anchor(img_w: int, img_h: int, text_w: int, text_h: int,
            margin: int, position: str) -> tuple:
    """按 position 算左上角落点（水平 right/left/center × 垂直 top/bottom）。"""
    y = img_h - text_h - margin if position.startswith("bottom") else margin
    if position.endswith("right"):
        x = img_w - text_w - margin
    elif position.endswith("left"):
        x = margin
    else:                                       # bottom_center：水平居中
        x = (img_w - text_w) / 2
    return max(0, int(x)), max(0, int(y))


def add_watermark(img_bytes: bytes, text: str, position: str = DEFAULT_POSITION,
                  font_size_ratio: float = 0.02) -> bytes:
    """在图片上画半透明白色文字水印，返回 JPEG 字节流。

    text 为空 / 纯空白 → 直接返回原字节流。
    """
    from PIL import Image, ImageDraw

    if not text or not str(text).strip():
        return img_bytes
    if position not in POSITIONS:
        logger.warning("未知水印位置 %r，回退 %s", position, DEFAULT_POSITION)
        position = DEFAULT_POSITION

    with Image.open(io.BytesIO(img_bytes)) as img:
        # 透明图先合成到白底，避免转 JPEG 后透明区变黑
        rgba = Image.alpha_composite(
            Image.new("RGBA", img.size, (255, 255, 255, 255)), img.convert("RGBA"))
        width, height = rgba.size
        font_size = max(1, int(min(width, height) * float(font_size_ratio)))
        margin = font_size
        font = _load_font(font_size)

        overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        box = draw.textbbox((0, 0), str(text), font=font)
        text_w, text_h = box[2] - box[0], box[3] - box[1]
        x, y = _anchor(width, height, text_w, text_h, margin, position)
        draw.text((x, y - box[1]), str(text), font=font, fill=TEXT_FILL)

        out = Image.alpha_composite(rgba, overlay).convert("RGB")
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=QUALITY)
        return buf.getvalue()


if __name__ == "__main__":
    """自测：造一张测试图 → 加「测试水印」→ 保存 /tmp/test_wm.jpg。"""
    import tempfile
    from pathlib import Path

    from PIL import Image

    test = Image.linear_gradient("L").resize((1200, 900)).convert("RGB")
    raw = io.BytesIO()
    test.save(raw, format="JPEG", quality=95)
    src_bytes = raw.getvalue()

    out_bytes = add_watermark(src_bytes, "测试水印")
    assert out_bytes and out_bytes != src_bytes, "水印未生效"

    out_path = Path("/tmp/test_wm.jpg")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:                             # Windows 无 /tmp 权限时退回系统临时目录
        out_path = Path(tempfile.gettempdir()) / "test_wm.jpg"
    out_path.write_bytes(out_bytes)
    print(f"水印自测通过：{len(src_bytes)} → {len(out_bytes)} 字节 → {out_path}")

    assert add_watermark(src_bytes, "") == src_bytes, "空文字不应改变图像"
    for pos in POSITIONS:
        assert add_watermark(src_bytes, "测试水印", position=pos), pos
    print(f"空文字原样返回 + 5 种位置均正常 → {POSITIONS}")
