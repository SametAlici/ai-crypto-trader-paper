/* Pure period computations shared by the dashboard and synthetic Node tests. */
(function (root) {
'use strict';
const DAY = 86400000;
function period(report, requested, field='equity') {
  const all=report.curve, days=all.length-1, insufficient=requested>days;
  const count=requested && !insufficient ? requested : days;
  const offset=days-count, curve=all.slice(offset), base=curve[0][field];
  const values=curve.map(r=>r[field]/base*100);
  let peak=100; const dd=values.map(v=>{peak=Math.max(peak,v); return (v/peak-1)*100;});
  const returns=values.slice(1).map((v,i)=>(v/values[i]-1)*100);
  const start=new Date(curve[0].date), end=new Date(curve.at(-1).date);
  const closed=(report.summary.closed_trades||[]).filter(t=>new Date(t.exit_date)>=start && new Date(t.exit_date)<end);
  const before=report.summary.daily_returns?.[offset-1]||{};
  const after=report.summary.daily_returns?.at(-1)||{};
  const coin={}, trade={};
  for (const [k,v] of Object.entries(after.per_coin_cumulative||{})) coin[k]=v-(before.per_coin_cumulative?.[k]||0);
  for (const [k,v] of Object.entries(after.per_trade_cumulative||{})) trade[k]=v-(before.per_trade_cumulative?.[k]||0);
  const profits=closed.map(t=>trade[t.trade_id]??t.profit_usdt).sort((a,b)=>b-a);
  const net=curve.at(-1)[field]-base, best=profits[0]||0;
  const drawdown=-Math.min(...dd), ret=(values.at(-1)-100);
  const fees=(after.fees_cumulative||0)-(before.fees_cumulative||0);
  return {curve,values,dd,returns,days:count,available:days,insufficient,offset,closed,coin,
    net,ret,drawdown,fees,win:closed.length?closed.filter(t=>t.profit_usdt>0).length/closed.length*100:null,
    share:net>0&&profits.length?best/net*100:null,top3:net>0?profits.slice(0,3).reduce((a,b)=>a+b,0)/net*100:null,
    without:(net-best)/base*100,
    calmar:count>=30&&drawdown>0?((values.at(-1)/100)**(365/count)-1)/(drawdown/100):null};
}
function months(curve, field='equity') {
  const grouped={};
  for(let i=1;i<curve.length;i++) {
    const month=new Date(new Date(curve[i].date)-DAY).toISOString().slice(0,7);
    grouped[month]=(grouped[month]??1)*curve[i][field]/curve[i-1][field];
  }
  return Object.fromEntries(Object.entries(grouped).map(([k,v])=>[k,(v-1)*100]));
}
function healthCounts(successfulDates, now, start) {
  const current=new Date(now), first=new Date(start+'T00:20:00Z').getTime()+DAY;
  const expected=Math.max(0,Math.floor((current-first)/DAY)+1);
  const lastDue=new Date(current.getTime()-20*60000).toISOString().slice(0,10);
  const firstDate=new Date(first).toISOString().slice(0,10);
  const actual=new Set(successfulDates.filter(d=>d>=firstDate&&d<=lastDue)).size;
  return {expected,actual,missing:Math.max(0,expected-actual)};
}
root.TradeMetrics={period,months,healthCounts};
if(typeof module!=='undefined')module.exports=root.TradeMetrics;
})(globalThis);
