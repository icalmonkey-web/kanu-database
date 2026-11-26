// Two Hotels.com plans are separately described in the official CTBC travel terms.
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const file=path.join(root,'data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const mappingFile=path.join(root,'official_catalogs/ctbc_linepay_travel_2026_mapping.json');
const mapping=JSON.parse(fs.readFileSync(mappingFile,'utf8'));
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_travel.html';
const specs=[
  {id:'pending_ctbc_linepay_travel_2026_hotels',title:'Hotels.com 優惠一：CTBCLP16 指定網頁最高16% LINE POINTS',
   promoRate:15,capAmount:1800,capScope:'TOTAL',quotaInfo:'全體顧客每月前450筆符合資格的優惠碼預訂；下單前須確認優惠碼仍有效',
   eligibilityRequirements:['中國信託 LINE Pay 卡於指定網頁線上以新臺幣付款','輸入優惠碼 CTBCLP16','預訂1至28晚，於2027-06-30前完成入住','不可與 Hotels.com Rewards 印花併用'],
   lines:'L238-L260'},
  {id:'review_ctbc_hotels_stamp_2026',title:'Hotels.com 優惠二：指定網頁6% LINE POINTS 可累積印花',
   promoRate:5,capAmount:null,capScope:'NONE',quotaInfo:'不需 CTBCLP16 優惠碼；可累積 Hotels.com Rewards 印花，仍須符合指定網頁與入住條件',
   eligibilityRequirements:['中國信託 LINE Pay 卡於指定網頁線上以新臺幣付款','不使用 CTBCLP16 優惠碼','於2027-06-30前完成入住','可累積 Hotels.com Rewards 印花'],
   lines:'L238-L260'}
];
for(const s of specs){
  let r=data.rules.find(x=>x.id===s.id);
  if(!r){r={id:s.id};data.rules.push(r);}
  else if(r.sourceUrl && r.sourceUrl!==source)throw Error(`Unexpected source: ${s.id}`);
  Object.assign(r,{
    bank:'中國信託',cardId:'card_中國信託_51',offerDomain:'CARD',paymentProvider:'',
    fundingMethods:['中國信託 LINE Pay 卡直接於 Hotels.com 指定網頁線上付款'],
    title:s.title,activityType:'DIRECT_PROMOTION',scope:'SPECIFIC',eligibleCardScope:'UNKNOWN',
    matchedMerchants:['Hotels.com'],searchKeywords:'Hotels.com,訂房',
    baseRate:1,promoRate:s.promoRate,rewardType:'points',rewardUnit:'percent',rewardAmount:null,
    pointValueTwd:null,capAmount:s.capAmount,capScope:s.capScope,capPeriod:'PER_TRANSACTION',
    roundingMode:'ROUND_COMPONENT',spendBasis:'PER_TRANSACTION',minimumSpend:0,
    rewardCalculationMode:'FLAT',rewardTiers:[],needReg:false,
    validFrom:'2026-01-01',validUntil:'2026-12-31',
    sourceUrl:source,registrationUrl:'',registrationMethods:[],
    eligibilityRequirements:s.eligibilityRequirements,
    excludedKeywords:['到店付款','未完成入住','取消訂房','退貨','非指定網頁'],
    quotaInfo:s.quotaInfo,
    benefitSummary:`點數方案需完成入住才取得資格；${s.quotaInfo}。國外交易手續費另計。`,
    quickSearchEligible:false,
    validationIssues:['CARD_NETWORK_SCOPE_UNVERIFIED','STAY_COMPLETION_AND_LIVE_AVAILABILITY_UNVERIFIED'],
    sourceFacts:{checkedAt:'2026-11-04T19:31:00+08:00',sourceUrl:source,
      locators:{eligibility:s.lines,reward:'L246-L260',stay:'L250-L252'}},
    fetchedAt:'2026-11-04T19:31:00+08:00'
  });
}
const previous=mapping.mappings.find(x=>x.offerId==='hotels');
if(previous)Object.assign(previous,{ruleIds:specs.map(x=>x.id),status:'candidate',
  reason:'16%優惠碼與6%印花方案已拆分；持卡卡別範圍、每月優惠碼剩餘名額與實際入住仍待交易時確認'});
else mapping.mappings.push({offerId:'hotels',ruleIds:specs.map(x=>x.id),status:'candidate',
  reason:'16%優惠碼與6%印花方案已拆分；持卡卡別範圍、每月優惠碼剩餘名額與實際入住仍待交易時確認'});
delete previous?.ruleId;
data.version='2026.11.04-v193500-hotels-two-plans';
fs.writeFileSync(mappingFile,JSON.stringify(mapping,null,2)+'\n');
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Hotels.com plans split=2');
