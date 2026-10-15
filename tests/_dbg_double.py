import sys, time, os
sys.path.insert(0, 'src')
from PIL import Image
from rename_master.core import watermark, blind_wm
import tempfile, shutil

WORK = tempfile.mkdtemp(prefix='wm_repro_')
SRC = os.path.join(WORK, 'src')
OUT = os.path.join(WORK, 'out')
os.makedirs(SRC, exist_ok=True)

# 造 3 张图
for i in range(3):
    img = Image.new('RGB', (300, 200), ((i*30) % 256, 100, 200))
    img.save(os.path.join(SRC, f'img{i}.jpg'))

# 双保险流程：嵌入盲水印 → 叠加可见水印
out_paths = []
t0 = time.time()
for i in range(3):
    src = os.path.join(SRC, f'img{i}.jpg')
    tmp = os.path.join(WORK, f'tmp{i}.png')
    print(f'[{i}] embed_blind... ', end='', flush=True)
    wlen = blind_wm.embed_watermark(src, tmp, 'test text', password_wm=1)
    print(f'wlen={wlen}', flush=True)

    print(f'[{i}] read + visible... ', end='', flush=True)
    with open(tmp, 'rb') as f:
        data = f.read()
    out_data = watermark.apply_watermark(
        data, text='VISIBLE', layout='tile',
        color='#D4A017', opacity=0.15, angle=30)
    print(f'len={len(out_data)}', flush=True)

    out_path = os.path.join(OUT, f'out{i}.jpg')
    os.makedirs(OUT, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(out_data)
    out_paths.append(out_path)
    print(f'[{i}] wrote {out_path}', flush=True)
    os.remove(tmp)

print(f'\nTotal: {time.time()-t0:.2f}s')
print('OUT files:', os.listdir(OUT))

# Extract to verify
for p in out_paths:
    txt = blind_wm.extract_watermark(p, wlen, password_wm=1)
    print(f'  {os.path.basename(p)} → {txt!r}')