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

// 이미지에서 좌측 절반 대표색 추출
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

// hex → rgb
function hexToRgb(hex) {
  hex = hex.replace('#', '');
  return [parseInt(hex.slice(0,2),16), parseInt(hex.slice(2,4),16), parseInt(hex.slice(4,6),16)];
}

// 배경색 기반 YES/NO 자동 색상
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

// 자동 폰트 크기
function fontSize(title) {
  const len = title.replace(/<br\/?>/g, '').length;
  if (len <= 12) return 44;
  if (len <= 20) return 38;
  return 32;
}

// ── 5개 주제 정의 ──

const thumbnails = [
  {
    name: 'v5_1_kospi',
    title: '2026년 1분기<br/>코스피 5,500 넘길까?',
    yes: 52, no: 48,
    bgType: 'image',
    bgImage: 'kospi_chart_0.jpg',
    bgBase: '#0a1628',
    overlayCSS: `background:linear-gradient(90deg,rgba(10,22,40,0.88) 0%,rgba(10,22,40,0.4) 60%,rgba(10,22,40,0.3) 100%)`,
    personImg: null,
    extraHTML: `<img style="position:absolute;right:20px;bottom:20px;width:50px;border-radius:3px;opacity:0.6;z-index:2" src="${IMG}/kospi_flag_0.png"/>`,
    extraCSS: '',
  },
  {
    name: 'v5_2_culinary',
    title: '흑백요리사 시즌2<br/>White Spoon이 이길까?',
    yes: 100, no: 0,
    bgType: 'image',
    bgImage: 'culinary_logo_0.png',
    bgBase: '#0a0a0a',
    bgContain: true,
    overlayCSS: `background:linear-gradient(90deg,rgba(10,10,10,0.9) 0%,rgba(10,10,10,0.5) 50%,rgba(10,10,10,0.3) 100%)`,
    personImg: 'culinary_person_0_nobg.png',
    extraHTML: '',
    extraCSS: '',
  },
  {
    name: 'v5_3_relay',
    title: 'Relay 런칭 하루 뒤<br/>FDV $1B 넘길까?',
    yes: 41, no: 59,
    bgType: 'gradient',
    bgGradient: 'linear-gradient(135deg,#0a000f 0%,#1a0030 50%,#12001e 100%)',
    bgColorHex: '#1a0030',
    personImg: null,
    extraHTML: `<img style="position:absolute;right:100px;top:50%;transform:translateY(-50%);width:160px;height:160px;border-radius:50%;object-fit:contain;padding:25px;background:rgba(168,85,247,0.08);box-shadow:0 0 50px rgba(168,85,247,0.2),0 0 100px rgba(168,85,247,0.08);z-index:1" src="${IMG}/relay_coin_0.png"/>`,
    extraCSS: `.grid{position:absolute;inset:0;
      background-image:linear-gradient(rgba(168,85,247,0.04) 1px,transparent 1px),
        linear-gradient(90deg,rgba(168,85,247,0.04) 1px,transparent 1px);
      background-size:30px 30px}`,
    extraBgHTML: '<div class="grid"></div>',
  },
  {
    name: 'v5_4_hottest',
    title: '2026년이 역대<br/>가장 더운 해일까?',
    yes: 68, no: 32,
    bgType: 'image',
    bgImage: 'hottest_earth_alt_clean.jpeg',
    bgBase: '#1a0000',
    overlayCSS: `background:linear-gradient(90deg,rgba(20,0,0,0.85) 0%,rgba(20,0,0,0.4) 50%,rgba(20,0,0,0.2) 100%)`,
    personImg: null,
    extraHTML: '',
    extraCSS: '',
  },
  {
    name: 'v5_5_badbunny',
    title: '배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?',
    yes: 58, no: 42,
    bgType: 'gradient',
    bgGradient: 'linear-gradient(135deg,#000814 0%,#001d3d 40%,#002244 100%)',
    bgColorHex: '#001d3d',
    personImg: 'badbunny_portrait_0_nobg.png',
    extraHTML: '',
    extraCSS: `.dots{position:absolute;inset:0;
      background-image:radial-gradient(rgba(6,182,212,0.08) 1px,transparent 1px);
      background-size:16px 16px}`,
    extraBgHTML: '<div class="dots"></div>',
  },
];

// ── HTML 빌더 ──

function buildHTML(t, colors) {
  const yesWin = t.yes >= t.no;
  const bigW = 120, bigH = 62, smallW = 88, smallH = 62;
  const yc = colors.yes, nc = colors.no;
  const fs = fontSize(t.title);

  // 배경 CSS
  let bgCSS, bgHTML;
  if (t.bgType === 'image') {
    const cover = t.bgContain ? 'center/contain no-repeat' : 'center/cover';
    bgCSS = `.thumb{background:${t.bgBase}} .bg{position:absolute;inset:0;background:url('${IMG}/${t.bgImage}') ${cover};opacity:${t.bgContain ? 0.2 : 0.5}} .overlay{position:absolute;inset:0;${t.overlayCSS}}`;
    bgHTML = `<div class="bg"></div><div class="overlay"></div>`;
  } else {
    bgCSS = `.thumb{background:${t.bgGradient}}`;
    bgHTML = t.extraBgHTML || '';
  }

  // 인물 CSS
  const personCSS = t.personImg ? `.person{position:absolute;right:0;bottom:0;height:110%;width:auto;z-index:1;mask-image:linear-gradient(to left,black 50%,transparent 95%);-webkit-mask-image:linear-gradient(to left,black 50%,transparent 95%)}` : '';
  const personHTML = t.personImg ? `<img class="person" src="${IMG}/${t.personImg}"/>` : '';

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white}
    ${bgCSS}
    ${personCSS}
    ${t.extraCSS || ''}
    .logo{position:absolute;top:16px;right:20px;height:22px;width:auto;z-index:5;opacity:0.9}
    .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
    .title{font-size:${fs}px;font-weight:900;line-height:1.15;max-width:430px;text-shadow:2px 2px 12px rgba(0,0,0,0.7)}

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
  </style></head><body><div class="thumb">
    ${bgHTML}
    <img class="logo" src="${LOGO}"/>
    ${personHTML}
    ${t.extraHTML || ''}
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

// ── 렌더 ──

async function renderAll() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 864, height: 280, deviceScaleFactor: 2 });

  for (const t of thumbnails) {
    // 배경 색상 추출
    let bgRgb;
    if (t.bgType === 'image') {
      bgRgb = await extractDominantColor(path.join(__dirname, IMG, t.bgImage));
    } else {
      bgRgb = hexToRgb(t.bgColorHex);
    }
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
  console.log('All 5 V5 thumbnails rendered!');
}

renderAll().catch(console.error);
