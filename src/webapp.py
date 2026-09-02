"""Render the Stage-1 terminal app: one self-contained HTML file.

All presentation logic lives here (client-side JS over an embedded JSON
payload); all calculation logic stays in Python. No CDNs, no build chain —
the file opens from disk, GitHub Pages, or a Cowork artifact.

Design system: the validated light/dark token palette from Phase 1, applied
with terminal density — shared surfaces + hairline dividers over card-per-
metric, 4-level type hierarchy, tabular numerals, sparklines, restrained
accent, colour never the only channel (arrows/labels everywhere).
"""
from __future__ import annotations

import json

CSS = r"""
:root { color-scheme:light;
  --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,.10);
  --pos:#2a78d6; --neg:#e34948; --accent:#2a78d6; --accent2:#eb6834;
  --up:#006300; --down:#d03b3b; --wash:rgba(42,120,214,.08); --hover:rgba(11,11,11,.035);
}
:root[data-theme=dark], :root[data-theme=auto].sys-dark {
  color-scheme:dark;
  --surface:#1a1a19; --page:#111110; --ink:#f2f1ec; --ink2:#c3c2b7; --muted:#8b8a84;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10);
  --pos:#3987e5; --neg:#e66767; --accent:#3987e5; --accent2:#d95926;
  --up:#0ca30c; --down:#e66767; --wash:rgba(57,135,229,.10); --hover:rgba(255,255,255,.05);
}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0;background:var(--page);color:var(--ink);
  font:13px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.num,td.num,th.num,.val{font-variant-numeric:tabular-nums}
a{color:inherit}
/* ---------- top bar ---------- */
#topbar{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:14px;
  padding:0 18px;height:46px;background:var(--surface);border-bottom:1px solid var(--border)}
#brand{font-weight:650;font-size:14px;letter-spacing:-.01em;white-space:nowrap}
#brand span{color:var(--muted);font-weight:400}
.tabs{display:flex;gap:2px;background:var(--hover);border-radius:7px;padding:2px}
.tab{border:0;background:none;color:var(--ink2);font:inherit;font-weight:550;
  padding:4px 14px;border-radius:5px;cursor:pointer}
.tab.on{background:var(--surface);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.12)}
#topbar .sp{flex:1}
.tbtn{border:1px solid var(--border);background:none;color:var(--ink2);font:inherit;
  font-size:12px;padding:4px 10px;border-radius:6px;cursor:pointer;white-space:nowrap}
.tbtn:hover{background:var(--hover)}
.chip-sample{font-size:11px;font-weight:600;color:var(--accent2);
  border:1px solid var(--accent2);border-radius:5px;padding:2px 8px;white-space:nowrap}
/* ---------- layout ---------- */
#wrap{max-width:1340px;margin:0 auto;padding:14px 18px 80px}
.grid12{display:grid;grid-template-columns:repeat(12,1fr);gap:14px;margin-top:14px}
.c8{grid-column:span 8}.c4{grid-column:span 4}.c12{grid-column:span 12}
.c8,.c4,.c12{min-width:0}
@media(max-width:980px){.c8,.c4{grid-column:span 12}}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:9px;overflow:hidden}
.phead{display:flex;align-items:baseline;gap:8px;padding:10px 14px 8px;
  border-bottom:1px solid var(--grid)}
.phead h2{font-size:13px;font-weight:650;margin:0}
.phead .note{font-size:11px;color:var(--muted)}
.phead .sp{flex:1}
.pbody{padding:10px 14px}
/* ---------- command header ---------- */
#cmdhead{display:flex;align-items:stretch;background:var(--surface);
  border:1px solid var(--border);border-radius:9px;overflow-x:auto}
.ch-cell{padding:10px 16px;border-right:1px solid var(--grid);min-width:118px;flex:0 0 auto}
.ch-cell:last-child{border-right:0}
.ch-lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
  white-space:nowrap}
.ch-val{font-size:19px;font-weight:650;line-height:1.25;white-space:nowrap}
.ch-big .ch-val{font-size:25px}
.ch-sub{font-size:11.5px;color:var(--ink2);white-space:nowrap}
.ch-cell svg{display:block;margin-top:3px}
/* ---------- drivers strip ---------- */
#drivers{display:flex;gap:0;margin-top:14px;background:var(--surface);
  border:1px solid var(--border);border-radius:9px;overflow-x:auto}
.drv{padding:8px 14px;border-right:1px solid var(--grid);min-width:108px;flex:0 0 auto;
  cursor:default}
.drv:last-child{border-right:0}
.drv:hover{background:var(--hover)}
/* ---------- read cards ---------- */
#readgrid{display:grid;grid-template-columns:1fr 1fr;gap:0}
@media(max-width:720px){#readgrid{grid-template-columns:1fr}}
.readcard{padding:11px 14px;border-bottom:1px solid var(--grid);border-right:1px solid var(--grid)}
.readcard:nth-child(2n){border-right:0}
.readcard:nth-last-child(-n+2){border-bottom:0}
@media(max-width:720px){.readcard{border-right:0}.readcard:nth-last-child(2){border-bottom:1px solid var(--grid)}}
.rc-title{font-size:12.5px;font-weight:650;display:flex;gap:7px;align-items:baseline}
.rc-dir{font-size:11px;flex:0 0 auto}
.rc-dir.up{color:var(--up)}.rc-dir.down{color:var(--down)}.rc-dir.flat{color:var(--muted)}
.rc-body{font-size:12px;color:var(--ink2);margin:3px 0 6px}
.tk{display:inline-block;font-size:10.5px;font-weight:600;color:var(--accent);
  border:1px solid var(--border);border-radius:4px;padding:0 5px;margin-right:3px;
  cursor:pointer;background:var(--wash)}
.tk:hover{border-color:var(--accent)}
/* ---------- regime ---------- */
#regime .big{font-size:19px;font-weight:650;margin:2px 0 8px}
.rfac{display:flex;gap:8px;padding:5px 0;border-top:1px solid var(--grid);font-size:12px;
  align-items:baseline}
.rfac .nm{color:var(--muted);flex:0 0 118px}
.rfac .st{color:var(--ink2);flex:1}
.rdir{font-weight:700;flex:0 0 14px;text-align:center}
.rdir.p{color:var(--up)}.rdir.n{color:var(--down)}.rdir.z{color:var(--muted)}
/* ---------- tables ---------- */
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%}
thead th{position:sticky;top:0;background:var(--surface);z-index:5;
  text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--muted);font-weight:600;border-bottom:1px solid var(--axis);
  padding:5px 7px;cursor:pointer;white-space:nowrap}
td{padding:4px 7px;border-bottom:1px solid var(--grid);white-space:nowrap;font-size:12.5px}
td.num,th.num{text-align:right}
tbody tr:hover{background:var(--hover)}
tr.clickable{cursor:pointer}
.pos{color:var(--up)}.neg{color:var(--down)}
.tick{font-weight:650;color:var(--accent);cursor:pointer}
.co{color:var(--muted);font-size:11px}
/* phase + signal chips */
.phase,.sig{display:inline-block;font-size:10.5px;font-weight:600;border-radius:4px;
  padding:1px 7px;border:1px solid var(--border);color:var(--ink2);white-space:nowrap}
.phase.entering{background:var(--wash);color:var(--accent);border-color:transparent}
.phase.emerging{background:rgba(27,175,122,.12);color:var(--up);border-color:transparent}
.phase.crowded{background:rgba(237,161,0,.14);border-color:transparent}
.phase.rolling{background:rgba(227,73,72,.10);color:var(--down);border-color:transparent}
.phase.washed{background:var(--hover)}
.sig{background:var(--wash);color:var(--accent);border-color:transparent}
/* inline bars */
.hbar{display:inline-flex;align-items:center;width:48px;height:12px;vertical-align:middle}
.hbar .half{flex:1;display:flex;height:7px}
.hbar .half.l{justify-content:flex-end}
.hbar i{height:7px;display:block}
.hbar i.p{background:var(--pos);border-radius:0 3px 3px 0}
.hbar i.n{background:var(--neg);border-radius:3px 0 0 3px}
.hbar .mid{width:1px;height:11px;background:var(--axis)}
.meter{display:inline-block;width:58px;height:6px;background:var(--hover);border-radius:3px;
  vertical-align:middle;overflow:hidden}
.meter i{display:block;height:6px;background:var(--accent);border-radius:3px}
/* sort chips */
.sorts{display:flex;gap:4px;flex-wrap:wrap}
.schip{border:1px solid var(--border);background:none;color:var(--ink2);font:inherit;
  font-size:11px;padding:2px 8px;border-radius:5px;cursor:pointer}
.schip.on{background:var(--wash);color:var(--accent);border-color:var(--accent)}
/* theme expand row */
tr.expand td{background:var(--hover);padding:10px 14px;white-space:normal}
.exgrid{display:flex;gap:22px;flex-wrap:wrap;font-size:12px}
.exgrid .kv b{display:block;font-size:13px}
.exgrid .kv{color:var(--muted)}
.mini-cons{margin-top:8px;width:100%}
/* ---------- breadth ---------- */
.bstat{display:flex;justify-content:space-between;align-items:center;padding:5px 0;
  border-top:1px solid var(--grid);font-size:12px}
.bstat:first-child{border-top:0}
.bstat .k{color:var(--muted)}
/* ---------- momentum map ---------- */
.mapctl{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
select.ctl{border:1px solid var(--border);background:var(--surface);color:var(--ink2);
  font:inherit;font-size:11.5px;border-radius:5px;padding:2px 6px}
#map svg{display:block;width:100%}
#map .qlab{font-size:10.5px;fill:var(--muted);text-transform:uppercase;letter-spacing:.03em}
#map .alab{font-size:10.5px;fill:var(--muted)}
#map .dlab{font-size:10.5px;fill:var(--ink2)}
/* ---------- leaders panel ---------- */
.lrow{display:flex;align-items:baseline;gap:8px;padding:5px 0;border-top:1px solid var(--grid);
  font-size:12px}
.lrow:first-child{border-top:0}
.lrow .sig{margin-left:auto}
/* ---------- tooltip ---------- */
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);
  border:1px solid var(--border);border-radius:7px;padding:8px 10px;font-size:12px;
  box-shadow:0 6px 18px rgba(0,0,0,.18);display:none;z-index:80;max-width:280px;
  white-space:normal}
#tip .t{font-weight:650}
#tip .f{display:flex;justify-content:space-between;gap:12px;color:var(--ink2)}
#tip .f b{font-variant-numeric:tabular-nums}
/* ---------- drawer ---------- */
#scrim{position:fixed;inset:0;background:rgba(0,0,0,.25);z-index:60;display:none}
#drawer{position:fixed;top:0;right:-420px;width:400px;max-width:94vw;height:100%;
  background:var(--surface);border-left:1px solid var(--border);z-index:70;
  transition:right .18s ease;overflow-y:auto;padding:16px 18px 40px}
#drawer.open{right:0}
#drawer h3{margin:0;font-size:20px}
#drawer .co2{color:var(--muted);font-size:12px;margin-bottom:10px}
#drawer .price{font-size:24px;font-weight:650}
.dret{display:flex;gap:0;margin:10px 0;border:1px solid var(--grid);border-radius:7px;
  overflow:hidden}
.dret div{flex:1;text-align:center;padding:6px 2px;border-right:1px solid var(--grid)}
.dret div:last-child{border-right:0}
.dret .k{font-size:10px;color:var(--muted);text-transform:uppercase}
.dret .v{font-size:12.5px;font-weight:600}
#drawer h4{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
  margin:16px 0 6px}
.fac{display:flex;justify-content:space-between;gap:10px;font-size:12px;padding:3px 0;
  color:var(--ink2)}
.fac b{font-variant-numeric:tabular-nums;color:var(--ink)}
.kvrow{display:flex;justify-content:space-between;font-size:12.5px;padding:4px 0;
  border-top:1px solid var(--grid)}
.kvrow:first-of-type{border-top:0}
.kvrow .k{color:var(--muted)}
#drawer .close{position:absolute;top:10px;right:12px;border:0;background:none;
  font-size:18px;color:var(--muted);cursor:pointer}
.star{border:0;background:none;cursor:pointer;font-size:15px;color:var(--muted);padding:0 4px}
.star.on{color:var(--accent2)}
.stub{font-size:11.5px;color:var(--muted);border:1px dashed var(--border);border-radius:6px;
  padding:6px 10px;margin-top:14px;text-align:center}
/* ---------- command palette ---------- */
#pal{position:fixed;inset:0;background:rgba(0,0,0,.30);z-index:90;display:none;
  align-items:flex-start;justify-content:center;padding-top:12vh}
#palbox{width:520px;max-width:92vw;background:var(--surface);border:1px solid var(--border);
  border-radius:10px;box-shadow:0 18px 50px rgba(0,0,0,.30);overflow:hidden}
#palin{width:100%;border:0;outline:0;background:none;color:var(--ink);font:inherit;
  font-size:15px;padding:13px 16px;border-bottom:1px solid var(--grid)}
#palres{max-height:320px;overflow-y:auto}
.palrow{display:flex;gap:10px;align-items:baseline;padding:8px 16px;cursor:pointer;font-size:13px}
.palrow:hover,.palrow.sel{background:var(--hover)}
.palrow .kind{font-size:10.5px;color:var(--muted);text-transform:uppercase;margin-left:auto}
/* global view */
.dgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:0}
.dcell{padding:10px 14px;border-right:1px solid var(--grid);border-bottom:1px solid var(--grid)}
footer{margin-top:26px;color:var(--muted);font-size:11.5px;line-height:1.6}

/* ---------- view switcher ---------- */
.vtabs{display:flex;gap:4px;margin:0 0 2px}
.vtab{border:1px solid var(--border);background:none;color:var(--ink2);font:inherit;
  font-size:12px;font-weight:550;padding:3px 12px;border-radius:6px;cursor:pointer}
.vtab.on{background:var(--wash);color:var(--accent);border-color:var(--accent)}
/* ---------- modal ---------- */
#modal{position:fixed;inset:0;background:rgba(0,0,0,.32);z-index:55;display:none;
  align-items:flex-start;justify-content:center;padding:5vh 16px}
.modal-box{width:920px;max-width:100%;max-height:90vh;overflow-y:auto;background:var(--surface);
  border:1px solid var(--border);border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.35);
  padding:18px 22px 26px;position:relative}
.modal-box h3{margin:0;font-size:19px}
.modal-box .mclose{position:sticky;top:0;float:right;border:0;background:none;font-size:18px;
  color:var(--muted);cursor:pointer;z-index:2}
.mstats{display:flex;gap:0;margin:12px 0;border:1px solid var(--grid);border-radius:7px;
  overflow:hidden;flex-wrap:wrap}
.mstats div{flex:1;min-width:86px;text-align:center;padding:7px 4px;border-right:1px solid var(--grid)}
.mstats div:last-child{border-right:0}
.mstats .k{font-size:10px;color:var(--muted);text-transform:uppercase;white-space:nowrap}
.mstats .v{font-size:13px;font-weight:600}
.gh{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
  margin:16px 0 4px;display:flex;gap:8px;align-items:baseline}
.tfchips{display:inline-flex;gap:4px;margin-left:auto}
/* ---------- heatmap ---------- */
.hm-sec{margin-bottom:12px}
.hm-sechead{display:flex;gap:8px;align-items:baseline;font-size:12px;font-weight:650;margin:0 0 4px}
.hm-sechead .co{font-weight:400}
.hm-tiles{display:flex;flex-wrap:wrap;gap:3px}
.hm-tile{border-radius:4px;padding:4px 6px;min-width:44px;cursor:pointer;
  display:flex;flex-direction:column;justify-content:center;border:1px solid var(--border)}
.hm-tile b{font-size:11px;line-height:1.1}
.hm-tile span{font-size:10px;opacity:.85;font-variant-numeric:tabular-nums}
.hm-tile:hover{outline:2px solid var(--accent)}
/* watch empty state */
.empty{padding:26px 18px;text-align:center;color:var(--muted);font-size:13px}

@media(max-width:760px){ .lo{display:none} }
@media(max-width:720px){
  #topbar{flex-wrap:wrap;height:auto;padding:6px 10px;gap:8px;row-gap:6px}
  #brand span{display:none}
  #wrap{padding:10px 10px 60px}
  .ch-cell{min-width:100px;padding:8px 12px}
  td .co{display:none}
  .modal-box{max-height:96vh}
  #modal{padding:2vh 6px}
}
"""

