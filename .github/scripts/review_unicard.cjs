// Manually read official sections: scheme mechanics, base benefit, merchant recognition,
// and the September 1 general-consumption exclusions. This is not an AI auto-approval.
const fs=require('node:fs'),path=require('node:path'),A=require('../../accuracy-core.js');
const root=path.resolve(__dirname,'../..'),file=path.join(root,'data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const source='https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card/unicard';
const checkedAt='2026-10-03T00:00:00+08:00';
const commonExcluded=['全聯','大全聯','超商','7-ELEVEN','全家','萊爾富','OK超商','繳稅','學費','醫療費','政府規費','小額支付','自動加值','儲值','eTag','電費','水費','瓦斯費','電信費','投資平台','賭博','預借現金','手續費','菸品'];
const europe=['英國','奧地利','比利時','保加利亞','克羅埃西亞','賽普勒斯','捷克','丹麥','愛沙尼亞','芬蘭','法國','德國','希臘','匈牙利','愛爾蘭','義大利','拉脫維亞','立陶宛','盧森堡','馬爾他','荷蘭','波蘭','葡萄牙','羅馬尼亞','斯洛伐克','斯洛維尼亞','西班牙','瑞典'];
const common={cardId:'card_玉山銀行_9',bank:'玉山銀行',offerDomain:'CARD',activityType:'BASE_BENEFIT',
 sourceUrl:source,validFrom:'2026-07-01',validUntil:'2026-12-31',fetchedAt:checkedAt,
 baseRate:0,promoRate:0,rewardAmount:null,rewardType:'points',rewardUnit:'percent',pointValueTwd:1,
 roundingMode:'ROUND_COMPONENT',minimumSpend:0,spendBasis:'PER_TRANSACTION',needReg:false,
 registrationMethods:[],rewardCalculationMode:'TIERED',selectionMode:'FIXED',associationStatus:'matched',
 quickSearchEligible:true,validationIssues:[],capPeriod:'MONTHLY',excludedKeywords:commonExcluded,
 eligibilityRequirements:['須申辦帳單e化；最高基本回饋還需玉山臺幣帳戶成功自扣'],
 evidenceStatus:'SOURCE_CHECKED'};
const baseTiers=[{name:'帳單e化',totalRate:.3,baseRate:.3,requirements:['帳單e化'],isDefault:false},
 {name:'帳單e化及成功自扣',totalRate:1,baseRate:1,requirements:['帳單e化','玉山臺幣帳戶成功自扣'],isDefault:false}];
const schemeTiers=[];
for(const [name,bonus,cap,requirements] of [
 ['簡單選',2,1000,['月底最終方案為簡單選']],
 ['任意選',2.5,1000,['月底任意選的8家名單包含本通路']],
 ['UP選',3.5,5000,['月底方案為UP選','上月刷卡>=3萬元且平均資產>=30萬元，或以149點訂閱；需Wallet完成訂閱']]]) {
 for(const b of baseTiers) schemeTiers.push({name:`${name}／${b.name}`,totalRate:b.totalRate+bonus,
   baseRate:b.baseRate,promoRate:bonus,capAmount:cap,capPeriod:'MONTHLY',isDefault:false,
   requirements:[...b.requirements,...requirements]});
}
const rules=[{...common,id:'review_unicard_general_202610',title:'Unicard 一般消費：依帳單與自扣資格最高1%',
 category:'一般消費',scope:'ALL',matchedMerchants:['國內一般消費','海外一般消費'],searchKeywords:'一般消費 海外 國外',
 capAmount:null,capScope:'NONE',rewardTiers:baseTiers,
 excludedKeywords:[...commonExcluded,...europe,'分期','躉繳保費','三商美邦投資型保單'],
 quotaInfo:'e point折抵價值1點1元。國外一般消費不含公告排除的歐洲實體交易；特殊通路依專案另計。',
 evidenceSection:'一般消費最高1%；一般消費排除公告2026/9/1'}];
const regions=['日本','韓國','泰國','越南','新加坡','馬來西亞','菲律賓','中國','香港','澳門','美國','加拿大','澳洲','紐西蘭'];
for(const [key,label,merchants,keywords,requirements,excluded] of [
 ['linepay','LINE Pay',['LINE Pay'],'LINEPAY LINE Pay', ['請款名稱符合銀行認列；不能用LINE Pay繳保費'],['保費']],
 ['apple','台灣Apple直營通路',['Apple Store','Apple 台北101','Apple 信義A13'],'Apple Store 蘋果官網', ['限台灣Apple直營及台灣官網；實體卡或感應付款，電子錢包另按支付通路認列'],['App Store','Apple Music','iCloud','美國','日本','國外','海外']],
 ['cpc','中油直營站',['台灣中油直營站','中油Pay'],'中油 加油', ['限中油官方直營站；付款方式須符合本通路認列'],['加盟站','台塑','台亞','福懋']],
 ['overseas','指定國家實體消費',regions,'海外 國外 日本 韓國 泰國', ['須確認國家在本筆列出的14個地區內；面對面實體交易、外幣，不含網路交易或服務費'],['網購','網路','線上','關島',...europe]]
]) {
 rules.push({...common,id:`review_unicard_${key}_202610`,title:`Unicard ${label}：依方案及任務最高4.5%`,
  category:label,scope:'SPECIFIC',matchedMerchants:merchants,searchKeywords:keywords,
  capAmount:5000,capScope:'PROMO',rewardTiers:schemeTiers,selectionMode:'SWITCHABLE',
  eligibilityRequirements:[...common.eligibilityRequirements,...requirements,'按月底方案認列，需次月10日前請款；正附卡共用加碼上限'],
  excludedKeywords:[...commonExcluded,...excluded,'分期'],
  quotaInfo:'各方案擇一，不疊加。簡單選最高3%、任意選最高3.5%、UP選最高4.5%；回饋為e point折抵價值，不是現金入帳。UP選付費訂閱時，試算尚未扣149點成本。分期及歐洲特殊基本回饋未納入本筆。',
  evidenceSection:`方案機制1-4／一般消費／百大指定消費列表及${label}認列`});
}
for(const r of rules) r.accuracyReview={status:'SOURCE_CHECKED',checkedAt,sourceUrl:source,
 method:'official_terms_read',fields:Object.keys(A.termsSnapshot(r)),issues:[],
 evidenceSources:[source,'https://event.esunbank.com.tw/credit/notice/index.html'],
 evidence:r.evidenceSection,termsSnapshot:A.termsSnapshot(r)};
data.rules=data.rules.filter(r=>!rules.some(v=>v.id===r.id)).concat(rules);
if(!data.version.includes('-trusted-core-20261003')) data.version+='-trusted-core-20261003';
fs.writeFileSync(file,JSON.stringify(data,null,2));
console.log(`Added ${rules.length} scoped official Unicard rules. No other rules approved.`);
