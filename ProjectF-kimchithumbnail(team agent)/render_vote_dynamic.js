const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

// 테스트 케이스: YES 유리 / NO 유리 / 비슷
const cases = [
  { name: 'yes_dominant', yes: 72, no: 28, title: '배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?', img: 'badbunny_portrait_0_nobg.png' },
  { name: 'no_dominant',  yes: 31, no: 69, title: '배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?', img: 'badbunny_portrait_0_nobg.png' },
  { name: 'close_match',  yes: 52, no: 48, title: '배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?', img: 'badbunny_portrait_0_nobg.png' },
];

function buildHTML(c) {
  const yesWin = c.yes >= c.no;
  // 우세한 쪽: 큰 박스 + 강한 색, 열세한 쪽: 작은 박스 + 수수한 색
  const bigW = 120, bigH = 62, bigRadius = 10, bigLabel = 18, bigPct = 14;
  const smallW = 88, smallH = 62, smallRadius = 8, smallLabel = 15, smallPct = 12;

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white;
      background:linear-gradient(135deg,#000814 0%,#001d3d 40%,#002244 100%)}
    .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
    .person{position:absolute;right:0;bottom:0;height:110%;width:auto;z-index:1;
      mask-image:linear-gradient(to left,black 50%,transparent 95%);
      -webkit-mask-image:linear-gradient(to left,black 50%,transparent 95%)}

    .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
    .title{font-size:38px;font-weight:900;line-height:1.15;max-width:430px;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}

    .vote-wrapper{
      display:flex;gap:10px;margin-top:18px;
      background:rgba(255,255,255,0.10);
      border:1.5px solid rgba(255,255,255,0.15);
      border-radius:16px;
      padding:10px 12px;
      backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
      align-items:center;
    }
    .vote-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:8px}
    .vote-label{font-weight:800;letter-spacing:1px}
    .vote-pct{font-weight:600;opacity:0.85;margin-top:2px}

    /* YES 버튼 */
    .yes-btn{
      width:${yesWin ? bigW : smallW}px;height:${yesWin ? bigH : smallH}px;
      border-radius:${yesWin ? bigRadius : smallRadius}px;
      background:${yesWin ? 'rgba(6,182,212,0.75)' : 'rgba(6,182,212,0.3)'};
      border:2px solid ${yesWin ? 'rgba(6,182,212,0.95)' : 'rgba(6,182,212,0.4)'};
    }
    .yes-btn .vote-label{font-size:${yesWin ? bigLabel : smallLabel}px}
    .yes-btn .vote-pct{font-size:${yesWin ? bigPct : smallPct}px}

    /* NO 버튼 */
    .no-btn{
      width:${!yesWin ? bigW : smallW}px;height:${!yesWin ? bigH : smallH}px;
      border-radius:${!yesWin ? bigRadius : smallRadius}px;
      background:${!yesWin ? 'rgba(100,130,180,0.7)' : 'rgba(30,58,95,0.4)'};
      border:2px solid ${!yesWin ? 'rgba(100,130,180,0.9)' : 'rgba(30,58,95,0.5)'};
    }
    .no-btn .vote-label{font-size:${!yesWin ? bigLabel : smallLabel}px}
    .no-btn .vote-pct{font-size:${!yesWin ? bigPct : smallPct}px}

    .label{position:absolute;top:8px;left:36px;font-size:11px;color:rgba(255,255,255,0.5);z-index:6;letter-spacing:1px}
  </style></head><body><div class="thumb">
    <img class="logo" src="${LOGO}"/>
    <img class="person" src="${IMG}/${c.img}"/>
    <div class="label">YES ${c.yes}% vs NO ${c.no}% — ${yesWin ? 'YES 우세' : 'NO 우세'}</div>
    <div class="content">
      <div class="title">${c.title}</div>
      <div class="vote-wrapper">
        <div class="vote-btn yes-btn">
          <span class="vote-label">YES</span>
          <span class="vote-pct">(${c.yes}%)</span>
        </div>
        <div class="vote-btn no-btn">
          <span class="vote-label">NO</span>
          <span class="vote-pct">(${c.no}%)</span>
        </div>
      </div>
    </div>
  </div></body></html>`;
}

async function renderAll() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 864, height: 280, deviceScaleFactor: 2 });

  for (const c of cases) {
    const html = buildHTML(c);
    const htmlPath = path.join(__dirname, `thumb_dyn_${c.name}.html`);
    const pngPath = path.join(__dirname, `thumb_dyn_${c.name}.png`);
    fs.writeFileSync(htmlPath, html);
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 300));
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`Done: ${c.name} (YES ${c.yes}% / NO ${c.no}%)`);
  }

  await browser.close();
  console.log('All done!');
}

renderAll().catch(console.error);