# The application. Vanilla JS over the embedded PAYLOAD. No frameworks.
JS = r"""
const P = window.PAYLOAD;
let MK = 'asx';                       // current market tab
let VIEW = 'overview';                // overview | heatmap | watch
let WATCH = new Set(); try { WATCH = new Set(JSON.parse(localStorage.getItem('sa_watch')||'[]')); } catch(e) {}
const $ = s => document.querySelector(s);
const el = (t,c,h) => { const e=document.createElement(t); if(c)e.className=c; if(h!=null)e.innerHTML=h; return e; };
const esc = s => String(s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct = (x,d=1) => x==null?'–':`<span class="${x>0?'pos':x<0?'neg':''}">${(x>0?'+':'')+(100*x).toFixed(d)}%</span>`;
const pctT = (x,d=1) => x==null?'–':(x>0?'+':'')+(100*x).toFixed(d)+'%';
const arrow = d => d>0?'<span class="rdir p">▲</span>':d<0?'<span class="rdir n">▼</span>':'<span class="rdir z">→</span>';
const money = (x,cur) => x==null?'–':cur+Number(x).toLocaleString(undefined,{maximumFractionDigits:2});

function spark(arr,w=64,h=20,cls){ if(!arr||arr.length<2)return '';
  const mn=Math.min(...arr),mx=Math.max(...arr),rg=(mx-mn)||1;
  const pts=arr.map((v,i)=>`${(i/(arr.length-1)*w).toFixed(1)},${(h-2-(v-mn)/rg*(h-4)).toFixed(1)}`).join(' ');
  const up=arr[arr.length-1]>=arr[0];
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${up?'var(--pos)':'var(--neg)'}" stroke-width="1.5" stroke-linejoin="round"/></svg>`; }

function saveWatch(){ try{ localStorage.setItem('sa_watch', JSON.stringify([...WATCH])); }catch(e){} }

/* ---------- tooltip ---------- */
const tip=$('#tip');
function bindTips(root){ root.querySelectorAll('[data-tip]').forEach(n=>{
  n.addEventListener('mousemove',e=>{ tip.innerHTML=n.dataset.tip; tip.style.display='block';
    const r=280; tip.style.left=Math.min(e.clientX+14,innerWidth-r-10)+'px';
    tip.style.top=Math.min(e.clientY+14,innerHeight-140)+'px'; });
  n.addEventListener('mouseleave',()=>tip.style.display='none'); }); }

/* ---------- session clock ---------- */
function sessionState(sess){ if(!sess||!sess.tz) return {open:false,txt:'—'};
  try{ const now=new Date();
    const parts=new Intl.DateTimeFormat('en-AU',{timeZone:sess.tz,hour12:false,weekday:'short',hour:'2-digit',minute:'2-digit'}).formatToParts(now);
    const get=k=>parts.find(p=>p.type===k).value;
    const wd=get('weekday'), hm=get('hour')+':'+get('minute');
    const wkday=!['Sat','Sun'].includes(wd);
    const open= wkday && hm>=sess.open && hm<sess.close;
    return {open, txt:`${hm} local`}; }catch(e){ return {open:false,txt:'—'}; } }

/* ---------- shell ---------- */
function switchMarket(k){ MK=k;
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.dataset.mk===k));
  render(); window.scrollTo({top:0}); }

function render(){
  const root=$('#wrap'); root.innerHTML='';
  if(MK==='global') renderGlobal(root); else renderMarket(root, P.markets[MK]);
  bindTips(root); }

/* ================= MARKET VIEW ================= */
function renderMarket(root,M){
  const vt=el('div','vtabs');
  [['overview','Overview'],['heatmap','Heatmap'],['watch','Watchlist'+(WATCH.size?` (${WATCH.size})`:'')]]
    .forEach(([k,l])=>{ const b=el('button','vtab'+(VIEW===k?' on':''),l);
      b.onclick=()=>{VIEW=k;render();}; vt.appendChild(b); });
  root.appendChild(vt);
  root.appendChild(cmdHeader(M));
  if(VIEW==='heatmap'){ root.appendChild(heatmapPanel(M)); root.appendChild(marketFooter()); return; }
  if(VIEW==='watch'){ root.appendChild(watchlistPanel(M)); root.appendChild(marketFooter()); return; }
  if(M.drivers&&M.drivers.length) root.appendChild(driverStrip(M));
  const r2=el('div','grid12');
  r2.appendChild(panel('c8','Today’s read','what changed and why it matters', readGrid(M)));
  r2.appendChild(regimePanel(M));
  root.appendChild(r2);
  const r3=el('div','grid12');
  r3.appendChild(flowPanel(M));
  r3.appendChild(breadthPanel(M));
  root.appendChild(r3);
  const r4=el('div','grid12');
  r4.appendChild(mapPanel(M));
  r4.appendChild(leadersPanel(M));
  root.appendChild(r4);
  root.appendChild(actionPanel(M));
  root.appendChild(marketFooter());
}
function marketFooter(){ return el('footer',null,
    `Deterministic build — same rules every day · generated ${P.generated} · data as at close ${P.run_date}`+
    (P.sample?' · <b style="color:var(--accent2)">SAMPLE DATA — synthetic, not real prices</b>':'')+
    ' · price/volume signals only until the Phase-2 options layer · decision support, not financial advice.'); }

function panel(span,title,note,body,headExtra){
  const p=el('section','panel '+span);
  const h=el('div','phead',`<h2>${title}</h2><span class="note">${note||''}</span><span class="sp"></span>`);
  if(headExtra) h.appendChild(headExtra);
  p.appendChild(h); p.appendChild(body); return p; }

/* ---------- command header ---------- */
function cmdHeader(M){
  const wrap=el('div','','');
  const ch=el('div'); ch.id='cmdhead';
  const bench=M.tape.find(t=>t.label.includes(M.benchmark))||M.tape[0];
  const ss=sessionState(M.session);
  const cell=(cls,lbl,val,sub,spk)=>`<div class="ch-cell ${cls||''}"><div class="ch-lbl">${lbl}</div><div class="ch-val">${val}</div><div class="ch-sub">${sub||''}</div>${spk||''}</div>`;
  let h= cell('ch-big',bench.label, bench.close!=null?Number(bench.close).toLocaleString():'–',
              `${pct(bench.ret_1d)} today · ${pct(bench.ret_1m)} 1M`, spark((bench.spark||[]).slice(-30),86,22));
  M.tape.filter(t=>t!==bench).forEach(t=>{
    h+=cell('',t.label,t.close!=null?Number(t.close).toLocaleString():'–',pct(t.ret_1d)+' today',spark((t.spark||[]).slice(-30),64,18)); });
  const b=M.breadth;
  h+=cell('','Breadth',`${Math.round(100*b.above_ma20)}% ${b.trend&&b.trend.length>5&&b.trend.at(-1)>b.trend.at(-6)?'▲':'▼'}`,'above 20DMA');
  h+=cell('','Volatility',esc(M.regime.vol_state||'—'),'20-day realised');
  const rg=M.regime;
  h+=`<div class="ch-cell" data-tip="${esc(rg.factors.map(f=>f.name+': '+f.state).join('<br>'))}"><div class="ch-lbl">Market regime</div><div class="ch-val" style="font-size:15px">${esc(rg.label)}</div><div class="ch-sub">${rg.note.split('·').slice(0,2).join('·')}</div></div>`;
  h+=cell('','Session',ss.open?'<span class="pos">OPEN</span>':'CLOSED',ss.txt);
  ch.innerHTML=h; wrap.appendChild(ch); return wrap; }

/* ---------- drivers ---------- */
function driverStrip(M){
  const d=el('div'); d.id='drivers';
  d.innerHTML=M.drivers.map(v=>{
    const tipTxt=`<div class="t">${esc(v.label)}</div>`+
      `1W ${pctT(v.ret_1w)} · 1M ${pctT(v.ret_1m)} · momentum ${v.accel}<br>`+
      (v.themes.length?`<i>${esc(v.themes.join(' · '))}</i><br>`:'')+
      (v.beneficiaries.length?('Watch: '+v.beneficiaries.join(' · ')):'');
    return `<div class="drv" data-tip="${esc(tipTxt)}">
      <div class="ch-lbl">${esc(v.label)}</div>
      <div class="ch-val" style="font-size:14px">${v.close!=null?Number(v.close).toLocaleString():'–'}</div>
      <div class="ch-sub">${pct(v.ret_1d)} · 1W ${pct(v.ret_1w)} ${v.accel==='accelerating'?'▲':'▽'}</div></div>`; }).join('');
  return d; }

/* ---------- read ---------- */
function readGrid(M){
  const g=el('div'); g.id='readgrid';
  g.innerHTML=M.read.map(c=>`<div class="readcard">
    <div class="rc-title"><span class="rc-dir ${c.dir}">${c.dir==='up'?'▲':c.dir==='down'?'▼':'→'}</span>${esc(c.title)}</div>
    <div class="rc-body">${esc(c.body)}</div>
    ${c.tickers.map(t=>`<span class="tk" data-open="${t}">${t}</span>`).join('')}</div>`).join('');
  g.addEventListener('click',e=>{ const t=e.target.dataset.open; if(t) openDrawer(t); });
  return g; }

/* ---------- regime ---------- */
function regimePanel(M){
  const b=el('div','pbody'); b.id='regime';
  const rg=M.regime;
  b.innerHTML=`<div class="ch-lbl">Rules-based assessment</div><div class="big">${esc(rg.label)}</div>`+
    rg.factors.map(f=>`<div class="rfac" data-tip="${esc(f.name)}: ${esc(f.state)}">${arrow(f.dir)}<span class="nm">${esc(f.name)}</span><span class="st">${esc(f.state)}</span></div>`).join('')+
    `<div class="ch-sub" style="margin-top:8px">${esc(rg.note)}</div>`;
  return panel('c4','Market regime','explainable — hover any factor',b); }

/* ---------- money flow ---------- */
let FLOWSORT='rel_1w';
const PHASECLS={'Money entering':'entering','Emerging':'emerging','Crowded':'crowded','Rolling over':'rolling','Washed out':'washed','Quiet':''};
function flowPanel(M){
  const body=el('div','tablewrap'); body.id='flowbody';
  const sorts=el('div','sorts');
  [['rel_1w','Strongest 1W'],['rel_1m','Strongest 1M'],['accel','Accelerating'],['-accel','Deteriorating'],['breadth','Breadth'],['vol_ratio','Volume']]
   .forEach(([k,lbl])=>{ const c=el('button','schip'+(FLOWSORT===k?' on':''),lbl);
     c.onclick=()=>{FLOWSORT=k; renderFlow(M); document.querySelectorAll('#flowpanel .schip').forEach(x=>x.classList.toggle('on',x.textContent===lbl)); };
     sorts.appendChild(c); });
  const p=panel('c8','Where money is flowing','themes, finer than sectors — click a theme for the full view',body,sorts);
  p.id='flowpanel';
  renderFlow(M,body); return p; }

function renderFlow(M,body){
  body=body||$('#flowbody');
  const key=FLOWSORT.replace('-',''), dir=FLOWSORT.startsWith('-')?1:-1;
  const T=[...M.themes].sort((a,b)=>dir*((a[key]??-9)-(b[key]??-9)));
  const scale=Math.max(...T.map(t=>Math.abs(t.rel_1m||0)),0.01);
  body.innerHTML=`<table><thead><tr><th>Theme</th><th class="lo"></th><th>Phase</th>
    <th class="num lo">1D</th><th class="num">1W rel</th><th class="num">1M rel</th>
    <th class="num">Breadth</th><th class="num lo">Vol</th><th class="lo">Leaders</th></tr></thead><tbody>`+
    T.map((t,i)=>{
      const w=Math.min(Math.abs(t.rel_1m||0)/scale,1)*100;
      const bar=`<span class="hbar"><span class="half l">${t.rel_1m<0?`<i class="n" style="width:${w}%"></i>`:''}</span><span class="mid"></span><span class="half">${t.rel_1m>=0?`<i class="p" style="width:${w}%"></i>`:''}</span></span>`;
      return `<tr class="clickable" data-th="${i}">
        <td style="max-width:168px;overflow:hidden;text-overflow:ellipsis"><b>${esc(t.name)}</b> <span class="co">· ${t.n}</span></td>
        <td class="lo">${spark((t.spark||[]).slice(-30),46,15)}</td>
        <td><span class="phase ${PHASECLS[t.phase]||''}">${t.phase}</span></td>
        <td class="num lo">${pct(t.ret_1d)}</td><td class="num">${pct(t.rel_1w)}</td>
        <td class="num">${pct(t.rel_1m)} ${bar}</td>
        <td class="num"><span class="meter"><i style="width:${Math.round(100*t.breadth)}%"></i></span> ${Math.round(100*t.breadth)}%</td>
        <td class="num lo">${t.vol_ratio?t.vol_ratio.toFixed(1)+'×':'–'}</td>
        <td class="lo">${t.leaders.slice(0,3).map(x=>`<span class="tk" data-open="${x}">${x}</span>`).join('')}</td></tr>`; }).join('')+'</tbody></table>';
  body.onclick=e=>{
    const tk=e.target.dataset.open; if(tk){ openDrawer(tk); return; }
    const row=e.target.closest('tr[data-th]'); if(!row) return;
    themeModal(T[+row.dataset.th], M); };
}

/* ---------- breadth ---------- */
let BSEL='market';
function breadthPanel(M){
  const sel=el('select','ctl'); sel.innerHTML='<option value="market">Whole market</option>'+
    M.themes.map(t=>`<option value="${esc(t.name)}">${esc(t.name)}</option>`).join('');
  sel.value=BSEL; sel.onchange=()=>{BSEL=sel.value;renderBreadth(M);};
  const d=el('div','pbody'); d.id='breadthbody';
  const pn=panel('c4','Breadth','',d,sel);
  renderBreadth(M,d); return pn; }
function renderBreadth(M,d){
  d=d||$('#breadthbody');
  if(BSEL!=='market'){ const t=M.themes.find(x=>x.name===BSEL);
    if(t){ const mk2=(k,v)=>`<div class="bstat"><span class="k">${k}</span><span><span class="meter"><i style="width:${Math.round(100*v)}%"></i></span> <b class="num">${Math.round(100*v)}%</b></span></div>`;
      d.innerHTML=`<div class="ch-lbl">${esc(t.name)} · ${t.n} names</div>`+
        mk2('Above 20DMA',t.above_ma20)+mk2('Above 50DMA',t.above_ma50)+mk2('Above 200DMA',t.above_ma200)+
        mk2('1-week participation',t.breadth)+
        `<div class="bstat"><span class="k">Phase</span><span class="phase ${PHASECLS[t.phase]||''}">${t.phase}</span></div>`+
        `<div class="ch-sub" style="margin-top:8px">Breadth history is tracked at market level; theme history arrives with the stored-history phase.</div>`;
      return; } }
  const b=M.breadth;
  const mk=(k,v)=>`<div class="bstat"><span class="k">${k}</span><span><span class="meter"><i style="width:${Math.round(100*v)}%"></i></span> <b class="num">${Math.round(100*v)}%</b></span></div>`;
  let trend='';
  if(b.trend&&b.trend.length>2){
    const w=300,h=64,mn=0,mx=1;
    const pts=b.trend.map((v,i)=>`${(i/(b.trend.length-1)*w).toFixed(1)},${(h-4-(v-mn)/(mx-mn)*(h-8)).toFixed(1)}`);
    trend=`<div class="ch-lbl" style="margin-top:10px">% above 20DMA — 30 days</div>
      <svg viewBox="0 0 ${w} ${h}" style="width:100%;display:block">
      <line x1="0" y1="${h-4-0.5*(h-8)}" x2="${w}" y2="${h-4-0.5*(h-8)}" stroke="var(--grid)"/>
      <polyline points="${pts.join(' ')}" fill="none" stroke="var(--accent)" stroke-width="1.6"/></svg>`; }
  d.innerHTML=mk('Above 20DMA',b.above_ma20)+mk('Above 50DMA',b.above_ma50)+mk('Above 200DMA',b.above_ma200)+
    `<div class="bstat"><span class="k">Advancers / decliners</span><b class="num"><span class="pos">${b.advancers}</span> / <span class="neg">${b.decliners}</span></b></div>`+
    `<div class="bstat"><span class="k">New 20-day highs / lows</span><b class="num"><span class="pos">${b.new_hi20}</span> / <span class="neg">${b.new_lo20}</span></b></div>`+trend; }

/* ---------- momentum map ---------- */
const AXES={
  'w_m':{x:'rel_1m',y:'rel_1w',xl:'1M vs benchmark',yl:'1W vs benchmark',
    q:['Emerging leaders','Established leaders','Washed out / laggards','Fading leaders']},
  'm_3m':{x:'rel_3m',y:'rel_1m',xl:'3M vs benchmark',yl:'1M vs benchmark',
    q:['Emerging leaders','Established leaders','Washed out / laggards','Fading leaders']},
  'theme':{x:'rel_1m',y:'theme_rel_1m',xl:'1M vs benchmark',yl:'1M vs own theme',
    q:['Best of weak theme','Leader of leaders','Laggard everywhere','Lagging its theme']},
  'vol':{x:'rel_1m',y:'vol_ratio',xl:'1M vs benchmark',yl:'volume vs 20-day avg',
    q:['Volume into weakness','Volume into strength','Quiet laggards','Quiet leaders'],absY:true}};
let MAPAX='w_m', MAPUNI='all', MAPSZ='to';
function mapPanel(M){
  const ctl=el('div','mapctl');
  const sel=(id,opts,cur,fn)=>{ const s=el('select','ctl'); s.id=id;
    opts.forEach(([v,l])=>{const o=el('option',null,l);o.value=v;if(v===cur)o.selected=true;s.appendChild(o);});
    s.onchange=()=>{fn(s.value); drawMap(M);}; return s; };
  ctl.appendChild(sel('axsel',[['w_m','1W vs 1M'],['m_3m','1M vs 3M'],['theme','vs own theme'],['vol','momentum vs volume']],MAPAX,v=>MAPAX=v));
  ctl.appendChild(sel('unisel',[['all','All names'],['sig','Signals only'],['watch','Watchlist'],
    ...M.themes.map(t=>['th:'+t.name,t.name])],MAPUNI,v=>MAPUNI=v));
  ctl.appendChild(sel('szsel',[['to','Size: turnover'],['eq','Size: equal']],MAPSZ,v=>MAPSZ=v));
  const body=el('div','pbody'); body.id='map';
  const p=panel('c8','Momentum map','hover for detail · click to open',body,ctl);
  setTimeout(()=>drawMap(M),0); return p; }

function drawMap(M){
  const box=$('#map'); if(!box) return;
  const ax=AXES[MAPAX];
  let E=Object.entries(M.names).filter(([k,v])=>v.liquid&&v[ax.x]!=null&&v[ax.y]!=null);
  if(MAPUNI==='sig') E=E.filter(([k,v])=>v.signal);
  else if(MAPUNI==='watch') E=E.filter(([k])=>WATCH.has(k));
  else if(MAPUNI.startsWith('th:')) E=E.filter(([k,v])=>v.theme===MAPUNI.slice(3));
  const W=980,H=430,Pd=52;
  const q=(vals,p)=>{const s=[...vals].sort((a,b)=>a-b);return s[Math.min(s.length-1,Math.floor(p*s.length))];};
  const xs=E.map(([k,v])=>v[ax.x]), ys=E.map(([k,v])=>v[ax.y]);
  if(!xs.length){ box.innerHTML='<div class="pbody" style="color:var(--muted)">No names in this universe — add stocks to your watchlist with the ☆ button.</div>'; return; }
  const xm=Math.max(Math.abs(q(xs,.02)),Math.abs(q(xs,.98)),.04);
  let ymid=0,ym;
  if(ax.absY){ ymid=1; ym=Math.max(q(ys,.98)-1,1-q(ys,.02),.8); } else ym=Math.max(Math.abs(q(ys,.02)),Math.abs(q(ys,.98)),.02);
  const X=v=>Pd+(Math.max(-xm,Math.min(xm,v))+xm)/(2*xm)*(W-2*Pd);
  const Y=v=>H-Pd-(Math.max(ymid-ym,Math.min(ymid+ym,v))-(ymid-ym))/(2*ym)*(H-2*Pd);
  const acts=new Set(M.action);
  const labeled=new Set(E.map(([k,v])=>[k,v[ax.x]]).sort((a,b)=>b[1]-a[1]).slice(0,3).map(x=>x[0]));
  E.map(([k,v])=>[k,v[ax.x]]).sort((a,b)=>a[1]-b[1]).slice(0,3).forEach(x=>labeled.add(x[0]));
  E.filter(([k])=>acts.has(k)).slice(0,5).forEach(([k])=>labeled.add(k));
  const advs=E.map(([k,v])=>v.adv20||0), advMax=Math.max(...advs,1);
  let dots='',labs='';const placed=[];
  E.forEach(([k,v])=>{
    const x=X(v[ax.x]),y=Y(v[ax.y]);
    const hot=acts.has(k), r=MAPSZ==='eq'?4:(3+4*Math.sqrt((v.adv20||0)/advMax));
    const t=`<div class="t">${k}${v.co?' — '+esc(v.co):''} · ${money(v.close,M.currency)}</div>`+
      `today ${pctT(v.ret_1d)} · 1W ${pctT(v.ret_1w)} · 1M ${pctT(v.ret_1m)}<br>`+
      `vs ${esc(M.benchmark)} 1M ${pctT(v.rel_1m)} · vol ${v.vol_ratio?v.vol_ratio.toFixed(1)+'×':'–'} · ${v.trend}`+
      (v.signal?`<br><b>${v.signal}</b> — score ${v.score}`:'');
    dots+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${hot?'var(--accent2)':'var(--accent)'}" opacity="${hot?0.95:0.45}" stroke="var(--surface)" stroke-width="1.6" style="cursor:pointer" data-open="${k}" data-tip="${esc(t)}"/>`;
    if(labeled.has(k)&&!placed.some(p=>Math.abs(p[0]-x)<40&&Math.abs(p[1]-y)<12)){
      placed.push([x,y]); labs+=`<text class="dlab" x="${(x+7).toFixed(1)}" y="${(y+3.5).toFixed(1)}">${k}</text>`; } });
  const cx=X(ax.absY?xm*0+0:0), cy=Y(ymid);
  box.innerHTML=`<svg viewBox="0 0 ${W} ${H}">
    <line x1="${Pd}" y1="${cy}" x2="${W-Pd}" y2="${cy}" stroke="var(--axis)"/>
    <line x1="${X(0)}" y1="${Pd}" x2="${X(0)}" y2="${H-Pd}" stroke="var(--axis)"/>
    <text class="qlab" x="${Pd}" y="${Pd-10}">${ax.q[0]}</text>
    <text class="qlab" x="${W-Pd}" y="${Pd-10}" text-anchor="end">${ax.q[1]}</text>
    <text class="qlab" x="${Pd}" y="${H-Pd+26}">${ax.q[2]}</text>
    <text class="qlab" x="${W-Pd}" y="${H-Pd+26}" text-anchor="end">${ax.q[3]}</text>
    <text class="alab" x="${W/2}" y="${H-8}" text-anchor="middle">${ax.xl} →</text>
    <text class="alab" x="12" y="${H/2}" text-anchor="middle" transform="rotate(-90 12 ${H/2})">${ax.yl} →</text>
    ${dots}${labs}</svg>
    <div class="ch-sub" style="padding:0 2px 8px"><span style="color:var(--accent2)">●</span> action-list name · <span style="color:var(--accent);opacity:.55">●</span> covered · sized by ${MAPSZ==='eq'?'equal':'20-day turnover'}</div>`;
  box.onclick=e=>{const k=e.target.dataset&&e.target.dataset.open;if(k)openDrawer(k);};
  bindTips(box); }

/* ---------- leaders / discovery ---------- */
let LTAB='Leading', LTHEME='all';
function leadersPanel(M){
  const tabs=el('div','sorts');
  ['Leading','Emerging','Falling','Washed out'].forEach(t=>{
    const c=el('button','schip'+(t===LTAB?' on':''),t);
    c.onclick=()=>{LTAB=t;renderLeaders(M);document.querySelectorAll('#lead .schip').forEach(x=>x.classList.toggle('on',x.textContent===t));};
    tabs.appendChild(c); });
  const sel=el('select','ctl'); sel.innerHTML='<option value="all">All themes</option>'+
    M.themes.map(t=>`<option value="${esc(t.name)}">${esc(t.name)}</option>`).join('');
  sel.value=LTHEME==='all'?'all':LTHEME; sel.onchange=()=>{LTHEME=sel.value;renderLeaders(M);};
  tabs.appendChild(sel);
  const body=el('div','pbody'); body.id='leadbody';
  const p=panel('c4','Discovery','by current signal state',body,tabs); p.id='lead';
  renderLeaders(M,body); return p; }
function renderLeaders(M,body){
  body=body||$('#leadbody');
  let E=Object.entries(M.names).filter(([k,v])=>v.liquid);
  if(LTHEME!=='all') E=E.filter(([k,v])=>v.theme===LTHEME);
  let rows=[];
  if(LTAB==='Leading') rows=E.filter(([k,v])=>['Trend leader','RS leader','Breakout'].includes(v.signal)).sort((a,b)=>b[1].score-a[1].score);
  if(LTAB==='Emerging') rows=E.filter(([k,v])=>['Emerging','Bounce watch'].includes(v.signal)).sort((a,b)=>b[1].score-a[1].score);
  if(LTAB==='Falling') rows=E.filter(([k,v])=>v.signal==='Losing momentum'||(v.rel_1m>0&&v.accel<-0.015)).sort((a,b)=>a[1].accel-b[1].accel);
  if(LTAB==='Washed out') rows=E.filter(([k,v])=>v.signal==='Washed out').sort((a,b)=>a[1].rel_1m-b[1].rel_1m);
  body.innerHTML=rows.slice(0,9).map(([k,v])=>`<div class="lrow">
      <span class="tick" data-open="${k}">${k}</span>
      <span class="num">${pct(v.ret_1w)}</span><span class="co num">1M ${pctT(v.rel_1m)}</span>
      ${v.signal?`<span class="sig">${v.signal}</span>`:''}</div>`).join('')
    ||'<div class="co" style="padding:6px 0">Nothing in this state today.</div>';
  body.onclick=e=>{const k=e.target.dataset.open;if(k)openDrawer(k);}; }

/* ---------- action list ---------- */
function actionPanel(M){
  const body=el('div','tablewrap');
  const rows=M.action.map(k=>[k,M.names[k]]).filter(([k,v])=>v);
  body.innerHTML=`<table id="acttable"><thead><tr><th></th><th>Name</th><th>Signal</th>
    <th class="num" title="Sum of the factor points — hover the value">Score</th>
    <th class="num">Price</th><th class="num lo">1D</th><th class="num">1W</th><th class="num">1M</th><th class="num lo">3M</th>
    <th class="num">vs ${esc(M.benchmark)}</th><th class="num lo">vs theme</th><th class="num">Vol</th><th class="lo">Theme</th></tr></thead><tbody>`+
    rows.map(([k,v])=>{
      const facts=(v.factors||[]).map(f=>`<div class="f"><span>${esc(f[0])}</span><b>+${f[1]}</b></div>`).join('');
      return `<tr>
      <td><button class="star ${WATCH.has(k)?'on':''}" data-star="${k}">${WATCH.has(k)?'★':'☆'}</button></td>
      <td><span class="tick" data-open="${k}">${k}</span> <span class="co">${esc(v.co||'')}</span></td>
      <td><span class="sig">${v.signal}</span></td>
      <td class="num"><b data-tip="${esc('<div class=t>Score '+v.score+'</div>'+facts)}">${v.score}</b></td>
      <td class="num">${money(v.close,M.currency)}</td>
      <td class="num lo">${pct(v.ret_1d)}</td><td class="num">${pct(v.ret_1w)}</td>
      <td class="num">${pct(v.ret_1m)}</td><td class="num lo">${pct(v.ret_3m)}</td>
      <td class="num">${pct(v.rel_1m)}</td><td class="num lo">${pct(v.theme_rel_1m)}</td>
      <td class="num">${v.vol_ratio?v.vol_ratio.toFixed(1)+'×':'–'}</td>
      <td class="co lo">${esc(v.theme)}</td></tr>`; }).join('')+'</tbody></table>';
  body.addEventListener('click',e=>{
    const s=e.target.dataset.star; if(s){ toggleWatch(s,e.target); return; }
    const k=e.target.dataset.open; if(k) openDrawer(k); });
  sortable(body.querySelector('table'));
  return panel('c12','Action list','mathematically interesting — not buy recommendations · hover a score for its factors',body); }

function toggleWatch(k,btn){ if(WATCH.has(k)){WATCH.delete(k);}else{WATCH.add(k);} saveWatch();
  document.querySelectorAll(`[data-star="${k}"]`).forEach(b=>{b.classList.toggle('on',WATCH.has(k));b.textContent=WATCH.has(k)?'★':'☆';}); }

function sortable(tb){ tb.querySelectorAll('thead th').forEach((th,i)=>th.addEventListener('click',()=>{
  const dir=th.dataset.d==='a'?-1:1; th.dataset.d=dir===1?'a':'d';
  const rows=[...tb.tBodies[0].rows];
  rows.sort((a,b)=>{const x=a.cells[i].textContent.replace(/[^0-9.+\-]/g,''),y=b.cells[i].textContent.replace(/[^0-9.+\-]/g,'');
    const nx=parseFloat(x),ny=parseFloat(y);
    return (!isNaN(nx)&&!isNaN(ny))?(nx-ny)*dir:a.cells[i].textContent.localeCompare(b.cells[i].textContent)*dir;});
  rows.forEach(r=>tb.tBodies[0].appendChild(r)); })); }

/* ================= GLOBAL VIEW ================= */
function renderGlobal(root){
  const G=P['global'];
  ['asx','us'].forEach(mk=>{ const M=P.markets[mk];
    const bench=M.tape[0];
    const c=el('div','panel c12');
    c.innerHTML=`<div class="phead"><h2>${M.label} — ${esc(M.regime.label)}</h2><span class="note">breadth ${Math.round(100*M.breadth.above_ma20)}% above 20DMA</span><span class="sp"></span><button class="tbtn" data-go="${mk}">Open ${M.label} view →</button></div>
      <div class="pbody" style="display:flex;gap:26px;flex-wrap:wrap;align-items:center">
      <span><span class="ch-lbl">${esc(bench.label)}</span><div class="ch-val">${Number(bench.close).toLocaleString()}</div><span class="ch-sub">${pct(bench.ret_1d)} today · ${pct(bench.ret_1m)} 1M</span></span>
      ${spark((bench.spark||[]).slice(-30),120,30)}
      <span class="co">${esc(M.read[0]?M.read[0].title:'')}</span></div>`;
    c.querySelector('[data-go]').onclick=()=>switchMarket(mk);
    const g=el('div','grid12'); g.appendChild(c); root.appendChild(g); });
  const groups={}; G.drivers.forEach(d=>{(groups[d.group]=groups[d.group]||[]).push(d);});
  Object.entries(groups).forEach(([g,ds])=>{
    const body=el('div','dgrid');
    body.innerHTML=ds.map(v=>`<div class="dcell">
      <div class="ch-lbl">${esc(v.label)}</div>
      <div class="ch-val" style="font-size:17px">${v.close!=null?Number(v.close).toLocaleString():'–'}</div>
      <div class="ch-sub">${pct(v.ret_1d)} today · 1W ${pct(v.ret_1w)} · 1M ${pct(v.ret_1m)} ${v.accel==='accelerating'?'▲':'▽'}</div>
      ${spark(v.spark,120,24)}</div>`).join('');
    const wrap=el('div','grid12'); wrap.appendChild(panel('c12',g,'',body)); root.appendChild(wrap); });
  root.appendChild(el('footer',null,`Cross-market drivers view · generated ${P.generated}`+
    (P.sample?' · <b style="color:var(--accent2)">SAMPLE DATA</b>':'')));
}

/* ================= DRAWER ================= */
function openDrawer(k){
  const M=P.markets[MK==='global'?'asx':MK];
  const v=(M.names&&M.names[k])||(P.markets.asx.names[k]?P.markets.asx.names[k]:P.markets.us.names[k]);
  const mkt=(M.names&&M.names[k])?M:(P.markets.asx.names[k]?P.markets.asx.names[k]&&P.markets.asx:P.markets.us);
  if(!v) return;
  const rel=(P.markets.asx.names[k]&&!M.names[k])?P.markets.asx:M;
  const cur=rel.currency||'$';
  const related=Object.entries(rel.names).filter(([kk,vv])=>vv.theme===v.theme&&kk!==k)
    .sort((a,b)=>(b[1].rel_1w??-9)-(a[1].rel_1w??-9)).slice(0,6);
  const maRow=(lbl,x)=>`<div class="kvrow"><span class="k">${lbl}</span><span class="num">${x==null?'–':(x>0?'above ':'below ')+pctT(Math.abs(x))}</span></div>`;
  const d=$('#drawer');
  d.innerHTML=`<button class="close" onclick="closeDrawer()">✕</button>
    <h3>${k} <button class="star ${WATCH.has(k)?'on':''}" data-star="${k}" onclick="toggleWatch('${k}',this)">${WATCH.has(k)?'★':'☆'}</button></h3>
    <div class="co2">${v.co?esc(v.co)+' · ':''}${esc(v.theme)} · ${esc(rel.label||'')}</div>
    <div class="price">${money(v.close,cur)} <span style="font-size:13px">${pct(v.ret_1d)}</span></div>
    ${lineChart((v.spark||[]).slice(-63),360,64)}
    <div class="dret">${[['1D',v.ret_1d],['1W',v.ret_1w],['1M',v.ret_1m],['3M',v.ret_3m]].map(([kk,x])=>`<div><div class="k">${kk}</div><div class="v">${pct(x)}</div></div>`).join('')}</div>
    ${v.signal?`<h4>Signal</h4><div><span class="sig">${v.signal}</span> <b class="num">score ${v.score}</b></div>
      <h4>Why?</h4>${(v.factors||[]).map(f=>`<div class="fac"><span>· ${esc(f[0])}</span><b>+${f[1]}</b></div>`).join('')}`
      :'<h4>Signal</h4><div class="co2">No signal state today — nothing changed enough to flag.</div>'}
    <h4>Relative strength</h4>
    <div class="kvrow"><span class="k">vs ${esc(rel.benchmark)} 1W / 1M / 3M</span><span class="num">${pct(v.rel_1w)} / ${pct(v.rel_1m)} / ${pct(v.rel_3m)}</span></div>
    <div class="kvrow"><span class="k">vs own theme (1M)</span><span class="num">${pct(v.theme_rel_1m)}</span></div>
    <h4>Trend</h4>
    ${maRow('20-day average',v.ma20)}${maRow('50-day average',v.ma50)}${maRow('200-day average',v.ma200)}
    <div class="kvrow"><span class="k">vs 60-day high</span><span class="num">${pct(v.hi60)}</span></div>
    <h4>Volume</h4>
    <div class="kvrow"><span class="k">Today vs 20-day average</span><span class="num">${v.vol_ratio?v.vol_ratio.toFixed(2)+'×':'–'}</span></div>
    <h4>Related — ${esc(v.theme)}</h4>
    <div>${related.map(([kk])=>`<span class="tk" data-open="${kk}">${kk}</span>`).join('')||'<span class="co2">—</span>'}</div>
    <button class="tbtn" style="width:100%;margin-top:14px;padding:8px" onclick="stockModal('${k}')">Open full analysis →</button>`;
  d.onclick=e=>{const kk=e.target.dataset.open;if(kk)openDrawer(kk);};
  d.classList.add('open'); $('#scrim').style.display='block'; }
function closeDrawer(){ $('#drawer').classList.remove('open'); $('#scrim').style.display='none'; }

/* ================= COMMAND PALETTE ================= */
let PALIDX=0;
function palOpen(){ $('#pal').style.display='flex'; const i=$('#palin'); i.value=''; palQuery(''); i.focus(); }
function palClose(){ $('#pal').style.display='none'; }
function palQuery(q){
  q=q.trim().toUpperCase(); const res=[];
  ['asx','us'].forEach(mk=>{ const M=P.markets[mk];
    Object.keys(M.names).forEach(k=>{ const nm=(M.names[k].co||'').toUpperCase(); if(!q||k.startsWith(q)||nm.includes(q)) res.push({kind:M.label+' stock',label:k+(M.names[k].co?' — '+M.names[k].co:''),sub:M.names[k].theme,act:()=>{palClose();if(MK!==mk)switchMarket(mk);openDrawer(k);}}); });
    M.themes.forEach(t=>{ if(!q||t.name.toUpperCase().includes(q)) res.push({kind:M.label+' theme',label:t.name,sub:`${t.phase} · 1W ${pctT(t.rel_1w)}`,act:()=>{palClose();if(MK!==mk)switchMarket(mk);themeModal(t,M);}}); }); });
  [['asx','ASX'],['us','US'],['global','Global']].forEach(([k,l])=>{ if(!q||l.toUpperCase().startsWith(q)) res.push({kind:'market',label:l+' view',sub:'',act:()=>{palClose();switchMarket(k);}}); });
  PALIDX=0;
  $('#palres').innerHTML=res.slice(0,12).map((r,i)=>`<div class="palrow${i===0?' sel':''}" data-i="${i}"><b>${esc(r.label)}</b><span class="co">${esc(r.sub)}</span><span class="kind">${r.kind}</span></div>`).join('')
    ||'<div class="palrow co">No matches</div>';
  window.PALRES=res.slice(0,12);
  $('#palres').querySelectorAll('.palrow[data-i]').forEach(rw=>rw.onclick=()=>PALRES[+rw.dataset.i].act()); }


/* ================= MODAL ================= */
function openModal(html){ $('#modal-box').innerHTML='<button class="mclose" onclick="closeModal()">✕</button>'+html;
  $('#modal').style.display='flex'; $('#modal-box').scrollTop=0;
  $('#modal-box').onclick=e=>{ const k=e.target.dataset&&e.target.dataset.open; if(k) openDrawer(k); };
  bindTips($('#modal-box')); }
function closeModal(){ $('#modal').style.display='none'; }

/* ---------- line chart (price + MAs, min/max labels) ---------- */
function lineChart(arr,w=860,h=180,opts={}){ if(!arr||arr.length<2) return '';
  const pad=6, padR=44;
  const mas=(opts.mas||[]).filter(n=>arr.length>=n).map(n=>{
    const out=[]; for(let i=n-1;i<arr.length;i++){ let s2=0; for(let j=i-n+1;j<=i;j++)s2+=arr[j]; out.push([i,s2/n]); } return [n,out]; });
  const all=arr.concat(mas.flatMap(([n,o])=>o.map(x=>x[1])));
  const mn=Math.min(...all), mx=Math.max(...all), rg=(mx-mn)||1;
  const X=i=>pad+i/(arr.length-1)*(w-pad-padR), Y=v=>h-12-(v-mn)/rg*(h-24);
  const line=(pts,col,wd)=>`<polyline points="${pts.map(([i,v])=>X(i).toFixed(1)+','+Y(v).toFixed(1)).join(' ')}" fill="none" stroke="${col}" stroke-width="${wd}" stroke-linejoin="round"/>`;
  const up=arr[arr.length-1]>=arr[0];
  let svg=`<line x1="${pad}" y1="${Y(arr[0]).toFixed(1)}" x2="${w-padR}" y2="${Y(arr[0]).toFixed(1)}" stroke="var(--grid)"/>`;
  const maCol={20:'var(--muted)',50:'var(--accent2)'};
  mas.forEach(([n,o])=>{ svg+=line(o,maCol[n]||'var(--axis)',1); });
  svg+=line(arr.map((v,i)=>[i,v]),up?'var(--pos)':'var(--neg)',2);
  svg+=`<text x="${w-padR+4}" y="${Y(mx)+4}" style="font-size:10px;fill:var(--muted)">${(100*(mx-1)).toFixed(0)>0?'+':''}${(100*(mx-1)).toFixed(0)}%</text>`;
  svg+=`<text x="${w-padR+4}" y="${Y(mn)+4}" style="font-size:10px;fill:var(--muted)">${(100*(mn-1)).toFixed(0)>0?'+':''}${(100*(mn-1)).toFixed(0)}%</text>`;
  svg+=`<text x="${w-padR+4}" y="${Y(arr[arr.length-1])+4}" style="font-size:10px;fill:var(--ink2);font-weight:600">${(100*(arr[arr.length-1]-1)).toFixed(0)>0?'+':''}${(100*(arr[arr.length-1]-1)).toFixed(0)}%</text>`;
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;display:block">${svg}</svg>`; }

/* ================= THEME DETAIL ================= */
function themeModal(t,M){
  const cons=Object.entries(M.names).filter(([k,v])=>v.theme===t.name);
  const groups=[
    ['Leaders', cons.filter(([k,v])=>v.rel_1m>0&&v.rel_1w>=0).sort((a,b)=>b[1].rel_1m-a[1].rel_1m)],
    ['Improving', cons.filter(([k,v])=>v.rel_1m<=0&&v.accel>0.005).sort((a,b)=>b[1].accel-a[1].accel)],
    ['Weakening', cons.filter(([k,v])=>v.rel_1m>0&&v.rel_1w<0).sort((a,b)=>a[1].rel_1w-b[1].rel_1w)],
  ];
  const used=new Set(groups.flatMap(([g,rows])=>rows.map(([k])=>k)));
  groups.push(['Laggards', cons.filter(([k])=>!used.has(k)).sort((a,b)=>a[1].rel_1m-b[1].rel_1m)]);
  const st=(k,v)=>`<div><div class="k">${k}</div><div class="v">${v}</div></div>`;
  const consTable=rows=>rows.length?`<table><thead><tr><th>Stock</th><th class="num">Price</th><th class="num lo">1D</th><th class="num">1W</th><th class="num">1M</th><th class="num">vs ${esc(M.benchmark)}</th><th class="num lo">Vol</th><th>Signal</th></tr></thead><tbody>`+
    rows.map(([k,v])=>`<tr><td><span class="tick" data-open="${k}">${k}</span> <span class="co">${esc(v.co||'')}</span></td>
      <td class="num">${money(v.close,M.currency)}</td><td class="num lo">${pct(v.ret_1d)}</td>
      <td class="num">${pct(v.ret_1w)}</td><td class="num">${pct(v.ret_1m)}</td>
      <td class="num">${pct(v.rel_1m)}</td><td class="num lo">${v.vol_ratio?v.vol_ratio.toFixed(1)+'×':'–'}</td>
      <td>${v.signal?`<span class="sig">${v.signal}</span>`:''}</td></tr>`).join('')+'</tbody></table>'
    :'<div class="co" style="padding:4px 0 8px">None today.</div>';
  openModal(`<h3>${esc(t.name)} <span class="phase ${PHASECLS[t.phase]||''}" style="vertical-align:middle">${t.phase}</span></h3>
    <div class="co2">${t.n} constituents · ${esc(M.label)} theme</div>
    <div class="mstats">
      ${st('Today',pct(t.ret_1d))}${st('1W vs '+esc(M.benchmark),pct(t.rel_1w))}
      ${st('1M vs '+esc(M.benchmark),pct(t.rel_1m))}${st('3M',pct(t.rel_3m))}
      ${st('Acceleration',pct(t.accel))}${st('Breadth',Math.round(100*t.breadth)+'%')}
      ${st('Volume',t.vol_ratio?t.vol_ratio.toFixed(1)+'×':'–')}${st('$ flow',t.flow_bps+' bps')}
    </div>
    <div class="mstats">
      ${st('Above 20DMA',Math.round(100*t.above_ma20)+'%')}
      ${st('Above 50DMA',Math.round(100*t.above_ma50)+'%')}
      ${st('Above 200DMA',Math.round(100*t.above_ma200)+'%')}
    </div>
    <div class="gh">Composite — 6 months, turnover-weighted</div>
    ${lineChart(t.spark,860,150)}
    ${groups.map(([g,rows])=>`<div class="gh">${g} <span class="co">· ${rows.length}</span></div><div class="tablewrap">${consTable(rows)}</div>`).join('')}`);
}

/* ================= FULL STOCK ANALYSIS ================= */
let STF=63;
function stockModal(k){
  const M=P.markets[MK==='global'?'asx':MK];
  const rel=(M.names&&M.names[k])?M:(P.markets.asx.names[k]?P.markets.asx:P.markets.us);
  const v=rel.names[k]; if(!v) return;
  const draw=()=>{
    const arr=(v.spark||[]).slice(-STF); const base=arr[0]||1;
    const norm=arr.map(x=>x/base);
    $('#stkchart').innerHTML=lineChart(norm,860,190,{mas:[20,50]})+
      `<div class="ch-sub" style="margin-top:2px">— price · <span style="color:var(--muted)">—</span> 20DMA · <span style="color:var(--accent2)">—</span> 50DMA · indexed to start of window · EOD data</div>`;
    document.querySelectorAll('#stf .schip').forEach(c=>c.classList.toggle('on',+c.dataset.tf===STF)); };
  const st=(k2,v2)=>`<div><div class="k">${k2}</div><div class="v">${v2}</div></div>`;
  const related=Object.entries(rel.names).filter(([kk,vv])=>vv.theme===v.theme&&kk!==k)
    .sort((a,b)=>(b[1].rel_1w??-9)-(a[1].rel_1w??-9)).slice(0,8);
  openModal(`<h3>${k}${v.co?' — '+esc(v.co):''}
      <button class="star ${WATCH.has(k)?'on':''}" data-star="${k}" onclick="toggleWatch('${k}',this)">${WATCH.has(k)?'★':'☆'}</button></h3>
    <div class="co2">${esc(v.theme)} · ${esc(rel.label)} · ${money(v.close,rel.currency)} <span style="font-size:12px">${pct(v.ret_1d)}</span></div>
    <div class="gh">Price <span class="tfchips" id="stf">${[[21,'1M'],[63,'3M'],[130,'6M']].map(([n,l])=>`<button class="schip" data-tf="${n}">${l}</button>`).join('')}</span></div>
    <div id="stkchart"></div>
    <div class="gh">Performance</div>
    <div class="mstats">
      ${st('1D',pct(v.ret_1d))}${st('1W',pct(v.ret_1w))}${st('1M',pct(v.ret_1m))}${st('3M',pct(v.ret_3m))}
      ${st('vs '+esc(rel.benchmark)+' 1M',pct(v.rel_1m))}${st('vs '+esc(rel.benchmark)+' 3M',pct(v.rel_3m))}
      ${st('vs '+esc(v.theme)+' 1M',pct(v.theme_rel_1m))}
    </div>
    <div class="gh">Technical structure</div>
    <div class="mstats">
      ${st('vs 20DMA',pct(v.ma20))}${st('vs 50DMA',pct(v.ma50))}${st('vs 200DMA',pct(v.ma200))}
      ${st('vs 60-day high',pct(v.hi60))}${st('Momentum',esc(v.trend))}${st('Volume',v.vol_ratio?v.vol_ratio.toFixed(2)+'×':'–')}
    </div>
    ${v.signal?`<div class="gh">Signal — ${v.signal} · score ${v.score}</div>
      ${(v.factors||[]).map(f=>`<div class="fac"><span>· ${esc(f[0])}</span><b>+${f[1]}</b></div>`).join('')}`:''}
    <div class="gh">Quantitative read</div>
    <div style="font-size:12.5px;color:var(--ink2);line-height:1.55">${quantRead(k,v,rel)}</div>
    <div class="gh">Related — ${esc(v.theme)}</div>
    <div>${related.map(([kk,vv])=>`<span class="tk" data-open="${kk}">${kk}</span>`).join('')}</div>
    <div class="stub" style="margin-top:16px">Fundamentals · news &amp; catalysts · institutional positioning — sections reserved; data sources arrive in later phases and will never be simulated.</div>`);
  $('#stf').onclick=e=>{ const tf=e.target.dataset.tf; if(tf){ STF=+tf; draw(); } };
  draw();
}
function quantRead(k,v,rel){
  const s=[];
  s.push(`${k} is ${v.rel_1m>=0?'ahead of':'behind'} the ${esc(rel.benchmark)} by ${pctT(Math.abs(v.rel_1m))} over the past month and ${v.rel_3m>=0?'ahead':'behind'} by ${pctT(Math.abs(v.rel_3m))} over three months.`);
  s.push(`This week it ran ${pctT(v.rel_1w)} versus the index, with momentum ${v.accel>0.005?'accelerating':v.accel<-0.005?'decelerating':'steady'}.`);
  s.push(`It trades ${v.ma50>0?'above':'below'} its 50-day average, ${pctT(Math.abs(v.ma200||0))} ${v.ma200>0?'above':'below'} the 200-day, and ${pctT(Math.abs(v.hi60||0))} from its 60-day high.`);
  s.push(`Today's turnover was ${v.vol_ratio?v.vol_ratio.toFixed(1):'–'}× its 20-day average.`);
  if(v.theme_rel_1m!=null) s.push(`Within ${esc(v.theme)}, it is ${v.theme_rel_1m>=0?'leading':'lagging'} the group by ${pctT(Math.abs(v.theme_rel_1m))} this month.`);
  s.push(`<i>This is a mechanical description of price and volume. It knows nothing about earnings, news, valuation or management — treat it as context, not a forecast.</i>`);
  return s.join(' ');
}

/* ================= HEATMAP ================= */
let HMC='ret_1d', HMS='to';
const HMMETRICS={ret_1d:['Today',1],ret_1w:['1W',1],ret_1m:['1M',1],rel_1m:['vs benchmark (1M)',1],vol_ratio:['Volume anomaly',0]};
function heatmapPanel(M){
  const ctl=el('div','mapctl');
  const sel=(opts,cur,fn)=>{ const x=el('select','ctl');
    opts.forEach(([v2,l])=>{const o=el('option',null,l);o.value=v2;if(v2===cur)o.selected=true;x.appendChild(o);});
    x.onchange=()=>{fn(x.value); drawHeat(M);}; return x; };
  ctl.appendChild(sel(Object.entries(HMMETRICS).map(([k2,[l]])=>[k2,'Colour: '+l]),HMC,v2=>HMC=v2));
  ctl.appendChild(sel([['to','Size: turnover'],['eq','Size: equal']],HMS,v2=>HMS=v2));
  const body=el('div','pbody'); body.id='heat';
  const pn=el('div','grid12'); const pa=panel('c12','Heatmap','grouped by theme · click any tile',body,ctl);
  setTimeout(()=>drawHeat(M),0); pn.appendChild(pa); return pn; }
function drawHeat(M){
  const box=$('#heat'); if(!box) return;
  const diverging=HMMETRICS[HMC][1]===1;
  const E=Object.entries(M.names).filter(([k,v])=>v.liquid&&v[HMC]!=null);
  const vals=E.map(([k,v])=>Math.abs(diverging?v[HMC]:v[HMC]-1)).sort((a,b)=>a-b);
  const scale=vals[Math.floor(vals.length*0.92)]||0.03;
  const advMax=Math.max(...E.map(([k,v])=>v.adv20||0),1);
  const themes=[...M.themes].sort((a,b)=>(b.rel_1m??-9)-(a.rel_1m??-9));
  box.innerHTML=themes.map(t=>{
    const rows=E.filter(([k,v])=>v.theme===t.name).sort((a,b)=>(b[1].adv20||0)-(a[1].adv20||0));
    if(!rows.length) return '';
    return `<div class="hm-sec"><div class="hm-sechead">${esc(t.name)} <span class="co">${pctT(t.rel_1m)} 1M vs ${esc(M.benchmark)}</span></div>
      <div class="hm-tiles">`+rows.map(([k,v])=>{
        const raw=diverging?v[HMC]:(v[HMC]-1);
        const pI=Math.min(Math.abs(raw)/scale,1);
        const mixc=diverging?(raw>=0?'var(--pos)':'var(--neg)'):'var(--accent)';
        const bg=`color-mix(in oklab, ${mixc} ${(8+58*pI).toFixed(0)}%, var(--surface))`;
        const wpx=HMS==='eq'?58:Math.round(44+92*Math.sqrt((v.adv20||0)/advMax));
        const showVal=wpx>=56;
        const tt=`<div class="t">${k}${v.co?' — '+esc(v.co):''}</div>${HMMETRICS[HMC][0]}: ${diverging?pctT(raw):(v[HMC].toFixed(1)+'×')}<br>today ${pctT(v.ret_1d)} · 1W ${pctT(v.ret_1w)} · 1M ${pctT(v.ret_1m)}${v.signal?'<br><b>'+v.signal+'</b>':''}`;
        return `<div class="hm-tile" style="width:${wpx}px;background:${bg}" data-open="${k}" data-tip="${esc(tt)}"><b>${k}</b>${showVal?`<span>${diverging?pctT(raw):(v[HMC].toFixed(1)+'×')}</span>`:''}</div>`;
      }).join('')+'</div></div>'; }).join('');
  box.onclick=e=>{ const t2=e.target.closest('[data-open]'); if(t2) openDrawer(t2.dataset.open); };
  bindTips(box); }

/* ================= WATCHLIST VIEW ================= */
function watchlistPanel(M){
  const body=el('div','tablewrap');
  const rows=[...WATCH].map(k=>[k,M.names[k]]).filter(([k,v])=>v);
  const pn=el('div','grid12');
  if(!rows.length){
    body.innerHTML=`<div class="empty">No ${M.label} names on your watchlist yet.<br><br>Star any ticker — in the action list, the drawer, or a theme view — and it lands here.<br><span class="co">The watchlist is stored in this browser. Alerts &amp; notifications are reserved for a later phase.</span></div>`;
    pn.appendChild(panel('c12','Watchlist','',body)); return pn; }
  body.innerHTML=`<table><thead><tr><th></th><th>Name</th><th>Signal</th>
    <th class="num">Price</th><th class="num">Today</th><th class="num">1W</th><th class="num">1M</th>
    <th class="num">vs ${esc(M.benchmark)}</th><th class="num lo">Vol</th><th class="lo">Trend</th><th class="lo">Theme</th></tr></thead><tbody>`+
    rows.map(([k,v])=>`<tr>
      <td><button class="star on" data-star="${k}">★</button></td>
      <td><span class="tick" data-open="${k}">${k}</span> <span class="co">${esc(v.co||'')}</span></td>
      <td>${v.signal?`<span class="sig">${v.signal}</span>`:'<span class="co">—</span>'}</td>
      <td class="num">${money(v.close,M.currency)}</td>
      <td class="num">${pct(v.ret_1d)}</td><td class="num">${pct(v.ret_1w)}</td><td class="num">${pct(v.ret_1m)}</td>
      <td class="num">${pct(v.rel_1m)}</td><td class="num lo">${v.vol_ratio?v.vol_ratio.toFixed(1)+'×':'–'}</td>
      <td class="lo trend-${v.trend}">${v.trend==='improving'?'▲':'▼'} ${v.trend}</td>
      <td class="co lo">${esc(v.theme)}</td></tr>`).join('')+'</tbody></table>';
  body.addEventListener('click',e=>{
    const st2=e.target.dataset.star; if(st2){ toggleWatch(st2,e.target); render(); return; }
    const k=e.target.dataset.open; if(k) openDrawer(k); });
  sortable(body.querySelector('table'));
  const other=[...WATCH].filter(k=>!M.names[k]).length;
  pn.appendChild(panel('c12','Watchlist',`${rows.length} ${M.label} names`+(other?` · ${other} on other markets`:''),body));
  return pn; }

/* ================= boot ================= */
function boot(){
  document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>switchMarket(b.dataset.mk));
  $('#themebtn').onclick=()=>{ const r=document.documentElement;
    const cur=r.dataset.theme||'auto';
    r.dataset.theme=cur==='auto'?'dark':cur==='dark'?'light':'auto';
    $('#themebtn').textContent={auto:'◐ Auto',dark:'● Dark',light:'○ Light'}[r.dataset.theme]; };
  const mq=matchMedia('(prefers-color-scheme: dark)');
  const sync=()=>document.documentElement.classList.toggle('sys-dark',mq.matches);
  mq.addEventListener('change',sync); sync();
  $('#searchbtn').onclick=palOpen;
  $('#scrim').onclick=closeDrawer;
  $('#pal').onclick=e=>{if(e.target.id==='pal')palClose();};
  $('#modal').onclick=e=>{if(e.target.id==='modal')closeModal();};
  $('#palin').addEventListener('input',e=>palQuery(e.target.value));
  document.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();palOpen();}
    if(e.key==='Escape'){palClose();closeDrawer();closeModal();}
    if($('#pal').style.display==='flex'&&['ArrowDown','ArrowUp','Enter'].includes(e.key)){
      e.preventDefault(); const rows=[...$('#palres').querySelectorAll('.palrow[data-i]')];
      if(e.key==='Enter'){ if(PALRES&&PALRES[PALIDX])PALRES[PALIDX].act(); return; }
      PALIDX=Math.max(0,Math.min(rows.length-1,PALIDX+(e.key==='ArrowDown'?1:-1)));
      rows.forEach((r,i)=>r.classList.toggle('sel',i===PALIDX)); } });
  render(); }
document.addEventListener('DOMContentLoaded',boot);
"""

