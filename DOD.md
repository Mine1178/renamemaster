# RenameMaster 交付完成单（Definition of Done）

版本：v1.10 | 交付日期：2026-10-15 | 项目目录：`D:\Desktop\SD\13.Rename`

## 1. 交付物清单

| 交付物 | 路径 | 说明 |
|---|---|---|
| **免安装 EXE** | `dist\RenameMaster.exe` | 单文件，29,113,502 B（27.8 MiB），双击即用、无黑窗 |
| **安装程序** | `dist\RenameMaster_Setup.exe` | 30,813,066 B（29.4 MiB），桌面/开始菜单快捷方式 + 卸载入口 |
| **PDF 使用手册** | `dist\RenameMaster_使用手册.pdf` | 474,847 B，内容与 v1.10 一致（封面 + 目录页码 + 截图 + FAQ；已去除水印章节） |
| Markdown 手册 | `USER_MANUAL.md` / `.docx` / `.html` | 源文件，便于修订 |
| 需求契约 | `PRD.md` | F1-F27 + B1-B33 |
| 验收清单 | `CHECKLIST.md` | A-Q 组 |
| 打包脚本 | `build.py` / `RenameMaster.spec` | PyInstaller 可重复打包 |
| 安装脚本 | `installer\rename_master.iss` | Inno Setup 可重新编译（1.10.0 / 1.10.0.0） |
| 手册脚本 | `build_manual_pdf.py` | Word COM 生成 PDF |
| 回归入口 | `tests\run_all.py` / `run.bat` | 12 用例一键全量回归 / 一键启动 |
| 源码（git） | v1.10 归档提交 | 见下方「归档」 |

## 2. v1.10 变更：水印功能剥离

「添加水印」功能整体迁出，后续作为独立软件「水印助手」单独发布；本轮只做剥离，不改动其余功能面。

### 移除范围

| 项 | 处理 |
|---|---|
| 独立页面 | 删除 `src/rename_master/ui/pages/watermark.py`（4 布局卡片 / 九宫格定位 / 提取分支），左导航去掉「添加水印」 |
| 水印引擎 | 删除 `src/rename_master/core/watermark.py`（可见水印）与 `core/blind_wm.py`（频域盲水印嵌入 / 提取） |
| 导航与首页 | `ui/app.py` 的 NAV_ITEMS / `_page_builders` / `_build_watermark()` 全部移除；首页功能卡片 5 → 4（照片 / PDF / 表格 / 文档），页头副标题同步去水印 |
| 关于页 / 主题 | 关于页功能清单与技术栈去掉水印条目；`ui/theme.py` 删除仅水印使用的 `C_CYAN` |
| 历史记录 | `core/history.py` 的 `PAGE_NAMES` 删除 `"watermark"`，旧批次记录不再解析到已不存在的页面 |
| 依赖清理 | `requirements.txt` / `build.py` / `RenameMaster.spec` 去掉 numpy / opencv / PyWavelets / blind-watermark；打包脚本移除 `COLLECT_ALL`、ffmpeg dll 收集与 cv2 瘦身逻辑 |
| 测试同步 | 删除 `tests/test_watermark_page.py` 及 `run_all.py` 中的挂载点；`t_core_edges` / `_shot_verify` 的噪声图生成与像素比对改为纯 Pillow（不再依赖 numpy）；`t_ui_layout` 首页卡片断言 5 → 4 |
| 交付物重打 | EXE / 安装程序 / PDF 手册按无 numpy / opencv 的环境重新打包，功能面与 v1.9 一致，仅少一个页面 |
| 历史可追溯 | PRD / 手册 / 变更记录保留水印条目并标注「v1.10 已剥离」，注明后续由独立软件「水印助手」承载 |

### 体积收益

| 指标 | v1.9 | v1.10 | 变化 |
|---|---|---|---|
| 免安装 EXE | 51,634,208 B（49.2 MiB） | 29,113,502 B（27.8 MiB） | −21.7 MiB |
| 安装程序 | 53,331,110 B（50.9 MiB） | 30,813,066 B（29.4 MiB） | −21.4 MiB |

## 3. v1.9 修复内容（历史）

### 本轮新增（B27~B33）

