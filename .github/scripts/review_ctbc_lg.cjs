// Fixed manual review of the official LG activity section; rerunning does not extend freshness.
const fs = require('node:fs');
const path = require('node:path');
const A = require('../../accuracy-core.js');
const file = path.resolve(__dirname, '../../data.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const rule = data.rules.find(r => r.id === 'rule_0056b90e9684f6396cb5');
if (!rule) throw new Error('lg_rule_missing');
const source = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_shopping.html';
const checkedAt = '2026-11-03T21:30:00+08:00';
Object.assign(rule, {
  title: 'LG官方線上商城：單筆滿 NT$20,000 加碼 LINE POINTS 500點',
  sourceUrl: source, validFrom: '2026-09-01', validUntil: '2026-12-31',
  baseRate: 0, promoRate: 0, rewardType: 'points', rewardUnit: 'points',
  rewardAmount: 500, pointValueTwd: null, capAmount: 500, capScope: 'PROMO',
  capPeriod: 'CAMPAIGN', minimumSpend: 20000, spendBasis: 'PER_TRANSACTION',
  roundingMode: 'ROUND', rewardCalculationMode: 'FLAT', rewardTiers: [],
  needReg: false, regDeadline: '', registrationStart: '', registrationEnd: '', registrationMethods: [],
  eligibilityRequirements: [
    '每週一至週五於LG官方線上商城消費單筆滿NT$20,000',
    '付款前已註冊台灣LINE Pay帳號並同意行銷資訊提供政策',
    '綁定中國信託LINE Pay信用卡或簽帳金融卡，透過LINE Pay付款',
    '依符合資格交易時序核算；當月及活動總點數額滿即停止'
  ],
  excludedKeywords: ['任何分期付款','LINE POINTS折抵金額','LINE Pay優惠券折抵金額','退款交易'],
  quotaInfo: '每LINE Pay帳號活動期間最高500點；總限量200,000點，9至12月每月各40,000、60,000、60,000、40,000點，額滿為止。',
  benefitSummary: '週一至週五單筆滿NT$20,000加碼固定LINE POINTS 500點，須LINE Pay綁定中信LINE Pay卡付款；一般消費1%另行發點，不併入本活動固定獎勵試算。',
  quickSearchEligible: false, validationIssues: [], fetchedAt: checkedAt
});
const locators = {
  title:'LG官方線上商城活動／L269-L274',
  cardEligibility:'參加資格／L274、L277-L281',
  reward:'固定加碼500點／L274-L276', rewardType:'LINE POINTS／L274-L276',
  validFrom:'活動卡片／L61-L65', validUntil:'活動卡片／L61-L65',
  cap:'帳號與月總量／L275', minimumSpend:'單筆NT$20,000／L274',
  exclusions:'分期、折抵及退款／L282、L285-L291',
  rounding:'LINE POINTS通用條款／L285-L286'
};
const fields = Object.fromEntries(Object.entries(locators).map(([key,locator]) =>
  [key,{status:'supported',sourceUrl:source,locator}]));
fields.registration = {status:'not_applicable',sourceUrl:source,
  locator:'LG活動完整條款／L273-L299',reason:'本活動沒有銀行登錄步驟；付款前須完成LINE Pay註冊與行銷政策同意'};
rule.termEvidence = {sourceUrl:source,checkedAt,method:'manual_official_terms_read',fields};
rule.accuracyReview = {status:'SOURCE_CHECKED',checkedAt,sourceUrl:source,
  fields:Object.keys(A.termsSnapshot(rule)),issues:[],method:'official_terms_read',
  evidenceSources:[source],evidence:rule.benefitSummary,termsSnapshot:A.termsSnapshot(rule)};
rule.evidenceStatus = 'SOURCE_CHECKED';
data.version = '2026.11.03-v220000-ctbc-lg-review';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`LG reviewed=${A.isReviewed(rule)}; quickSearch=${rule.quickSearchEligible}`);
