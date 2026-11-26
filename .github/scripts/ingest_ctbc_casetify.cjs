// One observed 2026 CASETiFY offer, manually transcribed from CTBC page_life.
const fs=require('node:fs');
const path=require('node:path');
const A=require('../../accuracy-core.js');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_life.html';
const checkedAt='2026-11-03T21:30:00+08:00';
const id='review_ctbc_casetify_2026q4';
let r=data.rules.find(x=>x.id===id);
if(!r){r={id};data.rules.push(r);}
Object.assign(r,{
  bank:'中國信託',cardId:'card_中國信託_51',offerDomain:'CARD',
  paymentProvider:'中國信託LINE Pay卡',fundingMethods:['實體卡直接刷卡','LINE Pay綁定中國信託LINE Pay卡'],
  stackingStatus:'STACKABLE',title:'CASETiFY 官網／APP 單筆滿 NT$2,500 享 LINE POINTS 4%',
  activityType:'DIRECT_PROMOTION',scope:'SPECIFIC',eligibleCardScope:'SPECIFIC_CARD',
  matchedMerchants:['CASETiFY'],searchKeywords:'CASETiFY,CASETiFY官網',intentTags:['網購'],
  intentEvidence:'官方脆慢活頁 L504-L516',baseRate:1,promoRate:3,
  rewardType:'points',rewardUnit:'percent',rewardAmount:null,pointValueTwd:null,
  capAmount:200,capPeriod:'MONTHLY',capScope:'PROMO',roundingMode:'ROUND_COMPONENT',
  spendBasis:'PER_TRANSACTION',minimumSpend:2500,rewardCalculationMode:'FLAT',rewardTiers:[],
  eligibilityRequirements:['CASETiFY官網或APP單筆實際刷卡滿NT$2,500',
    '使用中國信託LINE Pay卡直接刷卡或綁定LINE Pay付款',
    '加碼點數每人每月上限200點；須確認當月剩餘額度'],
  excludedKeywords:['其他第三方支付','付款失敗','訂單取消','退貨'],
  needReg:false,regDeadline:'',registrationStart:'',registrationEnd:'',registrationMethods:[],
  validFrom:'2026-10-01',validUntil:'2026-12-31',sourceUrl:source,
  registrationUrl:'',quotaInfo:'加碼3%每人每月上限200點；點數入帳時間以官方條款為準。',
  benefitSummary:'單筆滿NT$2,500享LINE POINTS 4%＝一般1%＋加碼3%；加碼每人每月最多200點。',
  quickSearchEligible:false,validationIssues:[],fetchedAt:checkedAt
});
const locators={title:'活動標題／L504-L510',cardEligibility:'適用卡與支付／L510-L511',
  reward:'基本1%加碼3%／L510',rewardType:'LINE POINTS／L505-L510',
  validFrom:'活動期間／L46及L509',validUntil:'活動期間／L46及L509',
  cap:'列表每人每月上限200點／L46',minimumSpend:'單筆NT$2,500／L510',
  exclusions:'第三方支付與取消退貨／L511-L514',rounding:'加碼逐筆四捨五入／L515'};
const fields=Object.fromEntries(Object.entries(locators).map(([key,locator])=>
  [key,{status:'supported',sourceUrl:source,locator}]));
fields.registration={status:'not_applicable',sourceUrl:source,
  locator:'活動完整條款／L508-L516',reason:'CASETiFY活動未列銀行登錄步驟'};
r.termEvidence={sourceUrl:source,checkedAt,method:'manual_official_terms_read',fields};
r.accuracyReview={status:'SOURCE_CHECKED',checkedAt,sourceUrl:source,
  fields:Object.keys(A.termsSnapshot(r)),issues:[],method:'official_terms_read',
  evidenceSources:[source],evidence:r.benefitSummary,termsSnapshot:A.termsSnapshot(r)};
r.evidenceStatus='SOURCE_CHECKED';
data.version='2026.11.03-v213000-ctbc-casetify-review';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`CASETiFY reviewed=${A.isReviewed(r)}; quickSearch=${r.quickSearchEligible}`);
