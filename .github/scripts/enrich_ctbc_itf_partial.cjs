// Public LINE Pay ITF summary only. Login-gated detailed tasks remain unresolved.
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const file=path.join(root,'data.json');
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const id='pending_ctbc_linepay_travel_2026_itf';
const r=data.rules.find(x=>x.id===id);
if(!r||r.validFrom!=='2026-11-06'||r.validUntil!=='2026-11-09')throw Error('ITF official listing mismatch');
const source='https://web-tw-pay.line.me/svc/event/display2/5df8b961-43f7-4806-994f-51f7932714ef';
Object.assign(r,{
  title:'ITF台灣國際旅展：LINE Pay 多項優惠（完整條款待核）',
  offerDomain:'PAYMENT',paymentProvider:'LINE Pay',
  fundingMethods:['中信 LINE Pay 卡或永豐 DAWAY 卡（6%滿額方案，細則待核）'],
  benefitSummary:'官方活動頁公開摘要：現場售票滿200元標示15點；大會DM可領500元優惠券；綁中信LINE Pay卡／永豐DAWAY卡單筆滿6000元標示最高6%；單筆滿100元累計兩筆可抽最高520點。各方案資格、上限、名額與是否可併用均須再核對。',
  advertisedOffers:[
    {kind:'ticket_points',threshold:200,advertisedPoints:15},
    {kind:'coupon',advertisedTwd:500,source:'大會DM'},
    {kind:'card_points',threshold:6000,advertisedMaxRate:6,cardText:'中信LINE Pay卡／永豐DAWAY卡'},
    {kind:'draw',threshold:100,transactionCount:2,advertisedMaxPoints:520}
  ],
  sourceUrl:source,quickSearchEligible:false,
  validationIssues:['MULTIPLE_ITF_BENEFITS_NEED_SPLIT','DETAILS_LOGIN_REQUIRED','QUOTA_CAP_AND_STACKING_UNVERIFIED'],
  sourceFacts:{checkedAt:'2026-11-04T19:37:00+08:00',sourceUrl:source,
    locators:{summary:'活動頁展開看優惠一覽；全場LINE Pay合作品牌適用、門票優惠、指定品牌再加碼'}},
  fetchedAt:'2026-11-04T19:37:00+08:00'
});
const catalogFile=path.join(root,'official_catalogs/ctbc_linepay_travel_2026.json');
const catalog=JSON.parse(fs.readFileSync(catalogFile,'utf8'));
const offer=catalog.offers.find(x=>x.id==='itf');
if(!offer)throw Error('ITF missing from independent catalog');
offer.detailUrl=source;
data.version='2026.11.04-v193800-itf-partial';
fs.writeFileSync(catalogFile,JSON.stringify(catalog,null,2)+'\n');
fs.writeFileSync(file,JSON.stringify(data,null,2)+'\n');
console.log('ITF public summary recorded; details remain blocked');
