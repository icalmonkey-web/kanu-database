// Official Under Armour terms checked on 2026-11-03; reruns do not renew the review.
const fs = require('node:fs');
const path = require('node:path');
const A = require('../../accuracy-core.js');
const file = path.resolve(__dirname, '../../data.json');
const data = JSON.parse(fs.readFileSync(file,'utf8'));
const r = data.rules.find(x=>x.id==='rule_04710b8837a6e3f2b94f');
if (!r) throw new Error('under_armour_rule_missing');
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_life.html';
const checkedAt='2026-11-03T21:30:00+08:00';
Object.assign(r,{
  sourceUrl:source,validFrom:'2026-01-01',validUntil:'2026-12-31',
  title:'Under Armour 官方網站：LINE POINTS 最高 7%',
  baseRate:1,promoRate:6,rewardType:'points',rewardUnit:'percent',
  rewardAmount:null,pointValueTwd:null,capAmount:200,capScope:'PROMO',
  capPeriod:'PER_TRANSACTION',minimumSpend:0,spendBasis:'PER_TRANSACTION',
  roundingMode:'ROUND_COMPONENT',rewardCalculationMode:'FLAT',rewardTiers:[],
  needReg:false,regDeadline:'',registrationStart:'',registrationEnd:'',registrationMethods:[],
  eligibilityRequirements:[
    '於Under Armour官方網站透過LINE Pay綁定中國信託LINE Pay卡付款',
    '付款前以台灣LINE帳號註冊LINE Pay並同意行銷資訊提供政策',
    '活動總限量900,000點，依交易順序核算，額滿為止'
  ],
  excludedKeywords:['任何分期付款','LINE POINTS折抵金額','LINE Pay優惠券折抵金額','取消交易'],
  quotaInfo:'加碼6%每LINE Pay帳號單筆最高200點；活動總限量900,000點，依交易順序，額滿為止。',
  benefitSummary:'官網LINE Pay支付最高7% LINE POINTS＝一般消費1%＋活動加碼6%；加碼單筆上限200點，活動總量額滿即止。',
  quickSearchEligible:false,validationIssues:[],fetchedAt:checkedAt
});
const locators={title:'Under Armour活動標題／L385-L390',cardEligibility:'參加資格／L390、L394-L398',
  reward:'1%+6%／L390-L393',rewardType:'LINE POINTS／L390-L393',
  validFrom:'活動卡片／L111-L116',validUntil:'活動卡片／L111-L116',
  cap:'加碼單筆上限及總量／L392',minimumSpend:'活動條款無滿額門檻／L389-L393',
  exclusions:'分期及點數折抵／L399、L402-L408',rounding:'實付金額四捨五入／L402-L403'};
const fields=Object.fromEntries(Object.entries(locators).map(([key,locator])=>
  [key,{status:'supported',sourceUrl:source,locator}]));
fields.registration={status:'not_applicable',sourceUrl:source,locator:'Under Armour活動完整條款／L389-L416',
  reason:'沒有銀行活動登錄步驟；LINE Pay帳號註冊及行銷政策同意另列為資格'};
r.termEvidence={sourceUrl:source,checkedAt,method:'manual_official_terms_read',fields};
r.accuracyReview={status:'SOURCE_CHECKED',checkedAt,sourceUrl:source,
  fields:Object.keys(A.termsSnapshot(r)),issues:[],method:'official_terms_read',
  evidenceSources:[source],evidence:r.benefitSummary,termsSnapshot:A.termsSnapshot(r)};
r.evidenceStatus='SOURCE_CHECKED';
data.version='2026.11.03-v214500-ctbc-under-armour-review';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`Under Armour reviewed=${A.isReviewed(r)}; quickSearch=${r.quickSearchEligible}`);
