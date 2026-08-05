"""
pad_web_map.py — 麦轮车 Web 遥控 + 实时地图 (Server + Canvas, 单文件)

浏览器 canvas 绘制场地/轨迹/车体, Python 起 HTTP server + SSE 推流。
无 matplotlib/Tk, 无 GIL 饿死问题。

用法:
    python mc602/examples/pad_web_map.py
    浏览器打开 http://<电脑IP>:8000  (手机/平板同一局域网也可)

控制:
    W/S/A/D = 前后左右平移   Q/E = 旋转   Shift = 加速
    Space = 停车            滚轮缩放 / 拖拽平移 / 双击重置视野
"""

import json
import socket
import sys
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

grandparent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, grandparent_dir)

from mc602 import MC602, MecanumChassis, SerialNotFoundError, ConnectionError

# ====================================================================
# 配置 (按你的车/场地改)
# ====================================================================
FIELD_W = 380.0          # 场地宽 cm (比赛场地 380x420)
FIELD_H = 420.0          # 场地高 cm
TRACK = 30.0             # 轮距 cm
WHEEL_BASE = 28.0        # 轴距 cm
WHEEL_RADIUS = 3.0       # 轮半径 cm
ENCODER_PPR = 2048       # 编码器 PPR
MAX_V = 60.0             # 最大线速度 cm/s
MAX_W = 0.8              # 最大角速度 rad/s (~46°/s, 遥控细腻; Shift 加速×1.5)
FAST_MULT = 1.5          # Shift 加速倍率
LOOP_HZ = 20             # 控制/推流频率
PORT = 8000

# ====================================================================
# 共享状态
# ====================================================================
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.pose = {"x": 0.0, "y": 0.0, "theta": 0.0}
        self.distance = 0.0
        self.status = "connecting"
        self.cmd = {"vx": 0.0, "vy": 0.0, "w": 0.0}

state = State()

# ====================================================================
# 控制循环线程: 读前端命令 → 底盘
# ====================================================================
def control_loop(car):
    last = {"vx": 0.0, "vy": 0.0, "w": 0.0}
    while True:
        with state.lock:
            cmd = dict(state.cmd)
        # 命令变化才下发 (避免 20Hz 刷屏干扰)
        if cmd != last:
            car.move(cmd["vx"], cmd["vy"], cmd["w"])
            last = cmd
        # 读固件里程计
        try:
            p = car.pose
            with state.lock:
                state.pose = {"x": p.x, "y": p.y, "theta": p.theta}
                state.distance = car.distance
                state.status = "ok"
        except Exception:
            with state.lock:
                state.status = "comm-error"
        time.sleep(1.0 / LOOP_HZ)

