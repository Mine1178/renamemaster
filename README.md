# RenameMaster 文件批量命名助手

Windows 桌面端工具：一键把照片 / 表格 / 文档批量改名，并在改名同时把照片压缩到指定大小（1M / 500K / 200K / 100K / 自定义）。

当前版本：v1.9（2026-10-15）

## 运行

```bat
cd D:\Desktop\SD\13.Rename\src
pip install -r ..\requirements.txt
python -m rename_master.main
```

也可以直接双击项目根目录的 `run.bat` 一键启动。

## 自测（v1.9）

```bat
cd D:\Desktop\SD\13.Rename
python tests\run_all.py -v    :: 13 个用例一键全量回归，末行输出「合计 13 个用例：通过 13，失败 0」
```

单跑某一项：`python tests\smoke.py`、`python tests\t_core_edges.py`、`python tests\t_pkg_exe.py`（打包产物真实启动冒烟）等。

## 说明

- 默认输出到 `<源目录>_重命名输出`，**绝不原地覆盖原文件**；
- 执行前弹预览表（原文件名 → 新文件名 / 原大小 → 预计新大小 / 状态），确认后才写盘；
- 改名与压缩在后台线程跑，UI 不冻结，可随时取消；
- 操作日志写在 `logs\rename_YYYYMMDD.log`，配置写在 `%APPDATA%\RenameMaster\config.json`。
