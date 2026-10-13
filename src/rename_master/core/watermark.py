"""照片水印引擎：在图片上叠半透明文字 / LOGO（压缩之后的最后一步 transform）。

文字水印 add_watermark() 规格：
- color: white / black / yellow / red / cyan，默认 white；
- opacity: 0~1，默认 0.4（alpha = 255 × 0.4 = 102，旧版 ALPHA）；
- 字号 = 短边 × font_size_ratio（默认 0.02，即短边 1000px → 20px）；
- 距边缘边距 = 字号；
- text 含 \\n → 逐行绘制，行距 = 字号 × 0.4，多行整体按 position 对齐，
  行内再按 position 的水平分量（left/right/center）二次对齐；
- position 共 9 个：bottom_right / bottom_left / top_right / top_left /
  bottom_center / top_center / center_left / center_right / center；
- text 为空 → 原样返回字节流（不加水印）；
- 输出 JPEG（quality=95）。

LOGO 水印 add_logo_watermark()：指定角落贴一张等比缩放小图（宽 = 短边 ×
logo_ratio），支持 PNG 透明底。

模板 render_template()：内置 operator / survey / general 三套常用文案。

全程在内存 BytesIO 里完成，不落盘、不改原图。
"""
from __future__ import annotations

import io
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

DEFAULT_OPACITY = 0.4
ALPHA = int(255 * DEFAULT_OPACITY)          # 40% 不透明度（255 * 0.4）= 102
TEXT_FILL = (255, 255, 255, ALPHA)          # 旧默认白色填充，保留兼容
QUALITY = 95
LINE_GAP_RATIO = 0.4                        # 行距 = 字号 × 0.4

# 水印文字颜色（RGB 三通道，alpha 由 opacity 决定）
COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "yellow": (255, 255, 0),
    "red": (255, 0, 0),
    "cyan": (0, 255, 255),
}
DEFAULT_COLOR = "white"

# 内置文案模板
TEMPLATES = {
    "operator": "中国移动巡检\n{date}\n{location}",
    "survey": "现场勘查\n{date}\n{location}",
    "general": "{text}",
}
DEFAULT_TEMPLATE = "general"

# 优先系统微软雅黑；ttc 索引 0 即 msyh 常规体
FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyh.ttf",
    "C:/Windows/Fonts/msyhl.ttc",
)

POSITIONS = ("bottom_right", "bottom_left", "top_right", "top_left",
             "bottom_center", "top_center", "center_left", "center_right",
             "center")
DEFAULT_POSITION = "bottom_right"
DEFAULT_LOGO_POSITION = "top_right"


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


def _fill(color: str, opacity: float) -> tuple:
    """颜色名 + 不透明度 → RGBA 填充色；非法值回退默认白 / 0.4。"""
    key = str(color).lower()
    rgb = COLORS.get(key)
    if rgb is None:
        logger.warning("未知水印颜色 %r，回退 %s", color, DEFAULT_COLOR)
        rgb = COLORS[DEFAULT_COLOR]
    try:
        ratio = min(1.0, max(0.0, float(opacity)))
    except (TypeError, ValueError):             # noqa: BLE001 脏输入按默认处理
        logger.warning("非法不透明度 %r，回退 %s", opacity, DEFAULT_OPACITY)
        ratio = DEFAULT_OPACITY
    return (*rgb, int(round(255 * ratio)))


