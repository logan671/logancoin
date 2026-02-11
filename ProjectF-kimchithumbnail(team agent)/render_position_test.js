const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

const voteHTML = `
  <div class="vote-btn yes-btn">
    <span class="vote-label">YES</span>
    <span class="vote-pct">(68%)</span>
  </div>
  <div class="vote-btn no-btn">
    <span class="vote-label">NO</span>
    <span class="vote-pct">(32%)</span>
  </div>`;

const shared = `
  *{margin:0;padding:0;box-sizing:border-box}
  .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white}
  .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
  .title{font-size:38px;font-weight:900;line-height:1.15;max-width:430px;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}
  .thumb{background:#1a0000}
  .bg{position:absolute;inset:0;background:url('${IMG}/hottest_earth_alt_clean.jpeg') center/cover;opacity:0.5}
  .overlay{position:absolute;inset:0;background:linear-gradient(90deg,rgba(20,0,0,0.85) 0%,rgba(20,0,0,0.4) 50%,rgba(20,0,0,0.2) 100%)}
  .vote-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;width:100px;height:52px;border-radius:10px}
  .vote-label{font-size:16px;font-weight:800;letter-spacing:1px}
  .vote-pct{font-size:13px;font-weight:600;opacity:0.8;margin-top:1px}
  .yes-btn{background:rgba(239,68,68,0.8);border:2px solid rgba(239,68,68,1)}
  .no-btn{background:rgba(59,130,246,0.6);border:2px solid rgba(59,130,246,0.8)}
  .label{position:absolute;top:8px;left:36px;font-size:11px;color:rgba(255,255,255,0.5);z-index:6;letter-spacing:1px}
`;

const positions = [
  {
    name: 'pos_A_left_bottom',
    label: 'A: 좌측 하단',
    css: `
      .content{position:absolute;left:36px;top:32px;z-index:4}
      .vote-area{position:absolute;bottom:24px;left:36px;display:flex;gap:10px;z-index:5}
    `
  },
  {
    name: 'pos_B_below_title',
    label: 'B: 제목 바로 아래',
    css: `
      .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
      .vote-area{display:flex;gap:10px;margin-top:18px}
    `
  },
  {
    name: 'pos_C_right_bottom',
    label: 'C: 우측 하단',
    css: `
      .content{position:absolute;left:36px;top:32px;z-index:4}
      .vote-area{position:absolute;bottom:24px;right:24px;display:flex;gap:10px;z-index:5}
    `
  },
  {
    name: 'pos_D_center_bottom',
    label: 'D: 중앙 하단',
    css: `
      .content{position:absolute;left:36px;top:32px;z-index:4}
      .vote-area{position:absolute;bottom:24px;left:50%;transform:translateX(-50%);display:flex;gap:10px;z-index:5}
    `
  },
];

async function renderAll() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 864, height: 280, deviceScaleFactor: 2 });

  for (const p of positions) {
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${shared} ${p.css}
    </style></head><body><div class="thumb">
      <div class="bg"></div><div class="overlay"></div>
      <img class="logo" src="${LOGO}"/>
      <div class="label">${p.label}</div>
      <div class="content">
        <div class="title">2026년이 역대<br/>가장 더운 해일까?</div>
        ${p.name === 'pos_B_below_title' ? `<div class="vote-area">${voteHTML}</div>` : ''}
      </div>
      ${p.name !== 'pos_B_below_title' ? `<div class="vote-area">${voteHTML}</div>` : ''}
    </div></body></html>`;

    const htmlPath = path.join(__dirname, `thumb_${p.name}.html`);
    const pngPath = path.join(__dirname, `thumb_${p.name}.png`);
    fs.writeFileSync(htmlPath, html);
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 300));
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`Done: ${p.name}`);
  }

  await browser.close();
  console.log('All 4 positions rendered!');
}

renderAll().catch(console.error);
