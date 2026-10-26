'use strict';
const DATA=JSON.parse(document.getElementById('report-data').textContent);
const $=id=>document.getElementById(id), M=globalThis.TradeMetrics;
let view='overview',track='r1',days=0,sortColumn='exit_date',ascending=false;
const COLORS=['#546DE5','#A1A1A6','#626269','#2EBD85','#F6465D'];
let overviewTrack='r1',overviewSort='ret',overviewAscending=false;
let overviewDays=0,source='forward',referenceLoad;
let referenceState='';
const BOT_ORDER=['r1','r5','r6','r7','r8'];
const num=(v,d=1)=>v==null?'—':Number(v).toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=v=>{if(v==null)return '—';const r=Math.round(Number(v)*10)/10;return r===0?'0,0%':(r>0?'+':'−')+num(Math.abs(r))+'%';};
// Drawdowns are magnitudes: never signed, never "-0,0%".
const ddPct=v=>v==null?'—':num(Math.abs(Math.round(Number(v)*10)/10))+'%';
const date=v=>v?new Date(v).toLocaleDateString('tr-TR',{timeZone:'UTC'}):'—';
function el(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;}
function svg(tag,attrs={}){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;}
function plot(target,series,mode='line',labels=[],labelFormat=date){
 const host=$(target);host.replaceChildren();const chart=svg('svg',{viewBox:'0 0 900 260',role:'img','aria-label':target==='equity'?'Seçili izlek, kendi al-tutu ve varsa %0,25 ücret stresi':target});
 const vals=series.flatMap(s=>s.values);if(!vals.length){host.append(el('p','Henüz günlük veri yok.','muted'));return;}let lo=Math.min(...vals),hi=Math.max(...vals);
 if(mode!=='line'){lo=Math.min(0,lo);hi=Math.max(0,hi);}const pad=Math.max((hi-lo)*.08,.1);lo-=pad;hi+=pad;
 const y=v=>225-(v-lo)/(hi-lo)*205, x=(i,n)=>65+i*815/Math.max(n-1,1);
 for(let i=0;i<5;i++){const val=lo+(hi-lo)*i/4,yy=y(val);chart.append(svg('path',{d:`M65 ${yy}H880`,stroke:'rgba(255,255,255,.06)'}));const text=svg('text',{x:3,y:yy+4,fill:'#A1A1A6','font-size':11});text.textContent=num(val);chart.append(text);}
 for(const s of series){
  if(mode==='bars'){s.values.forEach((v,i)=>{const width=815/Math.max(s.values.length,1),xx=65+i*width;const r=svg('rect',{x:xx,y:Math.min(y(v),y(0)),width:Math.max(width*.8,.4),height:Math.max(Math.abs(y(v)-y(0)),.5),fill:v>=0?'#2EBD85':'#F6465D'});const t=svg('title');t.textContent=`${date(labels[i])}: ${pct(v)}`;r.append(t);chart.append(r);});}
  else{const points=s.values.map((v,i)=>`${x(i,s.values.length)},${y(v)}`).join(' ');
   if(mode==='area'||(mode==='line'&&s===series[0]))chart.append(svg('polygon',{points:`65,${mode==='area'?y(0):225} ${points} ${x(s.values.length-1,s.values.length)},${mode==='area'?y(0):225}`,fill:s.color,'fill-opacity':.1}));
   chart.append(svg('polyline',{points,fill:'none',stroke:s.color,'stroke-width':2,'stroke-linejoin':'round','stroke-dasharray':s.dashed?'7 6':'none'}));
   if(s.values.length===1)chart.append(svg('circle',{cx:65,cy:y(s.values[0]),r:4,fill:s.color}));
  }
 }
 [[65,'start',labels[0]],[880,'end',labels.at(-1)]].forEach(([xx,anchor,label])=>{const t=svg('text',{x:xx,y:252,'text-anchor':anchor,fill:'#A1A1A6','font-size':11});t.textContent=labelFormat(label);chart.append(t);});host.append(chart);
 const cross=svg('path',{stroke:'#A1A1A6','stroke-dasharray':'3 3',class:'crosshair',visibility:'hidden'});
 const dot=svg('circle',{r:4,fill:series[0].color,visibility:'hidden'});chart.append(cross,dot);
 const tip=el('div',null,'chart-tooltip');tip.hidden=true;host.append(tip);
 const inspect=event=>{const rect=chart.getBoundingClientRect(),xx=(event.clientX-rect.left)/rect.width*900;
  const values=series[0].values,i=Math.max(0,Math.min(values.length-1,Math.round((xx-65)/815*Math.max(values.length-1,1)))),cx=mode==='bars'?65+(i+.4)*815/values.length:x(i,values.length);
  cross.setAttribute('d',`M${cx} 20V225`);cross.setAttribute('visibility','visible');dot.setAttribute('cx',cx);dot.setAttribute('cy',y(values[i]));dot.setAttribute('visibility','visible');
  tip.textContent=labelFormat(labels[i])+' · '+series.map((s,j)=>(j===0?'Seçili':s.dashed?'Al-tut':'Stres')+': '+(mode==='line'?num(s.values[i]):pct(s.values[i]))).join(' / ');tip.hidden=false;
 };
 chart.onpointermove=inspect;chart.onpointerdown=inspect;chart.onpointerleave=()=>{tip.hidden=true;cross.setAttribute('visibility','hidden');dot.setAttribute('visibility','hidden');};
}
function table(host,headers,rows,keys=[]){
 host.replaceChildren();if(!rows.length){host.append(el('p','Henüz kayıt yok.','muted'));return;}
 const t=el('table'),head=el('thead'),tr=el('tr');headers.forEach((h,i)=>{const th=el('th');th.scope='col';if(keys[i]){const b=el('button',h+(sortColumn===keys[i]?(ascending?' ↑':' ↓'):''));b.onclick=()=>{ascending=sortColumn===keys[i]?!ascending:true;sortColumn=keys[i];render();};th.append(b);}else th.textContent=h;tr.append(th);});head.append(tr);t.append(head);
 const body=el('tbody');for(const row of rows){const r=el('tr');row.forEach(value=>{const td=el('td');if(value instanceof Node)td.append(value);else td.textContent=value;r.append(td);});body.append(r);}t.append(body);host.append(t);
}
const PERIOD_LABELS={1:'Gün',7:'Hafta',30:'Ay',90:'3 Ay',180:'6 Ay',365:'12 Ay',0:'Tümü'};
function tone(v){return Number(v.toFixed(1))>0?'positive':Number(v.toFixed(1))<0?'negative':'';}
function periodTabs(selector,report,selected,field='equity'){
 document.querySelectorAll(selector).forEach(b=>{
  const d=Number(b.dataset.overviewDays??b.dataset.days),ready=report&&!report.summary.universe_pending&&report.summary.status!=='not_started'&&report.curve.length>1;
  const ret=ready?M.period(report,d,field).ret:null;
  b.setAttribute('aria-pressed',d===selected);
  b.replaceChildren(el('span',PERIOD_LABELS[d]),el('span',ret==null?'—':M.signed(ret)+'%', 'period-return '+(ret==null?'period-unavailable':tone(ret))));
 });
}
function statStrip(id,report,selected,field='equity'){
 const result=M.overview(report,selected),ready=result.state==='ready',host=$(id);
 host.className=ready?'stat-strip':'stat-strip stat-empty';
 if(!ready){
  const waiting=id==='overview-stats'?source==='forward':view==='forward';
  const banner=el('div',null,'stats-info');banner.setAttribute('role','status');
  banner.append(el('p',waiting?"Test 27 Ekim 2026'da başladı. İlk sonuçlar ilk gün kapanınca (03:20 TR) burada. Şimdilik 'Geçmiş simülasyon (örnek)' ile nasıl görüneceğine bakabilirsin.":referenceState||result.message));
  if(waiting){const button=el('button','Geçmiş simülasyon (örnek)');button.onclick=()=>{view='overview';source='reference';render();ensureReference();};banner.append(button);}
  host.replaceChildren(banner);return;
 }
 let values=[];
 if(ready){const p=M.period(report,selected,field),bh=M.period(report,selected,'buy_hold_equity');
  values=[num(p.curve[0][field])+' USDT',num(p.curve.at(-1)[field])+' USDT',M.signed(p.net)+' USDT',pct(p.ret),pct(bh.ret),field==='equity'?num(result.trades,0):'—',ddPct(p.drawdown)];}
 const labels=['Başlangıç','Şu an','Kâr/Zarar','Getiri %','Al-tut %','İşlem','En kötü düşüş'];
 $(id).replaceChildren(...labels.map((label,i)=>{const n=el('div',null,'stat');n.append(el('small',label),el('strong',values[i],ready&&[2,3].includes(i)?tone(result.net):''));return n;}));
}
function overviewTable(rows){
 // Keep unavailable rows last in either direction; never display synthetic zero results.
 const value=r=>overviewSort==='bot'?r.t:overviewSort==='verdict'?r.result.verdict:overviewSort==='diff'?r.result.ret-r.result.benchmark:r.result[overviewSort];
 const sorted=[...rows].sort((a,b)=>{
  const state=Number(a.result.state!=='ready')-Number(b.result.state!=='ready');if(state)return state;
  if(a.result.state!=='ready')return BOT_ORDER.indexOf(a.t)-BOT_ORDER.indexOf(b.t);
  const av=value(a),bv=value(b);return (typeof av==='number'?av-bv:String(av??a.t).localeCompare(String(bv??b.t),'tr'))*(overviewAscending?1:-1);
 });
 const t=el('table'),head=el('thead'),hr=el('tr');
 for(const [label,key]of [['Bot','bot'],['Bakiye','end'],['Kâr/Zarar USDT','net'],['Getiri %','ret'],['Al-tut %','benchmark'],['Fark','diff'],['İşlem','trades'],['Durum','verdict']]){
  const th=el('th');th.scope='col';th.setAttribute('aria-sort',overviewSort===key?(overviewAscending?'ascending':'descending'):'none');
  const b=el('button',label+(overviewSort===key?(overviewAscending?' ↑':' ↓'):''));b.onclick=()=>{overviewAscending=overviewSort===key?!overviewAscending:key==='bot';overviewSort=key;renderOverview();};th.append(b);hr.append(th);
 }
 head.append(hr);t.append(head);const body=el('tbody');
 for(const {t:key,result:r}of sorted){const row=el('tr',null,key===overviewTrack?'selected-row':'');row.dataset.bot=key;
  row.onclick=()=>{overviewTrack=key;renderOverview();};
  const name=el('td'),button=el('button',key.toUpperCase()+' · '+FRIENDLY[key][0],'bot-select');button.setAttribute('aria-pressed',key===overviewTrack);button.onclick=()=>{overviewTrack=key;renderOverview();};name.append(button,el('small',FRIENDLY[key][1]));row.append(name);
  if(r.state==='ready'){
   for(const [text,v]of [[num(r.end),null],[M.signed(r.net),r.net],[pct(r.ret),r.ret],[pct(r.benchmark),r.benchmark],[pct(r.ret-r.benchmark),r.ret-r.benchmark],[num(r.trades,0),null]])row.append(el('td',text,v==null?'':tone(v)));
   const td=el('td');td.append(el('span',r.verdict,'verdict '+tone(r.ret-r.benchmark)));row.append(td);
  }else{for(let i=0;i<6;i++)row.append(el('td','—','muted'));const td=el('td');td.append(el('span',source==='reference'&&!DATA.views.reference?referenceState||'Veri bekleniyor':r.message,'muted'));row.append(td);}
  body.append(row);
 }
 t.append(body);$('overview-comparison').replaceChildren(t);
}
function render(){
 const title={overview:'Özet',forward:'İleriye dönük test',reference:'Geçmiş simülasyon',research:'Araştırma özeti'}[view];
 $('page-title').textContent=title;$('breadcrumb').textContent='Sanal Test / '+title;
 document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.view===view));
 $('overview-content').hidden=view!=='overview';
 $('forward-content').hidden=!['forward','reference'].includes(view);$('research-content').hidden=view!=='research';
 if(view==='overview'){renderOverview();return;}
 if(view==='research'){research();return;}
 $('detail-content').hidden=view==='reference'&&!DATA.views.reference;
 if(view==='reference'&&!DATA.views.reference){$('state').textContent=referenceState;return;}
 const available=Object.keys(DATA.views[view]||{});
 if(!available.includes(track.startsWith('bh')?'r'+track.slice(2):track))track=available[0]||'r1';
 $('tracks').replaceChildren();
 available.forEach(t=>{for(const [key,label] of [[t,`${t.toUpperCase()} · ${DATA.registry[t].name} · ${DATA.registry[t].description}`],['bh'+t.slice(1),'Al-tut '+t.toUpperCase()+' evreni']]){const b=el('button',label);b.dataset.track=key;b.setAttribute('aria-pressed',key===track);b.onclick=()=>{track=key;render();};$('tracks').append(b);}});
 document.querySelectorAll('[data-days]').forEach(b=>b.setAttribute('aria-pressed',+b.dataset.days===days));
 $('reference-label').hidden=view!=='reference';$('monthly-panel').hidden=view!=='reference';
 const reports=DATA.views[view];if(!reports){$('state').textContent='Referans verisi henüz üretilmedi.';return;}
 const bh=track.startsWith('bh'),key=bh?'r'+track.slice(-1):track,report=reports[key];
 $('track-description').textContent=DATA.registry[key].description;
 const ranked=Object.entries(reports).map(([t,r])=>({t,p:M.period(r,days),pending:r.summary.universe_pending}));
 const net=[...ranked].sort((a,b)=>Number(a.pending)-Number(b.pending)||b.p.ret-a.p.ret),dd=[...ranked].sort((a,b)=>Number(a.pending)-Number(b.pending)||a.p.drawdown-b.p.drawdown);
 table($('comparison'),['Net getiri sırası','İzlek','Net getiri','Max DD sırası','İzlek','Max DD'],net.map((r,i)=>[r.pending?'—':i+1,r.t.toUpperCase(),r.pending?'Snapshot bekliyor':pct(r.p.ret),dd[i].pending?'—':i+1,dd[i].t.toUpperCase(),dd[i].pending?'Snapshot bekliyor':ddPct(dd[i].p.drawdown)]));
 const p=M.period(report,days,bh?'buy_hold_equity':'equity'),s=report.summary;
 periodTabs('[data-days]',report,days,bh?'buy_hold_equity':'equity');
 statStrip('detail-stats',report,days,bh?'buy_hold_equity':'equity');
 $('state').textContent=s.universe_pending?'Evren snapshot bekleniyor · 26 Ekim UTC kapanışı gerekli':s.status==='not_started'?'Başlamadı · 27 Ekim 2026 UTC’den sonra ilk tam gün kapanınca sonuç oluşur.':view==='forward'?'İleri dönem sürüyor':'Sabit referans · nightly yeniden hesaplanmaz';
 $('period-warning').textContent=p.insufficient?`Bu dönem için yeterli veri yok (${p.available} gün var) · Tüm mevcut veri gösteriliyor.`:`${date(p.curve[0].date)} → ${date(p.curve.at(-1).date)} · ${p.days} gün · UTC`;
 let fees=p.fees;
 if(bh){const initial=report.curve[0].buy_hold_equity;fees=p.days?((p.offset===0?initial*.0015/1.0015:0)+report.curve.at(-1).buy_hold_equity*.0015/.9985):0;}
 const cards=[['Getiri',pct(p.ret)],['Max düşüş',num(p.drawdown)+'%'],['Kapalı işlem',bh?'—':num(p.closed.length,0)],['Kazanma oranı',bh?'—':pct(p.win)],['Ödenen komisyon',num(fees,2)+' USDT'],['En iyi işlemin kârdaki payı',bh?'—':pct(p.share)],['En iyi işlem olmadan',bh?'—':pct(p.without)],['Calmar',num(p.calmar,2)]];
 $('kpis').replaceChildren(...cards.map(([label,value])=>{const c=el('article',null,'card');c.append(el('h3',label),el('strong',value));return c;}));
 const series=[{values:p.values,color:COLORS[0]},{values:M.period(report,days,'buy_hold_equity').values,color:COLORS[1],dashed:true}];
 if(s.fee_stress&&!bh){const stress={summary:{...s,daily_returns:[]},curve:s.fee_stress.curve};series.push({values:M.period(stress,days).values,color:COLORS[2]});}
 plot('equity',series,'line',p.curve.map(r=>r.date));plot('drawdown',[{values:p.dd,color:'#F6465D'}],'area',p.curve.map(r=>r.date));
 plot('returns',[{values:p.returns,color:COLORS[0]}],'bars',p.curve.slice(0,-1).map(r=>r.date));
 $('coins').replaceChildren();
 let coins=p.coin;
 if(bh){coins={};const first=report.summary.buy_hold_pairs||[]; // per-coin B&H is supplied by daily reports
  const before=s.daily_returns?.[p.offset-1]?.buy_hold_per_coin_cumulative||{};
  const after=s.daily_returns?.at(-1)?.buy_hold_per_coin_cumulative||{};
  first.forEach(k=>coins[k]=(after[k]||0)-(before[k]||0));
 }
 const contribution=Object.entries(coins).sort((a,b)=>b[1]-a[1]),max=Math.max(1,...contribution.map(r=>Math.abs(r[1])));
 if(!contribution.length)$('coins').append(el('p','Henüz katkı verisi yok.','muted'));
 contribution.forEach(([coin,value])=>{const row=el('div',null,'coin');const bar=el('span',null,'coin-bar');bar.style.width=Math.abs(value)/max*100+'%';bar.style.background=value>=0?'#2EBD85':'#F6465D';row.append(el('span',coin),el('b',num(value,2)),bar);$('coins').append(row);});
 const opened=bh?[]:s.open_positions||[];
 table($('open'),['Parite','Giriş (UTC)','Giriş fiyatı','Değerleme fiyatı','Güncel K/Z','Tutma (gün)'],opened.map(t=>[t.pair,date(t.entry_date),num(t.entry_price,4),num(t.valuation_price,4),pct(t.profit_pct),num(t.holding_days,0)]));
 if(!opened.length)$('open').textContent=bh?'Pasif sepet; sanal strateji pozisyonu yok.':'Henüz açık pozisyon yok.';
 const closed=bh?[]:[...p.closed].sort((a,b)=>{const av=a[sortColumn],bv=b[sortColumn];return(typeof av==='number'?av-bv:String(av).localeCompare(String(bv)))*(ascending?1:-1);});
 table($('closed'),['Parite','Giriş (UTC)','Çıkış (UTC)','Giriş fiyatı','Çıkış fiyatı','Net K/Z (USDT)','Komisyon','Net %'],closed.map(t=>[t.pair,date(t.entry_date),date(t.exit_date),num(t.entry_price,4),num(t.exit_price,4),num(t.profit_usdt,2),num(t.fees_usdt,2),pct(t.profit_pct)]),['pair','entry_date','exit_date','entry_price','exit_price','profit_usdt','fees_usdt','profit_pct']);
 if(!closed.length)$('closed').textContent='Henüz kapanmış işlem yok.';
 timeline(bh?[]:[...(s.closed_trades||[]),...opened],p);
 if(view==='reference')heatmap(M.months(p.curve,bh?'buy_hold_equity':'equity'));
 health();
}
function timeline(trades,p){
 const host=$('timeline');host.replaceChildren();const start=new Date(p.curve[0].date),end=new Date(p.curve.at(-1).date);
 const selected=trades.filter(t=>new Date(t.entry_date)<end&&new Date(t.exit_date||t.valuation_date)>=start);
 if(!selected.length){host.append(el('p','Bu dönemde pozisyon yok.','muted'));return;}
 const pairs=[...new Set(selected.map(t=>t.pair))];const chart=svg('svg',{viewBox:`0 0 900 ${pairs.length*32+30}`,role:'img','aria-label':'İşlem giriş ve çıkış tarihleri'});
 const xx=v=>140+Math.max(0,Math.min(1,(new Date(v)-start)/Math.max(end-start,1)))*730;
 pairs.forEach((pair,i)=>{const t=svg('text',{x:0,y:i*32+22,fill:'#A1A1A6','font-size':14});t.textContent=pair;chart.append(t);});
 selected.forEach(t=>{const y=pairs.indexOf(t.pair)*32+18,x1=xx(t.entry_date),x2=xx(t.exit_date||t.valuation_date);chart.append(svg('path',{d:`M${x1} ${y}H${x2}`,stroke:'#626269','stroke-width':2}));
  const title=`${t.pair} · ${date(t.entry_date)} → ${date(t.exit_date||t.valuation_date)} · ${pct(t.profit_pct)}`;
  for(const shape of [svg('polygon',{points:`${x1},${y-6} ${x1-5},${y+4} ${x1+5},${y+4}`,fill:COLORS[0]}),svg('circle',{cx:x2,cy:y,r:4,fill:t.exit_date?COLORS[1]:'#0F0F10',stroke:COLORS[1]})]){const label=svg('title');label.textContent=title;shape.append(label);chart.append(shape);}
 });host.append(chart);
}
function heatmap(months){const years=[...new Set(Object.keys(months).map(k=>k.slice(0,4)))];table($('monthly'),['Yıl','Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'],years.map(y=>[y,...Array.from({length:12},(_,i)=>{const v=months[`${y}-${String(i+1).padStart(2,'0')}`],n=el('span',pct(v),'heat');if(v!=null)n.style.background=v>=0?'#2EBD8520':'#F6465D2c';return n;})]));}
function health(){
 const h=DATA.health,last=h.runs.at(-1),counts=M.healthCounts(h.successful_dates,new Date(),h.start_date);
 const yesterday=new Date(Date.now()-86400000).toISOString().slice(0,10);
 const actual=h.latest_closed||DATA.views.forward.r1.summary.date;
 const fresh=last?.data_freshness&&actual===yesterday;
 $('health-status').textContent=`Beklenen / başarılı gün: ${counts.expected} / ${counts.actual} · Eksik: ${counts.missing} · Son mum: ${actual||'Henüz yok'} · Beklenen: ${yesterday} UTC · ${fresh?'Güncel':'Kontrol gerekli'}`;
 table($('health'),['Çalışma (UTC)','Sonuç','Veri tazeliği (koşu anı)','Parite iyi / eksik','Süre'],[...h.runs].reverse().map(r=>[new Date(r.run_date).toLocaleString('tr-TR',{timeZone:'UTC'}),r.success?'Başarılı':'Başarısız',r.data_freshness?'Güncel':'Kontrol gerekli',`${r.pairs_ok.length} / ${r.pairs_missing.length}`,num(r.duration_seconds,1)+' sn']));
}

