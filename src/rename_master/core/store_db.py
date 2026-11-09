"""门店档案管理：本地 SQLite 持久化 + Excel 批量导入 / 导出。

实现逻辑参照 addressmap-tool 的「Excel 批量处理 + 本地缓存」思路，但改为
更贴合本工具的「门店主数据」场景：

- 数据落在 %APPDATA%\\RenameMaster\\store.db（与配置同目录，可写、跨版本保留）；
- 支持按门店编号查重：导入时编号已存在则更新，否则新增；
- Excel 列名做同义词兼容（编号 / 编码 / 店名 / 店长 / 手机 …），降低使用门槛；
- 纯逻辑层，不依赖 tkinter，便于脱离 GUI 做单元自测。
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from rename_master.config.manager import CONFIG_DIR

DB_PATH = CONFIG_DIR / "store.db"

# 字段顺序（同时是导出表头顺序）
FIELDS: List[str] = ["code", "name", "city", "address", "manager", "phone", "remark"]

# 导出 / 导入用的中文表头
EXPORT_HEADERS: Dict[str, str] = {
    "code": "门店编号",
    "name": "门店名称",
    "city": "所在城市",
    "address": "详细地址",
    "manager": "负责人",
    "phone": "联系电话",
    "remark": "备注",
}

# 列名同义词 → 字段（全部小写、去空格后匹配）
_SYNONYMS: Dict[str, str] = {}
for _f, _zh in EXPORT_HEADERS.items():
    _SYNONYMS[_zh.lower()] = _f
_EXTRA = {
    "编号": "code", "编码": "code", "code": "code", "门店编码": "code",
    "名称": "name", "店名": "name", "门店": "name", "name": "name",
    "城市": "city", "市": "city", "city": "city",
    "地址": "address", "门店地址": "address", "address": "address",
    "负责人": "manager", "店长": "manager", "经理": "manager", "manager": "manager",
    "电话": "phone", "联系电话": "phone", "手机": "phone", "手机号": "phone",
    "tel": "phone", "phone": "phone",
    "备注": "remark", "说明": "remark", "备注说明": "remark", "remark": "remark",
}
_SYNONYMS.update({k.lower(): v for k, v in _EXTRA.items()})


def _norm_key(s: str) -> str:
    return str(s).strip().lower()


def _connect() -> sqlite3.Connection:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """建表（幂等）。"""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stores (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                code      TEXT    NOT NULL DEFAULT '',
                name      TEXT    NOT NULL DEFAULT '',
                city      TEXT    NOT NULL DEFAULT '',
                address   TEXT    NOT NULL DEFAULT '',
                manager   TEXT    NOT NULL DEFAULT '',
                phone     TEXT    NOT NULL DEFAULT '',
                remark    TEXT    NOT NULL DEFAULT '',
                created_at TEXT   NOT NULL,
                updated_at TEXT   NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_stores_code ON stores(code)"
        )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row: sqlite3.Row) -> Dict[str, str]:
    return {f: (row[f] or "") for f in FIELDS}


def count_stores() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM stores").fetchone()["n"]


def list_stores(search: str = "") -> List[Dict[str, str]]:
    """列出门店；search 非空时按编号 / 名称 / 城市 / 负责人 / 电话 / 地址模糊匹配。"""
    init_db()
    with _connect() as conn:
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT id, code, name, city, address, manager, phone, remark,
                          updated_at
                   FROM stores
                   WHERE code LIKE ? OR name LIKE ? OR city LIKE ?
                      OR manager LIKE ? OR phone LIKE ? OR address LIKE ?
                   ORDER BY id DESC""",
                (like, like, like, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, code, name, city, address, manager, phone, remark,
                          updated_at
                   FROM stores
                   ORDER BY id DESC"""
            ).fetchall()
        out: List[Dict[str, str]] = []
        for r in rows:
            d = {f: (r[f] or "") for f in FIELDS}
            d["id"] = r["id"]
            d["updated_at"] = r["updated_at"] or ""
            out.append(d)
        return out


def get_store(store_id: int) -> Optional[Dict[str, str]]:
    init_db()
    with _connect() as conn:
        r = conn.execute(
            "SELECT * FROM stores WHERE id = ?", (store_id,)
        ).fetchone()
        return _row_to_dict(r) if r else None


def add_store(data: Dict[str, str]) -> int:
    """新增一条，返回新 id。"""
    init_db()
    now = _now()
    vals = {f: (data.get(f) or "").strip() for f in FIELDS}
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO stores
               (code, name, city, address, manager, phone, remark,
                created_at, updated_at)
               VALUES (:code, :name, :city, :address, :manager, :phone, :remark,
                       :now, :now)""",
            {**vals, "now": now},
        )
        return int(cur.lastrowid)


