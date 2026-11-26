// One-time manual term review from the official 2026 digital-insurance card page.
const fs = require('node:fs');
const path = require('node:path');
const A = require('../../accuracy-core.js');
const file = path.resolve(__dirname, '../../data.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const rule = data.rules.find(r => r.id === 'rule_digital_insurance');
if (!rule) throw new Error('digital_insurance_rule_missing');
const source = 'https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card/inscard';
// Do not renew the fourteen-day source clock by rerunning this script.
const checkedAt = '2026-11-03T21:33:00+08:00';
Object.assign(rule, {
  cardId: 'card_玉山銀行_103', bank: '玉山銀行', associationStatus: 'matched',
  eligibleCardScope: 'SPECIFIC_CARD', offerDomain: 'CARD',
  title: '玉山數位保險卡：國內保費一次付清 1.2% 玉山 e point',
  sourceUrl: source, validFrom: '2026-01-01', validUntil: '2026-12-31',
  baseRate: 1.2, promoRate: 0, rewardType: 'points', rewardUnit: 'percent',
  rewardAmount: null, pointValueTwd: 1, capAmount: null, capScope: 'NONE',
  capPeriod: '', minimumSpend: 0, spendBasis: 'PER_TRANSACTION',
  roundingMode: 'FLOOR', rewardCalculationMode: 'FLAT', rewardTiers: [],
  needReg: false, regDeadline: '', registrationStart: '', registrationEnd: '',
  registrationMethods: [],
  eligibilityRequirements: ['玉山數位保險卡扣繳國內新臺幣計價之首期或續期保費',
    '保費一次付清；分期屬另一方案且需登錄'],
  excludedKeywords: ['南山人壽躉繳型保費','玉山銀行分行通路躉繳保費',
    '其他躉繳保費','三商美邦投資型保單','已享其他信用卡保險活動回饋',
    '分期保費','取消交易'],
  benefitSummary: '國內新臺幣保費一次付清享 1.2% 玉山 e point，無上限；逐筆無條件捨去至整數，分期方案另有登錄及門檻。',
  quotaInfo: '一次付清 1.2% 玉山 e point 無上限；須排除躉繳、指定投資型保單及其他保險活動回饋。',
  quickSearchEligible: false, validationIssues: [], fetchedAt: checkedAt,
  cardLinkEvidence: {method: 'official_card_product_page', sourceUrl: source,
    locator: '數位保險卡專屬優惠／L242-L259'}
});
rule.sourceFacts = {checkedAt, sourceUrl: source,
  locators: {titleAndPeriod: 'L242-L254', eligibility: 'L254-L259',
    exclusions: 'L258-L260', rounding: 'L263', pointValue: 'L235-L237'}};
delete rule.unresolvedCardId;
const locators = {
  title: '數位保險卡專屬優惠／L242-L254',
  cardEligibility: '數位保險卡專屬優惠／L254-L259',
  reward: '一次付清1.2%／L248-L259',
  rewardType: '玉山 e point／L248-L250、L235-L237',
  validFrom: '活動期間／L252', validUntil: '活動期間／L252',
  cap: '回饋無上限／L259',
  minimumSpend: '一次付清方案／L248-L259',
  exclusions: '一次付清方案注意事項／L258-L260',
  rounding: '玉山 e point 逐筆捨去／L263'
};
const fields = Object.fromEntries(Object.entries(locators).map(([field, locator]) =>
  [field, {status: 'supported', sourceUrl: source, locator}]));
fields.registration = {status: 'not_applicable', sourceUrl: source,
  locator: '一次付清方案及另一分期方案／L242-L267',
  reason: '一次付清 1.2% 段落未要求登錄；緊接的分期方案明確另列需登錄'};
rule.termEvidence = {sourceUrl: source, checkedAt, method: 'manual_official_terms_read', fields};
rule.accuracyReview = {status: 'SOURCE_CHECKED', checkedAt, sourceUrl: source,
  fields: Object.keys(A.termsSnapshot(rule)), issues: [], method: 'official_terms_read',
  evidenceSources: [source], evidence: rule.benefitSummary,
  termsSnapshot: A.termsSnapshot(rule)};
rule.evidenceStatus = 'SOURCE_CHECKED';
data.version = '2026.11.03-v233000-esun-digital-insurance-review';
fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
console.log(`digital insurance reviewed=${A.isReviewed(rule)}; quickSearch=${rule.quickSearchEligible}`);