| 级别 | 修复 |
|---|---|
| P1 | `core/mapper.py` CSV 编码：按 BOM + 0 字节分布自动判 UTF-8 / UTF-16 LE/BE / GBK / GB18030，Excel「Unicode 文本」另存的 UTF-16 csv 不再报 `new-line character seen in unquoted field`（B28） |
| P1 | `core/mapper.py` CSV 分隔符：前 20 个非空行嗅探 `,` `;` `\t` `\|`，分号 / 制表符表不再整行当一列静默出错表（B29） |
| P1 | `.xls` 对照表口径统一：`SUPPORTED_EXTS` 去掉 `.xls`，选到老式 `.xls` 给中文提示「另存为 .xlsx」；`.xls` 仍可作为**被改名的表格文件**；UI 文案（4 个页面）同步（B30） |
| P2 | `core/blind_wm.py` 盲水印解码健壮性：长度校验 + 严格 UTF-8 + 控制字符白名单，解不开返回空串不抛异常（B27，该模块已于 v1.10 随水印功能一并剥离） |
| P2 | `tests/t_pkg_exe.py` 源码态冒烟竞态：改为轮询到窗口尺寸正常（≥900x640）再测量并重发最大化，消除「窗口尺寸偏小 314x50」假失败（B31） |
| P1 | 表格页可选类型与对照表口径不一致：`scanner.SPREADSHEET_EXTS` 与表格页 `FILETYPES` 都漏了 `.xlsm`，宏工作簿既选不进列表也读不了 → 补齐类型集合、文件对话框与首页/表格页文案（B32） |
| P2 | 导出对照表扩展名与内容不符：「导出 Excel」允许手输任意扩展名，`.xlsm` / `.csv` 也照写 xlsx 字节流 → 新增 `normalize_export_path` 统一落盘 `.xlsx`，并把「文件正被 Excel 占用」的 `PermissionError` 翻成中文提示，4 个页面提示文案与实际落盘名一致（B33） |

### 交付环境校正（v1.9 历史）

| 级别 | 处理 |
|---|---|
| P1 | 环境里 `opencv-python 5.0.0.93` 与 `opencv-python-headless 5.0.0.93` 双装，两者共用同一份 `cv2` 包文件互相覆盖（实测磁盘上为 GUI 版内容）→ 双卸后仅装 headless，`cv2.getBuildInformation()` 显示 `GUI: NONE`；两个 wheel 已备份到 `.cache\whl`，可随时回滚。blind-watermark 元数据把依赖写死成 GUI 版，`pip check` 会提示，已在 `requirements.txt` 注明为上游元数据问题 |
| — | 产物按清理后的依赖环境重打：EXE 49.2 MiB / Setup 50.9 MiB，v1.9 内容不变 |

> v1.10 说明：RenameMaster 自 v1.10 起已不依赖 numpy / opencv / PyWavelets / blind-watermark，`requirements.txt` 仅保留 Pillow / openpyxl / python-docx / pypdf / tkinterdnd2。上述依赖仍留在开发环境中，供后续独立软件「水印助手」复用，`cv2` 保持 headless 单装状态（GUI: NONE），`.cache\whl` 的两份 wheel 备份一并保留。

### v1.9 前序批次（B1~B26 摘要）

内核 9 项：空单元格 / NaN / 公式无缓存不再生成 `None` 文件名；对照表第 2 个非空工作表可读；损坏对照表给中文原因；取消立即收尾；输出目录创建失败不再假死；Windows 保留设备名双层拦截；原地改名目标已存在一律拒绝；同名后缀 1~999 用尽报失败不回退覆盖；EXIF Orientation 竖拍转正。

界面 5 项：高 DPI `ui_scale` 改 96 DPI 基准；底部操作栏不再被滚动区吃光高度；导航栏 Logo 字号自适应；预览弹窗尺寸 / 双滚动条 / 按钮栏固定；「预览改名结果」统一为「预览」。

启动兜底 1 项：缺依赖 / Tk 不可用时中文错误框 + 崩溃日志双写，tkinterdnd2 缺失自动降级。

### v1.8 保留项（历史）

