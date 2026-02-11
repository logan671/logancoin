const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const BREAKING_API = 'https://polymarket.com/api/biggest-movers';

const server = http.createServer(async (req, res) => {
    // CORS 헤더
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://localhost:${PORT}`);

    // API 프록시 - 실제 폴리마켓 Breaking API 사용
    if (url.pathname === '/api/markets') {
        try {
            const data = await fetchJson(BREAKING_API);
            // markets 배열에서 상위 10개만 반환
            const markets = data.markets || data;
            const top10 = Array.isArray(markets) ? markets.slice(0, 10) : [];
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(top10));
        } catch (error) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: error.message }));
        }
        return;
    }

    // 정적 파일 서빙
    if (url.pathname === '/' || url.pathname === '/index.html') {
        const htmlPath = path.join(__dirname, 'polymarket-breaking.html');
        fs.readFile(htmlPath, (err, data) => {
            if (err) {
                res.writeHead(404);
                res.end('File not found');
                return;
            }
            // API URL을 로컬 프록시로 변경
            const modified = data.toString().replace(
                "const API_URL = 'https://gamma-api.polymarket.com/markets';",
                "const API_URL = '/api/markets';"
            );
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(modified);
        });
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

function fetchJson(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (response) => {
            let data = '';
            response.on('data', chunk => data += chunk);
            response.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(new Error('Invalid JSON response'));
                }
            });
        }).on('error', reject);
    });
}

server.listen(PORT, () => {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🚀 Polymarket Breaking Top 10 Server                    ║
║                                                           ║
║   서버가 실행 중입니다!                                   ║
║                                                           ║
║   브라우저에서 열기: http://localhost:${PORT}               ║
║                                                           ║
║   종료하려면: Ctrl+C                                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `);
});
