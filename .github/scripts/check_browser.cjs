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
  await page.clock.install({time:new Date('2026-11-02T23:30:00+08:00')});
  // Reject old published data rather than silently overwriting the repaired bundle.
  await page.route('https://raw.githubusercontent.com/**',route=>route.fulfill({json:{version:'2026.11.01-v184632-sourcefix',integrityRevision:1,cards:[],rules:[]}}));
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${server.address().port}`,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof appRules!=='undefined' && appRules.length>0);
  assert.equal(await page.evaluate(()=>appRules.length),JSON.parse(fs.readFileSync(path.join(root,'data.json'))).rules.length);
  const registrationUrls=await page.evaluate(()=>({
    short:getRegistrationDestination({sourceUrl:'https://bank.example/offer',registrationUrl:'https://lihi3.me/abc'}),
    sameHost:getRegistrationDestination({sourceUrl:'https://bank.example/offer',registrationUrl:'https://bank.example/register'}),
    observed:getRegistrationDestination({sourceUrl:'https://bank.example/offer',registrationUrl:'https://bank.example/register',registrationLinkEvidence:{sourceUrl:'https://bank.example/offer',method:'observed_page_anchor',urls:['https://bank.example/register']}}),
    label:getRegistrationActionLabel({sourceUrl:'https://bank.example/offer',registrationUrl:'https://lihi3.me/abc'})
  }));
  assert.deepEqual(registrationUrls,{short:'https://bank.example/offer',sameHost:'https://bank.example/offer',observed:'https://bank.example/register',label:'前往活動來源頁確認登錄方式'});
  const travelRegistration=await page.evaluate(()=>{
    const visa=appRules.find(r=>r.id==='review_ctbc_trip_registration_2026h2');
    const jcb=appRules.find(r=>r.id==='review_ctbc_tigerair_registration_2026h2');
    const at=new Date('2026-11-04T00:00:00Z');
    return {visa:visa&&getNextRecurringRegistrationOpening(visa,at)?.toISOString(),
      jcb:jcb&&getNextRecurringRegistrationOpening(jcb,at)?.toISOString(),
      visaStatus:visa&&KanuAccuracy.assessment(visa).level,
      jcbStatus:jcb&&KanuAccuracy.assessment(jcb).level};
  });
  assert.deepEqual(travelRegistration,{visa:'2026-11-06T02:00:00.000Z',jcb:'2026-11-06T05:00:00.000Z',
    visaStatus:'BLOCKED',jcbStatus:'BLOCKED'});
  assert.equal(await page.evaluate(()=>{
    const r={id:'unresolved_fixture',title:'CUBE卡優惠',cardId:null,unresolvedCardId:'cathay_cube',associationStatus:'needs_review'};
    appRules.push(r);reconcileRuleCardAssociations();appRules.pop();
    return r.cardId;
  }),null);
  const quality = await page.evaluate(()=>{
    const checked=appRules.filter(r=>KanuAccuracy.isReviewed(r));
    const unsafe=appRules.filter(r=>!KanuAccuracy.isReviewed(r)).some(r=>getRewardRankingMetrics(r,calcRuleCashBack(r,2000)).cash>0);
    const r=structuredClone(checked[0]);r.promoRate+=10;
    const pointRule=appRules.find(r=>r.id==='rule_1704bb66da21702598dd');
    return {checked:checked.length,unsafe,mutatedStillTrusted:KanuAccuracy.isReviewed(r),pointType:pointRule.rewardType};
  });
  assert.deepEqual(quality,{checked:3,unsafe:false,mutatedStillTrusted:false,pointType:'points'});
  const assessmentDisplay=await page.evaluate(()=>{
    const r={...appRules.find(r=>r.id==='review_ubear_online_202609'),id:'reference_fixture',accuracyReview:null,
      title:'最高3%網購回饋',rewardType:'percent',rewardUnit:'percent',sourceUrl:'https://bank.test/offer'};
    const calc=calcRuleCashBack(r,2000);
    return {headline:getRecommendationHeadline(r,calc,getRuleConditionStatus(r,null)),label:getRuleRewardLabel(r),cash:getRewardRankingMetrics(r,calc).cash};
  });
  assert.ok(assessmentDisplay.headline.includes('3%'));
  assert.ok(assessmentDisplay.headline.includes('資料列示'));
  assert.ok(!assessmentDisplay.headline.includes('待核實'));
  assert.equal(assessmentDisplay.cash,0);
  for (const query of ['LINE Pay','Apple Store','中油','海外']) {
    await page.evaluate(query=>{setScope('all');document.getElementById('search-input').value=query;handleSearchInput()},query);
    await page.waitForTimeout(100);
    const text=await page.locator('#spending-list-container').innerText();
    assert.ok(text.length>0,query+' must render a result or an honest empty state');
    const groups=page.locator('#spending-list-container details');
    if (await groups.count()) assert.equal(await groups.first().getAttribute('open'),null);
  }
  await page.evaluate(()=>{setQuickSearchMode('payment');document.getElementById('search-input').value='LOPIA';handleSearchInput()});
  const lopiaText=await page.locator('#spending-list-container').innerText();
  assert.match(lopiaText,/目前沒有找到可核對的行動支付活動/);
  await page.evaluate(()=>{document.getElementById('search-input').value='早餐';handleSearchInput()});
  const breakfastText=await page.locator('#spending-list-container').innerText();
  assert.match(breakfastText,/早餐咖啡/);
  assert.match(breakfastText,/條款待核對/);
  await page.evaluate(()=>setQuickSearchMode('card'));
  await page.evaluate(()=>{appCards.find(c=>c.id==='card_玉山銀行_9').owned=true;setScope('my');document.getElementById('search-input').value='LINE Pay';handleSearchInput()});
  assert.ok((await page.locator('#spending-list-container').innerText()).length>0);
  await page.evaluate(()=>{setScope('all');document.getElementById('search-input').value='網購';handleSearchInput()});
  await page.waitForTimeout(400);
  assert.ok((await page.locator('#spending-list-container').innerText()).length>0);
  const checked = await page.evaluate(()=>{
    const r=appRules.find(r=>r.id==='review_ubear_online_202609');
    const calc=calcRuleCashBack(r,6666);
    return {cash:calc.potentialCash,total:calc.totalCash,conditional:getRuleConditionStatus(r,appCards.find(c=>c.id===r.cardId)).conditional};
  });
  assert.deepEqual(checked,{cash:199,total:0,conditional:true});
  const badgeSafety=await page.evaluate(()=>{
    const r={id:'fixture',sourceUrl:'https://bank.test/offer',title:'最高3%回饋',rewardType:'percent',baseRate:1,promoRate:3};
    const ubear=appRules.find(x=>x.id==='review_ubear_online_202609');
    const switchBadge=getRuleDisplayBadge(
      {...ubear,selectionMode:'SWITCHABLE',benefitPlan:'集精選'},
      {potentialRate:3,potentialCash:60,totalCash:0,spendAmount:2000,calculable:true,capped:false},
      {conditional:true,reasons:['須切換方案']},
      {cardName:'CUBE卡'}
    );
    const cappedBadge=getRuleDisplayBadge(
      ubear,
      {potentialRate:3,potentialCash:150,totalCash:150,spendAmount:10000,calculable:true,capped:true},
      {conditional:false,reasons:[]},
      {cardName:'U Bear卡'}
    );
    return {blocked:getRuleDisplayBadge(r,{potentialRate:4,potentialCash:80,calculable:true}),switchTone:switchBadge.tone,cappedSub:cappedBadge.sub};
  });
  assert.equal(badgeSafety.blocked.rate,'待確認');assert.equal(badgeSafety.blocked.rateNum,0);
  assert.equal(badgeSafety.switchTone,'blue');
  assert.match(badgeSafety.cappedSub,/已達上限/);
  const capLoop=await page.evaluate(()=>{
    const r=appRules.find(x=>x.id==='review_ubear_online_202609');
    const before=calcRuleCashBack(r,6000).potentialCash;
    recordSpendForCard(r.cardId,6000,r.id);
    const after=calcRuleCashBack(r,6000).potentialCash;
    const usage=getCardMonthlyUsage(r.cardId);
    delete localStorage['kanu_cap_usage_'+getTaipeiYearMonth()];
    localStorage.removeItem('kanu_cap_usage_'+getTaipeiYearMonth());
    return {before,after,spent:usage.totalSpent,usedCap:usage.rules[r.id].usedCap};
  });
  assert.equal(capLoop.before,180);
  assert.equal(capLoop.usedCap,120);
  assert.equal(capLoop.after,90); // 60 base + 30 remaining promo cap!
  assert.equal(capLoop.spent,6000);
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
  await page.evaluate(()=>checkRemoteDataUpdate());
  assert.equal(await page.evaluate(()=>activeDataVersion),JSON.parse(fs.readFileSync(path.join(root,'data.json'))).version);
  assert.match(await page.locator('#sync-status-msg').innerText(),/本機資料版本較新/);
  await page.evaluate(()=>{setScope('all');document.getElementById('search-input').value='網購';handleSearchInput()});
  await page.waitForTimeout(400);
  await page.screenshot({path:path.join(root,'test-output/recommendation-mobile.png')});
  await page.evaluate(()=>{
    const older=JSON.parse(document.getElementById('bundled-data').textContent);
    older.version='2026.11.01-v184632-sourcefix';
    older.rules=older.rules.slice(0,1);
    localStorage.setItem(LOCAL_CACHE_KEY,JSON.stringify(older));
  });
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>appRules.length>0);
  assert.equal(await page.evaluate(()=>activeDataVersion),JSON.parse(fs.readFileSync(path.join(root,'data.json'))).version);
  assert.equal(await page.evaluate(()=>appRules.length),JSON.parse(fs.readFileSync(path.join(root,'data.json'))).rules.length);
  await page.evaluate(()=>{
    const newer=JSON.parse(document.getElementById('bundled-data').textContent);
    newer.version='2099.01.01-v000001-newer-cache-fixture';
    localStorage.setItem(LOCAL_CACHE_KEY,JSON.stringify(newer));
  });
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>appRules.length>0);
  assert.equal(await page.evaluate(()=>activeDataVersion),'2099.01.01-v000001-newer-cache-fixture');
  assert.deepEqual(errors,[]);
  console.log('Browser passed: load, search, unknown registration, persistent marks, desktop file, no JS errors.');
 } finally {if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1});
