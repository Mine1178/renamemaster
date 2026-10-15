import sys
sys.path.insert(0, 'src')
import tkinter as tk
import threading, time, os
from rename_master.ui.app import App
from rename_master.ui.pages import watermark as wm_mod

def log(msg):
    with open(r'D:/Desktop/SD/13.Rename/tests/_dbg_wm.log', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

# 清空旧 log
log_file = r'D:/Desktop/SD/13.Rename/tests/_dbg_wm.log'
open(log_file, 'w').close()

finished = threading.Event()
def _info(*a, **k):
        log('[fin] ' + repr(a[0])[:60])
        finished.set()
        return 'ok'
def _warn(*a, **k):
        log('[warn] ' + repr(a[0])[:60])
        return 'ok'
wm_mod.messagebox.showinfo = _info
wm_mod.messagebox.showwarning = _warn

root = tk.Tk()
app = App(root)
app.show('watermark')
for _ in range(8): root.update()
page = app.pages['watermark']
st = page.st
st['vis_on'].set(True); st['blind_on'].set(False); st['vis_layout'].set('tile')
page.vis_text_box.delete('1.0', 'end'); page.vis_text_box.insert('1.0', 'TEST')
import tempfile, shutil
SRC = os.path.join(tempfile.gettempdir(), 'rm_wm_dbgA')
shutil.rmtree(SRC, ignore_errors=True); os.makedirs(SRC, exist_ok=True)
from PIL import Image
for i in range(2):
        Image.new('RGB', (400, 300), (200, 100, 50)).save(os.path.join(SRC, f'img{i}.jpg'))
OUT = os.path.join(tempfile.gettempdir(), 'rm_wm_dbgA_out')
shutil.rmtree(OUT, ignore_errors=True)
st['out_dir'].set(OUT)
st['files'].clear()
page.set_source_dir(SRC)
for _ in range(4): root.update()
log('setup ok')

toplevels = []
_orig = tk.Toplevel
def _spy(*a, **k):
        w = _orig(*a, **k)
        toplevels.append(w)
        return w
tk.Toplevel = _spy

def walk(w):
        if type(w).__name__ == 'Button' and '开始执行' in str(w.cget('text')):
                return w
        for c in w.winfo_children():
                r = walk(c)
                if r: return r
        return None
walk(app._action_bars['watermark']).invoke()
root.update(); time.sleep(0.05)
log('after invoke 1')

def walk_c(w):
        if type(w).__name__ == 'Button' and '确认执行' in str(w.cget('text')):
                return w
        for c in w.winfo_children():
                r = walk_c(c)
                if r: return r
        return None
btn_c = walk_c(toplevels[0])
btn_c.invoke()
log('btn_c invoked')
time.sleep(1.0)
log(f'OUT exists={os.path.isdir(OUT)} files={os.listdir(OUT) if os.path.isdir(OUT) else None}')
for i in range(40):
        root.update()
        if finished.is_set():
                log(f'fin at {i}')
                break
        time.sleep(0.1)
log(f'final finished={finished.is_set()}')