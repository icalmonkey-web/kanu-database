// Source-backed correction of two mixed coupon and LINE POINTS records.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const source='https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_travel.html';
for(const [id,section] of [
  ['rule_4fce09de6cf66f5030eb','格上租車活動・注意事項第1、2、6點'],
  ['lp-visa-twdaidrive','台灣代駕活動・注意事項第1、2、10點']]){
  const r=data.rules.find(x=>x.id===id);
  if(!r||!['card_中國信託_51','card_中國信託_241'].includes(r.cardId))throw Error(`Unexpected rule/card: ${id}`);
  r.bank='中國信託';r.cardId='card_中國信託_241';r.eligibleCardIds=['card_中國信託_241'];
  r.fundingMethods=['中國信託 LINE Pay Visa 信用卡直接刷卡'];
  r.sourceUrl=source;
  r.cardAssociationEvidence={sourceUrl:source,sourceSection:section,
    observation:'官方活動條款限定 LINE Pay Visa 信用卡；簽帳金融卡資格未獲證明',checkedAt:'2026-11-04'};
  r.quickSearchEligible=false;
  r.validationIssues=Array.from(new Set([...(r.validationIssues||[]).filter(x=>x!=='SOURCE_MISSING'),
    'COMPOSITE_COUPON_AND_POINTS_NEEDS_SPLIT']));
  r.rewardAmount=null;
  r.rewardType='points';r.rewardUnit='percent';
  r.capScope='PROMO';r.capPeriod='MONTHLY';
  if(id==='lp-visa-twdaidrive'){
    r.title='台灣代駕：LINE POINTS 6% 與優惠券（混合方案待拆）';
    r.baseRate=1;r.promoRate=5;r.capAmount=50;
    r.validFrom='2026-09-01';r.validUntil='2026-12-31';
    r.evidenceStatus='SOURCE_REFERENCE';
  }
}
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Mixed travel offers quarantined=2');
