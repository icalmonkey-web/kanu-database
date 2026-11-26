// Three source-backed registration notices. Unknown close times and quotas block recommendations.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_travel.html';
const checkedAt='2026-11-04T08:30:00+08:00';
const specs=[
  {id:'review_ctbc_trip_registration_2026h2',merchant:'Trip.com',network:'Visa',
    total:5,base:1,promo:4,cap:100,quota:8000,hour:'10:00',lines:'L467-L480'},
  {id:'review_ctbc_airbnb_registration_2026h2',merchant:'Airbnb',network:'Visa',
    total:5,base:1,promo:4,cap:100,quota:8000,hour:'10:00',lines:'L481-L494'},
  {id:'review_ctbc_tigerair_registration_2026h2',merchant:'台灣虎航',network:'JCB',
    total:10,base:1,promo:9,cap:200,quota:5000,hour:'13:00',lines:'L495-L508'}
];
for(const s of specs){
  let r=data.rules.find(x=>x.id===s.id);
  if(!r){r={id:s.id};data.rules.push(r);}
  const registrationWindows=[7,8,9,10,11,12].map(month=>({
    start:`2026-${String(month).padStart(2,'0')}-06T${s.hour}:00+08:00`
  }));
  Object.assign(r,{
    bank:'中國信託',cardId:s.network==='JCB'?'card_中國信託_242':'card_中國信託_241',offerDomain:'CARD',
    eligibleCardIds:s.network==='Visa'?['card_中國信託_241','card_中國信託_328']:['card_中國信託_242'],
    paymentProvider:'',fundingMethods:[`中國信託LINE Pay ${s.network}卡${s.network==='Visa'?'（含簽帳金融卡）':''}`],
    title:`${s.merchant}：中信 LINE Pay ${s.network}卡登錄後最高 ${s.total}% 點數（名額待確認）`,
    activityType:'REG_PROMOTION',scope:'SPECIFIC',eligibleCardScope:'SPECIFIC_CARD',
    matchedMerchants:[s.merchant],searchKeywords:s.merchant,
    intentTags:['旅遊','網購'],intentEvidence:`官方脆自遊頁 ${s.lines}`,
    baseRate:s.base,promoRate:s.promo,rewardType:'points',rewardUnit:'percent',rewardAmount:null,
    pointValueTwd:null,capAmount:s.cap,capScope:'PROMO',capPeriod:'QUARTERLY',
    roundingMode:'ROUND_COMPONENT',spendBasis:'PER_TRANSACTION',minimumSpend:0,
    rewardCalculationMode:'FLAT',rewardTiers:[],
    needReg:true,registrationCycle:'QUARTERLY',registrationWindows,
    regDeadline:`每月6日${s.hour}開放，每季須重新登錄；額滿即關閉`,
    registrationStart:'',registrationEnd:'',registrationUrl:'',registrationMethods:[],
    eligibilityRequirements:[`限中國信託LINE Pay ${s.network}卡${s.network==='Visa'?'（含簽帳金融卡）':''}`,
      '每季須於中國信託官方活動登錄平台重新登錄',
      '指定商家交易且帳單明細須能辨識商家名稱',
      '活動名額與剩餘季度上限須以銀行即時資料確認'],
    excludedKeywords:['未登錄','活動額滿','無法辨識指定商家名稱','取消或退貨交易'],
    validFrom:'2026-07-01',validUntil:'2026-12-31',sourceUrl:source,
    quotaInfo:`每月限量登錄${s.quota.toLocaleString('en-US')}名；加碼點數每季每戶上限${s.cap}點；登錄額滿即關閉。`,
    benefitSummary:`${s.merchant}指定交易最高${s.total}% LINE POINTS＝一般${s.base}%＋登錄加碼${s.promo}%；${s.network}卡限定，每季重新登錄。`,
    quickSearchEligible:false,
    validationIssues:['REGISTRATION_CLOSE_AND_LIVE_QUOTA_UNVERIFIED'],
    sourceFacts:{checkedAt,sourceUrl:source,locators:{terms:s.lines,
      opening:s.network==='JCB'?'L502':'L474/L488',card:s.lines}},
    fetchedAt:checkedAt
  });
}
data.version='2026.11.04-v083000-ctbc-travel-registration-notices';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`registration notices updated=${specs.length}`);
