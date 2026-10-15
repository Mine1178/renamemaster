# v1.10.1 交付证据归档

本目录存放 **RenameMaster v1.10.1** 的交付验证证据。全部文件由下面记录的命令
在本机（Windows 11 / 1440×900 逻辑屏 / 200% DPI / Python 3.14.4）实跑产生，
未做任何后期修饰。

---

## 1. 文件清单

| 文件 | 生成方式 | 证明什么 |
| --- | --- | --- |
| `regress_v1.10.1.txt` | `python tests\run_all.py -v` | **12/12 用例通过**（含 EXE 冒烟、界面布局 960/1000/1100/1280/1440 五档、四页面表格列宽） |
| `regress_v1.10_watermark_removal.txt` | 剥离提交 `b25676a` 时的全量回归 | 水印剥离后回归仍 12/12，功能面未受影响 |
| `manual_v1.10_watermark_removal.txt` | `build_manual_pdf.py` 的 Word COM 输出 | PDF 手册在剥离后照常生成 |
| `table_widths_v1.10.1.txt` | `python inbox\_shot_table.py` | 四个页面表格「列宽合计 == 表格宽度」，无空白残列 |
| `table_photo.png` / `table_pdf.png` / `table_spreadsheet.png` / `table_document.png` | 同上 | 照片 / PDF / 表格 / 文档四页「添加文件」表格铺满界面、列宽贴合内容 |
| `home_grid.png` | `python tests\_shot_pages.py home` | 首页 4 张功能卡按 2×2 铺满，无 3+1 留白 |
| `exe_home.png` | `python inbox\_probe_exe_final.py <dest>` | **打包后的 EXE** 首页正常渲染（左导航只有 4 个功能页 + 关于，无「添加水印」，左下角 `v1.10.1`） |

> 表里的 `inbox\` 是本地探针脚本目录，**未纳入版本库**（只作一次性取证工具）。
> 抓图脚本的关键点写在下面第 4 节，换机器复现时照抄即可。

---

## 2. 本轮（v1.10.1）改了什么

对照用户本轮提出的四点：

1. **删除 `pic_重命名输出\` 里 6 张旧图** —— 已删（提交 `6a67f83`，Git 中标记删除）。
2. **水印助手代码暂不删除** —— 从 v1.9 快照 `bdad2d3` 按字节取回，存入
   `水印助手_存档/`（4 个源文件，含 sha1 核对），不参与打包与回归。
3. **关键证据归档进仓库** —— 即本目录。
4. **「添加文件」表格列宽按内容自适应、铺满界面** —— 提交 `faa05ba`；本目录
   `table_*.png` + `table_widths_v1.10.1.txt` 为验证证据。

另外，v1.10.1 顺手修掉了「去掉水印第 5 张卡后，首页在宽屏排成 3+1、第二行只
占 1/3 宽、右侧大片留白」的布局回退：末行只剩 1 张卡时自动降一档列数
（4 张 → 2×2；5 张仍是 3+2，v1.9 观感不变）。

---

## 3. 关键结论

### 3.1 回归

```
合计 12 个用例：通过 12，失败 0
```

含 `t_pkg_exe`（**对 `dist\RenameMaster.exe` 真机冒烟：启动 → 窗口尺寸正常 →
最大化 → 渲染通过**），即打包产物本身是被验证过的，不只是源码态。

### 3.2 表格列宽（用户本轮重点）

在 1440 逻辑宽内容区（表格控件 1254px）实测：

| 页面 | 列宽 | 合计 |
| --- | --- | --- |
| 照片命名 | `sel=48, name=996, size=90, dim=120` | 1254 |
| PDF 命名 | `name=1164, size=90` | 1254 |
| 表格命名 | `name=1164, size=90` | 1254 |
| 文档命名 | `name=1164, size=90` | 1254 |

四页都是「列宽合计 == 表格宽度」，勾选列固定 48px（不再被 `stretch` 拉成一大片
空白），文件名列吃掉全部剩余宽度。

### 3.3 水印剥离残留检查

对 `src/`、`tests/`、`build.py`、`RenameMaster.spec`、`requirements.txt`、
`installer/`、`run.bat` 检索
`watermark|blind_wm|cv2|opencv|pywt|PyWavelets|blind-watermark|水印`：

**功能性残留 0 处。** 唯一 1 处命中是 `src/rename_master/ui/pages/home.py` 里
解释「为什么末行只剩 1 张卡时要降列数」的注释文字（提到 v1.10 去掉了该卡片），
属说明性文本，不是代码依赖。

---

## 4. 抓图复现要点（踩过的坑，避免下次误判为缺陷）

1. **抓 EXE 时探针进程必须自己声明 DPI 感知**，否则 `GetWindowRect` 返回的是
   DPI 虚拟化后的逻辑坐标（2880×1800 的窗口被报成 1453×865），按该尺寸建位图再
   `PrintWindow` 只能拿到窗口内容的左上角一块，看起来就像「界面空白 / 缺一半」。
   做法：`ctypes.windll.shcore.SetProcessDpiAwareness(2)`。
2. **定位窗口要按窗口类 `TkTopLevel`**，不要按「尺寸最大的窗口」猜：ttk 还会创建
   同尺寸级的隐藏窗口（`TtkMonitorClass`），挑错就会抓出一张全白图。
   PyInstaller onefile 有父/子两个 PID，`TkTopLevel` 属于子进程。
3. **Tk 窗口被别的窗口压住时 `PrintWindow` 只重绘可见部分**，抓出来是残帧。
   抓图前先 `SetWindowPos(HWND_TOPMOST)` + `SetForegroundWindow`，抓完撤销置顶。
4. **源码态截图用 `ImageGrab.grab(all_screens=True)` 再按物理/逻辑比例换算裁剪**；
   直接按 `winfo_rootx()` 的逻辑坐标裁屏，在 200% 缩放下只能得到窗口的 1/4。
5. **窗口首次 `state("zoomed")` 可能还没摆到屏幕上**（`winfo_rootx()` 仍是
   `-32000` 之类的离屏值），此时裁屏得到全黑。抓图前轮询到 `rootx > -1000`
   且宽度 > 900 再抓。

---

## 5. 本机交付物（与证据同批）

| 交付物 | 大小 |
| --- | --- |
| `dist\RenameMaster.exe` | 29,118,795 B（27.8 MiB） |
| `dist\RenameMaster_Setup.exe` | 30,817,651 B（29.4 MiB） |
| `dist\RenameMaster_使用手册.pdf` | 476,578 B |

环境：Python 3.14.4 / PyInstaller 6.22.3 / Inno Setup 6；运行期依赖仅
Pillow、openpyxl、python-docx、pypdf、tkinterdnd2（numpy / OpenCV / PyWavelets /
blind-watermark 已随水印功能剥离，其 wheel 留在 `.cache/whl/` 供水印助手复用）。
