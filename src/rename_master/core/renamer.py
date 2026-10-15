"""重命名引擎：干跑生成计划（不碰磁盘） + 真正执行（输出目录隔离）。

任务书 §5.1：
1. `plan_rename()` 只在内存里算新名，做重名 / 非法字符校验，**不写盘**；
2. `execute_plan()` 把结果写到**独立输出目录**，默认复制（原目录零改动，CHECKLIST E1）；
   只有当调用方显式 `move=True` 时才用 shutil.move（原地改名，需调用方二次确认）。
"""
from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from rename_master.core import naming_vars, scanner

logger = logging.getLogger(__name__)

# 日志目录：<项目根>/logs（与任务书 §3.4 一致），不存在时自动创建
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"

# Windows / macOS 文件名非法字符（任务书 §3.2：自动替换为 _ 并标黄）
ILLEGAL_CHARS = '\\/:*?"<>|'
_ILLEGAL_TABLE = str.maketrans({ch: "_" for ch in ILLEGAL_CHARS})

# 重名自动追加的后缀序列：_b、_c …（任务书 §3.1）
_CONFLICT_SUFFIXES = [chr(c) for c in range(ord("b"), ord("z") + 1)]

# Windows 保留设备名：带扩展名同样非法（NUL.txt 依旧指向 NUL 设备，写盘会失败或写进设备）
_RESERVED_NAMES = {"con", "prn", "aux", "nul",
                   *(f"com{i}" for i in range(1, 10)),
                   *(f"lpt{i}" for i in range(1, 10))}

MODE_PREFIX = "prefix"   # 模式一：统一前缀 + 序号
MODE_MAP = "map"         # 模式二：一一对照


def is_reserved_name(name: str) -> bool:
    """是否为 Windows 保留设备名（CON/PRN/AUX/NUL/COM1-9/LPT1-9，含 `NUL.txt` 写法）。"""
    base = str(name or "").split(".")[0].strip().lower()
    return base in _RESERVED_NAMES


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
    base = naming_vars.render_template(src, str(rule.get("base_name") or "").strip())
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


def _sort_paths(paths: Sequence[Path], sort_by: str, desc: bool) -> List[Path]:
    """按排序键决定序号顺序（不改原始显示，只影响本次计划的序号）。"""
    sort_by = str(sort_by or "").lower()
    if sort_by not in ("name", "mtime", "size", "exif"):
        return list(paths)

    def _key(p: Path):
        try:
            stt = p.stat()
        except OSError:
            return ""
        if sort_by == "name":
            return p.name.lower()
        if sort_by == "size":
            return stt.st_size
        if sort_by == "exif":
            shot = naming_vars.exif_datetime(p)
            return shot.timestamp() if shot else stt.st_mtime
        return stt.st_mtime  # mtime

    try:
        return sorted(paths, key=_key, reverse=desc)
    except (OSError, TypeError):
        return list(paths)


def _apply_find_replace(stem: str, rule: Dict, plan: RenamePlan) -> str:
    """对主名（不含扩展名）做查找替换；支持正则捕获组。正则非法时退回原串。"""
    find = str(rule.get("find") or "")
    if not find:
        return stem
    repl = str(rule.get("repl") if rule.get("repl") is not None else "")
    try:
        if bool(rule.get("use_regex", False)):
            result = re.sub(find, repl, stem)
        else:
            result = stem.replace(find, repl)
    except re.error as exc:
        plan.add_warning(f"正则表达式有误，已忽略替换：{exc}")
        return stem
    return result


def plan_rename(files: Iterable[os.PathLike | str], mode: str, rule: Dict) -> List[RenamePlan]:
    """生成改名计划（**纯内存，不写盘**）。

    mode:
      - `"prefix"`：rule = {base_name, digits, start, sep, keep_ext, date_prefix, date}
      - `"map"`   ：rule = {mapping: {原文件名: 新文件名}, keep_ext: bool}

    重名自动追加 `_b`/`_c`…；非法字符替换为 `_`；模式二未匹配的文件保持原名。
    """
    rule = dict(rule or {})
    paths = [Path(f) for f in (files or [])]
    paths = _sort_paths(paths, str(rule.get("sort_by", "")),
                        bool(rule.get("sort_desc", False)))
    mapping: Dict[str, str] = dict(rule.get("mapping") or {}) if mode == MODE_MAP else {}
    keep_ext = bool(rule.get("keep_ext", True))

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
        # 查找替换：只作用于主名（扩展名保持），支持正则捕获组
        f_stem, f_ext = os.path.splitext(plan.dst_name)
        replaced = _apply_find_replace(f_stem, rule, plan)
        if replaced != f_stem:
            plan.dst_name = f"{replaced}{f_ext}"
        if not plan.dst_name or plan.dst_name.startswith("."):
            plan.mark_error("新文件名为空")
            plans.append(plan)
            continue
        # 文件名过长：Windows 文件名上限 255 字符，提前拦截（否则执行阶段 WinError 123）
        if len(plan.dst_name) > 255:
            plan.mark_error(f"文件名过长（{len(plan.dst_name)} 字符，上限 255），请缩短基础名")
            plans.append(plan)
            continue
        # Windows 保留设备名：CON / NUL / aux.jpg 之类系统建不出来（或会写进设备），提前拦截
        if is_reserved_name(plan.dst_name):
            plan.mark_error(f"“{plan.dst_name}”是 Windows 保留设备名，系统无法创建，请改名")
            plans.append(plan)
            continue

        # 重名冲突：基于「最终完整文件名」判定（扩展名已补齐）
        # - 模式二（对照表）：两个文件落到同一新名是对照表错误 → 禁止执行，提示回去修表
        # - 模式一（前缀+序号）：序号本应唯一；万一冲突自动追加 _b/_c…
        if plan.dst_name.lower() in used:
            if mode == MODE_MAP:
                plan.mark_error("对照表新名重复，禁止执行")
                plans.append(plan)
                continue
            stem, ext = os.path.splitext(plan.dst_name)
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