function research(){
 const r=DATA.research;if(!r){$('research-date').textContent='Araştırma snapshot bulunamadı.';return;}
 $('research-date').textContent='Sabit araştırma snapshot · '+date(r.generated_at);
 table($('research-strategies'),['Strateji','Aile','Mum','Açıklama','Durum','Eleme nedeni'],r.strategies.map(s=>[s.name,s.family,s.timeframe,s.description,s.status,s.elimination_reason||'—']));
 const host=$('research-evaluations');host.replaceChildren();
 [...new Set(r.evaluations.map(e=>e.evidence_type))].forEach(group=>{host.append(el('h3',group));const t=el('div',null,'table-scroll');host.append(t);table(t,['Strateji','Evren','Dönem UTC','Tek yön ücret','İşlem','Net getiri','Max DD','DD türü','Calmar'],r.evaluations.filter(e=>e.evidence_type===group).map(e=>[e.strategy,e.universe,e.period,pct(e.fee*100),num(e.trades,0),pct(e.net_return_pct),ddPct(e.max_dd_pct),e.dd_type,num(e.calmar,2)]));});
 const pts=r.evaluations.filter(e=>e.max_dd_pct!=null&&e.net_return_pct!=null),chart=svg('svg',{viewBox:'0 0 900 330',role:'img','aria-label':'Getiri ve max düşüş dağılımı'});
 const ymin=Math.min(0,...pts.map(e=>e.net_return_pct)),ymax=Math.max(1,...pts.map(e=>e.net_return_pct)),xmax=Math.max(1,...pts.map(e=>e.max_dd_pct));
 for(let i=0;i<5;i++){const y=280-i*60,t=svg('text',{x:0,y:y+4,fill:'#A1A1A6','font-size':11});t.textContent=num(ymin+(ymax-ymin)*i/4)+'%';chart.append(t,svg('path',{d:`M65 ${y}H880`,stroke:'rgba(255,255,255,.06)'}));const x=65+i*815/4,tx=svg('text',{x,y:310,fill:'#A1A1A6','font-size':11});tx.textContent=num(xmax*i/4)+'% DD';chart.append(tx);}
 const groups=[...new Set(pts.map(e=>e.evidence_type))];
 pts.forEach(e=>{const detail=`${e.strategy} · ${e.evidence_type} · ${e.universe} · ücret ${pct(e.fee*100)} · getiri ${pct(e.net_return_pct)} · DD ${ddPct(e.max_dd_pct)} (${e.dd_type})`;const c=svg('circle',{cx:65+e.max_dd_pct/xmax*815,cy:280-(e.net_return_pct-ymin)/(ymax-ymin)*240,r:5,fill:COLORS[groups.indexOf(e.evidence_type)%COLORS.length],tabindex:0,role:'button','aria-label':detail});const title=svg('title');title.textContent=detail;c.append(title);c.onclick=c.onfocus=()=>{$('scatter-detail').textContent=detail;};chart.append(c);});$('research-scatter').replaceChildren(chart);
 const feeGroups=[...new Set(r.fee_stress.map(e=>[e.strategy,e.evidence_type,e.universe].join(' · ')))];
 const feeSelect=$('research-fee-select');if(!feeSelect.options.length)feeGroups.forEach(g=>feeSelect.append(el('option',g)));
 const feeRender=()=>{const points=r.fee_stress.filter(e=>[e.strategy,e.evidence_type,e.universe].join(' · ')===feeSelect.value).sort((a,b)=>a.fee-b.fee);plot('research-fee',[{values:points.map(e=>e.net_return_pct),color:COLORS[0]}],'line',points.map(e=>pct(e.fee*100)),v=>v);const labels=el('p',points.map(e=>`${pct(e.fee*100)} ücret → ${pct(e.net_return_pct)} getiri`).join(' · '),'muted');$('research-fee').append(labels);};feeSelect.onchange=feeRender;feeRender();
 table($('research-concentration'),['Strateji','Evren','Ücret','İlk 3 payı','En iyi 1 olmadan','En iyi 3 olmadan','En iyi 5 olmadan'],r.concentration.map(c=>[c.strategy,c.universe,pct(c.fee*100),pct(c.top3_share_pct),pct(c.without_best1_pct),pct(c.without_best3_pct),pct(c.without_best5_pct)]));
 const ai=$('research-ai');ai.replaceChildren();r.ai_summary.tried.forEach(t=>ai.append(el('p',t)));ai.append(el('p',r.ai_summary.calibration_bug),el('p',r.ai_summary.verdict));const nums=el('div',null,'table-scroll');ai.append(nums);table(nums,['Deney','İşlem','Getiri','DD','Eğitim / CV olay','CV AUC','Eşik'],r.ai_summary.key_numbers.map(k=>[k.experiment,num(k.trades,0),pct(k.net_return_pct),ddPct(k.max_dd_pct),`${num(k.training_events,0)} / ${num(k.cv_events,0)}`,num(k.cv_auc,3),num(k.threshold,2)]));
 for(const [id,rows]of [['research-criteria',r.decision_criteria],['research-limitations',r.limitations]])$(id).replaceChildren(...rows.map(t=>el('li',t)));
 const select=$('research-equity-select');if(!select.options.length)r.equity_series.forEach((s,i)=>{const o=el('option',`${s.strategy} · ${s.evidence_type} · ${s.dd_type}`);o.value=i;select.append(o);});
 const equityRender=()=>{const s=r.equity_series[+select.value];$('research-equity-label').textContent=`${s.sampling} · Tek yön ücret ${pct(s.fee*100)} · DD: ${s.dd_type}`;plot('research-equity',[{values:s.curve.map(p=>p.value),color:COLORS[0]}],'line',s.curve.map(p=>p.date));};select.onchange=equityRender;equityRender();
}

