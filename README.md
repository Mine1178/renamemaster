<p align="center">
  <img src="assets/social-preview.png" width="100%" alt="重命名大师 RenameMaster">
</p>

# 重命名大师 · RenameMaster

> **纯本地**的文件批量命名助手 —— 照片 / PDF / 表格 / 文档一键规范改名，顺带压缩图片，还能管一份门店档案台账。**不联网、不上传、输出隔离、可撤销。**

<p align="center">
  <a href="https://github.com/Mine1178/renamemaster/releases/latest"><img src="https://img.shields.io/badge/Download-v1.11.0-d97706?style=for-the-badge" alt="下载最新版"></a>
  <a href="https://github.com/Mine1178/renamemaster/stargazers"><img src="https://img.shields.io/github/stars/Mine1178/renamemaster?style=social" alt="Stars"></a>
  <a href="https://github.com/Mine1178/renamemaster/issues"><img src="https://img.shields.io/github/issues/Mine1178/renamemaster" alt="Issues"></a>
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-1e293b" alt="Windows 10/11">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/data-local%20only-16a34a" alt="数据不出本机">
</p>

**⬇️ 直接下载**：[最新版 Release](https://github.com/Mine1178/renamemaster/releases/latest) · [安装版 `RenameMaster_Setup.exe`](https://github.com/Mine1178/renamemaster/releases/download/v1.11.0/RenameMaster_Setup.exe) · [便携版 ZIP](https://github.com/Mine1178/renamemaster/releases/download/v1.11.0/RenameMaster_v1.11.0_Portable.zip)

---

## 为什么用它

| 日常痛点 | 重命名大师的做法 |
| --- | --- |
| 一堆照片 / 文档名字乱七八糟 | 统一前缀 + 序号，或按 Excel 对照表一一改名；**执行前先看新旧文件名预览表** |
| 怕把原文件改坏、改错 | 输出到独立文件夹，**绝不原地覆盖**；支持跨重启撤销最近一次批次 |
| 照片太大传不上去 | 二分法调 JPEG 质量，压不到目标再等比缩分辨率；可选保留 EXIF / 备份原图 |
| 门店 / 客户资料散在各个 Excel | 本地 SQLite 台账，Excel 批量导入导出、按编号查重、任意字段模糊搜索 |

**全部处理在本机完成，不需要联网，账号、文件、门店数据都不会离开这台电脑。**

## 界面预览

![v1.11.0 首页](docs/screenshots/v1.11.0/home-preview.png)

> v1.11.0 真实软件截图（为保护隐私，已裁去含本机私有路径的「最近使用」区域）。左侧 9 项导航，包含新增的**门店管理**、**赞助**、**帮助**。

---

## 一、功能说明

| 模块 | 说明 |
| --- | --- |
| 📷 照片命名 | 统一前缀 + 序号；或按 Excel 对照表一一改名；可选图片压缩（1M / 500K / 200K），压不到再等比缩分辨率；保留 EXIF、备份原图可选。 |
| 📕 PDF 命名 | 按正文开头、统一前缀序号或 Excel 对照表批量改名；基于 pypdf 提取正文，自动跳过加密 / 空文本文件。 |
| 📊 表格命名 | 一堆「新建 XLS 表.xlsx」按规则统一取名；支持 `.xlsx` / `.xlsm` / `.xls` / `.csv`，对照表同格式。 |
| 📄 文档命名 | Word / PDF / TXT 取正文开头自动取名，再叠加前缀与序号规则。 |
| 🏪 门店管理 | 本地 SQLite 维护门店档案（编号 / 名称 / 城市 / 地址 / 负责人 / 电话 / 备注），支持新增、编辑、删除、模糊搜索、**Excel 批量导入 / 导出**。 |
| ☕ 赞助 | 微信 / 支付宝收款码，支持点击放大。 |
| ❓ 帮助 | 应用内使用说明，覆盖各功能操作要点。 |

**快捷键**：`Ctrl+O` 选源目录 · `Ctrl+Enter` 预览 / 执行 · `Esc` 关弹窗 / 取消执行；文件夹可直接拖进窗口。

## 二、安装与运行

### 安装版（推荐）
下载 `RenameMaster_Setup.exe` 双击安装，自动生成「重命名大师」快捷方式。

### 便携版
解压 `RenameMaster_v1.11.0_Portable.zip`（内含 `RenameMaster.exe` 与使用说明），直接运行，无需安装、无需联网。

> 系统要求：Windows 10 / 11。安装包与主程序均为单文件分发，不依赖 Python 环境。

## 三、使用方法

1. 左侧导航选择功能页（照片 / PDF / 表格 / 文档），选源文件夹。
2. 设定规则：**统一前缀 + 序号**（前缀、位数、起始值、分隔符）或 **Excel 对照表**（原文件名 → 新文件名，重名与非法字符自动标色）。
3. 点「预览」核对，确认后「开始执行」；结果输出到独立文件夹，随时可撤销。

## 四、门店管理（v1.11.0 新增）

轻量本地台账，适合维护门店 / 客户主数据。

- **新增 / 编辑**：点「＋ 新增门店」或双击表格行；「门店名称」必填。
- **删除**：选中一行或多行后点「🗑 删除选中」（二次确认，不可撤销）。
- **搜索**：顶部搜索框按编号 / 名称 / 城市 / 负责人 / 电话 / 地址模糊筛选。
- **批量导入**：「📥 导入 Excel」自动识别表头（兼容「门店编号 / 编码 / 店名 / 店长 / 手机」等写法）；**按编号查重**——已存在则更新、不存在则新增；文件里没写的列不会清空已有数据。
- **导出备份**：「📤 导出 Excel」导出全部档案。

数据存于本机 `%APPDATA%\RenameMaster\store.db`，**不上传任何服务器**。

## 五、适用场景

- 行政 / 工程资料归档：成批图纸、合同、扫描件按项目编号统一命名；
- 摄影 / 电商：一批照片按「前缀 + 序号」规范取名并压到指定体积；
- 连锁门店 / 网点：维护门店编号、地址、负责人台账，用 Excel 批量更新；
- 任何「文件名不能原样交出去」的场合 —— 输出隔离保证原件零风险。

## 六、赞助与反馈

觉得好用，可在应用内「☕ 赞助」页用微信 / 支付宝请作者喝杯咖啡。

- 问题反馈 / 功能建议：[Issues](https://github.com/Mine1178/renamemaster/issues)
- 更新日志：[CHANGELOG.md](CHANGELOG.md) · 完整手册：[USER_MANUAL.md](USER_MANUAL.md)

## 七、开发、构建与打包

### 环境
Python 3.10+（已验证 3.10.14）；依赖 `Pillow` `openpyxl` `python-docx` `pypdf` `tkinterdnd2` `pyinstaller`，见 `requirements.txt`。

```bash
python -m rename_master.main          # 开发态运行
python tests\run_all.py -v           # 全量回归
```

### 生产打包
```bash
pyinstaller RenameMaster.spec         # 单文件 EXE（已排除 cv2 以减小体积）
iscc installer/rename_master.iss      # Inno Setup 安装包（需 iscc 在 PATH）
python build_manual_pdf.py            # 由 USER_MANUAL.md 生成 docx/html/pdf
python build_social_preview.py        # 生成 GitHub 社交预览图 assets/social-preview.png
```

产物：`dist/RenameMaster.exe`、`dist/RenameMaster_Setup.exe`、便携版 ZIP。

## 八、版本历史

详见 [CHANGELOG.md](CHANGELOG.md)。当前 **v1.11.0**（2026-11-09）：新增门店管理、赞助页、帮助页，重写 README，视觉风格对齐 addressmap-tool。

## 九、许可

仓库当前**未附带 LICENSE 文件**，授权范围以作者说明为准。如需商用、二次分发或二次开发，请先通过 [Issues](https://github.com/Mine1178/renamemaster/issues) 与作者确认。

## 十、目录结构（核心）

```
src/rename_master/
├── main.py                 # 入口
├── ui/
│   ├── app.py              # 主窗口框架（左导航 + 右内容区）
│   ├── theme.py            # 全局配色 / 间距 / 字号规范
│   ├── widgets.py          # Card / PageHeader / 按钮工厂 / Treeview 工具
│   ├── sponsor_common.py   # 收款码资源定位 + 双码布局
│   └── pages/              # home / photo / pdf / spreadsheet / document
│                           # store / sponsor / help / about
├── core/
│   ├── store_db.py         # 门店档案：SQLite + Excel 导入导出
│   └── renamer.py / mapper.py / scanner.py ...   # 改名核心逻辑
└── config/manager.py       # JSON 配置（%APPDATA%\RenameMaster\config.json）
```

推广素材：`assets/social-preview.png`（社交预览）、`docs/screenshots/v1.11.0/`（界面截图）。

---

© 2026 · 重命名大师 · 本地工具，数据不出本机。
