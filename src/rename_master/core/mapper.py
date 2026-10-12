"""Excel / CSV 对照表解析：{原文件名: 新文件名}（任务书 §5.3）。

约定：
- 第 1 列原文件名、第 2 列新文件名（无表头时的默认口径）；
- 有表头时按列名识别：含「原文件名/原名/源文件/原始名」→ 左列，
  含「新文件名/新名/目标名/重命名」→ 右列；
- csv 统一用 `utf-8-sig` 读（防 BOM 把第一列表头污染成 `\\ufeff原文件名`）；
- xlsx 用 `openpyxl(read_only=True, data_only=True)`，不启 Excel 进程、不锁文件。
"""
from __future__ import annotations

import csv
import io
import logging
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

logger = logging.getLogger(__name__)

ORIGIN_KEYS = ("原文件名", "原名", "源文件", "原始文件名", "原文件", "来源", "old", "source")
TARGET_KEYS = ("新文件名", "新名", "目标名", "目标文件名", "重命名", "new", "target")

SUPPORTED_EXTS = {".xlsx", ".xlsm", ".xls", ".csv"}


def _norm(text) -> str:
    return str(text or "").strip().lstrip("\ufeff").lower()


def _is_header(row: Sequence) -> bool:
    cells = [_norm(c) for c in row if _norm(c)]
    if not cells:
        return False
    return any(any(k in c for k in ORIGIN_KEYS) for c in cells) or \
        any(any(k in c for k in TARGET_KEYS) for c in cells)


def _pick_columns(header: Sequence) -> Tuple[int, int]:
    """按表头列名挑左右列；识别不出就回落 (0, 1)。"""
    left = right = -1
    for idx, cell in enumerate(header):
        text = _norm(cell)
        if not text:
            continue
        if left < 0 and any(k in text for k in ORIGIN_KEYS):
            left = idx
        elif right < 0 and any(k in text for k in TARGET_KEYS):
            right = idx
    if left < 0:
        left = 0
    if right < 0:
        right = 1 if len(header) > 1 and left != 1 else 0
    return left, right


def _rows_to_mapping(rows: List[Sequence]) -> Dict[str, str]:
    if not rows:
        return {}
    left, right = (0, 1) if not _is_header(rows[0]) else _pick_columns(rows[0])
    body = rows[1:] if _is_header(rows[0]) else rows
    mapping: Dict[str, str] = {}
    for row in body:
        if not row:
            continue
        src = str(row[left]).strip() if left < len(row) else ""
        dst = str(row[right]).strip() if right < len(row) else ""
        if not src or not dst:
            continue
        mapping[src] = dst
    return mapping


def load_mapping(path: os.PathLike | str) -> Dict[str, str]:
    """读对照表，返回 {原文件名: 新文件名}；解析失败返回空 dict（不抛，UI 层提示）。"""
    p = Path(path)
    ext = p.suffix.lower()
    try:
        if ext in (".xlsx", ".xlsm", ".xls"):
            return _load_xlsx(p)
        if ext == ".csv":
            return _load_csv(p)
        raise ValueError(f"不支持的对照表格式：{ext or '(无扩展名)'}（支持 .xlsx / .xls / .csv）")
    except Exception as exc:                     # noqa: BLE001 解析失败不崩溃
        logger.warning("对照表解析失败 %s: %s", p, exc)
        raise


def _load_xlsx(path: Path) -> Dict[str, str]:
    from openpyxl import load_workbook
    wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        rows: List[Sequence] = []
        for row in ws.iter_rows(values_only=True):
            if row is None:
                continue
            if all(c is None or str(c).strip() == "" for c in row):
                continue
            rows.append(row)
    finally:
        wb.close()
    return _rows_to_mapping(rows)


def _load_csv(path: Path) -> Dict[str, str]:
    text = path.read_bytes()
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            content = text.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        content = text.decode("utf-8", errors="replace")
    rows: List[Sequence] = [row for row in csv.reader(io.StringIO(content)) if row]
    return _rows_to_mapping(rows)


def mapping_rows(mapping: Dict[str, str]) -> List[Tuple[str, str]]:
    """dict → [(原, 新), …]（供界面两列 Treeview 展示）。"""
    return [(str(k), str(v)) for k, v in mapping.items()]


def rows_to_mapping(rows: Sequence[Sequence]) -> Dict[str, str]:
    """界面手填的两列 → dict（与 load_mapping 同等校验口径）。"""
    return _rows_to_mapping([list(r) for r in rows])
