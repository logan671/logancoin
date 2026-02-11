const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SERPER_KEY = '192671b8fa232c45b7b75aa636d9650510a3ef2d';
const IMG_DIR = path.join(__dirname, 'images');

// Domains to skip (watermark sources)
const BLOCKED_DOMAINS = [
  'alamy.com', 'shutterstock.com', 'dreamstime.com', 'gettyimages.com',
  'istockphoto.com', '123rf.com', 'depositphotos.com', 'stock.adobe.com',
  'bigstockphoto.com', 'pond5.com', 'vectorstock.com', 'freepik.com'
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

async function searchAndDownload(name, query, num) {
  console.log(`\nSearching: "${query}"`);
  const result = await serperImageSearch(query, num);
  const images = (result.images || []).filter(img => !isBlocked(img.imageUrl));
  console.log(`  Clean results: ${images.length} (blocked ${(result.images||[]).length - images.length} stock sites)`);

  for (let i = 0; i < images.length; i++) {
    const url = images[i].imageUrl;
    const ext = url.match(/\.(png|jpg|jpeg|webp|gif)/i)?.[1] || 'jpg';
    const filepath = path.join(IMG_DIR, `${name}_clean.${ext}`);
    console.log(`  [${i}] ${images[i].title?.substring(0, 50)}`);
    console.log(`      ${url.substring(0, 80)}...`);
    try {
      await downloadImage(url, filepath);
      const stat = fs.statSync(filepath);
      // Check it's actually an image (not HTML)
      const header = fs.readFileSync(filepath, { encoding: null }).slice(0, 4);
      const isHTML = header.toString().startsWith('<') || header.toString().startsWith('<!');
      if (isHTML) {
        console.log(`      SKIP: got HTML instead of image`);
        fs.unlinkSync(filepath);
        continue;
      }
      console.log(`  Downloaded: ${name}_clean.${ext} (${(stat.size/1024).toFixed(1)} KB)`);
      return;
    } catch(e) {
      console.log(`      FAIL: ${e.message}`);
    }
  }
  console.log(`  WARNING: no clean image found for ${name}`);
}

async function main() {
  // Re-search problematic images with watermark exclusions
  await searchAndDownload('hottest_earth', 'global warming burning earth illustration -stock -watermark', 10);
  await searchAndDownload('hottest_earth_alt', 'climate change earth fire NASA free', 10);
  console.log('\nDone!');
}

main().catch(console.error);
