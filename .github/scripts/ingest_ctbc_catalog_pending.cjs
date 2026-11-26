// Capture missing official listing entries without inventing card or reward terms.
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const dataFile=path.join(root,'data.json');
const data=JSON.parse(fs.readFileSync(dataFile,'utf8'));
const targets=['ctbc_linepay_life_2026','ctbc_linepay_travel_2026'];
let added=0;
for(const catalogId of targets){
  const catalog=JSON.parse(fs.readFileSync(path.join(root,'official_catalogs',`${catalogId}.json`),'utf8'));
  const mappingFile=path.join(root,'official_catalogs',`${catalogId}_mapping.json`);
  const mapping=JSON.parse(fs.readFileSync(mappingFile,'utf8'));
  if(catalog.catalogId!==mapping.catalogId||!catalog.sourceUrl.startsWith('https://www.ctbcbank.com/'))
    throw Error(`Invalid catalog: ${catalogId}`);
  const observed=new Date(`${catalog.observedAt}T00:00:00+08:00`);
  if(!Number.isFinite(observed.getTime())||Math.abs(Date.now()-observed.getTime())>14*86400000)
    throw Error(`Catalog must be reread before adding pending entries: ${catalogId}`);
  const mapped=new Set(mapping.mappings.map(x=>x.offerId));
  for(const offer of catalog.offers){
    if(mapped.has(offer.id))continue;
    if(!offer.matchToken||!offer.validFrom||!offer.validUntil||!Number.isInteger(offer.sourceLineHint))
      throw Error(`Incomplete official listing: ${catalogId}/${offer.id}`);
    const id=`pending_${catalogId}_${offer.id}`;
    let rule=data.rules.find(x=>x.id===id);
    if(!rule){rule={id};data.rules.push(rule);added++;}
    const provider=offer.channel==='LINE_PAY'?'LINE Pay':offer.channel==='SHOPBACK'?'ShopBack':'';
    Object.assign(rule,{
      bank:'中國信託',cardId:'',offerDomain:provider?'PAYMENT':'CARD',paymentProvider:provider,
      title:`${offer.name}（官方列表；條款待核）`,
      activityType:'UNKNOWN',scope:'SPECIFIC',eligibleCardScope:'UNKNOWN',
      matchedMerchants:[offer.matchToken],searchKeywords:offer.matchToken,
      benefitSummary:`官方列表入口：${offer.name}。卡別、回饋、門檻、名額與登錄條款待逐項核對。`,
      rewardType:'unknown',rewardUnit:'unknown',rewardAmount:null,baseRate:0,promoRate:0,
      capAmount:null,minimumSpend:0,needReg:false,
      validFrom:offer.validFrom,validUntil:offer.validUntil,
      sourceUrl:catalog.sourceUrl,registrationUrl:'',registrationMethods:[],
      quickSearchEligible:false,
      validationIssues:['LISTING_ONLY_TERMS_UNVERIFIED','CARD_ELIGIBILITY_UNVERIFIED','REGISTRATION_REQUIREMENT_UNVERIFIED'],
      sourceFacts:{checkedAt:`${catalog.observedAt}T00:00:00+08:00`,sourceUrl:catalog.sourceUrl,
        locators:{listing:`L${offer.sourceLineHint}`}},
      fetchedAt:`${catalog.observedAt}T00:00:00+08:00`
    });
    mapping.mappings.push({offerId:offer.id,ruleId:id,status:'candidate',
      reason:'僅官方列表入口與日期已記錄；適用卡、回饋計算、名額及登錄資格未逐欄核對，暫停推薦'});
  }
  fs.writeFileSync(mappingFile,JSON.stringify(mapping,null,2)+'\n');
}
data.version='2026.11.04-v090000-ctbc-listing-pending';
fs.writeFileSync(dataFile,JSON.stringify(data,null,2)+'\n');
console.log(`official listing pending entries added=${added}`);
