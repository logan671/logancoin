const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';

const thumbnails = [
  {
    name: '1_kospi_v2',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#0a1628 0%,#0d2137 40%,#132d46 100%);
        font-family:Arial,sans-serif;color:white}
      .bg-chart{position:absolute;right:0;top:0;width:600px;height:100%;
        object-fit:cover;opacity:0.25;filter:brightness(0.8) contrast(1.2)}
      .bg-overlay{position:absolute;inset:0;
        background:linear-gradient(90deg,#0a1628 0%,#0a1628 35%,transparent 70%)}
      .flag{position:absolute;right:40px;top:30px;width:80px;height:auto;opacity:0.7;
        border-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,0.3)}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .tag{display:inline-block;background:#0ea5e9;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .title{font-size:46px;font-weight:900;line-height:1.2;max-width:520px}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.5)}
      .prices{margin-top:20px;display:flex;gap:12px;flex-wrap:wrap;max-width:500px}
      .chip{padding:8px 16px;border-radius:20px;font-size:14px;font-weight:700}
      .chip.hot{background:rgba(34,197,94,0.2);border:1px solid #22c55e;color:#22c55e}
      .chip.mid{background:rgba(234,179,8,0.2);border:1px solid #eab308;color:#eab308}
      .chip.cold{background:rgba(100,116,139,0.2);border:1px solid #64748b;color:#94a3b8}
    </style></head><body><div class="thumb">
      <img class="bg-chart" src="${IMG}/kospi_chart_0.jpg"/>
      <div class="bg-overlay"></div>
      <img class="flag" src="${IMG}/kospi_flag_0.png"/>
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
    </div></body></html>`
  },
  {
    name: '2_culinary_v2',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#1a0a00 0%,#2d1a0a 40%,#1a0f05 100%);
        font-family:Arial,sans-serif;color:white}
      .logo{position:absolute;right:60px;top:50%;transform:translateY(-50%);
        width:450px;height:auto;opacity:0.85}
      .person{position:absolute;right:80px;bottom:0;height:105%;width:auto;z-index:2;
        filter:drop-shadow(0 0 20px rgba(0,0,0,0.5))}
      .person-fade{position:absolute;right:250px;top:0;width:200px;height:100%;
        background:linear-gradient(90deg,#1a0a00,transparent);z-index:3}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:4}
      .tag{display:inline-block;background:#f59e0b;color:#1a0a00;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .title{font-size:46px;font-weight:900;line-height:1.2}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.5)}
      .result-box{margin-top:24px;background:rgba(245,158,11,0.15);border:2px solid #f59e0b;
        border-radius:12px;padding:16px 24px;display:inline-block}
      .result-label{font-size:12px;color:#f59e0b;letter-spacing:1px;font-weight:700}
      .result-value{font-size:28px;font-weight:900;margin-top:4px;color:#fbbf24}
      .resolved{position:absolute;top:20px;right:20px;background:#22c55e;color:white;
        padding:6px 14px;border-radius:4px;font-size:12px;font-weight:700;z-index:5}
    </style></head><body><div class="thumb">
      <img class="logo" src="${IMG}/culinary_logo_0.png"/>
      <div class="resolved">RESOLVED</div>
      <div class="content">
        <div class="tag">ENTERTAINMENT</div>
        <div class="title">흑백요리사<br/>시즌2 승자는?</div>
        <div class="sub">Culinary Class Wars Season 2</div>
        <div class="result-box">
          <div class="result-label">WINNER</div>
          <div class="result-value">White Spoon 승리!</div>
        </div>
      </div>
    </div></body></html>`
  },
  {
    name: '3_relay_v2',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#0a000f 0%,#1a0030 40%,#0f0025 100%);
        font-family:Arial,sans-serif;color:white}
      .coin-logo{position:absolute;left:420px;top:50%;transform:translateY(-50%);
        width:140px;height:140px;border-radius:50%;object-fit:contain;
        box-shadow:0 0 40px rgba(168,85,247,0.3),0 0 80px rgba(168,85,247,0.1);
        background:rgba(168,85,247,0.1);padding:20px}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .tag{display:inline-block;background:#a855f7;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .title{font-size:44px;font-weight:900;line-height:1.2}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.5)}
      .bars{position:absolute;right:50px;top:50%;transform:translateY(-50%);
        display:flex;flex-direction:column;gap:8px;z-index:2;width:460px}
      .bar-row{display:flex;align-items:center;gap:10px}
      .bar-label{width:55px;text-align:right;font-size:14px;font-weight:700;color:rgba(255,255,255,0.7)}
      .bar-track{flex:1;height:28px;background:rgba(168,85,247,0.1);border-radius:14px;overflow:hidden}
      .bar-fill{height:100%;border-radius:14px;display:flex;align-items:center;justify-content:flex-end;
        padding-right:10px;font-size:12px;font-weight:700}
      .purple{background:linear-gradient(90deg,#a855f7,#7c3aed)}
      .dim{background:linear-gradient(90deg,rgba(168,85,247,0.4),rgba(124,58,237,0.3))}
      .orb{position:absolute;width:400px;height:400px;border-radius:50%;
        background:radial-gradient(circle,rgba(168,85,247,0.08),transparent 70%);right:-100px;top:-100px}
    </style></head><body><div class="thumb"><div class="orb"></div>
      <img class="coin-logo" src="${IMG}/relay_coin_0.png"/>
      <div class="content">
        <div class="tag">CRYPTO</div>
        <div class="title">Relay 런칭<br/>D+1 FDV는?</div>
        <div class="sub">런칭 하루 뒤 시가총액 예측</div>
      </div>
      <div class="bars">
        <div class="bar-row"><div class="bar-label">$100M</div><div class="bar-track"><div class="bar-fill purple" style="width:52.5%">52.5%</div></div></div>
        <div class="bar-row"><div class="bar-label">$300M</div><div class="bar-track"><div class="bar-fill purple" style="width:38.5%">38.5%</div></div></div>
        <div class="bar-row"><div class="bar-label">$500M</div><div class="bar-track"><div class="bar-fill dim" style="width:30%">30%</div></div></div>
        <div class="bar-row"><div class="bar-label">$1B</div><div class="bar-track"><div class="bar-fill dim" style="width:41%">41%</div></div></div>
        <div class="bar-row"><div class="bar-label">$1.2B</div><div class="bar-track"><div class="bar-fill dim" style="width:43%">43%</div></div></div>
        <div class="bar-row"><div class="bar-label">$1.5B</div><div class="bar-track"><div class="bar-fill dim" style="width:9.5%">9.5%</div></div></div>
      </div>
    </div></body></html>`
  },
  {
    name: '4_hottest_v2',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#1a0000 0%,#3d0a00 30%,#2d0a00 100%);
        font-family:Arial,sans-serif;color:white}
      .earth{position:absolute;right:80px;top:50%;transform:translateY(-50%);
        height:320px;width:auto;opacity:0.85;
        filter:drop-shadow(0 0 30px rgba(239,68,68,0.4))}
      .earth-glow{position:absolute;right:100px;top:50%;transform:translateY(-50%);
        width:350px;height:350px;border-radius:50%;
        background:radial-gradient(circle,rgba(239,68,68,0.2),transparent 60%)}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:2}
      .tag{display:inline-block;background:#ef4444;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .title{font-size:44px;font-weight:900;line-height:1.2;max-width:550px}
      .sub{margin-top:10px;font-size:18px;color:rgba(255,255,255,0.5)}
      .gauge-row{margin-top:24px;display:flex;align-items:center;gap:20px}
      .pct{font-size:56px;font-weight:900;color:#ef4444}
      .pct-label{font-size:16px;color:rgba(255,255,255,0.5)}
      .heat-bar{margin-top:20px;width:400px}
      .heat-track{height:12px;border-radius:6px;
        background:linear-gradient(90deg,#3b82f6,#22c55e,#eab308,#f97316,#ef4444);position:relative}
      .heat-marker{position:absolute;top:-4px;left:67.5%;width:4px;height:20px;
        background:white;border-radius:2px;transform:translateX(-50%)}
      .heat-labels{display:flex;justify-content:space-between;margin-top:6px;font-size:11px;color:rgba(255,255,255,0.4)}
    </style></head><body><div class="thumb">
      <div class="earth-glow"></div>
      <img class="earth" src="${IMG}/hottest_earth_0_nobg.png"/>
      <div class="content">
        <div class="tag">CLIMATE</div>
        <div class="title">2026년이 역대<br/>가장 더운 해일까?</div>
        <div class="sub">역대 최고 기온 기록 갱신 여부</div>
        <div class="gauge-row">
          <div><div class="pct">67.5%</div><div class="pct-label">YES 예측</div></div>
        </div>
        <div class="heat-bar">
          <div class="heat-track"><div class="heat-marker"></div></div>
          <div class="heat-labels"><span>Cool</span><span>Record Hot</span></div>
        </div>
      </div>
    </div></body></html>`
  },
  {
    name: '5_badbunny_v2',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      .thumb{width:1200px;height:400px;position:relative;overflow:hidden;
        background:linear-gradient(135deg,#000814 0%,#001d3d 40%,#003566 100%);
        font-family:Arial,sans-serif;color:white}
      .person{position:absolute;right:-30px;bottom:0;height:115%;width:auto;z-index:2;
        filter:drop-shadow(0 0 30px rgba(6,182,212,0.3))}
      .person-fade{position:absolute;right:200px;top:0;width:300px;height:100%;
        background:linear-gradient(90deg,#001d3d,transparent);z-index:3}
      .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:4}
      .tag{display:inline-block;background:#06b6d4;color:#000814;padding:6px 16px;font-size:13px;
        font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
      .title{font-size:42px;font-weight:900;line-height:1.2;max-width:550px}
      .sub{margin-top:10px;font-size:16px;color:rgba(255,255,255,0.5)}
      .views{margin-top:20px;display:flex;flex-direction:column;gap:5px;max-width:450px}
      .view-row{display:flex;align-items:center;gap:8px}
      .view-label{width:90px;text-align:right;font-size:12px;color:rgba(255,255,255,0.6);font-weight:600}
      .view-track{flex:1;height:26px;background:rgba(6,182,212,0.08);border-radius:6px;overflow:hidden}
      .view-fill{height:100%;border-radius:6px;display:flex;align-items:center;justify-content:flex-end;
        padding-right:8px;font-size:11px;font-weight:700}
      .cyan{background:linear-gradient(90deg,#06b6d4,#0891b2)}
      .cyan-hot{background:linear-gradient(90deg,#06b6d4,#0ea5e9);box-shadow:0 0 15px rgba(6,182,212,0.3)}
      .cyan-dim{background:linear-gradient(90deg,rgba(6,182,212,0.3),rgba(8,145,178,0.2))}
      .hot-tag{background:#f59e0b;color:#000;padding:1px 6px;border-radius:3px;font-size:9px;margin-left:6px}
    </style></head><body><div class="thumb">
      <div class="person-fade"></div>
      <img class="person" src="${IMG}/badbunny_portrait_0_nobg.png"/>
      <div class="content">
        <div class="tag">ENTERTAINMENT</div>
        <div class="title">배드버니 하프타임쇼<br/>1주차 유튜브 조회수는?</div>
        <div class="sub">Super Bowl 2026 Halftime Show</div>
        <div class="views">
          <div class="view-row"><div class="view-label">75~100M</div><div class="view-track"><div class="view-fill cyan-dim" style="width:10%">5.4%</div></div></div>
          <div class="view-row"><div class="view-label">100~125M</div><div class="view-track"><div class="view-fill cyan-hot" style="width:58%">37%<span class="hot-tag">HOT</span></div></div></div>
          <div class="view-row"><div class="view-label">125~150M</div><div class="view-track"><div class="view-fill cyan-hot" style="width:63%">39.8%<span class="hot-tag">TOP</span></div></div></div>
          <div class="view-row"><div class="view-label">150M+</div><div class="view-track"><div class="view-fill cyan" style="width:28%">18%</div></div></div>
        </div>
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

    fs.writeFileSync(htmlPath, t.html);
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 500));
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`Done: ${t.name}`);
  }

  await browser.close();
  console.log('All 5 thumbnails rendered!');
}

renderAll().catch(console.error);
