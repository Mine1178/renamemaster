# RenameMaster 交付完成单（Definition of Done）

版本：v1.9 | 交付日期：2026-10-15 | 项目目录：`D:\Desktop\SD\13.Rename`

## 1. 交付物清单

| 交付物 | 路径 | 说明 |
|---|---|---|
| **免安装 EXE** | `dist\RenameMaster.exe` | 单文件，51,634,208 B（49.2 MiB），双击即用、无黑窗 |
| **安装程序** | `dist\RenameMaster_Setup.exe` | 53,331,110 B（50.9 MiB），桌面/开始菜单快捷方式 + 卸载入口 |
| **PDF 使用手册** | `dist\RenameMaster_使用手册.pdf` | 495,479 B，内容与 v1.9 一致（封面 + 目录页码 + 截图 + FAQ） |
| Markdown 手册 | `USER_MANUAL.md` / `.docx` / `.html` | 源文件，便于修订 |
| 需求契约 | `PRD.md` | F1-F23 + B1-B33 |
| 验收清单 | `CHECKLIST.md` | A-Q 组 |
| 打包脚本 | `build.py` / `RenameMaster.spec` | PyInstaller 可重复打包 |
| 安装脚本 | `installer\rename_master.iss` | Inno Setup 可重新编译（1.9.0 / 1.9.0.0） |
| 手册脚本 | `build_manual_pdf.py` | Word COM 生成 PDF |
| 回归入口 | `tests\run_all.py` / `run.bat` | 13 用例一键全量回归 / 一键启动 |
| 源码（git） | v1.9 归档提交 | 见下方「归档」 |

## 2. v1.9 修复内容（全维度深度测试）

### 本轮新增（B27~B33）

| 级别 | 修复 |
|---|---|
| P1 | `core/mapper.py` CSV 编码：按 BOM + 0 字节分布自动判 UTF-8 / UTF-16 LE/BE / GBK / GB18030，Excel「Unicode 文本」另存的 UTF-16 csv 不再报 `new-line character seen in unquoted field`（B28） |
| P1 | `core/mapper.py` CSV 分隔符：前 20 个非空行嗅探 `,` `;` `\t` `\|`，分号 / 制表符表不再整行当一列静默出错表（B29） |
| P1 | `.xls` 对照表口径统一：`SUPPORTED_EXTS` 去掉 `.xls`，选到老式 `.xls` 给中文提示「另存为 .xlsx」；`.xls` 仍可作为**被改名的表格文件**；UI 文案（4 个页面）同步（B30） |
| P2 | `core/blind_wm.py` 盲水印解码健壮性：长度校验 + 严格 UTF-8 + 控制字符白名单，解不开返回空串不抛异常（B27） |
| P2 | `tests/t_pkg_exe.py` 源码态冒烟竞态：改为轮询到窗口尺寸正常（≥900x640）再测量并重发最大化，消除「窗口尺寸偏小 314x50」假失败（B31） |
| P1 | 表格页可选类型与对照表口径不一致：`scanner.SPREADSHEET_EXTS` 与表格页 `FILETYPES` 都漏了 `.xlsm`，宏工作簿既选不进列表也读不了 → 补齐类型集合、文件对话框与首页/表格页文案（B32） |
| P2 | 导出对照表扩展名与内容不符：「导出 Excel」允许手输任意扩展名，`.xlsm` / `.csv` 也照写 xlsx 字节流 → 新增 `normalize_export_path` 统一落盘 `.xlsx`，并把「文件正被 Excel 占用」的 `PermissionError` 翻成中文提示，4 个页面提示文案与实际落盘名一致（B33） |

### 交付环境校正（本轮）

