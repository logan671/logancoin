const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SERPER_KEY = '192671b8fa232c45b7b75aa636d9650510a3ef2d';
const IMG_DIR = path.join(__dirname, 'images');

if (!fs.existsSync(IMG_DIR)) fs.mkdirSync(IMG_DIR);

// Search queries for each topic
const searches = [
  { name: 'kospi_flag', query: 'South Korea flag PNG transparent background', num: 3 },
  { name: 'kospi_chart', query: 'KOSPI stock market chart 2026', num: 3 },
  { name: 'culinary_logo', query: '흑백요리사 로고 PNG', num: 3 },
  { name: 'culinary_person', query: '흑백요리사 시즌2 출연자', num: 3 },
  { name: 'relay_logo', query: 'Relay Chain crypto logo PNG', num: 3 },
  { name: 'relay_coin', query: 'Relay protocol crypto coin', num: 3 },
  { name: 'hottest_earth', query: 'global warming earth burning illustration', num: 3 },
  { name: 'hottest_thermometer', query: 'thermometer hot red PNG transparent', num: 3 },
  { name: 'badbunny_superbowl', query: 'Bad Bunny Super Bowl 2025 halftime show performance', num: 5 },
  { name: 'badbunny_portrait', query: 'Bad Bunny portrait high resolution', num: 3 },
];

function serperImageSearch(query, num) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ q: query, num: num, gl: 'us' });
    const options = {
      hostname: 'google.serper.dev',
      path: '/images',
      method: 'POST',
      headers: {
        'X-API-KEY': SERPER_KEY,
        'Content-Type': 'application/json',
      }
    };
    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); } catch(e) { reject(e); }
      });
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
        // Follow redirect
        return downloadImage(res.headers.location, filepath).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      const stream = fs.createWriteStream(filepath);
      res.pipe(stream);
      stream.on('finish', () => { stream.close(); resolve(filepath); });
      stream.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

async function main() {
  for (const s of searches) {
    console.log(`\nSearching: "${s.query}"`);
    try {
      const result = await serperImageSearch(s.query, s.num);
      const images = result.images || [];
      console.log(`  Found ${images.length} results`);

      // Show all results
      images.forEach((img, i) => {
        console.log(`  [${i}] ${img.imageUrl?.substring(0, 80)}...`);
        console.log(`      title: ${img.title?.substring(0, 60)}`);
      });

      // Download first image
      if (images.length > 0) {
        const url = images[0].imageUrl;
        const ext = url.match(/\.(png|jpg|jpeg|webp|gif)/i)?.[1] || 'jpg';
        const filepath = path.join(IMG_DIR, `${s.name}_0.${ext}`);
        try {
          await downloadImage(url, filepath);
          const stat = fs.statSync(filepath);
          console.log(`  Downloaded: ${s.name}_0.${ext} (${(stat.size/1024).toFixed(1)} KB)`);
        } catch(e) {
          console.log(`  Download failed for first, trying second...`);
          if (images.length > 1) {
            const url2 = images[1].imageUrl;
            const ext2 = url2.match(/\.(png|jpg|jpeg|webp|gif)/i)?.[1] || 'jpg';
            const filepath2 = path.join(IMG_DIR, `${s.name}_0.${ext2}`);
            try {
              await downloadImage(url2, filepath2);
              const stat2 = fs.statSync(filepath2);
              console.log(`  Downloaded: ${s.name}_0.${ext2} (${(stat2.size/1024).toFixed(1)} KB)`);
            } catch(e2) {
              console.log(`  Failed again: ${e2.message}`);
            }
          }
        }
      }
    } catch(e) {
      console.log(`  Error: ${e.message}`);
    }
  }
  console.log('\nDone! Check images/ folder.');
}

main();
