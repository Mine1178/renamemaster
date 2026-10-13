"""用 Win32 API 截图当前屏幕。"""
import ctypes
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# 获取屏幕尺寸
SW = user32.GetSystemMetrics(0)
SH = user32.GetSystemMetrics(1)
print(f"屏幕尺寸: {SW}x{SH}")

# 获取桌面窗口 DC
hdc_screen = user32.GetDC(0)
hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, SW, SH)
gdi32.SelectObject(hdc_mem, hbitmap)

# 截图
gdi32.BitBlt(hdc_mem, 0, 0, SW, SH, hdc_screen, 0, 0, 0x00CC0020)

# 保存为 BMP
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

bmi = BITMAPINFOHEADER()
bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.biWidth = SW
bmi.biHeight = -SH
bmi.biPlanes = 1
bmi.biBitCount = 32
bmi.biCompression = 0

buffer_size = SW * SH * 4
buffer = ctypes.create_string_buffer(buffer_size)
gdi32.GetDIBits(hdc_mem, hbitmap, 0, SH, buffer, ctypes.byref(bmi), 0)

# 用 PIL 保存
from PIL import Image
img = Image.frombuffer("RGB", (SW, SH), buffer, "raw", "BGRX", 0, 1)
out = Path(__file__).parent / "screenshots" / "screen.png"
out.parent.mkdir(exist_ok=True)
img.save(str(out))
print(f"截图已保存: {out}")

# 清理
gdi32.DeleteObject(hbitmap)
gdi32.DeleteDC(hdc_mem)
user32.ReleaseDC(0, hdc_screen)
