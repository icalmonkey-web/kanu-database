const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname,'../..');
const file = path.join(root,'index.html');
let html=fs.readFileSync(file,'utf8');
const match=html.match(/<script>\s*(tailwind.config = [\s\S]*?)<\/script>/);
if(match){
 const ctx={tailwind:{}};vm.runInNewContext(match[1],ctx);
 fs.writeFileSync(path.join(root,'tailwind.config.cjs'),'module.exports='+JSON.stringify({...ctx.tailwind.config,content:['./index.html']},null,2));
 html=html.replace(match[0],'').replace('  <script src="https://cdn.tailwindcss.com"></script>','');
}
html=html.replace(/<style id="compiled-utilities">[\s\S]*?<\/style>/,'');
fs.writeFileSync(file,html);
fs.writeFileSync(path.join(root,'tailwind.input.css'),'@tailwind base;\n@tailwind components;\n@tailwind utilities;\n');
execFileSync(process.execPath,[path.join(root,'.build-deps/node_modules/tailwindcss/lib/cli.js'),'-c','tailwind.config.cjs','-i','tailwind.input.css','-o','tailwind.generated.css','--minify'],{cwd:root,stdio:'inherit'});
const css=fs.readFileSync(path.join(root,'tailwind.generated.css'),'utf8');
html=html.replace('  <style>',`  <style id="compiled-utilities">${css}</style>\n  <style>`);
html=html.replace(/const trusted = rule.accuracyReview\?\.status === 'SOURCE_CHECKED'\s*&& !rule.accuracyReview\?\.issues\?\.length;/,'const trusted = KanuAccuracy.isReviewed(rule);')
 .replaceAll("rule.accuracyReview?.status !== 'SOURCE_CHECKED'",'!KanuAccuracy.isReviewed(rule)')
 .replaceAll("rule.accuracyReview?.status === 'SOURCE_CHECKED'",'KanuAccuracy.isReviewed(rule)')
 .replace("const checked = audit?.status === 'SOURCE_CHECKED';",'const checked = KanuAccuracy.isReviewed(rule);');
fs.writeFileSync(file,html);
