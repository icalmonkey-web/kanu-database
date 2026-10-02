// Field-by-field official terms read on 2026-10-02. Never infer cash value of N points.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const file = path.join(root, 'data.json');
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const checkedAt = '2026-10-02T12:00:00+08:00';
const patches = {
  rule_9c70fd44c57790fe712f: {
    validFrom: '2026-07-01', validUntil: '2026-09-30', claimDeadline: '2026-10-15',
    rewardType: 'points', rewardUnit: 'percent', capAmount: null, capScope: 'NONE',
    spendBasis: 'PER_TRANSACTION', roundingMode: 'ROUND',
    issues: ['N_POINT_CASH_VALUE_NOT_VERIFIED'],
    evidence: 'Part 1 clauses 1, 3 and 4: purchase by September 30; claim by October 15; 0.5% N points, uncapped, rounded per transaction.'
  },
  rule_599877f136e1ea70a6cb: {
    title: '理想生活指定通路：單筆滿1,000元固定加碼45 N點',
    baseRate: 0, promoRate: 0, rewardAmount: 45, rewardType: 'points', rewardUnit: 'points',
    rewardCalculationMode: 'FIXED', rewardTiers: [], capScope: 'PROMO',
    validFrom: '2026-07-01', validUntil: '2026-12-31', spendBasis: 'PER_TRANSACTION',
    registrationCycle: 'MONTHLY', regDeadline: '每月1日至月底，當月消費須當月APP登錄',
    registrationMethods: [{type: 'APP', label: '將來銀行APP登錄', appName: '將來銀行',
      deepLink: '', appStoreUrl: '', playStoreUrl: '', path: [], activityName: '理想生活指定通路加碼回饋'}],
    excludedKeywords: ['Apple Store', '蘋果直營店'],
    issues: ['N_POINT_CASH_VALUE_NOT_VERIFIED'],
    evidence: 'Part 2 clauses 1-2 and examples: fixed 45 N points for each qualifying transaction >=1,000, monthly cap225, monthly APP registration. Apple media services explicitly exclude Apple Store.'
  },
  rule_1704bb66da21702598dd: {
    validFrom: '2026-08-17', registrationStart: '2026-08-17', registrationEnd: '2026-10-18',
    spendBasis: 'CAMPAIGN', capScope: 'PROMO', rewardType: 'points', rewardUnit: 'percent',
    roundingMode: 'ROUND', issues: ['N_POINT_CASH_VALUE_NOT_VERIFIED','CUMULATIVE_SPEND_NOT_KNOWN'],
    evidence: 'Part 1 clauses 1-3: campaign aggregate spend >=6,000, APP registration; additional2.5% N points, campaign cap300.'
  },
  rule_9e258a1bada075ba54df: {
    validFrom: '2026-08-17', registrationStart: '2026-08-17', registrationEnd: '2026-10-18',
    spendBasis: 'CAMPAIGN', capScope: 'PROMO', rewardType: 'points', rewardUnit: 'percent',
    roundingMode: 'ROUND', issues: ['N_POINT_CASH_VALUE_NOT_VERIFIED','CUMULATIVE_SPEND_NOT_KNOWN'],
    evidence: 'Part 2 clauses 1-3 and notes: campaign aggregate spend >=6,000, APP registration, Japan face-to-face/non-online transactions; additional5% N points, campaign cap450.'
  }
};
let ledger = {startedAt: checkedAt, scope: 'Every existing rule; pending is NOT verified', entries: {}};
const ledgerFile = path.join(root, 'rule_review_ledger.json');
if (fs.existsSync(ledgerFile)) ledger = JSON.parse(fs.readFileSync(ledgerFile, 'utf8'));
for (const rule of data.rules) {
  ledger.entries[rule.id] ||= {status: 'PENDING', title: rule.title, sourceUrl: rule.sourceUrl || ''};
  const patch = patches[rule.id];
  if (!patch) continue;
  const before = JSON.parse(JSON.stringify(rule));
  const {issues, evidence, excludedKeywords, ...fields} = patch;
  Object.assign(rule, fields);
  if (excludedKeywords) rule.excludedKeywords = [...new Set([...(rule.excludedKeywords || []), ...excludedKeywords])];
  // Terms checked, but insufficient to claim a fully verified cash estimate.
  rule.accuracyReview = {status: 'PARTIAL', checkedAt, sourceUrl: rule.sourceUrl,
    method: 'official_terms_read', fields: Object.keys(fields), issues, evidence};
  ledger.entries[rule.id] = {status: 'PARTIAL', checkedAt, sourceUrl: rule.sourceUrl,
    evidence, issues, before, corrected: JSON.parse(JSON.stringify(rule))};
}
ledger.updatedAt = checkedAt;
ledger.counts = Object.values(ledger.entries).reduce((a,r) => (a[r.status]=(a[r.status]||0)+1,a),{});
fs.writeFileSync(file, JSON.stringify(data, null, 2));
fs.writeFileSync(ledgerFile, JSON.stringify(ledger, null, 2));
console.log(JSON.stringify(ledger.counts));
