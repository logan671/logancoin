const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const thumbnails = [
  {
    name: '1_kospi',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#0a1628 0%,#0d2137 40%,#132d46 100%);
        font-family:Arial,sans-serif;color:white}
      .grid{position:absolute;inset:0;
        background-image:linear-gradient(rgba(0,200,255,0.05) 1px,transparent 1px),
          linear-gradient(90deg,rgba(0,200,255,0.05) 1px,transparent 1px);
        background-size:40px 40px}
      .chart{position:absolute;right:40px;bottom:30px;width:550px;height:280px}
      .chart svg{width:100%;height:100%}
      .tag{display:inline-block;background:#0ea5e9;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .title{font-size:44px;font-weight:900;line-height:1.2;max-width:520px}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.6)}
      .prices{margin-top:20px;display:flex;gap:12px;flex-wrap:wrap;max-width:500px}
      .chip{padding:8px 16px;border-radius:20px;font-size:14px;font-weight:700}
      .chip.hot{background:rgba(34,197,94,0.2);border:1px solid #22c55e;color:#22c55e}
      .chip.mid{background:rgba(234,179,8,0.2);border:1px solid #eab308;color:#eab308}
      .chip.cold{background:rgba(100,116,139,0.2);border:1px solid #64748b;color:#94a3b8}
      .glow{position:absolute;width:300px;height:300px;border-radius:50%;
        background:radial-gradient(circle,rgba(14,165,233,0.15),transparent 70%);
        right:200px;top:-50px}
    </style></head><body><div class="thumb"><div class="grid"></div><div class="glow"></div>
      <div class="content">
        <div class="tag">ECONOMY</div>
        <div class="title">2026년 1분기<br/>코스피 마감은?</div>
        <div class="sub">Polymarket 실시간 예측</div>
        <div class="prices">
          <div class="chip hot">5500↑ 52%</div>
          <div class="chip hot">5300↑ 100%</div>
          <div class="chip mid">5000↑ 50%</div>
          <div class="chip cold">4500↓ 44%</div>
        </div>
      </div>
      <div class="chart"><svg viewBox="0 0 550 280">
        <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0ea5e9" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="#0ea5e9" stop-opacity="0"/>
        </linearGradient></defs>
        <polyline fill="url(#g1)" stroke="none" points="0,200 50,180 100,160 150,170 200,120 250,100 300,110 350,80 400,90 450,60 500,70 550,50 550,280 0,280"/>
        <polyline fill="none" stroke="#0ea5e9" stroke-width="3" points="0,200 50,180 100,160 150,170 200,120 250,100 300,110 350,80 400,90 450,60 500,70 550,50"/>
        <circle cx="550" cy="50" r="5" fill="#0ea5e9"/>
        <text x="500" y="42" fill="rgba(255,255,255,0.5)" font-size="12">5,500</text>
        <line x1="0" y1="200" x2="550" y2="200" stroke="rgba(255,255,255,0.1)" stroke-dasharray="4"/>
        <text x="0" y="215" fill="rgba(255,255,255,0.3)" font-size="11">4,500</text>
      </svg></div>
    </div></body></html>`
  },
  {
    name: '2_culinary_class_wars',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#1a0a00 0%,#2d1a0a 40%,#3d2415 100%);
        font-family:Arial,sans-serif;color:white}
      .tag{display:inline-block;background:#f59e0b;color:#1a0a00;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .title{font-size:44px;font-weight:900;line-height:1.2}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.6)}
      .result-box{margin-top:24px;background:rgba(245,158,11,0.15);border:2px solid #f59e0b;
        border-radius:12px;padding:20px 28px;display:inline-block}
      .result-label{font-size:13px;color:#f59e0b;letter-spacing:1px;font-weight:700}
      .result-value{font-size:36px;font-weight:900;margin-top:4px;color:#fbbf24}
      .spoons{position:absolute;right:60px;top:50%;transform:translateY(-50%);
        display:flex;gap:30px;align-items:center;z-index:2}
      .spoon{text-align:center}
      .spoon-icon{font-size:80px;margin-bottom:8px}
      .spoon-label{font-size:16px;font-weight:700;padding:6px 20px;border-radius:20px}
      .white-bg{background:rgba(255,255,255,0.15);color:white;border:2px solid white}
      .black-bg{background:rgba(100,100,100,0.15);color:#666;border:2px solid #666;text-decoration:line-through}
      .vs{font-size:32px;font-weight:900;color:rgba(255,255,255,0.3)}
      .resolved{position:absolute;top:20px;right:20px;background:#22c55e;color:white;
        padding:6px 14px;border-radius:4px;font-size:12px;font-weight:700}
      .flame1{position:absolute;right:350px;bottom:0;font-size:120px;opacity:0.08}
      .flame2{position:absolute;right:150px;bottom:-20px;font-size:160px;opacity:0.06}
    </style></head><body><div class="thumb">
      <div class="flame1">🔥</div><div class="flame2">🍳</div>
      <div class="resolved">RESOLVED</div>
      <div class="content">
        <div class="tag">ENTERTAINMENT</div>
        <div class="title">흑백요리사<br/>시즌2 승자는?</div>
        <div class="sub">Culinary Class Wars Season 2</div>
        <div class="result-box">
          <div class="result-label">WINNER</div>
          <div class="result-value">🥄 White Spoon 승리!</div>
        </div>
      </div>
      <div class="spoons">
        <div class="spoon">
          <div class="spoon-icon">🥄</div>
          <div class="spoon-label white-bg">White 100%</div>
        </div>
        <div class="vs">VS</div>
        <div class="spoon">
          <div class="spoon-icon" style="opacity:0.4">🥄</div>
          <div class="spoon-label black-bg">Black 0%</div>
        </div>
      </div>
    </div></body></html>`
  },
  {
    name: '3_relay_fdv',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#0a000f 0%,#1a0030 40%,#0f0025 100%);
        font-family:Arial,sans-serif;color:white}
      .tag{display:inline-block;background:#a855f7;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .title{font-size:44px;font-weight:900;line-height:1.2}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.5)}
      .bars{position:absolute;right:50px;top:50%;transform:translateY(-50%);
        display:flex;flex-direction:column;gap:8px;z-index:2;width:500px}
      .bar-row{display:flex;align-items:center;gap:10px}
      .bar-label{width:60px;text-align:right;font-size:14px;font-weight:700;color:rgba(255,255,255,0.7)}
      .bar-track{flex:1;height:28px;background:rgba(168,85,247,0.1);border-radius:14px;overflow:hidden;position:relative}
      .bar-fill{height:100%;border-radius:14px;display:flex;align-items:center;padding-left:12px;
        font-size:12px;font-weight:700}
      .purple{background:linear-gradient(90deg,#a855f7,#7c3aed)}
      .dim{background:linear-gradient(90deg,rgba(168,85,247,0.4),rgba(124,58,237,0.3))}
      .bar-pct{margin-left:auto;margin-right:10px;font-size:13px}
      .orb{position:absolute;width:400px;height:400px;border-radius:50%;
        background:radial-gradient(circle,rgba(168,85,247,0.1),transparent 70%);
        right:-100px;top:-100px}
      .orb2{position:absolute;width:200px;height:200px;border-radius:50%;
        background:radial-gradient(circle,rgba(124,58,237,0.08),transparent 70%);
        left:300px;bottom:-50px}
    </style></head><body><div class="thumb"><div class="orb"></div><div class="orb2"></div>
      <div class="content">
        <div class="tag">CRYPTO</div>
        <div class="title">Relay 런칭<br/>하루 뒤 FDV는?</div>
        <div class="sub">런칭 D+1 시가총액 예측</div>
      </div>
      <div class="bars">
        <div class="bar-row"><div class="bar-label">$100M</div><div class="bar-track"><div class="bar-fill purple" style="width:52.5%"><span class="bar-pct">52.5%</span></div></div></div>
        <div class="bar-row"><div class="bar-label">$300M</div><div class="bar-track"><div class="bar-fill purple" style="width:38.5%"><span class="bar-pct">38.5%</span></div></div></div>
        <div class="bar-row"><div class="bar-label">$500M</div><div class="bar-track"><div class="bar-fill dim" style="width:30%"><span class="bar-pct">30%</span></div></div></div>
        <div class="bar-row"><div class="bar-label">$1B</div><div class="bar-track"><div class="bar-fill dim" style="width:41%"><span class="bar-pct">41%</span></div></div></div>
        <div class="bar-row"><div class="bar-label">$1.2B</div><div class="bar-track"><div class="bar-fill dim" style="width:43%"><span class="bar-pct">43%</span></div></div></div>
        <div class="bar-row"><div class="bar-label">$1.5B</div><div class="bar-track"><div class="bar-fill dim" style="width:9.5%"><span class="bar-pct">9.5%</span></div></div></div>
      </div>
    </div></body></html>`
  },
  {
    name: '4_hottest_year',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#1a0000 0%,#3d0a00 30%,#5c1a00 60%,#2d0a00 100%);
        font-family:Arial,sans-serif;color:white}
      .tag{display:inline-block;background:#ef4444;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .title{font-size:44px;font-weight:900;line-height:1.2;max-width:550px}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.5)}
      .gauge{position:absolute;right:100px;top:50%;transform:translateY(-50%);z-index:2;text-align:center}
      .gauge-circle{width:220px;height:220px;border-radius:50%;position:relative;
        background:conic-gradient(#ef4444 0% 67.5%,rgba(255,255,255,0.1) 67.5% 100%)}
      .gauge-inner{position:absolute;inset:16px;border-radius:50%;
        background:linear-gradient(135deg,#2d0a00,#1a0000);
        display:flex;flex-direction:column;align-items:center;justify-content:center}
      .gauge-pct{font-size:52px;font-weight:900;color:#ef4444}
      .gauge-label{font-size:14px;color:rgba(255,255,255,0.5);margin-top:2px}
      .heat-bar{margin-top:24px;width:400px}
      .heat-track{height:12px;border-radius:6px;
        background:linear-gradient(90deg,#3b82f6,#22c55e,#eab308,#f97316,#ef4444);position:relative}
      .heat-marker{position:absolute;top:-4px;left:67.5%;width:4px;height:20px;
        background:white;border-radius:2px;transform:translateX(-50%)}
      .heat-labels{display:flex;justify-content:space-between;margin-top:6px;font-size:11px;color:rgba(255,255,255,0.4)}
      .heatglow{position:absolute;width:500px;height:500px;border-radius:50%;
        background:radial-gradient(circle,rgba(239,68,68,0.12),transparent 60%);
        right:-100px;bottom:-200px}
    </style></head><body><div class="thumb"><div class="heatglow"></div>
      <div class="content">
        <div class="tag">CLIMATE</div>
        <div class="title">2026년이 역대<br/>가장 더운 해일까?</div>
        <div class="sub">역대 최고 기온 기록 갱신 여부</div>
        <div class="heat-bar">
          <div class="heat-track"><div class="heat-marker"></div></div>
          <div class="heat-labels"><span>Cool</span><span>Record Hot</span></div>
        </div>
      </div>
      <div class="gauge">
        <div class="gauge-circle"><div class="gauge-inner">
          <div class="gauge-pct">67.5%</div>
          <div class="gauge-label">YES</div>
        </div></div>
      </div>
    </div></body></html>`
  },
  {
    name: '5_bad_bunny',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#000814 0%,#001d3d 40%,#003566 100%);
        font-family:Arial,sans-serif;color:white}
      .tag{display:inline-block;background:#06b6d4;color:#000814;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .title{font-size:40px;font-weight:900;line-height:1.2;max-width:500px}
      .sub{margin-top:10px;font-size:16px;color:rgba(255,255,255,0.5)}
      .views{position:absolute;right:50px;top:50%;transform:translateY(-50%);z-index:2;width:520px}
      .view-row{display:flex;align-items:center;gap:10px;margin-bottom:6px}
      .view-label{width:110px;text-align:right;font-size:13px;color:rgba(255,255,255,0.6);font-weight:600}
      .view-track{flex:1;height:32px;background:rgba(6,182,212,0.08);border-radius:8px;overflow:hidden;position:relative}
      .view-fill{height:100%;border-radius:8px;display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-size:13px;font-weight:700}
      .cyan{background:linear-gradient(90deg,#06b6d4,#0891b2)}
      .cyan-hot{background:linear-gradient(90deg,#06b6d4,#0ea5e9);box-shadow:0 0 20px rgba(6,182,212,0.3)}
      .cyan-dim{background:linear-gradient(90deg,rgba(6,182,212,0.4),rgba(8,145,178,0.3))}
      .hot-tag{background:#f59e0b;color:#000;padding:2px 8px;border-radius:4px;font-size:10px;margin-left:8px}
      .sparkle{position:absolute;width:300px;height:300px;border-radius:50%;
        background:radial-gradient(circle,rgba(6,182,212,0.08),transparent 70%);left:350px;top:-100px}
    </style></head><body><div class="thumb"><div class="sparkle"></div>
      <div class="content">
        <div class="tag">ENTERTAINMENT</div>
        <div class="title">배드버니 하프타임쇼<br/>1주차 유튜브 조회수는?</div>
        <div class="sub">Super Bowl 2026 Halftime Show</div>
      </div>
      <div class="views">
        <div class="view-row"><div class="view-label">&lt;50M</div><div class="view-track"><div class="view-fill cyan-dim" style="width:5%">0.05%</div></div></div>
        <div class="view-row"><div class="view-label">50~75M</div><div class="view-track"><div class="view-fill cyan-dim" style="width:5%">0.95%</div></div></div>
        <div class="view-row"><div class="view-label">75~100M</div><div class="view-track"><div class="view-fill cyan" style="width:10%">5.4%</div></div></div>
        <div class="view-row"><div class="view-label">100~125M</div><div class="view-track"><div class="view-fill cyan-hot" style="width:60%">37%<span class="hot-tag">HOT</span></div></div></div>
        <div class="view-row"><div class="view-label">125~150M</div><div class="view-track"><div class="view-fill cyan-hot" style="width:65%">39.8%<span class="hot-tag">TOP</span></div></div></div>
        <div class="view-row"><div class="view-label">150M+</div><div class="view-track"><div class="view-fill cyan" style="width:30%">18%</div></div></div>
      </div>
    </div></body></html>`
  }
];

async function renderAll() {
  console.log('Browser launching...');
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 400 });

  for (const t of thumbnails) {
    const htmlPath = path.join(__dirname, `thumb_${t.name}.html`);
    const pngPath = path.join(__dirname, `thumb_${t.name}.png`);

    // Write HTML file
    fs.writeFileSync(htmlPath, t.html);

    // Render
    await page.goto(`file://${htmlPath}`, { waitUntil: 'load' });
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`Done: ${t.name}`);
  }

  await browser.close();
  console.log('All 5 thumbnails rendered!');
}

renderAll().catch(console.error);
