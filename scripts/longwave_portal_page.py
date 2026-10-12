"""Additions to the page of the portal for the set of long-wave scenarios.

The page of the Stagnone portal shows one model run. For the set of scenarios
it gains four elements, added around its markup and after its script without
change to either:

- a title over the map naming the scenario shown;
- a vertical bar at the right edge of the map, with a README button and one
  button for each direction of arrival, which opens the page of that scenario
  at the same view and time;
- a panel at the right, a quarter of the window wide, with the description of
  the scenarios, opened by the README button;
- markers at the stations whose records are plotted, a click on a marker
  bringing the plot of that station into view in the panel at the left.

`extend` takes the page, the description of the set written by
build_longwave_portal_set.py and the scenario of the page, and returns the page
with the additions.
"""

from __future__ import annotations

import json

ABBR = {0: "S", 45: "SW", 90: "W", 135: "NW", 180: "N", 225: "NE", 270: "E", 315: "SE"}
FROM = {0: "south", 45: "southwest", 90: "west", 135: "northwest", 180: "north",
        225: "northeast", 270: "east", 315: "southeast"}

STYLE = """<style>
#scn-title{position:absolute;left:58px;top:10px;z-index:1000;max-width:62%;
  background:rgba(13,17,23,.84);border:1px solid var(--line);border-radius:8px;
  padding:8px 13px;pointer-events:none}
#scn-title .t1{font-size:15.5px;font-weight:650;color:#e6edf3;letter-spacing:.1px}
#scn-title .t2{font-size:11.5px;color:#9aa7b4;margin-top:2px}
#scn-bar{position:absolute;right:10px;top:50%;transform:translateY(-50%);z-index:1000;
  display:flex;flex-direction:column;gap:6px;align-items:stretch}
#scn-bar button{font:600 12px system-ui,Segoe UI,Roboto,sans-serif;cursor:pointer;
  border-radius:7px;border:1px solid #30363d;background:rgba(13,17,23,.86);color:#c9d4df;
  padding:7px 0;width:62px}
#scn-bar button:hover{border-color:#58c8d9;color:#e6edf3}
#scn-bar button.cur{background:#e8a860;border-color:#e8a860;color:#0d1117}
#scn-bar #readme-btn{background:#58c8d9;border-color:#58c8d9;color:#0d1117;
  letter-spacing:.6px;margin-bottom:8px;padding:9px 0}
#scn-bar #readme-btn.on{background:#e6edf3;border-color:#e6edf3}
#scn-bar .lab{font:500 9.5px system-ui,sans-serif;color:#9aa7b4;text-align:center;
  text-transform:uppercase;letter-spacing:.5px;background:rgba(13,17,23,.7);border-radius:4px;
  padding:2px 0}
#readme{width:25vw;min-width:310px;flex:none;display:none;overflow-y:auto;
  background:var(--panel);border-left:1px solid var(--line);padding:16px 18px 30px;
  font-size:12.5px;line-height:1.55}
#readme h2{font-size:15px;margin:0 0 4px}
#readme h3{font-size:12.5px;margin:18px 0 6px;color:var(--accent);font-weight:600}
#readme p{margin:0 0 9px}
#readme ul{margin:0 0 9px 16px;padding:0}
#readme li{margin-bottom:5px}
#readme .sub{color:var(--ink2);font-size:11.5px;margin-bottom:6px}
#readme table{border-collapse:collapse;width:100%;font-size:11.5px}
#readme th,#readme td{padding:5px 6px;border-bottom:1px solid var(--line);text-align:right}
#readme th:first-child,#readme td:first-child{text-align:left}
#readme th{color:var(--ink2);font-weight:500}
#readme a{color:var(--accent);text-decoration:none;font-weight:600}
#readme .note{color:var(--ink2);font-size:11.5px}
#readme .x{float:right;border:1px solid var(--line);background:none;color:var(--ink2);
  border-radius:6px;font-size:10.5px;padding:3px 9px;cursor:pointer}
.sc.flash{outline:2px solid #ffd166;outline-offset:2px;border-radius:6px}
</style>
"""

