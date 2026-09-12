// __data() with the v3 field-name and number-parsing bugs fixed.
// See crawl-fixes.md. Paste, then: 
await new Promise(r=>setTimeout(r,5500));
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
    rooms.push({lvl,name,sqft:(sq&&sq<1200)?sq:null,txt:T(el).slice(0,140)});});
  const bed=rooms.filter(r=>/bed/i.test(r.name)&&r.sqft&&!/base|lower/i.test(r.lvl||''));
  // FIX 1: strip thousands separators before parsing, or "$5,411" reads as 5.
  // FIX 2: accept a LIST of candidate field names; the two boards disagree.
  const N=(...keys)=>{ for(const s of keys){ const v=F[s]; if(!v) continue;
      const m=v.replace(/,/g,'').match(/[\d.]+/); if(m) return +m[0]; } return null; };
  const S=(...keys)=>{ for(const s of keys){ if(F[s]) return F[s]; } return null; };
  // FIX 3: lot comes as "40 x 110" in one field, not as Frontage/Depth.
  let lf=N('Frontage'), ld=N('Depth');
  const ld_raw=S('Lot Size Dimensions');
  if((!lf||!ld) && ld_raw){ const m=ld_raw.replace(/,/g,'').match(/([\d.]+)\s*[xX]\s*([\d.]+)/);
    if(m){ lf=+m[1]; ld=+m[2]; } }
  // FIX 4: beds. Prefer the explicit above/below split, fall back to "Beds" ("3+1").
  let bag=N('Above Grade Bedrooms','Bedrooms Above Grade'), bbg=N('Below Grade Bedrooms','Bedrooms Below Grade');
  const braw=S('Beds');
  if(bag==null && braw){ const m=braw.match(/(\d+)(?:\s*\+\s*(\d+))?/); if(m){ bag=+m[1]; if(bbg==null) bbg=m[2]?+m[2]:0; } }
  // FIX 5: garage. Absent field does not mean zero; "Garage" in the features string does.
  let gar=N('Garage Spaces');
  if(gar==null) gar=/garage/i.test(S('Garage/Parking Features','Garage Parking Features')||'')?1:0;
  return {
    listing_id:(location.pathname.match(/property\/([^?]+)/)||[])[1],
    // FIX 6: h1 is not the address on these pages.
    address:(txt.match(/\n([^\n]*,\s*(?:Burlington|Oakville|Hamilton|Milton),\s*ON\s*[A-Z0-9]{3} ?[A-Z0-9]{3})/)||[])[1]||null,
    mls:(txt.match(/MLS[®\s#]*([A-Z0-9]+)/)||[])[1]||null,
    list_price:+((txt.match(/\$[\d,]{7,}/)||[''])[0].replace(/[$,]/g,''))||null,
    dom:+((txt.match(/Days on OneHome\s*(\d+)/)||[])[1]||0)||null,
    year_built:N('Year Built'), year_built_details:S('Year Built Details'),
    style:S('Style','Property Style','Architectural Style'),
    sqft_above:N('Above Grade Finished Area','Square Footage','Size'),
    sqft_below:N('Below Grade Finished Area'),
    beds_ag:bag, beds_bg:bbg,
    baths_full:N('Full Bathrooms'), baths_half:N('Half Bathrooms'),
    lot_frontage_ft:lf, lot_depth_ft:ld,
    annual_taxes:N('Annual Taxes','Annual Tax Amount'),
    neighbourhood:(S('Neighbourhood','Community')||'').replace(/^\d+\s*-\s*/,'')||null,
    municipality:(S('Municipality','City','Postal City')||'').replace(/^\d+\s*-\s*/,'')||null,
    basement:S('Basement'), heating:S('Heating'), cooling:S('Cooling'),
    roof_material:S('Roof'), foundation:S('Foundation Details'),
    garage_spaces:gar, parking_spots:N('Parking Spots','Parking Spaces'),
    primary_bed_sqft:bed.length?Math.max(...bed.map(b=>b.sqft)):null,
    beds_under_100sqft:bed.filter(b=>b.sqft<100).length,
    walk:+((txt.match(/Walk\s+(\d+)\/100/)||[])[1]||0)||null,
    transit:+((txt.match(/Transit\s+(\d+)\/100/)||[])[1]||0)||null,
    nearest_school_km:Math.min(...[...txt.matchAll(/Distance:([\d.]+) km/g)].map(m=>+m[1]),99),
    mech_ages_stated:(txt.match(/\b(roof|furnace|A\/?C|windows?)\b[^.]{0,40}?\b(19|20)\d{2}\b/gi)||[]).join('; ')||null,
        remarks:(T(document.querySelector('.overview-container'))||'').slice(0,1800),
    fields_keep:{zoning:S('Zoning Details'),faces:S('Direction Faces'),construction:S('Construction Materials'),storeys:S('Storeys'),size_range:S('Size'),inclusions:(S('Inclusions')||'').slice(0,200),badge:(txt.match(/(New Listing|Back on Market|Price Decrease|Price Increase|Sold Conditional)/)||[])[1]||null}, rooms_raw:rooms.map(r=>[r.lvl,r.name,r.sqft,r.txt.replace(/^[^\d]+[\d.]+x[\d.]+ ft/,'').split(' ft')[0].slice(0,50)]),
    photo_count_text:+((txt.match(/View All (\d+) Photos/i)||[])[1]||0)||null,
    virtual_staging_lang:/virtual(ly)? staged|virtual staging|digitally (staged|enhanced)/i.test(txt),
    room_dims_present:rooms.some(r=>r.sqft)
  };
};


JSON.stringify(await window.__data())