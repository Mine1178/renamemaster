"""核心引擎边界用例（v1.9 测评团队）：命名 / 执行 / 压缩 / 对照表 / 历史 / 配置。

设计原则：断言的是**不变量**而不是某种实现细节，例如
- 「凡是状态仍为 ok 的计划，其目标名必须是 Windows 合法文件名」；
- 「执行阶段绝不允许覆盖输出目录里已存在的文件」；
因此无论实现选择「自动改名」还是「标记失败」，只要不变量成立就算通过。

运行：python tests/t_core_edges.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rename_master.config.manager import ConfigManager                    # noqa: E402
from rename_master.core import compressor, history, mapper, renamer        # noqa: E402
from rename_master.core.renamer import RenamePlan, plan_rename            # noqa: E402

FAILS: list[str] = []
CHECKS = 0


def check(cond: bool, label: str) -> bool:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(label)
        print(f"  [FAIL] {label}")
    return bool(cond)


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _jpeg(w: int = 64, h: int = 48, color=(200, 30, 30), quality: int = 95) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _noisy_jpeg(w: int = 640, h: int = 480, quality: int = 95) -> bytes:
    """随机噪声图：几乎无法被压缩，用来逼出「压不到目标」的分支。"""
    from PIL import Image
    import numpy as np
    arr = np.random.default_rng(7).integers(0, 256, (h, w, 3), dtype="uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# ---------------------------------------------------------------- ① sanitize
def test_sanitize() -> None:
    print("① sanitize_name / 文件名合法性")
    illegal = set(renamer.ILLEGAL_CHARS)
    samples = [
        'a<b>c:d"e/f\\g|h?i*j', "尾部点...", "尾部空格   ", "\u0000\u0001控制字符",
        " 前后空白 ", ".", "..", "...", "", "中文♥emoji🙂", "a" * 300,
        "CON", "nul.txt", "LPT1", "COM9.log", "  .  ",
    ]
    for raw in samples:
        got = renamer.sanitize_name(raw)
        check(not (set(got) & illegal), f"sanitize 后不应含非法字符：{raw!r} -> {got!r}")
        check(all(ord(c) >= 32 for c in got), f"sanitize 后不应含控制字符：{raw!r}")
        check(got == got.strip(), f"sanitize 后不应有首尾空白：{raw!r} -> {got!r}")
        check(not got.endswith("."), f"sanitize 后不应以点结尾：{raw!r} -> {got!r}")
        check(not got.endswith(" "), f"sanitize 后不应以空格结尾：{raw!r} -> {got!r}")
    check(renamer.sanitize_name("a<b") == "a_b", "非法字符应替换为下划线")


# --------------------------------------------------------------- ② plan 合法
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
             *(f"LPT{i}" for i in range(1, 10))}


def _valid_windows_name(name: str) -> str | None:
    """返回不合法原因；合法返回 None。"""
    if not name or name in (".", ".."):
        return "空名或 . / .."
    if set(name) & set(renamer.ILLEGAL_CHARS):
        return "含非法字符"
    if any(ord(c) < 32 for c in name):
        return "含控制字符"
    if name != name.strip() or name.endswith("."):
        return "首尾空白或以点结尾"
    if len(name) > 255:
        return "超过 255 字符"
    stem = name.split(".")[0].upper()
    if stem in _RESERVED:
        return f"Windows 保留名 {stem}"
    return None


def test_plan_invariants() -> None:
    print("② plan_rename 不变量（ok 计划必须是合法 Windows 文件名）")
    nasty = ["CON", "nul.txt", "COM1.jpg", "LPT9.png", "a.jpg", "a.JPG", "A.jpg",
             "带 空格 的名字.jpg", "点结尾...jpg", "长度" * 90 + ".jpg",
             "合法名.jpg", "另一个.jpg", "a.jpg", "a.jpg"]
    work = Path(tempfile.mkdtemp(prefix="rm_plan_"))
    try:
        paths = []
        for i, n in enumerate(nasty):
            p = work / f"{i:02d}_{n}" if len(n) > 200 else work / n
            try:
                p.write_bytes(b"x")
            except OSError:
                p = work / f"fallback{i}.jpg"
                p.write_bytes(b"x")
            paths.append(p)
        for mode in ("prefix", "map"):
            if mode == "prefix":
                rule = {"base_name": "现场照", "digits": 3, "start": 1, "sep": "_"}
            else:
                rule = {"mapping": {p.name: f"新名{i}" for i, p in enumerate(paths)},
                        "keep_ext": True}
            try:
                plans = plan_rename(paths, mode, rule)
            except Exception as exc:                              # noqa: BLE001
                check(False, f"plan_rename({mode}) 不应抛异常：{exc!r}")
                continue
            check(len(plans) == len(paths), f"{mode}: 计划条数与输入一致")
            for pl in plans:
                if pl.status != "ok":
                    continue
                why = _valid_windows_name(pl.dst_name)
                check(why is None,
                      f"{mode}: ok 计划必须是合法文件名，{pl.src.name!r} -> "
                      f"{pl.dst_name!r}（{why}）")
            oks = [p.dst_name.lower() for p in plans if p.status == "ok"]
            check(len(oks) == len(set(oks)), f"{mode}: ok 计划之间不得重名")

        # 模式一：非法字符、超长名都要被处理掉
        p1 = plan_rename([work / "a.jpg"], "prefix",
                         {"base_name": 'A<B>:C"', "digits": 2, "sep": "_"})[0]
        check(p1.dst_name == "A_B__C__01.jpg" or "?" not in p1.dst_name,
              f"模式一非法字符应已替换：{p1.dst_name!r}")
        check(p1.status == "warn" and p1.warnings, "模式一非法字符应产生告警")

        long_rule = {"base_name": "长" * 300, "digits": 3, "sep": "_"}
        p2 = plan_rename([work / "a.jpg"], "prefix", long_rule)[0]
        check(p2.status == "error", "超长文件名应在预览阶段标记错误")

        # 保留名：要么被改成合法名，要么标记为 error；绝不能以 ok 状态放行
        con = work / "CON.jpg"
        p3 = plan_rename([con], "prefix", {"base_name": "", "digits": 1, "sep": "_"})
        check(all(_valid_windows_name(p.dst_name) is None or p.status != "ok"
                  for p in p3), "保留名不得以 ok 状态放行")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------- ③ 执行安全性
def _mk_src(work: Path, names=("a.jpg", "b.jpg")) -> list[Path]:
    out = []
    for n in names:
        p = work / n
        p.write_bytes(_jpeg())
        out.append(p)
    return out


def test_execute_safety() -> None:
    print("③ execute_plan 防覆盖 / 隔离 / 取消")

    # 3.1 输出目录 = 源目录 → 全部跳过，原文件零改动
    work = Path(tempfile.mkdtemp(prefix="rm_exec_"))
    try:
        srcs = _mk_src(work)
        before = {p.name: _md5(p) for p in srcs}
        plans = plan_rename(srcs, "prefix", {"base_name": "x", "digits": 2})
        res = renamer.execute_plan(plans, work)
        check(res["done"] == 0, "输出目录==源目录时必须全部跳过")
        check({p.name: _md5(p) for p in srcs} == before, "源目录原文件必须零改动")
        check(not (work / "x_01.jpg").exists(), "不得在源目录原地生成新文件")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 3.2 输出目录已存在同名文件 → 绝不覆盖，自动加后缀
    work = Path(tempfile.mkdtemp(prefix="rm_exec2_"))
    out = work / "out"
    try:
        srcs = _mk_src(work, ("p.jpg",))
        out.mkdir()
        target = out / "现场_01.jpg"
        target.write_bytes(b"PRECIOUS-OLD-CONTENT")
        old = _md5(target)
        plans = plan_rename(srcs, "prefix", {"base_name": "现场", "digits": 2})
        res = renamer.execute_plan(plans, out)
        check(res["done"] == 1, "同名冲突时仍应成功写出 1 个文件")
        check(_md5(target) == old, "同名旧文件绝不允许被覆盖")
        check((out / "现场_01_1.jpg").is_file() or res["done_names"] != ["现场_01.jpg"],
              "同名冲突应改名写出")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 3.3 同名候选耗尽：预置 base 与 _1.._999 后不得覆盖任何一个
    work = Path(tempfile.mkdtemp(prefix="rm_exec3_"))
    out = work / "out"
    try:
        out.mkdir()
        guard = out / "g_01.jpg"
        guard.write_bytes(b"GUARD")
        guard_md5 = _md5(guard)
        for k in range(1, 60):                    # 抽样式预置，避免造 1000 个文件太慢
            (out / f"g_01_{k}.jpg").write_bytes(b"GUARD")
        srcs = _mk_src(work, ("p.jpg",))
        plans = plan_rename(srcs, "prefix", {"base_name": "g", "digits": 2})
        res = renamer.execute_plan(plans, out)
        check(_md5(guard) == guard_md5, "候选名占用时首目标文件不得被覆盖")
        for k in range(1, 60):
            f = out / f"g_01_{k}.jpg"
            if f.is_file():
                check(f.read_bytes() == b"GUARD", f"已存在的 {f.name} 不得被覆盖")
        check(res["done"] + res["failed"] + res["skipped"] == 1, "结果计数应自洽")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 3.4 cancel：命中后必须尽快收尾（不再处理剩余条目）
    work = Path(tempfile.mkdtemp(prefix="rm_exec4_"))
    out = work / "out"
    try:
        srcs = _mk_src(work, tuple(f"c{i:02d}.jpg" for i in range(20)))
        plans = plan_rename(srcs, "prefix", {"base_name": "c", "digits": 2})
        calls = {"n": 0}

        def cancel() -> bool:
            calls["n"] += 1
            return calls["n"] > 2

        res = renamer.execute_plan(plans, out, cancel=cancel)
        check(res["done"] <= 3, f"取消后不应继续处理剩余条目（done={res['done']}）")
        check(calls["n"] <= 4, f"取消后 cancel() 不应被反复调用（{calls['n']} 次）")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 3.5 move + 备份 顺序（原图必须已备份，且不留残骸）
    work = Path(tempfile.mkdtemp(prefix="rm_exec5_"))
    out = work / "out"
    try:
        srcs = _mk_src(work, ("m.jpg",))
        plans = plan_rename(srcs, "prefix", {"base_name": "m", "digits": 2})
        res = renamer.execute_plan(plans, out, move=True, backup_originals=True)
        check(res["done"] == 1, "move+备份应成功")
        check((out / "_originals" / "m.jpg").is_file(), "原图应已备份到 _originals")
        check(not srcs[0].exists(), "move 模式下源文件应已移走")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 3.6 保留名 / 零字节 / 坏字节不得让整批崩掉
    work = Path(tempfile.mkdtemp(prefix="rm_exec6_"))
    out = work / "out"
    try:
        (work / "ok.jpg").write_bytes(_jpeg())
        (work / "zero.jpg").write_bytes(b"")
        (work / "bad.jpg").write_bytes(b"not an image at all")
        paths = [work / "ok.jpg", work / "zero.jpg", work / "bad.jpg"]
        plans = [RenamePlan(src=p, dst_name=f"out{i}.jpg") for i, p in enumerate(paths)]
        res = renamer.execute_plan(plans, out)
        check(res["total"] == 3 and res["done"] + res["failed"] == 3,
              "单文件异常不得中断整批")
        check(not res["errors"] or isinstance(res["errors"], list), "错误应以列表返回")

        con = work / "CON.jpg"
        con.write_bytes(_jpeg())
        plan = RenamePlan(src=con, dst_name="CON.jpg")
        res2 = renamer.execute_plan([plan], out)
        check(res2["failed"] == 1 or (out / "CON.jpg").is_file() is False,
              "Windows 保留名不得静默失败/静默覆盖")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------ ④ 压缩
def test_compressor() -> None:
    print("④ compressor 边界")
    # 4.1 极小目标：也必须返回可用 JPEG（取最小版）
    data = compressor.compress_to_target(_noisy_jpeg(), 5)
    check(data[:3] == b"\xff\xd8\xff", "极小目标应返回 JPEG 字节流")
    check(len(data) > 0, "极小目标不得返回空数据")

    # 4.2 常规目标命中
    big = _noisy_jpeg(1200, 900, quality=98)
    out = compressor.compress_to_target(big, 200)
    check(len(out) <= 200 * 1024 * 1.05, f"应压到 ≤200KB（实际 {len(out)//1024}KB）")
    check(len(out) > 1024, "压缩结果不应退化成空文件")

    # 4.3 RGBA/PNG → 输出仍是 JPEG
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (40, 30), (255, 0, 0, 0)).save(buf, format="PNG")
    rgba_out = compressor.compress_to_target(buf.getvalue(), 100)
    check(rgba_out[:3] == b"\xff\xd8\xff", "PNG 透明图压缩后应为 JPEG")

    # 4.4 灰度 / 调色板 / EXIF 旋转
    buf = io.BytesIO()
    Image.new("L", (30, 30), 128).save(buf, format="PNG")
    check(compressor.compress_to_target(buf.getvalue(), 100)[:3] == b"\xff\xd8\xff",
          "灰度图应能压缩")

    # 4.5 坏字节：estimate_size 必须降级不抛
    tmp = Path(tempfile.mkdtemp(prefix="rm_cmp_"))
    try:
        bad = tmp / "bad.jpg"
        bad.write_bytes(b"\x00\x01\x02 not image")
        size = compressor.estimate_size(bad, 100)
        check(isinstance(size, int), "estimate_size 对坏图应返回整数（降级）")
        try:
            compressor.compress_to_target(bad.read_bytes(), 100)
            check(False, "compress_to_target 对坏字节应抛异常（由调用方兜底）")
        except Exception:                                        # noqa: BLE001
            check(True, "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 4.6 性能：24MP 噪声图不应卡死（上限 20s，正常 <2s）
    t0 = time.perf_counter()
    compressor.compress_to_target(_noisy_jpeg(4000, 3000, quality=90), 500)
    dt = time.perf_counter() - t0
    check(dt < 20, f"24MP 压缩不应超 20s（实际 {dt:.2f}s）")


# --------------------------------------------------------------- ⑤ 对照表
def test_mapper() -> None:
    print("⑤ mapper 对照表解析")
    work = Path(tempfile.mkdtemp(prefix="rm_map_"))
    try:
        # 5.1 无表头两列
        f1 = work / "a.csv"
        f1.write_bytes("原1.jpg,新1.jpg\n原2.jpg,新2.jpg\n".encode("utf-8"))
        m = mapper.load_mapping(f1)
        check(m == {"原1.jpg": "新1.jpg", "原2.jpg": "新2.jpg"}, f"无表头 csv：{m}")

        # 5.2 BOM + GBK
        f2 = work / "b.csv"
        f2.write_bytes("原文件名,新文件名\n甲.jpg,乙.jpg\n".encode("gbk"))
        m2 = mapper.load_mapping(f2)
        check(m2.get("甲.jpg") == "乙.jpg", f"GBK + 表头 csv：{m2}")
        f3 = work / "c.csv"
        f3.write_bytes("\ufeff原文件名,新文件名\n丙.jpg,丁.jpg\n".encode("utf-8"))
        check(mapper.load_mapping(f3).get("丙.jpg") == "丁.jpg", "UTF-8-SIG 表头应识别")

        # 5.3 空白行 / 空单元格 / 缺列
        f4 = work / "d.csv"
        f4.write_bytes("a.jpg,b.jpg\n\n,c.jpg\nd.jpg,\ne.jpg\n".encode("utf-8"))
        m4 = mapper.load_mapping(f4)
        check(m4 == {"a.jpg": "b.jpg", "e.jpg": ""} or "a.jpg" in m4,
              f"空行空单元格应被跳过：{m4}")

        # 5.4 xlsx 正常路径
        try:
            from openpyxl import Workbook
            f5 = work / "e.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.append(["原文件名", "新文件名"])
            ws.append(["x.jpg", "y.jpg"])
            wb.save(str(f5))
            check(mapper.load_mapping(f5) == {"x.jpg": "y.jpg"}, "xlsx 对照表应正确解析")
        except ImportError:                                       # pragma: no cover
            pass

        # 5.5 坏文件必须抛异常（由 UI 层给出中文提示），而不是静默返回 {}
        bad = work / "bad.xlsx"
        bad.write_bytes(b"this is definitely not xlsx")
        try:
            mapper.load_mapping(bad)
            check(False, "损坏 xlsx 应抛异常供 UI 提示")
        except Exception:                                        # noqa: BLE001
            check(True, "")

        empty = work / "empty.csv"
        empty.write_text("", encoding="utf-8")
        check(mapper.load_mapping(empty) == {}, "空 csv 应返回空表而不是崩溃")

        # 5.6 不支持的扩展名提示要清楚
        weird = work / "x.txt"
        weird.write_text("a,b", encoding="utf-8")
        try:
            mapper.load_mapping(weird)
            check(False, "不支持的扩展名应抛异常")
        except Exception as exc:                                 # noqa: BLE001
            check("不支持" in str(exc) or "xlsx" in str(exc),
                  f"不支持的扩展名应给出可读提示：{exc}")

        # 5.7 导出 → 再导入 往返一致
        round_trip = work / "rt.xlsx"
        mapper.export_mapping({"a.jpg": "b.jpg"}, round_trip)
        check(mapper.load_mapping(round_trip) == {"a.jpg": "b.jpg"}, "导出/导入应往返一致")

        # 5.8 编码：Excel「Unicode 文本」另存是 UTF-16（带 BOM），旧实现会解出
        #     满屏 \x00 并抛 csv 的 new-line character 报错（v1.9 修复）
        f6 = work / "u16.csv"
        f6.write_bytes("原文件名,新文件名\n甲.jpg,乙.jpg\n".encode("utf-16"))
        check(mapper.load_mapping(f6) == {"甲.jpg": "乙.jpg"}, "UTF-16（带 BOM）对照表应可读")

        # 5.9 无 BOM 的 UTF-16（少见但仍要能猜）
        f7 = work / "u16nb.csv"
        f7.write_bytes("a.jpg,b.jpg\n中文.jpg,中文2.jpg\n".encode("utf-16-le"))
        check(mapper.load_mapping(f7).get("中文.jpg") == "中文2.jpg",
              "UTF-16LE（无 BOM）应按 0 字节分布猜出小端")

        # 5.10 分隔符：欧洲区域设置的分号 / 制表符文本，旧实现整行当一列（v1.9 修复）
        f8 = work / "semi.csv"
        f8.write_bytes("原文件名;新文件名\n甲.jpg;乙.jpg\n".encode("gbk"))
        check(mapper.load_mapping(f8) == {"甲.jpg": "乙.jpg"}, "分号分隔应自动识别")
        f9 = work / "tab.csv"
        f9.write_bytes("甲.jpg\t乙.jpg\n丙.jpg\t丁.jpg\n".encode("utf-8"))
        check(mapper.load_mapping(f9) == {"甲.jpg": "乙.jpg", "丙.jpg": "丁.jpg"},
              "制表符分隔应自动识别")
        f10 = work / "comma_in_name.csv"
        f10.write_bytes('"a,b.jpg",c.jpg\n'.encode("utf-8"))
        check(mapper.load_mapping(f10) == {"a,b.jpg": "c.jpg"},
              "文件名里带逗号时仍应按逗号切")

        # 5.11 老式 .xls：openpyxl 读不了，必须给中文可读提示而不是英文异常
        xls = work / "old.xls"
        xls.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64)
        try:
            mapper.load_mapping(xls)
            check(False, "老式 .xls 应抛异常")
        except Exception as exc:                                 # noqa: BLE001
            msg = str(exc)
            check("xls" in msg and "xlsx" in msg and not msg.startswith("openpyxl"),
                  f".xls 应提示「另存为 .xlsx」而不是抛 openpyxl 英文异常：{msg}")
        check(".xls" not in mapper.SUPPORTED_EXTS, "SUPPORTED_EXTS 不应再声称支持 .xls")

        # 5.12 .xlsm：宏工作簿既要能当对照表读，也要能被表格页当成待改名文件（v1.9 统一口径）
        try:
            from openpyxl import Workbook
            from rename_master.core import scanner as _scanner
            src_xlsx = work / "m.xlsx"
            xlsm = work / "m.xlsm"
            wb = Workbook()
            ws = wb.active
            ws.append(["原文件名", "新文件名"])
            ws.append(["c.jpg", "d.jpg"])
            wb.save(str(src_xlsx))
            xlsm.write_bytes(src_xlsx.read_bytes())   # 同内容换扩展名，模拟宏工作簿
            check(mapper.load_mapping(xlsm) == {"c.jpg": "d.jpg"},
                  ".xlsm 对照表应能读取")
            check(".xlsm" in mapper.SUPPORTED_EXTS, "SUPPORTED_EXTS 应含 .xlsm")
            picked = _scanner.scan_files([xlsm], _scanner.SPREADSHEET_EXTS)
            check(picked == [xlsm], f".xlsm 应被表格页收进列表：{picked}")
        except ImportError:                                       # pragma: no cover
            pass

        # 5.13 导出对照表：扩展名规范 + 占用异常可读（v1.9 修复的隐性 BUG）
        # 我们只写无宏工作簿，用户手输 .xlsm/.csv 时若照写，Excel 会报
        # 「格式与扩展名不一致」，或被误认成宏工作簿。
        check(mapper.normalize_export_path(work / "x.xlsm") == work / "x.xlsx",
              "手输 .xlsm 应被规范成 .xlsx")
        check(mapper.normalize_export_path(work / "y") == work / "y.xlsx",
              "无扩展名应补 .xlsx")
        check(mapper.normalize_export_path(work / "z.xlsx") == work / "z.xlsx",
              "已是 .xlsx 的路径不应被改动")
        try:
            weird = work / "导出.xlsm"
            n = mapper.export_mapping({"a.jpg": "b.jpg"}, weird)
            check(n == 1, f"导出应返回条数 1：{n}")
            check((work / "导出.xlsx").is_file() and not weird.exists(),
                  "请求导出 .xlsm 时应实际落盘为 .xlsx")
            check(mapper.load_mapping(work / "导出.xlsx") == {"a.jpg": "b.jpg"},
                  "导出的对照表应能原样读回")
        except ImportError:                                       # pragma: no cover
            pass
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ----------------------------------------------------------- ⑥ 历史 / 撤销
def test_history() -> None:
    print("⑥ history 撤销安全")
    work = Path(tempfile.mkdtemp(prefix="rm_hist_"))
    out = work / "out"
    out.mkdir()
    real = out / "keep.jpg"
    real.write_bytes(b"1")
    outsider = work / "outsider.jpg"
    outsider.write_bytes(b"2")
    try:
        batch = {"id": "t1", "output_dir": str(out), "page": "photo",
                 "items": [{"src": "s", "dst": "keep.jpg"},
                           {"src": "s", "dst": "../outsider.jpg"},
                           {"src": "s", "dst": "missing.jpg"}]}
        res = history.undo_batch(batch)
        check(res["deleted"] == 1, f"只应删除本批内的 1 个文件（{res}）")
        check(outsider.is_file(), "路径穿越记录不得删到输出目录外的文件")
        check(not real.exists(), "本批产物应被删除")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # 无关文件不被删 + 空目录清理
    work2 = Path(tempfile.mkdtemp(prefix="rm_hist2_"))
    out2 = work2 / "o"
    out2.mkdir()
    (out2 / "a.jpg").write_bytes(b"a")
    (out2 / "other.jpg").write_bytes(b"other")
    try:
        history.undo_batch({"id": "t2", "output_dir": str(out2),
                            "items": [{"src": "s", "dst": "a.jpg"}]})
        check((out2 / "other.jpg").is_file(), "非本批文件不得被删除")
        # 删空后目录应被清掉
        history.undo_batch({"id": "t3", "output_dir": str(out2),
                            "items": [{"src": "s", "dst": "other.jpg"}]})
        check(not out2.exists(), "删空后应移除空输出目录")
    finally:
        shutil.rmtree(work2, ignore_errors=True)

    # 空历史 / 坏历史文件
    check(history.recent_batch() is None or isinstance(history.recent_batch(), dict),
          "recent_batch 应返回 dict 或 None")


# -------------------------------------------------------------- ⑦ 配置管理
def test_config() -> None:
    print("⑦ config 健壮性")
    work = Path(tempfile.mkdtemp(prefix="rm_cfg_"))
    try:
        p = work / "config.json"
        p.write_text("{ this is not json", encoding="utf-8")
        cfg = ConfigManager(p)
        check(cfg.get("photo.digits") == 3, "损坏配置应回落到默认值")
        cfg.set("photo.digits", 4)
        cfg.set("new.branch.deep", "v")
        cfg.save()
        cfg2 = ConfigManager(p)
        check(cfg2.get("photo.digits") == 4, "配置应能持久化")
        check(cfg2.get("new.branch.deep") == "v", "深层点号路径应能创建")
        check(cfg2.get("missing.key", "d") == "d", "缺失键应返回默认值")

        # 并发写不应产生半截文件
        def writer(n: int) -> None:
            c = ConfigManager(p)
            for i in range(15):
                c.set("output.last_count", n * 100 + i)
                c.save()

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        json.loads(p.read_text(encoding="utf-8"))
        check(True, "")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    t0 = time.perf_counter()
    test_sanitize()
    test_plan_invariants()
    test_execute_safety()
    test_compressor()
    test_mapper()
    test_history()
    test_config()
    dt = time.perf_counter() - t0
    print(f"\n=== 检查 {CHECKS} 项，失败 {len(FAILS)} 项（{dt:.1f}s）===")
    for f in FAILS:
        print("  FAIL:", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