MAP_OLD = """    <div id="map-wrap"><div id="map"></div>
      <div id="vel-readout" style="display:none"></div>
    </div>
  </div>
  <div id="tbar">"""

MAP_NEW = """    <div id="map-wrap"><div id="map"></div>
      <div id="vel-readout" style="display:none"></div>
      <div id="scn-title"><div class="t1">__T1__</div><div class="t2">__T2__</div></div>
      <div id="scn-bar"></div>
    </div>
    <div id="readme"><button class="x" onclick="toggleReadme()">close</button>__README__</div>
  </div>
  <div id="tbar">"""

SCRIPT = """
<script>
const SCN=__SET__, SCN_CASE='__CASE__';
function scnHash(){
  if(!map)return '';
  const c=map.getCenter();
  return '#'+map.getZoom().toFixed(2)+'/'+c.lat.toFixed(5)+'/'+c.lng.toFixed(5)+'/'+currentT;
}
function scnGo(c){
  if(c===SCN_CASE)return;
  location.href='../'+c+'/index.html'+scnHash();
}
function toggleReadme(){
  const r=document.getElementById('readme');
  const on=r.style.display!=='block';
  r.style.display=on?'block':'none';
  document.getElementById('readme-btn').classList.toggle('on',on);
  if(map)setTimeout(()=>map.invalidateSize(),60);
}
(function(){
  let h='<button id="readme-btn" onclick="toggleReadme()">README</button>'
       +'<div class="lab">arrives from</div>';
  SCN.forEach(s=>{
    h+='<button class="'+(s.case===SCN_CASE?'cur':'')+'" onclick="scnGo(\\''+s.case+'\\')" '
      +'title="arriving from the '+s.from+', '+s.kmh+' km/h">'+s.abbr+'</button>';
  });
  document.getElementById('scn-bar').innerHTML=h;
})();
function staFocus(n){
  const sec=document.getElementById('sta-sec');
  if(!staBuilt)toggleSta(); else sec.style.display='';
  const el=document.getElementById('sp-'+n);
  if(!el)return;
  const card=el.parentElement;
  card.scrollIntoView({behavior:'smooth',block:'center'});
  card.classList.add('flash');
  setTimeout(()=>card.classList.remove('flash'),1800);
}
const scnWait=setInterval(()=>{
  if(!map||!META||!LAYERS)return;
  clearInterval(scnWait);
  map.createPane('staPane');
  map.getPane('staPane').style.zIndex=470;
  const ren=L.svg({pane:'staPane'});
  Object.keys(META.sta_info).forEach(n=>{
    const s=META.sta_info[n];
    L.circleMarker([s.lat,s.lon],{renderer:ren,pane:'staPane',radius:6,color:'#0d1117',
                                  weight:2,fillColor:'#ffd166',fillOpacity:1})
      .addTo(map).bindTooltip(n,{direction:'top',offset:[0,-6]})
      .on('click',()=>staFocus(n));
  });
  const m=location.hash.slice(1).split('/').map(Number);
  if(m.length===4&&m.every(isFinite)){
    map.setView([m[1],m[2]],m[0],{animate:false});
    const t=Math.min(Math.max(0,Math.round(m[3])),TIMES.length-1);
    document.getElementById('tslider').value=t;
    seek(t);
  }
},200);
</script>
"""

