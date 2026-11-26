// The 20% plan has three disjoint date windows; keep blocked until the UI models them.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const id='review_ctbc_kkday_member_day_2026_pending';
let r=data.rules.find(x=>x.id===id);
if(!r){r={id};data.rules.push(r);}
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_travel.html';
Object.assign(r,{
  bank:'中國信託',cardId:'card_中國信託_51',offerDomain:'CARD',
  paymentProvider:'',fundingMethods:['中國信託LINE Pay卡直接刷卡'],
  title:'KKday 會員日指定團體旅遊最高 LINE POINTS 20%（指定日期）',
  activityType:'DIRECT_PROMOTION',scope:'SPECIFIC',eligibleCardScope:'SPECIFIC_CARD',
  matchedMerchants:['KKday'],searchKeywords:'KKday,團體旅遊,會員日',intentTags:['旅遊','網購'],
  intentEvidence:'中信脆自遊頁 L389-L414',baseRate:1,promoRate:19,
  rewardType:'points',rewardUnit:'percent',rewardAmount:null,pointValueTwd:null,
  capAmount:1500,capPeriod:'PER_TRANSACTION',capScope:'TOTAL',minimumSpend:0,
  spendBasis:'PER_TRANSACTION',roundingMode:'ROUND_COMPONENT',rewardCalculationMode:'MAX_ONLY',rewardTiers:[],
  eligibilityRequirements:['僅限2026/10/10-11、11/10-11、12/10-11，非連續活動',
    '指定團體、迷你團或多日遊商品，結帳前輸入當月對應優惠碼',
    '直接使用中國信託LINE Pay卡付款；每位會員每月限一次，每月限量50組',
    '行程出發期限按各月份優惠碼另行適用'],
  excludedKeywords:['第三方支付綁定卡片','JR相關及部分商品','取消交易','優惠券或點數折抵金額'],
  needReg:false,regDeadline:'',registrationStart:'',registrationEnd:'',registrationUrl:'',registrationMethods:[],
  validFrom:'2026-10-10',validUntil:'2026-12-11',sourceUrl:source,
  quotaInfo:'每筆最多1,500點；每位會員每月限用一次，每月限量50組。活動只在三段指定日期開放。',
  benefitSummary:'會員日指定團體旅遊最高20% LINE POINTS；只在10/10-11、11/10-11、12/10-11且輸入當月優惠碼，非連續適用。',
  eligibleDateRanges:[['2026-10-10','2026-10-11'],['2026-11-10','2026-11-11'],['2026-12-10','2026-12-11']],
  quickSearchEligible:false,validationIssues:['DISCONTINUOUS_ACTIVITY_DATES_NEED_RUNTIME_SUPPORT'],
  sourceFacts:{checkedAt:'2026-11-03T21:30:00+08:00',sourceUrl:source,
    locators:{dates:'L392-L406',quota:'L394-L406',exclusions:'L407-L413'}},
  fetchedAt:'2026-11-03T21:30:00+08:00'
});
data.version='2026.11.03-v213000-ctbc-kkday-member-pending';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
