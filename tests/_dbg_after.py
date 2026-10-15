import sys
import tkinter as tk
import time

log_path = r'D:/Desktop/SD/13.Rename/tests/_dbg_after.log'
def log(msg):
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

open(log_path, 'w').close()

log('start')

root = tk.Tk()
log('root created')
root.withdraw()

# 手动用 after 调度
fired = [False]
def cb():
    fired[0] = True
    log('callback fired')

# 用 update_idletasks + mainloop iteration
root.after_idle(cb)
log('after_idle scheduled')

# 跑 mainloop 5 秒
root.after(5000, root.quit)
root.mainloop()
log(f'after mainloop: fired={fired[0]}')
root.destroy()