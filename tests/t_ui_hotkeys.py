"""全局快捷键 + 首页「最近使用」刷新回归（v1.9）。

为什么需要它：v1.8 交付版有三个"用户能感觉到但单元测试抓不到"的缺口——
1. 首页「最近使用」只建一次，执行完一批切回首页还是旧数字；
2. 只有鼠标点底部按钮一条路，Ctrl+O / Ctrl+Enter / Esc 全无反应；
3. Esc 关不掉弹出窗（预览窗只能点按钮）。
本用例真实拉起 App，把这三件事变成可断言的检查。

判定标准
--------
1. `<Control-o>` / `<Control-Return>` / `<Escape>` 三个绑定已注册；
2. 5 个功能页都暴露 `set_source_dir` 与 `hotkey_run`；
3. Ctrl+O 经 `set_source_dir` 把目录填进源目录框并扫出文件（照片页）；
4. Ctrl+Enter 在空列表时走校验分支（弹提示 / 开预览窗），不抛异常；
5. Esc 先关最上层弹出窗，其次置位 `st["cancel"]` 取消执行中批次；
6. `cfg` 里的 output.last_dir / last_count 变化后，切回首页文本随之更新。

用法：python tests/t_ui_hotkeys.py
"""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

from tkinter import messagebox  # noqa: E402
from tkinterdnd2 import TkinterDnD  # noqa: E402

import rename_master.ui.app as app_mod  # noqa: E402
from rename_master.ui.app import App  # noqa: E402

FUNC_PAGES = ["photo", "pdf", "spreadsheet", "document"]


def _iter(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _iter(child)


def _texts(widget) -> list[str]:
    """收集子树里所有控件的 text（vlabel 是 Text，需走 cget('text')）。"""
    out = []
    for w in _iter(widget):
        try:
            t = w.cget("text")
        except Exception:  # noqa: BLE001
            continue
        if t:
            out.append(str(t))
    return out


def _toplevels(root) -> list:
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]


class _BoxRecorder:
    """替换 messagebox 弹窗函数：记录调用并立即返回，避免测试被模态窗卡死。"""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self._orig: dict[str, object] = {}

    def install(self) -> None:
        for name, ret in (("showwarning", None), ("showerror", None),
                          ("showinfo", None), ("askyesno", False)):
            self._orig[name] = getattr(messagebox, name)
            setattr(messagebox, name, self._make(name, ret))

    def _make(self, name, ret):
        def _fn(title="", message="", **_kw):
            self.calls.append((str(title), str(message)))
            return ret
        return _fn

    def restore(self) -> None:
        for name, orig in self._orig.items():
            setattr(messagebox, name, orig)


def _make_png(path: Path) -> None:
    from PIL import Image
    Image.new("RGB", (16, 16), (200, 120, 40)).save(path)


