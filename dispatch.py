# -*- coding: utf-8 -*-
"""
dispatch.py — 豆包 -> WorkBuddy 派活桥（双 AI 协作闭环核心工具）

用法：
  python dispatch.py "任务内容" [--cwd D:/path] [--timeout 300] [--debug]
  python dispatch.py --stop          # 停止本地 serve 服务
  python dispatch.py --status        # 查看 serve 与登录态

原理：
  从 WorkBuddy 运行内存提取账号 token（缓存至 .cache/wb_token.txt），
  注入 CODEBUDDY_AUTH_TOKEN 启动 headless CLI 的 HTTP 服务（--auth none
  --permission-mode auto），再通过 POST /api/v1/runs 派任务、SSE 流读结果。

可配置项（环境变量，未设时用默认值）：
  WB_CLI_PATH   WorkBuddy headless CLI 绝对路径（默认本机安装路径）
  WB_PORT       serve 端口（默认 51741）
  WB_PROJECT    默认工作目录（默认当前目录）
"""
import argparse, base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, uuid

# ---------- 关键：绕过系统/环境 HTTP 代理 ----------
# 环境里若有 HTTP_PROXY/HTTPS_PROXY（如 WorkBuddy 自带的本地代理），urllib 默认会把
# 127.0.0.1 的请求也发给代理，导致 502 Bad Gateway / 无法连接，且 port_busy() 误判"服务在跑"。
# 本机 loopback 通信必须直连，统一走这个 opener。
_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# ---------- 配置（环境变量可覆盖，便于换机/换项目） ----------
CLI = os.environ.get("WB_CLI_PATH",
    r"E:\LenovoSoftstore\Install\WorkBuddy\resources\app.asar.unpacked\cli\dist\codebuddy-headless.js")
PORT = int(os.environ.get("WB_PORT", "51741"))
PROJECT = os.environ.get("WB_PROJECT", os.getcwd())
CACHE_DIR = os.path.join(PROJECT, ".cache")
TOKEN_CACHE = os.path.join(CACHE_DIR, "wb_token.txt")
BASE = f"http://127.0.0.1:{PORT}"
PID_FILE = os.path.join(CACHE_DIR, "serve.pid")
LOG_FILE = os.path.join(CACHE_DIR, "serve.log")

# ---------- token ----------
def token_valid(tok):
    try:
        h, p, s = tok.split(".")
        payload = json.loads(base64.urlsafe_b64decode(p + "=="))
        return payload.get("iss") and "realms" in payload.get("iss", "") and payload.get("exp", 0) > time.time() + 3600
    except Exception:
        return False

def load_token():
    if os.path.exists(TOKEN_CACHE):
        tok = open(TOKEN_CACHE, encoding="utf-8").read().strip()
        if token_valid(tok):
            return tok
    return extract_token()

