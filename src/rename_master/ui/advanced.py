"""高级选项共享卡片：排序 / 查找替换（含正则） / 日期变量，4 个功能页复用。

用法（每个功能页 3 处接入）：
    from rename_master.ui import advanced
    adv = advanced.create_vars(app, "photo")          # 放进 st
    advanced.build_card(page, app, adv)               # ②命名规则 之后
    advanced.apply_to_rule(rule, adv)                 # 组装 rule 时
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from rename_master.ui import theme as T
from rename_master.ui.widgets import Card, hint_label, vlabel, enable_label_copy

# (内部 key, 显示文字)
SORT_CHOICES = [
    ("", "不排序（按列表顺序）"),
    ("name", "文件名"),
    ("mtime", "修改时间"),
    ("size", "文件大小"),
    ("exif", "拍摄时间(照片)"),
]
_LABEL_TO_KEY = {label: key for key, label in SORT_CHOICES}
_KEY_TO_LABEL = {key: label for key, label in SORT_CHOICES}


def _check(master, text: str, variable: tk.Variable) -> tk.Checkbutton:
    w = tk.Checkbutton(master, text=text, variable=variable,
                       bg=T.C_CARD, fg=T.C_TEXT, activebackground=T.C_CARD,
                       activeforeground=T.C_ACCENT, selectcolor=T.C_CARD,
                       highlightthickness=0, font=(T.FONT_FAMILY, T.F_BODY),
                       anchor="w", cursor="hand2")
    enable_label_copy(w)
    return w


def create_vars(app, cfg_prefix: str) -> dict:
    """创建一组高级选项状态变量（从配置读默认值）。"""
    def g(k, d):
        return app.cfg.get(f"{cfg_prefix}.{k}", d)

    adv = {
        "sort_by": tk.StringVar(value=str(g("sort_by", ""))),
        "sort_desc": tk.BooleanVar(value=bool(g("sort_desc", False))),
        "find": tk.StringVar(value=str(g("find", ""))),
        "repl": tk.StringVar(value=str(g("repl", ""))),
        "use_regex": tk.BooleanVar(value=bool(g("use_regex", False))),
    }
    adv["sort_label"] = tk.StringVar(
        value=_KEY_TO_LABEL.get(adv["sort_by"].get(), SORT_CHOICES[0][1]))
    return adv


def build_card(page, app, adv: dict) -> Card:
    """构建「高级选项」卡片：排序一行、查找替换一行、变量说明一行。"""
    card = Card(page, "高级选项（可选）",
                "排序决定序号顺序 · 查找替换批量改字 · 基础名称支持日期变量",
                accent=T.C_INFO, collapsible=True, start_collapsed=True)
    card.pack(fill=tk.X, pady=(0, T.S_MD))

    # ---- 排序行 ----
    row1 = tk.Frame(card.body, bg=T.C_CARD)
    row1.pack(fill=tk.X)
    vlabel(row1, text="排序", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
           fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    sort_combo = ttk.Combobox(row1, textvariable=adv["sort_label"],
                              values=[c[1] for c in SORT_CHOICES],
                              state="readonly", width=18,
                              style="RenameMaster.TCombobox")
    sort_combo.pack(side=tk.LEFT, padx=(T.S_SM, T.S_SM))
    sort_combo.bind(
        "<<ComboboxSelected>>",
        lambda _e: adv["sort_by"].set(
            _LABEL_TO_KEY.get(adv["sort_label"].get(), "")))
    _check(row1, "降序", adv["sort_desc"]).pack(side=tk.LEFT)

    # ---- 查找替换行 ----
    row2 = tk.Frame(card.body, bg=T.C_CARD)
    row2.pack(fill=tk.X, pady=(T.S_SM, 0))
    vlabel(row2, text="查找", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
           fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row2, textvariable=adv["find"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER, highlightthickness=1,
             width=16).pack(side=tk.LEFT, padx=(T.S_SM, T.S_MD))
    vlabel(row2, text="替换为", font=(T.FONT_FAMILY, T.F_BODY), bg=T.C_CARD,
           fg=T.C_TEXT_M, anchor="w").pack(side=tk.LEFT)
    tk.Entry(row2, textvariable=adv["repl"], relief=tk.FLAT, bg=T.C_CARD,
             fg=T.C_TEXT, highlightbackground=T.C_BORDER, highlightthickness=1,
             width=16).pack(side=tk.LEFT, padx=(T.S_SM, T.S_SM))
    _check(row2, "正则", adv["use_regex"]).pack(side=tk.LEFT)

    # ---- 变量说明（一行显示，不换行）----
    hint_label(
        card.body,
        "基础名称可写：{date}今天 {mtime}修改时间 {exif}拍摄时间 {parent}父文件夹；"
        "正则示例：查找 (\\d+) 替换 P\\1",
    ).pack(fill=tk.X, pady=(T.S_SM, 0))
    return card


def apply_to_rule(rule: dict, adv: dict) -> dict:
    """把高级选项合入命名 rule（引擎据此排序 / 查找替换）。"""
    rule["sort_by"] = adv["sort_by"].get()
    rule["sort_desc"] = bool(adv["sort_desc"].get())
    rule["find"] = adv["find"].get()
    rule["repl"] = adv["repl"].get()
    rule["use_regex"] = bool(adv["use_regex"].get())
    return rule


def save_prefs(app, cfg_prefix: str, adv: dict) -> None:
    """把高级选项写回配置（下次打开记住）。"""
    for k in ("sort_by", "sort_desc", "find", "repl", "use_regex"):
        app.cfg.set(f"{cfg_prefix}.{k}", adv[k].get())
