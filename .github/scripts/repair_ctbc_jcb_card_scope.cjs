// Official LINE Pay JCB merchant terms name the JCB card as the eligible product.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const evidence={
  rule_26ab533bf77c05b5133c:['page_food.html','SUSHIRO 活動注意事項第1點'],
  rule_1e1328f849591e9e8f10:['page_food.html','Komeda 活動注意事項第1點'],
  rule_e74497743e60187f7f2a:['page_food.html','MOS Burger 活動注意事項第1點'],
  rule_a7fcac04b54ea87a2f43:['page_food.html','藏壽司活動注意事項第1點'],
  review_ctbc_linepay_uniqlo_2026h2:['page_shopping.html','UNIQLO 活動注意事項第1點'],
  review_ctbc_linepay_gu_2026h2:['page_shopping.html','GU 活動注意事項第1點']
};
for(const [id,[page,section]] of Object.entries(evidence)){
  const r=data.rules.find(x=>x.id===id);
  if(!r||!['card_中國信託_51','card_中國信託_242'].includes(r.cardId))throw Error(`Unexpected rule/card: ${id}`);
  if(!Array.isArray(r.fundingMethods)||!r.fundingMethods.some(x=>/LINE Pay JCB卡/.test(x)))throw Error(`JCB terms missing: ${id}`);
  if(!r.sourceUrl?.endsWith('/'+page))throw Error(`Official source mismatch: ${id}`);
  r.cardId='card_中國信託_242';
  r.cardAssociationEvidence={sourceUrl:r.sourceUrl,sourceSection:section,
    observation:'官方活動條款指定中國信託 LINE Pay JCB 卡',checkedAt:'2026-11-04'};
}
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`JCB card associations checked=${Object.keys(evidence).length}`);