SHELL = r"""<!doctype html><html lang="en" data-theme="auto"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Analyser</title><style>__CSS__</style></head><body>
<header id="topbar">
  <div id="brand">Stock Analyser <span>· daily terminal</span></div>
  <nav class="tabs">
    <button class="tab on" data-mk="asx">ASX</button>
    <button class="tab" data-mk="us">US</button>
    <button class="tab" data-mk="global">Global</button>
  </nav>
  <span class="sp"></span>
  __SAMPLE__
  <button class="tbtn" id="searchbtn">Search&nbsp;&nbsp;⌘K</button>
  <button class="tbtn" id="themebtn">◐ Auto</button>
</header>
<main id="wrap"></main>
<div id="tip"></div>
<div id="scrim"></div><aside id="drawer"></aside>
<div id="modal"><div id="modal-box" class="modal-box"></div></div>
<div id="pal"><div id="palbox"><input id="palin" placeholder="Search stocks, themes, markets…"><div id="palres"></div></div></div>
<script>window.PAYLOAD=__PAYLOAD__;</script>
<script>__JS__</script>
</body></html>"""


def render(data: dict) -> str:
    sample = ('<span class="chip-sample">SAMPLE DATA</span>' if data.get("sample") else "")
    return (SHELL
            .replace("__CSS__", CSS)
            .replace("__SAMPLE__", sample)
            .replace("__PAYLOAD__", json.dumps(data, separators=(",", ":")))
            .replace("__JS__", JS))
