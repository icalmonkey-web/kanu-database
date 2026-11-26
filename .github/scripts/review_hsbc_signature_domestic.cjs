// Manual field review of the current Chinese HSBC Cashback Signature terms.
const fs = require('node:fs');
const path = require('node:path');
const A = require('../../accuracy-core.js');

const file = path.resolve(__dirname, '../../data.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const rule = data.rules.find(r => r.id === 'rule_b976c4a9577d484419b6');
if (!rule) throw new Error('hsbc_signature_domestic_rule_missing');
const source = 'https://www.hsbc.com.tw/zh-tw/credit-cards/products/cashback-signature/';
// A rerun must never refresh the fourteen-day evidence clock without rereading the source.
const checkedAt = '2026-11-03T21:25:00+08:00';
Object.assign(rule, {
  title: '滙豐現金回饋御璽卡國內合格消費 1.22% 現金積點',
  sourceUrl: source, validFrom: '2026-10-01', validUntil: '2026-12-31',
  baseRate: 1.22, promoRate: 0, rewardType: 'points', rewardUnit: 'percent',
  rewardAmount: null, pointValueTwd: 1, capAmount: null, capScope: 'NONE',
  capPeriod: '', spendBasis: 'STATEMENT', roundingMode: 'ROUND', minimumSpend: 0,
  needReg: false, registrationStart: '', registrationEnd: '', registrationMethods: [],
  eligibilityRequirements: ['交易商店國別為台灣且交易幣別為新臺幣；須為符合資格的一般交易',
    '正附卡消費合併計算；按當期帳單同回饋比率消費扣退貨後四捨五入'],
  excludedKeywords: ['年費','掛失費','循環信用利息','預借現金','匯轉金','通信貸款','餘額代償',
    '相關手續費及利息','逾期繳款費用','基金扣款','各項稅款','學費','中華電信繳費',
    '台電營業用電及高壓電電費','交通違規罰鍰','旅行支票','博奕籌碼','退貨交易',
    '取消交易','爭議款','非持卡人交易','公共事業代扣繳','公務機關暨醫療院所繳費平台',
    '財金電子化繳費稅平台','公部門及公立醫療機構','醫指付','特約商店分期付款',
    '便利商店自有支付 iCash pay','便利商店自有支付 FAMI PAY'],
  quotaInfo: '國內合格交易享 1.22% 現金積點，無上限、無最低門檻；每期帳單同類消費合計扣退貨後四捨五入。',
  benefitSummary: '國內合格消費 1.22% 現金積點；每期帳單彙總計算，1 點可折抵 NT$1，單筆金額不代表實際入點。',
  quickSearchEligible: false, validationIssues: [], fetchedAt: checkedAt,
  associationStatus: 'matched'
});
const locators = {
  title: '現金回饋須知／L371-L375',
  cardEligibility: '現金積點活動辦法／L384-L387',
  reward: '現金積點回饋比率及使用／L388-L390、L424-L429',
  rewardType: '現金積點回饋比率／L388-L389',
  validFrom: '優惠期間／L386', validUntil: '優惠期間／L386',
  cap: '現金積點回饋無上限／L401-L402',
  minimumSpend: '現金回饋須知／L371-L375',
  exclusions: '符合資格消費／L403-L420',
  rounding: '現金積點計算／L392-L400'
};
const fields = Object.fromEntries(Object.entries(locators).map(([field, locator]) =>
  [field, {status: 'supported', sourceUrl: source, locator}]));
fields.registration = {status: 'not_applicable', sourceUrl: source,
  locator: '現金積點活動辦法／L384-L420',
  reason: '本卡國內一般消費現金積點條款未列活動登錄步驟；新戶首刷禮屬另一活動'};
rule.termEvidence = {sourceUrl: source, checkedAt, method: 'manual_official_terms_read', fields};
rule.accuracyReview = {status: 'SOURCE_CHECKED', checkedAt, sourceUrl: source,
  fields: Object.keys(A.termsSnapshot(rule)), issues: [], method: 'official_terms_read',
  evidenceSources: [source], evidence: rule.benefitSummary,
  termsSnapshot: A.termsSnapshot(rule)};
rule.evidenceStatus = 'SOURCE_CHECKED';
data.version = '2026.11.03-v223500-hsbc-domestic-review';
fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
console.log(`HSBC domestic reviewed; current eligibility=${A.assessment(rule).level}; cash calculator=${A.calculate(rule, 10000).calculable}`);
