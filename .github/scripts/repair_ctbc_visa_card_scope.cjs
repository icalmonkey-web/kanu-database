// Only offers with explicit official 2026 product and debit scope are changed.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const specs={
  rule_141a6550938b29d8ba13:['page_food.html','Uber Eats活動・注意事項第1點',true],
  rule_77b16b4262cd2c2704ad:['page_food.html','星巴克活動・注意事項第1點',true],
  rule_fbadc5644cfad449e41d:['page_shopping.html','淘寶活動・注意事項第1點',true],
  review_ctbc_linepay_shopee_2026h2:['page_shopping.html','蝦皮購物活動・注意事項第1點',true],
  rule_d06f4a5bdc36a2ea8e23:['page_life.html','Netflix活動・注意事項第1點',true],
  review_ctbc_shopping_coupang_discount_2026h2:['page_shopping.html','酷澎活動①・注意事項第1、9點',false],
  review_ctbc_shopping_coupang_points_2026h2:['page_shopping.html','酷澎活動②・注意事項第1點',true]
};
for(const [id,[page,section,debit]] of Object.entries(specs)){
  const r=data.rules.find(x=>x.id===id);
  if(!r||!['card_中國信託_51','card_中國信託_241'].includes(r.cardId))throw Error(`Unexpected rule/card: ${id}`);
  if(!r.sourceUrl?.endsWith('/'+page))throw Error(`Official source mismatch: ${id}`);
  if(!Array.isArray(r.fundingMethods)||!r.fundingMethods.some(x=>/LINE Pay Visa/.test(x)))throw Error(`Visa eligibility missing: ${id}`);
  r.cardId='card_中國信託_241';
  r.eligibleCardIds=debit?['card_中國信託_241','card_中國信託_328']:['card_中國信託_241'];
  r.cardAssociationEvidence={sourceUrl:r.sourceUrl,sourceSection:section,
    observation:debit?'官方限 LINE Pay Visa 卡，含簽帳金融卡':'官方限 LINE Pay Visa 信用卡，排除 Visa 金融卡',
    checkedAt:'2026-11-04'};
  if(debit && !r.fundingMethods.some(x=>/含簽帳金融卡/.test(x)))
    r.fundingMethods=r.fundingMethods.map(x=>x.replace(/(LINE Pay Visa卡)/,'$1（含簽帳金融卡）'));
}
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`Visa credit/debit associations checked=${Object.keys(specs).length}`);
