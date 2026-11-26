// Partial official correction; not a full review or registration window certification.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const r=data.rules.find(x=>x.id==='rule_a84722535184bc3700e1');
if(!r) throw new Error('overseas_rule_missing');
const excludedCountries=['奧地利','比利時','保加利亞','克羅埃西亞','賽普勒斯',
  '捷克','丹麥','愛沙尼亞','芬蘭','法國','德國','希臘','匈牙利','愛爾蘭',
  '義大利','拉脫維亞','立陶宛','盧森堡','馬爾他','荷蘭','波蘭','葡萄牙',
  '羅馬尼亞','斯洛伐克','斯洛維尼亞','西班牙','瑞典','英國','冰島',
  '列支敦斯登','挪威'];
const registrationWindows=[];
for(let d=new Date('2026-10-01T00:00:00Z');d<=new Date('2026-12-31T00:00:00Z');d.setUTCDate(d.getUTCDate()+1)){
  if(d.getUTCDay()===2) registrationWindows.push({start:d.toISOString().slice(0,10)+'T00:00:00+08:00'});
}
Object.assign(r,{
  baseRate:2.8,promoRate:2.2,rewardType:'points',rewardUnit:'percent',
  rewardAmount:null,pointValueTwd:null,capAmount:450,capScope:'PROMO',capPeriod:'CAMPAIGN',
  roundingMode:'ROUND_COMPONENT',rewardCalculationMode:'FLAT',
  maxRateRequires:['每週二00:00起限量開放3,000名登錄，成功登錄後國外實體面對面交易',
    '額外加碼2.2%活動總限量20,000名，額滿不再回饋'],
  eligibilityRequirements:['須於中國信託活動登錄平台成功登錄',
    '限中國信託LINE Pay信用卡，簽帳金融卡不適用',
    '國外實體店面面對面交易，含實體卡及Apple Pay／Google Pay／Samsung Pay實體店支付',
    '交易日介於2026/10/1-12/31且於2027/1/20前請款入帳'],
  excludedCountries,
  excludedKeywords:['簽帳金融卡','網路交易','條碼支付','第三方支付',
    '銀行不回饋項目',...excludedCountries,'取消或退貨交易'],
  registrationUrl:'',registrationMethods:[],registrationStart:'',registrationEnd:'',registrationWindows,
  quotaInfo:'每週二00:00開放3,000名登錄；加碼2.2%每歸戶活動期間上限450點，活動總限量20,000名。',
  benefitSummary:'國外實體面對面消費最高5% LINE POINTS＝原2.8%＋登錄加碼2.2%；部分歐洲國家不回饋，登錄窗口及即時名額仍待確認。',
  quickSearchEligible:false,
  validationIssues:[...new Set([...(r.validationIssues||[]).filter(x=>x!=='REGISTRATION_WINDOW_AND_COUNTRY_EXCLUSIONS_UNVERIFIED'),
    'REGISTRATION_WINDOW_AND_GENERAL_EXCLUSIONS_UNVERIFIED'])],
  sourceFacts:{checkedAt:'2026-11-03T21:30:00+08:00',
    sourceUrl:'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_travel.html',
    locators:{listing:'L49-L54',cardAndPeriod:'L290-L292',
      paymentAndCap:'L293-L295',quotaAndPosting:'L295-L299',
      excludedCountries:'https://service.ctbcbank.com/FAQ/Page01?kmid=15719 L17-L33 (2026)'}},
  fetchedAt:'2026-11-03T21:30:00+08:00'
});
data.version='2026.11.03-v213000-ctbc-overseas-registration-repair';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
