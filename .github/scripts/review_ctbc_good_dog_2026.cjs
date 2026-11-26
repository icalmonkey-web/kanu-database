// Fixed manual reading of the 2026 CTBC 好狗運 terms; reruns do not renew the review.
const fs = require('node:fs');
const path = require('node:path');
const A = require('../../accuracy-core.js');
const file = path.resolve(__dirname, '../../data.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const r = data.rules.find(x => x.id === 'rule_8993c54bfe963a2c628a');
if (!r) throw new Error('good_dog_rule_missing');
const source = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html';
const checkedAt = '2026-11-08T00:20:00+08:00';
Object.assign(r, {
  title: '好狗運：週一至週五單筆滿NT$1,300贈LINE POINTS 30點',
  sourceUrl: source, cardId: 'card_中國信託_51',
  eligibleCardIds: ['card_中國信託_51', 'card_中國信託_241', 'card_中國信託_242',
    'card_中國信託_324', 'card_中國信託_327', 'card_中國信託_328'],
  eligibleCardScope: 'SELECTED_CARDS',
  cardAssociationEvidence: { sourceUrl: source,
    locator: '好狗運活動注意事項第1點；頁面第148行' },
  offerDomain: 'CARD', paymentProvider: '',
  fundingMethods: ['中國信託LINE Pay卡直接刷卡或綁定LINE Pay、行動支付、第三方支付'],
  validFrom: '2026-01-01', validUntil: '2026-12-31', eligibleWeekdays: [1,2,3,4,5],
  baseRate: 0, promoRate: 0, rewardType: 'points', rewardUnit: 'points',
  rewardAmount: 30, pointValueTwd: null, capAmount: 30,
  capPeriod: 'MONTHLY', capScope: 'PROMO',
  minimumSpend: 1300, spendBasis: 'PER_TRANSACTION',
  roundingMode: 'ROUND', rewardCalculationMode: 'FLAT', rewardTiers: [],
  needReg: false, regDeadline: '', registrationStart: '', registrationEnd: '',
  registrationUrl: '', registrationMethods: [],
  eligibilityRequirements: [
    '每週一至週五於全臺好狗運貓狗福利中心消費單筆滿NT$1,300',
    '持中國信託LINE Pay卡直接刷卡或綁定LINE Pay、行動支付、第三方支付',
    '每人每月限回饋一次；需確認本月尚未領取'
  ],
  excludedKeywords: ['分期交易', '付款失敗', '訂單退貨'],
  quotaInfo: '每人每月限回饋一次，固定30點；商店展店或撤店依商店公告是否參與。',
  benefitSummary: '週一至週五單筆滿NT$1,300贈LINE POINTS 30點，每人每月一次；須確認店家參與及本月尚未領取。',
  quickSearchEligible: false, validationIssues: [], fetchedAt: checkedAt
});
const locators = {
  title:'好狗運列表與活動標題／L40-L44、L145-L147',
  cardEligibility:'中國信託LINE Pay卡及綁定付款／L148',
  reward:'固定30點／L148', rewardType:'LINE POINTS／L146-L148',
  validFrom:'列表活動日期／L40-L44', validUntil:'列表活動日期／L40-L44',
  cap:'每人每月限一次／L148', minimumSpend:'單筆NT$1,300／L148',
  exclusions:'分期、付款失敗與退貨／L148-L150',
  rounding:'固定30點；一般點數入點取整／L148、L152',
  schedule:'每週一至週五／L148'
};
const fields = Object.fromEntries(Object.entries(locators).map(([key, locator]) =>
  [key, {status:'supported', sourceUrl:source, locator}]));
fields.registration = {status:'not_applicable', sourceUrl:source,
  locator:'好狗運活動完整注意事項／L147-L154',
  reason:'此活動沒有銀行登錄步驟；LINE Pay帳號綁定是收點資格'};
r.termEvidence = {sourceUrl:source, checkedAt, method:'manual_official_terms_read', fields};
r.accuracyReview = {status:'SOURCE_CHECKED', checkedAt, sourceUrl:source,
  fields:Object.keys(A.termsSnapshot(r)), issues:[], method:'official_terms_read',
  evidenceSources:[source], evidence:r.benefitSummary, termsSnapshot:A.termsSnapshot(r)};
r.evidenceStatus = 'SOURCE_CHECKED';
data.version = '2026.11.08-v335000-gooddog';
fs.writeFileSync(file, JSON.stringify(data,null,2)+'\n');
console.log(`good dog reviewedOnEligibleDay=${A.isReviewed(r,new Date('2026-11-09T02:00:00Z'))} quickSearch=${r.quickSearchEligible}`);
