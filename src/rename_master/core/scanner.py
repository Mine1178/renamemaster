"""文件扫描：把用户选中的文件 / 文件夹展开成待处理文件列表。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Sequence

# 图片类（照片命名页）
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".heic"}
# 表格类（表格命名页）
SPREADSHEET_EXTS = {".xlsx", ".xlsm", ".xls", ".csv"}
# 文档类（文档命名页）
DOCUMENT_EXTS = {".docx", ".pdf", ".txt", ".md"}
# scan_files 默认口径（任务书 §5：图片 + 文档）
DOC_EXTS = {".xlsx", ".docx", ".pdf", ".txt"}
DEFAULT_EXTS = IMAGE_EXTS | DOC_EXTS


def scan_files(paths: Iterable[os.PathLike | str],
               exts: Sequence[str] | None = None,
               recursive: bool = True) -> List[Path]:
    """把一组路径（文件 / 目录混合）展开为文件列表。

    - 文件：扩展名命中 `exts`（大小写不敏感）才收；
    - 目录：递归（默认）收集命中的文件；
    - 结果按路径升序去重返回，保证多批次导入顺序稳定。
    """
    allow = {e.lower() if e.startswith(".") else f".{e}".lower()
             for e in (exts if exts is not None else DEFAULT_EXTS)}
    found: List[Path] = []
    seen: set[str] = set()
    for raw in paths or ():
        try:
            p = Path(raw)
        except TypeError:
            continue
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            for sub in it:
                if sub.is_file() and sub.suffix.lower() in allow:
                    key = str(sub.resolve()).lower()
                    if key not in seen:
                        seen.add(key)
                        found.append(sub)
        elif p.is_file():
            if p.suffix.lower() in allow:
                key = str(p.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(p)
    found.sort(key=lambda x: str(x).lower())
    return found


def file_size(path: os.PathLike | str) -> int:
    """文件大小（字节）；读取失败返回 0（不因单个坏文件中断整批）。"""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def image_size(path: os.PathLike | str) -> str:
    """图片尺寸 '宽×高'；非图片 / 读取失败返回 '-'（Pillow 缺失时同样降级）。"""
    try:
        from PIL import Image
        with Image.open(path) as img:
            return f"{img.width}×{img.height}"
    except Exception:
        return "-"


def fmt_size(num_bytes: float) -> str:
    """字节数人性化（B/KB/MB/GB）。"""
    n = float(max(0, num_bytes))
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"
