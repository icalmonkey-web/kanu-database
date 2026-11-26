const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const A = require('../../accuracy-core.js');
const flat = {rewardType:'percent', baseRate:1, promoRate:2, rewardCalculationMode:'FLAT', roundingMode:'FLOOR_COMPONENT', capAmount:150, capScope:'PROMO', capPeriod:'MONTHLY'};
test('disjoint eligible dates exclude gaps and include Taipei date boundaries',()=>{
 const rule={...flat,validFrom:'2026-11-01',validUntil:'2026-11-30',eligibleDateRanges:[['2026-11-10','2026-11-11'],{from:'2026-11-20',until:'2026-11-21'}]};
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-09T15:59:59Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-09T16:00:00Z')),'ELIGIBLE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-11T15:59:59Z')),'ELIGIBLE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-11T16:00:00Z')),'OUTSIDE');
 assert.equal(A.calculate(rule,1000,new Date('2026-11-15T04:00:00Z')).calculable,false);
 assert.match(A.calculate(rule,1000,new Date('2026-11-15T04:00:00Z')).reason,/不是指定活動日/);
 assert.equal(A.calculate(rule,1000,new Date('2026-11-10T04:00:00Z')).calculable,true);
 assert.equal(A.eligibleDateStatus({...rule,eligibleDateRanges:[['2026-11-31','2026-12-01']]},new Date('2026-11-10T04:00:00Z')),'UNKNOWN');
});
test('eligible weekdays use Taipei day boundaries and reject invalid schedules',()=>{
 const rule={eligibleWeekdays:[0]};
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-07T15:59:59Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-07T16:00:00Z')),'ELIGIBLE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-08T15:59:59Z')),'ELIGIBLE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-08T16:00:00Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus({...rule,eligibleWeekdays:[7]},new Date('2026-11-08T00:00:00Z')),'UNKNOWN');
 assert.equal(A.eligibleDateStatus({...rule,eligibleWeekdays:[0,0]},new Date('2026-11-08T00:00:00Z')),'UNKNOWN');
 assert.equal(A.eligibleDateStatus({...rule,eligibleDateRanges:[['2026-11-01','2026-11-07']]},new Date('2026-11-08T00:00:00Z')),'OUTSIDE');
});
test('monthly start day combines with weekday and Taipei midnight',()=>{
 const rule={...flat,eligibleMonthDayFrom:10,eligibleWeekdays:[5,6,0]};
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-06T04:00:00Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-08T15:59:59Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-13T04:00:00Z')),'ELIGIBLE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-12T16:00:00Z')),'ELIGIBLE');
 assert.equal(A.calculate(rule,1000,new Date('2026-11-06T04:00:00Z')).calculable,false);
 assert.equal(A.eligibleDateStatus({...rule,eligibleMonthDayFrom:0},new Date('2026-11-13T04:00:00Z')),'UNKNOWN');
 assert.equal(A.eligibleDateStatus({...rule,eligibleMonthDayFrom:32},new Date('2026-11-13T04:00:00Z')),'UNKNOWN');
});
test('excluded date ranges block exact Taipei days and reject malformed dates',()=>{
 const rule={...flat,excludedDateRanges:[['2026-12-24','2026-12-25']]};
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-12-23T15:59:59Z')),'ELIGIBLE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-12-23T16:00:00Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-12-25T15:59:59Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-12-25T16:00:00Z')),'ELIGIBLE');
 assert.equal(A.calculate(rule,1000,new Date('2026-12-24T04:00:00Z')).calculable,false);
 assert.equal(A.eligibleDateStatus({...rule,excludedDateRanges:[['2026-12-31','2026-12-30']]},new Date('2026-12-24T04:00:00Z')),'UNKNOWN');
 assert.equal(A.eligibleDateStatus({...rule,excludedDateRanges:[]},new Date('2026-12-24T04:00:00Z')),'UNKNOWN');
});
test('a reviewed weekday offer needs a sourced schedule field',()=>{
 const r={sourceUrl:'https://bank.test/sunday',eligibleWeekdays:[0],
   accuracyReview:{...provenance,evidenceSources:['https://bank.test/sunday'],status:'SOURCE_CHECKED',sourceUrl:'https://bank.test/sunday',
     fields:['schedule'],checkedAt:'2026-11-07T00:00:00Z'}};
 r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 r.termEvidence=proofFor(r,'2026-11-07T00:00:00Z');
 const sunday=new Date('2026-11-08T04:00:00Z');
 assert.equal(A.isReviewed(r,sunday),false);
 r.termEvidence.fields.schedule={status:'supported',sourceUrl:r.sourceUrl,locator:'Official terms: Sundays'};
 assert.equal(A.isReviewed(r,sunday),true);
 assert.equal(A.isReviewed(r,new Date('2026-11-09T04:00:00Z')),false);
});
test('reviewed LG and KKday offers respect official weekdays',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const lg=data.rules.find(r=>r.id==='rule_0056b90e9684f6396cb5');
 const kkday=data.rules.find(r=>r.id==='rule_d1385d908fb4b07473ef');
 assert.deepEqual(lg.eligibleWeekdays,[1,2,3,4,5]);
 assert.deepEqual(kkday.eligibleWeekdays,[4]);
 assert.equal(A.isReviewed(lg,new Date('2026-11-05T04:00:00Z')),true);
 assert.equal(A.isReviewed(kkday,new Date('2026-11-05T04:00:00Z')),true);
 assert.equal(A.isReviewed(lg,new Date('2026-11-07T04:00:00Z')),false);
 assert.equal(A.isReviewed(kkday,new Date('2026-11-06T04:00:00Z')),false);
});
const provenance={method:'official_terms_read',evidence:'Official terms, reward section',evidenceSources:['https://bank.test/offer']};
const proofFor=(r,checkedAt)=>({method:'manual_official_terms_read',sourceUrl:r.sourceUrl,checkedAt,fields:Object.fromEntries(['title','cardEligibility','reward','rewardType','validFrom','validUntil','cap','minimumSpend','registration','exclusions','rounding'].map(field=>[field,{status:'supported',sourceUrl:r.sourceUrl,locator:'Official terms: '+field}]))});
test('Great Tree mixed points and coupon are not ranked as a flat percentage',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const id of ['lp-greattree-pharmacy','rule_9c6ffc76a3ac58fdda9c','rule_4a815ab4479aa69a6253','rule_repaired_7ebc83efb4827b644354']){
  const rule=data.rules.find(r=>r.id===id);
  assert.ok(rule,id);
  assert.equal(rule.quickSearchEligible,false);
  assert.equal(rule.rewardType,'points');
  assert.equal(rule.promoRate,1);
  assert.equal(rule.rewardAmount,null);
  assert.equal(rule.capAmount,60);
  assert.deepEqual(rule.eligibleWeekdays,[3,6]);
  assert.ok(rule.validationIssues.includes('OFFICIAL_LIST_DETAIL_RATE_CONFLICT'));
 }
});
test('LOPIA Wednesday and Thursday offer cannot rank as cash before full review',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(r=>r.id==='review_linepay_lopia_2026q4');
 assert.ok(rule);
 assert.deepEqual(rule.eligibleWeekdays,[3,4]);
 assert.equal(rule.minimumSpend,700);
 assert.equal(rule.quickSearchEligible,false);
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-06T04:00:00Z')),'OUTSIDE');
});
test('GoAmazing card points and checkout code have separate periods and cannot rank as cash',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const byId=id=>data.rules.find(r=>r.id===id);
 const points=byId('rule_414f177bc95a5bcc3ad1');
 const code=byId('review_ctbc_goamazing_code_2026_pending');
 assert.ok(points&&code);
 assert.deepEqual([points.validFrom,points.validUntil],['2026-05-01','2026-12-31']);
 assert.deepEqual([code.validFrom,code.validUntil],['2026-10-07','2026-11-30']);
 assert.equal(points.rewardType,'points');
 assert.equal(code.rewardType,'discount');
 assert.equal(points.minimumSpend,0);
 assert.equal(code.minimumSpend,2000);
 assert.equal(points.quickSearchEligible,false);
 assert.equal(code.quickSearchEligible,false);
});
test('icash Sunday points cap is not a fixed 200 point reward',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(r=>r.id==='rule_89b5c2182f6e449769ba');
 assert.ok(rule);
 assert.equal(rule.rewardType,'points');
 assert.equal(rule.rewardAmount,null);
 assert.equal(rule.rewardUnit,'percent');
 assert.equal(rule.capAmount,200);
 assert.equal(rule.minimumSpend,200);
  assert.deepEqual(rule.eligibleWeekdays,[0]);
 assert.equal(rule.quickSearchEligible,false);
 assert.ok(rule.validationIssues.includes('SUNDAY_ONLY_AND_LIVE_QUOTA_NOT_MACHINE_CHECKED'));
});
test('Cosmed Monday 200 points is a monthly cap in both legacy records',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const id of ['rule_7647a98b1201fe830bb0','rule_b14bca5c6b9f02338f6f']){
  const rule=data.rules.find(r=>r.id===id);
  assert.ok(rule);
  assert.deepEqual(rule.eligibleWeekdays,[1]);
  assert.equal(rule.rewardType,'points');
  assert.equal(rule.rewardUnit,'percent');
  assert.equal(rule.rewardAmount,null);
  assert.equal(rule.capAmount,200);
  assert.equal(rule.quickSearchEligible,false);
  assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-06T04:00:00Z')),'OUTSIDE');
 }
});
test('KFC and Pizza Hut Sunday offers retain separate spend thresholds',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const [id,spend] of [['review_icashpay_sunday_food_2026_kfc',399],['review_icashpay_sunday_food_2026_pizza_hut',599]]){
  const rule=data.rules.find(r=>r.id===id);
  assert.ok(rule);
  assert.equal(rule.minimumSpend,spend);
  assert.deepEqual(rule.eligibleWeekdays,[0]);
  assert.equal(rule.rewardAmount,null);
  assert.equal(rule.capAmount,100);
  assert.equal(rule.capPeriod,'CAMPAIGN');
  assert.equal(rule.quickSearchEligible,false);
 }
});
test('Wanjiafu base, uniopen and issuer bonuses stay separate and blocked before day ten',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const id of ['review_icashpay_wanjiafu_2026_base','review_icashpay_wanjiafu_2026_uniopen',
                  'icashpay_wanjiafu_2026_cathay','icashpay_wanjiafu_2026_hncb','icashpay_wanjiafu_2026_hsbc']){
  const rule=data.rules.find(r=>r.id===id);
  assert.ok(rule);
  assert.deepEqual(rule.eligibleWeekdays,[5,6,0]);
  assert.equal(rule.eligibleMonthDayFrom,10);
  assert.equal(rule.rewardType,'points');
  assert.equal(rule.promoRate,5);
  assert.equal(rule.capAmount,150);
  assert.equal(rule.quickSearchEligible,false);
 }
 assert.notEqual(data.rules.find(r=>r.id==='review_icashpay_wanjiafu_2026_base').id,
                 data.rules.find(r=>r.id==='review_icashpay_wanjiafu_2026_uniopen').id);
});
test('new icash Pay official offers keep caps, weekdays and lottery separate from guaranteed reward',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const get=id=>data.rules.find(r=>r.id===id);
 const ikari=get('review_icashpay_ikari_2026');
 assert.equal(ikari.minimumSpend,200);
 assert.equal(ikari.capAmount,50);
 assert.equal(ikari.quickSearchEligible,false);
 const bowls=get('review_icashpay_500bowls_2026');
 assert.deepEqual(bowls.eligibleWeekdays,[5,6,0]);
 assert.equal(A.eligibleDateStatus(bowls,new Date('2026-11-09T04:00:00Z')),'OUTSIDE');
 assert.equal(bowls.capPeriod,'MONTHLY');
 assert.equal(bowls.quickSearchEligible,false);
 const draw=get('review_icashpay_postoffice_draw_2026');
 assert.equal(draw.rewardType,'draw');
 assert.equal(draw.spendBasis,'CUMULATIVE');
 assert.equal(draw.needReg,true);
 assert.equal(A.calculate(draw,350,new Date('2026-11-05T04:00:00Z')).calculable,false);
 assert.equal(draw.quickSearchEligible,false);
});
test('Taia fuel and ETmall are distinct icash Pay point offers with their own caps',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const taia=data.rules.find(r=>r.id==='review_icashpay_taia_fuel_2026');
 const etmall=data.rules.find(r=>r.id==='review_icashpay_etmall_2026');
 assert.equal(taia.promoRate,2.5);
 assert.equal(taia.capAmount,100);
 assert.equal(taia.campaignCapAmount,500000);
 assert.match(taia.title,/人工島/);
 assert.equal(taia.quickSearchEligible,false);
 assert.equal(etmall.minimumSpend,1000);
 assert.equal(etmall.promoRate,5);
 assert.equal(etmall.capAmount,250);
 assert.equal(etmall.capPeriod,'MONTHLY');
 assert.equal(etmall.rewardType,'points');
 assert.equal(etmall.quickSearchEligible,false);
});
test('icash2.0 auto reload is a monthly registration with exhausted November pool, not a purchase reward',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(r=>r.id==='rule_c2608a63f2e39c6340bb');
 assert.equal(rule.sourceUrl,'https://www.icash.com.tw/Home/NewsDetail/?ID=12880');
 assert.equal(rule.validFrom,'2026-07-01');
 assert.equal(rule.registrationCycle,'MONTHLY');
 assert.equal(rule.rewardAmount,null);
 assert.equal(rule.minimumSpend,500);
 assert.ok(rule.validationIssues.includes('NOVEMBER_2026_POOL_EXHAUSTED'));
 assert.equal(rule.quickSearchEligible,false);
 assert.equal(A.calculate(rule,500,new Date('2026-11-05T04:00:00Z')).calculable,false);
});
test('21Plus bundle is a 99 dollar product discount with excluded dates, never cash back',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(r=>r.id==='review_icash_21plus_meal_2026');
 assert.equal(rule.rewardType,'discount');
 assert.equal(rule.bundlePriceAmount,99);
 assert.equal(rule.promoRate,0);
 assert.ok(rule.excludedKeywords.includes('2026-12-24'));
 assert.deepEqual(rule.excludedDateRanges,[['2026-12-24','2026-12-24'],['2026-12-25','2026-12-25'],['2026-12-31','2026-12-31']]);
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-12-24T04:00:00Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-12-26T04:00:00Z')),'ELIGIBLE');
 assert.equal(rule.quickSearchEligible,false);
 assert.equal(A.calculate(rule,165,new Date('2026-11-05T04:00:00Z')).calculable,false);
});
test('DREAM PLAZA existing record uses Tuesday and weekly point cap from current official listing',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(r=>r.id==='rule_013375e0585b4bb72251');
 assert.equal(rule.validFrom,'2026-01-01');
 assert.deepEqual(rule.eligibleWeekdays,[2]);
 assert.equal(rule.capPeriod,'WEEKLY');
 assert.equal(rule.capAmount,100);
 assert.equal(rule.minimumSpend,899);
 assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-04T04:00:00Z')),'OUTSIDE');
 assert.equal(rule.quickSearchEligible,false);
});
test('November TWQR cross merchant points are conditional and separate from the expired listing',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const old=data.rules.find(r=>r.id==='rule_730beab079a8ada2bef0');
 const current=data.rules.find(r=>r.id==='review_icashpay_twqr_novdec_2026_listing');
 assert.equal(old.validUntil,'2026-10-31');
 assert.equal(current.validFrom,'2026-11-01');
 assert.equal(current.rewardAmount,null);
 assert.equal(current.capAmount,40);
 assert.equal(current.minimumSpend,50);
 assert.equal(current.spendBasis,'CROSS_MERCHANT_MONTHLY');
 assert.equal(current.quickSearchEligible,false);
 assert.equal(A.calculate(current,50,new Date('2026-11-05T04:00:00Z')).calculable,false);
});
test('mobile tea offers keep two product discounts distinct and only on four official Tuesdays',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const ice=data.rules.find(r=>r.id==='review_mobile_tea_ice_2026_listing');
 const pearl=data.rules.find(r=>r.id==='review_mobile_tea_pearl_2026_listing');
 assert.equal(ice.rewardType,'discount');
 assert.equal(ice.buyQuantity,2);
 assert.equal(ice.freeQuantity,2);
 assert.equal(pearl.bundlePriceAmount,88);
 assert.equal(pearl.rewardType,'discount');
 for(const rule of [ice,pearl]){
  assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-10T04:00:00Z')),'ELIGIBLE');
  assert.equal(A.eligibleDateStatus(rule,new Date('2026-11-11T04:00:00Z')),'OUTSIDE');
  assert.equal(rule.quickSearchEligible,false);
  assert.equal(A.calculate(rule,100,new Date('2026-11-10T04:00:00Z')).calculable,false);
 }
});
test('official U Bear component rounding: 6666 => 66 + 133', () => assert.equal(A.calculate(flat,6666).totalCash,199));
test('official U Bear component rounding: 133 => 1 + 2', () => assert.equal(A.calculate(flat,133).totalCash,3));
test('promo cap leaves base reward intact', () => assert.equal(A.calculate(flat,10000).totalCash,250));
test('used cap applies to remaining allowance', () => assert.equal(A.calculate({...flat,remainingCap:20},10000).totalCash,120));
test('zero cap is not unlimited', () => assert.equal(A.calculate({...flat,capAmount:0},10000).totalCash,100));
test('total cap includes base', () => assert.equal(A.calculate({...flat,capScope:'TOTAL'},10000).totalCash,150));
test('unknown cap scope refuses cash estimate', () => assert.equal(A.calculate({...flat,capScope:''},1000).calculable,false));
test('minimum spend is enforced', () => assert.equal(A.calculate({...flat,minimumSpend:1000},999).potentialCash,0));
test('cumulative threshold is not inferred from one transaction', () => assert.equal(A.calculate({...flat,quotaInfo:'累積滿 1000'},2000).calculable,false));
test('HSBC statement-aggregated cash points are not estimated from a single purchase',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));for(const id of ['rule_b976c4a9577d484419b6','rule_700a5c10e2380bc2df84','rule_578a5d7f1307b489e5c1']){const r=d.rules.find(x=>x.id===id);assert.ok(r);assert.equal(r.spendBasis,'STATEMENT');assert.equal(r.pointValueTwd,1);assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,10000).calculable,false)}});
test('HSBC domestic term review has all eleven source locators and stays out of per-purchase ranking',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const r=d.rules.find(x=>x.id==='rule_b976c4a9577d484419b6');const reviewedAt=new Date('2026-11-05T04:00:00Z');assert.ok(r);assert.equal(Object.keys(r.termEvidence.fields).length,11);assert.equal(A.assessment(r,reviewedAt).level,'CHECKED');assert.equal(A.assessment(r,new Date('2026-11-26T04:00:00Z')).level,'REFERENCE');assert.equal(A.assessment(r,new Date('2026-11-26T04:00:00Z')).reviewExpired,true);assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,10000,reviewedAt).calculable,false);assert.equal(A.isReviewed({...r,baseRate:2},reviewedAt),false)});
test('HSBC overseas rate remains blocked until FX-fee and physical-store conditions can be checked',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const r=d.rules.find(x=>x.id==='rule_700a5c10e2380bc2df84');assert.ok(r);assert.equal(r.baseRate,2.22);assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');assert.match(r.benefitSummary,/國外交易手續費/);assert.match(r.benefitSummary,/實體商店/);assert.equal(A.calculate(r,10000).calculable,false)});
test('Mega partner offers use official issuer-wide card scope and never masquerade as cash',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));for(const id of ['rule_06','rule_07','rule_08']){const r=d.rules.find(x=>x.id===id);assert.ok(r);assert.equal(r.associationStatus,'issuer_wide_official');assert.equal(r.eligibleCardScope,'ALL_BANK_CARDS');assert.ok(!r.unresolvedCardId);assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,1000).calculable,false)}assert.equal(d.rules.find(x=>x.id==='rule_06').minimumSpend,499);assert.equal(d.rules.find(x=>x.id==='rule_06').rewardType,'coupon');assert.equal(d.rules.find(x=>x.id==='rule_07').validUntil,'2025-12-31');assert.equal(d.rules.find(x=>x.id==='rule_08').rewardType,'mixed_benefit')});
test('Esun digital insurance single-pay review is distinct from installment registration',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const r=d.rules.find(x=>x.id==='rule_digital_insurance');const reviewedAt=new Date('2026-11-05T04:00:00Z');assert.ok(r);assert.equal(r.cardId,'card_玉山銀行_103');assert.ok(!r.unresolvedCardId);assert.equal(r.baseRate,1.2);assert.equal(r.promoRate,0);assert.equal(r.needReg,false);assert.equal(r.roundingMode,'FLOOR');assert.equal(Object.keys(r.termEvidence.fields).length,11);assert.equal(A.assessment(r,reviewedAt).level,'CHECKED');assert.equal(A.assessment(r,new Date('2026-11-26T04:00:00Z')).level,'REFERENCE');assert.equal(r.quickSearchEligible,false);for(const id of ['rule_world_infinite_insurance','rule_nanshan_insurance'])assert.equal(A.assessment(d.rules.find(x=>x.id===id),reviewedAt).level,'BLOCKED')});
test('tier total is never added to promo again', () => {
 const r=A.calculate({...flat,rewardCalculationMode:'TIERED',rewardTiers:[{totalRate:2,baseRate:1,isDefault:true},{totalRate:3,baseRate:1,requirements:['VIP']}]},1000);
 assert.equal(r.totalCash,20); assert.equal(r.potentialCash,30); assert.equal(r.effectiveRate,2);
});
test('conditional tier is not treated as default', () => assert.equal(A.calculate({...flat,rewardCalculationMode:'TIERED',rewardTiers:[{totalRate:3,isDefault:true,requirements:['VIP']}]},1000).totalCash,0));
test('MAX_ONLY cannot yield guaranteed cash', () => { const r=A.calculate({...flat,rewardCalculationMode:'MAX_ONLY'},1000); assert.equal(r.totalCash,0);assert.equal(r.calculable,false); });
for (const type of ['draw','installment','insurance_benefit']) test(type+' cannot rank as cash',()=>assert.equal(A.calculate({...flat,rewardType:type,rewardAmount:10000},1000).potentialCash,0));
for (const type of ['discount','coupon','mixed_benefit']) test(type+' cannot rank as cash',()=>assert.equal(A.calculate({...flat,rewardType:type,rewardAmount:10000},1000).calculable,false));
test('CTBC restaurant discount stays a sourced reference without cashback',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const r=d.rules.find(x=>x.id==='review_ctbc_linepay_caesar_202609');assert.ok(r);assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,2000).calculable,false);assert.equal(A.assessment(r).level,'REFERENCE');assert.match(A.referenceReward(r),/平日7折/) });
test('CTBC foodpanda coupon variants are separate discounts, not cash rewards or 1400 NTD caps',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const ids=['rule_08a40a8180ff16448a91','rule_3d990c1ffca1103a85f3','review_ctbc_foodpanda_first_grocery_2026','review_ctbc_foodpanda_breakfast_2026'];const expected=[[260,20],[99,200],[300,250],[200,15]];for(let i=0;i<ids.length;i++){const r=d.rules.find(x=>x.id===ids[i]);assert.ok(r);assert.equal(r.rewardType,'discount');assert.equal(r.minimumSpend,expected[i][0]);assert.equal(r.capAmount,expected[i][1]);assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,1000).calculable,false)}for(const id of ['rule_foodpanda','lp-foodpanda-discount','ctbc_lp_foodpanda'])assert.ok(!d.rules.some(x=>x.id===id))});
test('LINE Pay partner coupons and LOPIA are not misassigned to the CTBC card',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));for(const id of ['review_linepay_selected_hotels_2026h2','review_linepay_breakfast_coffee_coupon_2026q4','review_linepay_brand_restaurant_coupon_2026q4','review_linepay_lopia_2026q4']){const r=d.rules.find(x=>x.id===id);assert.ok(r);assert.equal(r.offerDomain,'PAYMENT');assert.equal(r.paymentProvider,'LINE Pay');assert.ok(!r.cardId);assert.equal(r.quickSearchEligible,id!=='review_linepay_lopia_2026q4');assert.equal(A.calculate(r,1000).calculable,false)}const lopia=d.rules.find(x=>x.id==='review_linepay_lopia_2026q4');assert.equal(lopia.minimumSpend,700);assert.equal(lopia.eligibleCardScope,'ALL_ISSUERS');assert.equal(A.assessment(lopia).level,'BLOCKED')});
test('ShopBack 4 percent is documented as mixed cashback and points with registration',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));for(const id of ['review_ctbc_shopback_pizzahut_2026h2','review_ctbc_shopback_kfc_2026h2']){const r=d.rules.find(x=>x.id===id);assert.ok(r);assert.equal(r.rewardType,'mixed_benefit');assert.equal(r.needReg,true);assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');assert.equal(A.calculate(r,1000).calculable,false);assert.match(r.benefitSummary,/現金回饋2%.*POINTS 2%/)}});
test('ShopBack shopping entries keep cash and points separate and require registration',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const keys=['popchill','mercari','skm','pchome','yahoo','friday','rakuten','eslite','iherb','myprotein','life_market','books','etmall','global_mall'];for(const key of keys){const r=d.rules.find(x=>x.id==='review_ctbc_shopback_'+key+'_2026h2');assert.ok(r,key);assert.equal(r.rewardType,'mixed_benefit');assert.equal(r.cardPointsRate,2);assert.ok(Math.abs(r.partnerCashbackRate+r.cardPointsRate-r.combinedRate)<1e-8);assert.equal(r.needReg,true);assert.equal(A.assessment(r).level,'BLOCKED');assert.equal(A.calculate(r,1000).calculable,false)}});
test('shopping page legacy records with absent listing or title stay quarantined',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const tao=d.rules.find(x=>x.id==='rule_fbadc5644cfad449e41d');const go=d.rules.find(x=>x.id==='rule_414f177bc95a5bcc3ad1');assert.equal(tao.capPeriod,'QUARTERLY');assert.equal(tao.registrationCycle,'QUARTERLY');assert.equal(A.assessment(tao).level,'BLOCKED');assert.equal(A.assessment(go).level,'BLOCKED')});
test('CTBC LINE Pay card merchant offers require quarterly registration without LINE Pay payment binding',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const expected=[['shopee',4,100],['uniqlo',9,200],['gu',9,200]];for(const [key,bonus,cap] of expected){const r=d.rules.find(x=>x.id==='review_ctbc_linepay_'+key+'_2026h2');assert.ok(r);assert.equal(r.paymentProvider,'');assert.equal(r.promoRate,bonus);assert.equal(r.capAmount,cap);assert.equal(r.capPeriod,'QUARTERLY');assert.equal(r.registrationCycle,'QUARTERLY');assert.equal(A.assessment(r).level,'BLOCKED')}});
test('unknown-value points are not cash',()=>assert.equal(A.calculate({...flat,rewardType:'points',rewardUnit:'miles'},1000).calculable,false));
test('fixed points are not converted into a linear percentage',()=>assert.equal(A.calculate({...flat,baseRate:0,promoRate:0,capAmount:null,rewardType:'points',rewardUnit:'twd',rewardAmount:45,minimumSpend:1000,spendBasis:'PER_TRANSACTION'},2000).potentialCash,45));
test('invalid dates are rejected',()=>{for(const d of ['2026-02-30','2026-13-01','2026-09-01T24:00'])assert.equal(A.date(d),null)});
test('Taipei end-of-day is independent of system timezone',()=>assert.equal(A.date('2026-09-30',true).toISOString(),'2026-09-30T15:59:59.999Z'));
test('deadline alone is not an opening date',()=>assert.equal(A.lifecycle({regDeadline:'2026-10-01'},new Date('2026-09-29T00:00Z')),'unknown'));
test('unknown dates do not mean open registration',()=>assert.equal(A.lifecycle({regDeadline:'依官方公告'}),'unknown'));
test('future date range is upcoming',()=>assert.equal(A.lifecycle({regDeadline:'2026-10-01~2026-10-31'},new Date('2026-09-29T00:00Z')),'upcoming'));
test('expired marked registration is still expired',()=>assert.equal(A.lifecycle({registered:true,validUntil:'2026-01-01'}),'expired'));
test('recurring marks expire at Taipei month boundary',()=>{const r={id:'r',regDeadline:'每月1日開放'};assert.notEqual(A.periodKey(r,new Date('2026-09-30T15:59Z')),A.periodKey(r,new Date('2026-09-30T16:00Z')))});
test('quarterly registrations persist within quarter and expire at Taipei quarter boundary',()=>{const r={id:'r',registrationCycle:'QUARTERLY'};assert.equal(A.periodKey(r,new Date('2026-10-01T00:00Z')),A.periodKey(r,new Date('2026-12-31T15:59Z')));assert.notEqual(A.periodKey(r,new Date('2026-12-31T15:59Z')),A.periodKey(r,new Date('2026-12-31T16:00Z')))});
test('every validation conflict blocks a recommendation',()=>{const r={sourceUrl:'https://bank.test/offer',validFrom:'2026-01-01',validUntil:'2026-12-31',validationIssues:['OFFICIAL_CAP_PERIOD_CONFLICT']};assert.equal(A.assessment(r).level,'BLOCKED')});
test('CTBC dining offers use official quarterly cap and registration cycle',()=>{const d=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));const ids=['rule_141a6550938b29d8ba13','rule_77b16b4262cd2c2704ad','rule_26ab533bf77c05b5133c','rule_1e1328f849591e9e8f10','rule_e74497743e60187f7f2a','rule_a7fcac04b54ea87a2f43'];for(const id of ids){const r=d.rules.find(x=>x.id===id);assert.ok(r);assert.equal(r.capPeriod,'QUARTERLY');assert.equal(r.registrationCycle,'QUARTERLY')}});
test('campaign changes invalidate marks',()=>assert.notEqual(A.periodKey({id:'r',validUntil:'2026-09-30'}),A.periodKey({id:'r',validUntil:'2026-10-31'})));
test('HTML inline scripts compile',()=>{const html=fs.readFileSync(require('node:path').join(__dirname,'../../index.html'),'utf8'); for(const m of html.matchAll(/<script(?![^>]*src=)[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(m[1]);});
test('deployed engine matches tested engine',()=>{const p=require('node:path');const html=fs.readFileSync(p.join(__dirname,'../../index.html'),'utf8').replace(/\r\n/g,'\n');const core=fs.readFileSync(p.join(__dirname,'../../accuracy-core.js'),'utf8').replace(/\r\n/g,'\n');assert.ok(html.includes(core.trim()));});
test('independent reviews expire and must match the source',()=>{
 const r={sourceUrl:'https://bank.test/offer',accuracyReview:{...provenance,status:'SOURCE_CHECKED',sourceUrl:'https://bank.test/offer',fields:['baseRate'],checkedAt:'2026-09-01T00:00:00Z'}};
 r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 r.termEvidence=proofFor(r,'2026-09-01T00:00:00Z');
 assert.ok(A.isReviewed(r,new Date('2026-09-02T00:00Z')));
 assert.equal(A.isReviewed(r,new Date('2026-09-20T00:00Z')),false);
 r.sourceUrl='https://bank.test/other';assert.equal(A.isReviewed(r,new Date('2026-09-02T00:00Z')),false);
});
test('changed terms invalidate review even at same URL',()=>{
 const r={...flat,sourceUrl:'https://bank.test/offer',accuracyReview:{...provenance,status:'SOURCE_CHECKED',sourceUrl:'https://bank.test/offer',fields:['baseRate'],checkedAt:'2026-10-02T00:00:00Z'}};
 r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 r.termEvidence=proofFor(r,'2026-10-02T00:00:00Z');
 assert.equal(A.isReviewed(r,new Date('2026-10-03T00:00Z')),true);
 r.promoRate=20;assert.equal(A.isReviewed(r,new Date('2026-10-03T00:00Z')),false);
});
test('percentage points without exchange evidence are not cash',()=>assert.equal(A.calculate({...flat,rewardType:'points',rewardUnit:'percent'},2000).calculable,false));
test('CTBC LG fixed bonus is not merged with the separate general-spend 1 percent',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='rule_0056b90e9684f6396cb5');
 assert.ok(A.isReviewed(r,new Date('2026-11-05T04:00:00Z')));assert.equal(r.rewardAmount,500);assert.equal(r.baseRate,0);
 assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,20000).calculable,false);
 assert.match(r.quotaInfo,/每月/);
});
test('CTBC Under Armour 200 points is a cap, not a fixed award',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='rule_04710b8837a6e3f2b94f');
 const reviewedAt=new Date('2026-11-05T04:00:00Z');
 assert.ok(A.isReviewed(r,reviewedAt));assert.equal(A.isReviewed(r,new Date('2026-11-26T04:00:00Z')),false);
 assert.equal(r.baseRate,1);assert.equal(r.promoRate,6);
 assert.equal(r.rewardAmount,null);assert.equal(r.capAmount,200);
 assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,10000,reviewedAt).calculable,false);
});
test('CTBC CASETiFY uses a monthly bonus cap and remains out of cash ranking',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='review_ctbc_casetify_2026q4');
 const reviewedAt=new Date('2026-11-05T04:00:00Z');
 assert.ok(A.isReviewed(r,reviewedAt));assert.equal(A.isReviewed(r,new Date('2026-11-26T04:00:00Z')),false);
 assert.equal(r.minimumSpend,2500);
 assert.equal(r.baseRate,1);assert.equal(r.promoRate,3);
 assert.equal(r.capAmount,200);assert.equal(r.capPeriod,'MONTHLY');
 assert.equal(r.quickSearchEligible,false);assert.equal(A.calculate(r,2500,reviewedAt).calculable,false);
});
test('short Adidas promotion stays blocked until quota and cap are verified',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='review_ctbc_adidas_2026_11_pending');
 assert.equal(r.minimumSpend,3900);
 assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');
 assert.equal(A.calculate(r,5200).calculable,false);
 assert.match(r.quotaInfo,/待查/);
});
test('KKday weekly coupon is not bank registration or a fixed 360 point award',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='rule_d1385d908fb4b07473ef');
 assert.ok(A.isReviewed(r,new Date('2026-11-05T04:00:00Z')));assert.equal(r.needReg,false);
 assert.equal(r.registrationUrl,'');assert.deepEqual(r.registrationMethods,[]);
 assert.equal(r.rewardAmount,null);assert.equal(r.capAmount,360);
 assert.equal(r.quickSearchEligible,false);
});
test('KKday member days remain blocked between disjoint date windows',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='review_ctbc_kkday_member_day_2026_pending');
 assert.equal(r.eligibleDateRanges.length,3);
 assert.equal(r.quickSearchEligible,false);assert.equal(A.assessment(r).level,'BLOCKED');
 assert.equal(A.calculate(r,10000).calculable,false);
});
test('CTBC overseas registration timing and cap are corrected but unresolved terms stay blocked',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='rule_a84722535184bc3700e1');
 assert.equal(r.rewardAmount,null);assert.equal(r.capAmount,450);
 assert.match(r.quotaInfo,/週二00:00/);assert.doesNotMatch(r.maxRateRequires.join(' '),/下午/);
 assert.ok(r.excludedCountries.includes('法國'));
 assert.ok(r.excludedCountries.includes('德國'));
 assert.ok(r.excludedCountries.includes('英國'));
 assert.equal(r.excludedCountries.length,31);
 assert.equal(r.registrationWindows.length,13);
 assert.equal(r.registrationWindows.find(w=>A.date(w.start)>new Date('2026-11-04T00:00:00Z')).start,
   '2026-11-10T00:00:00+08:00');
 assert.equal(r.registrationWindows.at(-1).start,'2026-12-29T00:00:00+08:00');
 assert.equal(r.registrationUrl,'');assert.deepEqual(r.registrationMethods,[]);
 assert.equal(A.assessment(r).level,'BLOCKED');
});
test('CTBC travel registration notices keep Visa and JCB opening times distinct',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const [id,network,hour,cap,cardId] of [
   ['review_ctbc_trip_registration_2026h2','Visa','10:00',100,'card_中國信託_241'],
   ['review_ctbc_airbnb_registration_2026h2','Visa','10:00',100,'card_中國信託_241'],
   ['review_ctbc_tigerair_registration_2026h2','JCB','13:00',200,'card_中國信託_242']]){
   const r=data.rules.find(x=>x.id===id);
   assert.ok(r);assert.match(r.title,new RegExp(network));assert.equal(r.cardId,cardId);
   assert.deepEqual(r.eligibleCardIds,network==='Visa'?['card_中國信託_241','card_中國信託_328']:['card_中國信託_242']);
   assert.equal(r.registrationCycle,'QUARTERLY');assert.equal(r.capPeriod,'QUARTERLY');
   assert.equal(r.capAmount,cap);assert.equal(r.registrationWindows.length,6);
   assert.equal(r.registrationWindows[4].start,`2026-11-06T${hour}:00+08:00`);
   assert.equal(r.registrationUrl,'');assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('CTBC ShopBack offers are linked to Visa credit card rather than generic LINE Pay card',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const offers=data.rules.filter(r=>r.id.startsWith('review_ctbc_shopback_'));
 assert.equal(offers.length,16);
 for(const r of offers){
   assert.equal(r.cardId,'card_中國信託_241');
   assert.match(r.cardAssociationEvidence.sourceUrl,/ctbcbank\.com\/.*page_(food|shopping)\.html$/);
   assert.match(r.fundingMethods.join(' '),/Visa信用卡/);
 }
 const debitIncluded=data.rules.find(r=>r.id==='review_ctbc_shopping_coupang_points_2026h2');
 assert.deepEqual(debitIncluded.eligibleCardIds,['card_中國信託_241','card_中國信託_328']);
});
test('CTBC JCB restaurant and shopping offers use the JCB product',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const id of ['rule_26ab533bf77c05b5133c','rule_1e1328f849591e9e8f10',
   'rule_e74497743e60187f7f2a','rule_a7fcac04b54ea87a2f43',
   'review_ctbc_linepay_uniqlo_2026h2','review_ctbc_linepay_gu_2026h2']){
   const r=data.rules.find(x=>x.id===id);
   assert.equal(r.cardId,'card_中國信託_242');
   assert.match(r.fundingMethods.join(' '),/LINE Pay JCB卡/);
   assert.ok(r.cardAssociationEvidence.sourceUrl===r.sourceUrl);
 }
});
test('CTBC Visa merchant scope distinguishes credit-only from credit plus debit',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const id of ['rule_141a6550938b29d8ba13','rule_77b16b4262cd2c2704ad',
   'rule_fbadc5644cfad449e41d','review_ctbc_linepay_shopee_2026h2',
   'rule_d06f4a5bdc36a2ea8e23',
   'review_ctbc_shopping_coupang_points_2026h2']){
   const r=data.rules.find(x=>x.id===id);
   assert.equal(r.cardId,'card_中國信託_241');
   assert.deepEqual(r.eligibleCardIds,['card_中國信託_241','card_中國信託_328']);
   assert.equal(r.cardAssociationEvidence.sourceUrl,r.sourceUrl);
 }
 const creditOnly=data.rules.find(x=>x.id==='review_ctbc_shopping_coupang_discount_2026h2');
 assert.deepEqual(creditOnly.eligibleCardIds,['card_中國信託_241']);
});
test('CTBC travel coupon plus points records cannot become a single numeric reward',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const id of ['rule_4fce09de6cf66f5030eb','lp-visa-twdaidrive']){
   const r=data.rules.find(x=>x.id===id);
   assert.equal(r.cardId,'card_中國信託_241');
   assert.deepEqual(r.eligibleCardIds,['card_中國信託_241']);
   assert.equal(r.rewardAmount,null);
   assert.ok(r.validationIssues.includes('COMPOSITE_COUPON_AND_POINTS_NEEDS_SPLIT'));
   assert.equal(r.quickSearchEligible,false);
   assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('CTBC welcome gifts remain separate cumulative conditional awards',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const gifts=['rule_681876489680b798102e','ctbc_linepay_first_card_gift_2026h2']
   .map(id=>data.rules.find(r=>r.id===id));
 assert.deepEqual(gifts.map(r=>r.rewardAmount),[300,100]);
 for(const gift of gifts){
   assert.equal(gift.spendBasis,'CUMULATIVE');
   assert.equal(gift.minimumSpend,888);
   assert.equal(gift.quickSearchEligible,false);
   assert.ok(gift.eligibilityRequirements.some(x=>x.includes('30日')));
   assert.ok(gift.eligibilityRequirements.some(x=>x.includes('不得同領')));
   assert.equal(A.assessment(gift).level,'BLOCKED');
 }
});
test('CTBC iPASS transit is one monthly cumulative point scheme',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const primary=data.rules.find(r=>r.id==='rule_b252bd65776f66527221');
 assert.deepEqual(primary.eligibleCardIds,['card_中國信託_241','card_中國信託_328']);
 assert.equal(primary.validFrom,'2026-01-01');
 assert.equal(primary.spendBasis,'CUMULATIVE');
 assert.equal(primary.minimumSpend,100);
 assert.equal(primary.rewardAmount,null);
 assert.equal(primary.rewardUnit,'percent');
 assert.equal(primary.quickSearchEligible,false);
 assert.equal(A.assessment(primary).level,'BLOCKED');
 for(const id of ['rule_icash_transit','rule_ipass_transit','lp-ipass-transport']){
   const legacy=data.rules.find(r=>r.id===id);
   assert.equal(legacy.duplicateOf,primary.id);
   assert.equal(legacy.quickSearchEligible,false);
 }
});
test('CTBC LINE Pay general and overseas rates have distinct eligible cards',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const general=data.rules.find(r=>r.id==='rule_0f8c8cd7c63feebcc3e1');
 const abroad=data.rules.find(r=>r.id==='rule_02d342bf71118f6a54cd');
 assert.equal(general.baseRate,1);
 assert.equal(general.promoRate,0);
 assert.equal(general.validFrom,'2026-01-01');
 assert.ok(general.eligibleCardIds.includes('card_中國信託_328'));
 assert.equal(abroad.baseRate,1);
 assert.equal(abroad.promoRate,1.8);
 assert.equal(abroad.validFrom,'2026-07-01');
 assert.ok(!abroad.eligibleCardIds.includes('card_中國信託_328'));
 assert.equal(abroad.rewardAmount,null);
 for(const rule of [general,abroad]){
   assert.equal(Object.values(rule.termEvidence.fields).filter(x=>x.status==='supported').length,7);
   assert.ok(!rule.termEvidence.fields.exclusions);
 }
 assert.equal(A.assessment(abroad).level,'BLOCKED');
 assert.equal(data.rules.find(r=>r.id==='ctbc_lp_general').duplicateOf,general.id);
 assert.equal(data.rules.find(r=>r.id==='rule_repaired_f66c0b62fda271b17663').duplicateOf,abroad.id);
});
test('CTBC good dog fixed 30 points apply only on weekdays and once monthly',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='rule_8993c54bfe963a2c628a');
 assert.deepEqual(r.eligibleWeekdays,[1,2,3,4,5]);
 assert.equal(r.rewardAmount,30);
 assert.equal(r.capPeriod,'MONTHLY');
 assert.equal(r.minimumSpend,1300);
 assert.equal(r.paymentProvider,'');
 assert.equal(r.quickSearchEligible,false);
 assert.equal(Object.keys(r.termEvidence.fields).length,12);
 assert.equal(A.eligibleDateStatus(r,new Date('2026-11-08T02:00:00Z')),'OUTSIDE');
 assert.equal(A.isReviewed(r,new Date('2026-11-09T02:00:00Z')),true);
 assert.equal(A.calculate(r,1300,new Date('2026-11-09T02:00:00Z')).calculable,false);
});
test('CTBC Popocat official date cap and card ambiguity block recommendation',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='rule_d4ed298d1db9c2c09f54');
 assert.equal(r.validFrom,'2026-04-01');
 assert.equal(r.baseRate,1);
 assert.equal(r.promoRate,9);
 assert.equal(r.rewardAmount,null);
 assert.equal(r.capAmount,null);
 assert.equal(r.quickSearchEligible,false);
 assert.ok(r.validationIssues.includes('OFFICIAL_HOME_DETAIL_START_DATE_CONFLICT'));
 assert.ok(r.validationIssues.includes('OFFICIAL_HOME_DETAIL_CAP_CONFLICT'));
 assert.ok(r.validationIssues.includes('CARD_ELIGIBILITY_LIST_DETAIL_CONFLICT'));
 assert.equal(A.assessment(r).level,'BLOCKED');
 for(const id of ['rule_7bb19aad5016a4e4ba4c','rule_repaired_3485d52d661a15b0cada']){
   const old=data.rules.find(x=>x.id===id);
   assert.equal(old.duplicateOf,r.id);
   assert.equal(old.quickSearchEligible,false);
 }
});
test('CTBC fish and good life accept direct card payment and round points',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const [id,minimum,cap,bonus] of [
   ['rule_959a861cabb8b515f17f',1500,150,3],
   ['rule_b0e3b7c1e8eb9111f052',1800,180,4]]){
   const r=data.rules.find(x=>x.id===id);
   assert.equal(r.paymentProvider,'');
   assert.match(r.fundingMethods.join(' '),/直接刷卡/);
   assert.equal(r.roundingMode,'ROUND_COMPONENT');
   assert.equal(r.promoRate,bonus);
   assert.equal(r.minimumSpend,minimum);
   assert.equal(r.capAmount,cap);
   assert.equal(r.capScope,'UNKNOWN');
   assert.equal(r.quickSearchEligible,false);
   assert.equal(Object.keys(r.termEvidence.fields).length,10);
   assert.ok(!r.termEvidence.fields.cap);
   assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('three CTBC pet listing gaps have detailed terms but live pools block use',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 for(const [suffix,minimum,cap] of [['dogcatstar',1000,40],['litomon',500,30],['heromama',300,30]]){
   const r=data.rules.find(x=>x.id==='pending_ctbc_linepay_pet_2026_'+suffix);
   assert.equal(r.baseRate,1);
   assert.equal(r.promoRate,4);
   assert.equal(r.rewardAmount,null);
   assert.equal(r.minimumSpend,minimum);
   assert.equal(r.capAmount,cap);
   assert.equal(r.capScope,'PROMO');
   assert.equal(r.capPeriod,'PER_TRANSACTION');
   assert.equal(r.needReg,false);
   assert.equal(r.quickSearchEligible,false);
   assert.equal(Object.keys(r.termEvidence.fields).length,11);
   assert.ok(r.validationIssues.includes('LIVE_CAMPAIGN_POOL_UNVERIFIED'));
   assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('ShopBack Maohao needs registration and separates cash from points',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='pending_ctbc_linepay_pet_2026_maohao');
 assert.equal(r.cardId,'card_中國信託_241');
 assert.deepEqual(r.eligibleCardIds,['card_中國信託_241']);
 assert.equal(r.paymentProvider,'ShopBack');
 assert.equal(r.rewardType,'mixed_benefit');
 assert.equal(r.rewardAmount,null);
 assert.deepEqual(r.benefitComponents.map(x=>x.rate),[4,2]);
 assert.equal(r.needReg,true);
 assert.equal(r.registrationUrl,'');
 assert.equal(r.quickSearchEligible,false);
 assert.equal(A.assessment(r).level,'BLOCKED');
 assert.equal(A.calculate(r,1000).calculable,false);
});
test('Petlife 80 dollar coupon belongs to LINE Pay and needs live coupon checks',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='pending_ctbc_linepay_pet_2026_petlife');
 assert.ok(r);
 assert.equal(r.bank,'LINE Pay');
 assert.equal(r.cardId,'');
 assert.equal(r.eligibleCardScope,'ALL_ISSUERS');
 assert.equal(r.rewardType,'coupon');
 assert.equal(r.rewardAmount,80);
 assert.equal(r.minimumSpend,null);
 assert.equal(r.needReg,false);
 assert.equal(r.quickSearchEligible,false);
 assert.equal(A.assessment(r).level,'BLOCKED');
 assert.equal(A.calculate(r,1000).calculable,false);
});
test('a generic CTBC card cannot approve a Visa or JCB-specific offer',()=>{
 const rule={cardId:'card_中國信託_51',title:'Visa卡指定通路',
   sourceUrl:'https://www.ctbcbank.com/offer',validFrom:'2026-01-01',validUntil:'2026-12-31'};
 assert.equal(A.assessment(rule).level,'BLOCKED');
 rule.cardId='card_中國信託_241';
 assert.equal(A.assessment(rule).level,'REFERENCE');
});
test('official listing-only entries remain quarantined pending full terms',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const entries=data.rules.filter(r=>r.id.startsWith('pending_ctbc_linepay_life_2026_')
   || r.id.startsWith('pending_ctbc_linepay_travel_2026_'));
 assert.equal(entries.length,44);
 for(const r of entries){
   assert.equal(r.quickSearchEligible,false);
   if(!['pending_ctbc_linepay_travel_2026_hotels','pending_ctbc_linepay_travel_2026_itf'].includes(r.id)){
     assert.equal(r.cardId,'');assert.equal(r.rewardAmount,null);assert.equal(r.needReg,false);
     assert.ok(r.validationIssues.includes('REGISTRATION_REQUIREMENT_UNVERIFIED'));
   }
   assert.equal(A.assessment(r).level,'BLOCKED');
 }
});
test('ITF public summary is separated from unverified calculations',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const r=data.rules.find(x=>x.id==='pending_ctbc_linepay_travel_2026_itf');
 assert.equal(r.advertisedOffers.length,4);
 assert.equal(r.advertisedOffers.find(x=>x.kind==='card_points').threshold,6000);
 assert.equal(r.rewardAmount,null);assert.equal(r.promoRate,0);
 assert.ok(r.validationIssues.includes('DETAILS_LOGIN_REQUIRED'));
 assert.equal(A.assessment(r).level,'BLOCKED');
});
test('Hotels.com 16 percent code and 6 percent stamp plans remain distinct and blocked',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const code=data.rules.find(r=>r.id==='pending_ctbc_linepay_travel_2026_hotels');
 const stamp=data.rules.find(r=>r.id==='review_ctbc_hotels_stamp_2026');
 assert.equal(code.promoRate,15);assert.equal(code.capAmount,1800);
 assert.match(code.eligibilityRequirements.join(' '),/CTBCLP16/);
 assert.equal(stamp.promoRate,5);assert.equal(stamp.capAmount,null);
 assert.match(stamp.eligibilityRequirements.join(' '),/Rewards 印花/);
 assert.equal(A.assessment(code).level,'BLOCKED');
 assert.equal(A.assessment(stamp).level,'BLOCKED');
});
test('structured cumulative threshold is never a single purchase',()=>assert.equal(A.calculate({...flat,spendBasis:'CAMPAIGN',minimumSpend:6000},10000).calculable,false));
test('expired offers cannot yield a reward estimate',()=>assert.equal(A.calculate({...flat,validUntil:'2020-01-01'},2000).calculable,false));
test('future offers cannot yield a current reward estimate',()=>assert.equal(A.calculate({...flat,validFrom:'2099-01-01'},2000).calculable,false));
test('review snapshots include the search scope, not only reward numbers',()=>{
 const r={searchKeywords:'LINE Pay',accuracyReview:{}};r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 assert.equal(A.reviewMatches(r),true);r.searchKeywords='海外';assert.equal(A.reviewMatches(r),false);
});
test('review snapshots include recurring windows, excluded countries and disjoint dates',()=>{
 const r={registrationWindows:[{start:'2026-11-03T00:00:00+08:00'}],
   excludedCountries:['法國'],eligibleDateRanges:[['2026-11-10','2026-11-11']],accuracyReview:{}};
 r.accuracyReview.termsSnapshot=A.termsSnapshot(r);
 assert.equal(A.reviewMatches(r),true);
 r.registrationWindows[0].start='2026-11-04T00:00:00+08:00';
 assert.equal(A.reviewMatches(r),false);
 r.registrationWindows[0].start='2026-11-03T00:00:00+08:00';
 r.excludedCountries.push('德國');assert.equal(A.reviewMatches(r),false);
 r.excludedCountries.pop();r.eligibleDateRanges[0][1]='2026-11-12';
 assert.equal(A.reviewMatches(r),false);
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
test('November Unicard country correction stays pending full review',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const overseas=data.rules.find(r=>r.id==='review_unicard_overseas_202610');
 const general=data.rules.find(r=>r.id==='review_unicard_general_202610');
 for(const country of ['英國','法國','德國','義大利']) {
  assert.ok(overseas.matchedMerchants.includes(country));
  assert.ok(!overseas.excludedKeywords.includes(country));
  assert.ok(!general.excludedKeywords.includes(country));
 }
 assert.equal(A.assessment(overseas).level,'BLOCKED');
 assert.equal(A.assessment(general).level,'BLOCKED');
});
test('expired Unicard acquisition offer is not a current registration',()=>{
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(r=>r.id==='unicard_new_user');
 assert.equal(rule.validUntil,'2026-09-30');
 assert.equal(rule.needReg,false);
 assert.equal(rule.quickSearchEligible,false);
 assert.equal(A.calculate(rule,2000).calculable,false);
});
test('offline utilities are bundled',()=>{const html=fs.readFileSync(require('node:path').join(__dirname,'../../index.html'),'utf8');assert.ok(html.includes('id="compiled-utilities"'));assert.ok(!html.includes('<script src="https://cdn.tailwindcss.com">'));});
test('duplicate offer aliases resolve to one visible campaign',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const html=fs.readFileSync(path.join(__dirname,'../../index.html'),'utf8');
 const source=html.match(/    function isCanonicalDisplayRule\(rule\) \{[\s\S]*?\n    \}/)?.[0];
 assert.ok(source,'the UI must have a duplicate display guard');
 const ids=new Set(data.rules.map(rule=>rule.id));
 const aliases=data.rules.filter(rule=>rule.duplicateOf);
 assert.ok(aliases.length>=5);
 for(const rule of aliases){
  assert.ok(ids.has(rule.duplicateOf),`${rule.id} has a missing canonical offer`);
  assert.notEqual(rule.id,rule.duplicateOf);
 }
 const visible=vm.runInNewContext(`${source}; appRules.filter(isCanonicalDisplayRule).map(rule=>rule.id)`,{appRules:data.rules});
 for(const rule of aliases) assert.ok(!visible.includes(rule.id),`${rule.id} appears twice in the offer UI`);
 for(const rule of aliases) assert.ok(visible.includes(rule.duplicateOf),`${rule.id} loses its canonical offer`);
 assert.match(html,/appRules\.filter\(isCanonicalDisplayRule\)\.map\(rule =>/);
 assert.match(html,/appRules\.filter\(r => isCanonicalDisplayRule\(r\) && r\.needReg\)/);
});
test('KKBOX plan price reduction is never a fixed LINE POINTS award',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const rule=data.rules.find(rule=>rule.id==='rule_12b96d96f580a52b4648');
 assert.equal(rule.rewardType,'points');
 assert.equal(rule.rewardAmount,null);
 assert.equal(rule.baseRate+rule.promoRate,5);
 assert.equal(rule.needReg,false);
 assert.equal(rule.quickSearchEligible,false);
 assert.ok(rule.validationIssues.includes('MIXED_PRICE_DISCOUNT_AND_POINTS_NOT_SINGLE_REWARD'));
 assert.equal(A.assessment(rule).level,'BLOCKED');
 assert.equal(A.calculate(rule,1440).calculable,false);
});
test('six CTBC dining quarterly caps are not fixed point awards',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const ids=['rule_141a6550938b29d8ba13','rule_77b16b4262cd2c2704ad','rule_26ab533bf77c05b5133c','rule_1e1328f849591e9e8f10','rule_e74497743e60187f7f2a','rule_a7fcac04b54ea87a2f43'];
 const officialRegister='https://www.ctbcbank.com/twrbo/zh_tw/onlinecounter_index/cc_service/cc_service_register.html';
 for(const id of ids){
  const rule=data.rules.find(r=>r.id===id);
  assert.ok(rule,id);
  assert.equal(rule.rewardAmount,null,id);
  assert.ok([100,200].includes(rule.capAmount),id);
  assert.equal(rule.capPeriod,'QUARTERLY',id);
  assert.equal(rule.registrationCycle,'QUARTERLY',id);
  assert.equal(rule.registrationUrl,officialRegister,id);
  assert.equal(rule.registrationMethods[0].url,officialRegister,id);
  assert.equal(rule.quickSearchEligible,false,id);
  assert.equal(A.assessment(rule).level,'BLOCKED',id);
  assert.equal(A.calculate(rule,1000).calculable,false,id);
 }
});
test('five CTBC pet offer caps do not become fixed point awards',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const expected=new Map([
  ['rule_959a861cabb8b515f17f',[150,'MONTHLY']],
  ['rule_b0e3b7c1e8eb9111f052',[180,'MONTHLY']],
  ['rule_5597df0306591339c831',[140,'CAMPAIGN']],
  ['rule_135b9e6c4621fc0c2dc8',[360,'PER_TRANSACTION']],
  ['rule_80b907fa6a35daa916fd',[30,'PER_TRANSACTION']]
 ]);
 for(const [id,[cap,period]] of expected){
  const rule=data.rules.find(r=>r.id===id);
  assert.ok(rule,id);
  assert.equal(rule.rewardAmount,null,id);
  assert.equal(rule.capAmount,cap,id);
  assert.equal(rule.capPeriod,period,id);
  assert.equal(rule.quickSearchEligible,false,id);
  assert.equal(A.assessment(rule).level,'BLOCKED',id);
  assert.equal(A.calculate(rule,rule.minimumSpend).calculable,false,id);
 }
});
test('CTBC life percentage caps differ from Samsung fixed Thursday Friday award',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 for(const [id,cap,period] of [
  ['rule_d06f4a5bdc36a2ea8e23',100,'QUARTERLY'],
  ['rule_c442e0aac014708858e2',1000,'MONTHLY'],
  ['rule_7d6f97e638c3e5042864',700,'MONTHLY']]){
  const rule=data.rules.find(r=>r.id===id);
  assert.equal(rule.rewardAmount,null,id);
  assert.equal(rule.capAmount,cap,id);
  assert.equal(rule.capPeriod,period,id);
  assert.equal(rule.quickSearchEligible,false,id);
  assert.equal(A.assessment(rule).level,'BLOCKED',id);
 }
 const samsung=data.rules.find(r=>r.id==='rule_59a9da0c6ecc1c0d909f');
 assert.equal(samsung.rewardAmount,1000);
 assert.equal(samsung.minimumSpend,50000);
 assert.deepEqual(samsung.eligibleWeekdays,[4,5]);
 assert.equal(A.eligibleDateStatus(samsung,new Date('2026-11-04T04:00:00Z')),'OUTSIDE');
 assert.equal(A.eligibleDateStatus(samsung,new Date('2026-11-05T04:00:00Z')),'ELIGIBLE');
 assert.equal(samsung.quickSearchEligible,false);
 assert.equal(A.calculate(samsung,50000).calculable,false);
});
test('ambiguous percent points display no fixed award and remain quarantined',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const ambiguous=data.rules.filter(rule=>rule.rewardType==='points' &&
  Number.isFinite(rule.rewardAmount) && Number.isFinite(rule.capAmount) &&
  rule.rewardAmount>0 && rule.rewardAmount===rule.capAmount &&
  (rule.baseRate>0 || rule.promoRate>0) && !rule.fixedAwardEvidence);
 assert.ok(ambiguous.length>=50);
 for(const rule of ambiguous){
  assert.equal(rule.quickSearchEligible,false,rule.id);
  assert.ok(rule.validationIssues.includes('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD'),rule.id);
  assert.equal(A.assessment(rule).level,'BLOCKED',rule.id);
  assert.equal(A.referenceReward(rule),'點數上限／固定獎勵待核',rule.id);
 }
 const samsung=data.rules.find(rule=>rule.id==='rule_59a9da0c6ecc1c0d909f');
 assert.ok(samsung.fixedAwardEvidence?.locator);
 assert.equal(samsung.rewardAmount,1000);
});
test('all unresolved numeric point awards beside rates stay out of quick search',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const mixed=data.rules.filter(rule=>rule.rewardType==='points' &&
  !['percent','%'].includes(String(rule.rewardUnit||'').toLowerCase()) &&
  Number.isFinite(rule.rewardAmount) && rule.rewardAmount>0 &&
  (rule.baseRate>0 || rule.promoRate>0) && !rule.fixedAwardEvidence);
 assert.ok(mixed.length>=100);
 for(const rule of mixed){
  assert.equal(rule.quickSearchEligible,false,rule.id);
  assert.ok(rule.validationIssues.includes('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD'),rule.id);
  assert.equal(A.referenceReward(rule),'點數上限／固定獎勵待核',rule.id);
 }
});
test('CTBC fashion point caps and physical-card restriction stay distinct',()=>{
 const path=require('node:path');
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data.json'),'utf8'));
 const expected=new Map([
  ['rule_9b4fdf62817e99e7418a',150],
  ['rule_ea7cdd2e0b8e36a8b01a',300],
  ['rule_fe3b235a35f6c2330652',200],
  ['rule_8be1d7ac2cc79e568969',1000]
 ]);
 for(const [id,cap] of expected){
  const rule=data.rules.find(r=>r.id===id);
  assert.equal(rule.rewardAmount,null,id);
  assert.equal(rule.capAmount,cap,id);
  assert.equal(rule.quickSearchEligible,false,id);
  assert.equal(A.assessment(rule).level,'BLOCKED',id);
 }
 const watsons=data.rules.find(r=>r.id==='rule_9b4fdf62817e99e7418a');
 assert.deepEqual(watsons.eligibleWeekdays,[0]);
 assert.equal(A.eligibleDateStatus(watsons,new Date('2026-11-06T04:00:00Z')),'OUTSIDE');
 const vacanza=data.rules.find(r=>r.id==='rule_ea7cdd2e0b8e36a8b01a');
 assert.deepEqual(vacanza.fundingMethods,['中國信託 LINE Pay 實體卡直接刷卡']);
 assert.ok(vacanza.validationIssues.includes('DISCOUNT_TIERS_AND_EXCLUSIONS_NOT_MACHINE_CHECKED'));
 const sisley=data.rules.find(r=>r.id==='rule_8be1d7ac2cc79e568969');
 assert.ok(sisley.validationIssues.includes('OFFICIAL_MERCHANT_LINK_CONFLICT'));
});
test('having a source is useful reference, not automatic factual approval',()=>{
 const r={...flat,sourceUrl:'https://bank.test/offer',title:'最高3%回饋',validFrom:'2026-11-01',validUntil:'2026-11-30'};
 assert.equal(A.assessment(r).level,'REFERENCE');assert.equal(A.assessment(r).cashAllowed,false);
 assert.equal(A.referenceReward(r),'最高 3%（資料列示）');
});
test('unknown offer or registration dates cannot appear as usable recommendations',()=>{
 const current={...flat,sourceUrl:'https://bank.test/offer',validFrom:'2026-11-01',validUntil:'2026-11-30'};
 assert.equal(A.assessment({...current,validUntil:''}).level,'BLOCKED');
 assert.equal(A.assessment({...current,validFrom:''}).level,'BLOCKED');
 assert.equal(A.assessment({...current,needReg:true}).level,'BLOCKED');
});
test('cash cap is not presented as a fixed gift and zero points are not promoted',()=>{
 assert.equal(A.referenceReward({rewardType:'cash',rewardAmount:150,capAmount:150}),'活動優惠（條件待補）');
 assert.equal(A.referenceReward({rewardType:'points',rewardAmount:0,rewardUnit:'points'}),'活動優惠（條件待補）');
});
test('conflicts and changed official sources stop numeric recommendation',()=>{
 assert.equal(A.assessment({sourceUrl:'https://bank.test',accuracyReview:{status:'CONFLICT'}}).level,'BLOCKED');
 assert.equal(A.assessment({sourceUrl:'https://bank.test',accuracyReview:{status:'RECHECK_REQUIRED'}}).level,'BLOCKED');
 assert.equal(A.assessment({sourceUrl:'https://bank.test',validationIssues:['SOURCE_CLAIM_UNCONFIRMED']}).level,'BLOCKED');
 assert.equal(A.referenceReward({title:'旅遊保險',rewardType:'cash',rewardAmount:3190000}),'保險保障，非刷卡回饋');
});
test('Taipei month key, intent aliases, three-color badges, cap loop and backup sanitizer are safe',()=>{
 const html=fs.readFileSync(require('node:path').join(__dirname,'../../index.html'),'utf8');
 const scriptBody=[...html.matchAll(/<script(?![^>]*src=)[^>]*>([\s\S]*?)<\/script>/g)][0][1];
 const store=Object.create(null);
 const storage={
  getItem:k=>Object.prototype.hasOwnProperty.call(store,k)?store[k]:null,
  setItem:(k,v)=>{store[k]=String(v)},
  removeItem:k=>{delete store[k]},
  clear:()=>{for(const k of Object.keys(store))delete store[k]},
  key:i=>Object.keys(store)[i]||null,
  get length(){return Object.keys(store).length}
 };
 const sandbox={
  console,setTimeout:()=>0,clearTimeout:()=>{},URL,Blob,
  localStorage:storage,sessionStorage:storage,
  location:{protocol:'https:',reload:()=>{}},
  navigator:{userAgent:'Test'},
  window:{addEventListener:()=>{},confirm:()=>true,open:()=>{}},
  document:{addEventListener:()=>{},getElementById:()=>null,querySelectorAll:()=>[]}
 };
 sandbox.globalThis=sandbox;
 vm.runInNewContext(scriptBody,sandbox);

 assert.equal(sandbox.getTaipeiYearMonth(new Date('2026-10-31T15:59:59Z')),'2026-10');
 assert.equal(sandbox.getTaipeiYearMonth(new Date('2026-10-31T16:00:00Z')),'2026-11');
 assert.equal(sandbox.matchesQueryTermWithAliases('7-ELEVEN統一超商','小七'),true);
 assert.equal(sandbox.matchesQueryTermWithAliases('UBEREATS優食','外送'),true);
 assert.equal(sandbox.matchesQueryTermWithAliases('海外實體消費','日本'),true);

 const sanitized=sandbox.sanitizeUsageMap(JSON.parse('{"__proto__":{"polluted":1},"card_esun_ubear":{"totalSpent":3000,"txCount":2,"rules":{"r1":{"spent":3000,"usedCap":90,"__proto__":1}}}}'));
 assert.equal(({}).polluted,undefined);
 assert.equal(sanitized.card_esun_ubear.totalSpent,3000);
 assert.equal(sanitized.card_esun_ubear.rules.r1.usedCap,90);
});