def extract_token():
    """扫描 WorkBuddy daemon 进程内存找账号 JWT（需桌面版正在运行且已登录）"""
    import ctypes, ctypes.wintypes
    k32 = ctypes.windll.kernel32
    ntdll = ctypes.windll.ntdll
    class PBI(ctypes.Structure):
        _fields_ = [("R1", ctypes.c_void_p), ("Peb", ctypes.c_void_p), ("R2", ctypes.c_void_p * 2),
                    ("Pid", ctypes.c_void_p), ("R3", ctypes.c_void_p)]
    class MBI(ctypes.Structure):
        _fields_ = [("Base", ctypes.c_void_p), ("Alloc", ctypes.c_void_p), ("Prot", ctypes.wintypes.DWORD),
                    ("Size", ctypes.c_size_t), ("State", ctypes.wintypes.DWORD),
                    ("Prot2", ctypes.wintypes.DWORD), ("Type", ctypes.wintypes.DWORD)]
    # 找 daemon 进程（命令行含 daemon-app-server-entry.js）
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'daemon-app-server-entry' } | Select-Object -ExpandProperty ProcessId"],
        capture_output=True, text=True).stdout
    pids = [int(x) for x in re.findall(r"\d+", out)]
    if not pids:
        print("ERR: 未找到 WorkBuddy daemon 进程（WorkBuddy 桌面版在运行吗？）", file=sys.stderr)
        sys.exit(1)
    jwt_re = re.compile(rb"eyJ[A-Za-z0-9_\-]{10,2000}\.[A-Za-z0-9_\-]{10,4000}\.[A-Za-z0-9_\-]{10,2000}")
    for pid in pids:
        h = k32.OpenProcess(0x0410, False, pid)  # QUERY_LIMITED | VM_READ
        if not h:
            continue
        try:
            pbi = PBI()
            if ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), None) != 0:
                continue
            ptr = ctypes.c_void_p()
            sz = ctypes.c_size_t()
            if not k32.ReadProcessMemory(h, ctypes.c_void_p(pbi.Peb + 0x20), ctypes.byref(ptr), 8, ctypes.byref(sz)):
                continue
            envp = ctypes.c_void_p()
            if not k32.ReadProcessMemory(h, ctypes.c_void_p(ptr.value + 0x80), ctypes.byref(envp), 8, ctypes.byref(sz)):
                continue
            mbi = MBI()
            addr = 0
            while True:
                if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
                    break
                base, size = mbi.Base or 0, mbi.Size or 0
                if mbi.State == 0x1000 and size > 0 and mbi.Prot2 in (0x04, 0x02, 0x08, 0x40, 0x20):
                    buf = ctypes.create_string_buffer(size)
                    rd = ctypes.c_size_t()
                    if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(rd)) and rd.value:
                        for m in jwt_re.finditer(buf.raw[:rd.value]):
                            tok = m.group(0).decode()
                            try:
                                hp, pp, sp = tok.split(".")
                                pl = json.loads(base64.urlsafe_b64decode(pp + "=="))
                                if pl.get("iss") and "realms" in pl.get("iss", "") and pl.get("exp", 0) > time.time() + 3600:
                                    os.makedirs(CACHE_DIR, exist_ok=True)
                                    open(TOKEN_CACHE, "w", encoding="utf-8").write(tok)
                                    return tok
                            except Exception:
                                pass
                try:
                    na = base + size
                    addr = na
                    if na >= (1 << 48):
                        break
                except OverflowError:
                    break
        finally:
            k32.CloseHandle(h)
    print("ERR: 内存中未找到有效账号 token（WorkBuddy 未登录？）", file=sys.stderr)
    sys.exit(1)

# ---------- serve ----------
def port_busy():
    """判断 serve 是否真在监听 127.0.0.1:PORT。

    注意：必须直连（_NO_PROXY_OPENER），否则经过环境代理拿到的是代理返回的
    502 Bad Gateway，会被 HTTPError 分支误判为"服务活着"，从而跳过启动、直接派活失败。
    """
    req = urllib.request.Request(f"{BASE}/api/v1/health", headers={"x-codebuddy-request": str(uuid.uuid4())})
    try:
        _NO_PROXY_OPENER.open(req, timeout=3)
        return True
    except urllib.error.HTTPError as e:
        # 401/403 等 = 服务确实在跑（只是要鉴权）；502/503/504 是代理或网关的错误，不算存活
        return e.code not in (502, 503, 504)
    except Exception:
        return False

