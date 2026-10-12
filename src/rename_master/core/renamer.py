"""重命名引擎：干跑生成计划（不碰磁盘） + 真正执行（输出目录隔离）。

任务书 §5.1：
1. `plan_rename()` 只在内存里算新名，做重名 / 非法字符校验，**不写盘**；
2. `execute_plan()` 把结果写到**独立输出目录**，默认复制（原目录零改动，CHECKLIST E1）；
   只有当调用方显式 `move=True` 时才用 shutil.move（原地改名，需调用方二次确认）。
"""
from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from rename_master.core import scanner

logger = logging.getLogger(__name__)

# 日志目录：<项目根>/logs（与任务书 §3.4 一致），不存在时自动创建
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"

# Windows / macOS 文件名非法字符（任务书 §3.2：自动替换为 _ 并标黄）
ILLEGAL_CHARS = '\\/:*?"<>|'
_ILLEGAL_TABLE = str.maketrans({ch: "_" for ch in ILLEGAL_CHARS})

# 重名自动追加的后缀序列：_b、_c …（任务书 §3.1）
_CONFLICT_SUFFIXES = [chr(c) for c in range(ord("b"), ord("z") + 1)]

MODE_PREFIX = "prefix"   # 模式一：统一前缀 + 序号
MODE_MAP = "map"         # 模式二：一一对照


def sanitize_name(name: str) -> str:
    """替换非法字符与控制字符为 '_'，去首尾空白与末尾点号。"""
    cleaned = str(name or "").translate(_ILLEGAL_TABLE)
    cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32)
    cleaned = cleaned.strip().rstrip(".")
    return cleaned


def default_output_dir(files: Sequence[Path]) -> Path:
    """默认输出目录 `<源目录>_重命名输出`（取第一个文件的父目录，永不等于源目录）。"""
    if not files:
        return Path.cwd() / "重命名输出"
    parent = Path(files[0]).resolve().parent
    return parent.parent / f"{parent.name}_重命名输出"


@dataclass
class RenamePlan:
    """单条改名计划（src 为绝对路径，dst_name 仅为**文件名**，不含目录）。"""

    src: Path
    dst_name: str
    warnings: List[str] = field(default_factory=list)
    status: str = "ok"            # ok / warn / error
    new_size: Optional[int] = None  # 预计（或实际）输出大小，压缩后填
    note: str = ""

    @property
    def src_name(self) -> str:
        return self.src.name

    @property
    def blocked(self) -> bool:
        return self.status == "error"

    def add_warning(self, reason: str) -> None:
        if reason not in self.warnings:
            self.warnings.append(reason)
        if self.status == "ok":
            self.status = "warn"

    def mark_error(self, reason: str) -> None:
        self.status = "error"
        self.note = reason


# ---------- 模式一：统一前缀 + 序号 ----------
def _prefix_name(src: Path, index: int, rule: Dict) -> str:
    base = str(rule.get("base_name") or "").strip()
    digits = int(rule.get("digits", 3) or 3)
    start = int(rule.get("start", 1) or 1)
    sep = str(rule.get("sep", "_") or "")
    keep_ext = bool(rule.get("keep_ext", True))
    date_prefix = bool(rule.get("date_prefix", False))

    ext = src.suffix if keep_ext else ".jpg"
    if not ext:
        ext = ".jpg"
    head = f"{rule.get('date') or date.today().strftime('%Y%m%d')}_" if date_prefix else ""
    number = f"{start + index:0{max(1, digits)}d}"
    return f"{head}{base}{sep}{number}{ext}"


# ---------- 模式二：一一对照 ----------
def _map_name(src: Path, index: int, mapping: Dict[str, str]) -> tuple:
    """按 原名 → 主名(stem) → 序号 三级匹配；返回 (新名 or None, 是否带扩展名)。"""
    for key in (src.name, src.stem, str(index + 1)):
        val = mapping.get(key)
        if val:
            return str(val).strip(), True
        # 大小写不敏感兜底（Windows 文件名不区分大小写）
        for mk, mv in mapping.items():
            if str(mk).lower() == str(key).lower() and mv:
                return str(mv).strip(), True
    return None, False


