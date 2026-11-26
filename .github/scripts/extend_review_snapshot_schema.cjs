// Extend snapshots for newly tracked fields only when each prior field still matches.
// This does not renew checkedAt or term evidence, and refuses nonempty new fields.
const fs=require('node:fs');
const path=require('node:path');
const A=require('../../accuracy-core.js');
const file=path.resolve(__dirname,'../../data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const additions=['registrationWindows','excludedCountries','eligibleDateRanges','eligibleCardIds'];
let changed=0;
for(const r of data.rules){
  const review=r.accuracyReview;
  if(review?.status!=='SOURCE_CHECKED'||!review.termsSnapshot) continue;
  const current=A.termsSnapshot(r),previous=review.termsSnapshot;
  for(const [key,value] of Object.entries(previous)){
    if(JSON.stringify(value)!==JSON.stringify(current[key])) throw new Error(`review_terms_changed:${r.id}:${key}`);
  }
  for(const key of additions){
    if(Object.hasOwn(previous,key)) continue;
    if(current[key]!==null) throw new Error(`new_field_needs_manual_review:${r.id}:${key}`);
    previous[key]=null;
    changed++;
  }
}
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log(`snapshot fields appended=${changed}; review clocks unchanged`);
