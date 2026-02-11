const puppeteer = require('puppeteer');
const path = require('path');

async function renderThumbnail() {
  console.log('1. 브라우저 실행 중...');
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  // Set viewport to thumbnail size
  await page.setViewport({ width: 1200, height: 400 });

  // Load the HTML file
  const htmlPath = path.join(__dirname, 'test_thumbnail.html');
  console.log('2. HTML 파일 로딩 중...');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'load' });

  // Screenshot
  const outputPath = path.join(__dirname, 'result_thumbnail.png');
  console.log('3. 스크린샷 찍는 중...');
  await page.screenshot({ path: outputPath, type: 'png' });

  console.log(`4. 완료! ${outputPath}`);
  await browser.close();
}

renderThumbnail().catch(console.error);