def _parse_color(color) -> tuple:
    """颜色名 / #RRGGBB / (r,g,b) → RGB；非法值回退默认白。"""
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return tuple(int(c) for c in color[:3])
    key = str(color).strip().lstrip("#")
    if str(color).lower() in COLORS:
        return COLORS[str(color).lower()]
    if len(key) == 6:
        try:
            return tuple(int(key[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    logger.warning("无法解析水印颜色 %r，回退 %s", color, DEFAULT_COLOR)
    return COLORS[DEFAULT_COLOR]


def _with_alpha(rgb: tuple, opacity: float) -> tuple:
    """RGB + 不透明度 → RGBA（兼容旧 _fill 的范围校验）。"""
    try:
        ratio = min(1.0, max(0.0, float(opacity)))
    except (TypeError, ValueError):
        logger.warning("非法不透明度 %r，回退 %s", opacity, DEFAULT_OPACITY)
        ratio = DEFAULT_OPACITY
    return (*rgb, int(round(255 * ratio)))


def _h_align(position: str) -> str:
    """position 的水平分量：left / right / center。"""
    if position.endswith("left"):
        return "left"
    if position.endswith("right"):
        return "right"
    return "center"


def _anchor(img_w: int, img_h: int, text_w: int, text_h: int,
            margin: int, position: str) -> tuple:
    """按 position 算左上角落点（水平 left/right/center × 垂直 top/bottom/center）。"""
    if position.startswith("top"):
        y = margin
    elif position.startswith("bottom"):
        y = img_h - text_h - margin
    else:                                       # center / center_left / center_right
        y = (img_h - text_h) / 2
    h = _h_align(position)
    if h == "left":
        x = margin
    elif h == "right":
        x = img_w - text_w - margin
    else:
        x = (img_w - text_w) / 2
    return max(0, int(x)), max(0, int(y))


def _base_rgba(img_bytes: bytes):
    """字节流 → 白底 RGBA 底图（透明图先合成白底，避免转 JPEG 后透明区变黑）。"""
    from PIL import Image

    with Image.open(io.BytesIO(img_bytes)) as img:
        return Image.alpha_composite(
            Image.new("RGBA", img.size, (255, 255, 255, 255)), img.convert("RGBA"))


def _to_jpeg(rgba) -> bytes:
    """RGBA → JPEG 字节流。"""
    buf = io.BytesIO()
    rgba.convert("RGB").save(buf, format="JPEG", quality=QUALITY)
    return buf.getvalue()


def add_watermark(img_bytes: bytes, text: str, position: str = DEFAULT_POSITION,
                  font_size_ratio: float = 0.02, color: str = DEFAULT_COLOR,
                  opacity: float = DEFAULT_OPACITY) -> bytes:
    """在图片上画半透明文字水印，返回 JPEG 字节流。

    text 含 \\n 时按行绘制；text 为空 / 纯空白 → 直接返回原字节流。
    """
    from PIL import Image, ImageDraw

    if not text or not str(text).strip():
        return img_bytes
    if position not in POSITIONS:
        logger.warning("未知水印位置 %r，回退 %s", position, DEFAULT_POSITION)
        position = DEFAULT_POSITION

    rgba = _base_rgba(img_bytes)
    width, height = rgba.size
    font_size = max(1, int(min(width, height) * float(font_size_ratio)))
    margin = font_size
    gap = max(0, int(font_size * LINE_GAP_RATIO))
    font = _load_font(font_size)
    fill = _with_alpha(_parse_color(color), opacity)

    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 每行单独量一次 bbox；空行按一个字号计高，避免塌成 0
    lines = str(text).split("\n")
    boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    widths = [max(0, box[2] - box[0]) for box in boxes]
    heights = [max(0, box[3] - box[1]) or font_size for box in boxes]
    block_w = max(widths)
    block_h = sum(heights) + gap * (len(lines) - 1)

    x, y = _anchor(width, height, block_w, block_h, margin, position)
    h_align = _h_align(position)

    cursor = y
    for line, box, line_w, line_h in zip(lines, boxes, widths, heights):
        if h_align == "left":
            line_x = x
        elif h_align == "right":
            line_x = x + block_w - line_w
        else:
            line_x = x + (block_w - line_w) / 2
        draw.text((line_x, cursor - box[1]), line, font=font, fill=fill)
        cursor += line_h + gap


    return _to_jpeg(Image.alpha_composite(rgba, overlay))


def add_logo_watermark(img_bytes: bytes, logo_path, position: str = DEFAULT_LOGO_POSITION,
                       logo_ratio: float = 0.08) -> bytes:
    """在指定角落贴一张等比缩放的 LOGO，返回 JPEG 字节流。

    宽度 = 图片短边 × logo_ratio，高度按比例缩放；PNG 透明底会被保留。
    LOGO 打不开 → 记日志并返回原字节流。
    """
    from PIL import Image

    if position not in POSITIONS:
        logger.warning("未知 LOGO 位置 %r，回退 %s", position, DEFAULT_LOGO_POSITION)
        position = DEFAULT_LOGO_POSITION

    try:
        with Image.open(logo_path) as logo:
            logo = logo.convert("RGBA")
    except Exception:                           # noqa: BLE001 路径失效属正常降级
        logger.warning("LOGO 打开失败，跳过水印：%s", logo_path)
        return img_bytes

    rgba = _base_rgba(img_bytes)
    width, height = rgba.size
    logo_w, logo_h = logo.size
    if logo_w <= 0 or logo_h <= 0:
        return img_bytes

    target_w = max(1, int(min(width, height) * float(logo_ratio)))
    target_h = max(1, round(target_w * logo_h / logo_w))
    logo = logo.resize((target_w, target_h), Image.LANCZOS)
    margin = max(2, target_w // 2)
    x, y = _anchor(width, height, target_w, target_h, margin, position)

    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    overlay.paste(logo, (x, y), logo)           # 第 3 个参数即 alpha 蒙版
    return _to_jpeg(Image.alpha_composite(rgba, overlay))


def add_tile_watermark(img_bytes: bytes, text: str, angle: float = 30,
                       font_size_ratio: float = 0.02, color="white",
                       opacity: float = 0.3, spacing: float = 1.0,
                       stroke: int = 0, shadow: bool = False) -> bytes:
    """斜向平铺旋转文字水印：铺满全图，裁掉一块仍有残留（防盗核心）。

    angle：旋转角度（默认 30°）；spacing：水印间距倍数（小=密，大=疏）；
    stroke：非 0 时给文字加深色描边；shadow：投影，复杂背景上更清晰。
    """
    from PIL import Image, ImageDraw

    if not text or not str(text).strip():
        return img_bytes

    rgba = _base_rgba(img_bytes)
    width, height = rgba.size
    font_size = max(1, int(min(width, height) * float(font_size_ratio)))
    font = _load_font(font_size)
    fill = _with_alpha(_parse_color(color), opacity)

    # 工作画布边长取对角线 + 余量：旋转后中心 W×H 必被覆盖，不留空角
    diag = int((width ** 2 + height ** 2) ** 0.5) + font_size * 4
    tile = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    bbox = td.textbbox((0, 0), str(text), font=font)
    tw = max(1, bbox[2] - bbox[0])
    th = max(1, bbox[3] - bbox[1])
    sx = int((tw + font_size * 2) * float(spacing))
    sy = int((th + font_size * 3) * float(spacing))
    stroke_w = max(1, int(font_size * 0.07)) if stroke else 0
    stroke_fill = (0, 0, 0, min(255, fill[3] + 90)) if stroke else None

    for row, y in enumerate(range(-diag, diag * 2, sy)):
        offset = sx // 2 if row % 2 else 0          # 奇偶行交错，更难裁
        for x in range(-diag, diag * 2, sx):
            if shadow:
                td.text((x - offset + 2, y - bbox[1] + 2), str(text),
                        font=font, fill=(0, 0, 0, fill[3] // 2))
            td.text((x - offset, y - bbox[1]), str(text), font=font,
                    fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)

    rot = tile.rotate(angle, resample=Image.BICUBIC, expand=False)
    left, top = (diag - width) // 2, (diag - height) // 2
    overlay = rot.crop((left, top, left + width, top + height))
    return _to_jpeg(Image.alpha_composite(rgba, overlay))


def apply_watermark(img_bytes: bytes, *, text: str = "", layout: str = "single",
                    position: str = "bottom_right", angle: float = 30,
                    font_size_ratio: float = 0.02, color="white",
                    opacity: float = 0.4, spacing: float = 1.0,
                    stroke: int = 0, shadow: bool = False,
                    logo_path: str = "", logo_position: str = "top_left",
                    logo_ratio: float = 0.08) -> bytes:
    """统一水印入口（新页面调用）。

    layout：single=按 position 角落单处；tile=斜向平铺（angle/spacing）。
    文字与 LOGO 可叠加；无任何水印内容时原样返回。
    """
    data = img_bytes
    if text and str(text).strip():
        if layout == "tile":
            data = add_tile_watermark(
                data, text, angle=angle, font_size_ratio=font_size_ratio,
                color=color, opacity=opacity, spacing=spacing,
                stroke=stroke, shadow=shadow)
        else:
            data = add_watermark(
                data, text, position=position,
                font_size_ratio=font_size_ratio, color=color, opacity=opacity)
    if logo_path and str(logo_path).strip():
        data = add_logo_watermark(data, logo_path, position=logo_position,
                                  logo_ratio=logo_ratio)
    return data


def render_template(template_name: str, **kwargs) -> str:
    """渲染内置水印文案；缺字段填空串，未知模板回退 general。

    operator → 中国移动巡检\\n{date}\\n{location}
    survey   → 现场勘查\\n{date}\\n{location}
    general  → {text}
    """
    tpl = TEMPLATES.get(str(template_name).lower())
    if tpl is None:
        logger.warning("未知水印模板 %r，回退 %s", template_name, DEFAULT_TEMPLATE)
        tpl = TEMPLATES[DEFAULT_TEMPLATE]
    return tpl.format_map(defaultdict(str, kwargs))


if __name__ == "__main__":
    """自测：默认白字 / 多行 / 黄色 center / 9 位置 / 颜色与透明度 / LOGO 叠加。"""
    import tempfile
    from pathlib import Path

    from PIL import Image, ImageDraw

    out_dir = Path(tempfile.gettempdir()) / "rename_wm_selftest"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ① 底图：渐变图 + 纯黑图（纯黑便于断言颜色真的画上去了）
    src = Image.linear_gradient("L").resize((1200, 900)).convert("RGB")
    raw = io.BytesIO()
    src.save(raw, format="JPEG", quality=95)
    src_bytes = raw.getvalue()

    black = io.BytesIO()
    Image.new("RGB", (800, 600), (0, 0, 0)).save(black, format="JPEG", quality=95)
    black_bytes = black.getvalue()

    # ② 向后兼容：旧签名（仅 position + font_size_ratio）→ 默认白色 40%
    out = add_watermark(src_bytes, "测试水印")
    assert out and out != src_bytes, "水印未生效"
    (out_dir / "wm_default.jpg").write_bytes(out)
    assert add_watermark(src_bytes, "") == src_bytes, "空文字不应改变图像"
    assert add_watermark(src_bytes, "   ") == src_bytes, "纯空白不应改变图像"

    # ③ 9 个位置
    for pos in POSITIONS:
        assert add_watermark(src_bytes, "测试水印", position=pos), pos
    assert len(POSITIONS) == 9, POSITIONS
    assert add_watermark(src_bytes, "测试水印", position="nowhere"), "未知位置应回退"

    def _any_pixel(jpeg: bytes, hit) -> bool:
        """JPEG 字节流里是否存在满足 hit(r, g, b) 的像素。"""
        img = Image.open(io.BytesIO(jpeg)).convert("RGB")
        for count, rgb in img.getcolors(maxcolors=img.width * img.height) or ():
            if count and hit(*rgb):
                return True
        return False

    # ④ 颜色 + 透明度：黑底画黄色满不透明 → 必须出现黄色像素
    yellow = add_watermark(black_bytes, "中国移动巡检\n2026-10-13\n曲靖",
                           position="center", color="yellow", opacity=1.0,
                           font_size_ratio=0.06)
    assert _any_pixel(yellow, lambda r, g, b: r > 150 and g > 150 and b < 120), \
        "黄色水印未画上"
    (out_dir / "wm_yellow_center.jpg").write_bytes(yellow)

    white = add_watermark(black_bytes, "测试水印", position="bottom_right",
                          color="white", opacity=1.0, font_size_ratio=0.06)
    assert _any_pixel(white, lambda r, g, b: r > 200 and g > 200 and b > 200), \
        "白色水印未画上"

    invisible = add_watermark(black_bytes, "测试水印", opacity=0.0,
                              font_size_ratio=0.06)
    assert not _any_pixel(invisible,
                          lambda r, g, b: r > 60 or g > 60 or b > 60), \
        "opacity=0 应完全不可见"

    for name in COLORS:
        assert add_watermark(src_bytes, "测试水印", color=name,
                             opacity=0.5), name
    assert add_watermark(src_bytes, "测试水印", color="pink"), "未知颜色应回退白色"

    # ⑤ 多行模板 + 居中
    multi = render_template("operator", date="2026-10-13", location="曲靖")
    assert multi == "中国移动巡检\n2026-10-13\n曲靖", multi
    assert render_template("survey", date="2026-10-13",
                           location="曲靖") == "现场勘查\n2026-10-13\n曲靖"
    assert render_template("general", text="自定义文案") == "自定义文案"
    assert render_template("nope", text="兜底") == "兜底"

    # ⑥ LOGO：造一张带透明底的 PNG，贴到右上角；再叠加文字水印
    logo_path = out_dir / "logo.png"
    lg = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(lg).ellipse((10, 10, 190, 190), fill=(255, 0, 0, 255))
    lg.save(logo_path)

    logo_out = add_logo_watermark(src_bytes, logo_path)
    assert logo_out and logo_out != src_bytes, "LOGO 未贴上"
    (out_dir / "wm_logo.jpg").write_bytes(logo_out)

    both = add_logo_watermark(
        add_watermark(src_bytes, multi, position="bottom_left",
                      color="cyan", opacity=0.6),
        logo_path, position="top_right", logo_ratio=0.12)
    assert both != src_bytes, "LOGO + 文字叠加失败"
    (out_dir / "wm_logo_text.jpg").write_bytes(both)

    assert add_logo_watermark(src_bytes, out_dir / "missing.png") == src_bytes, \
        "LOGO 缺失应原样返回"
    for pos in POSITIONS:
        assert add_logo_watermark(src_bytes, logo_path, position=pos), pos

    print(f"自测输出目录：{out_dir}")
    print(f"水印自测通过：{len(src_bytes)} → {len(out)} 字节（默认白色 40%）")
    print(f"9 位置 {POSITIONS}")
    print(f"5 颜色 {tuple(COLORS)} + 透明度 0/0.4/1.0 均正常")
    print(f"多行模板 {multi!r} + LOGO 叠加（透明底 PNG）正常")
