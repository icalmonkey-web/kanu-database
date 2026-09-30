// Preserve fresh crawler data while reapplying independently reviewed records/images.
const fs = require('node:fs');
const cp = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const readRef = ref => JSON.parse(cp.execFileSync('git', ['show', `${ref}:data.json`], {cwd:root, encoding:'utf8', maxBuffer:32*1024*1024}));
const local = readRef('HEAD');
const remote = readRef('origin/main');
const cards = new Map(remote.cards.map(c => [c.id,c]));
for (const card of local.cards) {
  if (card.imageUrl && cards.has(card.id) && cards.get(card.id).cardName === card.cardName) {
    Object.assign(cards.get(card.id), {imageUrl:card.imageUrl, imageEvidence:card.imageEvidence, imageSourceUrl:card.imageSourceUrl});
  }
}
for (const rule of local.rules.filter(r => r.accuracyReview?.status === 'SOURCE_CHECKED')) {
  if (!cards.has(rule.cardId)) {
    const card = local.cards.find(c => c.id === rule.cardId);
    if (!card) throw new Error('Reviewed card missing');
    remote.cards.push(card); cards.set(card.id, card);
  }
  const index = remote.rules.findIndex(r => r.id === rule.id);
  if (index < 0) remote.rules.push(rule); else remote.rules[index] = rule;
}
for (const rule of remote.rules) {
  if (rule.cardId === 'card_esun_ubear' && !rule.accuracyReview && /日本.*實體|日本.*消費/.test(rule.title || '')) {
    rule.quickSearchEligible = false;
    rule.validationIssues = [...new Set([...(rule.validationIssues || []), 'REVIEW_UBEAR_CHANNEL_ASSOCIATION'])];
  }
}
fs.writeFileSync(path.join(root, 'data.json'), JSON.stringify(remote,null,2));
console.log(`Preserved fresh data: ${remote.cards.length} cards, ${remote.rules.length} rules`);
