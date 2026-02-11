const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

const baseCSS = `
  *{margin:0;padding:0;box-sizing:border-box}
  .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white}
  .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
  .content{position:absolute;left:36px;top:36px;z-index:4}
  .title{font-weight:900;line-height:1.15;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}

  /* YES/NO fixed bottom-left */
  .vote-area{position:absolute;bottom:24px;left:36px;display:flex;gap:10px;z-index:5}
  .vote-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;
    width:100px;height:52px;border-radius:10px}
  .vote-label{font-size:16px;font-weight:800;letter-spacing:1px}
  .vote-pct{font-size:13px;font-weight:600;opacity:0.8;margin-top:1px}
`;

const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
  ${baseCSS}
  .thumb{background:#1a0000}
  .bg{position:absolute;inset:0;background:url('${IMG}/hottest_earth_alt_clean.jpeg') center/cover;opacity:0.5}
  .overlay{position:absolute;inset:0;
    background:linear-gradient(90deg,rgba(20,0,0,0.85) 0%,rgba(20,0,0,0.4) 50%,rgba(20,0,0,0.2) 100%)}
  .title{font-size:38px;max-width:430px}
  .yes-btn{background:rgba(239,68,68,0.8);border:2px solid rgba(239,68,68,1)}
  .no-btn{background:rgba(59,130,246,0.6);border:2px solid rgba(59,130,246,0.8)}
</style></head><body><div class="thumb">
  <div class="bg"></div>
  <div class="overlay"></div>
  <img class="logo" src="${LOGO}"/>
  <div class="content">
    <div class="title">2026년이 역대<br/>가장 더운 해일까?</div>
  </div>
  <div class="vote-area">
    <div class="vote-btn yes-btn">
      <span class="vote-label">YES</span>
      <span class="vote-pct">(68%)</span>
    </div>
    <div class="vote-btn no-btn">
      <span class="vote-label">NO</span>
      <span class="vote-pct">(32%)</span>
    </div>
  </div>
</div></body></html>`;

async function render() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  // 2x resolution: CSS stays 864x280 but output image is 1728x560
  await page.setViewport({ width: 864, height: 280, deviceScaleFactor: 2 });

  const htmlPath = path.join(__dirname, 'thumb_hd_test.html');
  const pngPath = path.join(__dirname, 'thumb_hd_test.png');
  fs.writeFileSync(htmlPath, html);
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: pngPath, type: 'png' });

  const stat = fs.statSync(pngPath);
  console.log(`Done! ${(stat.size/1024).toFixed(0)} KB (2x resolution: 1728x560)`);
  await browser.close();
}

render().catch(console.error);