def plan_rename(files: Iterable[os.PathLike | str], mode: str, rule: Dict) -> List[RenamePlan]:
    """生成改名计划（**纯内存，不写盘**）。

    mode:
      - `"prefix"`：rule = {base_name, digits, start, sep, keep_ext, date_prefix, date}
      - `"map"`   ：rule = {mapping: {原文件名: 新文件名}, keep_ext: bool}

    重名自动追加 `_b`/`_c`…；非法字符替换为 `_`；模式二未匹配的文件保持原名。
    """
    rule = dict(rule or {})
    paths = [Path(f) for f in (files or [])]
    mapping: Dict[str, str] = dict(rule.get("mapping") or {}) if mode == MODE_MAP else {}
    keep_ext = bool(rule.get("keep_ext", True))

    # 模式二：新名重复 → 红色标记、禁止执行（CHECKLIST C4）
    dup_new: set[str] = set()
    if mode == MODE_MAP:
        seen: Dict[str, int] = {}
        for _k, v in mapping.items():
            raw_v = str(v or "").strip().lower()
            if not raw_v:
                continue
            # 同时按「完整名」与「去扩展名主名」计数：对照表可能带 .jpg 也可能不带
            for key in (raw_v, os.path.splitext(raw_v)[0]):
                if key:
                    seen[key] = seen.get(key, 0) + 1
        dup_new = {k for k, n in seen.items() if n > 1}

    used: set[str] = set()
    plans: List[RenamePlan] = []
    for i, src in enumerate(paths):
        if mode == MODE_MAP:
            raw, matched = _map_name(src, i, mapping)
            if not matched or not raw:
                plans.append(RenamePlan(src=src, dst_name=src.name,
                                        status="warn",
                                        warnings=["对照表未匹配，保持原名"]))
                used.add(src.name.lower())
                continue
            new_name = raw
            # 新名没写扩展名 → 按 keep_ext 补（不勾则统一 .jpg）
            if not Path(new_name).suffix:
                new_name = f"{new_name}{src.suffix if keep_ext else '.jpg'}"
        else:
            new_name = _prefix_name(src, i, rule)

        cleaned = sanitize_name(new_name)
        plan = RenamePlan(src=src, dst_name=cleaned or src.name)
        if cleaned != new_name:
            plan.add_warning("新名含非法字符，已替换为 _")
        if not Path(plan.dst_name).suffix:
            plan.dst_name = f"{plan.dst_name}{src.suffix}"
        if not plan.dst_name or plan.dst_name.startswith("."):
            plan.mark_error("新文件名为空")
            plans.append(plan)
            continue

        # 重名冲突：序号后追加 _b / _c …
        stem, ext = os.path.splitext(plan.dst_name)
        if plan.dst_name.lower() in used:
            for suf in _CONFLICT_SUFFIXES:
                cand = f"{stem}_{suf}{ext}"
                if cand.lower() not in used:
                    plan.dst_name = cand
                    plan.add_warning("目标名重复，已自动加后缀")
                    break
            else:
                plan.mark_error("目标名重复且无可用后缀")
                plans.append(plan)
                continue
        if mode == MODE_MAP and (plan.dst_name.lower() in dup_new
                                 or str(stem).lower() in dup_new):
            plan.mark_error("对照表新名重复，禁止执行")

        used.add(plan.dst_name.lower())
        plans.append(plan)
    return plans


# ---------- 执行 ----------
def _open_log() -> Optional[Path]:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        return LOG_DIR / f"rename_{date.today().strftime('%Y%m%d')}.log"
    except OSError:
        return None


def execute_plan(plans: Sequence[RenamePlan],
                 output_dir: os.PathLike | str,
                 move: bool = False,
                 transform: Optional[Callable[[Path, str], Optional[bytes]]] = None,
                 progress: Optional[Callable[[int, int, str], None]] = None,
                 cancel: Optional[Callable[[], bool]] = None,
                 backup_originals: bool = False) -> Dict:
    """把计划落到**独立输出目录**。

    - 默认 `shutil.copy2`（原目录零改动，符合 CHECKLIST E1 / 硬约束"绝不原地覆盖"）；
    - `move=True` 时改用 `shutil.move`（原地改名，调用方必须先做红色二次确认）；
    - `transform(src, dst_name)` 返回字节则按字节写盘（压缩后的图片走这条路径）；
    - `progress(done, total, name)` / `cancel()` 供后台线程与 UI 联动。

    输出目录与任一源文件目录相同 → 该条直接标记失败跳过，绝不覆盖原文件。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = _open_log()
    total = len(plans)
    done = failed = skipped = 0
    errors: List[str] = []
    out_resolved = out_dir.resolve()

    for i, plan in enumerate(plans):
        if cancel is not None and cancel():
            skipped += 1
            continue
        if progress is not None:
            progress(i, total, plan.src.name)
        try:
            src = Path(plan.src)
            if plan.blocked:
                failed += 1
                errors.append(f"{plan.src.name}: {plan.note}")
                continue
            src_dir = src.resolve().parent
            if move and src_dir == out_resolved:
                # 原地改名：目标名不得命中任何已存在文件（防覆盖）
                dst = out_dir / plan.dst_name
                if dst.exists() and dst.resolve() != src.resolve():
                    raise FileExistsError(f"目标已存在，拒绝覆盖：{dst.name}")
            elif src_dir == out_resolved and not move:
                failed += 1
                errors.append(f"{plan.src.name}: 输出目录与源目录相同，已跳过（拒绝原地覆盖）")
                continue
            dst = out_dir / plan.dst_name

            old_size = scanner.file_size(src)
            data = transform(src, plan.dst_name) if transform else None
            if data is not None:
                dst.write_bytes(data)
                new_size = len(data)
            elif move:
                shutil.move(str(src), str(dst))
                new_size = scanner.file_size(dst)
            else:
                shutil.copy2(str(src), str(dst))
                new_size = scanner.file_size(dst)
            if backup_originals:
                bak_dir = out_dir / "_originals"
                bak_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(bak_dir / src.name))
            plan.new_size = new_size
            done += 1
            if log_path is not None:
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write(f"{src.name} → {plan.dst_name} | "
                             f"{scanner.fmt_size(old_size)} → {scanner.fmt_size(new_size)} | "
                             f"{'; '.join(plan.warnings) or 'OK'}\n")
        except Exception as exc:                      # noqa: BLE001 单个文件失败不中断整批
            failed += 1
            errors.append(f"{plan.src.name}: {exc}")
            logger.warning("执行失败 %s: %s", plan.src.name, exc)
    if progress is not None:
        progress(total, total, "完成")
    return {"total": total, "done": done, "failed": failed, "skipped": skipped,
            "output_dir": str(out_dir), "errors": errors}
