# RenameMaster 文件批量命名助手

Windows 桌面端工具：一键把照片 / 表格 / 文档批量改名，并在改名同时把照片压缩到指定大小（1M / 500K / 200K / 100K / 自定义）。

## 运行

```bat
cd D:\Desktop\SD\13.Rename\src
pip install -r ..\requirements.txt
python -m rename_master.main
```

## 自测

```bat
cd D:\Desktop\SD\13.Rename\src
python ..\tests\smoke.py      :: 输出 SMOKE OK 即通过
```

## 说明

- 默认输出到 `<源目录>_重命名输出`，**绝不原地覆盖原文件**；
- 执行前弹预览表（原文件名 → 新文件名 / 原大小 → 预计新大小 / 状态），确认后才写盘；
- 改名与压缩在后台线程跑，UI 不冻结，可随时取消；
- 操作日志写在 `logs\rename_YYYYMMDD.log`，配置写在 `%APPDATA%\RenameMaster\config.json`。
