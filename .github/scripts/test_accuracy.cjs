const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const A = require('../../accuracy-core.js');
const flat = {rewardType:'percent', baseRate:1, promoRate:2, rewardCalculationMode:'FLAT', roundingMode:'FLOOR_COMPONENT', capAmount:150, capScope:'PROMO', capPeriod:'MONTHLY'};
test('official U Bear component rounding: 6666 => 66 + 133', () => assert.equal(A.calculate(flat,6666).totalCash,199));
test('official U Bear component rounding: 133 => 1 + 2', () => assert.equal(A.calculate(flat,133).totalCash,3));
test('promo cap leaves base reward intact', () => assert.equal(A.calculate(flat,10000).totalCash,250));
test('used cap applies to remaining allowance', () => assert.equal(A.calculate({...flat,remainingCap:20},10000).totalCash,120));
test('zero cap is not unlimited', () => assert.equal(A.calculate({...flat,capAmount:0},10000).totalCash,100));
test('total cap includes base', () => assert.equal(A.calculate({...flat,capScope:'TOTAL'},10000).totalCash,150));
test('unknown cap scope refuses cash estimate', () => assert.equal(A.calculate({...flat,capScope:''},1000).calculable,false));
test('minimum spend is enforced', () => assert.equal(A.calculate({...flat,minimumSpend:1000},999).potentialCash,0));
test('cumulative threshold is not inferred from one transaction', () => assert.equal(A.calculate({...flat,quotaInfo:'累積滿 1000'},2000).calculable,false));
test('tier total is never added to promo again', () => {
 const r=A.calculate({...flat,rewardCalculationMode:'TIERED',rewardTiers:[{totalRate:2,baseRate:1,isDefault:true},{totalRate:3,baseRate:1,requirements:['VIP']}]},1000);
 assert.equal(r.totalCash,20); assert.equal(r.potentialCash,30); assert.equal(r.effectiveRate,2);
});
test('conditional tier is not treated as default', () => assert.equal(A.calculate({...flat,rewardCalculationMode:'TIERED',rewardTiers:[{totalRate:3,isDefault:true,requirements:['VIP']}]},1000).totalCash,0));
test('MAX_ONLY cannot yield guaranteed cash', () => { const r=A.calculate({...flat,rewardCalculationMode:'MAX_ONLY'},1000); assert.equal(r.totalCash,0);assert.equal(r.calculable,false); });
for (const type of ['draw','installment','insurance_benefit']) test(type+' cannot rank as cash',()=>assert.equal(A.calculate({...flat,rewardType:type,rewardAmount:10000},1000).potentialCash,0));
test('unknown-value points are not cash',()=>assert.equal(A.calculate({...flat,rewardType:'points',rewardUnit:'miles'},1000).calculable,false));
test('fixed points are not converted into a linear percentage',()=>assert.equal(A.calculate({...flat,baseRate:0,promoRate:0,capAmount:null,rewardType:'points',rewardUnit:'twd',rewardAmount:45,minimumSpend:1000,spendBasis:'PER_TRANSACTION'},2000).potentialCash,45));
test('invalid dates are rejected',()=>{for(const d of ['2026-02-30','2026-13-01','2026-09-01T24:00'])assert.equal(A.date(d),null)});
test('Taipei end-of-day is independent of system timezone',()=>assert.equal(A.date('2026-09-30',true).toISOString(),'2026-09-30T15:59:59.999Z'));
test('deadline alone is not an opening date',()=>assert.equal(A.lifecycle({regDeadline:'2026-10-01'},new Date('2026-09-29T00:00Z')),'unknown'));
test('unknown dates do not mean open registration',()=>assert.equal(A.lifecycle({regDeadline:'依官方公告'}),'unknown'));
test('future date range is upcoming',()=>assert.equal(A.lifecycle({regDeadline:'2026-10-01~2026-10-31'},new Date('2026-09-29T00:00Z')),'upcoming'));
test('expired marked registration is still expired',()=>assert.equal(A.lifecycle({registered:true,validUntil:'2026-01-01'}),'expired'));
test('recurring marks expire at Taipei month boundary',()=>{const r={id:'r',regDeadline:'每月1日開放'};assert.notEqual(A.periodKey(r,new Date('2026-09-30T15:59Z')),A.periodKey(r,new Date('2026-09-30T16:00Z')))});
test('campaign changes invalidate marks',()=>assert.notEqual(A.periodKey({id:'r',validUntil:'2026-09-30'}),A.periodKey({id:'r',validUntil:'2026-10-31'})));
test('HTML inline scripts compile',()=>{const html=fs.readFileSync(require('node:path').join(__dirname,'../../index.html'),'utf8'); for(const m of html.matchAll(/<script(?![^>]*src=)[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(m[1]);});
test('deployed engine matches tested engine',()=>{const p=require('node:path');const html=fs.readFileSync(p.join(__dirname,'../../index.html'),'utf8').replace(/\r\n/g,'\n');const core=fs.readFileSync(p.join(__dirname,'../../accuracy-core.js'),'utf8').replace(/\r\n/g,'\n');assert.ok(html.includes(core.trim()));});
test('independent reviews expire and must match the source',()=>{
 const r={sourceUrl:'https://bank.test/offer',accuracyReview:{status:'SOURCE_CHECKED',sourceUrl:'https://bank.test/offer',fields:['baseRate'],checkedAt:'2026-09-01T00:00:00Z'}};
 r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 assert.ok(A.isReviewed(r,new Date('2026-09-02T00:00Z')));
 assert.equal(A.isReviewed(r,new Date('2026-09-20T00:00Z')),false);
 r.sourceUrl='https://bank.test/other';assert.equal(A.isReviewed(r,new Date('2026-09-02T00:00Z')),false);
});
test('changed terms invalidate review even at same URL',()=>{
 const r={...flat,sourceUrl:'https://bank.test/offer',accuracyReview:{status:'SOURCE_CHECKED',sourceUrl:'https://bank.test/offer',fields:['baseRate'],checkedAt:'2026-10-02T00:00:00Z'}};
 r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 assert.equal(A.isReviewed(r,new Date('2026-10-03T00:00Z')),true);
 r.promoRate=20;assert.equal(A.isReviewed(r,new Date('2026-10-03T00:00Z')),false);
});
test('percentage points without exchange evidence are not cash',()=>assert.equal(A.calculate({...flat,rewardType:'points',rewardUnit:'percent'},2000).calculable,false));
test('structured cumulative threshold is never a single purchase',()=>assert.equal(A.calculate({...flat,spendBasis:'CAMPAIGN',minimumSpend:6000},10000).calculable,false));
test('expired offers cannot yield a reward estimate',()=>assert.equal(A.calculate({...flat,validUntil:'2020-01-01'},2000).calculable,false));
test('future offers cannot yield a current reward estimate',()=>assert.equal(A.calculate({...flat,validFrom:'2099-01-01'},2000).calculable,false));
test('review snapshots include the search scope, not only reward numbers',()=>{
 const r={searchKeywords:'LINE Pay',accuracyReview:{}};r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 assert.equal(A.reviewMatches(r),true);r.searchKeywords='海外';assert.equal(A.reviewMatches(r),false);
});
test('reviewed Unicard separates scheme total, cap and point value',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(r=>r.id==='review_unicard_linepay_202610');
 assert.ok(r); assert.equal(A.calculate(r,2000).potentialCash,90);
 assert.equal(A.calculate(r,2000).totalCash,0); // e-bill, debit and scheme are not confirmed by this app.
 assert.equal(A.calculate(r,2000).potentialRate,4.5);
 assert.equal(A.calculate({...r,remainingCap:0},2000).potentialCash,20);
 assert.equal(A.calculate(r,149).potentialCash,6); // basic round(1.49) + bonus round(5.215)
});
test('offline utilities are bundled',()=>{const html=fs.readFileSync(require('node:path').join(__dirname,'../../index.html'),'utf8');assert.ok(html.includes('id="compiled-utilities"'));assert.ok(!html.includes('<script src="https://cdn.tailwindcss.com">'));});
test('having a source is useful reference, not automatic factual approval',()=>{
 const r={...flat,sourceUrl:'https://bank.test/offer',title:'最高3%回饋'};
 assert.equal(A.assessment(r).level,'REFERENCE');assert.equal(A.assessment(r).cashAllowed,false);
 assert.equal(A.referenceReward(r),'最高 3%（資料列示）');
});
test('cash cap is not presented as a fixed gift and zero points are not promoted',()=>{
 assert.equal(A.referenceReward({rewardType:'cash',rewardAmount:150,capAmount:150}),'活動優惠（條件待補）');
 assert.equal(A.referenceReward({rewardType:'points',rewardAmount:0,rewardUnit:'points'}),'活動優惠（條件待補）');
});
test('conflicts and changed official sources stop numeric recommendation',()=>{
 assert.equal(A.assessment({sourceUrl:'https://bank.test',accuracyReview:{status:'CONFLICT'}}).level,'BLOCKED');
 assert.equal(A.assessment({sourceUrl:'https://bank.test',accuracyReview:{status:'RECHECK_REQUIRED'}}).level,'BLOCKED');
 assert.equal(A.referenceReward({title:'旅遊保險',rewardType:'cash',rewardAmount:3190000}),'保險保障，非刷卡回饋');
});
