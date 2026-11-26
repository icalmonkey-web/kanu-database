// Targeted recovery of the auto-signing incident; later independent edits survive.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
function recover(current,before,after) {
 const originals=new Map(before.rules.map(r=>[r.id,r]));
 const incident=new Map(after.rules.map(r=>[r.id,r]));
 const report=[];
 const fields=['cardId','bank','associationStatus','unresolvedCardId','sourceUrl','validationIssues','accuracyReview'];
 for(const rule of current.rules){
  const original=originals.get(rule.id),bad=incident.get(rule.id);
  if(!original || !bad) continue;
  const restored=[];
  for(const field of fields){
   if(JSON.stringify(rule[field])===JSON.stringify(bad[field]) && JSON.stringify(original[field])!==JSON.stringify(bad[field])){
    if(original[field]===undefined)delete rule[field];else rule[field]=structuredClone(original[field]);
    restored.push(field);
   }
  }
  if(restored.length){delete rule._reviewTermsBaseline;report.push({id:rule.id,restored});}
 }
 return report;
}
if(require.main===module){
 const root=path.resolve(__dirname,'../..'),file=path.join(root,'data.json');
 const read=ref=>JSON.parse(cp.execFileSync('git',['show',ref+':data.json'],{cwd:root,encoding:'utf8',maxBuffer:64*1024*1024}));
 const current=JSON.parse(fs.readFileSync(file,'utf8'));
 const report=recover(current,read('60bb94e^'),read('60bb94e'));
 if(report.length){
  current.version+='-integrity-20261102';
  fs.writeFileSync(file,JSON.stringify(current,null,2));
  fs.writeFileSync(path.join(root,'integrity_recovery_report.json'),JSON.stringify({incidentCommit:'60bb94e',repairDate:'2026-11-02',affectedRules:report.length,restorations:report},null,2));
 }
 console.log(JSON.stringify({restored:report.length,cardLinks:report.filter(r=>r.restored.includes('cardId')).length,sources:report.filter(r=>r.restored.includes('sourceUrl')).length}));
}
module.exports={recover};
