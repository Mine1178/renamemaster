"""Excel / CSV 对照表解析：{原文件名: 新文件名}（任务书 §5.3）。

约定：
- 第 1 列原文件名、第 2 列新文件名（无表头时的默认口径）；
- 有表头时按列名识别：含「原文件名/原名/源文件/原始名」→ 左列，
  含「新文件名/新名/目标名/重命名」→ 右列；
- csv 的编码靠 BOM / 内容自动判定（utf-8-sig、utf-16、gbk 都能读），
  分隔符在 `,` `;` `\\t` `|` 之间自动嗅探（欧洲区域设置的 Excel 默认分号）；
- xlsx/xlsm 用 `openpyxl(read_only=True, data_only=True)`，不启 Excel 进程、不锁文件；
- 老式二进制 `.xls` 无法用 openpyxl 读，明确报错并提示「另存为 .xlsx」，
  不再伪装成支持（v1.9 修复：此前选到 .xls 会抛 openpyxl 的英文异常）。
"""
from __future__ import annotations

import codecs
import csv
import io
import logging
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

logger = logging.getLogger(__name__)

ORIGIN_KEYS = ("原文件名", "原名", "源文件", "原始文件名", "原文件", "来源", "old", "source")
TARGET_KEYS = ("新文件名", "新名", "目标名", "目标文件名", "重命名", "new", "target")

SUPPORTED_EXTS = {".xlsx", ".xlsm", ".csv"}
XLS_HINT = ("不支持老式 .xls 对照表（这是 2003 版二进制格式）："
            "请在 Excel / WPS 里「另存为 .xlsx」后再导入。")


def _norm(text) -> str:
    return str(text or "").strip().lstrip("\ufeff").lower()


def _cell_text(value) -> str:
    """单元格 → 去首尾空白的字符串。

    空单元格、以及「有公式但 Excel 从未缓存过结果」的单元格，openpyxl 读出来都是
    None。旧实现直接 str(None)，于是文件名被改成字面量 "None"（v1.9 修复）。
    NaN 同理（openpyxl 对空数字单元格会返回 float('nan')）。
    """
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("none", "nan") else text


def _is_header(row: Sequence) -> bool:
    cells = [_norm(c) for c in row if _norm(c) and _cell_text(c)]
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
        src = _cell_text(row[left]) if left < len(row) else ""
        dst = _cell_text(row[right]) if right < len(row) else ""
        if not src or not dst:
            continue
        mapping[src] = dst
    return mapping


def load_mapping(path: os.PathLike | str) -> Dict[str, str]:
    """读对照表，返回 {原文件名: 新文件名}。

    文件损坏 / 格式不支持时**向上抛异常**（带可读中文原因），由 UI 层弹框提示，
    绝不静默返回空表 —— 空表在界面上和「表里没内容」无法区分（v1.9 澄清）。
    """
    p = Path(path)
    ext = p.suffix.lower()
    try:
        if ext == ".xls":
            # 老式 .xls 是 OLE 复合文档，openpyxl 明确不支持；给出可操作的中文提示，
            # 而不是把 openpyxl 的 InvalidFileException 原文抛到界面上（v1.9 修复）。
            raise ValueError(XLS_HINT)
        if ext in (".xlsx", ".xlsm"):
            return _load_xlsx(p)
        if ext == ".csv":
            return _load_csv(p)
        raise ValueError(f"不支持的对照表格式：{ext or '(无扩展名)'}（支持 .xlsx / .xlsm / .csv）")
    except Exception as exc:                     # noqa: BLE001 解析失败不崩溃
        logger.warning("对照表解析失败 %s: %s", p, exc)
        raise


def _load_xlsx(path: Path) -> Dict[str, str]:
    from openpyxl import load_workbook
    wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        first: Dict[str, str] = {}
        for idx, name in enumerate(wb.sheetnames):
            ws = wb[name]
            rows: List[Sequence] = []
            for row in ws.iter_rows(values_only=True):
                if row is None:
                    continue
                if all(c is None or str(c).strip() == "" for c in row):
                    continue
                rows.append(row)
            mapping = _rows_to_mapping(rows)
            if idx == 0:
                first = mapping
                if mapping:
                    return mapping
                continue
            if mapping:
                # 首个工作表是空白/封面/说明页时顺延到下一个有数据的页。
                # 旧实现只看第一个 sheet，用户把数据放在第二个 sheet 就会得到
                # 一张「解析成功但一条都没有」的空表，且没有任何提示（v1.9 修复）。
                logger.info("对照表首个工作表无数据，改用「%s」", name)
                return mapping
        return first
    finally:
        wb.close()


