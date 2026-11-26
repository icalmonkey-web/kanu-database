const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const entries=[
 {id:'rule_5036b814fc5e1e83202e',points:1,basis:'一般新增刷卡消費',locator:'L377-L379'},
 {id:'rule_45ac71e9e9d63a71fea7',points:3,basis:'百貨公司、餐廳、飯店新增刷卡消費',locator:'L380'},
 {id:'rule_86e75835845ffbb5a367',points:6,basis:'海外新增外幣刷卡消費',locator:'L381'},
 {id:'sc_pi_overseas',points:6,basis:'海外新增外幣刷卡消費',locator:'L381',duplicateOf:'rule_86e75835845ffbb5a367'}
];
for(const entry of entries){
 const r=data.rules.find(x=>x.id===entry.id);
 if(!r||r.cardId!=='card_渣打銀行_117'||!r.rewardAmount)throw Error(`Unexpected SC rule ${entry.id}`);
 Object.assign(r,{
  title:`渣打優先理財無限卡${entry.basis}每10元得${entry.points}點`,
  baseRate:0,promoRate:0,rewardType:'points',rewardUnit:'points_per_spend',rewardAmount:null,
  pointEarnRate:{spendTwd:10,points:entry.points},
  benefitSummary:`${entry.basis}每滿NT$10累積${entry.points}點紅利積點（${entry.points}倍含基本點數）`,
  capAmount:null,capPeriod:'',minimumSpend:10,
  quickSearchEligible:false,
  validationIssues:[...(r.validationIssues||[]),'POINTS_PER_SPEND_NOT_MACHINE_CALCULABLE',
    ...(entry.duplicateOf?['DUPLICATE_OFFICIAL_OFFER']:[])],
  sourceFacts:{checkedAt:'2026-11-04',sourceUrl:r.sourceUrl,locators:{earnRate:entry.locator,redemption:'L382:每2000點可兌換50元'}}
 });
 if(entry.duplicateOf)r.duplicateOf=entry.duplicateOf;
 if(Array.isArray(r.rewardTiers))for(const tier of r.rewardTiers){tier.totalRate=0;tier.baseRate=0;tier.promoRate=0;}
}
data.version='2026.11.04-v202500-sc-point-multipliers';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Corrected 4 SC point-multiplier records; one duplicate retained as blocked');