| 级别 | 修复 |
|---|---|
| P0 | 水印「平铺密度 grid」布局走错分支 → 改为 `layout in ("tile","grid")` 都走平铺（水印模块已于 v1.10 剥离） |
| P0 | 操作栏 destroy 导致切回页面崩溃 → 改 pack_forget 复用 |
| P1 | photo.py `src_dir` 字典 key 重复 → 删除冗余 |
| P1 | advanced.py checkbox 仍用系统样式 → 统一 ☑/☐ font=18 大方框 |
| P2 | 盲水印提取分支空 out_dir 仍 mkdir → 提取时跳过（水印模块已于 v1.10 剥离） |

v1.7 已有（水印页相关条目均随 v1.10 剥离）：水印页 4 布局 2×2 卡片 / 9 位置九宫格 / 真色块 swatch / 弹窗 1100×700 统一 / Treeview 撑满 / checkbox 大方框化。

## 4. 验收结果

| 检查项 | 结果 |
|---|---|
| py_compile 全部源码 | ✅ 0 错误 |
| `python tests\run_all.py` 全量回归 | ✅ **12/12 通过，0 失败**（三轮一致，末轮 58.9s） |
| core_edges 核心引擎边界 | ✅ 235 项，失败 0（4.4s） |
| core_extra 补充边界 | ✅ 33 项，失败 0（2.3s） |
| smoke / smoke_final | ✅ 6/6 项 + 拖放派发全过，GUI 6 页切换正常 |
| test_features4 / test_ui_features4 | ✅ 26/26 / 45/45 |
| t_ui_bind / t_ui_hotkeys / t_ui_layout | ✅ 29 项 / 快捷键全过 / 960~1440px 无溢出 |
| t_pkg_exe 打包产物真实启动 | ✅ EXE 4.2s 出窗 2906x1730；源码态 2.1s 出窗（截图落盘 `inbox\exe_smoke.png` / `src_smoke.png`） |
| EXE 真实启动冒烟 | ✅ 无闪退、无黑窗、图标正确；左导航 6 项（首页/照片/PDF/表格/文档/关于），无「添加水印」，底部版本号 v1.10 |
| Inno Setup 编译 | ✅ 6.5 秒成功（1.10.0 / 1.10.0.0） |
| 水印残留检索 | ✅ `watermark` / `水印` / `blind_` / `cv2` / `numpy` / `pywt` 在 `src`、`tests`、`requirements.txt`、打包配置中 0 命中 |
| 依赖环境 | ✅ 项目已不依赖 numpy / opencv / PyWavelets / blind-watermark；环境中 `cv2` 保持 headless 单装（GUI: NONE），`.cache\whl` 两份 wheel 保留备「水印助手」复用 |
| PDF 手册重建 | ✅ Word COM FileFormat=17，474,847 B（已去水印章节，章节号顺延） |
| 版本号同步 | ✅ app.py=1.10 / iss=1.10.0 / 手册 V1.10 |
| 原文件零改动 | ✅ 输出隔离 |
| 用户数据隔离 | ✅ 回归统一 APPDATA 到 `.cache/test_appdata` |

## 5. 已知缺口

- 未做代码签名，SmartScreen 首次提示属正常（点「仍要运行」）。
- 高 DPI（125%/150%）缩放未做实测，需在高分屏目检。
- 扫描件 PDF（无文字层）无法提取正文，会保留原名并标注。
- 对照表不支持老式 2003 二进制 `.xls`（openpyxl 无写入/读取能力），导入时给中文提示引导另存为 `.xlsx`；`.xls` 仍可作为被改名文件。
- EXE 体积 27.8 MiB：水印剥离后已不含 opencv / numpy，仅剩 Pillow 与 Tk 运行时，无需再做 dll 排除。
- 水印功能已不属本产品范围，相关历史条目（B27、v1.7/v1.8 水印项）仅作追溯保留，后续维护在独立软件「水印助手」中进行。

## 6. 使用说明

1. **推荐安装包**：双击 `dist\RenameMaster_Setup.exe`，勾选桌面快捷方式，装完启动。
2. **免安装**：直接双击 `dist\RenameMaster.exe`。
3. **原文件绝对安全**：结果统一输出到 `<源目录>_重命名输出\`，源文件零改动；同名自动加后缀。
4. 详细操作见 `dist\RenameMaster_使用手册.pdf`。
