"""盲水印（隐形）：基于 GitHub guofei9987/blind_watermark 频域方案。

- 肉眼不可见，不影响图片观感；
- 抗 JPEG 压缩 / 格式转换 / 轻度处理；可见水印被抹掉后仍可取证；
- embed_watermark 嵌入文字，返回水印比特长度（提取时必须）；
- extract_watermark 提取文字。

重要：全程使用 numpy.fromfile + cv2.imdecode / imencode + tofile，
绕开 OpenCV 在 Windows 上不支持中文路径的问题。

水印比特长度只取决于"文字长度"，与图片大小、密码无关；
同一段文字嵌入任意图片长度都相同，故同批可直接用嵌入时返回的长度提取。
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PW_WM = 1
DEFAULT_PW_IMG = 1


def _imread(path, color: bool = False):
    """读取图片（支持中文路径）。color=True 时按三通道彩色读。"""
    import cv2
    import numpy as np

    data = np.fromfile(str(path), dtype=np.uint8)
    flags = cv2.IMREAD_COLOR if color else cv2.IMREAD_UNCHANGED
    return cv2.imdecode(data, flags)


def _imwrite(path, img, ext: str = "") -> None:
    """写入图片（支持中文路径）。"""
    import cv2
    import numpy as np

    ext = ext or Path(path).suffix or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise OSError(f"图片编码失败：{path}")
    buf.tofile(str(path))


def embed_watermark(src, dst, text: str, password_wm=DEFAULT_PW_WM,
                    password_img=DEFAULT_PW_IMG) -> int:
    """在图片中嵌入盲水印文字，返回水印比特长度（提取时需要）。

    src/dst 为文件路径，支持中文路径；建议 dst 用 PNG（无损，水印最完整）。
    """
    from blind_watermark import WaterMark

    img = _imread(src)
    if img is None:
        raise OSError(f"无法读取图片：{src}")

    bwm = WaterMark(password_wm=int(password_wm), password_img=int(password_img))
    bwm.read_img(img=img)
    bwm.read_wm(str(text), mode="str")
    embed_img = bwm.embed(filename=None)            # 只拿数组，不 cv2.imwrite
    _imwrite(dst, embed_img, Path(dst).suffix or ".png")
    length = len(bwm.wm_bit)
    logger.info("盲水印已嵌入 %s（长度 %s）", dst, length)
    return length


def extract_watermark(src, wm_len, password_wm=DEFAULT_PW_WM,
                      password_img=DEFAULT_PW_IMG) -> str:
    """从图片提取盲水印文字；wm_len 为嵌入时返回的长度。"""
    from blind_watermark import WaterMark

    img = _imread(src, color=True)
    if img is None:
        raise OSError(f"无法读取图片：{src}")
    bwm = WaterMark(password_wm=int(password_wm), password_img=int(password_img))
    return str(bwm.extract(embed_img=img, wm_shape=int(wm_len), mode="str"))
