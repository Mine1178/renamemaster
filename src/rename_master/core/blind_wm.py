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


def _imread_checked(path, color: bool = False):
    """读图前先判存在：np.fromfile 直接抛英文 FileNotFoundError，先转成中文。"""
    if not Path(path).is_file():
        raise OSError(f"图片不存在或不是文件：{path}")
    return _imread(path, color)


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

    img = _imread_checked(src)
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
    img = _imread_checked(src, color=True)
    if img is None:
        raise OSError(f"无法读取图片：{src}")
    try:
        length = int(wm_len)
    except (TypeError, ValueError):
        logger.warning("盲水印长度无效（%r），按未检出处理", wm_len)
        return ""
    if length <= 0:
        logger.warning("盲水印长度 %s <= 0，按未检出处理", length)
        return ""
    try:
        return _decode_str(img, length, password_wm, password_img)
    except Exception as exc:                                  # noqa: BLE001
        logger.warning("盲水印提取失败（可能未嵌入或长度不符）：%s: %s",
                       type(exc).__name__, exc)
        return ""


# 控制字符白名单：只放行制表/换行/回车，其余（含 NUL）都视为「不是有效文字」
_CTRL_WHITELIST = {"\t", "\n", "\r"}


def _decode_str(img, length: int, password_wm, password_img) -> str:
    """复刻 blind-watermark 的 str 模式提取，并修正其两处缺陷：

    1. 原实现取到 bit 串后 `hex(int(bits, 2))[2:]` 丢前导 0 位、再不补零交给
       `bytes.fromhex`，位长 ≡ 1 (mod 4) 时直接抛
       `ValueError: fromhex() arg must contain an even number of hexadecimal
       digits`（实测：水印文字以 `\\x01` 这类控制字符开头即可复现，
       见 inbox/_probe_wm_decode.py）→ 这里补足偶数位，字节序与原库一致。
    2. 原实现 `decode("utf-8", errors="replace")`：对「压根没有盲水印」的图，
       随机位会被解成带 U+FFFD 的乱码并当作成功结果返回给界面 → 这里改严格
       解码，解不出合法 UTF-8（或解出控制字符）一律视为「未检出」，返回空串。
    """
    import numpy as np
    from blind_watermark import WaterMark

    bwm = WaterMark(password_wm=int(password_wm), password_img=int(password_img))
    # extract_decrypt 依赖 self.wm_size 生成解扰下标，原库在 extract() 里赋过，
    # 这里自己走一遍流程，必须补上。
    bwm.wm_size = np.array(length).prod()
    wm_avg = bwm.bwm_core.extract_with_kmeans(img=img, wm_shape=int(length))
    wm = bwm.extract_decrypt(wm_avg=wm_avg)
    bits = "".join(str(int(i >= 0.5)) for i in wm)
    if not bits:
        return ""
    hexs = hex(int(bits, 2))[2:]
    if len(hexs) % 2:
        hexs = "0" + hexs
    try:
        text = bytes.fromhex(hexs).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
    if any(ord(ch) < 0x20 and ch not in _CTRL_WHITELIST for ch in text):
        return ""
    return text
