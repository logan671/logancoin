const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

// Auto font size based on title length
function fontSize(title) {
  const len = title.replace(/<br\/?>/g, '').length;
  if (len <= 12) return 44;
  if (len <= 20) return 38;
  return 32;
}

// YES/NO buttons component
function voteButtons(yesPct, noPct) {
  return `
    <div class="vote-area">
      <div class="vote-btn yes-btn">
        <span class="vote-label">YES</span>
        <span class="vote-pct">(${yesPct}%)</span>
      </div>
      <div class="vote-btn no-btn">
        <span class="vote-label">NO</span>
        <span class="vote-pct">(${noPct}%)</span>
      </div>
    </div>`;
}

// Shared styles
const baseCSS = `
  *{margin:0;padding:0;box-sizing:border-box}
  .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white}
  .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
  .title{font-weight:900;line-height:1.15;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}
  .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
  .vote-area{display:flex;gap:10px;margin-top:18px}
  .vote-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;
    width:100px;height:52px;border-radius:10px;cursor:pointer}
  .vote-label{font-size:16px;font-weight:800;letter-spacing:1px}
  .vote-pct{font-size:13px;font-weight:600;opacity:0.8;margin-top:1px}
  .yes-btn{background:rgba(34,197,94,0.85);border:2px solid rgba(34,197,94,1)}
  .no-btn{background:rgba(239,68,68,0.85);border:2px solid rgba(239,68,68,1)}
`;

