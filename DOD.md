# RenameMaster 交付完成单（Definition of Done）

版本：v1.8 | 交付日期：2026-10-15 | 项目目录：`D:\Desktop\SD\13.Rename`

## 1. 交付物清单

| 交付物 | 路径 | 说明 |
|---|---|---|
| **免安装 EXE** | `dist\RenameMaster.exe` | 单文件，49.5 MB，双击即用、无黑窗 |
| **安装程序** | `dist\RenameMaster_Setup.exe` | 51.2 MB，桌面/开始菜单快捷方式 + 卸载入口 |
| **PDF 使用手册** | `dist\RenameMaster_使用手册.pdf` | 0.5 MB，内容与 v1.4 一致（v1.8 无新功能） |
| Markdown 手册 | `USER_MANUAL.md` / `.docx` / `.html` | 源文件，便于修订 |
| 需求契约 | `PRD.md` | F1-F22 + B1-B10 |
| 验收清单 | `CHECKLIST.md` | A-O 组 |
| 打包脚本 | `build.py` / `RenameMaster.spec` | PyInstaller 可重复打包 |
| 安装脚本 | `installer\rename_master.iss` | Inno Setup 可重新编译（v1.8.0） |
| 手册脚本 | `build_manual_pdf.py` | Word COM 生成 PDF |
| 源码（git） | 主分支 v1.8 归档提交 | `3988733` |

## 2. v1.8 修复内容（全文审查）

| 级别 | 修复 |
|---|---|
| P0 | 水印「平铺密度 grid」布局走错分支 → 改为 `layout in ("tile","grid")` 都走平铺 |
| P0 | 操作栏 destroy 导致切回页面崩溃 → 改 pack_forget 复用 |
| P1 | photo.py `src_dir` 字典 key 重复 → 删除冗余 |
| P1 | advanced.py checkbox 仍用系统样式 → 统一 ☑/☐ font=18 大方框 |
| P2 | 盲水印提取分支空 out_dir 仍 mkdir → 提取时跳过 |

v1.7 已有：水印页 4 布局 2×2 卡片 / 9 位置九宫格 / 真色块 swatch / 弹窗 1100×700 统一 / Treeview 撑满 / checkbox 大方框化。

## 3. 验收结果

| 检查项 | 结果 |
|---|---|
| py_compile 全部源码 | ✅ 0 错误 |
| 水印引擎自测 | ✅ 9 位置 / 5 颜色 / 透明度 / LOGO / 平铺密度 / 印章全过 |
| GUI 无头冒烟（7 页两轮切换） | ✅ SMOKE OK，操作栏存活 |
| 核心引擎真实落盘（3 文件改名） | ✅ done=3/failed=0，非法字符清洗 / 序号唯一性正确 |
| grid vs tile 输出一致性 | ✅ 23632 字节完全相等 |
| EXE 真实启动冒烟 | ✅ 进程存活 6s 无闪退 |
| Inno Setup 编译 | ✅ 10.7 秒成功 |
| 版本号同步 | ✅ app.py=1.8 / iss=1.8.0 |
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
