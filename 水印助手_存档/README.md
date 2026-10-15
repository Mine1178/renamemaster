# 水印助手 · 源码存档

本目录**不属于 RenameMaster 产品**，不会被 `build.py` / `RenameMaster.spec` /
`tests/run_all.py` 引用，也不进入任何安装包。

RenameMaster 自 v1.10 起已把「添加水印」功能整体剥离（用户要求：功能剔除，
后期单独做成软件「水印助手」）。为满足「水印助手代码暂不删除」，
把剥离前的源码按字节原样取回存档于此，供后续独立软件复用。

## 来源

| 项 | 值 |
| --- | --- |
| 来源提交 | `bdad2d3`（v1.9 交付快照，水印功能最后一次通过全量回归的版本） |
| 剥离提交 | `b25676a`（v1.10，从产品中删除水印源码与依赖） |
| 取回方式 | `git show bdad2d3:<路径>` 按字节写盘，已逐个比对 blob 大小与内容 |

## 目录内容

| 存档路径 | 原仓库路径 | 大小 | sha1(前 12 位) |
| --- | --- | --- | --- |
| `core/watermark.py` | `src/rename_master/core/watermark.py` | 27,193 B | `797151eeca00` |
| `core/blind_wm.py` | `src/rename_master/core/blind_wm.py` | 5,442 B | `4eceae41aa89` |
| `ui/pages/watermark.py` | `src/rename_master/ui/pages/watermark.py` | 44,650 B | `866ab4d121bf` |
| `tests/test_watermark_page.py.bak` | `tests/test_watermark_page.py` | 16,055 B | `6e10727afe6e` |

> 用例后缀改成 `.bak` 是为了避免被 pytest 之类的自动发现机制扫到（它会
> `import rename_master.core.watermark`，而该模块已不在产品里）。回填到新项目时
> 把后缀改回 `.py` 即可。

功能范围（依据 v1.9 的 PRD / 关于页）：4 种可见水印布局（斜向平铺 / 九宫格
9 位置 / 印章 / 密度网格，默认关闭）+ 频域隐形盲水印（版权文字，裁剪压缩后仍可提取取证）。

## 运行依赖（本机环境已具备，未卸载）

| 包 | 本机版本 |
| --- | --- |
| numpy | 2.5.4 |
| opencv-python-headless | 5.0.0.93（已按用户要求只留 headless，卸掉 `opencv-python`） |
| PyWavelets | 1.10.0 |
| blind-watermark | 0.4.4 |
| Pillow | 12.3.0 |

离线 wheel 缓存：`.cache/whl/`（目前只有 `opencv_python-5.0.0.93-*.whl` 与
`opencv_python_headless-5.0.0.93-*.whl`，共约 88 MB）。

## 剥离时同步改动的集成点（新项目重建时按此清单回填）

以下改动都在剥离提交 `b25676a` 里，方向是「删」。做「水印助手」时反向补上即可：

| 文件 | 剥离时删掉的内容 |
| --- | --- |
| `src/rename_master/ui/app.py` | `NAV_ITEMS` 里的 `("watermark", "💧", "添加水印")`、`_page_builders["watermark"]`、`_build_watermark()` 方法 |
| `src/rename_master/ui/pages/home.py` | 首页入口卡片 `("💧", "添加水印", T.C_CYAN, "斜向平铺（裁不掉）或角落单处…", "watermark")`；副标题里的「添加水印」字样 |
| `src/rename_master/ui/pages/about.py` | 功能清单两条（照片水印 / 隐形盲水印）与技术栈三条（numpy + OpenCV、PyWavelets + blind-watermark、Pillow 括注） |
| `src/rename_master/ui/theme.py` | `C_CYAN = "#0891b2"`（水印入口色） |
| `src/rename_master/core/history.py` | `PAGE_NAMES["watermark"] = "水印"` |
| `tests/run_all.py` | `LEGACY` 表里的 `"test_watermark_page.py"` |
| `requirements.txt` | numpy / opencv / PyWavelets / blind-watermark 四行 |
| `build.py`、`RenameMaster.spec` | 隐藏导入与收集配置里的 `numpy` / `cv2` / `pywt` / `blind_watermark` |
| `installer/rename_master.iss` | 安装包描述文字里的水印字样 |

## 自检

```powershell
python -m compileall -q 水印助手_存档      # 语法自检（已通过）
git show bdad2d3:src/rename_master/core/watermark.py | Measure-Object -Character   # 与上表大小核对
```

## 注意

- 本存档是**只读备份**：RenameMaster 后续迭代不要再来改这里的文件。
- 取回时的原始提交仍在仓库历史里（`bdad2d3`），本存档的价值是让 v1.9 的水印实现
  在主干上可见、可 diff，而不必翻历史。
