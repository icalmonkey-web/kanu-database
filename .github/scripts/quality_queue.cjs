// Deterministic triage, NOT an automatic factual review. Never stamps SOURCE_CHECKED.
const fs = require('node:fs');
const path = require('node:path');
const A = require('../../accuracy-core.js');
const root = path.resolve(__dirname,'../..');
const data = JSON.parse(fs.readFileSync(path.join(root,'data.json'),'utf8'));
const now = new Date();
const cards = new Map(data.cards.map(c=>[c.id,c]));
const rows = data.rules.map(r=>{
 const issues=[];
 if (!r.sourceUrl) issues.push('MISSING_SOURCE');
 if (r.cardId && !cards.has(r.cardId)) issues.push('ORPHAN_CARD');
 if (r.associationStatus==='needs_review') issues.push('UNRESOLVED_CARD_ASSOCIATION');
 if (r.accuracyReview?.status==='SOURCE_CHECKED' && !A.reviewMatches(r)) issues.push('TERMS_CHANGED_OR_SNAPSHOT_MISSING');
 const until=A.date(r.validUntil,true), from=A.date(r.validFrom);
 const state=until && until<now?'EXPIRED':from && from>now?'UPCOMING':'ACTIVE_OR_UNKNOWN';
 const trusted=A.isReviewed(r,now);
 const calc=A.calculate(r,2000);
 if (!trusted) issues.push('INDEPENDENT_REVIEW_REQUIRED');
 if (!calc.calculable) issues.push(calc.reason);
 return {id:r.id,bank:r.bank || cards.get(r.cardId)?.bank || '未分類',title:r.title,sourceUrl:r.sourceUrl || '',
   lifecycle:state,reviewStatus:trusted?'SOURCE_CHECKED':r.accuracyReview?.status==='SOURCE_CHECKED'?'RECHECK_REQUIRED':r.accuracyReview?.status || 'PENDING',
   comparable:trusted && calc.calculable && state==='ACTIVE_OR_UNKNOWN',issues};
});
const groups = new Map();
for (const row of rows.filter(r=>r.reviewStatus!=='SOURCE_CHECKED')) {
 const key=row.sourceUrl || `missing:${row.bank}`;
 if(!groups.has(key)) groups.set(key,{sourceUrl:row.sourceUrl,bank:row.bank,ruleIds:[],activeRules:0});
 const group=groups.get(key);group.ruleIds.push(row.id);group.activeRules+=row.lifecycle==='ACTIVE_OR_UNKNOWN'?1:0;
}
const queue=[...groups.values()].sort((a,b)=>b.activeRules-a.activeRules);
const report={generatedAt:now.toISOString(),disclaimer:'結構檢查不是事實核對；待確認點數不換算現金。',
 totalRules:rows.length,reviewed:rows.filter(r=>r.reviewStatus==='SOURCE_CHECKED').length,
 comparable:rows.filter(r=>r.comparable).length,expired:rows.filter(r=>r.lifecycle==='EXPIRED').length,
 sourceGroups:queue.length,queue, rules:rows};
fs.writeFileSync(path.join(root,'quality_queue.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({...report,queue:undefined,rules:undefined}));
