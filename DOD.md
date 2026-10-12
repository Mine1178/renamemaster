# RenameMaster 交付完成单（Definition of Done）

版本：v1.0 | 交付日期：2026-10-12 | 项目目录：`D:\Desktop\SD\13.Rename`

## 1. 交付物清单

| 交付物 | 路径 | 说明 |
|---|---|---|
| 可执行程序（EXE） | `dist\RenameMaster.exe` | 单文件，19.2 MB，免安装，双击即用 |
| 应用图标 | `assets\rename_master.ico` | 深蓝灰底 + 橙色 ◉，多尺寸 |
| 打包脚本 | `build.py` / `RenameMaster.spec` | 可重复打包 |
| 使用手册 | `USER_MANUAL.md` | 含安装/功能/FAQ/隐私说明 |
| 任务书 | `任务书.md` | 完整需求契约（R1~R6 已拍板） |
| 源码（git） | commit `136f835` | 最终归档 commit |
| 核心测试 | `tests\smoke.py` | 6/6 通过 |

## 2. 验收结果

| 检查项 | 结果 | 验证方式 |
|---|---|---|
| py_compile | ✅ | `python -m compileall src/rename_master` 0 错误 |
| smoke 测试 | ✅ | `python tests/smoke.py` 6/6 通过（造图→plan→execute+压缩→非法字符→mapper→doc_extract） |
| 5 页面无窗口构建 | ✅ | home/photo/spreadsheet/document/about 切换无异常 |
| EXE 真实启动 | ✅ | `dist\RenameMaster.exe` 启动后 5 秒仍存活（PID 33784） |
| 原文件零改动 | ✅ | 输出到 `<源目录>_重命名输出\`，原目录只读 |
| about 页无残留按钮 | ✅ | 切到 about 页底部操作栏全清（commit 525be15 修复） |
| 杀软误报 | ⚠️ 待验 | 未做代码签名，PyInstaller 包偶被误报，属正常 |
| 安装程序（Inno Setup） | ❌ 未做 | v1.0 直接用单文件 EXE，免安装 |
| 快捷键 | ❌ 未做 | v1.0 以鼠标操作为主 |

## 3. 已知缺口（如实写）

- **未做 Inno Setup 安装包**：当前是单文件 EXE 免安装，够用；需要开始菜单/桌面快捷方式/卸载入口时再补。
- **未做撤销功能**：v1.0 不支持一键撤销重命名（输出隔离已经足够安全，原文件不动）。
- **未做缩略图预览**：照片列表只显示文件名+大小，不显示缩略图（v2.0 再加）。
- **未做 OCR 取标题**：文档命名靠正文前 30 字，不做 OCR。
- **未做代码签名**：首次启动 SmartScreen 会提示「未识别应用」，用户点「仍要运行」即可。
- **快捷键未配**：v1.0 全鼠标操作。

## 4. 使用说明（给用户的 3 句话）

1. **双击 `dist\RenameMaster.exe` 即可使用**（首次若被 SmartScreen 拦截，点「更多信息」→「仍要运行」）。
2. **照片批量改名**：左侧「📷 照片命名」→ 选文件夹 → 选模式（统一前缀+序号 / Excel 对照表）→ 选压缩档位 → 开始执行。
3. **原文件绝对安全**：所有结果输出到 `<源目录>_重命名输出\`，原文件一个字节都不会动。详细操作见 `USER_MANUAL.md`。
