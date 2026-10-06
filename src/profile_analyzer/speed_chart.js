// Seconds per game year chart, shared by the profiler explorer and the standalone speed report.
// speed = game_speed.read_session(): segments [{start,end,years,seconds,per_year,reference,outlier,sources}].
function renderSpeed(container, speed){
 const NS='http://www.w3.org/2000/svg';
 const node=(tag,attrs={},text)=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e};
 const html=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e};
 const one=v=>v==null?'—':v.toFixed(1);
 const date=v=>{const y=Math.floor(v),d=Math.round((v-y)*365),starts=[0,31,59,90,120,151,181,212,243,273,304,334];let m=0;while(m<11&&starts[m+1]<=d)m++;return y+'.'+(m+1)+'.'+(d-starts[m]+1)};
 container.replaceChildren();
 const segs=speed.segments||[], s=speed.summary||{};
 if(!segs.length){container.append(html('p','No game dates yet: the speed log and the autosaves of this session hold fewer than two dated points.','muted'));return}
 const kept=segs.filter(x=>!x.outlier), out=segs.filter(x=>x.outlier);
 const stats=html('div',undefined,'speed-stats');
 for(const [label,val] of [['Seconds per game year (pauses removed)',one(s.clean_seconds_per_year)],['Raw, pauses included',one(s.raw_seconds_per_year)],['Game dates',s.first_date+' → '+s.last_date],['Pause outliers removed',out.length+' of '+segs.length+' · '+Math.round(s.paused_seconds||0)+' s']]){const d=html('div',undefined,'speed-stat');d.append(html('strong',val),html('span',label));stats.append(d)}
 container.append(stats);
 const w=900,h=330,left=58,right=18,top=20,bottom=44;
 const x0=Math.min(...segs.map(x=>x.start)),x1=Math.max(...segs.map(x=>x.end));
 const keptMax=Math.max(1,...(kept.length?kept:segs).map(x=>x.per_year));
 const step=[1,2,5,10,20,25,50,100,200,500].find(v=>keptMax*1.25/v<=6)||1000, ymax=Math.ceil(keptMax*1.25/step)*step;
 const X=v=>left+(v-x0)/(x1-x0||1)*(w-left-right), Y=v=>h-bottom-Math.min(v,ymax)/ymax*(h-top-bottom);
 const svg=node('svg',{viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':'Wall-clock seconds per game year over game dates'});
 for(let v=0;v<=ymax+1e-9;v+=step){svg.append(node('line',{x1:left,x2:w-right,y1:Y(v),y2:Y(v),class:'speed-grid'}));svg.append(node('text',{x:left-8,y:Y(v)+4,'text-anchor':'end'},String(v)))}
 const span=x1-x0, ystep=[1,2,5,10,20,25,50,100].find(v=>span/v<=10)||200;
 for(let v=Math.ceil(x0/ystep)*ystep;v<=x1;v+=ystep)svg.append(node('text',{x:X(v),y:h-bottom+20,'text-anchor':'middle'},String(v)));
 svg.append(node('text',{x:left,y:12},'seconds per game year'),node('text',{x:(w+left)/2,y:h-4,'text-anchor':'middle'},'game year'));
 if(s.clean_seconds_per_year!=null){const y=Y(s.clean_seconds_per_year);svg.append(node('line',{x1:left,x2:w-right,y1:y,y2:y,class:'speed-mean'}));svg.append(node('text',{x:w-right,y:y-6,'text-anchor':'end',class:'speed-mean-label'},'average '+one(s.clean_seconds_per_year)))}
 for(const seg of segs){
  const g=node('g',{class:seg.outlier?'speed-out':'speed-seg'}), y=Y(seg.per_year);
  g.append(node('rect',{x:X(seg.start),y,width:Math.max(1.5,X(seg.end)-X(seg.start)),height:h-bottom-y,rx:1.5}));
  if(seg.outlier&&seg.per_year>ymax)g.append(node('text',{x:(X(seg.start)+X(seg.end))/2,y:top+10,'text-anchor':'middle'},'↑ '+Math.round(seg.per_year)));
  g.append(node('title',{},`${date(seg.start)} → ${date(seg.end)}: ${one(seg.per_year)} s per game year (${Math.round(seg.seconds)} s for ${seg.years.toFixed(2)} years, ${seg.sources})`+(seg.outlier?` · pause outlier, neighbours ${one(seg.reference)}`:'')));
  svg.append(g);
 }
 const run=speed.running||[];
 if(run.length>1){svg.append(node('polyline',{points:run.map(p=>`${X(p.x)},${Y(p.per_year)}`).join(' '),class:'speed-run'}));for(const p of run){const c=node('circle',{cx:X(p.x),cy:Y(p.per_year),r:3,class:'speed-run-dot'});c.append(node('title',{},`${date(p.x)}: ${one(p.per_year)} s per game year (${speed.running_window}-year running average)`));svg.append(c)}}
 const chart=html('div',undefined,'speed-chart');chart.append(svg);container.append(chart);
 container.append(html('p',`Bars: wall-clock seconds for each stretch between two dated points (speed log rows and autosaves of this session), divided by the game years it covers. Line: ${speed.running_window||10}-year running average. Dashed: average of the whole session. Grey bars are more than ${speed.outlier_factor}× slower than their neighbours (paused, menus, alt-tab) and stay out of both averages. Saving time is included.`,'muted speed-note'));
}
