// Split the issuer-specific terms published by icash Pay. Keep all four blocked
// until recurring dates, live bank quotas and registration can be checked.
const fs = require('node:fs');
const path = require('node:path');
const file = path.resolve(__dirname, '../../data.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const original = data.rules.find(r => r.id === 'rule_e5062b26fc4d515cb603');
if (!original || original.fundingMethods.length !== 4) throw Error('Unexpected original icash Pay rule');
const icash = 'https://www.icashpay.com.tw/advertMessage/view/id/2476';
const esun = 'https://www.esunbank.com/zh-tw/personal/credit-card/discount/shopInfo?sno=8023';
const issuers = [
  {id: 'rule_e5062b26fc4d515cb603', bank: '玉山銀行', funding: '玉山銀行全信用卡', quota: '每月限登錄1,200名', registration: true},
  {id: 'icashpay_wanjiafu_2026_cathay', bank: '國泰世華銀行', funding: '國泰世華icash聯名卡', quota: '每月銀行回饋總量15萬點'},
  {id: 'icashpay_wanjiafu_2026_hncb', bank: '華南銀行', funding: '華南銀行全信用卡', quota: '每月銀行回饋總量10萬點'},
  {id: 'icashpay_wanjiafu_2026_hsbc', bank: '滙豐銀行', funding: '滙豐銀行信用卡（公司卡、商務卡除外）', quota: '每月銀行回饋總量10萬點'}
];
const rules = issuers.map((issuer) => {
  const rule = structuredClone(original);
  Object.assign(rule, {
    id: issuer.id, bank: issuer.bank,
    title: `${issuer.bank} icash Pay 萬家福等通路 5% OPENPOINT`,
    fundingMethods: [issuer.funding],
    rewardAmount: null, rewardUnit: 'percent', rewardCalculationMode: 'FLAT',
    validFrom: '2026-09-10', validUntil: '2026-12-31',
    minimumSpend: 0,
    needReg: Boolean(issuer.registration),
    regDeadline: issuer.registration ? '每月15日10:00至當月最後一日23:59:59；須當月登錄，限正卡人' : '',
    registrationUrl: '',
    registrationMethods: issuer.registration ? [{type:'WEB', label:'玉山官方活動頁查當月登錄入口', url:esun, activityName:'icash Pay 萬家福等通路 5%'}] : [],
    quotaInfo: `每位 icash Pay 用戶每月最多回饋150點；${issuer.quota}；名額或點數池是否已額滿尚未驗證`,
    eligibilityRequirements: ['icash Pay用戶', `綁定${issuer.funding}`, '每月10日後指定週五至週日消費', ...(issuer.registration ? ['玉山正卡持卡人須每月登錄'] : [])],
    sourceUrl: issuer.registration ? esun : icash,
    quickSearchEligible: false,
    validationIssues: ['RECURRING_ELIGIBLE_DATES_NOT_MACHINE_CHECKED', 'LIVE_BANK_QUOTA_UNVERIFIED', ...(issuer.registration ? ['MONTHLY_REGISTRATION_STATUS_UNVERIFIED'] : [])],
    sourceFacts: {checkedAt:'2026-11-04', sourceUrl:issuer.registration ? esun : icash,
      locators: issuer.registration ? {terms:'活動辦法與各月登錄入口、指定消費日期'} : {terms:'活動期間、指定銀行優惠與注意事項'}},
    fetchedAt: '2026-11-04T00:00:00+08:00'
  });
  rule.rewardTiers[0].requirements = [issuer.funding, '單筆消費不限金額', '僅指定消費日', ...(issuer.registration ? ['每月須登錄'] : [])];
  rule.maxRateRequires = [...rule.rewardTiers[0].requirements];
  if (issuer.registration) rule.eligibleDateRanges = [
    ['2026-09-11','2026-09-13'],['2026-09-18','2026-09-20'],['2026-09-25','2026-09-27'],
    ['2026-10-10','2026-10-11'],['2026-10-16','2026-10-18'],['2026-10-23','2026-10-25'],['2026-10-30','2026-10-31'],
    ['2026-11-13','2026-11-15'],['2026-11-20','2026-11-22'],['2026-11-27','2026-11-29'],
    ['2026-12-11','2026-12-13'],['2026-12-18','2026-12-20'],['2026-12-25','2026-12-27']
  ].map(([from,until])=>({from,until}));
  return rule;
});
const index = data.rules.indexOf(original);
data.rules.splice(index, 1, ...rules);
data.version = '2026.11.04-vicashpay-issuer-split';
fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
console.log(`Split icash Pay promotion into ${rules.length} blocked issuer rules`);