def ensure_server(tok):
    if port_busy():
        return True
    os.makedirs(CACHE_DIR, exist_ok=True)
    env = dict(os.environ)
    env["CODEBUDDY_AUTH_TOKEN"] = tok
    env["CODEBUDDY_HOST"] = "workbuddy-desktop"
    # 关键：新版 CLI（v2.156+）里 `--auth none` 会被 settings.json 的 gateway.auth 或
    # 内建默认( password ) 覆盖，必须用 CODEBUDDY_GATEWAY_AUTH=none 才能真正关闭鉴权，
    # 否则 /api/v1/runs 返回 401 AUTH_REQUIRED。
    env["CODEBUDDY_GATEWAY_AUTH"] = "none"
    log = open(LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(["node", CLI, "--serve", "--port", str(PORT), "--auth", "none",
                             "--permission-mode", "auto"],
                            cwd=PROJECT, env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    open(PID_FILE, "w").write(str(proc.pid))
    for _ in range(30):
        time.sleep(1)
        if port_busy():
            return True
    print("ERR: serve 启动失败，日志见 .cache/serve.log", file=sys.stderr)
    sys.exit(1)

def stop_server():
    if os.path.exists(PID_FILE):
        pid = int(open(PID_FILE).read().strip())
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            print(f"已停止 serve (pid {pid})")
        except Exception:
            print("停止失败")
    else:
        print("没有记录到 serve 进程")

# ---------- HTTP ----------
def _req(path, method="GET", data=None, timeout=10):
    headers = {"x-codebuddy-request": str(uuid.uuid4())}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        resp = _NO_PROXY_OPENER.open(r, timeout=timeout)
        return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")

def _extract_text(obj, out):
    """递归收集 JSON 里的文本字段（text / content.markdown 等）"""
    if isinstance(obj, dict):
        for key in ("text", "markdown"):
            t = obj.get(key)
            if isinstance(t, str) and t.strip():
                out.append(t)
        for v in obj.values():
            _extract_text(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _extract_text(v, out)

# ---------- 派活 ----------
def dispatch(text, cwd, timeout, debug):
    tok = load_token()
    ensure_server(tok)
    st, body = _req("/api/v1/runs", "POST", {
        "id": str(uuid.uuid4()),
        "type": "message",
        "version": "1.0",
        "source": {"platform": "generic", "sender": {"id": "doubao", "name": "豆包"}, "conversation": {"id": str(uuid.uuid4()), "type": "direct"}},
        "text": text,
        "timeoutMs": timeout * 1000,
    }, timeout=15)
    if st != 202:
        print(f"ERR: 派任务失败 {st}: {body[:300]}", file=sys.stderr)
        sys.exit(1)
    run_id = json.loads(body)["data"]["runId"]
    print(f"[ok] 任务已派发 runId={run_id}，等待 agent 执行（{timeout}s）...", file=sys.stderr)
    # 读 SSE
    req = urllib.request.Request(f"{BASE}/api/v1/runs/{run_id}/stream",
                                 headers={"x-codebuddy-request": str(uuid.uuid4())})
    collected = []
    raw = []
    try:
        resp = _NO_PROXY_OPENER.open(req, timeout=timeout + 10)
        end = time.time() + timeout
        while time.time() < end:
            line = resp.readline()
            if not line:
                break
            txt = line.decode("utf-8", errors="replace").strip()
            if not txt:
                continue
            raw.append(txt)
            if debug:
                print("EVENT:", txt[:200], file=sys.stderr)
            if txt.startswith("data:"):
                try:
                    obj = json.loads(txt[5:].strip())
                    _extract_text(obj, collected)
                except Exception:
                    pass
    except Exception as e:
        print(f"warn: SSE 读取中断 ({e})", file=sys.stderr)
    if collected:
        print("\n".join(collected[-40:]))
    else:
        print("(agent 未返回文本内容，--debug 查看原始事件)")

# ---------- main ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="豆包 -> WorkBuddy 派活")
    ap.add_argument("task", nargs="?", help="任务内容")
    ap.add_argument("--cwd", default=PROJECT, help="工作目录（默认项目目录）")
    ap.add_argument("--timeout", type=int, default=300, help="任务超时秒数")
    ap.add_argument("--debug", action="store_true", help="打印原始 SSE 事件")
    ap.add_argument("--stop", action="store_true", help="停止 serve")
    ap.add_argument("--status", action="store_true", help="查看状态")
    args = ap.parse_args()
    if args.stop:
        stop_server()
    elif args.status:
        tok = load_token()
        print("token:", "有效" if token_valid(tok) else "无效")
        print("serve:", "运行中" if port_busy() else "未运行")
    elif args.task:
        dispatch(args.task, args.cwd, args.timeout, args.debug)
    else:
        ap.print_help()
