const {test}=require('node:test'),assert=require('node:assert/strict');
const {recover}=require('./recover_unverified_data.cjs');
const A=require('../../accuracy-core.js');
test('icash Pay member listing is scoped to 7-ELEVEN and remains pending detail',()=>{
 const r=require('../../data.json').rules.find(x=>x.id==='rule_e0de86b169c8af40b1cd');
 assert.equal(r.scope,'SPECIFIC');assert.deepEqual(r.matchedMerchants,['7-ELEVEN']);
 assert.equal(r.baseRate,0.5);assert.equal(r.rewardAmount,null);
 assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');
});
test('FEIB HAPPY GO is one point per 100 TWD, with partner bonus unverified',()=>{
 const data=require('../../data.json');
 for(const id of ['rule_5a93150fd5808fac5b8b','rule_c5039b4990adc6a3ac89']){
  const r=data.rules.find(x=>x.id===id);
  assert.deepEqual(r.pointEarnRate,{spendTwd:100,points:1});
  assert.equal(r.baseRate,0);assert.equal(r.promoRate,0);assert.equal(r.rewardAmount,null);
  assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('SC Infinite point multipliers never become percentage or cash rankings',()=>{
 const data=require('../../data.json');
 for(const [id,points] of [['rule_5036b814fc5e1e83202e',1],['rule_45ac71e9e9d63a71fea7',3],['rule_86e75835845ffbb5a367',6],['sc_pi_overseas',6]]){
  const r=data.rules.find(x=>x.id===id);
  assert.deepEqual(r.pointEarnRate,{spendTwd:10,points});
  assert.equal(r.baseRate,0);assert.equal(r.promoRate,0);assert.equal(r.rewardAmount,null);
  assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');
 }
 assert.equal(data.rules.find(r=>r.id==='sc_pi_overseas').duplicateOf,'rule_86e75835845ffbb5a367');
});
test('Esun digital e-card bonus caps are statement limits, not fixed gifts',()=>{
 const data=require('../../data.json');
 const ids=['rule_8807edb9cc0a7446a63a','rule_8e664cc6701709f25c11','rule_0574b56f47ff0e503186'];
 const rules=ids.map(id=>data.rules.find(r=>r.id===id));
 assert.deepEqual(rules.map(r=>r.needReg),[true,false,false]);
 for(const r of rules){
  assert.equal(r.rewardAmount,null);assert.equal(r.capAmount,250);assert.equal(r.capScope,'PROMO');
  assert.equal(r.capPeriod,'STATEMENT');assert.equal(r.validFrom,'2026-07-01');
  assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('Next Bank convenience offer is fixed N points and cannot rank as cash',()=>{
 const rule=require('../../data.json').rules.find(r=>r.id==='rule_ece0d2ee5916fccdb0fe');
 assert.equal(rule.promoRate,0);
 assert.equal(rule.rewardAmount,10);
 assert.equal(rule.rewardUnit,'points');
 assert.equal(rule.campaignCapAmount,210);
 assert.equal(rule.needReg,true);
 assert.equal(A.assessment(rule).level,'BLOCKED');
 assert.equal(A.calculate(rule,100).calculable,false);
});
test('expired O-Bank Lucky Money is one fixed 88 TWD multi-month benefit',()=>{
 const rule=require('../../data.json').rules.find(r=>r.id==='rule_229343b9772b7b044c12');
 assert.equal(rule.promoRate,0);
 assert.equal(rule.rewardAmount,88);
 assert.equal(rule.rewardUnit,'twd');
 assert.equal(rule.capPeriod,'CAMPAIGN');
 assert.equal(rule.spendBasis,'MULTI_MONTH_CUMULATIVE');
 assert.equal(rule.needReg,false);
 assert.deepEqual(rule.registrationMethods,[]);
 assert.ok(rule.applicationMethods.length);
 assert.equal(rule.quickSearchEligible,false);
});
test('HSBC app login and service actions do not appear as offer registration',()=>{
 const data=require('../../data.json');
 const appIds=['rule_47a58937296d266f1947','rule_7321d1cf917b19af0434','rule_d480574a89ad14beec9a','rule_ede6e42f7c869bb77e96','rule_9e44e2c771cdd2f31f36','rule_68bd7592f9bcc80456f4'];
 const find=id=>data.rules.find(r=>r.id===id);
 for(const id of appIds){const r=find(id);assert.ok(r.appLoginRequirement);assert.deepEqual(r.registrationMethods,[]);assert.equal(r.quickSearchEligible,false);}
 const installment=find('rule_f34ef295f82e5da66608');
 assert.match(installment.applicationMethods[0].label,/申辦/);
 assert.deepEqual(installment.registrationMethods,[]);
 for(const id of ['rule_fa6ce36b01a5927f26e8','rule_0f612849011eb074fcee']){
  const r=find(id);assert.ok(r.bookingMethods.length);assert.equal(r.registrationUrl,'');assert.deepEqual(r.registrationMethods,[]);assert.ok(r.validationIssues.includes('BOOKING_DESTINATIONS_NEED_RECHECK'));
 }
});
test('airport service booking links are not registration links',()=>{
 const data=require('../../data.json');
 for(const id of ['rule_75661eedf72783c7f272','rule_7ca28b718202881a8c5e','rule_4026053d9565e18e8223']){
   const rule=data.rules.find(r=>r.id===id);
   assert.ok(rule.bookingUrl.startsWith('https://www.youfirst.com.tw/'));
   assert.equal(rule.needReg,false);
   assert.equal(rule.registrationUrl,'');
   assert.deepEqual(rule.registrationMethods,[]);
   assert.equal(rule.bookingSourceEvidence.sourceUrl,rule.sourceUrl);
 }
});
test('icash Pay issuer offers keep Esun registration separate and remain blocked',()=>{
 const data=require('../../data.json');
 const ids=['rule_e5062b26fc4d515cb603','icashpay_wanjiafu_2026_cathay','icashpay_wanjiafu_2026_hncb','icashpay_wanjiafu_2026_hsbc'];
 const rules=ids.map(id=>data.rules.find(r=>r.id===id));
 assert.ok(rules.every(Boolean));
 assert.deepEqual(rules.map(r=>r.needReg),[true,false,false,false]);
 assert.ok(rules.every(r=>r.fundingMethods.length===1&&r.rewardAmount===null&&r.capAmount===150&&r.validationIssues.length>0));
 assert.ok(rules.slice(1).every(r=>!r.registrationMethods.length&&!r.registrationUrl));
 assert.equal(rules[0].eligibleDateRanges.length,13);
});
test('auto-signing snapshots cannot replace official review evidence',()=>{
 const r={sourceUrl:'https://bank.test/terms',baseRate:99};
 r.accuracyReview={status:'SOURCE_CHECKED',sourceUrl:r.sourceUrl,fields:['baseRate'],checkedAt:'2026-11-02T00:00:00+08:00',termsSnapshot:A.termsSnapshot(r)};
 assert.equal(A.isReviewed(r,new Date('2026-11-02T12:00:00+08:00')),false);
});
test('incident recovery restores only incident edits and is idempotent',()=>{
 const before={rules:[{id:'a',cardId:null,sourceUrl:'',validationIssues:['WRONG_CARD']}]};
 const after={rules:[{id:'a',cardId:'first-bank-card',sourceUrl:'https://bank.test',validationIssues:[],accuracyReview:{status:'SOURCE_CHECKED'}}]};
 const current=structuredClone(after); current.rules[0].title='Later user edit';
 assert.equal(recover(current,before,after).length,1);
 assert.equal(current.rules[0].cardId,null);assert.equal(current.rules[0].title,'Later user edit');
 assert.equal(current.rules[0].sourceUrl,'');assert.equal(recover(current,before,after).length,0);
});
test('later independent corrections are not rolled back',()=>{
 const before={rules:[{id:'a',cardId:null}]},after={rules:[{id:'a',cardId:'wrong'}]},current={rules:[{id:'a',cardId:'correct'}]};
 assert.equal(recover(current,before,after).length,0);assert.equal(current.rules[0].cardId,'correct');
});
test('daily workflow cannot reapprove hardcoded historical reviews',()=>{
 const text=require('node:fs').readFileSync(require('node:path').join(__dirname,'../workflows/daily_crawler.yml'),'utf8');
 assert.doesNotMatch(text,/node .*review_(ubear|unicard)\.cjs/);
});
