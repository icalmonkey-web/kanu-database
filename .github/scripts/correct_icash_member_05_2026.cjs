const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const r=data.rules.find(x=>x.id==='rule_e0de86b169c8af40b1cd');
if(!r||r.rewardAmount!==0.5||r.baseRate!==0.5||r.scope!=='ALL')throw Error('Unexpected icash Pay member offer');
Object.assign(r,{
 title:'統一超商 icash Pay 消費 0.5% OPENPOINT（詳情待核）',
 scope:'SPECIFIC',matchedMerchants:['7-ELEVEN'],
 baseRate:0.5,promoRate:0,rewardType:'points',rewardUnit:'percent',rewardAmount:null,pointValueTwd:1,
 validFrom:'2026-07-01',validUntil:'2026-12-31',
 benefitSummary:'官方會員優惠列表：統一超商使用 icash Pay 消費標示 0.5% OPENPOINT；詳細適用付款方式、排除與上限待核。',
 quickSearchEligible:false,
 validationIssues:['LISTING_ONLY_PAYMENT_AND_EXCLUSIONS_UNVERIFIED','MERCHANT_DETAIL_UNVERIFIED'],
 sourceFacts:{checkedAt:'2026-11-04',sourceUrl:r.sourceUrl,locators:{period:'L1-L5',merchantAndRate:'L7-L13',pointValue:'L95-L97'}}
});
data.version='2026.11.04-v205500-icash-member-scope';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Corrected icash Pay member listing scope and rate; detail remains blocked');
