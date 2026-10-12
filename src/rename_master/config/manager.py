"""配置读写：JSON 存 %APPDATA%\\RenameMaster\\config.json（与 Wifibond 同款）。

用法：
    cfg = ConfigManager()
    cfg.get("output.last_dir", "")     # 点号路径取值，缺失返回默认值
    cfg.set("output.last_dir", "D:\\x")
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict

APP_NAME = "RenameMaster"

# Windows：%APPDATA%\RenameMaster；其它系统回退到用户目录
_base = os.environ.get("APPDATA") or str(Path.home())
CONFIG_DIR = Path(_base) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "photo": {
        "mode": "prefix",          # prefix | map
        "base_name": "",
        "digits": 3,
        "start": 1,
        "sep": "_",
        "keep_ext": True,
        "date_prefix": False,
        "compress": "none",        # none | 1024 | 500 | 200 | 100 | custom
        "custom_kb": 300,
        "keep_exif": True,
        "backup_originals": False,
    },
    "output": {
        "last_dir": "",
        "last_count": 0,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ConfigManager:
    """线程安全的 JSON 配置管理器（读写均加锁，后台线程也能安全落盘）。"""

    def __init__(self, path: os.PathLike | str | None = None):
        self.path = Path(path) if path is not None else CONFIG_PATH
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self.load()

    # ---------- 持久化 ----------
    def load(self) -> Dict[str, Any]:
        with self._lock:
            data: Dict[str, Any] = {}
            try:
                if self.path.is_file():
                    with open(self.path, "r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        data = loaded
            except (OSError, ValueError):
                data = {}
            self._data = _deep_merge(DEFAULT_CONFIG, data)
            return self._data

    def save(self) -> None:
        """原子写盘（先写临时文件再 replace），避免写一半崩溃导致配置损坏。"""
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".json.tmp")
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(self._data, fh, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)
            except OSError:
                pass

    # ---------- 点号路径读写 ----------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            cur: Any = self._data
            for part in str(key).split("."):
                if not isinstance(cur, dict) or part not in cur:
                    return default
                cur = cur[part]
            return cur

    def set(self, key: str, value: Any) -> None:
        parts = str(key).split(".")
        with self._lock:
            cur = self._data
            for part in parts[:-1]:
                nxt = cur.get(part)
                if not isinstance(nxt, dict):
                    nxt = {}
                    cur[part] = nxt
                cur = nxt
            cur[parts[-1]] = value

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)
