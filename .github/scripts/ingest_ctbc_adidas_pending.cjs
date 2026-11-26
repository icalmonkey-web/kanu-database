// Time-limited official Adidas listing: preserve known thresholds without inventing quota terms.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const id='review_ctbc_adidas_2026_11_pending';
let r=data.rules.find(x=>x.id===id);
if(!r){r={id};data.rules.push(r);}
const source='https://web-tw-pay.line.me/cms/event/template1.3/9ca2772f-41b7-42d4-973d-f6ff4ce18021';
Object.assign(r,{
  bank:'中國信託',cardId:'card_中國信託_51',offerDomain:'CARD',
  paymentProvider:'LINE Pay',fundingMethods:['LINE Pay綁定中國信託LINE Pay卡'],
  title:'Adidas 台灣官網：LINE Pay 滿額最高 16% 點數（名額待查）',
  activityType:'DIRECT_PROMOTION',scope:'SPECIFIC',eligibleCardScope:'SPECIFIC_CARD',
  matchedMerchants:['Adidas台灣官網'],searchKeywords:'Adidas,adidas台灣官網',intentTags:['網購','行動支付'],
  intentEvidence:'中信脆慢活頁 L29-L34；LINE Pay活動頁 L25-L30',
  baseRate:0,promoRate:0,rewardType:'points',rewardUnit:'percent',rewardAmount:null,
  pointValueTwd:null,capAmount:null,capScope:'UNKNOWN',capPeriod:'',minimumSpend:3900,
  spendBasis:'PER_TRANSACTION',roundingMode:'UNKNOWN',rewardCalculationMode:'MAX_ONLY',rewardTiers:[],
  eligibilityRequirements:['活動期間於Adidas台灣官網以LINE Pay付款',
    '任一已綁定付款方式單筆實付滿NT$3,900，LINE POINTS最高6%',
    '已綁定中國信託LINE Pay卡單筆實付滿NT$5,200，再享最高10%',
    '付款前同意LINE Pay行銷資訊提供政策'],
  excludedKeywords:['LINE POINTS折抵金額','LINE Pay優惠券折抵金額'],
  needReg:false,regDeadline:'',registrationStart:'',registrationEnd:'',registrationMethods:[],
  validFrom:'2026-11-01',validUntil:'2026-11-12',sourceUrl:source,registrationUrl:'',
  quotaInfo:'官方入口及可讀活動內容未見完整名額／回饋上限，待查；不得依最高16%試算。',
  benefitSummary:'已知門檻：LINE Pay實付滿NT$3,900最高6%；中信LINE Pay卡實付滿NT$5,200再最高10%。名額、上限及實際可得點數待核。',
  quickSearchEligible:false,validationIssues:['OFFICIAL_QUOTA_AND_CAP_UNVERIFIED'],
  sourceFacts:{checkedAt:'2026-11-03T21:30:00+08:00',sourceUrl:source,
    locators:{period:'L10-L12 GMT+0, Taipei 11/1~11/12',thresholds:'L25-L30',
      listing:'CTBC page_life L29-L34 and store.html L850-L858'}},
  fetchedAt:'2026-11-03T21:30:00+08:00'
});
data.version='2026.11.03-v213000-ctbc-adidas-pending';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