const thumbnails = [
  // 1. KOSPI - Type B: full cover background
  {
    name: '1_kospi_v4',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:#0a1628}
      .bg{position:absolute;inset:0;background:url('${IMG}/kospi_chart_0.jpg') center/cover;opacity:0.4}
      .overlay{position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,22,40,0.85) 0%,rgba(10,22,40,0.4) 60%,rgba(10,22,40,0.3) 100%)}
      .title{font-size:${fontSize('2026년 1분기 코스피 5,500 넘길까?')}px;max-width:420px}
      .flag{position:absolute;right:20px;bottom:20px;width:50px;border-radius:3px;opacity:0.6;z-index:2}
    </style></head><body><div class="thumb">
      <div class="bg"></div>
      <div class="overlay"></div>
      <img class="logo" src="${LOGO}"/>
      <img class="flag" src="${IMG}/kospi_flag_0.png"/>
      <div class="content">
        <div class="title">2026년 1분기<br/>코스피 5,500 넘길까?</div>
        ${voteButtons(52, 48)}
      </div>
    </div></body></html>`
  },
  // 2. Culinary - Type B: full cover with logo background
  {
    name: '2_culinary_v4',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:#0a0a0a}
      .bg{position:absolute;inset:0;background:url('${IMG}/culinary_logo_0.png') center/contain no-repeat;opacity:0.2}
      .overlay{position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,10,10,0.9) 0%,rgba(10,10,10,0.5) 50%,rgba(10,10,10,0.3) 100%)}
      .title{font-size:${fontSize('흑백요리사 시즌2 White Spoon이 이길까?')}px;max-width:420px}
      .person{position:absolute;right:10px;bottom:0;height:105%;width:auto;z-index:1;
        mask-image:linear-gradient(to left,black 50%,transparent 95%);
        -webkit-mask-image:linear-gradient(to left,black 50%,transparent 95%)}
      .resolved{position:absolute;top:16px;left:36px;background:#22c55e;color:white;
        padding:4px 12px;border-radius:4px;font-size:11px;font-weight:700;z-index:5}
      .yes-btn{background:rgba(34,197,94,0.5);border:2px solid rgba(34,197,94,0.6)}
      .no-btn{background:rgba(100,100,100,0.4);border:2px solid rgba(100,100,100,0.5)}
    </style></head><body><div class="thumb">
      <div class="bg"></div>
      <div class="overlay"></div>
      <img class="logo" src="${LOGO}"/>
      <img class="person" src="${IMG}/culinary_person_0_nobg.png"/>
      <div class="resolved">RESOLVED</div>
      <div class="content" style="top:58%">
        <div class="title">흑백요리사 시즌2<br/>White Spoon이 이길까?</div>
        ${voteButtons(100, 0)}
      </div>
    </div></body></html>`
  },
  // 3. Relay - Type A: cutout right
  {
    name: '3_relay_v4',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#0a000f 0%,#1a0030 50%,#12001e 100%)}
      .title{font-size:${fontSize('Relay 런칭 하루 뒤 FDV $1B 넘길까?')}px;max-width:400px}
      .coin{position:absolute;right:100px;top:50%;transform:translateY(-50%);
        width:160px;height:160px;border-radius:50%;object-fit:contain;padding:25px;
        background:rgba(168,85,247,0.08);
        box-shadow:0 0 50px rgba(168,85,247,0.2),0 0 100px rgba(168,85,247,0.08);z-index:1}
      .grid{position:absolute;inset:0;
        background-image:linear-gradient(rgba(168,85,247,0.04) 1px,transparent 1px),
          linear-gradient(90deg,rgba(168,85,247,0.04) 1px,transparent 1px);
        background-size:30px 30px}
      .yes-btn{background:rgba(168,85,247,0.7);border:2px solid rgba(168,85,247,0.9)}
      .no-btn{background:rgba(80,40,120,0.5);border:2px solid rgba(80,40,120,0.7)}
    </style></head><body><div class="thumb">
      <div class="grid"></div>
      <img class="logo" src="${LOGO}"/>
      <img class="coin" src="${IMG}/relay_coin_0.png"/>
      <div class="content">
        <div class="title">Relay 런칭 하루 뒤<br/>FDV $1B 넘길까?</div>
        ${voteButtons(41, 59)}
      </div>
    </div></body></html>`
  },
  // 4. Hottest year - Type B: full cover (like sample 1)
  {
    name: '4_hottest_v4',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:#1a0000}
      .bg{position:absolute;inset:0;background:url('${IMG}/hottest_earth_0.jpg') center/cover;opacity:0.5}
      .overlay{position:absolute;inset:0;
        background:linear-gradient(90deg,rgba(20,0,0,0.85) 0%,rgba(20,0,0,0.4) 50%,rgba(20,0,0,0.2) 100%)}
      .title{font-size:${fontSize('2026년이 역대 가장 더운 해일까?')}px;max-width:430px}
      .yes-btn{background:rgba(239,68,68,0.8);border:2px solid rgba(239,68,68,1)}
      .no-btn{background:rgba(59,130,246,0.6);border:2px solid rgba(59,130,246,0.8)}
    </style></head><body><div class="thumb">
      <div class="bg"></div>
      <div class="overlay"></div>
      <img class="logo" src="${LOGO}"/>
      <div class="content">
        <div class="title">2026년이 역대<br/>가장 더운 해일까?</div>
        ${voteButtons(68, 32)}
      </div>
    </div></body></html>`
  },
  // 5. Bad Bunny - Type A: cutout right (like sample 2)
  {
    name: '5_badbunny_v4',
    html: `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      ${baseCSS}
      .thumb{background:linear-gradient(135deg,#000814 0%,#001d3d 40%,#002244 100%)}
      .title{font-size:${fontSize('배드버니 하프타임쇼 조회수 1.25억 넘길까?')}px;max-width:430px}
      .person{position:absolute;right:0;bottom:0;height:110%;width:auto;z-index:1;
        mask-image:linear-gradient(to left,black 50%,transparent 95%);
        -webkit-mask-image:linear-gradient(to left,black 50%,transparent 95%)}
      .dots{position:absolute;inset:0;
        background-image:radial-gradient(rgba(6,182,212,0.08) 1px,transparent 1px);
        background-size:16px 16px}
      .yes-btn{background:rgba(6,182,212,0.7);border:2px solid rgba(6,182,212,0.9)}
      .no-btn{background:rgba(30,58,95,0.7);border:2px solid rgba(30,58,95,0.9)}
    </style></head><body><div class="thumb">
      <div class="dots"></div>
      <img class="logo" src="${LOGO}"/>
      <img class="person" src="${IMG}/badbunny_portrait_0_nobg.png"/>
      <div class="content">
        <div class="title">배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?</div>
        ${voteButtons(58, 42)}
      </div>
    </div></body></html>`
  }
];

async function renderAll() {
  console.log('Browser launching...');
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 864, height: 280 });

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
