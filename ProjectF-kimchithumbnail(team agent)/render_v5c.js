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

async function extractDominantColor(imgPath) {
  const { data, info } = await sharp(imgPath)
    .resize(100, 60, { fit: 'cover' })
    .raw()
    .toBuffer({ resolveWithObject: true });
  let rSum = 0, gSum = 0, bSum = 0, count = 0;
  for (let y = 0; y < info.height; y++) {
    for (let x = 0; x < Math.floor(info.width / 2); x++) {
      const idx = (y * info.width + x) * info.channels;
      rSum += data[idx]; gSum += data[idx + 1]; bSum += data[idx + 2]; count++;
    }
  }
  return [Math.round(rSum / count), Math.round(gSum / count), Math.round(bSum / count)];
}

function hexToRgb(hex) {
  hex = hex.replace('#', '');
  return [parseInt(hex.slice(0,2),16), parseInt(hex.slice(2,4),16), parseInt(hex.slice(4,6),16)];
}

function generateVoteColors(bgRgb) {
  const [h, s, l] = rgbToHsl(...bgRgb);
  const yesHue = (h + 150) % 360;
  const yesRgb = hslToRgb(yesHue, Math.min(s + 0.3, 0.7), 0.5);
  const noRgb = hslToRgb(h, Math.min(s + 0.1, 0.4), Math.max(l + 0.15, 0.35));
  return {
    yes: { r: yesRgb[0], g: yesRgb[1], b: yesRgb[2] },
    no:  { r: noRgb[0],  g: noRgb[1],  b: noRgb[2] },
  };
}

function fontSize(title) {
  const len = title.replace(/<br\/?>/g, '').length;
  if (len <= 12) return 44;
  if (len <= 20) return 38;
  return 32;
}

// ── 5개 주제 (스마트 검색 이미지 적용) ──

const thumbnails = [
  {
    name: 'v5c_1_kospi',
    title: '2026년 1분기<br/>코스피 5,500 넘길까?',
    yes: 52, no: 48,
    bgType: 'image', bgImage: 'kospi_smart.jpg', bgBase: '#0a1628',
    overlayCSS: `background:linear-gradient(90deg,rgba(10,22,40,0.9) 0%,rgba(10,22,40,0.5) 50%,rgba(10,22,40,0.2) 100%)`,
  },
  {
    name: 'v5c_2_culinary',
    title: '흑백요리사 시즌2<br/>White Spoon이 이길까?',
    yes: 100, no: 0,
    bgType: 'image', bgImage: 'culinary_smart.jpg', bgBase: '#0a0a0a',
    overlayCSS: `background:linear-gradient(90deg,rgba(5,5,5,0.92) 0%,rgba(5,5,5,0.5) 50%,rgba(5,5,5,0.15) 100%)`,
  },
  {
    name: 'v5c_3_relay',
    title: 'Relay 런칭 하루 뒤<br/>FDV $1B 넘길까?',
    yes: 41, no: 59,
    bgType: 'image', bgImage: 'relay_smart.jpg', bgBase: '#0a0a2a',
    overlayCSS: `background:linear-gradient(90deg,rgba(10,10,30,0.92) 0%,rgba(10,10,30,0.5) 50%,rgba(10,10,30,0.15) 100%)`,
  },
  {
    name: 'v5c_4_hottest',
    title: '2026년이 역대<br/>가장 더운 해일까?',
    yes: 68, no: 32,
    bgType: 'image', bgImage: 'hottest_smart.jpg', bgBase: '#1a2030',
    overlayCSS: `background:linear-gradient(90deg,rgba(15,20,35,0.9) 0%,rgba(15,20,35,0.45) 50%,rgba(15,20,35,0.15) 100%)`,
  },
  {
    name: 'v5c_5_badbunny',
    title: '배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?',
    yes: 58, no: 42,
    bgType: 'image', bgImage: 'badbunny_smart.jpg', bgBase: '#0a1008',
    overlayCSS: `background:linear-gradient(90deg,rgba(8,12,6,0.92) 0%,rgba(8,12,6,0.5) 50%,rgba(8,12,6,0.15) 100%)`,
  },
];

// ── HTML 빌더 ──

