// HSBC calls these Card+ login, installment application and lounge booking,
// respectively. They are not promotional registration tasks.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const appIds=['rule_47a58937296d266f1947','rule_7321d1cf917b19af0434','rule_d480574a89ad14beec9a','rule_ede6e42f7c869bb77e96','rule_9e44e2c771cdd2f31f36','rule_68bd7592f9bcc80456f4'];
const loungeIds=['rule_fa6ce36b01a5927f26e8','rule_0f612849011eb074fcee'];
function get(id){const r=data.rules.find(x=>x.id===id);if(!r||r.needReg)throw Error(`Unexpected HSBC rule ${id}`);return r;}
for(const id of appIds){
  const r=get(id);
  if(r.registrationMethods?.[0]?.label!=='銀行 App 登錄')throw Error(`Unexpected app method ${id}`);
  r.appLoginRequirement={appName:'HSBC Card+',deadline:'核卡後30天內',sourceUrl:r.sourceUrl,
    evidence:'官方條款使用「登入滙豐銀行信用卡行動App」，並非活動登錄'};
  r.registrationMethods=[];
  r.quickSearchEligible=false;
  r.validationIssues=[...new Set([...(r.validationIssues||[]),'CURRENT_OFFICIAL_TERMS_URL_UNAVAILABLE'])];
}
const installment=get('rule_f34ef295f82e5da66608');
if(installment.registrationMethods?.[0]?.label!=='電話登錄')throw Error('Unexpected installment method');
installment.applicationMethods=installment.registrationMethods.map(m=>({...m,label:'電話申辦消費分期'}));
installment.registrationMethods=[];
installment.quickSearchEligible=false;
installment.validationIssues=[...new Set([...(installment.validationIssues||[]),'INSTALLMENT_TERMS_NOT_LOCATED_AT_SOURCE'])];
for(const id of loungeIds){
  const r=get(id);
  if(!r.registrationUrl||!r.registrationMethods?.length)throw Error(`Unexpected lounge methods ${id}`);
  r.bookingUrl=r.registrationUrl;
  r.bookingMethods=r.registrationMethods;
  r.registrationUrl='';
  r.registrationMethods=[];
  r.quickSearchEligible=false;
  r.validationIssues=[...new Set([...(r.validationIssues||[]),'CURRENT_OFFICIAL_LOUNGE_TERMS_URL_UNAVAILABLE','BOOKING_DESTINATIONS_NEED_RECHECK'])];
}
data.version='2026.11.04-vhsbc-actions-separated';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('Separated 6 app logins, 1 installment application and 2 lounge bookings');
