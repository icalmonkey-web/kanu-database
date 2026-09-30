const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const http = require('node:http');
const {chromium} = require(require.resolve('playwright', {paths:[process.env.KANU_NODE_MODULES || 'C:/Users/IcalM/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules']}));
const root = path.resolve(__dirname, '../..');
(async()=>{
 const server = http.createServer((req,res)=>{
  const name = req.url.split('?')[0] === '/data.json' ? 'data.json' : 'index.html';
  res.setHeader('Content-Type',name.endsWith('json')?'application/json':'text/html; charset=utf-8');
  res.end(fs.readFileSync(path.join(root,name)));
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 let browser;
 try {
  browser = await chromium.launch({channel:'msedge',headless:true});
  const page = await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${server.address().port}`,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof appRules!=='undefined' && appRules.length>0);
  assert.equal(await page.evaluate(()=>appRules.length),JSON.parse(fs.readFileSync(path.join(root,'data.json'))).rules.length);
  await page.evaluate(()=>{setScope('all');document.getElementById('search-input').value='網購';handleSearchInput()});
  await page.waitForTimeout(400);
  assert.ok((await page.locator('#spending-list-container').innerText()).length>0);
  const checked = await page.evaluate(()=>{
    const r=appRules.find(r=>r.id==='review_ubear_online_202609');
    const calc=calcRuleCashBack(r,6666);
    return {cash:calc.potentialCash,total:calc.totalCash,conditional:getRuleConditionStatus(r,appCards.find(c=>c.id===r.cardId)).conditional};
  });
  assert.deepEqual(checked,{cash:199,total:0,conditional:true});
  await page.evaluate(()=>openCardDetailModal('card_esun_ubear','review_ubear_online_202609'));
  assert.ok((await page.locator('#modal-card-body').innerText()).includes('已核對官方條款'));
  await page.evaluate(()=>closeCardDetailModal());
  await page.evaluate(()=>{switchTab('rewards-store');setRegFilter('unknown')});
  assert.ok((await page.locator('#rewards-store-container').innerText()).includes('待確認'));
  await page.evaluate(()=>{const r=appRules.find(r=>r.needReg);r.registered=true;r.registeredPeriod=getRuleStateKey(r);saveRegisteredState()});
  const marked=await page.evaluate(()=>appRules.find(r=>r.registered).id);
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>appRules.length>0);
  assert.equal(await page.evaluate(id=>appRules.find(r=>r.id===id).registered,marked),true);
  await page.evaluate(()=>{switchTab('rewards-store');setRegFilter('unknown')});
  fs.mkdirSync(path.join(root,'test-output'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-output/registration-mobile.png')});
  await page.goto(require('node:url').pathToFileURL(path.join(root,'../卡奴.html')).href,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>appRules.length>0);
  assert.equal(await page.evaluate(()=>appRules.length),JSON.parse(fs.readFileSync(path.join(root,'data.json'))).rules.length);
  await page.evaluate(()=>{setScope('all');document.getElementById('search-input').value='網購';handleSearchInput()});
  await page.waitForTimeout(400);
  await page.screenshot({path:path.join(root,'test-output/recommendation-mobile.png')});
  assert.deepEqual(errors,[]);
  console.log('Browser passed: load, search, unknown registration, persistent marks, desktop file, no JS errors.');
 } finally {if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1});
