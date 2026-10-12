"""文档正文提取：取开头若干字符作为默认文件名（docx / pdf / txt / md）。

只读取、不写盘；任何异常（缺库 / 加密 PDF / 编码问题）都降级返回空串，
绝不因单个坏文件中断整批。
"""
from __future__ import annotations

from pathlib import Path


def extract_title(path: Path, max_chars: int = 30) -> str:
    """从 docx/pdf/txt/md 提取前 max_chars 个字符作为默认文件名。失败返回空串。"""
    suffix = Path(path).suffix.lower()
    try:
        if suffix == ".docx":
            from docx import Document
            doc = Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text = ""
            for page in reader.pages[:2]:
                text += page.extract_text() or ""
        elif suffix in (".txt", ".md"):
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        else:
            return ""
        # 清理：去空白换行截断
        cleaned = "".join(text.split())[:max_chars]
        return cleaned
    except Exception:
        return ""
