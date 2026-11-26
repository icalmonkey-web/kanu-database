const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const rule=data.rules.find(r=>r.id==='rule_ece0d2ee5916fccdb0fe');
if(!rule||rule.promoRate!==10||rule.rewardAmount!==10||!rule.needReg)throw Error('Unexpected Next Bank rule');
Object.assign(rule,{
  title:'將來支付全聯及四大超商：單筆滿100元贈10 N點',
  offerDomain:'PAYMENT',paymentProvider:'將來支付',
  promoRate:0,rewardType:'points',rewardUnit:'points',rewardAmount:10,
  rewardCalculationMode:'FLAT',spendBasis:'PER_TRANSACTION',
  capAmount:30,capPeriod:'MONTHLY',campaignCapAmount:210,
  validFrom:'2026-06-24',validUntil:'2026-12-31',
  registrationStart:'2026-06-24',registrationEnd:'',registrationCycle:'CAMPAIGN',
  quotaInfo:'單筆滿100元贈10 N點；每戶每月最多30點、活動期間最多210點；每月總量90,000點、活動期間630,000點，是否額滿待查。',
  eligibilityRequirements:['將來銀行存戶','全聯福利中心（不含大全聯）或四大超商實體門市','使用將來支付出示付款碼或掃碼','單筆滿100元','於將來銀行 App 完成活動登錄'],
  quickSearchEligible:false,
  validationIssues:['REGISTRATION_END_UNVERIFIED','LIVE_MONTHLY_AND_CAMPAIGN_QUOTA_UNVERIFIED'],
  sourceFacts:{checkedAt:'2026-11-04',sourceUrl:rule.sourceUrl,
    locators:{dates:'L66-L67',places:'L69-L73',rewardAndCaps:'L74-L75',registration:'L76',sharedQuota:'L80-L81'}}
});
data.version='2026.11.04-v200100-nextbank-fixed-points';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Corrected Next Bank 10 N points, monthly and campaign caps; registration remains blocked');