| 级别 | 处理 |
|---|---|
| P1 | 环境里 `opencv-python 5.0.0.93` 与 `opencv-python-headless 5.0.0.93` 双装，两者共用同一份 `cv2` 包文件互相覆盖（实测磁盘上为 GUI 版内容）→ 双卸后仅装 headless，`cv2.getBuildInformation()` 显示 `GUI: NONE`；两个 wheel 已备份到 `.cache\whl`，可随时回滚。blind-watermark 元数据把依赖写死成 GUI 版，`pip check` 会提示，已在 `requirements.txt` 注明为上游元数据问题 |
| — | 产物按清理后的依赖环境重打：EXE 49.2 MiB / Setup 50.9 MiB，v1.9 内容不变 |

### v1.9 前序批次（B1~B26 摘要）

内核 9 项：空单元格 / NaN / 公式无缓存不再生成 `None` 文件名；对照表第 2 个非空工作表可读；损坏对照表给中文原因；取消立即收尾；输出目录创建失败不再假死；Windows 保留设备名双层拦截；原地改名目标已存在一律拒绝；同名后缀 1~999 用尽报失败不回退覆盖；EXIF Orientation 竖拍转正。

界面 5 项：高 DPI `ui_scale` 改 96 DPI 基准；底部操作栏不再被滚动区吃光高度；导航栏 Logo 字号自适应；预览弹窗尺寸 / 双滚动条 / 按钮栏固定；「预览改名结果」统一为「预览」。

启动兜底 1 项：缺依赖 / Tk 不可用时中文错误框 + 崩溃日志双写，tkinterdnd2 缺失自动降级。

### v1.8 保留项（历史）

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
| `python tests\run_all.py` 全量回归 | ✅ **13/13 通过，0 失败**（约 2 分 40 秒） |
| core_edges 核心引擎边界 | ✅ 235 项，失败 0（5.4s） |
| core_extra 补充边界 | ✅ 33 项，失败 0 |
| smoke / smoke_final | ✅ 6/6，GUI 7 页切换正常 |
| test_features4 / test_ui_features4 | ✅ 26/26 / 45/45 |
| test_watermark_page（真实检查） | ✅ 21/21（16.3s） |
| t_ui_bind / t_ui_hotkeys / t_ui_layout | ✅ 35 项 / 快捷键全过 / 960~1440px 无溢出 |
| t_pkg_exe 打包产物真实启动 | ✅ EXE 4.5s 出窗 2906x1730；源码态 2.1s 出窗（截图落盘） |
| EXE 真实启动冒烟 | ✅ 无闪退、无黑窗、图标正确 |
| Inno Setup 编译 | ✅ 13.0 秒成功（1.9.0 / 1.9.0.0） |
| 依赖环境 | ✅ 仅 headless opencv（cv2 GUI: NONE），双装已清理；`.cache\whl` 存有 GUI/headless 两份 wheel 可回滚 |
| PDF 手册重建 | ✅ Word COM FileFormat=17，495,479 B |
| 版本号同步 | ✅ app.py=1.9 / iss=1.9.0 / 手册 V1.9 |
| 原文件零改动 | ✅ 输出隔离 |
| 用户数据隔离 | ✅ 回归统一 APPDATA 到 `.cache/test_appdata` |

## 4. 已知缺口

- 未做代码签名，SmartScreen 首次提示属正常（点「仍要运行」）。
- 高 DPI（125%/150%）缩放未做实测，需在高分屏目检。
- 扫描件 PDF（无文字层）无法提取正文，会保留原名并标注。
- 对照表不支持老式 2003 二进制 `.xls`（openpyxl 无写入/读取能力），导入时给中文提示引导另存为 `.xlsx`；`.xls` 仍可作为被改名文件。
- EXE 体积 51.8 MB：含 opencv / numpy / Tk 运行时；已排除 `opencv_videoio_ffmpeg500_64.dll`（29.4 MB，本项目不处理视频）。

## 5. 使用说明

1. **推荐安装包**：双击 `dist\RenameMaster_Setup.exe`，勾选桌面快捷方式，装完启动。
2. **免安装**：直接双击 `dist\RenameMaster.exe`。
3. **原文件绝对安全**：结果统一输出到 `<源目录>_重命名输出\`，源文件零改动；同名自动加后缀。
4. 详细操作见 `dist\RenameMaster_使用手册.pdf`。
