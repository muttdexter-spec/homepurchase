// First House crawler v3 — one file, two stages, no photo work in stage 1.
// Paste whole file into javascript_tool once per listing. Then call the stage fns.

// ---------- STAGE 1: data only. No gallery click. ~600 tokens out. ----------
window.__data = async () => {
  const T = e => e ? e.textContent.replace(/\s+/g,' ').trim() : null;
  const rm = [...document.querySelectorAll('button,a,span,div')]
    .filter(e => e.offsetParent && e.innerText && /^Read More$/i.test(e.innerText.trim()))
    .sort((a,b)=>a.innerText.length-b.innerText.length)[0];
  if (rm) { rm.click(); await new Promise(r=>setTimeout(r,1200)); }
  const txt = document.body.innerText, F = {};
  document.querySelectorAll('dl.property-details').forEach(dl=>{
    const dt=[...dl.querySelectorAll('dt')], dd=[...dl.querySelectorAll('dd')];
    dt.forEach((d,k)=>{ if(dd[k]) F[d.textContent.replace(/:$/,'').trim()]=T(dd[k]); });});
  const rooms=[]; let lvl=null;
  document.querySelectorAll('.level-heading, .room-row').forEach(el=>{
    if(el.classList.contains('level-heading')){lvl=T(el);return;}
    const c=[...el.children], name=T(c[0]); if(!name||name==='Room Type')return;
    const d=el.textContent.match(/([\d.]+)\s*x\s*([\d.]+)\s*ft/);
    const sq=d?Math.round(d[1]*d[2]):null;
    rooms.push({lvl,name,sqft:(sq&&sq<1200)?sq:null});});
  const bed=rooms.filter(r=>/bed/i.test(r.name)&&r.sqft&&!/base|lower/i.test(r.lvl||''));
  const N=s=>{const m=(F[s]||'').match(/[\d.]+/);return m?+m[0]:null;};
  // return ONLY what the model consumes. Everything else stays in the browser.
  return {
    listing_id:(location.pathname.match(/property\/([^?]+)/)||[])[1],
    address:(document.querySelector('h1')||{}).textContent||null,
    mls:(txt.match(/MLS[®\s#]*([A-Z0-9]+)/)||[])[1]||null,
    list_price:+((txt.match(/\$[\d,]{7,}/)||[''])[0].replace(/[$,]/g,''))||null,
    dom:+((txt.match(/Days on OneHome\s*(\d+)/)||[])[1]||0)||null,
    year_built:N('Year Built'), style:F['Style']||F['Property Style']||null,
    sqft_above:N('Square Footage')||N('Above Grade Finished Area'),
    sqft_below:N('Below Grade Finished Area'),
    beds_ag:N('Bedrooms Above Grade'), beds_bg:N('Bedrooms Below Grade'),
    baths_full:N('Full Bathrooms'), baths_half:N('Half Bathrooms'),
    lot_frontage_ft:N('Frontage'), lot_depth_ft:N('Depth'),
    annual_taxes:N('Annual Tax Amount'), neighbourhood:F['Neighbourhood']||F['Community']||null,
    municipality:F['City']||F['Municipality']||null, basement:F['Basement']||null,
    heating:F['Heating']||null, garage_spaces:N('Garage Spaces'), parking_spots:N('Parking Spaces'),
    primary_bed_sqft:bed.length?Math.max(...bed.map(b=>b.sqft)):null,
    beds_under_100sqft:bed.filter(b=>b.sqft<100).length,
    walk:+((txt.match(/Walk\s+(\d+)\/100/)||[])[1]||0)||null,
    transit:+((txt.match(/Transit\s+(\d+)\/100/)||[])[1]||0)||null,
    nearest_school_km:Math.min(...[...txt.matchAll(/Distance:([\d.]+) km/g)].map(m=>+m[1]),99),
    mech_ages_stated:(txt.match(/\b(roof|furnace|A\/?C|windows?|水)\b[^.]{0,40}?\b(19|20)\d{2}\b/gi)||[]).join('; ')||null,
    room_dims_present:rooms.some(r=>r.sqft)
  };
};

// ---------- STAGE 2: photos. Only run on listings that pass the gate. ----------
window.__photos_load = async () => {
  const dec=t=>{try{return JSON.parse(atob(t.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));}catch(e){return null;}};
  const f=[...document.querySelectorAll('img')].find(i=>/GetMedia\.ashx/.test(i.src||''));
  f.scrollIntoView({block:'center'}); await new Promise(r=>setTimeout(r,1500));
  f.click(); await new Promise(r=>setTimeout(r,6000));
  const m=new Map();
  [...document.querySelectorAll('img')].map(i=>i.src).filter(s=>/GetMedia\.ashx/.test(s))
    .forEach(s=>{const p=dec(new URL(s).searchParams.get('t')); if(p&&p.Size==='3') m.set(+p.Number,s);});
  window.__P=[...m.entries()].sort((a,b)=>a[0]-b[0]).map(e=>e[1]);
  // RESOLUTION PROBE. If naturalWidth > ~800, rendering the photo at 496 CSS px
  // is a DOWNSCALE and you are not looking at full resolution.
  const probe=new Image(); probe.src=window.__P[0];
  await new Promise(r=>{probe.onload=r; probe.onerror=r;});
  return {total:window.__P.length, natural_w:probe.naturalWidth, natural_h:probe.naturalHeight,
          note: probe.naturalWidth>800 ? 'SOURCE EXCEEDS VIEWPORT — use __tell(), not full-frame' : 'full-frame ok'};
};

// ONE contact sheet, everything, one screenshot. 6 across fits 496px viewport.
window.__sheet = (w=78) => {
  document.body.innerHTML='<div id=g style="display:flex;flex-wrap:wrap;gap:1px;background:#222"></div>';
  const g=document.getElementById('g');
  window.__P.forEach((u,k)=>g.insertAdjacentHTML('beforeend',
    `<div style="position:relative"><img src="${u}" style="width:${w}px;display:block">`+
    `<span style="position:absolute;top:0;left:0;background:#000;color:#0f0;font:9px monospace">${k}</span></div>`));
  scrollTo(0,0); return window.__P.length;
};

// TELL SHEET: up to 4 magnified crops in ONE screenshot, at or above 1:1.
// specs = [[photoIdx, xPct, yPct, zoom, label], ...]   xPct/yPct = centre of interest
window.__tell = (specs) => {
  document.body.innerHTML='<div id=g style="display:flex;flex-wrap:wrap;gap:4px;background:#111"></div>';
  const g=document.getElementById('g');
  specs.forEach(([i,x,y,z,lab])=>{
    const id='c'+i+'_'+x+'_'+y;
    g.insertAdjacentHTML('beforeend',
      `<div style="position:relative;width:240px;height:200px;overflow:hidden;background:#000">
       <img id="${id}" src="${window.__P[i]}" style="position:absolute">
       <span style="position:absolute;bottom:0;left:0;background:#000;color:#0f0;font:10px monospace">${i} ${lab||''}</span></div>`);
    const im=document.getElementById(id);
    im.onload=()=>{const W=im.naturalWidth*(z||1);
      im.style.width=W+'px';
      im.style.left=(120-W*x/100)+'px';
      im.style.top=(100-im.naturalHeight*(z||1)*y/100)+'px';};
  });
  scrollTo(0,0); return specs.length;
};