def main() -> int:
    problems: list[str] = []

    def check(cond: bool, msg: str) -> bool:
        if not cond:
            problems.append(msg)
        return bool(cond)

    root = TkinterDnD.Tk()
    root.geometry("1280x820")
    app = App(root)
    root.update_idletasks()
    root.update()

    # ---------- ① 三个快捷键已注册 ----------
    for seq in ("<Control-o>", "<Control-Return>", "<Escape>"):
        check(bool(root.bind_all(seq)),
              f"快捷键未注册：{seq}（bind_all 返回空）")

    # ---------- ② 各功能页暴露 set_source_dir / hotkey_run ----------
    for key in FUNC_PAGES:
        try:
            app.show(key)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{key}: show() 抛异常 {exc!r}")
            continue
        root.update()
        page = app.pages[key]
        check(callable(getattr(page, "set_source_dir", None)),
              f"{key}: 缺 set_source_dir（Ctrl+O 无落点）")
        check(callable(getattr(page, "hotkey_run", None)),
              f"{key}: 缺 hotkey_run（Ctrl+Enter 无落点）")

    # ---------- ③ Ctrl+O：选目录 → 填入源目录框 ----------
    with TemporaryDirectory(prefix="rm_hotkey_") as tmp:
        tmp_path = Path(tmp)
        _make_png(tmp_path / "a.png")
        _make_png(tmp_path / "b.png")

        orig_ask = app_mod.filedialog.askdirectory
        app_mod.filedialog.askdirectory = lambda **_kw: str(tmp_path)
        try:
            app.show("photo")
            root.update()
            app._hotkey_open()
            root.update()
            st = app.pages["photo"].st
            check(st["src_dir"].get() == str(tmp_path),
                  f"Ctrl+O 未填入源目录：{st['src_dir'].get()!r}")
            check(len(st["files"]) == 2,
                  f"Ctrl+O 未扫出图片：files={len(st['files'])}（期望 2）")

            # 首页没有源目录输入框：不能抛异常，只能给状态提示
            app.show("home")
            root.update()
            app._hotkey_open()
            root.update()
            check("首页" in app.status.get() or "源目录" in app.status.get(),
                  f"Ctrl+O 在首页没有提示，状态栏={app.status.get()!r}")
        finally:
            app_mod.filedialog.askdirectory = orig_ask

    # ---------- ④ Ctrl+Enter：空列表走校验分支，不崩 ----------
    rec = _BoxRecorder()
    rec.install()
    try:
        for key in FUNC_PAGES:
            app.show(key)
            root.update()
            page = app.pages[key]
            if isinstance(getattr(page, "st", None), dict):
                page.st["files"].clear()          # 保证走"缺文件"分支
            before = len(_toplevels(root))
            box_before = len(rec.calls)
            try:
                app._hotkey_run()
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{key}: Ctrl+Enter 抛异常 {exc!r}")
                continue
            root.update()
            boxed = len(rec.calls) > box_before
            opened = len(_toplevels(root)) > before
            check(boxed or opened,
                  f"{key}: Ctrl+Enter 无任何反应（既没提示也没开预览窗）")
            for extra in _toplevels(root)[before:]:
                try:
                    extra.destroy()
                except tk.TclError:
                    pass
            root.update()

        # ---------- ⑤ Esc：先关弹出窗 ----------
        dlg = tk.Toplevel(root)
        dlg.title("假预览窗")
        root.update()
        check(len(_toplevels(root)) > 0, "Esc 用例前置失败：弹窗没建起来")
        app._hotkey_escape()
        root.update()
        check(len(_toplevels(root)) == 0,
              f"Esc 没关掉弹出窗，仍有 {len(_toplevels(root))} 个 Toplevel")

        # ---------- ⑤b Esc：没有弹窗时取消执行中批次 ----------
        app.show("photo")
        root.update()
        ev = threading.Event()
        app.pages["photo"].st["cancel"] = ev
        try:
            app._hotkey_escape()
            check(ev.is_set(), "Esc 未置位 cancel（执行中批次取消失效）")
            # 没有任务在跑时：不崩、状态栏给说明
            app.pages["photo"].st["cancel"] = None
            app._hotkey_escape()
            check("执行" in app.status.get() or "Esc" in app.status.get(),
                  f"Esc 空转时状态栏无说明：{app.status.get()!r}")
        finally:
            app.pages["photo"].st["cancel"] = None
    finally:
        rec.restore()

    # ---------- ⑥ 首页「最近使用」实时刷新 ----------
    app.show("home")
    root.update()
    check(callable(getattr(app.pages["home"], "refresh", None)),
          "首页缺 refresh 钩子（App.show 无法刷新最近使用）")
    app.cfg.set("output.last_dir", r"D:\Desktop\SD\13.Rename\pic_重命名输出")
    app.cfg.set("output.last_count", 128)
    app.show("photo")          # 先离开首页，模拟"执行完再切回来"
    root.update()
    app.show("home")
    root.update()
    texts = " | ".join(_texts(app.pages["home"]))
    check("pic_重命名输出" in texts, f"首页未刷新输出目录：{texts[:200]}")
    check("128 个文件" in texts, f"首页未刷新批次数量：{texts[:300]}")

    root.destroy()

    if problems:
        print(f"\n共 {len(problems)} 项快捷键 / 刷新问题：")
        for p in problems:
            print(f"  FAIL {p}")
        return 1
    print("\n快捷键与首页刷新检查全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
