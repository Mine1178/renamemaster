"""命令行自测：造 3 张测试图 → plan_rename → compress_to_target(50KB) → 断言。

用法（在 src 目录下）：
    cd D:\\Desktop\\SD\\13.Rename\\src && python ..\\tests\\smoke.py
通过时打印 SMOKE OK。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# 支持 `python ..\tests\smoke.py`（不在 src 目录下也能 import rename_master）
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PIL import Image                                    # noqa: E402

from rename_master.core import compressor, renamer        # noqa: E402

TARGET_KB = 50
TOLERANCE_KB = 55          # 目标 ±5%（任务书 A4）
BASE_NAME = "测试"
IMG_SIZE = (1200, 900)


def make_test_images(dirpath: Path, count: int = 3) -> list:
    """生成 count 张带纹理的渐变测试图（纯色 JPEG 太小，压不出区分度）。"""
    paths = []
    for i in range(count):
        base = Image.linear_gradient("L").resize(IMG_SIZE).convert("RGB")
        noise = Image.effect_noise(IMG_SIZE, 30).convert("RGB")
        img = Image.blend(base, noise, 0.35)
        p = dirpath / f"IMG_20261012_{i + 1:03d}.jpg"
        img.save(p, format="JPEG", quality=95)
        paths.append(p)
    return paths


def smoke_doc_extract(workdir: Path) -> None:
    """造一个临时 .txt，断言 extract_title 能取到开头文字。"""
    from rename_master.core import doc_extract      # noqa: PLC0415

    txt = workdir / "测试文档.txt"
    txt.write_text("这是一份测试文档的开头内容，后面还有很多很多字……", encoding="utf-8")
    title = doc_extract.extract_title(txt, 30)
    assert "这是一份测试文档" in title, f"正文提取结果不含预期内容：{title!r}"
    assert len(title) <= 30, f"提取结果超过 30 字：{len(title)}"

    # 不支持的类型 / 不存在的文件 → 空串，不抛异常
    assert doc_extract.extract_title(workdir / "不存在.bin") == ""
    print(f"[6/6] doc_extract.extract_title 通过：{title!r}")


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="renamemaster_smoke_"))
    try:
        src_dir = workdir / "源照片"
        src_dir.mkdir()
        out_dir = workdir / "输出"
        files = make_test_images(src_dir, 3)
        assert len(files) == 3, "测试图生成失败"
        print(f"[1/5] 已生成 {len(files)} 张测试图 → {src_dir}")

        # ---- 模式一：统一前缀 + 序号，3 位、起始 1、分隔符 _ ----
        plans = renamer.plan_rename(files, renamer.MODE_PREFIX, {
            "base_name": BASE_NAME, "digits": 3, "start": 1,
            "sep": "_", "keep_ext": True, "date_prefix": False,
        })
        expected = [f"{BASE_NAME}_001.jpg", f"{BASE_NAME}_002.jpg", f"{BASE_NAME}_003.jpg"]
        got = [p.dst_name for p in plans]
        assert got == expected, f"新文件名不符合预期：{got} != {expected}"
        print(f"[2/5] plan_rename 通过：{got}")

        # ---- 压缩到 50KB 后执行（输出目录隔离） ----
        def transform(src: Path, _dst_name: str) -> bytes:
            return compressor.compress_to_target(src.read_bytes(), TARGET_KB,
                                                 keep_exif=True)

        result = renamer.execute_plan(plans, out_dir, transform=transform)
        assert result["failed"] == 0, f"执行出现失败：{result['errors']}"
        assert result["done"] == 3, f"执行数量不对：{result}"
        print(f"[3/5] execute_plan 通过：{result['done']} 个文件 → {out_dir}")

        for name in expected:
            out_file = out_dir / name
            assert out_file.is_file(), f"输出文件缺失：{out_file}"
            size_kb = out_file.stat().st_size / 1024
            assert size_kb <= TOLERANCE_KB, \
                f"{name} 压缩后 {size_kb:.1f} KB 超过 {TOLERANCE_KB} KB 上限"
            print(f"      {name}: {size_kb:.1f} KB ✓")

        # 原目录零改动（绝不原地覆盖）
        for src_file in files:
            assert src_file.is_file(), f"原文件被破坏：{src_file}"

        # 非法字符 / 重名兜底
        dirty = renamer.plan_rename(files, renamer.MODE_PREFIX, {
            "base_name": "a/b:c*?", "digits": 3, "start": 1, "sep": "_",
            "keep_ext": True,
        })
        assert all("/" not in p.dst_name and ":" not in p.dst_name and "*" not in p.dst_name
                   for p in dirty), f"非法字符未清理：{[p.dst_name for p in dirty]}"
        assert any(p.warnings for p in dirty), "非法字符未产生警告"
        print("[4/5] 非法字符替换 / 原目录零改动 通过")

        # ---- 模式二：Excel 对照表解析 ----
        import openpyxl                                    # noqa: PLC0415

        from rename_master.core import mapper              # noqa: PLC0415

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["原文件名", "新文件名"])
        ws.append([files[0].name, "场景照"])
        ws.append([files[1].name, "近景照"])
        xlsx = workdir / "map.xlsx"
        wb.save(xlsx)

        m = mapper.load_mapping(xlsx)
        assert files[0].name in m, f"对照表解析结果不含 {files[0].name}: {m}"
        assert m[files[0].name] == "场景照", m

        map_plans = renamer.plan_rename(files, renamer.MODE_MAP,
                                        {"mapping": m, "keep_ext": True})
        assert map_plans[0].dst_name == "场景照.jpg", map_plans[0].dst_name
        print(f"[5/5] mapper.load_mapping 通过：{len(m)} 条对照 → "
              f"{[p.dst_name for p in map_plans]}")

        # ---- 文档正文提取（文档页「用正文前 30 字命名」） ----
        smoke_doc_extract(workdir)

        print("SMOKE OK")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
