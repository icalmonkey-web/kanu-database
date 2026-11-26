// The official 2026 ShopBack terms require the LINE Pay Visa credit card.
// This deliberately excludes Visa debit and unrelated network-specific offers.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const ids=data.rules.filter(r=>r.id.startsWith('review_ctbc_shopback_'));
if(ids.length!==16)throw Error(`Expected 16 ShopBack offers, found ${ids.length}`);
for(const r of ids){
  if(r.cardId!=='card_中國信託_51' && r.cardId!=='card_中國信託_241')
    throw Error(`Unexpected card association: ${r.id} ${r.cardId}`);
  if(!Array.isArray(r.fundingMethods)||!r.fundingMethods.some(x=>/LINE Pay Visa信用卡/.test(x)))
    throw Error(`Visa credit eligibility is missing: ${r.id}`);
  if(!/page_(food|shopping)\.html$/.test(r.sourceUrl||''))
    throw Error(`Unexpected official source: ${r.id}`);
  r.cardId='card_中國信託_241';
  r.cardAssociationEvidence={sourceUrl:r.sourceUrl,
    sourceSection:'SHOPBACK活動・注意事項／詳細活動辦法第1、3項',
    observation:'持有中國信託LINE Pay Visa卡，線上刷卡消費；簽帳金融卡與第三方支付不在資格內',
    checkedAt:'2026-11-04'};
}
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`ShopBack Visa credit card associations checked=${ids.length}`);
