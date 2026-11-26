// Official 2026 weekly Thursday KKday plan, distinct from 20% member days.
const fs=require('node:fs');
const path=require('node:path');
const A=require('../../accuracy-core.js');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const r=data.rules.find(x=>x.id==='rule_d1385d908fb4b07473ef');
if(!r) throw new Error('kkday_weekly_rule_missing');
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_travel.html';
const checkedAt='2026-11-03T21:30:00+08:00';
Object.assign(r,{
  title:'KKday 指定商品每週四輸入優惠碼，LINE POINTS 最高 10%',
  sourceUrl:source,validFrom:'2026-01-01',validUntil:'2026-12-31',
  baseRate:1,promoRate:9,rewardType:'points',rewardUnit:'percent',
  rewardAmount:null,pointValueTwd:null,capAmount:360,capScope:'TOTAL',
  capPeriod:'PER_TRANSACTION',minimumSpend:0,spendBasis:'PER_TRANSACTION',
  roundingMode:'ROUND_COMPONENT',rewardCalculationMode:'FLAT',rewardTiers:[],
  needReg:false,regDeadline:'',registrationStart:'',registrationEnd:'',
  registrationUrl:'',registrationMethods:[],
  eligibilityRequirements:[
    '每週四00:00至23:59於KKday指定專屬網頁購買一日遊、體驗、交通或景點通票等指定商品',
    '結帳前輸入當週優惠碼，直接輸入中國信託LINE Pay卡卡號付款',
    '每個帳號每週限用一次，每週限量60組優惠碼，額滿即止',
    '行程出發／使用期限及實際入點依官方條款'
  ],
  excludedKeywords:['第三方支付綁定卡片','JR相關及部分商品','訂單取消或退款','折價券及點數折抵金額'],
  quotaInfo:'每筆總回饋上限360點；每週四限量60組優惠碼，每帳號每週限用一次。',
  benefitSummary:'每週四指定商品輸入當週優惠碼，最高10% LINE POINTS（含一般1%）；每筆上限360點，限量60組。與會員日20%為不同方案。',
  quickSearchEligible:false,validationIssues:[],fetchedAt:checkedAt
});
const locators={title:'KKday每週四方案／L415-L427及L444-L448',
  cardEligibility:'適用卡及直接卡號付款／L416-L418、L446-L447、L459',
  reward:'最高10%含一般1%／L424-L426、L446',rewardType:'LINE POINTS／L424-L426',
  validFrom:'活動優惠期間／L444-L445',validUntil:'活動優惠期間／L444-L445',
  cap:'每筆360點、每週60組／L425-L427、L448',
  minimumSpend:'指定品項與優惠碼，未列最低金額／L444-L449',
  exclusions:'排除JR、第三方支付與退款／L449-L461',
  rounding:'加碼點數四捨五入／L450-L451'};
const fields=Object.fromEntries(Object.entries(locators).map(([key,locator])=>
  [key,{status:'supported',sourceUrl:source,locator}]));
fields.registration={status:'not_applicable',sourceUrl:source,
  locator:'每週四優惠碼與結帳條款／L424-L427、L444-L448',
  reason:'優惠碼須結帳前輸入；無銀行活動登錄步驟，原KKday專屬購物網址不是登錄頁'};
r.termEvidence={sourceUrl:source,checkedAt,method:'manual_official_terms_read',fields};
r.accuracyReview={status:'SOURCE_CHECKED',checkedAt,sourceUrl:source,
  fields:Object.keys(A.termsSnapshot(r)),issues:[],method:'official_terms_read',
  evidenceSources:[source],evidence:r.benefitSummary,termsSnapshot:A.termsSnapshot(r)};
r.evidenceStatus='SOURCE_CHECKED';
data.version='2026.11.03-v213000-ctbc-kkday-weekly-review';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`KKday weekly reviewed=${A.isReviewed(r)}; quickSearch=${r.quickSearchEligible}`);
