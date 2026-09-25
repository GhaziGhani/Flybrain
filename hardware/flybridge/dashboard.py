"""A live view of the loop at http://127.0.0.1:8765 while it runs. Standard library only."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Dashboard:
    def __init__(self, loop, host: str = "127.0.0.1", port: int = 8765):
        self.loop = loop
        self.host, self.port = host, port
        self.server = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        loop = self.loop

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/state.json"):
                    body, kind = json.dumps(loop.snapshot()).encode(), "application/json"
                elif self.path in ("/", "/index.html"):
                    body, kind = PAGE.encode(), "text/html; charset=utf-8"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlyBridge</title>
<style>
:root{color-scheme:dark;--bg:#0d0d0d;--panel:#15161b;--panel2:#1b1c22;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#454541;--border:rgba(255,255,255,.1);--accent:#d95926;--blue:#3987e5;
--good:#0ca30c;--warning:#fab219;--critical:#d03b3b;--vnc:#d55181;--aqua:#199e70}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink2);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;padding:20px}
h1{margin:0;color:var(--ink);font-size:22px}header{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px;margin-bottom:16px}
.pill{font:600 11.5px ui-monospace,Menlo,monospace;padding:4px 10px;border-radius:999px;border:1px solid var(--border);background:var(--panel)}
.meta{font:12px ui-monospace,Menlo,monospace;color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.tile{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px 14px}
.tile .l{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.tile .v{font:600 22px ui-monospace,Menlo,monospace;color:var(--ink);font-variant-numeric:tabular-nums;margin-top:2px}
.tile .s{font-size:12px;color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px 14px}
.card h2{margin:0 0 2px;font-size:14px;color:var(--ink)}.card p{margin:0 0 8px;font-size:12px;color:var(--muted)}
canvas{width:100%;display:block;background:var(--surface);border-radius:8px}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;font-size:12px}.legend span{display:flex;align-items:center;gap:5px}
.sw{width:10px;height:10px;border-radius:2px;display:inline-block}.wide{grid-column:1/-1}
</style></head><body>
<header><h1>FlyBridge</h1><span class="pill" id="phase">connecting…</span><span class="meta" id="meta"></span></header>
<div class="tiles">
 <div class="tile"><div class="l">Distance</div><div class="v" id="dist">—</div><div class="s" id="thr"></div></div>
 <div class="tile"><div class="l">LED (brain's decision)</div><div class="v" id="led">—</div><div class="s" id="pav"></div></div>
 <div class="tile"><div class="l">Balanced accuracy</div><div class="v" id="acc">—</div><div class="s" id="hits"></div></div>
 <div class="tile"><div class="l">Avoided / crashed</div><div class="v" id="ac">—</div><div class="s" id="fa"></div></div>
 <div class="tile"><div class="l">Dopamine updates</div><div class="v" id="upd">—</div><div class="s" id="exp"></div></div>
</div>
<div class="grid">
 <div class="card wide"><h2>World and decision</h2><p>Sensor distance, with the near threshold dashed. Shaded where the brain turned the LED on; red ticks are crashes.</p>
  <canvas id="cWorld" height="180"></canvas>
  <div class="legend"><span><i class="sw" style="background:var(--ink2)"></i>distance</span><span><i class="sw" style="background:rgba(217,89,38,.45)"></i>LED on</span><span><i class="sw" style="background:var(--critical)"></i>crash</span></div></div>
 <div class="card"><h2>How the brain responds</h2><p>Spikes per reading: eyes (LPLC2 + LC4), the DNp01 giant fiber, and the output motor population.</p>
  <canvas id="cEye" height="60"></canvas><canvas id="cGF" height="60" style="margin-top:6px"></canvas><canvas id="cMot" height="60" style="margin-top:6px"></canvas>
  <div class="legend"><span><i class="sw" style="background:var(--blue)"></i>eyes</span><span><i class="sw" style="background:var(--aqua)"></i>giant fiber</span><span><i class="sw" style="background:var(--vnc)"></i>motor output</span></div></div>
 <div class="card"><h2>Dopamine</h2><p>Reward prediction error after each judged decision: PAM reward bursts up, PPL1 punishment down.</p>
  <canvas id="cDA" height="200"></canvas>
  <div class="legend"><span><i class="sw" style="background:var(--good)"></i>PAM (reward)</span><span><i class="sw" style="background:var(--critical)"></i>PPL1 (punishment)</span></div></div>
 <div class="card"><h2>Motor population activity</h2><p>The 48 most variable output neurons (rows) over the last 120 readings (columns), each on its own scale: the pattern the readout learns from.</p>
  <canvas id="cHeat" height="200"></canvas></div>
 <div class="card"><h2>Learning curve</h2><p>Balanced accuracy over the most recent near and far decisions.</p>
  <canvas id="cAcc" height="200"></canvas></div>
</div>
<script>
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function setup(c){const r=c.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2);const w=Math.round(r.width*d),h=Math.round(c.getAttribute('height')*d);
 if(c.width!==w||c.height!==h){c.width=w;c.height=h;c.style.height=c.getAttribute('height')+'px'}const x=c.getContext('2d');x.clearRect(0,0,w,h);return[x,w,h,d]}
function line(c,vals,color,lo,hi){const[x,w,h,d]=setup(c);if(!vals.length)return;const top=hi??Math.max(1,...vals),bot=lo??0;
 x.strokeStyle=css('--grid');x.beginPath();x.moveTo(0,h-1);x.lineTo(w,h-1);x.stroke();
 x.strokeStyle=color;x.lineWidth=1.8*d;x.beginPath();vals.forEach((v,i)=>{const px=i/(Math.max(1,vals.length-1))*w,py=h-4*d-(v-bot)/(top-bot||1)*(h-8*d);i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();
 x.fillStyle=css('--muted');x.font=`${10*d}px ui-monospace,monospace`;x.fillText(Math.round(top),4*d,11*d)}
function world(s){const[x,w,h,d]=setup(document.getElementById('cWorld'));const H=s.history;if(!H.length)return;
 const max=Math.max(s.near_cm*3,...H.map(r=>Math.min(r.cm,200)));const X=i=>i/(Math.max(1,H.length-1))*w,Y=v=>h-6*d-Math.min(v,max)/max*(h-12*d);
 x.fillStyle='rgba(217,89,38,.28)';H.forEach((r,i)=>{if(r.led)x.fillRect(X(i)-w/H.length/2,0,w/H.length+1,h)});
 x.strokeStyle=css('--grid');for(let k=0;k<=4;k++){const v=max*k/4;x.beginPath();x.moveTo(0,Y(v));x.lineTo(w,Y(v));x.stroke();x.fillStyle=css('--muted');x.font=`${10*d}px ui-monospace,monospace`;x.fillText(Math.round(v)+' cm',4*d,k===4?Y(v)+12*d:Y(v)-3*d)}
 x.setLineDash([5*d,4*d]);x.strokeStyle=css('--warning');x.beginPath();x.moveTo(0,Y(s.near_cm));x.lineTo(w,Y(s.near_cm));x.stroke();x.setLineDash([]);
 x.strokeStyle=css('--ink2');x.lineWidth=1.8*d;x.beginPath();H.forEach((r,i)=>i?x.lineTo(X(i),Y(r.cm)):x.moveTo(X(i),Y(r.cm)));x.stroke();
 x.fillStyle=css('--critical');H.forEach((r,i)=>{if(r.verdict==='crash')x.fillRect(X(i)-1*d,h-10*d,2*d,10*d)})}
function dopa(s){const[x,w,h,d]=setup(document.getElementById('cDA'));const H=s.history;
 if(s.mode!=='train'){x.fillStyle=css('--muted');x.font=`${12*d}px system-ui,sans-serif`;x.fillText(`No dopamine in ${s.mode} mode: learning is switched off.`,12*d,h/2);return}
 if(!H.length)return;const mid=h/2,bw=w/H.length;
 const m=Math.max(0.5,...H.map(r=>Math.abs(r.dopamine)));x.strokeStyle=css('--axis');x.beginPath();x.moveTo(0,mid);x.lineTo(w,mid);x.stroke();
 H.forEach((r,i)=>{if(!r.dopamine)return;const bh=Math.abs(r.dopamine)/m*(mid-6*d);x.fillStyle=r.dopamine>0?css('--good'):css('--critical');
  x.fillRect(i*bw,r.dopamine>0?mid-bh:mid,Math.max(1,bw-1),bh)})}
function heat(s){const[x,w,h,d]=setup(document.getElementById('cHeat'));const M=s.heatmap;if(!M)return;const rows=M.length,cols=M[0].length;
 const cw=w/cols,ch=h/rows;M.forEach((row,i)=>row.forEach((v,j)=>{const a=Math.min(1,v);x.fillStyle=`rgba(213,81,129,${0.08+0.92*a})`;x.fillRect(j*cw,i*ch,cw+.5,ch+.5)}))}
function acc(s){const vals=s.history.map(r=>r.accuracy).filter(v=>v!==null);line(document.getElementById('cAcc'),vals,css('--accent'),0,1)}
const f=(v,dg=1)=>v===null||v===undefined?'—':(+v).toFixed(dg);
async function tick(){try{const s=await(await fetch('/state.json',{cache:'no-store'})).json();const H=s.history,last=H[H.length-1];
 document.getElementById('phase').textContent=s.phase+(s.calibration?` ${s.calibration[0]}/${s.calibration[1]}`:'');
 document.getElementById('meta').textContent=`${s.mode} · readout ${s.readout} · port ${s.port}${s.arduino?' · arduino '+s.arduino:''} · ${s.totals.readings} readings · ${Math.round(s.uptime)}s`;
 if(last){document.getElementById('dist').textContent=f(last.cm)+' cm';document.getElementById('led').textContent=last.led?'ON':'OFF';
  document.getElementById('led').style.color=last.led?css('--accent'):css('--ink');document.getElementById('pav').textContent=`p(avoid) ${f(last.p_avoid,2)} · pwm ${last.pwm}`}
 document.getElementById('thr').textContent=`near below ${s.near_cm} cm`;
 document.getElementById('acc').textContent=s.accuracy===null?'—':Math.round(s.accuracy*100)+'%';
 const hr=s.hit_rates;document.getElementById('hits').textContent=`near ${hr.near===null?'—':Math.round(hr.near*100)+'%'} · far ${hr.far===null?'—':Math.round(hr.far*100)+'%'}`;
 document.getElementById('ac').textContent=`${s.totals.avoided} / ${s.totals.crash}`;document.getElementById('fa').textContent=`${s.totals['false alarm']} false alarms`;
 document.getElementById('upd').textContent=s.updates;document.getElementById('exp').textContent=`expected reward ${f(s.expected_reward,2)}`;
 world(s);line(document.getElementById('cEye'),H.map(r=>r.eye_spikes),css('--blue'));line(document.getElementById('cGF'),H.map(r=>r.giant_fiber_spikes),css('--aqua'));
 line(document.getElementById('cMot'),H.map(r=>r.motor_spikes),css('--vnc'));dopa(s);heat(s);acc(s)}catch(e){document.getElementById('phase').textContent='disconnected'}}
setInterval(tick,300);tick();
</script></body></html>
"""
