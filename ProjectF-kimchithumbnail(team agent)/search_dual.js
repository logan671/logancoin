const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SERPER_KEY = '192671b8fa232c45b7b75aa636d9650510a3ef2d';
const IMG_DIR = path.join(__dirname, 'images');

const BLOCKED_DOMAINS = [
  'alamy.com', 'shutterstock.com', 'dreamstime.com', 'gettyimages.com',
  'istockphoto.com', '123rf.com', 'depositphotos.com', 'stock.adobe.com',
  'bigstockphoto.com', 'pond5.com', 'vectorstock.com', 'freepik.com',
  'instagram.com', 'fbcdn.net'
];

const MIN_WIDTH = 800; // 최소 해상도 필터

function isBlocked(url) {
  return BLOCKED_DOMAINS.some(d => url.includes(d));
}

function serperImageSearch(query, num) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ q: query, num: num, gl: 'us' });
    const options = {
      hostname: 'google.serper.dev',
      path: '/images',
      method: 'POST',
      headers: { 'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json' }
    };
    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => { try { resolve(JSON.parse(body)); } catch(e) { reject(e); } });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function downloadImage(url, filepath) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const req = mod.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 10000 }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return downloadImage(res.headers.location, filepath).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) return reject(new Error(`HTTP ${res.statusCode}`));
      const stream = fs.createWriteStream(filepath);
      res.pipe(stream);
      stream.on('finish', () => { stream.close(); resolve(filepath); });
      stream.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

async function downloadFirst(name, images, suffix) {
  for (let i = 0; i < Math.min(images.length, 5); i++) {
    const img = images[i];
    const url = img.imageUrl;
    const ext = url.match(/\.(png|jpg|jpeg|webp|gif)/i)?.[1] || 'jpg';
    const filepath = path.join(IMG_DIR, `${name}_${suffix}.${ext}`);
    const dimInfo = img.imageWidth ? ` (${img.imageWidth}x${img.imageHeight})` : '';
    console.log(`    [${i}] ${img.title?.substring(0, 55)}${dimInfo}`);
    try {
      await downloadImage(url, filepath);
      const stat = fs.statSync(filepath);
      if (stat.size < 5000) {
        console.log(`        SKIP: too small`);
        fs.unlinkSync(filepath); continue;
      }
      const header = fs.readFileSync(filepath, { encoding: null }).slice(0, 4);
      if (header.toString().startsWith('<')) {
        console.log(`        SKIP: HTML`);
        fs.unlinkSync(filepath); continue;
      }
      console.log(`    ✓ ${(stat.size/1024).toFixed(0)} KB`);
      return filepath;
    } catch(e) {
      console.log(`        FAIL: ${e.message}`);
    }
  }
  return null;
}

// ── 듀얼 검색: basic + smart 각각 1장씩 ──

async function dualSearch(name, basicQuery, smartQuery) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📷 ${name}`);

  // A: 기본 검색
  console.log(`\n  [A 기본] "${basicQuery}"`);
  const resultA = await serperImageSearch(basicQuery, 15);
  const imagesA = (resultA.images || [])
    .filter(img => !isBlocked(img.imageUrl))
    .filter(img => !img.imageWidth || img.imageWidth >= MIN_WIDTH); // 해상도 필터
  console.log(`  결과: ${imagesA.length}개 (HD필터 적용, min ${MIN_WIDTH}px)`);
  await downloadFirst(name, imagesA, 'basic');

  // B: 스마트 검색 (키워드 조합)
  console.log(`\n  [B 스마트] "${smartQuery}"`);
  const resultB = await serperImageSearch(smartQuery, 15);
  const imagesB = (resultB.images || [])
    .filter(img => !isBlocked(img.imageUrl))
    .filter(img => !img.imageWidth || img.imageWidth >= MIN_WIDTH);
  console.log(`  결과: ${imagesB.length}개 (HD필터 적용, min ${MIN_WIDTH}px)`);
  await downloadFirst(name, imagesB, 'smart2');
}

async function main() {
  console.log('🔍 듀얼 검색 시작 (기본 vs 스마트, HD 필터)\n');

  await dualSearch('kospi',
    'KOSPI index Korea stock',                           // 기본
    'KOSPI 2026 stock market rally record high Korea'    // 스마트
  );

  await dualSearch('culinary',
    '흑백요리사 포스터',                                   // 기본
    '흑백요리사 시즌2 요리 대결 넷플릭스'                    // 스마트
  );

  await dualSearch('relay',
    'Relay crypto token logo',                           // 기본
    'Relay token TGE crypto launch 2025'                 // 스마트
  );

  await dualSearch('hottest',
    'hottest year climate change',                       // 기본
    '2026 hottest year record breaking temperature'      // 스마트
  );

  await dualSearch('badbunny',
    'Bad Bunny portrait',                                // 기본
    'Bad Bunny Super Bowl halftime show 2025 performance' // 스마트
  );

  console.log('\n\n✅ 듀얼 검색 완료!');
}

main().catch(console.error);
