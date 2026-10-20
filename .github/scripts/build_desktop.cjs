const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const core = fs.readFileSync(path.join(root, 'accuracy-core.js'), 'utf8');
let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
html = html.replace(/\/\* Shared deterministic rules\.[\s\S]*?(?=    function safePlainText)/, () => core + '\n');
html = html.replace(/[\t ]+$/gm, '');
fs.writeFileSync(path.join(root, 'index.html'), html);
let desktop = html.replace("const dataUrl = location.protocol === 'file:' ? REMOTE_DATA_URL : './data.json';", "const dataUrl = location.protocol === 'file:' ? REMOTE_DATA_URL : './kanu-database/data.json';");
// 桌面單檔版會先連 GitHub 抓最新資料，連線失敗才使用下方內嵌的 bundled-data。
const data = fs.readFileSync(path.join(root, 'data.json'), 'utf8').replace(/</g, '\\u003c');
desktop = desktop.replace('</body>', `<script id="bundled-data" type="application/json">${data}</script>\n</body>`);
fs.writeFileSync(path.join(root, '../卡奴.html'), desktop);
