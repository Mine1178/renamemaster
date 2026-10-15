"""操作历史与撤销：每次执行成功后记录批次，可一键删除本批生成的文件。

- 历史持久化到 %APPDATA%\\RenameMaster\\history.json，跨重启也能撤销最近批次；
- 撤销只删除「本批记录在案」的目标文件，绝不碰输出目录里的其它内容；
- 输出目录在删空后会一并移除（避免留下空目录）。
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import List, Optional

from rename_master.config.manager import CONFIG_DIR

HISTORY_PATH = CONFIG_DIR / "history.json"
MAX_BATCHES = 30

# 页面 key → 中文名（弹窗展示用）
PAGE_NAMES = {
    "photo": "照片命名",
    "pdf": "PDF 命名",
    "spreadsheet": "表格命名",
    "document": "文档命名",
}


def _load() -> List[dict]:
    try:
        if HISTORY_PATH.is_file():
            with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return [b for b in data if isinstance(b, dict)]
    except (OSError, ValueError):
        return []
    return []


def _save(batches: List[dict]) -> None:
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = HISTORY_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(batches, fh, ensure_ascii=False, indent=2)
        import os
        os.replace(tmp, HISTORY_PATH)
    except OSError:
        pass


def record_batch(page: str, output_dir, plans, result: Optional[dict] = None) -> dict:
    """执行成功后记录一个批次。

    plans:  RenamePlan 列表（只记录实际落盘成功的）；
    result: execute_plan 返回的结果，用于只统计 done 的文件。
    """
    out_dir = Path(output_dir)
    done_names = set()
    if result and isinstance(result.get("done_names"), (list, set)):
        done_names = {str(n) for n in result["done_names"]}

    items = []
    for plan in plans:
        if done_names and plan.dst_name not in done_names:
            continue
        items.append({"src": str(plan.src), "dst": str(plan.dst_name)})

    batch = {
        "id": uuid.uuid4().hex[:12],
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ts": int(time.time()),
        "page": page,
        "page_name": PAGE_NAMES.get(page, page),
        "output_dir": str(out_dir),
        "items": items,
    }
    batches = _load()
    batches.append(batch)
    batches = batches[-MAX_BATCHES:]
    _save(batches)
    return batch


def recent_batch() -> Optional[dict]:
    """最近一个批次（没有则 None）。"""
    batches = _load()
    return batches[-1] if batches else None


def page_name(page: str) -> str:
    return PAGE_NAMES.get(page, page)


def undo_batch(batch: dict) -> dict:
    """删除该批次生成的文件，返回 {deleted, missing}；删除后从历史移除该批次。

    安全约束：只删除 output_dir 内部、且本批记录的文件，防路径穿越。
    """
    out_dir = Path(batch.get("output_dir", ""))
    deleted = 0
    missing = 0
    try:
        base = out_dir.resolve()
    except OSError:
        base = out_dir

    for item in batch.get("items", []):
        dst = Path(out_dir) / item.get("dst", "")
        try:
            # 必须仍在输出目录内，防止记录里被塞了 ../ 之类的路径
            if not dst.resolve().is_relative_to(base):
                continue
        except (OSError, ValueError):
            continue
        if dst.is_file():
            try:
                dst.unlink()
                deleted += 1
            except OSError:
                missing += 1
        else:
            missing += 1

    # 输出目录若已删空则移除（仅删本批产生的空目录，不递归删非空目录）
    try:
        if out_dir.is_dir() and not any(out_dir.iterdir()):
            out_dir.rmdir()
    except OSError:
        pass

    # 从历史中移除已撤销批次
    batches = _load()
    batches = [b for b in batches if b.get("id") != batch.get("id")]
    _save(batches)
    return {"deleted": deleted, "missing": missing}
