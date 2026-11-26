// Preserve observed official list/detail disagreement; this is not a completed terms review.
const fs=require('node:fs');
const path=require('node:path');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const rule=data.rules.find(r=>r.id==='rule_4a815ab4479aa69a6253');
if(!rule) throw new Error('greattree_rule_missing');
rule.validationIssues=[...new Set([...(rule.validationIssues||[]),'OFFICIAL_LIST_DETAIL_RATE_CONFLICT'])];
rule.quickSearchEligible=false;
rule.sourceFacts={...(rule.sourceFacts||{}),checkedAt:'2026-11-03T21:30:00+08:00',
  sourceUrl:'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_life.html',
  locators:{list:'L38-L42 lists 最高6%',detail:'L271-L276 lists 最高8%'}};
data.version='2026.11.03-v213000-ctbc-life-catalog';
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