function buildHTML(t, colors) {
  const yesWin = t.yes >= t.no;
  const btnW = 105, btnH = 58;
  const yc = colors.yes, nc = colors.no;
  const fs = fontSize(t.title);

  const yesOpacity = yesWin ? 0.8 : 0.25;
  const yesBorder  = yesWin ? 0.95 : 0.35;
  const yesFont    = yesWin ? 'rgba(255,255,255,1)' : 'rgba(255,255,255,0.5)';
  const noOpacity  = !yesWin ? 0.75 : 0.25;
  const noBorder   = !yesWin ? 0.9  : 0.35;
  const noFont     = !yesWin ? 'rgba(255,255,255,1)' : 'rgba(255,255,255,0.5)';

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white;
      background:${t.bgBase}}
    .bg{position:absolute;inset:0;background:url('${IMG}/${t.bgImage}') center/cover;opacity:0.55}
    .overlay{position:absolute;inset:0;${t.overlayCSS}}
    .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
    .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}

    /* 제목 외곽선 */
    .title{
      font-size:${fs}px;font-weight:900;line-height:1.15;max-width:430px;
      -webkit-text-stroke:1px rgba(0,0,0,0.3);
      text-shadow:
        0 0 8px rgba(0,0,0,0.8),
        0 2px 4px rgba(0,0,0,0.6),
        0 0 20px rgba(0,0,0,0.4);
    }

    /* 감싸는 박스 - 외곽선 강화 */
    .vote-wrapper{
      display:inline-flex;gap:8px;margin-top:18px;
      background:rgba(0,0,0,0.35);
      border:1.5px solid rgba(255,255,255,0.2);
      border-radius:14px;padding:8px 10px;
      backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
      box-shadow:0 2px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
    }

    /* 버튼 공통 - 외곽선 처리 */
    .vote-btn{
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      width:${btnW}px;height:${btnH}px;border-radius:10px;
      box-shadow:0 2px 8px rgba(0,0,0,0.3);
    }
    .vote-label{
      font-size:16px;font-weight:800;letter-spacing:1px;
      -webkit-text-stroke:0.5px rgba(0,0,0,0.2);
      text-shadow:0 1px 3px rgba(0,0,0,0.5);
    }
    .vote-pct{
      font-size:13px;font-weight:600;margin-top:2px;
      text-shadow:0 1px 2px rgba(0,0,0,0.4);
    }

    .yes-btn{
      background:rgba(${yc.r},${yc.g},${yc.b},${yesOpacity});
      border:2px solid rgba(${yc.r},${yc.g},${yc.b},${yesBorder});
      color:${yesFont};
      ${yesWin ? `box-shadow:0 2px 8px rgba(0,0,0,0.3), 0 0 12px rgba(${yc.r},${yc.g},${yc.b},0.25);` : ''}
    }
    .no-btn{
      background:rgba(${nc.r},${nc.g},${nc.b},${noOpacity});
      border:2px solid rgba(${nc.r},${nc.g},${nc.b},${noBorder});
      color:${noFont};
      ${!yesWin ? `box-shadow:0 2px 8px rgba(0,0,0,0.3), 0 0 12px rgba(${nc.r},${nc.g},${nc.b},0.25);` : ''}
    }
  </style></head><body><div class="thumb">
    <div class="bg"></div>
    <div class="overlay"></div>
    <img class="logo" src="${LOGO}"/>
    <div class="content">
      <div class="title">${t.title}</div>
      <div class="vote-wrapper">
        <div class="vote-btn yes-btn">
          <span class="vote-label">YES</span>
          <span class="vote-pct">(${t.yes}%)</span>
        </div>
        <div class="vote-btn no-btn">
          <span class="vote-label">NO</span>
          <span class="vote-pct">(${t.no}%)</span>
        </div>
      </div>
    </div>
  </div></body></html>`;
}

async function renderAll() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 864, height: 280, deviceScaleFactor: 2 });

  for (const t of thumbnails) {
    const bgRgb = await extractDominantColor(path.join(__dirname, IMG, t.bgImage));
    const colors = generateVoteColors(bgRgb);
    console.log(`${t.name}: bg(${bgRgb}) → YES(${colors.yes.r},${colors.yes.g},${colors.yes.b}) NO(${colors.no.r},${colors.no.g},${colors.no.b})`);

    const html = buildHTML(t, colors);
    const htmlPath = path.join(__dirname, `thumb_${t.name}.html`);
    const pngPath = path.join(__dirname, `thumb_${t.name}.png`);
    fs.writeFileSync(htmlPath, html);
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 300));
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`  Done!\n`);
  }

  await browser.close();
  console.log('All V5c rendered!');
}

renderAll().catch(console.error);