async function ensureReference(){
 if(DATA.views.reference)return;
 if(!DATA.reference_url){referenceState='Geçmiş simülasyon henüz üretilmedi.';render();return;}
 if(!referenceLoad){
  referenceState='Geçmiş simülasyon yükleniyor…';
  referenceLoad=fetch(DATA.reference_url).then(r=>{if(!r.ok)throw new Error('reference');return r.json();})
   .then(data=>{DATA.views.reference=data;referenceState='';})
   .catch(()=>{referenceState='Geçmiş simülasyon yüklenemedi. Tekrar seçerek yeniden deneyebilirsin.';referenceLoad=null;});
 }
 render();await referenceLoad;render();
}
const FRIENDLY={
 r1:['Çekirdek',"Sadece BTC, ETH ve SOL'de işlem yapar"],
 r5:['Seçili 33','Önceden belirlenen 33 coinde işlem yapar'],
 r6:['Büyük coinler','Piyasa değeri en büyük 10 coinde işlem yapar'],
 r7:['Geniş keşif','İşlem hacmine göre seçilen 70 coini takip eder'],
 r8:['Geniş keşif +','Aynı 70 coini takip eder; aynı anda 10 coinde işlem yapabilir']
};
function renderOverview(){
 document.querySelectorAll('[data-overview-days]').forEach(b=>b.setAttribute('aria-pressed',+b.dataset.overviewDays===overviewDays));
 document.querySelectorAll('[data-source]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.source===source));
 const reports=DATA.views[source];
 $('overview-label').textContent=source==='reference'?'Örnek: geçmiş veriyle simülasyon, gerçek test değil'+(referenceState?' · '+referenceState:''):'Her gün aynı kurallar. Sonuçlar ilk tam gün kapandıktan sonra burada.';
 const rows=BOT_ORDER.filter(t=>DATA.registry[t]).map(t=>({t,result:M.overview(reports?.[t],overviewDays,source)}));
 const ready=rows.filter(r=>r.result.state==='ready'),best=[...ready].sort((a,b)=>b.result.ret-a.result.ret)[0];
 const tied=best&&ready.filter(r=>Math.abs(r.result.ret-best.result.ret)<1e-9);
 $('ranking-title').textContent=best?(tied.length>1?'Bu dönemde aynı sonuç: '+tied.map(r=>r.t.toUpperCase()).join(', '):'Bu dönemin en iyisi: '+best.t.toUpperCase()):'İlk sonuçlarla birlikte karşılaştırma burada';
 const selected=rows.find(r=>r.t===overviewTrack);
 $('overview-bots').replaceChildren(...BOT_ORDER.filter(t=>DATA.registry[t]).map(t=>{
  const button=el('button',t.toUpperCase());button.setAttribute('aria-pressed',t===overviewTrack);
  button.setAttribute('aria-label',t.toUpperCase()+' · '+FRIENDLY[t][0]);
  button.onclick=()=>{overviewTrack=t;renderOverview();};return button;
 }));
 $('overview-bot-title').textContent=overviewTrack.toUpperCase()+' · '+FRIENDLY[overviewTrack][0];
 $('overview-bot-description').textContent=FRIENDLY[overviewTrack][1];
 periodTabs('[data-overview-days]',reports?.[selected?.t],overviewDays);
 statStrip('overview-stats',reports?.[selected?.t],overviewDays);
 overviewTable(rows);
 const host=$('bot-cards');host.replaceChildren();
 for(const {t,result:r}of rows){
  const card=el('article',null,'bot-card'),[name,description]=FRIENDLY[t];
  card.append(el('div',t.toUpperCase()+' / SANAL BOT','eyebrow'),el('h3',name),el('p',description,'bot-description'));
  if(source==='reference'&&!reports){card.append(el('p',referenceState||'Geçmiş simülasyon henüz üretilmedi.','muted'));host.append(card);continue;}
  if(r.state!=='ready'){card.append(el('p',r.message,'empty-state'));host.append(card);continue;}
  card.append(el('p',num(r.start,0)+' USDT → '+num(r.end,0)+' USDT','balance'),
   el('strong',M.signed(r.net)+' USDT ('+M.signed(r.ret)+'%)','bot-result '+(r.net>0?'positive':r.net<0?'negative':'')),el('p',r.message));
  card.append(el('p',date(r.curve[0].date)+' → '+date(r.curve.at(-1).date)+(r.insufficient?' ('+r.available+' günlük veri)':''),'muted period-detail'));
  card.append(el('p','Sadece alıp tutsaydın: '+M.signed(r.benchmark)+'%'),el('span',r.verdict,'verdict '+(r.ret>r.benchmark?'positive':r.ret<r.benchmark?'negative':'')));
  card.append(el('p','Bu dönemde '+r.trades+' yeni işlem','trade-count'));
  card.append(el('p',(source==='reference'?'Simülasyon sonunda':'Şu an')+' '+r.positions.length+' coinde pozisyon var'+(r.positions.length?': '+r.positions.join(', '):'.'),'muted'));
  host.append(card);
 }
}
$('all-columns').onclick=()=>{const button=$('all-columns'),expanded=button.getAttribute('aria-pressed')==='true';button.setAttribute('aria-pressed',!expanded);button.textContent=expanded?'Tüm sütunlar':'Temel sütunlar';$('overview-comparison').className='table-scroll'+(expanded?'':' show-all-columns');};
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;render();if(view==='reference')ensureReference();});
document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>{source=b.dataset.source;render();if(source==='reference')ensureReference();});
document.querySelectorAll('[data-overview-days]').forEach(b=>b.onclick=()=>{overviewDays=+b.dataset.overviewDays;render();});
document.querySelectorAll('[data-track]').forEach(b=>b.onclick=()=>{track=b.dataset.track;render();});
document.querySelectorAll('[data-days]').forEach(b=>b.onclick=()=>{days=+b.dataset.days;render();});
render();
setInterval(health,60000);
