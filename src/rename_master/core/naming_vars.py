"""命名变量：把 EXIF 拍摄时间 / 文件修改时间 / 父目录等动态信息填进文件名。

在模式一「基础名称」或模式二「前缀」里写占位符即可，例如：
    巡检_{exif}_{parent}   →  巡检_20260418_宣会高速
占位符：
    {date}   今天日期
    {mtime}  文件修改时间（YYYYMMDD）
    {exif}   照片拍摄时间（EXIF DateTimeOriginal，无 EXIF 时回退修改时间）
    {parent} 父文件夹名
    {stem}   原文件名（不含扩展名）
    {ext}    原扩展名（含点）
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

# EXIF 标签号
_EXIF_DATETIME_ORIGINAL = 36867
_EXIF_DATETIME = 306
_DATE_FMT = "%Y%m%d"


def exif_datetime(path) -> Optional[datetime]:
    """读取照片 EXIF 拍摄时间（DateTimeOriginal → DateTime 兜底），失败返回 None。"""
    try:
        from PIL import Image

        with Image.open(path) as img:
            exif = img.getexif()
            for tag in (_EXIF_DATETIME_ORIGINAL, _EXIF_DATETIME):
                val = exif.get(tag)
                if val:
                    try:
                        return datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        return None
    return None


def file_mtime(path) -> datetime:
    """文件修改时间，读取失败返回当前时间。"""
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime)
    except OSError:
        return datetime.now()


def render_template(src, template: str) -> str:
    """把模板里的占位符替换为该文件对应的实际值。"""
    src = Path(src)
    mtime = file_mtime(src)
    exif = exif_datetime(src)
    photo_date = exif or mtime

    replacements = {
        "{date}": datetime.now().strftime(_DATE_FMT),
        "{mtime}": mtime.strftime(_DATE_FMT),
        "{exif}": photo_date.strftime(_DATE_FMT),
        "{parent}": src.parent.name,
        "{stem}": src.stem,
        "{ext}": src.suffix,
    }
    out = str(template or "")
    for token, value in replacements.items():
        out = out.replace(token, value)
    return out


def has_variables(text: str) -> bool:
    """模板是否包含任意占位符。"""
    return any(t in str(text or "") for t in
               ("{date}", "{mtime}", "{exif}", "{parent}", "{stem}", "{ext}"))
