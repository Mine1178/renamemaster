# RenameMaster 交付完成单（Definition of Done）

版本：v1.1 | 交付日期：2026-10-12 | 项目目录：`D:\Desktop\SD\13.Rename`

## 1. 交付物清单

| 交付物 | 路径 | 说明 |
|---|---|---|
| **免安装 EXE** | `dist\RenameMaster.exe` | 单文件，20.2 MB，双击即用 |
| **安装程序** | `dist\RenameMaster_Setup.exe` | 21.9 MB，含桌面/开始菜单快捷方式 + 卸载入口 |
| **PDF 使用手册** | `dist\RenameMaster_使用手册.pdf` | 0.5 MB，深蓝封面/目录/蓝底表头 |
| Markdown 手册 | `USER_MANUAL.md` / `USER_MANUAL.docx` | 源文件，便于修订 |
| 应用图标 | `assets\rename_master.ico` | 深蓝灰底 + 橙色 ◉，多尺寸 |
| 打包脚本 | `build.py` / `RenameMaster.spec` | PyInstaller 可重复打包 |
| 安装脚本 | `installer\rename_master.iss` | Inno Setup 可重新编译 |
| 任务书 | `任务书.md` | 完整需求契约 |
| 验收清单 | `CHECKLIST.md` | A~Q 组全过 |
| 审核报告 | `inbox\review_round2.md` | 5 维评分 22/25 |
| 源码（git） | commit `52e6881` | 最终归档 |

## 2. v1.1 新增功能

- **照片水印**（默认关）：半透明白色文字，5 个位置 × 3 档字号，只在照片页
- **拖拽支持**：拖文件夹进窗口自动填路径，支持带空格路径/多文件取共同父目录

## 3. 验收结果

| 检查项 | 结果 |
|---|---|
| py_compile | ✅ 0 错误 |
| smoke 测试 | ✅ 6/6 通过 |
| E2E 真实场景 | ✅ 5 张图 236KB~2MB 压到 ≤200KB |
| EXE 真实启动 | ✅ |
| Inno Setup 编译 | ✅ 4.4 秒编译成功 |
| 原文件零改动 | ✅ |
| about 页无残留按钮 | ✅ |
| PDF 手册 | ✅ 文件头 %PDF- 正确 |

## 4. 已知缺口

- 未做代码签名（SmartScreen 提示属正常）
- 未做撤销/缩略图/OCR（任务书 R6 已拍板 v1.0 不做）
- 未配快捷键
- 水印开启后文件会变大（quality=95 重编码），v1.2 可加水印后二次压缩

## 5. 使用说明

1. **推荐用安装包**：双击 `dist\RenameMaster_Setup.exe`，勾选「创建桌面快捷方式」，装完从桌面启动
2. **免安装**：直接用 `dist\RenameMaster.exe` 也行
3. **原文件绝对安全**：所有结果输出到 `<源目录>_重命名输出\`，原文件一个字节都不会动
4. 详细操作见 `dist\RenameMaster_使用手册.pdf`
