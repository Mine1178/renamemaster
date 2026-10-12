"""拖放到主窗口的支持：解析 Windows 拖入的路径，并派发给当前页面。

tkinterdnd2 的 DND_FILES 数据是 Tk 列表格式：每项要么是裸路径，
要么被大括号包起来（路径含空格时必须包）。例：
    D:/照片/a.jpg
    {D:/照片/in box} {D:/照片/b.jpg}

本模块只做纯字符串逻辑（不 import tkinter），便于无头环境直接单测。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional


def parse_drop_paths(raw: str) -> List[Path]:
    """把 DND_FILES 的原始数据拆成一组路径（自动去大括号 / 末尾斜杠）。"""
    text = (raw or "").strip()
    out: List[Path] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():                      # 项分隔符
            i += 1
            continue
        if ch == "{":                         # 含空格的路径整段被包起来
            end = text.find("}", i)
            if end == -1:                     # 缺失右括号：剩下的全当作路径
                out.append(Path(text[i + 1:].strip()))
                break
            out.append(Path(text[i + 1:end].strip()))
            i = end + 1
            continue
        end = i
        while end < n and not text[end].isspace() and text[end] != "{":
            end += 1
        out.append(Path(text[i:end]))
        i = end
    # Windows 有时会多带一个尾随反斜杠（'{D:\\test}\\'）：剔除空 / 纯分隔符项
    return [Path(_strip_trailing_sep(str(p))) for p in out
            if str(p).strip("\\/")]


def _strip_trailing_sep(text: str) -> str:
    """去掉末尾多余分隔符，但保住盘符根目录（"D:\\" 剥成 "D:" 会变另一个含义）。"""
    stripped = text.rstrip("\\/")
    if not stripped or (len(stripped) == 2 and stripped[1] == ":"):
        return text
    return stripped


def resolve_source_dir(raw: str) -> Optional[str]:
    """把拖入数据折算成一个源目录。

    - 拖入目录：直接用它；
    - 拖入文件：用它的父目录；
    - 拖入多个：取共同目录（跨盘符时退化到第一个）。
    """
    paths = parse_drop_paths(raw)
    if not paths:
        return None
    dirs: List[str] = []
    for p in paths:
        try:
            d = str(p) if p.is_dir() else str(p.parent)
        except OSError:                       # 非法盘符 / 权限问题：退回 parent
            d = str(p.parent)
        dirs.append(d)
    try:
        common = os.path.commonpath(dirs)
    except ValueError:
        common = dirs[0]
    return common or dirs[0]


def make_drop_handler(app) -> Callable[[object], None]:
    """生成绑定到 '<<Drop>>' 的回调；app 需提供 apply_drop_path / set_status。"""

    def on_drop(event) -> None:
        raw = getattr(event, "data", "")
        dir_path = resolve_source_dir(raw)
        if not dir_path:
            app.set_status("拖入的不是有效路径", "warn")
            return
        applied = app.apply_drop_path(dir_path)
        if applied:                       # 未应用（暂存）时保留页面的提示文案
            app.set_status(f"已拖入: {dir_path}", "ok")

    return on_drop
