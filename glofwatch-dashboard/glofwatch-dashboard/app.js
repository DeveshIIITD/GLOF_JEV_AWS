/* GLOFWatch dashboard: no build tools required. API config: config.js */
(() => {
  'use strict';

  const ICONS = {
    layout: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    map: '<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21 3 6"/><path d="M9 3v15M15 6v15"/>',
    chart: '<path d="M3 3v18h18"/><path d="m7 16 4-5 3 3 6-8"/>',
    activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14-5L4 8"/><path d="M4 4v4h4M4 13a8 8 0 0 0 14 5l2-2"/><path d="M20 20v-4h-4"/>',
    download: '<path d="M12 3v12m-4-4 4 4 4-4"/><path d="M4 17v3h16v-3"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/>',
    waves: '<path d="M2 8c2 0 2 2 5 2s3-2 5-2 3 2 5 2 3-2 5-2M2 14c2 0 2 2 5 2s3-2 5-2 3 2 5 2 3-2 5-2"/>',
    alert: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5M12 17h.01"/>',
    layers: '<path d="m12 2 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'map-pin': '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    'arrow-right': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    'arrow-up-right': '<path d="M5 19 19 5M7 5h12v12"/>',
    scan: '<path d="M4 9V5h5M15 5h4v4M19 15v4h-4M9 19H5v-4"/><circle cx="12" cy="12" r="3"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>'
  };
  const icon = (key) => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[key] || ICONS.info}</svg>`;
  for (const element of document.querySelectorAll('[data-icon]')) element.innerHTML = icon(element.dataset.icon);
  const $ = (id) => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  const now = new Date();
  $('today-label').textContent = now.toLocaleDateString('en-IN', {day:'numeric', month:'short', year:'numeric'});

  // All DEMO records are fictional research examples, NOT measured lake conditions.
  const demoSeeds = [
    ['H-01','Demo Lake H-01','Eastern Nepal',27.93,86.89,'high',83,1.19,5.4],
    ['H-02','Demo Lake H-02','Sikkim, India',27.72,88.43,'high',78,0.91,4.9],
    ['H-03','Demo Lake H-03','Western Bhutan',27.96,89.56,'high',73,0.68,4.1],
    ['H-04','Demo Lake H-04','Uttarakhand, India',30.38,79.53,'watch',61,0.84,2.7],
    ['H-05','Demo Lake H-05','Central Nepal',28.20,84.68,'watch',56,0.59,2.1],
    ['H-06','Demo Lake H-06','Arunachal Pradesh',28.17,93.10,'watch',49,0.75,1.3],
    ['H-07','Demo Lake H-07','Himachal Pradesh',32.25,77.16,'low',31,0.48,-0.8],
    ['H-08','Demo Lake H-08','Ladakh, India',34.08,77.54,'low',27,0.65,0.4],
    ['H-09','Demo Lake H-09','Eastern Bhutan',27.78,91.23,'low',23,0.39,-0.5],
    ['H-10','Demo Lake H-10','Northern Pakistan',35.22,74.92,'low',20,0.74,0.7],
    ['H-11','Demo Lake H-11','Western Nepal',29.16,81.48,'low',16,0.52,-1.0],
    ['H-12','Demo Lake H-12','Kashmir, India',34.54,75.08,'low',11,0.68,0.1]
  ];
  const anchorDate = new Date('2026-10-08T08:00:00.000Z');
  function makeDemoHistory(seed, idx) {
    const area = seed[7], change = seed[8];
    return Array.from({length:91}, (_, i) => {
      const back = 90-i;
      const date = new Date(anchorDate.getTime() - back*86400000);
      const wave = Math.sin(i*.27 + idx*.6)*.009 + Math.cos(i*.11+idx)*.005;
      const estimate = area/(1+change/100) + (area-area/(1+change/100)) * (i/90) + wave - (Math.sin(90*.27+idx*.6)*.009 + Math.cos(90*.11+idx)*.005)*(i/90);
      return {date:date.toISOString().slice(0,10),area_km2:+Math.max(0, estimate).toFixed(3)};
    });
  }
  const DEMO_LAKES = demoSeeds.map((seed,i) => ({
    lake_id:seed[0],name:seed[1],region:seed[2],lat:seed[3],lon:seed[4],risk:seed[5],score:seed[6],
    area_km2:seed[7],area_change_pct:seed[8],assessed_at:new Date(anchorDate.getTime()-i*4200000).toISOString(),
    history:makeDemoHistory(seed,i),demo:true
  }));

  const state = {lakes:DEMO_LAKES,selectedId:DEMO_LAKES[0].lake_id,days:30,mode:'demo',search:'',risk:'all',map:null,baseLayers:null,mapView:'regular',tileErrorShown:false,markers:new Map(),fallbackZoom:1,toastTimer:null,leafletLoading:false};
  try { if(localStorage.getItem('glofwatch-map-view')==='satellite')state.mapView='satellite'; } catch { /* Storage may be unavailable. */ }
  const formatNum = (value, digits=2) => Number.isFinite(value) ? value.toFixed(digits) : '—';
  const fmtArea = (value) => Number.isFinite(value) ? `${formatNum(value)} km²` : '—';
  const dateLabel = (value) => {
    if (!value || Number.isNaN(Date.parse(value))) return '—';
    return new Date(value).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
  };
  const relativeDate = (value) => {
    if (!value || Number.isNaN(Date.parse(value))) return 'Unknown';
    const days = Math.round((Date.now()-Date.parse(value))/86400000);
    if (days < 0) return dateLabel(value);
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    return dateLabel(value);
  };
  const riskText = (risk) => ({high:'High',watch:'Watch',low:'Low',unknown:'Unknown'}[risk] || 'Unknown');
  const riskColor = (risk) => ({high:'#d75b53',watch:'#db9a46',low:'#2b9a7e',unknown:'#8c99a2'}[risk] || '#8c99a2');
  const riskPill = (risk) => `<span class="risk-pill ${risk}">${riskText(risk)}</span>`;
  const safeText = (value) => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const selectedLake = () => state.lakes.find(l=>l.lake_id===state.selectedId) || state.lakes[0];

  function showToast(message){const el=$('toast');el.textContent=message;el.classList.add('show');clearTimeout(state.toastTimer);state.toastTimer=setTimeout(()=>el.classList.remove('show'),3700);}
  function setMode(mode,detail='') {
    state.mode=mode;
    const el=$('mode-notice');el.className='notice'+(mode==='error'?' api-error':mode==='live'?' live-data':'');
    $('mode-message').textContent=mode==='demo'?'Demonstration mode — all displayed lake observations and risk scores are simulated.':mode==='live'?'API connected — showing assessments returned by your configured endpoint.':`API unavailable (${detail}). Displaying simulated examples instead.`;
    $('mode-tag').textContent=mode==='live'?'API CONNECTED':mode==='error'?'API OFFLINE':'DEMO DATA';
    $('footer-source').textContent=mode==='live'?'Source: connected API · verify scientific provenance':'Source: simulated demonstration dataset';
    $('chart-caption').textContent=mode==='live'?'API-provided trend (when available)':'Illustrative trend data';
  }
  function renderMetrics(){
    const lakes=state.lakes;
    const totalArea=lakes.reduce((sum,l)=>sum+(Number.isFinite(l.area_km2)?l.area_km2:0),0);
    $('metric-total').textContent=lakes.length;
    $('metric-flagged').textContent=lakes.filter(l=>l.risk==='high').length;
    $('metric-area').innerHTML=`${formatNum(totalArea)} <small>km²</small>`;
    const dates=lakes.map(l=>l.assessed_at).filter(Boolean).sort();
    const latest=dates[dates.length-1];
    $('metric-updated').textContent=relativeDate(latest);
    $('metric-update-foot').textContent=dateLabel(latest);
    $('map-count').textContent=`${lakes.length} lakes`;
    $('metric-coverage').textContent=state.mode==='live'?'From your AWS data feed':'Across demo study locations';
  }
  function selectLake(id, options={}){
    if(!state.lakes.some(l=>l.lake_id===id))return;
    state.selectedId=id;
    renderWatchList();renderTable();renderDetails();renderChart();highlightMap();
    if(options.center && state.map){const lake=selectedLake();if(Number.isFinite(lake.lat)&&Number.isFinite(lake.lon))state.map.flyTo([lake.lat,lake.lon],Math.max(7,state.map.getZoom()),{duration:.65});}
    if(options.scroll)$('trend-section').scrollIntoView({behavior:'smooth',block:'start'});
  }
  function renderWatchList(){
    const priority=[...state.lakes].filter(l=>l.risk==='high'||l.risk==='watch').sort((a,b)=>(b.score??-1)-(a.score??-1)).slice(0,4);
    const parent=$('watch-list');parent.innerHTML='';
    if(!priority.length){const empty=document.createElement('p');empty.className='watch-empty';empty.textContent='No high or watch-level assessments in this dataset.';parent.append(empty);return;}
    for(const lake of priority){
      const b=document.createElement('button');b.type='button';b.className=`watch-item ${lake.risk}${state.selectedId===lake.lake_id?' selected':''}`;
      b.innerHTML=`<span class="watch-icon">${icon('alert')}</span><span class="watch-text"><strong>${safeText(lake.name)}</strong><small>${safeText(lake.region||'Region unavailable')}</small></span><span class="watch-right">${riskPill(lake.risk)}<small>${Number.isFinite(lake.score)?`Score ${lake.score}/100`:'No score'}</small></span>`;
      b.addEventListener('click',()=>selectLake(lake.lake_id,{center:true}));
      parent.append(b);
    }
  }
  function renderTable(){
    const rows=state.lakes.filter(l=>`${l.name} ${l.region} ${l.lake_id}`.toLowerCase().includes(state.search.toLowerCase())&&(state.risk==='all'||l.risk===state.risk));
    $('table-count').textContent=`Showing ${rows.length} of ${state.lakes.length} lakes`;
    const tbody=$('lake-table-body');tbody.innerHTML='';
    if(!rows.length){tbody.innerHTML='<tr><td colspan="7" class="table-empty">No lakes match the selected filters.</td></tr>';return;}
    for(const lake of rows){
      const row=document.createElement('tr');row.tabIndex=0;row.className=lake.lake_id===state.selectedId?'is-selected':'';
      const width=Number.isFinite(lake.score)?Math.max(0,Math.min(100,lake.score)):0;
      row.innerHTML=`<td>${safeText(lake.name)}<span class="lake-id">${safeText(lake.lake_id)}</span></td><td>${safeText(lake.region||'—')}</td><td>${fmtArea(lake.area_km2)}</td><td>${Number.isFinite(lake.score)?lake.score:'—'}<span class="score-bar"><span class="${lake.risk}" style="width:${width}%"></span></span></td><td>${riskPill(lake.risk)}</td><td>${dateLabel(lake.assessed_at)}</td><td style="color:#158f83">${icon('arrow-right')}</td>`;
      row.addEventListener('click',()=>selectLake(lake.lake_id,{center:true,scroll:true}));
      row.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();selectLake(lake.lake_id,{center:true,scroll:true});}});
      tbody.append(row);
    }
  }
  function renderDetails(){
    const lake=selectedLake();if(!lake)return;
    $('selected-name').textContent=lake.name;$('selected-location').textContent=lake.region||'Region unavailable';
    $('selected-status').className=`risk-pill ${lake.risk}`;$('selected-status').textContent=riskText(lake.risk);
    $('detail-area').textContent=fmtArea(lake.area_km2);
    $('detail-score').textContent=Number.isFinite(lake.score)?`${lake.score} / 100`:'—';
    $('detail-change').textContent=Number.isFinite(lake.area_change_pct)?`${lake.area_change_pct>0?'+':''}${formatNum(lake.area_change_pct,1)}%`:'—';
    $('detail-observed').textContent=dateLabel(lake.assessed_at);
    $('chart-subtitle').textContent=`${lake.name} · ${lake.region||'Unknown region'}`;
  }
  function appendSvg(parent,tag,attrs={},content){
    const el=document.createElementNS(svgNS,tag);
    for(const [key,val] of Object.entries(attrs))el.setAttribute(key,String(val));
    if(content!=null)el.textContent=String(content);
    parent.append(el);return el;
  }
  function renderChart(){
    const svg=$('trend-chart'), empty=$('chart-empty'), lake=selectedLake();svg.innerHTML='';
    if(!lake)return;
    $('chart-reading').innerHTML=`${formatNum(lake.area_km2)} <span>km²</span>`;
    const change=lake.area_change_pct;
    const delta=$('chart-delta');delta.className='chart-delta'+(Number.isFinite(change)&&change<0?' negative':'');
    delta.textContent=Number.isFinite(change)?`${change>0?'+':''}${change.toFixed(1)}% area change`:'Change unavailable';
    const history=(lake.history||[]).filter(h=>Number.isFinite(h.area_km2)&&h.date&& !Number.isNaN(Date.parse(h.date))).sort((a,b)=>a.date.localeCompare(b.date));
    const series=history.slice(-(state.days+1));
    if(series.length<2){empty.hidden=false;svg.setAttribute('aria-label','No time series data available');return;}
    empty.hidden=true;
    const W=720,H=235,L=50,R=13,T=14,B=32,w=W-L-R,h=H-T-B;
    let min=Math.min(...series.map(d=>d.area_km2)),max=Math.max(...series.map(d=>d.area_km2));
    const pad=Math.max(.02,(max-min)*.22);min=Math.max(0,min-pad);max=max+pad;
    const x=i=>L+(i/(series.length-1))*w;
    const y=v=>T+(max-v)/(max-min)*h;
    const grid=appendSvg(svg,'g');
    for(let i=0;i<4;i++){
      const yy=T+(i/3)*h;
      appendSvg(grid,'line',{x1:L,y1:yy,x2:W-R,y2:yy,stroke:'#e9eff0','stroke-dasharray':'4 5'});
      appendSvg(grid,'text',{x:L-9,y:yy+3,'text-anchor':'end',fill:'#a1aeb4','font-size':10,'font-family':'DM Sans, sans-serif'},(max-i/3*(max-min)).toFixed(2));
    }
    for(let i=0;i<5;i++){
      const idx=Math.round(i*(series.length-1)/4),date=series[idx].date;
      const label=new Date(`${date}T12:00:00Z`).toLocaleDateString('en-IN',{day:'numeric',month:'short'});
      appendSvg(grid,'text',{x:x(idx),y:H-9,'text-anchor':i===0?'start':i===4?'end':'middle',fill:'#99a7af','font-size':10,'font-family':'DM Sans, sans-serif'},label);
    }
    const defs=appendSvg(svg,'defs');const gradient=appendSvg(defs,'linearGradient',{id:'areaFill',x1:0,y1:0,x2:0,y2:1});
    appendSvg(gradient,'stop',{offset:'0%','stop-color':'#22a9a0','stop-opacity':'.22'});
    appendSvg(gradient,'stop',{offset:'100%','stop-color':'#22a9a0','stop-opacity':'0'});
    const path=series.map((d,i)=>`${i===0?'M':'L'}${x(i).toFixed(2)} ${y(d.area_km2).toFixed(2)}`).join(' ');
    const bottom=T+h;
    appendSvg(svg,'path',{d:`${path} L ${x(series.length-1)} ${bottom} L ${x(0)} ${bottom} Z`,fill:'url(#areaFill)'});
    appendSvg(svg,'path',{d:path,fill:'none',stroke:'#17a89f','stroke-width':2.7,'stroke-linejoin':'round','stroke-linecap':'round'});
    appendSvg(svg,'circle',{cx:x(series.length-1),cy:y(series[series.length-1].area_km2),r:5.4,fill:'#fff',stroke:'#15a79c','stroke-width':2.8});
    const hoverLine=appendSvg(svg,'line',{x1:L,y1:T,x2:L,y2:bottom,stroke:'#8caead','stroke-dasharray':'3 5',visibility:'hidden'});
    const hoverCircle=appendSvg(svg,'circle',{cx:L,cy:T,r:5,fill:'#fff',stroke:'#0c9e94','stroke-width':2.5,visibility:'hidden'});
    const hitArea=appendSvg(svg,'rect',{x:L,y:T,width:w,height:h,fill:'transparent',style:'cursor:crosshair'});
    const tooltip=$('chart-tooltip');
    hitArea.addEventListener('pointermove',(event)=>{
      const pt=svg.createSVGPoint();pt.x=event.clientX;pt.y=event.clientY;
      const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return;
      const cursor=pt.matrixTransform(inverse);const index=Math.max(0,Math.min(series.length-1,Math.round((cursor.x-L)/w*(series.length-1))));
      const value=series[index],xx=x(index),yy=y(value.area_km2);
      hoverLine.setAttribute('x1',xx);hoverLine.setAttribute('x2',xx);hoverLine.setAttribute('visibility','visible');
      hoverCircle.setAttribute('cx',xx);hoverCircle.setAttribute('cy',yy);hoverCircle.setAttribute('visibility','visible');
      tooltip.replaceChildren();
      const label=document.createElement('div');label.textContent=dateLabel(value.date);
      const strong=document.createElement('strong');strong.textContent=`${value.area_km2.toFixed(3)} km²`;
      tooltip.append(label,strong);tooltip.hidden=false;
      const localX=xx/W*svg.getBoundingClientRect().width;
      tooltip.style.left=`${Math.min(Math.max(10,localX-45),Math.max(10,svg.clientWidth-115))}px`;
      tooltip.style.top=`${Math.max(0,yy/H*svg.getBoundingClientRect().height-52)}px`;
    });
    hitArea.addEventListener('pointerleave',()=>{hoverLine.setAttribute('visibility','hidden');hoverCircle.setAttribute('visibility','hidden');tooltip.hidden=true;});
    svg.setAttribute('aria-label',`${lake.name} lake area trend over ${state.days} days`);
  }
  function geoLakes(){return state.lakes.filter(l=>Number.isFinite(l.lat)&&Number.isFinite(l.lon)&&Math.abs(l.lat)<=90&&Math.abs(l.lon)<=180);}
  function renderFallbackPins(){
    const box=$('fallback-pins');box.replaceChildren();
    for(const lake of geoLakes()){
      const b=document.createElement('button');b.type='button';b.className=`fallback-pin ${lake.risk}${lake.lake_id===state.selectedId?' is-selected':''}`;
      // Synthetic regional projection only; fallback illustration is not a real map.
      b.style.left=`${Math.max(4,Math.min(96,(lake.lon-71)/(96-71)*100))}%`;
      b.style.top=`${Math.max(9,Math.min(92,(36.5-lake.lat)/(36.5-26)*100))}%`;
      b.title=`${lake.name} · ${riskText(lake.risk)} (demo locator)`;b.setAttribute('aria-label',b.title);
      b.addEventListener('click',()=>selectLake(lake.lake_id));
      box.append(b);
    }
  }
  function highlightMap(){
    renderFallbackPins();
    if(!state.map)return;
    for(const [id,marker] of state.markers){const l=state.lakes.find(x=>x.lake_id===id);if(!l)continue;marker.setStyle({radius:state.selectedId===id?10:7,weight:state.selectedId===id?3:2,color:'#fff',fillColor:riskColor(l.risk),fillOpacity:1});}
  }
  function updateMapViewControls(message){
    for(const button of document.querySelectorAll('[data-map-view]')){
      button.disabled=!state.map;
      button.setAttribute('aria-pressed',String(button.dataset.mapView===state.mapView));
    }
    $('map-view-status').textContent=message || (state.map
      ? (state.mapView==='satellite'?'Satellite basemap · imagery dates vary':'Regular street map')
      : 'Map views require internet access and lake coordinates.');
  }
  function setMapView(view){
    if(!state.map || !state.baseLayers || !['regular','satellite'].includes(view))return;
    const next=state.baseLayers[view];
    for(const layer of Object.values(state.baseLayers)){
      if(layer!==next && state.map.hasLayer(layer))state.map.removeLayer(layer);
    }
    state.mapView=view;state.tileErrorShown=false;
    if(!state.map.hasLayer(next))next.addTo(state.map);
    try {localStorage.setItem('glofwatch-map-view',view);} catch { /* Switching still works. */ }
    updateMapViewControls();
  }
  function removeMap(){
    if(state.map){state.map.remove();state.map=null;}
    state.baseLayers=null;state.markers.clear();$('map-fallback').style.display='block';
    updateMapViewControls();
  }
  function renderLeafletMap(){
    if(!window.L || state.map || !geoLakes().length)return;
    const map=window.L.map('map-canvas',{zoomControl:false,scrollWheelZoom:false,attributionControl:true}).setView([30.1,83.3],5);
    state.map=map;
    state.baseLayers={
      regular:window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
        maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }),
      satellite:window.L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{
        maxZoom:18,attribution:'Tiles &copy; Esri &mdash; Sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community &middot; <a href="https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9">Imagery credits</a>'
      })
    };
    for(const [view,layer] of Object.entries(state.baseLayers))layer.on('tileerror',()=>{
      if(state.mapView!==view || state.tileErrorShown)return;
      state.tileErrorShown=true;
      updateMapViewControls('Some map tiles could not load. Check your connection or switch views.');
    });
    setMapView(state.mapView);$('map-fallback').style.display='none';
    for(const lake of geoLakes()){
      const marker=window.L.circleMarker([lake.lat,lake.lon],{radius:7,weight:2,color:'#fff',fillColor:riskColor(lake.risk),fillOpacity:1}).addTo(map);
      marker.on('click',()=>selectLake(lake.lake_id));
      const popup=document.createElement('div');popup.className='lake-popup';
      const name=document.createElement('strong');name.textContent=lake.name;const details=document.createElement('small');details.textContent=`${lake.region||'Unknown'} · ${riskText(lake.risk)}`;
      const inspect=document.createElement('button');inspect.textContent='Inspect lake';inspect.addEventListener('click',()=>selectLake(lake.lake_id,{scroll:true}));
      popup.append(name,details,inspect);marker.bindPopup(popup);
      state.markers.set(lake.lake_id,marker);
    }
    const bounds=window.L.latLngBounds(geoLakes().map(l=>[l.lat,l.lon]));map.fitBounds(bounds.pad(.16),{maxZoom:6});highlightMap();
    setTimeout(()=>map.invalidateSize(),150);
  }
  function loadLeaflet(){
    if(state.leafletLoading||window.L||!geoLakes().length){renderLeafletMap();return;}
    state.leafletLoading=true;
    const stylesheet=document.createElement('link');stylesheet.rel='stylesheet';stylesheet.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';document.head.append(stylesheet);
    const script=document.createElement('script');script.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';script.async=true;
    script.onload=()=>{state.leafletLoading=false;renderLeafletMap();};
    script.onerror=()=>{state.leafletLoading=false;updateMapViewControls();/* keep schematic fallback */};
    document.head.append(script);
  }
  function renderAll(){renderMetrics();renderWatchList();renderTable();renderDetails();renderChart();removeMap();renderFallbackPins();loadLeaflet();}
  function parseNumber(...values){
    for(const val of values){if(val!==null&&val!==undefined&&val!==''&&Number.isFinite(Number(val)))return Number(val);}
    return null;
  }
  function parseRisk(raw,score){
    const v=String(raw??'').toLowerCase().replace(/[_\s-]+/g,' ').trim();
    if(['high','critical','elevated','severe','red','danger'].some(x=>v===x||v.startsWith(`${x} `)))return 'high';
    if(['watch','medium','moderate','yellow','amber'].some(x=>v===x||v.startsWith(`${x} `)))return 'watch';
    if(['low','normal','stable','green','safe'].some(x=>v===x||v.startsWith(`${x} `)))return 'low';
    if(Number.isFinite(score))return score>=70?'high':score>=40?'watch':'low';
    return 'unknown';
  }
  function normalizeLake(row,index){
    let metrics=row.metrics??row.metrics_json??{};
    if(typeof metrics==='string'){try{metrics=JSON.parse(metrics);}catch{metrics={};}}
    if(!metrics||typeof metrics!=='object')metrics={};
    const score=parseNumber(row.score,row.risk_score,metrics.risk_score);
    const area=parseNumber(row.area_km2,row.lake_area_km2,metrics.area_km2,metrics.lake_area_km2);
    const change=parseNumber(row.area_change_pct,row.change_pct,metrics.area_change_pct,metrics.change_pct);
    const lat=parseNumber(row.lat,row.latitude,metrics.lat,metrics.latitude);
    const lon=parseNumber(row.lon,row.lng,row.longitude,metrics.lon,metrics.longitude);
    const rawHistory=row.history??metrics.history??[];
    const history=Array.isArray(rawHistory)?rawHistory.map(h=>({date:String(h.date??h.assessed_at??''),area_km2:parseNumber(h.area_km2,h.area,h.value)})).filter(h=>h.date&&Number.isFinite(h.area_km2)):[];
    return {
      lake_id:String(row.lake_id??row.id??`lake-${index+1}`),
      name:String(row.name??row.lake_name??row.lake_id??`Lake ${index+1}`),
      region:String(row.region??metrics.region??''),lat,lon,
      score:score===null?null:Math.max(0,Math.min(100,score)),
      risk:parseRisk(row.risk??row.risk_level??row.level,score),
      area_km2:area,area_change_pct:change,
      assessed_at:String(row.assessed_at??row.observed_at??row.timestamp??''),
      history,demo:false
    };
  }
  async function loadApiData(){
    const url=String(window.GLOF_API_URL||'').trim().replace(/\/$/,'');
    if(!url){state.lakes=DEMO_LAKES;state.selectedId=DEMO_LAKES[0].lake_id;setMode('demo');renderAll();return;}
    const button=$('refresh-button');button.disabled=true;button.textContent='Refreshing…';
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),11000);
    try{
      const endpoint=url.endsWith('/lakes/latest')?url:`${url}/lakes/latest`;
      const response=await fetch(endpoint,{headers:{Accept:'application/json'},signal:controller.signal});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const body=await response.json();const entries=Array.isArray(body)?body:body.lakes??body.results??body.items;
      if(!Array.isArray(entries))throw new Error('Expected an array or { lakes: [...] }');
      if(entries.length===0)throw new Error('No lake assessments returned');
      state.lakes=entries.map(normalizeLake);state.selectedId=state.lakes[0].lake_id;setMode('live');renderAll();showToast(`Loaded ${state.lakes.length} observations from AWS API.`);
    }catch(error){
      const message=error.name==='AbortError'?'request timed out':error.message;
      state.lakes=DEMO_LAKES;state.selectedId=DEMO_LAKES[0].lake_id;setMode('error',message);renderAll();showToast('API data unavailable — showing clearly labeled demonstration data.');
    }finally{clearTimeout(timer);button.disabled=false;button.innerHTML=`${icon('refresh')} Refresh`;}
  }
  function csvEscape(input){let value=String(input??'');if(typeof input==='string' && (/^[=+@]/.test(value)||(/^-(?![0-9.])/.test(value))))value=`'${value}`;return `"${value.replace(/"/g,'""')}"`;}
  function exportCsv(){
    const header=['lake_id','name','region','latitude','longitude','risk_level','risk_score','area_km2','area_change_pct','assessed_at','data_mode'];
    const rows=state.lakes.map(l=>[l.lake_id,l.name,l.region,l.lat??'',l.lon??'',l.risk,l.score??'',l.area_km2??'',l.area_change_pct??'',l.assessed_at,state.mode==='live'?'api':'simulated']);
    const csv=[header,...rows].map(row=>row.map(csvEscape).join(',')).join('\r\n');
    const blob=new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8;'});const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=`glofwatch-${state.mode==='live'?'api':'demo'}-${new Date().toISOString().slice(0,10)}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    showToast(`Exported ${rows.length} ${state.mode==='live'?'API':'simulated'} records as CSV.`);
  }

  for(const button of document.querySelectorAll('.nav-link[data-target]'))button.addEventListener('click',()=>{
    document.querySelectorAll('.nav-link').forEach(b=>b.classList.remove('active'));button.classList.add('active');
    $('breadcrumb').textContent=button.textContent.trim();$(button.dataset.target)?.scrollIntoView({behavior:'smooth',block:'start'});
    $('sidebar').classList.remove('open');
  });
  $('menu-button').addEventListener('click',()=>$('sidebar').classList.toggle('open'));
  $('refresh-button').addEventListener('click',()=>{if(!window.GLOF_API_URL)showToast('Demo mode: set window.GLOF_API_URL in config.js to connect AWS.');loadApiData();});
  $('export-button').addEventListener('click',exportCsv);
  $('lake-search').addEventListener('input',e=>{state.search=e.target.value;renderTable();});
  $('risk-filter').addEventListener('change',e=>{state.risk=e.target.value;renderTable();});
  for(const button of document.querySelectorAll('[data-days]'))button.addEventListener('click',()=>{
    state.days=Number(button.dataset.days);document.querySelectorAll('[data-days]').forEach(b=>b.classList.toggle('selected',b===button));renderChart();
  });
  $('show-all-map').addEventListener('click',()=>{if(state.map){const lakes=geoLakes();if(lakes.length)state.map.fitBounds(window.L.latLngBounds(lakes.map(l=>[l.lat,l.lon])).pad(.16),{maxZoom:6});}else{$('fallback-pins').style.transform='scale(1)';state.fallbackZoom=1;}showToast(`${geoLakes().length} lake positions available in the current dataset.`);});
  for(const button of document.querySelectorAll('[data-map-view]'))button.addEventListener('click',()=>setMapView(button.dataset.mapView));
  $('zoom-in').addEventListener('click',()=>{if(state.map)state.map.zoomIn();else{state.fallbackZoom=Math.min(2.2,state.fallbackZoom+.2);$('fallback-pins').style.transform=`scale(${state.fallbackZoom})`;}});
  $('zoom-out').addEventListener('click',()=>{if(state.map)state.map.zoomOut();else{state.fallbackZoom=Math.max(1,state.fallbackZoom-.2);$('fallback-pins').style.transform=`scale(${state.fallbackZoom})`;}});

  const initialTarget = document.querySelector('.nav-link[data-target="' + location.hash.slice(1).replace(/[^a-z-]/g, '') + '"]');
  if (initialTarget) initialTarget.click();
  setMode('demo');renderAll();loadApiData();
})();
