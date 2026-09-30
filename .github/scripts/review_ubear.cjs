// One-time correction from the official card terms read on 2026-09-29.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname,'../..');
const file = path.join(root,'data.json');
const data = JSON.parse(fs.readFileSync(file,'utf8'));
const source = 'https://event.esunbank.com.tw/credit/ubear/card.html';
const checkedAt = '2026-09-29T01:00:00+08:00';
const fields = ['baseRate','promoRate','capAmount','capScope','capPeriod','validFrom','validUntil','eligibilityRequirements','excludedKeywords','roundingMode'];
const common = {cardId:'card_esun_ubear',bank:'玉山銀行',offerDomain:'CARD',sourceUrl:source,
 validFrom:'2026-09-01',validUntil:'2027-02-28',fetchedAt:checkedAt,needReg:false,
 rewardType:'percent',rewardUnit:'percent',roundingMode:'FLOOR_COMPONENT',spendBasis:'PER_TRANSACTION',
 minimumSpend:0,selectionMode:'FIXED',associationStatus:'matched',quickSearchEligible:true,
 accuracyReview:{status:'SOURCE_CHECKED',checkedAt,sourceUrl:source,fields,issues:[],method:'official_terms_read'},
 evidenceStatus:'SOURCE_CHECKED',validationIssues:[],rewardCalculationMode:'TIERED',
 capPeriod:'STATEMENT',registrationMethods:[]};
const tier=(name,totalRate,baseRate,requirements,capAmount=null)=>({name,totalRate,baseRate,promoRate:totalRate-baseRate,requirements,capAmount,isDefault:false});
const corrected=[
 {...common,id:'review_ubear_general_202609',title:'U Bear 一般消費：依帳單與自扣資格最高1%',category:'一般消費',baseRate:0,promoRate:0,rewardAmount:1,
  matchedMerchants:['國內一般消費','海外一般消費','日本實體消費'],searchKeywords:'一般消費 日本 實體',capAmount:null,capScope:'NONE',
  eligibilityRequirements:['電子帳單或玉山臺幣帳戶自扣；自扣须扣款成功'],
  rewardTiers:[tier('符合其中一項',.5,.5,['帳單e化或成功自扣']),tier('兩項皆符合',1,1,['帳單e化及成功自扣'])],
  excludedKeywords:['數位訂閱','分期','全聯','大全聯','繳費'],
  quotaInfo:'依帳單e化與玉山臺幣帳戶自扣資格，回饋0.5%或1%；兩者皆符合才是1%。分期及指定訂閱不適用。逐筆捨去至元，正附卡合併。'},
 {...common,id:'review_ubear_online_202609',title:'U Bear 網路消費：符合任務最高3%',category:'網購',baseRate:0,promoRate:0,rewardAmount:3,
  matchedMerchants:['網路消費','LINE Pay','Booking.com','agoda','Trip.com'],searchKeywords:'網購 訂房 網路消費 LINE Pay',
  capAmount:150,capScope:'PROMO',eligibilityRequirements:['帳單e化','收單交易須認列網路一般消費；自扣成功才享最高3%'],
  rewardTiers:[tier('電子帳單',2.5,.5,['帳單e化'],150),tier('電子帳單及成功自扣',3,1,['帳單e化及成功自扣'],150)],
  excludedKeywords:['保費','超商','全聯','大全聯','繳費','小額支付','Netflix','ChatGPT','Gemini','Steam','Nintendo','PlayStation','Google One','Google Services','Apple Pay','Google Pay','Samsung Pay'],
  quotaInfo:'網路加碼2%須帳單e化，每期帳單上限150元；基本回饋另依資格。實體感應支付不視為網購；排除保費、超商、指定訂閱等。分期只適用網路加碼，未納入此試算。'},
 {...common,id:'review_ubear_subscription_202609',title:'U Bear 指定數位訂閱10%（每期上限100元）',category:'數位訂閱',baseRate:0,promoRate:10,rewardAmount:10,
  rewardCalculationMode:'FLAT',rewardTiers:[],matchedMerchants:['Netflix','ChatGPT','Gemini','Steam','Nintendo','PlayStation'],searchKeywords:'數位訂閱 Netflix ChatGPT Gemini Steam Nintendo PlayStation',
  capAmount:100,capScope:'TOTAL',eligibilityRequirements:['直接在指定平台消費，帳單名稱須符合官方認列'],
  excludedKeywords:['PayPal','代扣繳'],
  quotaInfo:'指定平台依請款名稱認列；回饋總額每期100元，達上限後不再回饋，不能加一般或網路回饋。Gemini須依Google One／Google Services請款規則。'}
];
for(const r of data.rules){
 if(r.id==='rule_ubear_jp_booking'){
  r.quickSearchEligible=false;r.accuracyReview={status:'CONFLICT',checkedAt,sourceUrl:source,issues:['MIXED_ONLINE_AND_JAPAN_PHYSICAL_RATES']};
  r.validationIssues=[...new Set([...(r.validationIssues||[]),'MIXED_ONLINE_AND_JAPAN_PHYSICAL_RATES'])];
 }
}
data.rules=data.rules.filter(r=>!corrected.some(c=>c.id===r.id)).concat(corrected);
data.version += data.version.includes('-ubear-review')?'':'-ubear-review';
fs.writeFileSync(file,JSON.stringify(data,null,2));
console.log('Added 3 separately scoped official U Bear rules; quarantined mixed rate rule.');
