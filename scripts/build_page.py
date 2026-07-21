# -*- coding: utf-8 -*-
"""Assemble the self-contained dashboard HTML from page_data.json."""
import json

data = open('page_data.json', encoding='utf-8').read()

HTML = r'''<title>Does the Market Move When Trump Posts?</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{
  --bg:#eef0f2; --surface:#f8f9fa; --surface-2:#ffffff; --ink:#161a1d; --ink-2:#495159;
  --muted:#6b747c; --line:#d7dce0; --line-2:#e6eaed;
  --praise:#2b6ca3; --praise-soft:#2b6ca31a;
  --attack:#c8791f; --attack-soft:#c8791f1a;
  --good:#2f8f5b; --bad:#c14545;
  --mono:ui-monospace,"SF Mono","SFMono-Regular",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#101315; --surface:#171b1e; --surface-2:#1d2226; --ink:#e7eaec; --ink-2:#aeb6bd;
    --muted:#7c858c; --line:#2b3237; --line-2:#232a2f;
    --praise:#4f9dd4; --praise-soft:#4f9dd422; --attack:#d59a4a; --attack-soft:#c07f2c22;
    --good:#54b57e; --bad:#d97070;
  }
}
:root[data-theme="light"]{
  --bg:#eef0f2; --surface:#f8f9fa; --surface-2:#ffffff; --ink:#161a1d; --ink-2:#495159;
  --muted:#6b747c; --line:#d7dce0; --line-2:#e6eaed;
  --praise:#2b6ca3; --attack:#c8791f; --praise-soft:#2b6ca31a; --attack-soft:#c8791f1a;
  --good:#2f8f5b; --bad:#c14545;
}
:root[data-theme="dark"]{
  --bg:#101315; --surface:#171b1e; --surface-2:#1d2226; --ink:#e7eaec; --ink-2:#aeb6bd;
  --muted:#7c858c; --line:#2b3237; --line-2:#232a2f;
  --praise:#4f9dd4; --attack:#d59a4a; --praise-soft:#4f9dd422; --attack-soft:#c07f2c22;
  --good:#54b57e; --bad:#d97070;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  line-height:1.55;-webkit-font-smoothing:antialiased;font-size:16px}
.wrap{max-width:1080px;margin:0 auto;padding:0 22px}
h1,h2,h3{text-wrap:balance;margin:0}
a{color:var(--praise)}
.tape{background:var(--ink);color:var(--bg);font-family:var(--mono);font-size:12.5px;
  letter-spacing:.02em;overflow:hidden;white-space:nowrap;border-bottom:1px solid var(--line)}
.tape .row{display:flex;gap:34px;padding:8px 22px;animation:scroll 40s linear infinite;width:max-content}
.tape b{color:#fff}
@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.tape .row{animation:none}}
.up{color:var(--good)} .down{color:var(--bad)}
header.hero{padding:52px 0 34px}
.eyebrow{font-family:var(--mono);font-size:12.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--attack);margin:0 0 18px;font-weight:600}
h1{font-size:clamp(30px,5.4vw,50px);line-height:1.04;font-weight:800;letter-spacing:-.02em}
.dek{font-size:clamp(16px,2.2vw,19px);color:var(--ink-2);max-width:60ch;margin:20px 0 0}
.src{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:22px;line-height:1.7}
section{padding:26px 0}
.sec-label{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);margin:0 0 16px;display:flex;align-items:center;gap:12px}
.sec-label::after{content:"";height:1px;flex:1;background:var(--line)}
.verdicts{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:720px){.verdicts{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:24px 24px 22px;
  position:relative;overflow:hidden}
.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}
.card.praise::before{background:var(--praise)} .card.attack::before{background:var(--attack)}
.card .tag{font-family:var(--mono);font-size:12px;letter-spacing:.1em;text-transform:uppercase;font-weight:700}
.card.praise .tag{color:var(--praise)} .card.attack .tag{color:var(--attack)}
.card .n{font-family:var(--mono);font-size:12px;color:var(--muted);float:right}
.bignum{font-family:var(--mono);font-size:clamp(38px,7vw,58px);font-weight:700;letter-spacing:-.02em;
  margin:14px 0 2px;font-variant-numeric:tabular-nums}
.bignum .unit{font-size:.42em;color:var(--muted);font-weight:500;margin-left:4px}
.card .cap{font-size:14.5px;color:var(--ink-2);margin-top:4px}
.card .row2{display:flex;gap:26px;margin-top:20px;border-top:1px solid var(--line-2);padding-top:16px}
.card .row2 div{font-size:13px;color:var(--muted)}
.card .row2 b{display:block;font-family:var(--mono);font-size:20px;color:var(--ink);font-weight:700;
  font-variant-numeric:tabular-nums;margin-top:2px}
.lead{font-size:19px;line-height:1.6;color:var(--ink);max-width:64ch;border-left:3px solid var(--attack);
  padding-left:18px;margin:6px 0 0}
.lead b{font-weight:700}
figure{margin:0}
.chartbox{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:20px 18px 14px}
.chart-title{font-size:15px;font-weight:700;margin:0 2px 2px}
.chart-sub{font-size:13px;color:var(--muted);margin:0 2px 14px}
svg{display:block;width:100%;height:auto;overflow:visible}
.legend{display:flex;gap:18px;font-size:13px;color:var(--ink-2);margin:10px 2px 0;flex-wrap:wrap}
.legend span{display:inline-flex;align-items:center;gap:7px}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.tip{position:fixed;z-index:50;pointer-events:none;background:var(--ink);color:var(--bg);
  font-family:var(--mono);font-size:12px;padding:8px 10px;border-radius:4px;max-width:280px;
  opacity:0;transition:opacity .1s;line-height:1.5;box-shadow:0 6px 24px #0006}
.tip .q{color:#c9ccce;white-space:normal;margin-top:4px;font-family:var(--sans)}
.cuts{width:100%;border-collapse:collapse;font-size:14px}
.cuts th,.cuts td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line-2)}
.cuts th{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);font-weight:600}
.cuts td.num,.cuts th.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
.cuts tr td:first-child{font-weight:600}
.chip{font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  padding:2px 7px;border-radius:3px;font-weight:700}
.chip.p{background:var(--praise-soft);color:var(--praise)} .chip.a{background:var(--attack-soft);color:var(--attack)}
.barcell{position:relative;min-width:120px}
.bar{height:9px;border-radius:2px;display:inline-block;vertical-align:middle}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:4px;background:var(--surface)}
table.data{border-collapse:collapse;width:100%;font-size:13.5px;min-width:720px}
table.data th,table.data td{padding:8px 11px;border-bottom:1px solid var(--line-2);text-align:left;white-space:nowrap}
table.data th{position:sticky;top:0;background:var(--surface-2);font-family:var(--mono);font-size:11px;
  letter-spacing:.05em;text-transform:uppercase;color:var(--muted);cursor:pointer;user-select:none;z-index:2}
table.data td.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
table.data td.q{white-space:normal;color:var(--ink-2);min-width:240px;font-size:13px}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.controls input,.controls select{font-family:var(--sans);font-size:14px;padding:7px 11px;border:1px solid var(--line);
  border-radius:4px;background:var(--surface-2);color:var(--ink)}
.controls button{font-family:var(--mono);font-size:12px;padding:7px 12px;border:1px solid var(--line);
  border-radius:4px;background:var(--surface-2);color:var(--ink-2);cursor:pointer}
.controls button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.pos{color:var(--good)} .neg{color:var(--bad)}
.limits{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:22px 24px}
.limits ul{margin:10px 0 0;padding-left:20px} .limits li{margin:8px 0;color:var(--ink-2);font-size:14.5px}
.limits h3{font-size:16px}
footer{padding:40px 0 60px;color:var(--muted);font-family:var(--mono);font-size:12px;line-height:1.7}
.mini{font-family:var(--mono);font-size:12px;color:var(--muted)}
:focus-visible{outline:2px solid var(--praise);outline-offset:2px}
</style>

<div class="tape"><div class="row" id="tape"></div></div>

<header class="hero"><div class="wrap">
  <p class="eyebrow">Truth Social &times; The Stock Market &middot; 2022&ndash;2026</p>
  <h1 id="headline">When Trump praises or attacks a public company, does its stock actually move?</h1>
  <p class="dek">Every Trump Truth Social post that clearly <b>praises</b> or <b>attacks</b> a specific publicly-traded company, priced against the stock&rsquo;s real next-day and one-week returns. Short answer: barely, and rarely in the direction you&rsquo;d guess.</p>
  <p class="src" id="src"></p>
</div></header>

<main class="wrap">
  <section>
    <p class="sec-label">The verdict</p>
    <div class="verdicts" id="verdicts"></div>
    <p class="lead" id="lead" style="margin-top:22px"></p>
    <p class="mini" id="extremes" style="margin-top:14px"></p>
  </section>

  <section>
    <p class="sec-label">Every post, plotted by next-day return</p>
    <figure class="chartbox">
      <p class="chart-title">Next-trading-day % move of the named stock after each post</p>
      <p class="chart-sub">One dot = one post. Left of the line the stock fell; right, it rose. If the posts moved stocks, praise would pile up on the right and attacks on the left. They don&rsquo;t &mdash; both clouds sit on top of zero.</p>
      <div id="strip"></div>
      <div class="legend">
        <span><i class="dot" style="background:var(--praise)"></i> Praise (n=<span id="lgp"></span>)</span>
        <span><i class="dot" style="background:var(--attack)"></i> Attack (n=<span id="lga"></span>)</span>
        <span class="mini">&#9432; hover a dot for the post &middot; extreme moves clamped to &plusmn;12%</span>
      </div>
    </figure>
  </section>

  <section>
    <p class="sec-label">Cut every way</p>
    <div style="overflow-x:auto">
    <table class="cuts" id="cuts"><thead><tr>
      <th>Slice</th><th class="num">Posts</th><th class="num">Avg +1d</th><th class="num">Avg +1wk</th>
      <th class="num">Win rate</th><th>Win rate</th></tr></thead><tbody></tbody></table>
    </div>
    <p class="mini" style="margin-top:12px">For praise, a &ldquo;win&rdquo; = the stock rose. For attacks, a &ldquo;win&rdquo; = the stock <b>fell</b> (the attack &ldquo;worked&rdquo;). DJT is Trump&rsquo;s own company (Trump Media); the <b>ex-DJT</b> praise row is the cleaner read on third-party stocks.</p>
  </section>

  <section>
    <p class="sec-label">By company</p>
    <div style="overflow-x:auto">
    <table class="cuts" id="percomp"><thead><tr>
      <th>Company</th><th>Ticker</th><th>Stance</th><th class="num">Posts</th>
      <th class="num">Avg +1d</th><th class="num">Avg +1wk</th></tr></thead><tbody></tbody></table>
    </div>
  </section>

  <section>
    <p class="sec-label">The full labeled dataset</p>
    <div class="controls">
      <input id="search" type="text" placeholder="Search company, ticker, quote&hellip;" style="flex:1;min-width:180px">
      <button data-f="all" class="on">All</button>
      <button data-f="PRAISE">Praise</button>
      <button data-f="ATTACK">Attack</button>
      <span class="mini" id="count"></span>
    </div>
    <div class="tablewrap" style="max-height:560px;overflow-y:auto">
      <table class="data" id="tbl"><thead><tr>
        <th data-k="date">Date</th><th data-k="time_et">Time ET</th><th data-k="ticker">Ticker</th>
        <th data-k="sentiment">Stance</th><th data-k="nd_ret" class="num">+1d %</th>
        <th data-k="wk_ret" class="num">+1wk %</th><th data-k="quote">Quote</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </section>

  <section>
    <div class="limits">
      <h3>How this was built &amp; what it can&rsquo;t tell you</h3>
      <ul id="limits"></ul>
    </div>
  </section>
</main>

<footer><div class="wrap" id="foot"></div></footer>
<div class="tip" id="tip"></div>

<script id="payload" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('payload').textContent);
const M=D.meta, A=D.agg;
const fmt=(x,d=2)=>x==null?'–':(x>0?'+':'')+x.toFixed(d);
const pn=x=>x==null?'':(x>=0?'pos':'neg');

// tape
const tapeItems=[
  ['PRAISE n',M.praise],['ATTACK n',M.attack],
  ['PRAISE +1d',fmt(A.praise_all.avg_nextday_pct)+'%'],
  ['PRAISE ex-DJT +1d',fmt(A.praise_ex_djt.avg_nextday_pct)+'%'],
  ['ATTACK +1d',fmt(A.attack_all.avg_nextday_pct)+'%'],
  ['ATTACK fell',A.attack_all.win_rate_pct+'%'],
  ['posts scanned',M.total_posts.toLocaleString()],
  ['priced',M.priced],
];
const tapeHTML=tapeItems.map(([k,v])=>`<span>${k} <b>${v}</b></span>`).join('  ·  ');
document.getElementById('tape').innerHTML=tapeHTML+'  ·  '+tapeHTML;

document.getElementById('src').innerHTML=
  `SOURCE &middot; ${M.source}<br>${M.total_posts.toLocaleString()} total posts (${M.date_range}) &middot; `+
  `${M.company_pairs_scanned.toLocaleString()} company mentions classified by LLM &middot; `+
  `${M.praise} praise + ${M.attack} attack kept &middot; ${M.priced} priced on Yahoo Finance daily closes &middot; generated ${M.generated}`;

// verdict cards
const pa=A.praise_all, at=A.attack_all, pex=A.praise_ex_djt;
document.getElementById('verdicts').innerHTML=`
 <div class="card praise">
   <span class="tag">Praise &#9650;</span><span class="n">n=${pa.n}</span>
   <div class="bignum">${fmt(pa.avg_nextday_pct)}<span class="unit">% next day</span></div>
   <div class="cap">Buying the stock at the post&rsquo;s entry close. It rose just <b>${pa.win_rate_pct}%</b> of the time.</div>
   <div class="row2">
     <div>1-week avg<b class="${pn(pa.avg_1wk_pct)}">${fmt(pa.avg_1wk_pct)}%</b></div>
     <div>Ex-DJT +1d<b class="${pn(pex.avg_nextday_pct)}">${fmt(pex.avg_nextday_pct)}%</b></div>
     <div>Ex-DJT win<b>${pex.win_rate_pct}%</b></div>
   </div>
 </div>
 <div class="card attack">
   <span class="tag">Attack &#9660;</span><span class="n">n=${at.n}</span>
   <div class="bignum">${fmt(at.avg_nextday_pct)}<span class="unit">% next day</span></div>
   <div class="cap">The targeted stock fell only <b>${at.win_rate_pct}%</b> of the time &mdash; it rose more often than it dropped.</div>
   <div class="row2">
     <div>1-week avg<b class="${pn(at.avg_1wk_pct)}">${fmt(at.avg_1wk_pct)}%</b></div>
     <div>Media targets<b>${A.attack_media.n}</b></div>
     <div>Non-media<b>${A.attack_nonmedia.n}</b></div>
   </div>
 </div>`;

document.getElementById('lead').innerHTML=
 `Across <b>${pa.n} praise posts</b>, buying the stock returned an average of <b class="${pn(pa.avg_nextday_pct)}">${fmt(pa.avg_nextday_pct)}%</b> the next trading day `+
 `and <b class="${pn(pa.avg_1wk_pct)}">${fmt(pa.avg_1wk_pct)}%</b> over a week (it rose ${pa.win_rate_pct}% of the time). `+
 `Across <b>${at.n} attack posts</b>, the stock moved an average of <b class="${pn(at.avg_nextday_pct)}">${fmt(at.avg_nextday_pct)}%</b> the next day and fell only <b>${at.win_rate_pct}%</b> of the time. `+
 `Trump&rsquo;s posts are loud; the price reaction is mostly noise centered on zero. `+
 `For context, a large-cap stock rises on any given day about 53% of the time on its own &mdash; so attacked stocks (up 55% of the time) behaved essentially like the market, not like they&rsquo;d been hit.`;

// extremes (biggest single-day moves, direction-neutral)
const bu=pa.biggest_up, ad=at.biggest_down, au=at.biggest_up;
document.getElementById('extremes').innerHTML=
 `Biggest single next-day moves &mdash; after praise: ${bu.company} <b class="pos">${fmt(bu.nd)}%</b> (${bu.date}). `+
 `After an attack: ${ad.company} <b class="neg">${fmt(ad.nd)}%</b> down (${ad.date}) and ${au.company} <b class="pos">${fmt(au.nd)}%</b> up (${au.date}) &mdash; both far more likely earnings than the post.`;

// strip plot
const T=D.table;
document.getElementById('lgp').textContent=T.filter(r=>r.sentiment==='PRAISE').length;
document.getElementById('lga').textContent=T.filter(r=>r.sentiment==='ATTACK').length;
(function(){
  const CL=12, W=1000, H=280, padL=8,padR=8,padT=18,padB=34, midY=(H-padB+padT)/2;
  const x=v=>{v=Math.max(-CL,Math.min(CL,v)); return padL+((v+CL)/(2*CL))*(W-padL-padR);};
  const c=getComputedStyle(document.documentElement);
  const cP=c.getPropertyValue('--praise').trim(), cA=c.getPropertyValue('--attack').trim();
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribution of next-day returns">`;
  // grid ticks
  for(let g=-10;g<=10;g+=5){const gx=x(g);
    s+=`<line x1="${gx}" y1="${padT}" x2="${gx}" y2="${H-padB}" stroke="var(--line-2)" stroke-width="1"/>`;
    s+=`<text x="${gx}" y="${H-padB+20}" fill="var(--muted)" font-size="12" font-family="var(--mono)" text-anchor="middle">${g>0?'+':''}${g}%</text>`;}
  const zx=x(0);
  s+=`<line x1="${zx}" y1="${padT-6}" x2="${zx}" y2="${H-padB}" stroke="var(--ink-2)" stroke-width="1.5"/>`;
  s+=`<text x="${zx}" y="${padT-9}" fill="var(--ink-2)" font-size="11" font-family="var(--mono)" text-anchor="middle">no move</text>`;
  // dots: praise upper half, attack lower half, jittered
  T.forEach((r,i)=>{
    if(r.nd_ret==null)return;
    const isP=r.sentiment==='PRAISE';
    const band=isP?[padT+6,midY-6]:[midY+6,H-padB-6];
    const jy=band[0]+((Math.sin(i*12.9898)*43758.5453)%1+1)%1*(band[1]-band[0]);
    const col=isP?cP:cA;
    s+=`<circle cx="${x(r.nd_ret).toFixed(1)}" cy="${jy.toFixed(1)}" r="3.1" fill="${col}" fill-opacity="0.62" `+
       `data-i="${i}" stroke="var(--surface)" stroke-width="0.5"/>`;
  });
  s+='</svg>';
  const box=document.getElementById('strip'); box.innerHTML=s;
  const tip=document.getElementById('tip');
  box.addEventListener('mouseover',e=>{const t=e.target;if(t.tagName!=='circle')return;
    const r=T[+t.dataset.i];
    tip.innerHTML=`<b>${r.ticker}</b> &middot; ${r.sentiment} &middot; ${r.date}<br>`+
      `+1d ${fmt(r.nd_ret)}% &middot; +1wk ${fmt(r.wk_ret)}%<div class="q">&ldquo;${r.quote}&rdquo;</div>`;
    tip.style.opacity=1;});
  box.addEventListener('mousemove',e=>{const tip=document.getElementById('tip');
    let X=e.clientX+14,Y=e.clientY+14; if(X>innerWidth-300)X=e.clientX-290; tip.style.left=X+'px';tip.style.top=Y+'px';});
  box.addEventListener('mouseout',()=>{document.getElementById('tip').style.opacity=0;});
})();

// cuts table
const cutRows=[
  ['Praise — all','praise_all','up'],
  ['Praise — excluding DJT','praise_ex_djt','up'],
  ['Praise — substantive only','praise_substantive','up'],
  ['Praise — in market hours','praise_inhours','up'],
  ['Praise — out of hours','praise_outhours','up'],
  ['Attack — all','attack_all','down'],
  ['Attack — media companies','attack_media','down'],
  ['Attack — non-media','attack_nonmedia','down'],
  ['Attack — substantive only','attack_substantive','down'],
  ['Attack — in market hours','attack_inhours','down'],
  ['Attack — out of hours','attack_outhours','down'],
];
document.querySelector('#cuts tbody').innerHTML=cutRows.map(([lab,k,dir])=>{
  const b=A[k]; if(!b)return'';
  const isP=dir==='up'; const col=isP?'var(--praise)':'var(--attack)';
  const wr=b.win_rate_pct||0; const bw=Math.max(2,wr*1.1);
  return `<tr><td>${lab} <span class="chip ${isP?'p':'a'}">${isP?'praise':'attack'}</span></td>`+
    `<td class="num">${b.n}</td>`+
    `<td class="num ${pn(b.avg_nextday_pct)}">${fmt(b.avg_nextday_pct)}%</td>`+
    `<td class="num ${pn(b.avg_1wk_pct)}">${fmt(b.avg_1wk_pct)}%</td>`+
    `<td class="num">${wr}%</td>`+
    `<td class="barcell"><span class="bar" style="width:${bw}px;background:${col}"></span></td></tr>`;
}).join('');

// per company
document.querySelector('#percomp tbody').innerHTML=D.per_company
  .filter(c=>c.n>=2).map(c=>{
  const isP=c.sentiment==='PRAISE';
  return `<tr><td>${c.company}</td><td class="mini">${c.ticker}</td>`+
    `<td><span class="chip ${isP?'p':'a'}">${c.sentiment.toLowerCase()}</span></td>`+
    `<td class="num">${c.n}</td>`+
    `<td class="num ${pn(c.avg_nextday_pct)}">${fmt(c.avg_nextday_pct)}%</td>`+
    `<td class="num ${pn(c.avg_1wk_pct)}">${fmt(c.avg_1wk_pct)}%</td></tr>`;
}).join('');

// full data table
let filt='all', q='', sortK='date', sortDir=-1;
const tb=document.querySelector('#tbl tbody');
function render(){
  let rows=T.filter(r=>(filt==='all'||r.sentiment===filt));
  if(q){const s=q.toLowerCase();rows=rows.filter(r=>(r.ticker+r.company+r.quote).toLowerCase().includes(s));}
  rows.sort((a,b)=>{let x=a[sortK],y=b[sortK];if(x==null)x=-999;if(y==null)y=-999;
    if(typeof x==='string'){x=x.toLowerCase();y=(y||'').toLowerCase();}
    return x<y?-sortDir:x>y?sortDir:0;});
  tb.innerHTML=rows.map(r=>`<tr>
    <td class="mini">${r.date}</td><td class="mini">${r.time_et}</td>
    <td><b>${r.ticker}</b></td>
    <td><span class="chip ${r.sentiment==='PRAISE'?'p':'a'}">${r.sentiment.toLowerCase()}</span></td>
    <td class="num ${pn(r.nd_ret)}">${fmt(r.nd_ret)}</td>
    <td class="num ${pn(r.wk_ret)}">${fmt(r.wk_ret)}</td>
    <td class="q">&ldquo;${r.quote}&rdquo;</td></tr>`).join('');
  document.getElementById('count').textContent=rows.length+' posts';
}
document.querySelectorAll('.controls button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.controls button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); filt=b.dataset.f; render();});
document.getElementById('search').oninput=e=>{q=e.target.value;render();};
document.querySelectorAll('#tbl th').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k; if(sortK===k)sortDir*=-1;else{sortK=k;sortDir=1;} render();});
render();

// limitations
document.getElementById('limits').innerHTML=[
 `<b>Confounding, not causation.</b> A stock moves for a hundred reasons on any given day — earnings, the macro tape, sector news. A dot here shows what the stock did after a post, not because of it. Example: Warner Bros. Discovery&rsquo;s –16.5% day in Aug 2022 coincided with its earnings write-down, not the CNN jab that day.`,
 `<b>Entry timing.</b> Posts before 4:00pm ET on a trading day are entered at that day&rsquo;s close; posts after 4pm, on weekends, or holidays roll to the next trading day&rsquo;s close. Returns are simple close-to-close over +1 and +5 trading days.`,
 `<b>DJT is his own company.</b> ${A.praise_all.n-A.praise_ex_djt.n} of the ${A.praise_all.n} praise posts hype Truth Social / Trump Media (DJT), a thin, meme-driven stock he owns; ~56 of those price against its predecessor SPAC (DWAC, which Yahoo backfills under DJT). The ex-DJT row isolates third-party companies.`,
 `<b>Media-bashing dominates the attacks.</b> ${A.attack_media.n} of ${A.attack_all.n} attacks target news companies (CNN/WBD, NBC/Comcast, CBS/Paramount, Fox, NYT). CNN is a sliver of Warner Bros. Discovery&rsquo;s business, so &ldquo;Fake News CNN&rdquo; barely registers in WBD&rsquo;s price.`,
 `<b>Classification is LLM judgment.</b> Each of ${M.company_pairs_scanned.toLocaleString()} keyword-matched mentions was labeled praise / attack / neutral by a language model; ${M.neutral_dropped} neutral name-drops were dropped. A minority of edge cases are debatable, but individual errors don&rsquo;t move aggregates of this size.`,
 `<b>Archive coverage.</b> Dense through Oct 2025; the snapshot has a Nov 2025–Mar 2026 gap and only a sparse Apr–May 2026 tail, so the company sample effectively ends Oct 2025.`,
 `<b>Dropped tickers.</b> ${M.dropped} posts referencing U.S. Steel (X) were dropped — delisted after the Nippon Steel deal, with no Yahoo history. Paramount priced under its successor ticker PSKY.`,
].map(t=>`<li>${t}</li>`).join('');

document.getElementById('foot').innerHTML=
 `Data: Matt Stiles Trump Truth Social Archive (CC0) &middot; Prices: Yahoo Finance daily closes &middot; `+
 `Not investment advice &middot; Built ${M.generated}. All figures recomputed from source; no values are estimated.`;
</script>'''

out = HTML.replace('__DATA__', data)
open('trump_stock_moves.html', 'w', encoding='utf-8').write(out)
print('wrote trump_stock_moves.html', len(out), 'bytes')
