"""界面交互回归（v1.9 测评团队）：点击命中区 / 绑定不被吞 / 变量不重复。

为什么需要它
------------
`t_ui_layout.py` 只量几何，量不出“看得见但点不动”。首页 5 张入口卡片的
emoji / 标题 / 描述都是 SelectableText（tk.Text），而 Card 的点击绑定是在
`Card(...)` 构造时递归挂到**已存在**的子件上的；home.py 是构造完才往
`card.body` 里塞内容 —— 于是“点字没反应、只有点卡片空白才跳转”。
这类 bug 不崩溃、不报错，只有真点一下才知道。

判定标准
--------
1. 点入口卡片的 emoji / 标题 / 描述文字，都必须跳到对应页面；
2. 子件自带的 <Button-1>（复选框那种）不能被卡片的点击绑定吃掉；
3. 补绑必须幂等：反复 refresh_click 后点一下只触发一次跳转；
4. 同一页面内不允许两个输入框共享同一个 textvariable（重复控件指纹）。

用法：python tests/t_ui_bind.py
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

from tkinterdnd2 import TkinterDnD  # noqa: E402

from rename_master.ui.app import App  # noqa: E402
from rename_master.ui.pages.home import ENTRIES  # noqa: E402
from rename_master.ui.widgets import Card, SelectableText  # noqa: E402

FAILS: list[str] = []
CHECKS = 0


def check(cond: bool, label: str) -> bool:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(label)
        print(f"  [FAIL] {label}")
    else:
        print(f"  [ok]   {label}")
    return bool(cond)


def _iter(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _iter(child)


def _entry_card(app, key: str) -> Card | None:
    """首页里跳转到指定页面的那张入口卡片。"""
    for w in _iter(app.pages["home"]):
        if isinstance(w, Card) and w._click is not None:
            fn = w._click[0]
            try:
                if fn.__defaults__ and fn.__defaults__[0] == key:
                    return w
            except Exception:                         # noqa: BLE001
                pass
    return None


def _pump(root, times: int = 4) -> None:
    for _ in range(times):
        root.update_idletasks()
        root.update()


def test_home_card_text_clickable(app, root) -> None:
    """① 点 emoji / 标题 / 描述文字都要能跳转（本次修复的核心）。"""
    print("\n① 首页入口卡片：点文字也能跳转")
    for _emoji, title, _accent, _desc, key in ENTRIES:
        card = _entry_card(app, key)
        if not check(card is not None, f"找到「{title}」入口卡片"):
            continue
        texts = [w for w in _iter(card) if isinstance(w, SelectableText)]
        if not check(len(texts) >= 2,
                     f"「{title}」卡片含 emoji/标题/描述文字块（实得 {len(texts)}）"):
            continue
        for widget in texts:
            app.show("home")
            _pump(root)
            app.cur = "home"
            widget.event_generate("<Button-1>", x=3, y=3)
            _pump(root, 2)
            if not check(app.cur == key,
                         f"「{title}」点文字块 → 跳到 {key}（实际 {app.cur}）"):
                break          # 同一张卡失败一次就够，别刷屏
    app.show("home")
    _pump(root)


def test_child_binding_not_clobbered(root) -> None:
    """② 子件自带的 <Button-1> 不能被覆盖；③ refresh_click 必须幂等。

    用独立 Toplevel 而不是塞进 App 的主内容区：root 已被 App 的
    pack(fill=BOTH, expand=True) 占满，再 pack 的子件会被挤成 0 高而
    **未映射**，未映射控件收不到 <Button-1>，测出来的失败是假失败。
    """
    print("\n② 子件绑定不被覆盖 / ③ refresh_click 幂等")
    top = tk.Toplevel(root)
    top.geometry("420x320+80+80")
    holder = tk.Frame(top, bg="#ffffff")
    holder.pack(fill=tk.BOTH, expand=True)
    nav_hits: list[int] = []
    toggle_hits: list[int] = []

    card = Card(holder, title="", on_click=lambda: nav_hits.append(1))
    card.pack(fill=tk.BOTH, expand=True)
    # 模拟页面里的复选框：自己先绑一个 Button-1
    box = tk.Label(card.body, text="☐ 高级选项", bg="#ffffff")
    box.pack()
    box.bind("<Button-1>", lambda e: toggle_hits.append(1))

    # 调用方补绑内容后刷新点击区，多刷几次验证不会叠加
    card.refresh_click()
    card.refresh_click()
    card.refresh_click()
    _pump(root, 6)
    if not check(box.winfo_ismapped() and card.body.winfo_ismapped(),
                 "测试卡片已映射（否则点击事件会被 Tk 丢掉，是假失败）"):
        top.destroy()
        return

    box.event_generate("<Button-1>", x=3, y=3)
    _pump(root, 2)
    check(toggle_hits == [1],
          f"复选框自己的切换回调存活（实得 {len(toggle_hits)} 次）")
    check(nav_hits == [1],
          f"重复 refresh_click 后卡片跳转只触发一次（实得 {len(nav_hits)} 次）")

    nav_hits.clear()
    card.body.event_generate("<Button-1>", x=2, y=2)
    _pump(root, 2)
    check(nav_hits == [1], f"点卡片空白处触发跳转（实得 {len(nav_hits)} 次）")

    top.destroy()


def test_no_duplicate_textvariable(app, root) -> None:
    """④ 同一页面不允许两个输入框绑同一个变量（photo 页重复控件的指纹）。"""
    print("\n④ 页面内输入框变量不重复")
    from tkinter import ttk
    for key in app.pages:
        app.show(key)
        _pump(root)
        seen: dict[str, str] = {}
        dup: list[str] = []
        for w in _iter(app.pages[key]):
            if isinstance(w, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
                try:
                    var = str(w.cget("textvariable"))
                except Exception:                     # noqa: BLE001
                    continue
                if not var:
                    continue
                if var in seen:
                    dup.append(f"{var}（{seen[var]} 与 {w.winfo_class()}"
                               f"#{w.winfo_name()}）")
                else:
                    seen[var] = f"{w.winfo_class()}#{w.winfo_name()}"
        check(not dup, f"{key} 页无重复变量" + (f"：{dup}" if dup else ""))
    app.show("home")
    _pump(root)


def main() -> int:
    root = TkinterDnD.Tk()
    root.title("t_ui_bind")
    root.geometry("1280x900")
    app = App(root)
    _pump(root)
    test_home_card_text_clickable(app, root)
    test_child_binding_not_clobbered(root)
    test_no_duplicate_textvariable(app, root)
    root.destroy()

    print("\n" + "=" * 60)
    print(f"共 {CHECKS} 项检查，失败 {len(FAILS)} 项。")
    for f in FAILS:
        print(f"  FAIL {f}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