README = """<h2>Response of the Valletta harbours to moving pressure disturbances</h2>
<div class="sub">Eight scenarios of a numerical sweep, one for each direction of arrival.
Oceanography Malta Research Group, University of Malta, with the Universit&agrave; degli Studi
di Palermo. Interreg VI-A Italia-Malta WETWISE.</div>

<h3>Place of the scenarios in the study</h3>
<p>The study addresses the circulation and the renewal of the water of the Grand Harbour and
Marsamxett with a coupled wave and hydrodynamic model in Delft3D FM. One of its components
concerns the <em>mil&#289;&#295;uba</em>, the long wave raised by an atmospheric pressure
disturbance travelling over the sea, a meteotsunami, which floods the low ground at the head of
Msida Creek.</p>
<p>The scenarios shown here belong to that component. Each is an idealised experiment and
reproduces no particular event. A pressure rise of 2 hPa, 15 km long and 50 km wide, crosses the
Sicily Channel on a straight track of 400 km through the harbours at constant speed, and the
model computes the response of the sea in two dimensions over a domain of 419 by 361 km, with
cells of 15 m inside the harbours. A sweep of 96 such scenarios, over six speeds, eight
directions and two lengths, gives the response of the harbours as a function of the disturbance.
The eight maps are the scenarios of largest response for each direction.</p>

<h3>Reading the map</h3>
<ul>
<li>The buttons at the right edge of the map change the direction from which the disturbance
arrives. The view and the time are kept.</li>
<li>The water level is in centimetres and the currents in metres per second, both for the rise
of 2 hPa. The response is proportional to the rise within 2 per cent up to 10 hPa.</li>
<li>Zooming into the harbours brings in a finer grid. The time shown is the time elapsed from the
start, the disturbance passing over the harbours near the middle of its track.</li>
<li>The yellow points are the stations whose records are plotted. A click on a point brings its
plot into view in the panel at the left.</li>
</ul>

<h3>Scenarios</h3>
<table>
<tr><th>Arrives from</th><th>km/h</th><th>Senglea</th><th>Marsa</th><th>Msida</th></tr>
__ROWS__
</table>
<p class="note" style="margin-top:8px">The last three columns give the amplification, the largest
departure of the level from rest divided by the 1.99 cm that the same pressure rise would produce
if it stood still. At Marsa, the head of the Grand Harbour, the largest value corresponds to
__MARSA_CM__ cm for 2 hPa.</p>

<h3>Standing of the results</h3>
<p>The results are preliminary. The disturbances are of one shape and one width, wind is not
applied, and the response has not yet been tested against the pressure and sea level records of
dated events. The bed level at the heads of the inlets, where flooding is reported, rests on a
survey with gaps.</p>
<p class="note">Source code and documents at
<a href="https://github.com/cicero-martins/MaltaDT" target="_blank" rel="noopener">github.com/cicero-martins/MaltaDT</a>.
The interactive page is that of the Stagnone di Marsala digital twin, applied here without
change to its code.</p>
"""


def readme_html(rows) -> str:
    """The description of the set, with one row of the table for each scenario."""
    cells = []
    for r in rows:
        cells.append(
            f"<tr><td><a href=\"#\" onclick=\"scnGo('{r['case']}');return false\">the "
            f"{FROM[r['heading']]}</a></td><td>{r['speed'] * 3.6:.0f}</td>"
            f"<td>{r['senglea']:.1f}</td><td>{r['marsa']:.1f}</td><td>{r['msida']:.1f}</td></tr>")
    marsa_cm = max(r["marsa"] for r in rows) * 200.0 / (1025.0 * 9.81) * 100.0
    return README.replace("__ROWS__", "\n".join(cells)).replace("__MARSA_CM__", f"{marsa_cm:.0f}")


def extend(page: str, rows, scenario: dict, case: str) -> str:
    """The page of one scenario with the title, the bar, the README and the markers."""
    if MAP_OLD not in page:
        raise ValueError("the markup of the map was not found in the page of the portal")
    t1 = f"Pressure disturbance arriving from the {FROM[int(scenario['heading'])]}"
    t2 = (f"{scenario['speed'] * 3.6:.0f} km/h &middot; rise of {scenario['rise'] / 100:.0f} hPa "
          f"&middot; {scenario['sigma_along'] / 1e3:.0f} km long &middot; idealised scenario")
    listing = [dict(case=r["case"], abbr=ABBR[r["heading"]], **{"from": FROM[r["heading"]]},
                    kmh=round(r["speed"] * 3.6)) for r in rows]
    page = page.replace(MAP_OLD, MAP_NEW.replace("__T1__", t1).replace("__T2__", t2)
                        .replace("__README__", readme_html(rows)))
    page = page.replace("<style>", STYLE + "<style>", 1)
    return page + SCRIPT.replace("__SET__", json.dumps(listing)).replace("__CASE__", case)
