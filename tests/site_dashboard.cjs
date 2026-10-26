// Small DOM test double: exercise the shipped renderers and click handlers without dependencies.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.style={};this._text='';this.hidden=false;}
 set textContent(v){this._text=String(v);this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this._text='';this.children=[...nodes];}
 getAttribute(k){return this.attributes[k]??null;}
 setAttribute(k,v){this.attributes[k]=String(v);}
}
const ids={},groups={};
const html=fs.readFileSync('scripts/site.html','utf8');
for(const m of html.matchAll(/id="([^"]+)"/g))ids[m[1]]=new Element();
for(const name of ['view','source','overview-days','days','track']){
 groups[`[data-${name}]`]=[...html.matchAll(new RegExp(`data-${name}="([^"]+)"`,'g'))].map(m=>{const b=new Element('button');b.dataset[name.replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=m[1];return b;});
}
const report=(end=1100)=>({summary:{status:'active',daily_returns:[],closed_trades:[],open_positions:[]},curve:[{date:'2026-01-01',equity:1000,buy_hold_equity:1000},{date:'2026-01-02',equity:end,buy_hold_equity:1050}]});
const forward={r1:report(),r5:report(900),r6:report(1200),r7:report(),r8:report()};
forward.r7.summary.universe_pending=true;forward.r8.summary.status='not_started';
ids['report-data'].textContent=JSON.stringify({registry:Object.fromEntries(Object.keys(forward).map(k=>[k,{name:k,description:'Test'}])),views:{forward},reference_url:'reference.json',health:{runs:[],successful_dates:[],start_date:'2026-10-27'}});
let fetches=0;
const context=vm.createContext({document:{getElementById:id=>ids[id],querySelectorAll:s=>groups[s]||[],createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t)},Node:Element,TradeMetrics:require('../scripts/site_metrics.js'),setInterval:()=>{},fetch:async()=>{fetches++;return {ok:true,json:async()=>({r1:report(1400),r5:report(1300)})};}});
vm.runInContext(fs.readFileSync('scripts/site.js','utf8'),context);
const run=code=>vm.runInContext(code,context),tabs=groups['[data-overview-days]'];
assert.equal(fetches,0,'reference must stay lazy');
assert.equal(tabs.length,7);assert(tabs.every(b=>b.textContent.includes('+10,0%')),'default R1 returns');
assert.equal(ids['overview-bot-title'].textContent,'R1 · Çekirdek');
assert.equal(ids['overview-bots'].children[0].attributes['aria-pressed'],'true');
assert.equal(ids['overview-stats'].children[0].textContent,'Başlangıç1.000,0 USDT');
assert.equal(ids['overview-stats'].children[2].textContent,'Kâr/Zarar+100,0 USDT');
ids['overview-bots'].children[2].onclick();
assert(tabs.every(b=>b.textContent.includes('+20,0%')),'pill selects R6');
function rows(){return ids['overview-comparison'].children[0].children[1].children;}
function headers(){return ids['overview-comparison'].children[0].children[0].children[0].children;}
assert.deepEqual(rows().slice(0,3).map(r=>r.dataset.bot),['r6','r1','r5']);
assert(rows().find(r=>r.dataset.bot==='r7').textContent.includes('Coin listesi'));
assert(rows().find(r=>r.dataset.bot==='r8').textContent.includes('ilk sonuçlar'));
assert(rows().slice(-2).every(r=>!r.textContent.includes('0,0%')),'pending rows have no return');
assert.deepEqual(rows().slice(-2).map(r=>r.dataset.bot),['r7','r8']);
headers()[3].children[0].onclick();assert.deepEqual(rows().slice(0,3).map(r=>r.dataset.bot),['r5','r1','r6']);
assert.equal(headers()[3].attributes['aria-sort'],'ascending');
assert.deepEqual(rows().slice(-2).map(r=>r.dataset.bot),['r7','r8']);
for(let i=0;i<8;i++){
 headers()[i].children[0].onclick();
 assert.deepEqual(rows().slice(-2).map(r=>r.dataset.bot),['r7','r8']);
 headers()[i].children[0].onclick();
 assert.deepEqual(rows().slice(-2).map(r=>r.dataset.bot),['r7','r8']);
}
run("overviewSort='ret';overviewAscending=true;renderOverview()");
headers()[3].children[0].onclick();assert.equal(rows()[0].dataset.bot,'r6');
rows().find(r=>r.dataset.bot==='r5').onclick();assert(tabs.every(b=>b.textContent.includes('−10,0%')),'selected bot returns');
assert.equal(ids['overview-bot-title'].textContent,'R5 · Seçili 33');
for(const key of ['r7','r8']){
 rows().find(r=>r.dataset.bot===key).onclick();
 assert.equal(ids['overview-stats'].children.length,1,'single info banner');
 assert(ids['overview-stats'].textContent.includes('03:20 TR'));
 assert(tabs.every(b=>b.children[1].textContent==='—'&&b.children[1].className.includes('period-unavailable')));
}
ids['all-columns'].onclick();assert(ids['overview-comparison'].className.includes('show-all-columns'));
ids['all-columns'].onclick();assert.equal(ids['overview-comparison'].className,'table-scroll');
rows().find(r=>r.dataset.bot==='r5').onclick();
context.moneyReport=report(1466.3);run("statStrip('overview-stats',moneyReport,0)");
assert.equal(ids['overview-stats'].children[1].textContent,'Şu an1.466,3 USDT');
assert.equal(ids['overview-stats'].children[2].textContent,'Kâr/Zarar+466,3 USDT');
context.waitingReport=report();context.waitingReport.curve.length=1;
run("statStrip('overview-stats',waitingReport,0)");
assert.equal(ids['overview-stats'].children.length,1);
// The banner action selects the lazy reference source and preserves bot and period.
tabs.find(b=>b.dataset.overviewDays==='30').onclick();
rows().find(r=>r.dataset.bot==='r7').onclick();
ids['overview-stats'].children[0].children[1].onclick();
assert.equal(run('source'),'reference');
rows().find(r=>r.dataset.bot==='r5').onclick();
groups['[data-source]'].find(b=>b.dataset.source==='reference').onclick();
(async()=>{
 await run('ensureReference()');
 assert.equal(fetches,1);assert.equal(run('overviewDays'),30,'source switch preserves period');
 assert.equal(tabs.find(b=>b.dataset.overviewDays==='30').attributes['aria-pressed'],'true');
 assert(tabs.every(b=>b.textContent.includes('+30,0%')));
 assert.equal(rows().length,5);assert.equal(rows().filter(r=>r.textContent.includes('Geçmiş simülasyon yok')).length,3);
 // Unchanged at displayed precision must remain neutral.
 const tiny=report(1000.001);assert.equal(context.TradeMetrics.overview(tiny,0).message,'Bu dönemde değişmedi');
 groups['[data-view]'].find(b=>b.dataset.view==='forward').onclick();
 assert.equal(ids['equity'].children[0].tagName,'svg');
 const chart=ids['equity'].children[0];chart.getBoundingClientRect=()=>({left:0,width:900});
 chart.onpointerdown({clientX:880});
 assert(ids['equity'].children[1].textContent.includes('Seçili: 110,0'));
 assert.equal(ids['equity'].children[1].hidden,false);chart.onpointerleave();
 assert.equal(ids['equity'].children[1].hidden,true);
 assert(groups['[data-days]'].every(b=>b.textContent.includes('+10,0%')));
 const longReport=report();longReport.curve=Array.from({length:41},(_,i)=>({date:new Date(Date.UTC(2026,0,1+i)).toISOString(),equity:1000+i*10,buy_hold_equity:1000+i*5}));
 context.longReport=longReport;run("periodTabs('[data-days]',longReport,7)");
 const dayTabs=groups['[data-days]'];
 assert(dayTabs.find(b=>b.dataset.days==='1').textContent.includes('+0,7%'));
 assert(dayTabs.find(b=>b.dataset.days==='7').textContent.includes('+5,3%'));
 assert(dayTabs.find(b=>b.dataset.days==='30').textContent.includes('+27,3%'));
 assert(dayTabs.find(b=>b.dataset.days==='0').textContent.includes('+40,0%'));
 console.log('Dashboard period labels, selection, sorting, pending rows and lazy source switching passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
