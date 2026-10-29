"""Build the interactive map of a hindcast, in the form of the Stagnone portal.

The page and the regrid are those of build_longwave_portal.py, which imports
them unchanged from the StagnoneDT repository. A hindcast differs from a
long-wave scenario in four respects, which are set here:

- the source is the merged surface file of extract_surface_map.py, the top
  layer of a three-dimensional run, rather than a two-dimensional map;
- the layer that carries the wave height in the Stagnone portal carries the
  sea surface temperature, the currents being drawn as moving particles;
- the clock is the calendar date of the run, and the coarse grid covers
  domain B rather than the outer domain;
- the BLUE buoy is shown among the stations, and no bar of scenarios is added.

Usage:
    python build_hindcast_portal.py v03_3d20_0722_0801 [--serve 8765]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_longwave_portal as lw  # noqa: E402

ROOT = lw.ROOT
OUT = ROOT / "outputs" / "hindcast_portal"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84_open.gpkg"
COARSE_LON, COARSE_LAT, COARSE_STEP = (14.05, 15.00), (35.70, 36.30), 0.004
FINE_VELOCITY_RANGE = 0.15      # m/s, scale of the particles at harbour zoom
STATION_LABELS = dict(lw.STATION_LABELS, blue_buoy="BLUE buoy")

PAGE_TEXT = (
    ("<title>Stagnone Hydrodynamics</title>", "<title>Valletta hindcast</title>"),
    ('font-weight:600">Stagnone Hydrodynamics</div>',
     'font-weight:600">Valletta hindcast</div>'),
    ("<h1>WetWise Hydrodynamics</h1>", "<h1>Hindcast</h1>"),
    ("Stagnone di Marsala Digital Twin", "Valletta harbours and Malta Plateau, CMEMS and ERA5 forcing"),
    ("{key:'wl',  label:'Water Level',      unit:'m',   sym:true}",
     "{key:'wl',  label:'Water Level',      unit:'cm',  sym:true}"),
    ("{key:'hwav',label:'Wave Height',      unit:'m',   sym:false}",
     "{key:'hwav',label:'Sea Surface Temperature', unit:'°C', sym:false}"),
    ("setLoad(34,'Wave height...');", "setLoad(34,'Sea surface temperature...');"),
    ("'Lagoon detail - '", "'Harbour detail - '"),
    ("zoom in for lagoon detail", "zoom in for harbour detail"),
    ("water level (m)", "water level (cm)"),
    ("yaxis:{...ax,title:{text:'m',font:{size:9}}}", "yaxis:{...ax,title:{text:'cm',font:{size:9}}}"),
    # the sections of the lagoon members give way to those of the harbours,
    # written to sections/ beside the page by build_harbour_sections_view.py
    ('<div class="s3-m">WV- &middot; waves and canopy, fixed bed, stratified initial state</div>\n'
     '        <div class="s3-r"><a href="sections/WV-/particles.html">Particles</a>'
     '<a href="sections/WV-/index.html">Arrows</a></div>\n'
     '        <div class="s3-m">v04AE &middot; uniform initial state, outside the Paper 1 ensemble</div>\n'
     '        <div class="s3-r"><a href="sections/v04AE/particles.html">Particles</a>'
     '<a href="sections/v04AE/index.html">Arrows</a></div>',
     '<div class="s3-m">Axis and central cross section of the Grand Harbour and of Marsamxett, '
     '26 to 29 July 2025, hourly</div>\n'
     '        <div class="s3-r"><a href="sections/particles.html">Particles</a>'
     '<a href="sections/index.html">Arrows</a></div>'),
)


def regrid(case_dir: Path, case: str, out_dir: Path) -> None:
    import regrid_wetwise_source as rw
    import xarray as xr

    ds = xr.open_dataset(case_dir / "output" / f"{case}_surface_map.nc")
    wet = ds["mesh2d_waterdepth"].isel(time=0).values > lw.MIN_DEPTH
    dry = np.where(wet, 1.0, np.nan).astype(np.float32)
    data = {
        "mesh2d_s1": ds["mesh2d_s1"].values.astype(np.float32) * 100.0 * dry,     # cm
        "mesh2d_ucx": ds["mesh2d_ucx"].values.astype(np.float32) * dry,
        "mesh2d_ucy": ds["mesh2d_ucy"].values.astype(np.float32) * dry,
        "mesh2d_hwav": ds["mesh2d_tem1"].values.astype(np.float32) * dry,        # degC
    }
    xb, yb = ds["mesh2d_face_x_bnd"].values, ds["mesh2d_face_y_bnd"].values
    if "mesh2d_face_x" in ds.variables:
        cx, cy = ds["mesh2d_face_x"].values, ds["mesh2d_face_y"].values
    else:
        # mean of the face nodes, for a surface file written without the centres
        cx, cy = np.nanmean(xb, axis=1), np.nanmean(yb, axis=1)
    args = (cx, cy, xb, yb,
            ds["time"].values, data, out_dir)
    rw.regrid("coarse", COARSE_LON, COARSE_LAT, COARSE_STEP, *args)
    rw.regrid("fine", lw.FINE_LON, lw.FINE_LAT, lw.FINE_STEP, *args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case")
    ap.add_argument("--root", default="model/hindcast")
    ap.add_argument("--skip-regrid", action="store_true")
    ap.add_argument("--serve", type=int, default=0, metavar="PORT")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(lw.STAGNONE))
    import build_wetwise_hydrodynamics_demo as bw

    root = Path(args.root)
    case_dir = (root if root.is_absolute() else ROOT / root) / args.case
    meta_case = json.loads((case_dir / "case.json").read_text())
    out_dir = OUT / args.case
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_regrid:
        regrid(case_dir, args.case, out_dir)

    page = bw.PAGE
    for a, b in PAGE_TEXT:
        if a not in page:
            print(f"text not found in the page of the portal: {a}", file=sys.stderr)
            return 1
        page = page.replace(a, b)

    lw.COAST = COAST
    lw.COARSE_LON, lw.COARSE_LAT = COARSE_LON, COARSE_LAT
    lw.STATION_LABELS = STATION_LABELS
    bw.OUT_DIR, bw.DATA_DIR, bw.VEL_DIR = out_dir, out_dir / "data", out_dir / "data" / "vel"
    bw.CACHE = {"coarse": out_dir / "demo_coarse.nc", "fine": out_dir / "demo_fine.nc"}
    bw.HTML = out_dir / "index.html"
    bw.PAGE = page
    bw.ZOOM_FINE = lw.ZOOM_FINE
    bw.DEFAULT_CMAP = dict(lw.DEFAULT_CMAP, hwav="thermal")
    bw.LAGOON_STATS_BOX = lw.HARBOUR_STATS_BOX
    bw.STATIONS = lw.stations(case_dir)
    bw.load_station_obs = lambda: {name: None for name in bw.STATIONS}
    bw.build_land_geojson = lw.land_geojson
    bw.SRC_LABEL = args.case
    bw.SRC_DESC = (f"{meta_case['start'][:10]} to {meta_case['stop'][:10]}, "
                   f"{meta_case['kmx']} layers, {meta_case.get('vertical', 'sigma').replace('_', ' ')}"
                   + (", CMEMS current at the boundary" if meta_case.get("boundary_velocity") else ""))
    bw.build()
    meta_path = out_dir / "data" / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for key in ("sta_info", "sta_model", "sta_obs"):
        if key in meta:
            meta[key] = {STATION_LABELS.get(k, k): v for k, v in meta[key].items()}
    meta["start_t"] = 0
    fine = meta["grids"]["fine"]
    fine["range"]["vel"] = FINE_VELOCITY_RANGE
    fine["range_max"]["vel"] = max(fine["range_max"]["vel"], 4 * FINE_VELOCITY_RANGE)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    print(f"page written to {bw.HTML}")
    if args.serve:
        from functools import partial
        from http.server import HTTPServer

        import serve_wetwise as sv
        handler = partial(sv.NoCacheHandler, directory=str(out_dir))
        print(f"serving {out_dir} at http://localhost:{args.serve}")
        HTTPServer(("127.0.0.1", args.serve), handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
