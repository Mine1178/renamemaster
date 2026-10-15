"""核心引擎补充边界用例（v1.9 测评团队）。

这个文件专门装「第一轮回归没盖到、但真实用户会踩」的路径：

① 输出目录根本建不出来（父级是个文件 / 盘符不存在 / 无权限）
   —— 旧实现会抛异常穿透后台线程，界面永久停在「正在执行…」；
② xlsx 对照表里的合并表头、公式单元格、把数据放在第二张工作表；
③ 撤销历史必须能跨进程生效（关掉软件重开还能撤）；
④ 拖放的 DND_FILES 原始串：`{含 空格}`、尾随反斜杠、缺右括号、盘符根；
⑤ 零字节 / 不存在的图片不能让压缩预估把预览搞崩；
⑥ 配置存不下来（父目录被文件占住）时 `save()` 不得抛。

运行：python tests/t_core_extra.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rename_master.config.manager import ConfigManager                 # noqa: E402
from rename_master.core import compressor, history, mapper, renamer    # noqa: E402
from rename_master.core.renamer import RenamePlan, plan_rename         # noqa: E402
from rename_master.ui.dnd import parse_drop_paths                       # noqa: E402

FAILS: list[str] = []
CHECKS = 0


def check(cond: bool, label: str) -> bool:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(label)
        print(f"  [FAIL] {label}")
    return bool(cond)


def _jpeg(w: int = 96, h: int = 72, color=(30, 120, 200), quality: int = 95) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _digest(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


# ------------------------------------------------ ① 输出目录不可用
def test_output_dir_unusable() -> None:
    print("① execute_plan：输出目录建不出来时必须结构化失败（不许抛）")
    work = Path(tempfile.mkdtemp(prefix="rm_outbad_"))
    try:
        srcs = []
        for n in ("a.jpg", "b.jpg"):
            p = work / n
            p.write_bytes(_jpeg())
            srcs.append(p)
        before = {p.name: _digest(p) for p in srcs}

        blocker = work / "blocked"          # 同名文件挡在路径中间 → mkdir 必失败
        blocker.write_bytes(b"x")
        target = blocker / "sub" / "out"
        plans = plan_rename(srcs, "prefix", {"base_name": "x", "digits": 2})

        res = None
        try:
            res = renamer.execute_plan(plans, target)
        except Exception as exc:                                   # noqa: BLE001
            check(False, f"输出目录建不出来时不得抛异常（UI 会永久卡死）：{exc!r}")
        if res is not None:
            check(res["total"] == len(plans), "total 应为计划条数")
            check(res["done"] == 0, "不得有文件被写出")
            check(res["failed"] == len(plans), "整批应记为失败")
            check(bool(res["errors"]), "必须给出可读的原因")
            check(res["done_names"] == [], "done_names 应为空")
            check(str(target) in res["errors"][0] or "目录" in res["errors"][0],
                  f"错误文案应指认是目录问题：{res['errors'][0]!r}")
        check({p.name: _digest(p) for p in srcs} == before, "源目录必须零改动")

        # 空计划同样不该崩
        res2 = renamer.execute_plan([], target)
        check(res2["total"] == 0 and res2["done"] == 0, "空计划应返回全零计数")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------ ② xlsx 对照表
def test_mapper_xlsx_extras() -> None:
    print("② mapper：合并表头 / 公式单元格 / 多工作表")
    try:
        from openpyxl import Workbook
    except ImportError:                                            # pragma: no cover
        print("  （跳过：未安装 openpyxl）")
        return
    work = Path(tempfile.mkdtemp(prefix="rm_mapx_"))
    try:
        # 2.1 表头是 A1:B1 合并单元格
        f1 = work / "merged.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.merge_cells("A1:B1")
        ws["A1"] = "原文件名 / 新文件名"
        ws.append(["a.jpg", "b.jpg"])
        wb.save(str(f1))
        m1 = mapper.load_mapping(f1)
        check(m1 == {"a.jpg": "b.jpg"}, f"合并表头应仍能定位左右列：{m1}")

        # 2.2 数据行里放了公式（openpyxl 无缓存值 → 视为空，不得崩溃、不得瞎猜）
        f2 = work / "formula.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["原文件名", "新文件名"])
        ws["A2"] = "c.jpg"
        ws["B2"] = '=UPPER("d.jpg")'
        wb.save(str(f2))
        m2 = mapper.load_mapping(f2)
        check(isinstance(m2, dict), "公式单元格不得让解析崩掉")
        check(m2.get("c.jpg", None) in (None, ""), f"公式无缓存值时不得编造目标名：{m2}")

        # 2.3 第一张工作表空白、数据在第二张 → 应顺延读到（旧实现只认第一张）
        f3 = work / "second_sheet.xlsx"
        wb = Workbook()
        wb.active.title = "封面"                # 保持空白
        ws2 = wb.create_sheet("对照表")
        ws2.append(["原文件名", "新文件名"])
        ws2.append(["old.jpg", "new.jpg"])
        wb.save(str(f3))
        m3 = mapper.load_mapping(f3)
        check(m3 == {"old.jpg": "new.jpg"}, f"首页空白时应顺延到有数据的页：{m3}")

        # 2.4 第一张有数据 → 不得串到第二张去
        f4 = work / "two_sheets.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["原文件名", "新文件名"])
        ws.append(["x.jpg", "y.jpg"])
        other = wb.create_sheet("另一个")
        other.append(["原文件名", "新文件名"])
        other.append(["p.jpg", "q.jpg"])
        wb.save(str(f4))
        m4 = mapper.load_mapping(f4)
        check(m4 == {"x.jpg": "y.jpg"}, f"首页有数据时不得读其它工作表：{m4}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------ ③ 跨进程撤销
def test_history_cross_process() -> None:
    print("③ history：重启软件后仍能撤销上一批")
    work = Path(tempfile.mkdtemp(prefix="rm_histx_"))
    saved = history.HISTORY_PATH
    try:
        hist_file = work / "history.json"
        history.HISTORY_PATH = hist_file
        out = work / "out"
        out.mkdir()
        produced = out / "a_new.jpg"
        produced.write_bytes(b"payload")

        plans = [RenamePlan(src=work / "a.jpg", dst_name="a_new.jpg")]
        batch = history.record_batch("photo", out, plans, {"done": 1, "done_names": ["a_new.jpg"]})
        check(hist_file.is_file(), "历史应落盘到磁盘")
        raw = json.loads(hist_file.read_text(encoding="utf-8"))
        check(isinstance(raw, list) and raw and raw[-1].get("id") == batch["id"],
              "落盘的历史应可解析且能取到本批")

        script = (
            "import os, sys\n"
            f"sys.path.insert(0, {str(SRC)!r})\n"
            "from pathlib import Path\n"
            "from rename_master.core import history\n"
            "history.HISTORY_PATH = Path(os.environ['RM_TEST_HISTORY_PATH'])\n"
            "b = history.recent_batch()\n"
            "assert b, 'recent_batch 为空'\n"
            "print(history.undo_batch(b)['deleted'])\n"
        )
        env = dict(os.environ)
        env["RM_TEST_HISTORY_PATH"] = str(hist_file)
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  env=env, cwd=str(ROOT), timeout=120)
        except subprocess.TimeoutExpired:                           # pragma: no cover
            check(False, "子进程撤销超时")
            proc = None
        if proc is not None:
            check(proc.returncode == 0,
                  f"子进程撤销应成功：{(proc.stderr or '')[-400:]}")
            check((proc.stdout or "").strip().splitlines()[-1:] == ["1"],
                  f"子进程应报告删除 1 个文件：{proc.stdout!r}")
        check(not produced.exists(), "跨进程撤销后产物应被删除")
    finally:
        history.HISTORY_PATH = saved
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------ ④ 拖放路径解析
def test_drop_parsing() -> None:
    print("④ 拖放路径解析（DND_FILES 原始串）")
    cases: list[tuple[str, list[str]]] = [
        ("{D:\\x y}\\", ["D:\\x y"]),                 # 含空格 + 尾随反斜杠
        ("{D:\\a b}\\ {D:\\c}\\", ["D:\\a b", "D:\\c"]),
        ("D:\\no_space\\f.jpg", ["D:\\no_space\\f.jpg"]),
        ("{D:\\a b", ["D:\\a b"]),                    # 缺右括号：剩下整段当路径
        ("D:\\", ["D:\\"]),                            # 盘符根不得被剥成 D:
        ("", []),
        ("{C:\\带 中文 的空格目录}", ["C:\\带 中文 的空格目录"]),
    ]
    for raw, expected in cases:
        try:
            got = [str(p) for p in parse_drop_paths(raw)]
        except Exception as exc:                                    # noqa: BLE001
            check(False, f"解析 {raw!r} 抛异常：{exc!r}")
            continue
        check(got == expected, f"{raw!r} → {got}（期望 {expected}）")

    # 目录 / 文件混拖：至少不能丢项
    mixed = parse_drop_paths("{D:\\a b}\\ D:\\c.jpg")
    check([str(p) for p in mixed] == ["D:\\a b", "D:\\c.jpg"],
          f"目录+文件混拖应逐项保留：{[str(p) for p in mixed]}")


# ------------------------------------------------ ⑤ 压缩预估降级
def test_compressor_degrade() -> None:
    print("⑤ compressor：零字节 / 缺失文件不得让预览崩")
    work = Path(tempfile.mkdtemp(prefix="rm_cmpx_"))
    try:
        zero = work / "zero.jpg"
        zero.write_bytes(b"")
        size = compressor.estimate_size(zero, 100)
        check(isinstance(size, int) and size >= 0, f"零字节图预估应降级为整数：{size!r}")
        try:
            compressor.compress_to_target(zero.read_bytes(), 100)
            check(False, "零字节输入应抛异常交给调用方兜底")
        except Exception:                                           # noqa: BLE001
            check(True, "")

        missing = work / "nope.jpg"
        check(compressor.estimate_size(missing, 100) == 0,
              "不存在的文件预估应返回 0 而不是抛")

        big = compressor.compress_to_target(_jpeg(1600, 1200, quality=98), 100)
        check(big[:3] == b"\xff\xd8\xff" and len(big) > 0, "100KB 档应返回可用 JPEG")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------ ⑥ 配置保存失败
def test_config_save_failure() -> None:
    print("⑥ config：存不下来也不许抛")
    work = Path(tempfile.mkdtemp(prefix="rm_cfgx_"))
    try:
        blocker = work / "block"
        blocker.write_bytes(b"x")
        cfg = ConfigManager(blocker / "cfg.json")   # 父级是文件 → 永远写不进去
        cfg.set("photo.digits", 5)
        try:
            cfg.save()
            check(True, "")
        except Exception as exc:                                    # noqa: BLE001
            check(False, f"配置保存失败不得抛异常：{exc!r}")
        check(cfg.get("photo.digits") == 5, "内存中的设置应保留")
        check(cfg.get("missing.key", "d") == "d", "缺失键应回落默认值")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    print("核心引擎补充边界用例（v1.9）")
    test_output_dir_unusable()
    test_mapper_xlsx_extras()
    test_history_cross_process()
    test_drop_parsing()
    test_compressor_degrade()
    test_config_save_failure()
    print(f"\n=== 检查 {CHECKS} 项，失败 {len(FAILS)} 项 ===")
    for f in FAILS:
        print("  FAIL:", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
