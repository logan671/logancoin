const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

const voteHTML = `
  <div class="vote-btn yes-btn">
    <span class="vote-label">YES</span>
    <span class="vote-pct">(58%)</span>
  </div>
  <div class="vote-btn no-btn">
    <span class="vote-label">NO</span>
    <span class="vote-pct">(42%)</span>
  </div>`;

const shared = `
  *{margin:0;padding:0;box-sizing:border-box}
  .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white;
    background:linear-gradient(135deg,#000814 0%,#001d3d 40%,#002244 100%)}
  .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
  .title{font-size:38px;font-weight:900;line-height:1.15;max-width:430px;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}
  .person{position:absolute;right:0;bottom:0;height:110%;width:auto;z-index:1;
    mask-image:linear-gradient(to left,black 50%,transparent 95%);
    -webkit-mask-image:linear-gradient(to left,black 50%,transparent 95%)}
  .vote-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;width:100px;height:52px;border-radius:10px}
  .vote-label{font-size:16px;font-weight:800;letter-spacing:1px}
  .vote-pct{font-size:13px;font-weight:600;opacity:0.8;margin-top:1px}
  .yes-btn{background:rgba(6,182,212,0.7);border:2px solid rgba(6,182,212,0.9)}
  .no-btn{background:rgba(30,58,95,0.7);border:2px solid rgba(30,58,95,0.9)}
  .label{position:absolute;top:8px;left:36px;font-size:11px;color:rgba(255,255,255,0.5);z-index:6;letter-spacing:1px}
`;

const positions = [
  {
    name: 'bb_pos_A',
    label: 'A: 좌측 하단 고정',
    css: `.content{position:absolute;left:36px;top:32px;z-index:4}
          .vote-area{position:absolute;bottom:24px;left:36px;display:flex;gap:10px;z-index:5}`,
    voteInContent: false
  },
  {
    name: 'bb_pos_B',
    label: 'B: 제목 바로 아래',
    css: `.content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
          .vote-area{display:flex;gap:10px;margin-top:18px}`,
    voteInContent: true
  },
  {
    name: 'bb_pos_C',
    label: 'C: 우측 하단',
    css: `.content{position:absolute;left:36px;top:32px;z-index:4}
          .vote-area{position:absolute;bottom:24px;right:24px;display:flex;gap:10px;z-index:5}`,
    voteInContent: false
  },
  {
    name: 'bb_pos_D',
    label: 'D: 중앙 하단',
    css: `.content{position:absolute;left:36px;top:32px;z-index:4}
          .vote-area{position:absolute;bottom:24px;left:50%;transform:translateX(-50%);display:flex;gap:10px;z-index:5}`,
    voteInContent: false
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
      <img class="logo" src="${LOGO}"/>
      <img class="person" src="${IMG}/badbunny_portrait_0_nobg.png"/>
      <div class="label">${p.label}</div>
      <div class="content">
        <div class="title">배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?</div>
        ${p.voteInContent ? `<div class="vote-area">${voteHTML}</div>` : ''}
      </div>
      ${!p.voteInContent ? `<div class="vote-area">${voteHTML}</div>` : ''}
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
  console.log('All done!');
}

renderAll().catch(console.error);
