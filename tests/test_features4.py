"""第一梯队 4 项功能端到端验证：撤销 / 查找替换(含正则) / 排序 / 日期变量。

用真实临时文件 + 真实执行 + 真实删除，全部断言通过才打印 ALL PASS。
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rename_master.core import history, naming_vars, renamer  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def make_files(root, names):
    files = []
    for i, nm in enumerate(names):
        p = Path(root) / nm
        data = b"x" * (100 + i * 50)
        p.write_bytes(data)
        # 让修改时间彼此不同，便于排序验证
        ts = time.time() - (len(names) - i) * 1000
        os.utime(p, (ts, ts))
        files.append(p)
    return files


def base_rule(**kw):
    rule = {"base_name": "照片", "digits": 3, "start": 1, "sep": "_",
            "keep_ext": True}
    rule.update(kw)
    return rule


print("== ① 日期 / 变量 ==")
tmp = tempfile.mkdtemp(prefix="rm_var_")
files = make_files(tmp, ["a.jpg", "b.jpg", "c.jpg"])
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="{parent}_巡检_{date}"))
check("父文件夹变量 {parent}", Path(tmp).name in plans[0].dst_name,
      plans[0].dst_name)
check("今天日期变量 {date}", time.strftime("%Y%m%d") in plans[0].dst_name,
      plans[0].dst_name)

plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="{mtime}_拍"))
mt = time.strftime("%Y%m%d", time.localtime(files[0].stat().st_mtime))
check("修改时间变量 {mtime}", plans[0].dst_name.startswith(mt),
      plans[0].dst_name)

plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="{exif}_拍"))
check("无EXIF时 {exif} 回退修改时间", plans[0].dst_name.startswith(mt),
      plans[0].dst_name)
check("无EXIF文件 exif_datetime 返回 None",
      naming_vars.exif_datetime(files[0]) is None)

plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="{stem}_新"))
check("原名变量 {stem}", plans[0].dst_name.startswith("a_新"),
      plans[0].dst_name)

print("== ② 排序 ==")
# 文件名升序：a b c → 序号 001 002 003
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", sort_by="name", sort_desc=False))
names_asc = [p.dst_name for p in plans]
check("文件名升序顺序", names_asc[0].startswith("P_001") and
      names_asc[1].startswith("P_002") and names_asc[2].startswith("P_003"),
      names_asc)
# 文件名降序：c b a
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", sort_by="name", sort_desc=True))
names_desc = [p.dst_name for p in plans]
check("文件名降序首文件为 c", plans[0].src.name == "c.jpg" and
      names_desc[0].startswith("P_001"), names_desc)

# 按大小排序：a(100) < b(150) < c(200)
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", sort_by="size", sort_desc=False))
check("按大小升序首文件为 a", plans[0].src.name == "a.jpg",
      [p.src.name for p in plans])
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", sort_by="size", sort_desc=True))
check("按大小降序首文件为 c", plans[0].src.name == "c.jpg",
      [p.src.name for p in plans])

# 按修改时间排序
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", sort_by="mtime", sort_desc=False))
check("按修改时间升序", plans[0].src.name == "a.jpg",
      [p.src.name for p in plans])

print("== ③ 查找替换（普通 + 正则） ==")
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="老照片", find="老", repl="新"))
check("普通文本替换", all("新照片" in p.dst_name for p in plans),
      [p.dst_name for p in plans])
check("替换后被替换串消失", all("老照片" not in p.dst_name for p in plans))

# 正则：去掉数字？基础名无数字，用 stem 匹配。这里匹配序号 (\d+) 并加 P
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", sep="", find=r"(\d{3})", repl=r"#\1",
              use_regex=True))
check("正则捕获组替换", all("#" in p.dst_name for p in plans),
      [p.dst_name for p in plans])

# 非法正则：退回原名并给 warning
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", find=r"([0-9", repl="x", use_regex=True))
check("非法正则安全降级", all(p.status in ("ok", "warn") for p in plans),
      [p.status for p in plans])
check("非法正则产生警告", any("正则" in w for p in plans for w in p.warnings),
      [p.warnings for p in plans])

# 替换为空：主名保留部分（不会清空扩展名）
plans = renamer.plan_rename(
    files, renamer.MODE_PREFIX,
    base_rule(base_name="P", find="P", repl=""))
check("替换为空不报错", all(p.status in ("ok", "warn") for p in plans),
      [(p.dst_name, p.status) for p in plans])

print("== ④ 撤销 Undo ==")
run_tmp = tempfile.mkdtemp(prefix="rm_run_")
work = make_files(run_tmp, ["x1.jpg", "x2.jpg", "x3.jpg"])
out_dir = Path(run_tmp) / "out"
plans = renamer.plan_rename(work, renamer.MODE_PREFIX,
                            base_rule(base_name="导出"))
result = renamer.execute_plan(plans, out_dir)
check("执行成功 3 个", result["done"] == 3, result)
created = [out_dir / d for d in result["done_names"]]
check("生成文件真实存在", all(p.is_file() for p in created),
      [str(p) for p in created])

batch = history.record_batch("spreadsheet", out_dir, plans, result)
check("最近批次已记录", batch is not None and len(batch["items"]) == 3,
      batch)
check("批次记录页面", batch and batch.get("page") == "spreadsheet",
      batch and batch.get("page"))

undo = history.undo_batch(batch)
check("撤销删除 3 个文件", undo["deleted"] == 3, undo)
check("撤销后文件已不存在", all(not p.is_file() for p in created))
check("撤销后历史移除", history.recent_batch() is None or
      history.recent_batch().get("id") != batch.get("id"))
check("空输出目录已清理", not out_dir.exists(), str(out_dir))

# 再次撤销无历史
check("无历史时返回 None", history.recent_batch() is None or
      history.recent_batch().get("id") != batch.get("id"))

print()
print(f"=== 结果：{PASS} 通过，{FAIL} 失败 ===")
sys.exit(1 if FAIL else 0)
