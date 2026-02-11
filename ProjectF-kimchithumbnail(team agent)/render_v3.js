const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';

// Shared vote bar component
function voteBar(yesLabel, noLabel, yesPct, noPct) {
  return `
    <div class="vote">
      <div class="vote-row">
        <div class="vote-yes" style="width:${yesPct}%">
          <span class="vote-text">${yesLabel}</span>
          <span class="vote-pct">${yesPct}%</span>
        </div>
        <div class="vote-no" style="width:${noPct}%">
          <span class="vote-pct">${noPct}%</span>
          <span class="vote-text">${noLabel}</span>
        </div>
      </div>
    </div>`;
}

// Shared base styles
const baseCSS = `
  *{margin:0;padding:0;box-sizing:border-box}
  .thumb{width:1200px;height:400px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white}
  .content{position:absolute;left:50px;top:50%;transform:translateY(-50%);z-index:4}
  .tag{display:inline-block;padding:6px 16px;font-size:13px;font-weight:700;border-radius:4px;letter-spacing:1px;margin-bottom:14px}
  .title{font-size:48px;font-weight:900;line-height:1.15;max-width:600px;text-shadow:2px 2px 12px rgba(0,0,0,0.6)}
  .vote{margin-top:28px;max-width:480px}
  .vote-row{display:flex;height:40px;border-radius:20px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.3)}
  .vote-yes{display:flex;align-items:center;justify-content:space-between;padding:0 16px;
    font-weight:700;font-size:15px;color:white}
  .vote-no{display:flex;align-items:center;justify-content:space-between;padding:0 16px;
    font-weight:700;font-size:15px;color:white}
  .vote-text{font-size:13px;opacity:0.9}
  .vote-pct{font-size:17px;font-weight:900}
`;

const thumbnails = [
  {
    name: '1_kospi_v3',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#0a1628 0%,#0d2137 40%,#132d46 100%)}
      .tag{background:#0ea5e9}
      .vote-yes{background:#22c55e}
      .vote-no{background:#ef4444}
      .bg-chart{position:absolute;right:0;top:0;width:55%;height:100%;object-fit:cover;opacity:0.3}
      .bg-overlay{position:absolute;inset:0;background:linear-gradient(90deg,#0a1628 40%,transparent 75%)}
      .flag{position:absolute;right:40px;top:30px;width:80px;border-radius:4px;opacity:0.8;
        box-shadow:0 2px 8px rgba(0,0,0,0.3);z-index:2}
    </style></head><body><div class="thumb">
      <img class="bg-chart" src="${IMG}/kospi_chart_0.jpg"/>
      <div class="bg-overlay"></div>
      <img class="flag" src="${IMG}/kospi_flag_0.png"/>
      <div class="content">
        <div class="tag">ECONOMY</div>
        <div class="title">2026년 1분기<br/>코스피 5,500 넘길까?</div>
        ${voteBar('YES', 'NO', 52, 48)}
      </div>
    </div></body></html>`
  },
  {
    name: '2_culinary_v3',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#1a0a00 0%,#2d1a0a 40%,#1a0f05 100%)}
      .tag{background:#f59e0b;color:#1a0a00}
      .vote-yes{background:#22c55e}
      .vote-no{background:#ef4444}
      .logo{position:absolute;right:30px;top:50%;transform:translateY(-50%);
        width:480px;opacity:0.9;z-index:1}
      .logo-overlay{position:absolute;inset:0;
        background:linear-gradient(90deg,#1a0a00 38%,transparent 65%);z-index:2}
      .resolved{position:absolute;top:20px;right:20px;background:#22c55e;color:white;
        padding:6px 14px;border-radius:4px;font-size:12px;font-weight:700;z-index:5}
    </style></head><body><div class="thumb">
      <img class="logo" src="${IMG}/culinary_logo_0.png"/>
      <div class="logo-overlay"></div>
      <div class="resolved">RESOLVED</div>
      <div class="content">
        <div class="tag">ENTERTAINMENT</div>
        <div class="title">흑백요리사 시즌2<br/>White Spoon이 이길까?</div>
        ${voteBar('YES', 'NO', 100, 0)}
      </div>
    </div></body></html>`
  },
  {
    name: '3_relay_v3',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#0a000f 0%,#1a0030 40%,#0f0025 100%)}
      .tag{background:#a855f7}
      .vote-yes{background:#a855f7}
      .vote-no{background:#4b2080}
      .coin{position:absolute;right:120px;top:50%;transform:translateY(-50%);
        width:200px;height:200px;border-radius:50%;object-fit:contain;padding:30px;
        background:rgba(168,85,247,0.1);
        box-shadow:0 0 60px rgba(168,85,247,0.25),0 0 120px rgba(168,85,247,0.1);z-index:1}
      .orb{position:absolute;right:50px;top:50%;transform:translateY(-50%);
        width:400px;height:400px;border-radius:50%;
        background:radial-gradient(circle,rgba(168,85,247,0.08),transparent 60%)}
    </style></head><body><div class="thumb">
      <div class="orb"></div>
      <img class="coin" src="${IMG}/relay_coin_0.png"/>
      <div class="content">
        <div class="tag">CRYPTO</div>
        <div class="title">Relay 런칭 하루 뒤<br/>FDV $1B 넘길까?</div>
        ${voteBar('YES', 'NO', 41, 59)}
      </div>
    </div></body></html>`
  },
  {
    name: '4_hottest_v3',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#1a0000 0%,#3d0a00 30%,#2d0a00 100%)}
      .tag{background:#ef4444}
      .vote-yes{background:#ef4444}
      .vote-no{background:#3b82f6}
      .earth{position:absolute;right:60px;top:50%;transform:translateY(-50%);
        height:340px;width:auto;z-index:1;
        filter:drop-shadow(0 0 40px rgba(239,68,68,0.4)) drop-shadow(0 0 80px rgba(239,68,68,0.2))}
    </style></head><body><div class="thumb">
      <img class="earth" src="${IMG}/hottest_earth_0_nobg.png"/>
      <div class="content">
        <div class="tag">CLIMATE</div>
        <div class="title">2026년이 역대<br/>가장 더운 해일까?</div>
        ${voteBar('YES', 'NO', 68, 32)}
      </div>
    </div></body></html>`
  },
  {
    name: '5_badbunny_v3',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#000814 0%,#001d3d 40%,#003566 100%)}
      .tag{background:#06b6d4;color:#000814}
      .vote-yes{background:#06b6d4}
      .vote-no{background:#1e3a5f}
      .person{position:absolute;right:0;bottom:0;height:100%;width:auto;z-index:1;
        object-fit:cover;object-position:top;
        mask-image:linear-gradient(to left,black 60%,transparent 100%);
        -webkit-mask-image:linear-gradient(to left,black 60%,transparent 100%)}
    </style></head><body><div class="thumb">
      <img class="person" src="${IMG}/badbunny_portrait_0_nobg.png"/>
      <div class="content">
        <div class="tag">ENTERTAINMENT</div>
        <div class="title">배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?</div>
        ${voteBar('YES', 'NO', 58, 42)}
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
  console.log('All done!');
}

renderAll().catch(console.error);
