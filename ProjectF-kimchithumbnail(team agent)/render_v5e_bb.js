const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const IMG = './images';
const LOGO = './marketmotionlogo.webp';

function rgbToHsl(r,g,b){r/=255;g/=255;b/=255;const max=Math.max(r,g,b),min=Math.min(r,g,b);let h,s,l=(max+min)/2;if(max===min){h=s=0}else{const d=max-min;s=l>0.5?d/(2-max-min):d/(max+min);switch(max){case r:h=((g-b)/d+(g<b?6:0))/6;break;case g:h=((b-r)/d+2)/6;break;case b:h=((r-g)/d+4)/6;break}}return[h*360,s,l]}
function hslToRgb(h,s,l){h/=360;let r,g,b;if(s===0){r=g=b=l}else{const hue2rgb=(p,q,t)=>{if(t<0)t+=1;if(t>1)t-=1;if(t<1/6)return p+(q-p)*6*t;if(t<1/2)return q;if(t<2/3)return p+(q-p)*(2/3-t)*6;return p};const q=l<0.5?l*(1+s):l+s-l*s;const p=2*l-q;r=hue2rgb(p,q,h+1/3);g=hue2rgb(p,q,h);b=hue2rgb(p,q,h-1/3)}return[Math.round(r*255),Math.round(g*255),Math.round(b*255)]}
async function extractDominantColor(imgPath){const{data,info}=await sharp(imgPath).resize(100,60,{fit:'cover'}).raw().toBuffer({resolveWithObject:true});let rS=0,gS=0,bS=0,c=0;for(let y=0;y<info.height;y++)for(let x=0;x<Math.floor(info.width/2);x++){const i=(y*info.width+x)*info.channels;rS+=data[i];gS+=data[i+1];bS+=data[i+2];c++}return[Math.round(rS/c),Math.round(gS/c),Math.round(bS/c)]}
function generateVoteColors(bgRgb){const[h,s,l]=rgbToHsl(...bgRgb);const yH=(h+150)%360;const yR=hslToRgb(yH,Math.min(s+0.3,0.7),0.5);const nR=hslToRgb(h,Math.min(s+0.1,0.4),Math.max(l+0.15,0.35));return{yes:{r:yR[0],g:yR[1],b:yR[2]},no:{r:nR[0],g:nR[1],b:nR[2]}}}

function buildHTML(bgImage, colors, label) {
  const yc = colors.yes, nc = colors.no;
  const yesWin = true; // 58 vs 42

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    .thumb{width:864px;height:280px;position:relative;overflow:hidden;font-family:Arial,sans-serif;color:white;background:#080810}
    .bg{position:absolute;inset:0;background:url('${IMG}/${bgImage}') center/cover;opacity:0.7}
    .overlay{position:absolute;inset:0;
      background:linear-gradient(90deg,rgba(8,10,5,0.75) 0%,rgba(8,10,5,0.3) 45%,rgba(8,10,5,0.05) 100%)}
    .logo{position:absolute;top:14px;right:16px;height:16px;width:auto;z-index:5;opacity:0.75}
    .content{position:absolute;left:36px;top:50%;transform:translateY(-50%);z-index:4}
    .label{position:absolute;top:8px;left:36px;font-size:10px;color:rgba(255,255,255,0.4);z-index:6;letter-spacing:1px}

    .title{
      font-size:32px;font-weight:900;line-height:1.15;max-width:430px;
      color:white;
      -webkit-text-stroke:1.5px rgba(0,0,0,0.6);
      paint-order:stroke fill;
      text-shadow:
        0 0 6px rgba(0,0,0,1),
        0 0 12px rgba(0,0,0,0.8),
        0 2px 4px rgba(0,0,0,0.9),
        0 0 30px rgba(0,0,0,0.5);
    }

    .vote-wrapper{
      display:inline-flex;gap:8px;margin-top:18px;
      background:rgba(0,0,0,0.35);
      border:2px solid rgba(255,255,255,0.15);
      border-radius:14px;padding:8px 10px;
      backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
      box-shadow:0 4px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .vote-btn{
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      width:105px;height:58px;border-radius:10px;
    }
    .vote-label{font-size:16px;font-weight:800;letter-spacing:1.5px;text-shadow:0 1px 4px rgba(0,0,0,0.7)}
    .vote-pct{font-size:13px;font-weight:700;margin-top:2px;text-shadow:0 1px 3px rgba(0,0,0,0.6)}

    .yes-btn{
      background:rgba(${yc.r},${yc.g},${yc.b},0.8);
      border:2.5px solid rgba(${yc.r},${yc.g},${yc.b},0.95);
      color:rgba(255,255,255,1);
      box-shadow:0 2px 10px rgba(0,0,0,0.4), 0 0 15px rgba(${yc.r},${yc.g},${yc.b},0.3);
    }
    .no-btn{
      background:rgba(${nc.r},${nc.g},${nc.b},0.25);
      border:2.5px solid rgba(${nc.r},${nc.g},${nc.b},0.35);
      color:rgba(255,255,255,0.5);
      box-shadow:0 2px 8px rgba(0,0,0,0.3);
    }
  </style></head><body><div class="thumb">
    <div class="bg"></div>
    <div class="overlay"></div>
    <img class="logo" src="${LOGO}"/>
    <div class="label">${label}</div>
    <div class="content">
      <div class="title">배드버니 하프타임쇼<br/>조회수 1.25억 넘길까?</div>
      <div class="vote-wrapper">
        <div class="vote-btn yes-btn">
          <span class="vote-label">YES</span>
          <span class="vote-pct">(58%)</span>
        </div>
        <div class="vote-btn no-btn">
          <span class="vote-label">NO</span>
          <span class="vote-pct">(42%)</span>
        </div>
      </div>
    </div>
  </div></body></html>`;
}

async function renderAll() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 864, height: 280, deviceScaleFactor: 2 });

  const variants = [
    { img: 'badbunny_basic.jpg', label: 'A: 기본 검색', suffix: 'basic' },
    { img: 'badbunny_smart2.jpg', label: 'B: 스마트 검색', suffix: 'smart' },
  ];

  for (const v of variants) {
    const bgRgb = await extractDominantColor(path.join(__dirname, IMG, v.img));
    const colors = generateVoteColors(bgRgb);
    const html = buildHTML(v.img, colors, v.label);
    const htmlPath = path.join(__dirname, `thumb_v5e_bb_${v.suffix}.html`);
    const pngPath = path.join(__dirname, `thumb_v5e_bb_${v.suffix}.png`);
    fs.writeFileSync(htmlPath, html);
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 300));
    await page.screenshot({ path: pngPath, type: 'png' });
    console.log(`Done: ${v.suffix}`);
  }

  await browser.close();
}

renderAll().catch(console.error);
