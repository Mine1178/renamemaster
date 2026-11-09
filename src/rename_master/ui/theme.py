"""UI 配色规范（照抄 Wifibond theme.py，任务书 §4.3 / §4.4）。

所有页面 / 组件必须引用本模块常量，禁止在业务代码里硬编码色值、间距、字号。
"""
from __future__ import annotations

# ---------- 主配色 ----------
C_PRIMARY = "#1e293b"        # 左侧导航栏底色
C_SECONDARY = "#334155"      # 导航激活项 / 按钮 hover 背景
C_ACCENT = "#d97706"         # 强调色：Logo、分隔线、卡片顶条、主按钮
C_ACCENT_HOVER = "#b45309"   # 强调按钮 hover 深橙
C_BG = "#f1f5f9"             # 内容区底色
C_CARD = "#ffffff"           # 卡片底色
C_TEXT = "#0f172a"           # 主文字
C_TEXT_M = "#475569"         # 中级文字
C_TEXT_L = "#64748b"         # 次级文字
C_TEXT_SUB = "#64748b"       # 卡片描述等次级正文
C_TEXT_FADE = "#94a3b8"      # 导航未激活文字
C_BORDER = "#e2e8f0"         # 卡片边框
C_HOVER = "#eef2ff"          # 卡片 hover 背景
C_ROW_ALT = "#f8fafc"        # 表格隔行条纹底色
C_LOGO_SUB = "#9aa6c4"       # Logo 副标题（深底上小字可读）
C_SUCCESS = "#16a34a"        # 状态正常（绿 ✓）
C_DANGER = "#dc2626"         # 状态错误（红 ✗）
C_WARNING = "#ca8a04"        # 状态警告（黄 ⚠）
C_INFO = "#2563eb"           # 信息蓝
C_PURPLE = "#7c3aed"         # 紫色（PDF 入口）
C_WHITE = "#ffffff"          # 强调按钮前景

FONT_FAMILY = "微软雅黑"

# 左导航逻辑宽度 112px（高 DPI 下按 ui_scale 放大到物理像素，视觉宽度不变）
NAV_WIDTH = 112
LOGO_HEIGHT = 110
TREE_ROW_HEIGHT = 30         # Treeview 行高（高 DPI 下不至于过密）
SB_WIDTH = 12                # 内容区右侧竖向滚动条预留槽位（常驻，避免显隐时抖动）

# ---------- 间距系统（8pt 基准）----------
S_XS = 4
S_SM = 8
S_MD = 12                    # 卡片内边距标准值
S_LG = 16                    # 区块之间 / 页面外边距
S_XL = 24

# 卡片 body 内边距（所有 Card.body 统一引用，禁止各页各写一份）
CARD_BODY_PAD = S_MD

# ---------- 字体层级 ----------
F_H1 = 20        # 页面主标题
F_TITLE = 16     # 弹窗 / 卡片大标题
F_SECTION = 12   # 分区 / 卡片小标题（粗体）
F_LEAD = 12      # 卡片内强调正文（按钮、品牌名）
F_BODY = 10      # 正文
F_SM = 9         # 辅助说明
F_METRIC = 14    # 指标数字
F_CHECK = 18     # 自定义方框复选框 ☑/☐
F_ICON = 30      # 首页功能卡大图标
F_DISPLAY = 36   # 弹窗装饰图标
F_HERO = 44      # 关于页品牌大图标

# ---------- 尺寸约束（响应式用）----------
PAGE_MIN_W = 720     # 内容区最小可读宽度
CARD_MIN_W = 240     # 卡片最小宽度，用于动态计算列数
CARD_MAX_COLS = 3    # 卡片最大列数
