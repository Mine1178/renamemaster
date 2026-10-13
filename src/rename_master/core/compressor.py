"""图片压缩：二分法找 JPEG quality，把图压到目标 KB 以内（任务书 §5.2）。

流程：
1. `ImageOps.exif_transpose` 按 EXIF 旋转标记转正（手机竖拍图不再躺倒）；
2. 二分搜索 quality（10~90，最多 8 次），取「不超过目标的最大一版」；
3. quality 降到 10 仍超 → 最长边 ×0.9 缩分辨率（最多 5 次），回到第 2 步；
4. 全程在内存 BytesIO 里完成，不落盘、不改原图。
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

Q_MIN, Q_MAX = 10, 90
Q_STEPS = 8             # 二分迭代次数
SCALE_STEPS = 5         # 最多缩分辨率次数
SCALE_FACTOR = 0.9      # 每次最长边缩放比例
MAX_EDGE = 4096         # 默认最长边上限


def _load(src_bytes: bytes, keep_exif: bool):
    """读图 → EXIF 转正 → 取（可能清掉 orientation 的）EXIF 字节 → 转 RGB。"""
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(src_bytes))
    exif_bytes = b""
    if keep_exif:
        try:
            raw = img.info.get("exif")
            img.load()
            ex = img.getexif()          # 转正后仍带 orientation 标记会导致二次旋转
            if 274 in ex:               # 0x0112 Orientation
                del ex[274]
            exif_bytes = ex.tobytes() or (raw or b"")
        except Exception:               # noqa: BLE001 EXIF 异常不影响压缩
            exif_bytes = b""
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img, exif_bytes


def _encode(img, quality: int, exif_bytes: bytes, optimize: bool = True) -> bytes:
    buf = io.BytesIO()
    try:
        img.save(buf, format="JPEG", quality=quality, optimize=optimize,
                 exif=exif_bytes)
    except (ValueError, TypeError):      # 空/非法 EXIF：退化为不带 EXIF 再存
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=optimize)
    return buf.getvalue()


def _resample():
    from PIL import Image
    return getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)


def _resize(img, width: int, height: int):
    return img.resize((max(1, int(width)), max(1, int(height))), resample=_resample())


def _fit_edge(img, max_edge: int):
    """最长边 ≤ max_edge 等比缩放（默认 4096，任务书 §3.3）。"""
    if max_edge and max(img.width, img.height) > max_edge:
        scale = float(max_edge) / float(max(img.width, img.height))
        img = _resize(img, img.width * scale, img.height * scale)
    return img


def compress_to_target(src_bytes: bytes, target_kb: int,
                       keep_exif: bool = True, max_edge: int = MAX_EDGE,
                       optimize_enc: bool = True,
                       max_scale_rounds: int = SCALE_STEPS) -> bytes:
    """把图片字节压到 ≤ target_kb KB；压不到就返回**体积最小的那版**。

    返回值为 JPEG 字节流（PNG 透明图会先合成白底再转 JPEG）。

    - optimize_enc：落盘用 True（体积最小，编码慢）；预览预估传 False（快约 4 倍，
      体积差几个百分点，估计足够）。
    - max_scale_rounds：缩分辨率轮数上限；预估可压到 2，提早结束。
    """
    target = max(1, int(target_kb)) * 1024
    img, exif_bytes = _load(src_bytes, keep_exif)
    img = _fit_edge(img, max_edge)

    best: Optional[Tuple[int, bytes]] = None      # 不超过目标的最大一版
    fallback: Optional[Tuple[int, bytes]] = None  # 全程最小的一版（兜底）

    for _round in range(max(0, int(max_scale_rounds)) + 1):
        lo, hi = Q_MIN, Q_MAX
        for _ in range(Q_STEPS):
            if lo > hi:
                break
            q = (lo + hi) // 2
            data = _encode(img, q, exif_bytes, optimize=optimize_enc)
            size = len(data)
            if fallback is None or size < fallback[0]:
                fallback = (size, data)
            if size <= target:
                if best is None or size > best[0]:
                    best = (size, data)
                lo = q + 1
            else:
                hi = q - 1
        if best is not None:
            break
        # quality 已到底仍超目标 → 缩分辨率再来一轮
        img = _resize(img, img.width * SCALE_FACTOR, img.height * SCALE_FACTOR)

    return (best or fallback or (0, src_bytes))[1]


def compress_file(src: os.PathLike | str, dst: os.PathLike | str,
                  target_kb: int, keep_exif: bool = True,
                  max_edge: int = MAX_EDGE) -> int:
    """从文件读 → 压 → 写到 dst（用于执行阶段），返回输出字节数。"""
    data = Path(src).read_bytes()
    out = compress_to_target(data, target_kb, keep_exif=keep_exif, max_edge=max_edge)
    Path(dst).write_bytes(out)
    return len(out)


def estimate_size(src: os.PathLike | str, target_kb: int,
                  keep_exif: bool = True, max_edge: int = MAX_EDGE) -> int:
    """预览用：快速估算压缩后的字节数（不落盘）。

    走快速路径：不 optimize（编码快约 4 倍）、最多 2 轮缩分辨率，结果与正式压缩
    通常相差几个百分点，预览足够；在后台线程调用，避免主线程冻结。
    """
    try:
        return len(compress_to_target(Path(src).read_bytes(), target_kb,
                                      keep_exif=keep_exif, max_edge=max_edge,
                                      optimize_enc=False, max_scale_rounds=2))
    except Exception as exc:                    # noqa: BLE001 坏图不阻塞预览
        logger.warning("压缩预估失败 %s: %s", src, exc)
        try:
            return os.path.getsize(src)
        except OSError:
            return 0
