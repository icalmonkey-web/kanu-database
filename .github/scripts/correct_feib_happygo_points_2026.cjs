const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const rows=[
 {id:'rule_5a93150fd5808fac5b8b',from:'2026-01-01',locator:'NCTOP L24,L52',card:'New Century 世界卡／無限卡'},
 {id:'rule_c5039b4990adc6a3ac89',from:'2026-07-01',locator:'HappyCard L71-L87',card:'遠東頂級快樂卡'}
];
for(const item of rows){
 const r=data.rules.find(x=>x.id===item.id);
 if(!r||r.rewardAmount!==1||r.rewardType!=='points')throw Error(`Unexpected HAPPY GO rule ${item.id}`);
 Object.assign(r,{
  title:`${item.card}一般消費每滿100元得1點HAPPY GO`,
  baseRate:0,promoRate:0,rewardType:'points',rewardUnit:'points_per_spend',rewardAmount:null,
  pointEarnRate:{spendTwd:100,points:1},
  benefitSummary:'一般消費每滿NT$100累積1點HAPPY GO；快樂購特約商店最高2點含特約商店提供點數',
  capAmount:null,capPeriod:'',validFrom:item.from,validUntil:'2026-12-31',
  quickSearchEligible:false,
  validationIssues:[...(r.validationIssues||[]),'POINTS_PER_SPEND_NOT_MACHINE_CALCULABLE','PARTNER_POINT_CONTRIBUTION_UNVERIFIED'],
  sourceFacts:{checkedAt:'2026-11-04',sourceUrl:r.sourceUrl,locators:{terms:item.locator}}
 });
 for(const tier of r.rewardTiers||[]){tier.totalRate=0;tier.baseRate=0;tier.promoRate=0;tier.capAmount=null;}
}
data.version='2026.11.04-v204000-feib-happygo-points';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Corrected 2 FEIB HAPPY GO point accumulation rules');
