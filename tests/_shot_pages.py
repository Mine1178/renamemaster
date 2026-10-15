"""临时探针（用完即删）：真实 App 跑起来，逐页截图 + 导出操作栏结构。

用法：python tests/_shot_pages.py [页面key ...]
输出：inbox/shots/<key>.png + 控制台操作栏树
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

from tkinterdnd2 import TkinterDnD  # noqa: E402

from rename_master.ui.app import NAV_ITEMS, App  # noqa: E402

OUT = ROOT / "inbox" / "shots"


def _walk(widget, depth=0):
    """递归列出 widget 树（含 text / 几何信息）。"""
    lines = []
    try:
        cls = widget.winfo_class()
        text = ""
        try:
            text = widget.cget("text")
        except Exception:  # noqa: BLE001
            pass
        lines.append(f"{'  ' * depth}{cls} {text!r} "
                     f"mapped={widget.winfo_ismapped()} "
                     f"{widget.winfo_width()}x{widget.winfo_height()}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"{'  ' * depth}<{exc}>")
        return lines
    for child in widget.winfo_children():
        lines.extend(_walk(child, depth + 1))
    return lines


def _grab(root, path: Path) -> bool:
    from PIL import ImageGrab
    try:
        root.deiconify()
        root.state("zoomed")
    except Exception:  # noqa: BLE001
        pass
    root.lift()
    root.attributes("-topmost", True)
    try:
        root.focus_force()
    except Exception:  # noqa: BLE001
        pass
    root.update_idletasks()
    root.update()
    time.sleep(1.2)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    # 本机是 200% 缩放 + 本进程 DPI-unaware：窗口被系统按 2× 位图放大到物理像素，
    # 而 winfo_* 给的是逻辑像素 —— 直接按逻辑坐标 bbox 抓到的只是窗口左上角 1/4
    # （上一轮 about/document/spreadsheet 全黑就是这个原因，不是页面空白）。
    # 这里先整屏按物理像素抓，再按 物理/逻辑 比例换算窗口区域，得到完整窗口。
    full = ImageGrab.grab(all_screens=True)
    sx = full.width / max(1, root.winfo_screenwidth())
    sy = full.height / max(1, root.winfo_screenheight())
    img = full.crop((int(x * sx), int(y * sy),
                     int((x + w) * sx), int((y + h) * sy)))
    # 二次抓图比对：DWM 偶发把「上一帧合成画面」交给 BitBlt（v1.9 排查结论），
    # 单次抓图可能出现「已切走的旧页面仍被截到」的错页假象。
    # 再抓一张，若两张不一致就以第二张为准（此时页面已稳定呈现）。
    time.sleep(1.0)
    full2 = ImageGrab.grab(all_screens=True)
    img2 = full2.crop((int(x * sx), int(y * sy),
                       int((x + w) * sx), int((y + h) * sy)))
    if (img2.width, img2.height) == (img.width, img.height):
        from PIL import ImageChops
        diff = ImageChops.difference(img.convert("RGB"), img2.convert("RGB"))
        if diff.getbbox() is not None:
            img = img2
            print("    （抓图与 1s 后重抓不一致，已采用稳定后的第二张）")
    root.attributes("-topmost", False)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"  截图 {path.name} ({img.width}x{img.height}) @ ({x},{y}) {w}x{h} "
          f"物理屏={full.width}x{full.height} 逻辑屏={root.winfo_screenwidth()}x"
          f"{root.winfo_screenheight()} scale={sx:.2f}")
    return img.width > 200


def main() -> int:
    keys = sys.argv[1:] or [k for k, _i, _n in NAV_ITEMS]
    root = TkinterDnD.Tk()
    app = App(root)
    try:
        root.state("zoomed")
    except Exception as exc:  # noqa: BLE001
        print("zoomed 失败：", exc)
    root.update_idletasks()
    root.update()
    time.sleep(1.0)

    print("== 环境 ==")
    print(f"  screen={root.winfo_screenwidth()}x{root.winfo_screenheight()} "
          f"fpixels(1i)={root.winfo_fpixels('1i'):.1f} ui_scale={app.ui_scale:.3f} "
          f"tk_scaling={root.tk.call('tk', 'scaling'):.3f}")
    print(f"  window={root.winfo_width()}x{root.winfo_height()} "
          f"state={root.state()} geom={root.geometry()}")
    print(f"  nav={app.navs['home'].master.winfo_width()} "
          f"content={app.content.winfo_width()} "
          f"canvas={app.canvas.winfo_width()}x{app.canvas.winfo_height()}")

    for key in keys:
        try:
            app.show(key)
        except Exception as exc:  # noqa: BLE001
            print(f"[{key}] show() 抛异常：{exc!r}")
            continue
        root.update_idletasks()
        root.update()
        time.sleep(0.4)
        print(f"=== {key} ===")
        page = app.pages[key]
        vis = [k for k, p in app.pages.items() if p.winfo_ismapped()]
        if vis != [key]:
            print(f"  !! 可见页与目标不一致：{vis}（目标 {key}）")
        else:
            print(f"  可见页校验通过：{vis[0]} == {key}")
        print(f"  page: mapped={page.winfo_ismapped()} "
              f"size={page.winfo_width()}x{page.winfo_height()} "
              f"req={page.winfo_reqwidth()}x{page.winfo_reqheight()}")
        print(f"  page_host: size={app.page_host.winfo_width()}x"
              f"{app.page_host.winfo_height()} "
              f"req={app.page_host.winfo_reqwidth()}x"
              f"{app.page_host.winfo_reqheight()} "
              f"canvas={app.canvas.winfo_width()}x{app.canvas.winfo_height()} "
              f"OVERFLOW_X={app.page_host.winfo_reqwidth() - app.canvas.winfo_width()}")
        print("  action_host:", _walk(app.action_host)[0])
        for line in _walk(app.action_host)[1:]:
            print("   ", line.strip())
        _grab(root, OUT / f"{key}.png")
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
