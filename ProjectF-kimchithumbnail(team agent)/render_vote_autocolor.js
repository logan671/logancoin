const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

// ── 색상 유틸 ──

function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;
  if (max === min) { h = s = 0; }
  else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  return [h * 360, s, l];
}

function hslToRgb(h, s, l) {
  h /= 360;
  let r, g, b;
  if (s === 0) { r = g = b = l; }
  else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1; if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

// 배경 이미지에서 대표색 추출 (좌측 절반만 샘플링 - 버튼이 놓이는 영역)
async function extractDominantColor(imgPath) {
  const { data, info } = await sharp(imgPath)
    .resize(100, 60, { fit: 'cover' })
    .raw()
    .toBuffer({ resolveWithObject: true });

  // 좌측 절반 픽셀만 샘플링
  let rSum = 0, gSum = 0, bSum = 0, count = 0;
  for (let y = 0; y < info.height; y++) {
    for (let x = 0; x < Math.floor(info.width / 2); x++) {
      const idx = (y * info.width + x) * info.channels;
      rSum += data[idx];
      gSum += data[idx + 1];
      bSum += data[idx + 2];
      count++;
    }
  }
  return [Math.round(rSum / count), Math.round(gSum / count), Math.round(bSum / count)];
}

// 배경색 기반으로 YES/NO 버튼 색상 생성
function generateVoteColors(bgRgb) {
  const [h, s, l] = rgbToHsl(...bgRgb);

  // YES 색상: 배경 hue에서 보색 방향으로 살짝 이동 (+150도), 채도 높게
  const yesHue = (h + 150) % 360;
  const yesRgb = hslToRgb(yesHue, Math.min(s + 0.3, 0.7), 0.5);

  // NO 색상: 배경과 같은 색조인데 밝기만 조절 (배경에 묻히는 느낌)
  const noRgb = hslToRgb(h, Math.min(s + 0.1, 0.4), Math.max(l + 0.15, 0.35));

  return {
    yes: { r: yesRgb[0], g: yesRgb[1], b: yesRgb[2] },
    no:  { r: noRgb[0],  g: noRgb[1],  b: noRgb[2] },
  };
}

// ── 테스트 케이스 ──

const cases = [
  {
    name: 'auto_badbunny',
    yes: 58, no: 42,
    title: '배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?',
    personImg: 'badbunny_portrait_0_nobg.png',
    bgType: 'gradient', // 그라데이션 배경
    bgColor: '#000814,#001d3d,#002244',
  },
  {
    name: 'auto_hottest',
    yes: 68, no: 32,
    title: '2026년이 역대<br/>가장 더운 해일까?',
    personImg: null,
    bgType: 'image',
    bgImage: 'hottest_earth_alt_clean.jpeg',
  },
  {
    name: 'auto_hottest_nowin',
    yes: 35, no: 65,
    title: '2026년이 역대<br/>가장 더운 해일까?',
    personImg: null,
    bgType: 'image',
    bgImage: 'hottest_earth_alt_clean.jpeg',
  },
];

function buildHTML(c, colors) {
  const yesWin = c.yes >= c.no;
  const bigW = 120, bigH = 62, smallW = 88, smallH = 62;
  const yc = colors.yes, nc = colors.no;

  const bgCSS = c.bgType === 'image'
    ? `.thumb{background:#1a0000}
       .bg{position:absolute;inset:0;background:url('${IMG}/${c.bgImage}') center/cover;opacity:0.5}
       .overlay{position:absolute;inset:0;background:linear-gradient(90deg,rgba(20,0,0,0.85) 0%,rgba(20,0,0,0.4) 50%,rgba(20,0,0,0.2) 100%)}`
    : `.thumb{background:linear-gradient(135deg,${c.bgColor.split(',').join(' 0%,')} 100%)}`;

  const personCSS = c.personImg
    ? `.person{position:absolute;right:0;bottom:0;height:110%;width:auto;z-index:1;
        mask-image:linear-gradient(to left,black 50%,transparent 95%);
        -webkit-mask-image:linear-gradient(to left,black 50%,transparent 95%)}`
    : '';

  const personHTML = c.personImg
    ? `<img class="person" src="${IMG}/${c.personImg}"/>`
    : '';

  const bgHTML = c.bgType === 'image'
    ? `<div class="bg"></div><div class="overlay"></div>`
    : '';

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white}
    ${bgCSS}
    ${personCSS}
    .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
    .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
    .title{font-size:38px;font-weight:900;line-height:1.15;max-width:430px;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}

    .vote-wrapper{
      display:flex;gap:10px;margin-top:18px;
      background:rgba(255,255,255,0.10);
      border:1.5px solid rgba(255,255,255,0.15);
      border-radius:16px;padding:10px 12px;
      backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
      align-items:center;
    }
    .vote-btn{display:flex;flex-direction:column;align-items:center;justify-content:center}
    .vote-label{font-weight:800;letter-spacing:1px}
    .vote-pct{font-weight:600;opacity:0.85;margin-top:2px}

    .yes-btn{
      width:${yesWin ? bigW : smallW}px;height:${yesWin ? bigH : smallH}px;
      border-radius:${yesWin ? 10 : 8}px;
      background:rgba(${yc.r},${yc.g},${yc.b},${yesWin ? 0.75 : 0.3});
      border:2px solid rgba(${yc.r},${yc.g},${yc.b},${yesWin ? 0.95 : 0.4});
    }
    .yes-btn .vote-label{font-size:${yesWin ? 18 : 15}px}
    .yes-btn .vote-pct{font-size:${yesWin ? 14 : 12}px}

    .no-btn{
      width:${!yesWin ? bigW : smallW}px;height:${!yesWin ? bigH : smallH}px;
      border-radius:${!yesWin ? 10 : 8}px;
      background:rgba(${nc.r},${nc.g},${nc.b},${!yesWin ? 0.7 : 0.35});
      border:2px solid rgba(${nc.r},${nc.g},${nc.b},${!yesWin ? 0.9 : 0.45});
    }
    .no-btn .vote-label{font-size:${!yesWin ? 18 : 15}px}
    .no-btn .vote-pct{font-size:${!yesWin ? 14 : 12}px}

    .label{position:absolute;top:8px;left:36px;font-size:11px;color:rgba(255,255,255,0.5);z-index:6;letter-spacing:1px}
  </style></head><body><div class="thumb">
    ${bgHTML}
    <img class="logo" src="${LOGO}"/>
    ${personHTML}
    <div class="label">${c.name} — bg→YES(${yc.r},${yc.g},${yc.b}) NO(${nc.r},${nc.g},${nc.b})</div>
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
    // 배경 색상 추출
    let bgRgb;
    if (c.bgType === 'image') {
      bgRgb = await extractDominantColor(path.join(__dirname, IMG, c.bgImage));
      console.log(`  ${c.name} bg dominant: rgb(${bgRgb.join(',')})`);
    } else {
      // 그라데이션: 중간값 추정 (어두운 남색 계열)
      bgRgb = [0, 29, 61]; // #001d3d
    }

    const colors = generateVoteColors(bgRgb);
    console.log(`  YES color: rgb(${colors.yes.r},${colors.yes.g},${colors.yes.b})`);
    console.log(`  NO  color: rgb(${colors.no.r},${colors.no.g},${colors.no.b})`);

    const html = buildHTML(c, colors);
    const htmlPath = path.join(__dirname, `thumb_ac_${c.name}.html`);
    const pngPath = path.join(__dirname, `thumb_ac_${c.name}.png`);
    fs.writeFileSync(htmlPath, html);
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 300));
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`Done: ${c.name}\n`);
  }

  await browser.close();
  console.log('All auto-color done!');
}

renderAll().catch(console.error);
