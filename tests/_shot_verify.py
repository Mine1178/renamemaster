"""临时探针：验证「逐页截图内容错页」到底是探针竞态还是产品问题。

每页做三件事，全部落到控制台输出，便于比对：
  1. 切页后读回 widget 层真相（page_host 里 mapped 的是不是 app.pages[key]、页头标题是什么）
  2. 立即抓一张图 grab1
  3. 再等 1.5s 抓一张图 grab2，并报出 grab1/grab2 的像素差

若 grab1 少了内容而 grab2 完整 → 屏幕合成滞后（探针问题）；
若 grab1 内容就是别的页面 → 需要按标题断言重查产品逻辑。
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

from PIL import ImageChops, ImageGrab  # noqa: E402
from tkinterdnd2 import TkinterDnD  # noqa: E402

from rename_master.ui.app import NAV_ITEMS, App  # noqa: E402
from rename_master.ui.widgets import PageHeader  # noqa: E402

OUT = ROOT / "inbox" / "shots2"


def _page_header_title(page) -> str:
    for child in page.winfo_children():
        if isinstance(child, PageHeader):
            return str(child._title.cget("text"))
    return "(找不到 PageHeader)"


def _visible_page(app):
    for key, page in app.pages.items():
        if page.winfo_ismapped():
            return key, page
    return None, None


def _grab(root) -> "ImageGrab.Image":
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
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    full = ImageGrab.grab(all_screens=True)
    sx = full.width / max(1, root.winfo_screenwidth())
    sy = full.height / max(1, root.winfo_screenheight())
    img = full.crop((int(x * sx), int(y * sy), int((x + w) * sx), int((y + h) * sy)))
    root.attributes("-topmost", False)
    return img


def main() -> int:
    keys = sys.argv[1:] or [k for k, _i, _n in NAV_ITEMS]
    root = TkinterDnD.Tk()
    app = App(root)
    try:
        root.state("zoomed")
    except Exception:  # noqa: BLE001
        pass
    root.update_idletasks()
    root.update()
    time.sleep(1.0)
    OUT.mkdir(parents=True, exist_ok=True)

    for key in keys:
        app.show(key)
        root.update_idletasks()
        root.update()
        time.sleep(1.2)
        vis_key, vis_page = _visible_page(app)
        title = _page_header_title(vis_page) if vis_page is not None else "-"
        print(f"[{key}] app.cur={app.cur} 可见页={vis_key} widget 页头={title!r} "
              f"一致={vis_key == key}")
        g1 = _grab(root)
        time.sleep(1.5)
        g2 = _grab(root)
        diff = ImageChops.difference(g1.convert("RGB"), g2.convert("RGB"))
        bbox = diff.getbbox()
        changed = 0
        if bbox:
            changed = sum(1 for px in diff.getdata() if max(px) > 12)
        print(f"    grab1={g1.width}x{g1.height} grab2={g2.width}x{g2.height} "
              f"差异像素={changed} bbox={bbox}")
        g1.save(OUT / f"{key}.png")
        g2.save(OUT / f"{key}-b.png")
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