def update_store(store_id: int, data: Dict[str, str]) -> None:
    """更新门店：只覆盖 data 中显式给出的字段，其余保留原值。

    这样 Excel 导入时即使文件只含「编号 / 名称」两列，也不会把城市、
    地址、负责人等字段误清空（旧实现用 data.get(f) 兜底成空串，会整体覆盖）。
    """
    init_db()
    existing = get_store(store_id)
    if existing is None:
        return
    vals = {}
    for f in FIELDS:
        vals[f] = (data[f].strip() if data.get(f) is not None
                   else existing.get(f, ""))
    with _connect() as conn:
        conn.execute(
            """UPDATE stores SET
                  code=:code, name=:name, city=:city, address=:address,
                  manager=:manager, phone=:phone, remark=:remark,
                  updated_at=:now
               WHERE id=:id""",
            {**vals, "now": _now(), "id": store_id},
        )


def delete_store(store_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM stores WHERE id = ?", (store_id,))


def delete_stores(ids: Iterable[int]) -> int:
    ids = list(ids)
    if not ids:
        return 0
    with _connect() as conn:
        placeholders = ",".join("?" * len(ids))
        cur = conn.execute(
            f"DELETE FROM stores WHERE id IN ({placeholders})", ids
        )
        return cur.rowcount


def import_excel(path: str | Path) -> Dict[str, int]:
    """从 Excel 导入门店：按编号查重，存在则更新、不存在则新增。

    返回统计 {added, updated, skipped, errors}。
    """
    from openpyxl import load_workbook  # 延迟导入，开发态也能单独跑逻辑层

    init_db()
    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    path = Path(path)
    wb = load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return stats

    # 表头映射：第 0 行 → 字段
    header = rows[0]
    col_to_field: Dict[int, str] = {}
    for idx, h in enumerate(header):
        if h is None:
            continue
        field = _SYNONYMS.get(_norm_key(h))
        if field:
            col_to_field[idx] = field

    # 没有任何可识别列 → 全部跳过
    if not col_to_field:
        wb.close()
        return stats

    for r in rows[1:]:
        # 只记录文件中实际出现的列（缺失列不在 record 里 → 更新时保留原值）
        record: Dict[str, str] = {}
        for idx, field in col_to_field.items():
            v = r[idx] if idx < len(r) else None
            record[field] = "" if v is None else str(v).strip()
        if not record.get("name"):
            stats["skipped"] += 1
            continue
        try:
            code = record.get("code")
            existing = None
            if code:
                with _connect() as conn:
                    row = conn.execute(
                        "SELECT id FROM stores WHERE code = ?", (code,)
                    ).fetchone()
                    if row:
                        existing = row["id"]
            if existing is not None:
                update_store(existing, record)
                stats["updated"] += 1
            else:
                add_store(record)
                stats["added"] += 1
        except Exception:
            stats["errors"] += 1
    wb.close()
    return stats


def export_excel(path: str | Path, rows: Optional[List[Dict[str, str]]] = None) -> int:
    """导出门店到 Excel，返回导出条数。"""
    from openpyxl import Workbook  # 延迟导入

    if rows is None:
        rows = list_stores()
    wb = Workbook()
    ws = wb.active
    ws.title = "门店档案"
    ws.append([EXPORT_HEADERS[f] for f in FIELDS])
    for r in rows:
        ws.append([r.get(f, "") for f in FIELDS])
    wb.save(str(path))
    return len(rows)


# 简易非 GUI 自测（python -m rename_master.core.store_db 时运行）
if __name__ == "__main__":
    import tempfile

    # 临时库，避免污染真实配置
    import os
    os.environ.setdefault("APPDATA", tempfile.gettempdir())
    init_db()
    print("count before:", count_stores())
    a = add_store({"code": "S001", "name": "旗舰店", "city": "昆明",
                   "address": "五华区", "manager": "张三", "phone": "138000"})
    b = add_store({"code": "S002", "name": "自营店", "city": "曲靖"})
    print("count after add:", count_stores(), "ids", a, b)
    update_store(a, {"name": "旗舰店(改)", "phone": "139000"})
    print("get:", get_store(a))
    print("search 昆明:", [s["name"] for s in list_stores("昆明")])
    tmp = Path(tempfile.gettempdir()) / "store_selftest.xlsx"
    n = export_excel(tmp)
    print("export rows:", n, "->", tmp)
    print("import stats:", import_excel(tmp))
    print("SELFTEST OK")
