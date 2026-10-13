# RenameMaster 交付完成单（Definition of Done）

版本：v1.4 | 交付日期：2026-10-14 | 项目目录：`D:\Desktop\SD\13.Rename`

## 1. 交付物清单

| 交付物 | 路径 | 说明 |
|---|---|---|
| **免安装 EXE** | `dist\RenameMaster.exe` | 单文件，48.5 MB，双击即用、无黑窗 |
| **安装程序** | `dist\RenameMaster_Setup.exe` | 50.3 MB，桌面/开始菜单快捷方式 + 卸载入口 |
| **PDF 使用手册** | `dist\RenameMaster_使用手册.pdf` | 0.46 MB，深蓝封面/目录/蓝底表头，内容与 v1.4 一致 |
| Markdown 手册 | `USER_MANUAL.md` / `.docx` / `.html` | 源文件，便于修订 |
| 需求契约 | `PRD.md` | v1.4，F1-F22 + B1-B10 |
| 验收清单 | `CHECKLIST.md` | v1.4，A-O 组 |
| 打包脚本 | `build.py` / `RenameMaster.spec` | PyInstaller 可重复打包 |
| 安装脚本 | `installer\rename_master.iss` | Inno Setup 可重新编译 |
| 手册脚本 | `build_manual_pdf.py` | Word COM 生成 PDF |
| 源码（git） | 主分支 v1.4 归档提交 | 见 `git log --oneline` 最新记录 |

## 2. v1.4 修复内容（D2W 独立测试审查）

| 编号 | 修复 |
|---|---|
| B1 | 模式二新名不带扩展名误判重复 → 改为基于最终完整文件名判定 |
| B2 | 水印重名自动改名后历史与落盘不一致 → 记录实际落盘名 |
| B3 | 超长文件名 → 预览阶段（>255 字符）即友好报错 |
| B4 | 同名产物静默覆盖 → 自动加 `_1/_2` 后缀并告警 |
| B5 | move + 备份顺序崩溃 → 备份移到写盘前 |
| B6 | PNG 压缩变 JPEG 扩展名错位 → 扩展名同步 |
| B7 | 只读文本可被编辑 → 白名单，仅放行移动/全选/复制 |
| B8 | 平铺水印性能 → 单单元旋转 + 网格复用，1080P 14.9s→0.07s（约 213 倍） |
| B9 | 盲水印坏图临时文件泄漏 → try/finally 清理 |
| B10 | 预览界面冻结 → 窗口立即打开、大小后台异步回填 |

另：打包时排除 OpenCV 视频模块（`opencv_videoio_ffmpeg`，本软件不处理视频），EXE 由 58.3 MB 降至 48.5 MB。

## 3. 验收结果

| 检查项 | 结果 |
|---|---|
| py_compile 全部源码 | ✅ 0 错误 |
| smoke 测试 | ✅ 6/6 |
| test_features4（命名高级功能） | ✅ 26/26 |
| test_ui_features4（四命名页 UI） | ✅ 45/45 |
| test_watermark_page（水印页） | ✅ 9/9 |
| 盲水印嵌入/提取往返 | ✅ 文字正确还原 |
| r1-r10 复现脚本 | ✅ 全部修复并验证 |
| EXE 真实启动冒烟 | ✅ GUI 进程 56MB，未闪退 |
| Inno Setup 编译 | ✅ 9.9 秒成功 |
| 手册 PDF 视觉自检 | ✅ 封面/目录页码/表格无乱码 |
| 原文件零改动 | ✅ 输出隔离 |

## 4. 已知缺口

- 未做代码签名，SmartScreen 首次提示属正常（点「仍要运行」）。
- 高 DPI（125%/150%）缩放未做实测，需在高分屏目检。
- 扫描件 PDF（无文字层）无法提取正文，会保留原名并标注。

## 5. 使用说明

1. **推荐安装包**：双击 `dist\RenameMaster_Setup.exe`，勾选桌面快捷方式，装完启动。
2. **免安装**：直接双击 `dist\RenameMaster.exe`。
3. **原文件绝对安全**：结果统一输出到 `<源目录>_重命名输出\`，源文件零改动；同名自动加后缀。
4. 详细操作见 `dist\RenameMaster_使用手册.pdf`。
