'use strict';
const DATA=JSON.parse(document.getElementById('report-data').textContent);
const $=id=>document.getElementById(id), M=globalThis.TradeMetrics;
let view='forward',track='r1',days=0,sortColumn='exit_date',ascending=false;
const COLORS=['#58e0b5','#a899ff','#76b9ff','#ffc47c','#f58fd3'];
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
 for(let i=0;i<5;i++){const val=lo+(hi-lo)*i/4,yy=y(val);chart.append(svg('path',{d:`M65 ${yy}H880`,stroke:'#283344'}));const text=svg('text',{x:3,y:yy+4,fill:'#9eacbf','font-size':12});text.textContent=num(val);chart.append(text);}
 for(const s of series){
  if(mode==='bars'){s.values.forEach((v,i)=>{const width=815/Math.max(s.values.length,1),xx=65+i*width;const r=svg('rect',{x:xx,y:Math.min(y(v),y(0)),width:Math.max(width*.8,.4),height:Math.max(Math.abs(y(v)-y(0)),.5),fill:v>=0?COLORS[0]:'#fa7d91'});const t=svg('title');t.textContent=`${date(labels[i])}: ${pct(v)}`;r.append(t);chart.append(r);});}
  else{const points=s.values.map((v,i)=>`${x(i,s.values.length)},${y(v)}`).join(' ');
   if(mode==='area')chart.append(svg('polygon',{points:`65,${y(0)} ${points} 880,${y(0)}`,fill:'#fa7d9130'}));
   chart.append(svg('polyline',{points,fill:'none',stroke:s.color,'stroke-width':2.5,'stroke-linejoin':'round'}));
   if(s.values.length===1)chart.append(svg('circle',{cx:65,cy:y(s.values[0]),r:4,fill:s.color}));
  }
 }
 [[65,'start',labels[0]],[880,'end',labels.at(-1)]].forEach(([xx,anchor,label])=>{const t=svg('text',{x:xx,y:252,'text-anchor':anchor,fill:'#9eacbf','font-size':12});t.textContent=labelFormat(label);chart.append(t);});host.append(chart);
}
function table(host,headers,rows,keys=[]){
 host.replaceChildren();if(!rows.length){host.append(el('p','Henüz kayıt yok.','muted'));return;}
 const t=el('table'),head=el('thead'),tr=el('tr');headers.forEach((h,i)=>{const th=el('th');th.scope='col';if(keys[i]){const b=el('button',h+(sortColumn===keys[i]?(ascending?' ↑':' ↓'):''));b.onclick=()=>{ascending=sortColumn===keys[i]?!ascending:true;sortColumn=keys[i];render();};th.append(b);}else th.textContent=h;tr.append(th);});head.append(tr);t.append(head);
 const body=el('tbody');for(const row of rows){const r=el('tr');row.forEach(value=>{const td=el('td');if(value instanceof Node)td.append(value);else td.textContent=value;r.append(td);});body.append(r);}t.append(body);host.append(t);
}
function render(){
 document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.view===view));
 $('forward-content').hidden=view==='research';$('research-content').hidden=view!=='research';
 if(view==='research'){research();return;}
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
 $('state').textContent=s.universe_pending?'Evren snapshot bekleniyor · 26 Ekim UTC kapanışı gerekli':s.status==='not_started'?'Başlamadı · 27 Ekim 2026 UTC’den sonra ilk tam gün kapanınca sonuç oluşur.':view==='forward'?'İleri dönem sürüyor':'Sabit referans · nightly yeniden hesaplanmaz';
 $('period-warning').textContent=p.insufficient?`Bu dönem için yeterli veri yok (${p.available} gün var) · Tüm mevcut veri gösteriliyor.`:`${date(p.curve[0].date)} → ${date(p.curve.at(-1).date)} · ${p.days} gün · UTC`;
 let fees=p.fees;
 if(bh){const initial=report.curve[0].buy_hold_equity;fees=p.days?((p.offset===0?initial*.0015/1.0015:0)+report.curve.at(-1).buy_hold_equity*.0015/.9985):0;}
 const cards=[['Getiri',pct(p.ret)],['Max düşüş',num(p.drawdown)+'%'],['Kapalı işlem',bh?'—':num(p.closed.length,0)],['Kazanma oranı',bh?'—':pct(p.win)],['Ödenen komisyon',num(fees,2)+' USDT'],['En iyi işlemin kârdaki payı',bh?'—':pct(p.share)],['En iyi işlem olmadan',bh?'—':pct(p.without)],['Calmar',num(p.calmar,2)]];
 $('kpis').replaceChildren(...cards.map(([label,value])=>{const c=el('article',null,'card');c.append(el('h3',label),el('strong',value));return c;}));
 const series=[{values:p.values,color:COLORS[0]},{values:M.period(report,days,'buy_hold_equity').values,color:COLORS[1]}];
 if(s.fee_stress&&!bh){const stress={summary:{...s,daily_returns:[]},curve:s.fee_stress.curve};series.push({values:M.period(stress,days).values,color:COLORS[2]});}
 plot('equity',series,'line',p.curve.map(r=>r.date));plot('drawdown',[{values:p.dd,color:'#fa7d91'}],'area',p.curve.map(r=>r.date));
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
 contribution.forEach(([coin,value])=>{const row=el('div',null,'coin');const bar=el('span',null,'coin-bar');bar.style.width=Math.abs(value)/max*100+'%';bar.style.background=value>=0?COLORS[0]:'#fa7d91';row.append(el('span',coin),el('b',num(value,2)),bar);$('coins').append(row);});
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
 pairs.forEach((pair,i)=>{const t=svg('text',{x:0,y:i*32+22,fill:'#b7c4d5','font-size':14});t.textContent=pair;chart.append(t);});
 selected.forEach(t=>{const y=pairs.indexOf(t.pair)*32+18,x1=xx(t.entry_date),x2=xx(t.exit_date||t.valuation_date);chart.append(svg('path',{d:`M${x1} ${y}H${x2}`,stroke:'#62718a','stroke-width':2}));
  const title=`${t.pair} · ${date(t.entry_date)} → ${date(t.exit_date||t.valuation_date)} · ${pct(t.profit_pct)}`;
  for(const shape of [svg('polygon',{points:`${x1},${y-6} ${x1-5},${y+4} ${x1+5},${y+4}`,fill:COLORS[0]}),svg('circle',{cx:x2,cy:y,r:4,fill:t.exit_date?COLORS[1]:'#111b29',stroke:COLORS[1]})]){const label=svg('title');label.textContent=title;shape.append(label);chart.append(shape);}
 });host.append(chart);
}
function heatmap(months){const years=[...new Set(Object.keys(months).map(k=>k.slice(0,4)))];table($('monthly'),['Yıl','Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'],years.map(y=>[y,...Array.from({length:12},(_,i)=>{const v=months[`${y}-${String(i+1).padStart(2,'0')}`],n=el('span',pct(v),'heat');if(v!=null)n.style.background=v>=0?'#58e0b52c':'#fa7d912c';return n;})]));}
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
 for(let i=0;i<5;i++){const y=280-i*60,t=svg('text',{x:0,y:y+4,fill:'#9eacbf','font-size':12});t.textContent=num(ymin+(ymax-ymin)*i/4)+'%';chart.append(t,svg('path',{d:`M65 ${y}H880`,stroke:'#283344'}));const x=65+i*815/4,tx=svg('text',{x,y:310,fill:'#9eacbf','font-size':12});tx.textContent=num(xmax*i/4)+'% DD';chart.append(tx);}
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

document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{if(b.dataset.view!=='research'&&!DATA.views[b.dataset.view])return;view=b.dataset.view;render();});
document.querySelectorAll('[data-track]').forEach(b=>b.onclick=()=>{track=b.dataset.track;render();});
document.querySelectorAll('[data-days]').forEach(b=>b.onclick=()=>{days=+b.dataset.days;render();});
render();

setInterval(health,60000);
