// Official issuer pages call these links service reservations, not campaign registration.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const entries=[
  {id:'rule_75661eedf72783c7f272',url:'https://www.youfirst.com.tw/feib/',locator:'無限次國際機場接送／立即預約'},
  {id:'rule_7ca28b718202881a8c5e',url:'https://www.youfirst.com.tw/feib/',locator:'首刷滿額加碼送／注意事項第2項：預約網站'},
  {id:'rule_4026053d9565e18e8223',url:'https://www.youfirst.com.tw/tcb/',locator:'國際機場接送／優惠預約方式'}
];
for(const entry of entries){
  const rule=data.rules.find(r=>r.id===entry.id);
  if(!rule||rule.needReg||rule.registrationUrl?.toLowerCase()!==entry.url.toLowerCase())throw Error(`Unexpected booking rule: ${entry.id}`);
  rule.bookingUrl=entry.url;
  rule.bookingMethods=(rule.registrationMethods||[]).map(method=>({...method}));
  rule.registrationUrl='';
  rule.registrationMethods=[];
  rule.bookingSourceEvidence={sourceUrl:rule.sourceUrl,locator:entry.locator,checkedAt:'2026-11-04'};
}
data.version='2026.11.04-vairport-booking-separated';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Separated 3 airport service bookings from registration');
