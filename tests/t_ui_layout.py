"""界面布局回归：真实构建 App，逐页检查横向溢出 / 操作栏可见性 / 卡片列数。

为什么需要它：v1.8 交付版在 1440x900 逻辑屏（200% DPI）上首页卡片只露出一张半、
照片页表格右侧被裁、底部操作栏整条不可见——这些都不是崩溃，单元测试抓不到，
只有把真实窗口拉起来量像素才看得见。本用例把"被裁"变成可断言的数字。

判定标准
--------
1. 任一已映射控件的右边缘不得超出内容区（Canvas）右边缘；
2. 注册了操作栏的页面，操作栏必须可见且高度 > 0；
3. 首页 5 张功能入口卡片必须全部落在内容区内。

用法：python tests/t_ui_layout.py            # 默认 1440 宽
      python tests/t_ui_layout.py 1280 1100  # 指定多档窗口宽度
"""
from __future__ import annotations

import sys
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
from rename_master.ui.widgets import Card  # noqa: E402

TOL = 2          # 允许的像素误差
# 默认宽度阶梯：本机逻辑屏 1440x900（200% DPI），960 是 minsize 下限
WIDTH_LADDER = [1440, 1280, 1100, 1000, 960]


def _path(widget) -> str:
    """控件路径（用于报错定位）：cls#text 逐级拼接。"""
    parts = []
    cur = widget
    for _ in range(32):
        try:
            name = cur.winfo_name()
            cls = cur.winfo_class()
        except Exception:  # noqa: BLE001
            break
        label = f"{cls}"
        try:
            txt = cur.cget("text")
            if txt:
                label += f"[{str(txt)[:24]}]"
        except Exception:  # noqa: BLE001
            pass
        parts.append(label)
        if name in (".", ""):
            break
        try:
            parent = cur.winfo_parent()
            if not parent or parent == name:
                break
            cur = cur.nametowidget(parent)
        except Exception:  # noqa: BLE001
            break
    return " < ".join(reversed(parts))


def _clipped(root_widget, right_edge: int, skip: tuple) -> list[str]:
    """返回所有"右边缘越界"的已映射控件（跳过 Canvas / 滚动条等容器）。"""
    bad: list[str] = []

    def walk(w):
        try:
            if w in skip or not w.winfo_ismapped():
                return
            cls = w.winfo_class()
            if cls in ("Canvas", "TScrollbar", "Scrollbar", "Menu"):
                return
            x2 = w.winfo_rootx() + w.winfo_width()
            if x2 > right_edge + TOL:
                bad.append(f"{_path(w)} → 右边缘 {x2} 超出 {right_edge}"
                           f"（溢出 {x2 - right_edge}px）")
        except Exception:  # noqa: BLE001
            return
        for child in w.winfo_children():
            walk(child)

    walk(root_widget)
    return bad


def _iter(widget):
    """深度优先遍历控件树。"""
    yield widget
    for child in widget.winfo_children():
        yield from _iter(child)


def _check_width(app, root, width: int, height: int = 900) -> list[str]:
    problems: list[str] = []
    try:
        root.state("normal")     # App 启动时是 zoomed，先还原否则改不动尺寸
    except Exception:  # noqa: BLE001
        pass
    root.geometry(f"{width}x{height}")
    root.update_idletasks()
    root.update()

    for key, _icon, name in NAV_ITEMS:
        try:
            app.show(key)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{width}px / {key}: show() 抛异常 {exc!r}")
            continue
        # 多跑几轮事件循环：滚动条显隐会反过来改变 Canvas 宽度，
        # 必须等布局真正收敛后再量，否则量到的是中间态。
        for _ in range(4):
            root.update_idletasks()
            root.update()

        canvas = app.canvas
        right = canvas.winfo_rootx() + canvas.winfo_width()
        page = app.pages[key]
        bad = _clipped(page, right, ())
        if bad:
            problems.append(
                f"{width}px / {key}（{name}）横向溢出 {len(bad)} 处"
                f"［canvas={canvas.winfo_width()} "
                f"page_host={app.page_host.winfo_width()} "
                f"scrollbar={'显示' if app._vsb.winfo_ismapped() else '隐藏'}］：")
            problems.extend(f"    · {b}" for b in bad[:6])

        # 操作栏：该页注册了 bar 就必须看得见
        if app.action_host.winfo_children():
            if not app.action_host.winfo_ismapped():
                problems.append(f"{width}px / {key}: 操作栏未映射（不可见）")
            elif app.action_host.winfo_height() <= 1:
                problems.append(f"{width}px / {key}: 操作栏高度 "
                                f"{app.action_host.winfo_height()}，被压成一条线")
            else:
                a_bottom = (app.action_host.winfo_rooty()
                            + app.action_host.winfo_height())
                win_bottom = root.winfo_rooty() + root.winfo_height()
                if a_bottom > win_bottom + TOL:
                    problems.append(f"{width}px / {key}: 操作栏底部 {a_bottom} "
                                    f"超出窗口 {win_bottom}")
                bad_btn = _clipped(app.action_host, right, ())
                if bad_btn:
                    problems.append(f"{width}px / {key}: 操作栏内按钮溢出：")
                    problems.extend(f"    · {b}" for b in bad_btn[:4])

    # 首页卡片必须全部在可视区（v1.8 只露出 1.5 张）
    app.show("home")
    root.update_idletasks()
    root.update()
    right = app.canvas.winfo_rootx() + app.canvas.winfo_width()
    # 入口卡片 = 带 on_click 的 Card（"最近使用"卡片没有点击跳转）
    entry_cards = [w for w in _iter(app.pages["home"])
                   if isinstance(w, Card) and w.bind("<Button-1>")]
    visible = [c for c in entry_cards
               if c.winfo_ismapped() and c.winfo_rootx() + c.winfo_width() <= right + TOL]
    if len(visible) < 4:
        problems.append(f"{width}px / home: 功能卡片只完整可见 {len(visible)}/4 张")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    widths = [int(a) for a in args] or list(WIDTH_LADDER)
    root = TkinterDnD.Tk()
    root.title("t_ui_layout")
    app = App(root)
    root.update_idletasks()
    root.update()
    print(f"环境：screen={root.winfo_screenwidth()}x{root.winfo_screenheight()} "
          f"fpixels(1i)={root.winfo_fpixels('1i'):.1f} "
          f"ui_scale={app.ui_scale:.3f} "
          f"tk_scaling={root.tk.call('tk', 'scaling'):.3f}")
    print(f"导航宽度={app.navs['home'].master.winfo_width()}px")

    problems: list[str] = []
    for w in widths:
        print(f"--- 窗口 {w}px ---")
        found = _check_width(app, root, w)
        if found:
            for line in found:
                print(f"  FAIL {line}")
        else:
            print("  OK")
        problems.extend(found)

    root.destroy()
    if problems:
        print(f"\n共 {len(problems)} 项布局问题。")
        return 1
    print("\n布局检查全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
