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

// 이미지 다운로드 시도 (첫 성공 반환)
async function tryDownloadFirst(name, images, suffix) {
  for (let i = 0; i < images.length; i++) {
    const url = images[i].imageUrl;
    const ext = url.match(/\.(png|jpg|jpeg|webp|gif)/i)?.[1] || 'jpg';
    const filepath = path.join(IMG_DIR, `${name}_${suffix}.${ext}`);
    console.log(`    [${i}] ${images[i].title?.substring(0, 60)}`);
    console.log(`        ${url.substring(0, 80)}...`);
    try {
      await downloadImage(url, filepath);
      const stat = fs.statSync(filepath);
      if (stat.size < 5000) { // 너무 작으면 스킵
        console.log(`        SKIP: too small (${stat.size} bytes)`);
        fs.unlinkSync(filepath);
        continue;
      }
      const header = fs.readFileSync(filepath, { encoding: null }).slice(0, 4);
      const isHTML = header.toString().startsWith('<') || header.toString().startsWith('<!');
      if (isHTML) {
        console.log(`        SKIP: got HTML`);
        fs.unlinkSync(filepath);
        continue;
      }
      console.log(`    OK: ${name}_${suffix}.${ext} (${(stat.size/1024).toFixed(1)} KB)`);
      return filepath;
    } catch(e) {
      console.log(`        FAIL: ${e.message}`);
    }
  }
  return null;
}

// ── 스마트 검색: 1차(키워드 조합) → 2차(단일 키워드) ──

async function smartSearch(name, queries) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📷 ${name}`);

  for (let q = 0; q < queries.length; q++) {
    const query = queries[q];
    const label = q === 0 ? '1차 (조합)' : `${q+1}차 (fallback)`;
    console.log(`\n  [${label}] "${query}"`);

    const result = await serperImageSearch(query, 10);
    const images = (result.images || []).filter(img => !isBlocked(img.imageUrl));
    console.log(`  결과: ${images.length}개 (차단: ${(result.images||[]).length - images.length})`);

    if (images.length === 0) continue;

    const downloaded = await tryDownloadFirst(name, images.slice(0, 5), q === 0 ? 'smart' : `fb${q}`);
    if (downloaded) return downloaded;
  }

  console.log(`  ⚠️ 모든 검색 실패: ${name}`);
  return null;
}

// ── 5개 주제: 제목 → 키워드 조합 ──

async function main() {
  console.log('🔍 스마트 이미지 검색 시작\n');

  // 1. 코스피 - "코스피 상승" → "KOSPI chart"
  await smartSearch('kospi', [
    'KOSPI 2026 stock market rally Korea',
    'KOSPI chart bull market',
    'Korea stock exchange'
  ]);

  // 2. 흑백요리사 - "흑백요리사 시즌2 요리 대결" → "흑백요리사"
  await smartSearch('culinary', [
    '흑백요리사 시즌2 요리 대결',
    'Culinary Class Wars season 2 Netflix',
    '흑백요리사 포스터'
  ]);

  // 3. Relay - "Relay token TGE crypto" → "Relay protocol"
  await smartSearch('relay', [
    'Relay token TGE crypto launch',
    'Relay protocol crypto logo',
    'Relay chain cryptocurrency'
  ]);

  // 4. 더운해 - "2026 hottest year record climate" → "global warming"
  await smartSearch('hottest', [
    '2026 hottest year record breaking climate',
    'global warming 2026 temperature record NASA',
    'climate change burning earth'
  ]);

  // 5. 배드버니 - "Bad Bunny Super Bowl halftime show" → "Bad Bunny"
  await smartSearch('badbunny', [
    'Bad Bunny Super Bowl halftime show 2025 performance',
    'Bad Bunny NFL halftime concert stage',
    'Bad Bunny performing live'
  ]);

  console.log('\n\n✅ 스마트 검색 완료!');
}

main().catch(console.error);
