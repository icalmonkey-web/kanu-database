const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const entries=[
  {id:'rule_8807edb9cc0a7446a63a',promo:4.5,requiresReg:true,locator:'L266-L307'},
  {id:'rule_8e664cc6701709f25c11',promo:2.5,requiresReg:false,locator:'L308-L344'},
  {id:'rule_0574b56f47ff0e503186',promo:2.5,requiresReg:false,locator:'L345-L384'}
];
for(const entry of entries){
 const r=data.rules.find(x=>x.id===entry.id);
 if(!r||r.rewardAmount!==250||r.promoRate!==entry.promo||r.needReg!==entry.requiresReg)throw Error(`Unexpected e-card rule ${entry.id}`);
 Object.assign(r,{
   rewardAmount:null,rewardUnit:'percent',pointValueTwd:1,
   capAmount:250,capScope:'PROMO',capPeriod:'STATEMENT',
   validFrom:'2026-07-01',validUntil:'2026-12-31',minimumSpend:0,
   roundingMode:'FLOOR_COMPONENT',quickSearchEligible:false,
   validationIssues:[...(r.validationIssues||[]),'CARD_VARIANT_AND_PAYMENT_METHOD_NOT_MACHINE_CHECKED',
     ...(entry.requiresReg?['STATEMENT_REGISTRATION_DEADLINE_NOT_MACHINE_CHECKED']:[])],
   sourceFacts:{checkedAt:'2026-11-04',sourceUrl:r.sourceUrl,
     locators:{terms:entry.locator,cap:'加碼部分每期上限250點',rounding:'e point逐筆無條件捨去至整數'}}
 });
 for(const tier of r.rewardTiers||[]){
   if(tier.capAmount===250)tier.capPeriod='STATEMENT';
 }
}
data.version='2026.11.04-v201500-esun-ecard-caps';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Corrected 3 Esun digital e-card statement caps and point semantics');
