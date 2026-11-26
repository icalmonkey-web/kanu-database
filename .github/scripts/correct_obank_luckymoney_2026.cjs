const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const rule=data.rules.find(r=>r.id==='rule_229343b9772b7b044c12');
if(!rule||rule.rewardAmount!==88||rule.promoRate!==88||rule.needReg)throw Error('Unexpected Lucky Money rule');
Object.assign(rule,{
  title:'Lucky Money 回饋金撲滿：7至9月連續達標一次贈88元',
  baseRate:0,promoRate:0,rewardType:'cash',rewardUnit:'twd',rewardAmount:88,
  capAmount:88,capPeriod:'CAMPAIGN',spendBasis:'MULTI_MONTH_CUMULATIVE',minimumSpend:888,
  eligibilityRequirements:['2026/7/31前成功開啟回饋金撲滿','2026年7、8、9月連續三個月，每月指定行動支付一般消費累積滿888元','每人活動期間限回饋一次','限額3,000名，依開啟撲滿順序排序'],
  rewardTiers:[{name:'三個月連續達標一次贈88元',totalRate:0,baseRate:0,promoRate:0,isDefault:false,
    requirements:['7月、8月、9月每月累積指定行動支付消費滿888元'],capAmount:88,capPeriod:'CAMPAIGN'}],
  maxRateRequires:['7月、8月、9月每月累積指定行動支付消費滿888元','7/31前開啟撲滿'],
  quotaInfo:'每人一次，限額3,000名，依成功開啟撲滿順序排序；是否額滿待查',
  registrationMethods:[], registrationUrl:'',
  applicationMethods:[{type:'APP',label:'申辦 Lucky Money 回饋金撲滿',appName:'王道銀行 APP',path:['臺幣','臺幣總覽','回饋金撲滿立即申辦']}],
  quickSearchEligible:false,
  validationIssues:['MULTI_MONTH_CUMULATIVE_SPEND_NOT_MACHINE_CHECKED','HISTORICAL_ACTIVITY_TERMS_SOURCE_UNAVAILABLE'],
  sourceFacts:{checkedAt:'2026-11-04',sourceUrl:'https://www.o-bank.com/about/news/news-newslist?newsid=%7B4E789DDF-F550-4F3C-919F-FB169EE159F2%7D&tabName=main_default',
    locators:{terms:'2026/07/03 王道銀行新聞：7月底前開啟，7至9月連續三個月每月滿888元，一次回饋88元'}}
});
data.version='2026.11.04-vregistration-action-corrections';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Corrected expired O-Bank 88 TWD offer and removed false registration');