def _decode_bytes(raw: bytes) -> str:
    """把 csv 字节流解成文本。

    判定顺序（v1.9 修复：此前只认 utf-8-sig/gbk/utf-8，Excel 的「Unicode 文本」
    另存（UTF-16）会解出满屏 `\\x00`，csv 模块直接报
    `new-line character seen in unquoted field`，界面上表现为「导入失败」）：

    1. 带 BOM 的一律以 BOM 为准（UTF-8 / UTF-16 LE / UTF-16 BE / UTF-32）；
    2. 无 BOM 但每隔一字节就是 `\\x00` → 按 UTF-16 LE / BE 解；
    3. 其余先按 UTF-8 严格解，失败再退 GBK（中文 Excel 的 ANSI 另存）；
    4. 全都不行才用替换字符兜底，保证不抛异常。
    """
    for bom, enc in (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
    ):
        if raw.startswith(bom):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                break

    sample = raw[:4096]
    if len(sample) >= 4:
        even, odd = sample[0::2], sample[1::2]
        z_even, z_odd = even.count(0), odd.count(0)
        # 无 BOM 但疑似 UTF-16：ASCII 字符在 UTF-16 里有一个字节是 0，
        # 中文等非 ASCII 字符两个字节都非 0，于是「0 字节集中在奇位还是偶位」
        # 就能判出小端 / 大端。
        if z_odd >= 2 and z_odd > z_even * 2:
            return raw.decode("utf-16-le", errors="replace")
        if z_even >= 2 and z_even > z_odd * 2:
            return raw.decode("utf-16-be", errors="replace")

    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _sniff_delimiter(content: str) -> str:
    """在 `,` `;` `\\t` `|` 里猜分隔符（取前 20 个非空行里出现次数最多的）。

    欧洲区域设置的 Excel 用分号存 csv，制表符分隔的「文本」也很常见；
    此前固定按逗号切，整行会被当成一列，静默产出一张错表（v1.9 修复）。
    """
    delims = (",", ";", "\t", "|")
    lines = [ln for ln in content.splitlines() if ln.strip()][:20]
    counts = {d: sum(ln.count(d) for ln in lines) for d in delims}
    best = max(delims, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def _load_csv(path: Path) -> Dict[str, str]:
    content = _decode_bytes(path.read_bytes())
    delim = _sniff_delimiter(content)
    # newline="" 交给 csv 模块自己处理行尾（含字段内换行），避免
    # `new-line character seen in unquoted field` 这类误报。
    reader = csv.reader(io.StringIO(content, newline=""), delimiter=delim)
    try:
        rows: List[Sequence] = [row for row in reader if row]
    except csv.Error as exc:
        raise ValueError(f"csv 内容无法解析（分隔符按「{delim}」识别）：{exc}") from exc
    return _rows_to_mapping(rows)


def mapping_rows(mapping: Dict[str, str]) -> List[Tuple[str, str]]:
    """dict → [(原, 新), …]（供界面两列 Treeview 展示）。"""
    return [(str(k), str(v)) for k, v in mapping.items()]


def rows_to_mapping(rows: Sequence[Sequence]) -> Dict[str, str]:
    """界面手填的两列 → dict（与 load_mapping 同等校验口径）。"""
    return _rows_to_mapping([list(r) for r in rows])


def export_template(files: Sequence[os.PathLike | str], out_path: os.PathLike | str) -> int:
    """把当前文件列表导出成 Excel 模板：第1列原文件名（已填），第2列新文件名（空）。

    返回写入的行数（不含表头）。
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "对照表"
    # 表头
    ws.append(["原文件名", "新文件名"])
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F4E79")
    for cell in ws[1]:
        cell.font = head_font
        cell.fill = head_fill
    # 数据行
    n = 0
    for f in files:
        name = Path(f).name
        ws.append([name, ""])
        n += 1
    # 列宽
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 40
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    return n


def normalize_export_path(out_path: os.PathLike | str) -> Path:
    """把导出路径规范成 .xlsx。

    我们只写「无宏工作簿」：若用户手输了 ``.xlsm`` / ``.csv`` 之类扩展名，
    写出来的内容与扩展名不符，Excel 打开时会报「格式与扩展名不一致」，
    或被误当成宏工作簿（v1.9 修复的隐性 BUG）。
    """
    p = Path(out_path)
    if p.suffix.lower() == ".xlsx":
        return p
    if p.suffix:
        return p.with_suffix(".xlsx")
    return p.with_name(p.name + ".xlsx")


def export_mapping(mapping: Dict[str, str], out_path: os.PathLike | str) -> int:
    """把当前对照表 dict 导出成 Excel（供二次编辑后再导入）。"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    out_path = normalize_export_path(out_path)
    wb = Workbook()
    ws = wb.active
    ws.title = "对照表"
    ws.append(["原文件名", "新文件名"])
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F4E79")
    for cell in ws[1]:
        cell.font = head_font
        cell.fill = head_fill
    n = 0
    for k, v in mapping.items():
        ws.append([str(k), str(v)])
        n += 1
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 40
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(out_path))
    except PermissionError as exc:
        # 最常见的真实原因：目标文件正在 Excel 里打开（或所在目录只读）。
        # 直接把 PermissionError 抛到界面上只有一句英文，用户看不懂（v1.9 修复）。
        raise RuntimeError(
            f"无法写入 {Path(out_path).name}：文件可能正在 Excel 中打开或被占用，"
            "请关闭后重试") from exc
    return n
