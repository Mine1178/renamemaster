"""无头自测：验证拖入路径解析与派发逻辑（不需要窗口 / tkinterdnd2 运行时）。

用法：python tests/test_dnd.py
提供 Number 之外的依赖：无（纯字符串 + 临时目录）。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rename_master.ui.dnd import (make_drop_handler, parse_drop_paths,
                                  resolve_source_dir)


class _FakeEvent:
    """模仿 tkinterdnd2 的 <<Drop>> 事件：只带 data 字段。"""

    def __init__(self, data: str):
        self.data = data


class _FakePage:
    """模仿功能页：只暴露 set_source_dir，记录被填入的路径。"""

    def __init__(self):
        self.got = None

    def set_source_dir(self, path: str) -> None:
        self.got = path


class _FakeApp:
    """模仿 App：pages / cur / set_status / pending_drop_path / apply_drop_path。"""

    def __init__(self, page=None):
        self.pages = {"photo": page} if page else {}
        self.cur = "home" if page is None else "photo"
        self.status = ""
        self.pending_drop_path = None

    def set_status(self, text: str, kind: str = "info") -> None:
        self.status = text

    def _source_setter(self):
        page = self.pages.get(self.cur)
        return getattr(page, "set_source_dir", None) if page is not None else None

    def apply_drop_path(self, path: str) -> bool:
        setter = self._source_setter()
        if setter is None:
            self.pending_drop_path = path
            self.set_status("已记住拖入目录，切到功能页自动填入")
            return False
        setter(path)
        return True


def test_parse_windows_brace() -> None:
    """验收点：'{D:\\test}\\' 要 strip 掉大括号与尾部反斜杠，取到 D:\\test。"""
    paths = parse_drop_paths("{D:\\test}\\")
    assert [str(p) for p in paths] == ["D:\\test"], [str(p) for p in paths]
    print("[1/4] 大括号 / 尾斜杠清理通过：D:\\test")


def test_parse_multi_with_space() -> None:
    raw = "{D:/照片/in box} D:/照片/b.jpg"
    # Path 在 Windows 下会把 / 规范成 \，比较时同样统一成 Path
    expect = [str(Path("D:/照片/in box")), str(Path("D:/照片/b.jpg"))]
    paths = [str(p) for p in parse_drop_paths(raw)]
    assert paths == expect, paths
    print(f"[2/4] 多路径（含空格）拆分通过：{paths}")


def test_resolve_source_dir(workdir: Path) -> None:
    root = workdir / "相册"
    sub = root / "子目录"
    sub.mkdir(parents=True)
    (root / "a.jpg").write_bytes(b"x")
    (sub / "b.jpg").write_bytes(b"x")

    # 拖文件夹 → 用它自己
    assert resolve_source_dir(str(root)) == str(root)
    # 拖托盘尾斜杠形式
    assert resolve_source_dir("{%s}\\" % root) == str(root)
    # 拖文件 → 用它的父目录
    assert resolve_source_dir(str(root / "a.jpg")) == str(root)
    # 拖多个：不同目录时取共同目录
    assert resolve_source_dir("{%s} {%s}" % (root / "a.jpg", sub / "b.jpg")) == str(root)
    print(f"[3/4] 源目录折算通过：{root}")


def test_drop_handler(workdir: Path) -> None:
    src = workdir / "拖入测试"
    src.mkdir()
    page = _FakePage()
    app = _FakeApp(page)
    on_drop = make_drop_handler(app)
    on_drop(_FakeEvent("{%s}\\" % src))

    assert page.got == str(src), page.got
    assert app.status == f"已拖入: {src}", app.status
    print(f"[4/4] on_drop 派发通过：page={page.got} | status={app.status}")


def test_pending_on_home(workdir: Path) -> None:
    """在首页拖入时页面还没 build → 暂存到 pending_drop_path。"""
    src = workdir / "首页拖入"
    src.mkdir()
    app = _FakeApp()
    make_drop_handler(app)(_FakeEvent("{%s}\\" % src))
    assert app.pending_drop_path == str(src), app.pending_drop_path
    assert app.status == "已记住拖入目录，切到功能页自动填入", app.status
    print(f"     首页拖入暂存通过：pending_drop_path={app.pending_drop_path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="renamemaster_dnd_") as tmp:
        workdir = Path(tmp)
        test_parse_windows_brace()
        test_parse_multi_with_space()
        test_resolve_source_dir(workdir)
        test_drop_handler(workdir)
        test_pending_on_home(workdir)
    print("DND OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
