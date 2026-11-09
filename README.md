# 重命名大师（RenameMaster）

> 本地运行、数据不出本机的 **文件批量命名助手** —— 照片 / PDF / 表格 / 文档一键规范改名，附带门店档案管理。

[![版本](https://img.shields.io/badge/版本-1.11.0-blue)](CHANGELOG.md)
[![平台](https://img.shields.io/badge/平台-Windows%2010%2F11-lightgrey)](USER_MANUAL.md)
[![协议](https://img.shields.io/badge/协议-本地工具-green)]()

---

## 一、项目简介

重命名大师是一款 **纯本地** 的批量改名工具，解决以下日常痛点：

- 一堆照片 / PDF / Excel / Word 文档需要按统一规则快速规范命名；
- 想按 Excel 对照表把文件一一对应改名；
- 照片体积太大需要顺带压缩；
- 门店、客户等主数据散落在不同文件里，缺少一个轻量、可检索的本地台账。

所有处理都在本机完成，**不会上传任何文件或数据**。

---

## 二、功能说明

| 模块 | 说明 |
| --- | --- |
| 📷 照片命名 | 统一前缀 + 序号；或按 Excel 对照表一一改名；可选图片压缩（1M / 500K / 200K），压不到再等比缩分辨率；保留 EXIF、备份原图可选。 |
| 📕 PDF 命名 | 按正文开头、统一前缀序号或 Excel 对照表批量改名；基于 pypdf 提取正文，自动跳过加密 / 空文本文件。 |
| 📊 表格命名 | 一堆「新建 XLS 表.xlsx」按规则统一取名；支持 `.xlsx` / `.xlsm` / `.xls` / `.csv`，对照表同格式。 |
| 📄 文档命名 | Word / PDF / TXT 取正文开头自动取名，再叠加前缀与序号规则。 |
| 🏪 门店管理 | 本地 SQLite 维护门店档案（编号 / 名称 / 城市 / 地址 / 负责人 / 电话 / 备注），支持新增、编辑、删除、模糊搜索、**Excel 批量导入 / 导出**。 |
| ☕ 赞助 | 微信 / 支付宝收款码，支持点击放大。 |
| ❓ 帮助 | 应用内使用说明，与各功能操作要点。 |

**通用安全机制**：输出默认隔离到新文件夹，绝不原地覆盖；执行前可预览新旧文件名；提供操作撤销（跨重启有效）。

---

## 三、安装与运行

### 方式一：安装包（推荐）
下载 `RenameMaster_Setup.exe`，双击按向导安装，开始菜单 / 桌面生成「重命名大师」快捷方式。

### 方式二：便携版
解压 `RenameMaster_v1.11.0_Portable.zip`（内含 `RenameMaster.exe` 与使用说明），直接运行 `RenameMaster.exe` 即可，无需安装。

> 系统要求：Windows 10 / 11，无需联网。

---

## 四、使用方法

1. 在左侧导航选择要处理的功能页（照片 / PDF / 表格 / 文档）。
2. 选择源文件夹（也可把文件夹直接拖进窗口）。
3. 设定命名规则：
   - **统一前缀 + 序号**：填写前缀、序号位数、起始值、分隔符，是否保留扩展名。
   - **Excel 对照表**：准备一列原文件名、一列目标文件名（或按编号映射），导入后一一对应改名；重名与非法字符会自动标色提示。
4. 点「预览」核对新旧文件名，确认无误后点「开始执行」。
5. 结果默认输出到独立文件夹，可随时在「关于 / 撤销」中回滚。

**快捷键**：`Ctrl+O` 选源目录 · `Ctrl+Enter` 预览 / 执行 · `Esc` 关弹窗 / 取消执行。

---

## 五、门店管理（v1.11.0 新增）

门店管理是一个**轻量本地台账**，适合维护门店 / 客户主数据，并可与文件管理配合。

- **新增 / 编辑**：点「＋ 新增门店」或在表格中双击某行；带 `*` 的「门店名称」为必填。
- **删除**：选中一行或多行，点「🗑 删除选中」（不可撤销，会二次确认）。
- **搜索**：顶部搜索框按任意字段（编号 / 名称 / 城市 / 负责人 / 电话 / 地址）模糊筛选。
- **批量导入**：点「📥 导入 Excel」，选择 `.xlsx` / `.xlsm` 文件。程序按表头自动识别列（兼容「门店编号 / 编码 / 店名 / 店长 / 手机」等同义词）；**按门店编号查重**——编号已存在则更新、不存在则新增；只填写的列不会清空该记录其它字段。
- **导出备份**：点「📤 导出 Excel」导出当前全部档案。

数据存放于本机 `%APPDATA%\RenameMaster\store.db`，**不上传任何服务器**。

---

## 六、赞助

如果这套工具帮到了你，欢迎在「赞助」页用微信 / 支付宝请作者喝杯咖啡。工具完全本地运行，你的文件与门店数据不会离开本机。

---

## 七、开发、构建与打包

### 环境
- Python 3.10+（建议系统解释器，已验证 3.10.14）
- 依赖：`Pillow` `openpyxl` `python-docx` `pypdf` `tkinterdnd2` `pyinstaller`
- 安装依赖：`pip install -r requirements.txt`（若仓库未附，可按上面列表安装）

### 开发运行
```bash
python -m rename_master.main
# 或
python src/rename_master/main.py
```

### 打包（生产）
```bash
# 1) 生成单文件 EXE（已排除 cv2 的视频 I/O ffmpeg DLL 以减小体积）
pyinstaller RenameMaster.spec

# 2) 生成安装包（需 Inno Setup，iscc 在 PATH）
iscc installer/rename_master.iss
```
产物：`dist/RenameMaster.exe`（主程序）与 `dist/RenameMaster_Setup.exe`（安装包）。

### 使用手册再生成
```bash
python build_manual_pdf.py   # 由 USER_MANUAL.md 生成 docx/html/pdf（需本机安装 Word 以转 PDF）
```

### 自测
```bat
cd D:\Desktop\SD\13.Rename
python tests\run_all.py -v    :: 全量回归，末行输出通过 / 失败统计
```

---

## 八、版本历史

详见 [CHANGELOG.md](CHANGELOG.md)。当前版本 **v1.11.0**（2026-11-09）：新增门店管理、赞助页、帮助页，整体视觉风格对齐 addressmap-tool。

---

## 九、目录结构（核心）

```
src/rename_master/
├── main.py                 # 入口
├── ui/
│   ├── app.py              # 主窗口框架（左导航 + 右内容区）
│   ├── theme.py            # 全局配色 / 间距 / 字号规范
│   ├── widgets.py          # Card / PageHeader / 按钮工厂 / Treeview 工具
│   ├── sponsor_common.py   # 收款码资源定位 + 双码布局（about/赞助页共用）
│   └── pages/              # 各功能页（home/photo/pdf/spreadsheet/document/store/sponsor/help/about）
├── core/
│   ├── store_db.py         # 门店档案：SQLite + Excel 导入导出
│   ├── renamer.py / mapper.py / scanner.py ...  # 改名核心逻辑
└── config/manager.py       # JSON 配置（%APPDATA%\RenameMaster\config.json）
```

---

© 2026 · 重命名大师 · 本地工具，数据不出本机。
