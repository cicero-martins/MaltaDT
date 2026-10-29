"""Build the perspective views of the velocity sections in the Valletta harbours.

Consumes sections.nc as written by extract_harbour_sections.py and writes the
two pages of the Stagnone portal, the arrow view and the particle view, from
StagnoneDT/scripts/build_wetwise_sections_view.py and
build_wetwise_sections_particles.py, without modification of their code. In
both, the surface-layer currents are drawn on a plane at the free surface and
the vertical sections hang below it as curtains coloured by the velocity
normal to each section. What is specific to Valletta is passed in or replaced
in the page:

1. the names of the four sections, the labels of the places and the coastline;
2. the arrows on the curtains, drawn in the layers nearest to 15, 50 and 85 per
   cent of the column, since the 20 layers are stretched toward the surface;
3. the vertical interpolation of the particle view, which places the layer
   centres at the stretched sigma written by FM rather than at uniform sigma;
4. the link back, to the map of the hindcast beside which the pages are written;
5. the lengths of the arrows, scaled from a lagoon some 10 km long and 2 m deep
   to harbours some 4 km long and 30 m deep;
6. the camera on opening, from the southwest, which looks up both harbours
   from their heads toward the mouths.

The default window is the validation week, which holds calm days on either
side of the northwesterly wind of 26 to 31 July, strongest from 27 to 29 July. The map output at 30 minutes
is thinned to one frame an hour, since the browser downloads and parses the
whole payload before drawing, and the week takes some 42 and 58 MB hourly
against 82 and 115 MB at 30 minutes. Elevations and surface speeds are
rounded to centimetres and cm/s.

Usage:
    python build_harbour_sections_view.py v03_3d20s_0722_0801_uv_thd
        [--start 2025-07-25T00:00] [--stop 2025-08-01T00:00] [--every 2]
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "StagnoneDT" / "scripts"))
import build_wetwise_sections_particles as pv  # noqa: E402
import build_wetwise_sections_view as vw  # noqa: E402

COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
CASES = ROOT / "model" / "hindcast"
PORTAL = ROOT / "outputs" / "hindcast_portal"

SECTION_LABEL = {"gh_axis": "Grand Harbour, axis", "gh_cross": "Grand Harbour, cross section",
                 "mx_axis": "Marsamxett, axis", "mx_cross": "Marsamxett, cross section"}
LABELS = [(14.5150, 35.8940, "Grand Harbour"), (14.5060, 35.9040, "Marsamxett"),
          (14.4990, 35.8790, "Marsa"), (14.4925, 35.8978, "Msida"),
          (14.5141, 35.8893, "Senglea"), (14.5110, 35.8985, "Valletta"),
          (14.5000, 35.9025, "Manoel Island"), (14.5232, 35.9040, "St Elmo breakwater")]
ARROW_FRACTIONS = (0.15, 0.50, 0.85)
SURF_ARROW_STRIDE = 5             # every fifth surface grid point, ~200 m

# Horizontal lengths in km at the reference speed, surface then sections, and
# the vertical rise of the section arrows in m, at the 95th percentile of |w|
# and at most.
ARROW_SCALES = [("S.av[i], null, 0.30,", "S.av[i], null, 0.12,"),
                ("s.aw[i], 0.22,", "s.aw[i], 0.10,"),
                ("DZMAX = 0.25, DZREF = 0.12;", "DZMAX = 3.0, DZREF = 1.5;")]

# The opening camera and the preset that returns to it, both in the
# normalised scene box, set to the southwest preset of the page.
OPENING_CAMERA = [("camera:{eye:{x:0.95 * ZOOM, y:-0.40 * ZOOM, z:0.45 * ZOOM}",
                   "camera:{eye:{x:-0.62 * ZOOM, y:-0.72 * ZOOM, z:0.45 * ZOOM}"),
                  ("['Initial', {eye:{x:0.95, y:-0.40, z:0.45}, up:UP}],",
                   "['Initial', {eye:{x:-0.62, y:-0.72, z:0.45}, up:UP}],")]

# The dark theme of the hindcast map, which opens dark, in place of the theme
# of the operating system that the Stagnone pages follow.
DARK_TOKENS = ":root { --bg:#0d1117; --ink:#e6edf3; --muted:#9aa7b4; --line:#1f2937; }"
THEME = [(":root { --bg:#ffffff; --ink:#1b1b1b; --muted:#6b6b6b; --line:#e3e2de; }", DARK_TOKENS),
         (":root { --bg:#16171a; --ink:#ececec; --muted:#a0a0a0; --line:#33343a; }", DARK_TOKENS),
         ("const dark = matchMedia('(prefers-color-scheme: dark)').matches;", "const dark = true;"),
         ("const BG = dark ? '#16171a' : '#ffffff';", "const BG = '#0d1117';")]

# Every redraw passes layout.scene.camera, which the Stagnone pages update only
# from the relayout event at the end of a drag, so a redraw during the drag,
# every 50 ms in the particle view and every frame while playing, returns the
# camera to where it stood before. The camera is read from the scene before
# each redraw, and redraws wait while the mouse button is held.
LIVE_CAMERA = """const el = document.getElementById('scene');
let DRAG = false;
el.addEventListener('mousedown', () => { DRAG = true; }, true);
window.addEventListener('mouseup', () => { DRAG = false; }, true);
function liveCamera() {
  const s = el._fullLayout && el._fullLayout.scene && el._fullLayout.scene._scene;
  if (s && s.getCamera) layout.scene.camera = s.getCamera();
}"""
CAMERA = [("const el = document.getElementById('scene');", LIVE_CAMERA),
          ("function show(i) { Plotly.react(el",
           "function show(i) { if (DRAG) return; liveCamera(); Plotly.react(el"),
          ("function show(i) {\n  busy = true; shown = i;",
           "function show(i) {\n  liveCamera();\n  busy = true; shown = i;"),
          ("  if (busy) return;", "  if (busy || DRAG) return;")]

STAGNONE_LABELS ="const SECTION_LABEL = {ns_axis:'N–S section', ew_centre:'E–W section'};"
STAGNONE_BACK = '<a href="../../index.html">&larr; WetWise portal</a>'
UNIFORM_LAYERS = """// layer centres sit at sigma = (k + 1/2) / nk
function layerAt(F, i0, i1, al, p, sig, nk) {
  const ks = Math.max(0, Math.min(nk - 1.000001, sig * nk - 0.5));
  const k = Math.floor(ks), t = ks - k;"""
STRETCHED_LAYERS = """// layer centres sit at the stretched sigma written by FM, 0 at the bed
const SIGC = D.sigma;
function layerAt(F, i0, i1, al, p, sig, nk) {
  let k = 0;
  while (k < nk - 2 && SIGC[k + 1] < sig) k++;
  const t = Math.max(0, Math.min(1, (sig - SIGC[k]) / (SIGC[k + 1] - SIGC[k])));"""


def coarsen(a, nd: int):
    """Nested list rounded to nd decimals, None kept."""
    if isinstance(a, list):
        return [coarsen(x, nd) for x in a]
    return None if a is None else round(a, nd)


def read_coast(_path=None) -> dict:
    """Outlines of the land polygons near the harbours, in the form of _read_ldb."""
    land = gpd.read_file(COAST).clip(box(14.47, 35.86, 14.55, 35.93))
    rings = {}
    for geom in land.geometry:
        for poly in getattr(geom, "geoms", [geom]):
            if poly.geom_type == "Polygon":
                rings[f"L{len(rings)}"] = np.asarray(poly.exterior.coords)
    return rings


def adapt(template: str) -> str:
    """The Stagnone page with the names, the link back and the layers of Valletta."""
    labels = "const SECTION_LABEL = " + str(SECTION_LABEL).replace('"', "'") + ";"
    out = template.replace(STAGNONE_LABELS, labels).replace(
        STAGNONE_BACK, '<a href="../index.html">&larr; Valletta hindcast map</a>')
    if UNIFORM_LAYERS in out:
        out = out.replace(UNIFORM_LAYERS, STRETCHED_LAYERS)
    elif "layerAt" in out:
        raise SystemExit("particle page changed: vertical interpolation not found")
    for old, new in ARROW_SCALES:
        if old in out:
            out = out.replace(old, new)
        elif "function arrows(" in out:
            raise SystemExit(f"Stagnone page changed: {old} not found")
    for old, new in OPENING_CAMERA:
        if old not in out:
            raise SystemExit(f"Stagnone page changed: {old} not found")
        out = out.replace(old, new)
    for old, new in THEME + CAMERA:
        out = out.replace(old, new)
    particles = "function tick()" in out
    for marker in ["const dark = true;", DARK_TOKENS, "liveCamera(); ", "let DRAG"] + \
            (["const BG = '#0d1117';", "if (busy || DRAG) return;"] if particles else []):
        if marker not in out and not (marker == "liveCamera(); " and particles):
            raise SystemExit(f"Stagnone page changed: {marker} not applied")
    if particles and "  liveCamera();\n  busy = true;" not in out:
        raise SystemExit("Stagnone page changed: camera of the particle view not applied")
    if labels not in out or "Valletta hindcast map" not in out:
        raise SystemExit("Stagnone page changed: labels or link not found")
    return out


def main(argv=None) -> int:
    ap = vw.parser()
    ap.prog = "build_harbour_sections_view.py"
    ap.add_argument("case")
    ap.add_argument("--every", type=int, default=2, help="keep one frame in N")
    ap.set_defaults(cache=None, start="2025-07-25T00:00", stop="2025-08-01T00:00",
                    title="Valletta harbours, vertical sections")
    for a in ap._actions:
        if a.dest == "cache":
            a.required = False
    args = ap.parse_args(argv)
    src = CASES / args.case / "output" / "sections"
    out = PORTAL / args.case / "sections"
    out.mkdir(parents=True, exist_ok=True)
    args.cache = src
    args.member = args.member or args.case

    ds = vw.open_cache(args).isel(time=slice(None, None, args.every))
    sigma = ds.sigma.values
    vw.SEC_ARROW_LAYERS = tuple(int(np.abs(sigma - f).argmin()) for f in ARROW_FRACTIONS)
    vw.LABELS = LABELS
    vw.SURF_ARROW_STRIDE = SURF_ARROW_STRIDE
    vw._read_ldb = read_coast

    payload = vw.build_payload(ds, args)
    payload["sigma"] = [round(float(s), 5) for s in sigma]
    # the Stagnone payload keeps millimetres and mm/s; centimetres of elevation
    # and cm/s of surface speed are below what the scene resolves, and halve
    # the largest fields
    payload["mesh"]["z"] = coarsen(payload["mesh"]["z"], 2)
    payload["mesh"]["speed"] = coarsen(payload["mesh"]["speed"], 2)
    for sec in payload["sections"].values():
        sec["z"] = coarsen(sec["z"], 2)
    vw.write_page(payload, adapt(vw.TEMPLATE), out / "index.html", args.title)
    pv.add_particle_fields(ds, payload)
    vw.write_page(payload, adapt(pv.TEMPLATE), out / "particles.html", args.title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