# ====================================================================
# HTTP: 页面 + SSE 推流 + 控制命令
# ====================================================================
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def handle(self):
        """全局兜底: 客户端断连 (手机/平板关页/切后台) 不刷 traceback"""
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError,
                BrokenPipeError, TimeoutError, OSError):
            pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_page()
        elif self.path.startswith("/events"):
            self.stream_events()
        elif self.path.startswith("/cmd"):
            self.handle_cmd()
        else:
            self.send_error(404)

    def send_page(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def stream_events(self):
        """SSE: 每 100ms 推一帧 pose"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                with state.lock:
                    data = json.dumps({
                        "pose": state.pose, "distance": state.distance,
                        "status": state.status,
                    })
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass   # 浏览器断开, 正常退出

    def handle_cmd(self):
        """/cmd?dx=..&dy=..&rot=..  (dx/dy/rot: -1~1)"""
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        def f(key, default=0.0):
            try:
                return float(q[key][0])
            except Exception:
                return default
        dx, dy, rot = f("dx"), f("dy"), f("rot")
        with state.lock:
            state.cmd = {
                "vx": dx * MAX_V,
                "vy": dy * MAX_V,
                "w": rot * MAX_W,
            }
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

# ====================================================================
# 前端页面 (Canvas)
# ====================================================================
PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>麦轮车 Web 遥控地图</title>
<style>
  body { margin:0; background:#111418; color:#d7dde5;
         font-family: Consolas, monospace; overflow:hidden; }
  #wrap { display:flex; height:100vh; }
  canvas { flex:1; cursor:grab; background:#1a1f26; }
  #side { width:220px; padding:14px; background:#171c23; font-size:13px; }
  #side h2 { font-size:14px; color:#38bdf8; margin:0 0 10px; }
  .row { margin:6px 0; display:flex; justify-content:space-between; }
  .k { color:#fbbf24; }
  #status { margin-top:10px; padding:8px; border-radius:6px;
            background:#0d1116; font-size:12px; line-height:1.7; }
  .ok { color:#34d399; } .err { color:#f87171; }
</style>
</head>
<body>
<div id="wrap">
  <canvas id="map"></canvas>
  <div id="side">
    <h2>控制</h2>
    <div class="row"><span class="k">W/A/S/D</span><span>平移</span></div>
    <div class="row"><span class="k">Q/E</span><span>旋转</span></div>
    <div class="row"><span class="k">Shift</span><span>加速</span></div>
    <div class="row"><span class="k">Space</span><span>停车</span></div>
    <div class="row"><span class="k">滚轮/拖拽</span><span>缩放/平移</span></div>
    <div id="status">连接中...</div>
  </div>
</div>
<script>
const FIELD_W = """ + str(FIELD_W) + """, FIELD_H = """ + str(FIELD_H) + """;
const MAX_V = """ + str(MAX_V) + """, MAX_W = """ + str(MAX_W) + """;
const canvas = document.getElementById('map');
const DPR = Math.min(2, devicePixelRatio || 1);
const fctx = canvas.getContext('2d');
// 离屏背景层: 场地 + 轨迹 (只在更新时重绘)
const bg = document.createElement('canvas');
const bctx = bg.getContext('2d');

// ── 视野 ──
let view = { cx: FIELD_W/2, cy: FIELD_H/2, scale: 2.2 };
function resize() {
  canvas.width = canvas.clientWidth * DPR;
  canvas.height = canvas.clientHeight * DPR;
  fctx.setTransform(DPR,0,0,DPR,0,0);
  bg.width = canvas.width; bg.height = canvas.height;
  bctx.setTransform(DPR,0,0,DPR,0,0);
  drawBackground();
}
window.addEventListener('resize', resize); resize();

function toScreen(x, y) {
  return [(x - view.cx) * view.scale + canvas.clientWidth/2,
          (y - view.cy) * view.scale + canvas.clientHeight/2];
}

// ── 背景层: 场地 + 全部轨迹 (视野变化/新点时重绘) ──
const traj = [];            // {x, y, speed}
function drawBackground() {
  bctx.clearRect(0,0,canvas.clientWidth,canvas.clientHeight);
  const [sx, sy] = toScreen(0,0), [ex, ey] = toScreen(FIELD_W, FIELD_H);
  bctx.strokeStyle = '#9e9e9e'; bctx.lineWidth = 2;
  bctx.strokeRect(sx, sy, ex-sx, ey-sy);
  bctx.fillStyle = '#5b6472'; bctx.font = '12px monospace';
  bctx.fillText('0,0', sx+6, sy+16); bctx.fillText(FIELD_W+','+FIELD_H, ex-70, ey-6);
  for (let i = 1; i < traj.length; i++) {
    const a = traj[i-1], b = traj[i];
    const t = Math.min(1, Math.abs(b.speed) / MAX_V);
    bctx.strokeStyle = `rgb(${255-200*t},${80+170*t},${80})`;
    bctx.lineWidth = 2;
    bctx.beginPath();
    const [ax,ay] = toScreen(a.x,a.y), [bx,by] = toScreen(b.x,b.y);
    bctx.moveTo(ax,ay); bctx.lineTo(bx,by); bctx.stroke();
  }
}

// 新轨迹段: 只追加画一段 (不重绘全部)
function appendTraj(x1, y1, x2, y2, speed) {
  const t = Math.min(1, Math.abs(speed) / MAX_V);
  bctx.strokeStyle = `rgb(${255-200*t},${80+170*t},${80})`;
  bctx.lineWidth = 2;
  bctx.beginPath();
  const [ax,ay] = toScreen(x1,y1), [bx,by] = toScreen(x2,y2);
  bctx.moveTo(ax,ay); bctx.lineTo(bx,by); bctx.stroke();
}

// ── 前景层: 车体 (每帧只画几笔, 轻量) ──
function draw() {
  fctx.clearRect(0,0,canvas.clientWidth,canvas.clientHeight);
  fctx.drawImage(bg, 0, 0, canvas.clientWidth, canvas.clientHeight);
  const p = lastPose;
  const [px, py] = toScreen(p.x, p.y);
  fctx.save(); fctx.translate(px, py); fctx.rotate(p.theta);
  fctx.strokeStyle = '#ff5252'; fctx.lineWidth = 3;
  fctx.beginPath(); fctx.moveTo(18,0); fctx.lineTo(-10,0); fctx.stroke();
  fctx.fillStyle = '#ffffff';
  fctx.beginPath(); fctx.arc(0,0,5,0,7); fctx.fill();
  fctx.restore();
  requestAnimationFrame(draw);
}

// ── 键盘控制 ──
const keys = {};
function sendCmd() {
  const dx = (keys['d']?1:0) - (keys['a']?1:0);
  const dy = (keys['s']?1:0) - (keys['w']?1:0);
  const rot = (keys['e']?1:0) - (keys['q']?1:0);
  const fast = keys['Shift'] ? """ + str(FAST_MULT) + """ : 1;
  fetch('/cmd?dx='+dx*fast+'&dy='+dy*fast+'&rot='+rot*fast).catch(()=>{});
}
setInterval(sendCmd, 80);   // 12.5Hz 命令

window.addEventListener('keydown', e => {
  keys[e.key.toLowerCase()] = true;
  if (e.key === ' ') { keys['space'] = true; e.preventDefault(); }
});
window.addEventListener('keyup', e => {
  keys[e.key.toLowerCase()] = false;
  if (e.key === ' ') keys['space'] = false;
});

// Space 停车
setInterval(() => {
  if (keys['space']) fetch('/cmd?dx=0&dy=0&rot=0').catch(()=>{});
}, 200);

// ── 视野交互 ──
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const r = canvas.getBoundingClientRect();
  const mx = (e.clientX - r.left) - canvas.clientWidth/2;
  const my = (e.clientY - r.top) - canvas.clientHeight/2;
  const wx = view.cx + mx / view.scale, wy = view.cy + my / view.scale;
  view.scale *= (e.deltaY < 0 ? 1.2 : 1/1.2);
  view.scale = Math.max(0.5, Math.min(20, view.scale));
  view.cx = wx - mx / view.scale; view.cy = wy - my / view.scale;
  drawBackground();
}, {passive:false});

let drag = null;
canvas.addEventListener('mousedown', e => { drag = {x:e.clientX, y:e.clientY}; });
window.addEventListener('mousemove', e => {
  if (!drag) return;
  view.cx -= (e.clientX - drag.x) / view.scale;
  view.cy -= (e.clientY - drag.y) / view.scale;
  drag = {x:e.clientX, y:e.clientY};
  drawBackground();
});
window.addEventListener('mouseup', () => drag = null);
canvas.addEventListener('dblclick', () => {
  view.cx = FIELD_W/2; view.cy = FIELD_H/2; view.scale = 2.2;
  drawBackground();
});

// ── SSE 接收 ──
let lastPose = {x:0, y:0, theta:0};
const es = new EventSource('/events');
let lastTraj = null;
es.onmessage = e => {
  const d = JSON.parse(e.data);
  const prev = lastPose;
  lastPose = d.pose;
  const pt = {x:d.pose.x, y:d.pose.y, speed:0};
  traj.push(pt);
  if (traj.length > 800) traj.shift();
  if (lastTraj) appendTraj(lastTraj.x, lastTraj.y, pt.x, pt.y, 0);
  lastTraj = pt;
  const el = document.getElementById('status');
  const th = (d.pose.theta*180/Math.PI).toFixed(1);
  el.innerHTML = `<span class="${d.status==='ok'?'ok':'err'}">${d.status==='ok'?'在线':'通信异常'}</span><br>
    X=${d.pose.x.toFixed(1)} Y=${d.pose.y.toFixed(1)} θ=${th}°<br>
    距离=${d.distance.toFixed(1)}cm`;
};
es.onerror = () => {
  document.getElementById('status').innerHTML =
    '<span class="err">连接断开, 自动重连...</span>';
};
draw();
</script>
</body>
</html>"""

# ====================================================================
# main
# ====================================================================
def main() -> int:
    print("=" * 55)
    print("  麦轮车 Web 遥控 + 实时地图")
    print("=" * 55)
    print(f"  场地: {FIELD_W:.0f}x{FIELD_H:.0f} cm  控制: {LOOP_HZ}Hz")
    print(f"  速度: {MAX_V:.0f} cm/s  角速: {MAX_W:.1f} rad/s")

    try:
        bot = MC602.connect()
        car = MecanumChassis(bot, ports=(1, 2, 3, 4),
                             track=TRACK, wheel_base=WHEEL_BASE,
                             wheel_radius=WHEEL_RADIUS, encoder_ppr=ENCODER_PPR)
        car.set_max_vel(v_cm_s=MAX_V, w_deg_s=MAX_W * 180 / 3.14159)
        car.reset_pose()
    except (SerialNotFoundError, ConnectionError) as e:
        print(f"[!] 连接失败: {e}")
        return 1

    state.status = "ok"

    # 控制线程
    threading.Thread(target=control_loop, args=(car,), daemon=True).start()

    # HTTP server
    ip = socket.gethostbyname(socket.gethostname())
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[OK] 打开浏览器: http://{ip}:{PORT}")
    print("     控制: WASD平移 Q/E旋转 Shift加速 Space停车")
    print("     滚轮缩放 / 拖拽平移 / 双击重置 (Ctrl+C 退出)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        car.stop()
        bot.close()
        print("\n[OK] 已停止")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] 中断")
        sys.exit(130)