def _sniff_ext(data: bytes) -> str:
    """按字节头探测图片格式，返回扩展名（压缩后实际格式可能与原扩展名不同）。"""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:2] == b"BM":
        return ".bmp"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ""


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
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # 输出目录建不出来（路径含非法字符 / 父级是个文件 / 无写权限 / 盘符不存在）。
        # 这里绝不能往外抛：四个页面都在后台线程里直接调用本函数，异常会穿透线程，
        # 界面永远停在「正在执行…」且按钮全灰，用户只能强杀进程（v1.9 修复）。
        logger.error("无法创建输出目录 %s: %s", out_dir, exc)
        return {"total": len(plans), "done": 0, "failed": len(plans), "skipped": 0,
                "cancelled": False, "output_dir": str(out_dir),
                "errors": [f"无法创建输出目录“{out_dir}”：{exc}"],
                "done_names": []}
    log_path = _open_log()
    total = len(plans)
    done = failed = skipped = 0
    errors: List[str] = []
    done_names: List[str] = []
    out_resolved = out_dir.resolve()

    cancelled = False
    for i, plan in enumerate(plans):
        if cancel is not None and cancel():
            # 用户点了「取消」：立刻收尾，剩余条目不再处理（也不写盘），全部计入 skipped。
            # 旧实现命中后只 continue，仍会把整批走完 —— 取消 1 万张照片要等到底（v1.9 修复）。
            cancelled = True
            skipped += total - i
            break
        if progress is not None:
            progress(i, total, plan.src.name)
        try:
            src = Path(plan.src)
            if plan.blocked:
                failed += 1
                errors.append(f"{plan.src.name}: {plan.note}")
                continue
            # 保留设备名兜底：预览阶段已拦截，但对照表/外部调用仍可能塞进来。
            # 一旦 name 是 CON/NUL/COM1…，写盘会命中设备（数据丢失）或被系统拒绝，
            # 这里统一按失败记账，绝不静默写出（v1.9 修复）。
            if is_reserved_name(plan.dst_name):
                raise ValueError(
                    f"“{plan.dst_name}”是 Windows 保留设备名，拒绝写出")
            src_dir = src.resolve().parent
            old_size = scanner.file_size(src)

            # ① 备份原文件：必须在 move 之前做（move 后 src 已不在，否则 WinError 2）
            if backup_originals:
                bak_dir = out_dir / "_originals"
                bak_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(bak_dir / src.name))

            # ② 先做变换（压缩等），实际格式可能变化（PNG 透明图→JPEG）→ 同步扩展名
            data = transform(src, plan.dst_name) if transform else None
            if data is not None:
                sniffed = _sniff_ext(data)
                if sniffed and Path(plan.dst_name).suffix.lower() != sniffed:
                    plan.dst_name = Path(plan.dst_name).stem + sniffed
                    plan.add_warning(f"压缩后格式变为 {sniffed}，扩展名已同步")

            # ③ 输出目录 / 防覆盖（基于最终名）
            dst = out_dir / plan.dst_name
            try:
                same_file = dst.resolve() == src.resolve()
            except OSError:
                same_file = False

            if move:
                if same_file:
                    # 原地改名但新旧同名：本来不需要动，按"跳过"记账（绝不写盘）
                    skipped += 1
                    plan.note = "源与目标同名，无需改名"
                    continue
                if dst.exists():
                    # 原地改名更要守住：目标名已被占用 → 拒绝覆盖（无论是不是同一目录）
                    raise FileExistsError(f"目标已存在，拒绝覆盖：{dst.name}")
            elif src_dir == out_resolved:
                failed += 1
                errors.append(f"{plan.src.name}: 输出目录与源目录相同，已跳过（拒绝原地覆盖）")
                continue
            elif not same_file and dst.exists():
                # copy / transform：目标已存在 → 自动加 _1/_2，不覆盖
                stem_d, ext_d = dst.stem, dst.suffix
                for k in range(1, 1000):
                    cand = dst.with_name(f"{stem_d}_{k}{ext_d}")
                    if not cand.exists():
                        dst = cand
                        break
                else:
                    # 1~999 全部被占用：绝不能退回原名写盘（会覆盖别人的文件）→ 该条报失败
                    raise FileExistsError(
                        f"目标目录已有 999 个同名文件，无法自动改名：{dst.name}")
                plan.dst_name = dst.name
                plan.add_warning("目标已存在，已自动改名避免覆盖")

            # ④ 写盘
            if data is not None:
                dst.write_bytes(data)
                new_size = len(data)
            elif move:
                shutil.move(str(src), str(dst))
                new_size = scanner.file_size(dst)
            else:
                shutil.copy2(str(src), str(dst))
                new_size = scanner.file_size(dst)
            plan.new_size = new_size
            done += 1
            done_names.append(plan.dst_name)
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
            "cancelled": cancelled, "output_dir": str(out_dir),
            "errors": errors, "done_names": done_names}
