"""Build an interactive map of one long-wave scenario, in the form of the Stagnone portal.

The portal of the Stagnone digital twin is a static page, a Leaflet map on
which scalar fields are painted from binary files and the currents are drawn
as moving particles by leaflet-velocity, with a time slider and station plots.
This script produces the same page for a scenario of build_longwave_scenario.py
by reusing the two stages of that portal without modification of their code:

1. the regrid of the unstructured output onto two regular grids with an exact
   wet mask, from StagnoneDT/scripts/regrid_wetwise_source.py;
2. the conversion of those grids into the payload of the browser and the page
   itself, from StagnoneDT/scripts/build_wetwise_hydrodynamics_demo.py.

What is specific to Valletta is passed in: the grids, the stations, the land
outline, the units and the wording of the page. The water level is written in
centimetres, the scenario being a response of a few centimetres to a pressure
rise of 2 hPa. The layer that carries the wave height at the Stagnone carries
the current speed here, since the scenario has no waves.

    coarse grid   the outer domain at COARSE_STEP
    fine grid     the Valletta harbours at FINE_STEP

Usage:
    python build_longwave_portal.py outer01_h225_u36_s15 --root model/tests/longwave_video
    python ../StagnoneDT/scripts/serve_wetwise.py   is replaced by   --serve
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGNONE = ROOT.parent / "StagnoneDT" / "scripts"
OUT = ROOT / "outputs" / "longwave_portal"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
CHANNEL = ROOT / "data" / "external" / "emodnet_channel.tif"

COARSE_LON, COARSE_LAT, COARSE_STEP = (12.5, 17.0), (34.5, 37.7), 0.015
FINE_LON, FINE_LAT, FINE_STEP = (14.485, 14.540), (35.870, 35.915), 0.0002
HARBOUR_STATS_BOX = (14.490, 14.532, 35.876, 35.908)     # lon0, lon1, lat0, lat1
ZOOM_FINE = 13
FINE_VELOCITY_RANGE = 0.02      # m/s, scale of the particles at harbour zoom
DEFAULT_CMAP = {"wl": "viridis", "hwav": "haline", "vel": "wetwise-amber"}
MIN_DEPTH = 0.05                # m
MALTA_BOX = (14.0, 35.6, 14.8, 36.2)
STATION_NAMES = ("offshore_4km", "gh_mouth", "senglea", "marsa_head", "mx_mouth",
                 "msida_head")

# Wording of the page, the Stagnone text on the left and the Valletta text on the right.
PAGE_TEXT = (
    ("<title>Stagnone Hydrodynamics</title>", "<title>Valletta long-wave scenario</title>"),
    ('font-weight:600">Stagnone Hydrodynamics</div>',
     'font-weight:600">Valletta long-wave scenario</div>'),
    ("<h1>WetWise Hydrodynamics</h1>", "<h1>Long-wave scenario</h1>"),
    ("Stagnone di Marsala Digital Twin", "Valletta harbours, moving pressure disturbance"),
    ("{key:'wl',  label:'Water Level',      unit:'m',   sym:true}",
     "{key:'wl',  label:'Water Level',      unit:'cm',  sym:true}"),
    ("{key:'hwav',label:'Wave Height',      unit:'m',   sym:false}",
     "{key:'hwav',label:'Current Speed',    unit:'m/s', sym:false}"),
    ("setLoad(34,'Wave height...');", "setLoad(34,'Current speed...');"),
    ("{key:'vel', label:'Surface Velocity', unit:'m/s', sym:false}",
     "{key:'vel', label:'Current Velocity', unit:'m/s', sym:false}"),
    # The clock of the run is elapsed time, the calendar date being arbitrary.
    ("document.getElementById('tlabel').textContent=TIMES[currentT]||'-';",
     "document.getElementById('tlabel').textContent=(function(){"
     "const m=Math.round(currentT*__STEP_MIN__);"
     "return 't = '+Math.floor(m/60)+' h '+String(m%60).padStart(2,'0')+' min';})();"),
    ("&middot; surface &middot; 30 min", "&middot; depth-averaged &middot; __STEP__"),
    ("'Lagoon detail - '", "'Harbour detail - '"),
    ("zoom in for lagoon detail", "zoom in for harbour detail"),
    ("' - water level'", "' - water level'"),
    ("water level (m)", "water level (cm)"),
    ("yaxis:{...ax,title:{text:'m',font:{size:9}}}", "yaxis:{...ax,title:{text:'cm',font:{size:9}}}"),
)


def regrid(case_dir: Path, case: str, out_dir: Path) -> None:
    """Write the two regular-grid caches from the map output of the scenario."""
    import regrid_wetwise_source as rw
    import xarray as xr

    ds = xr.open_dataset(case_dir / "output" / f"{case}_map.nc")
    wet = ds["mesh2d_waterdepth"].isel(time=0).values > MIN_DEPTH
    dry = np.where(wet, 1.0, np.nan).astype(np.float32)
    ucx = ds["mesh2d_ucx"].values.astype(np.float32) * dry
    ucy = ds["mesh2d_ucy"].values.astype(np.float32) * dry
    data = {
        "mesh2d_s1": ds["mesh2d_s1"].values.astype(np.float32) * 100.0 * dry,    # cm
        "mesh2d_ucx": ucx,
        "mesh2d_ucy": ucy,
        "mesh2d_hwav": np.hypot(ucx, ucy),                                      # speed, m/s
    }
    args = (ds["mesh2d_face_x"].values, ds["mesh2d_face_y"].values,
            ds["mesh2d_face_x_bnd"].values, ds["mesh2d_face_y_bnd"].values,
            ds["time"].values, data, out_dir)
    rw.regrid("coarse", COARSE_LON, COARSE_LAT, COARSE_STEP, *args)
    rw.regrid("fine", FINE_LON, FINE_LAT, FINE_STEP, *args)


def land_geojson() -> dict:
    """The surveyed coastline for the Maltese Islands, the EMODnet grid elsewhere."""
    import geopandas as gpd
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import box, mapping, shape

    feats = []
    for k, g in enumerate(gpd.read_file(COAST).geometry):
        for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            feats.append({"type": "Feature", "properties": {"name": f"malta_{k}"},
                          "geometry": mapping(p.simplify(0.00002))})
    with rasterio.open(CHANNEL) as src:
        z = src.read(1)
        land = z >= 0
        polys = [shape(g) for g, v in shapes(land.astype("uint8"), mask=land,
                                             transform=src.transform) if v == 1]
    frame = box(COARSE_LON[0], COARSE_LAT[0], COARSE_LON[1], COARSE_LAT[1])
    for k, p in enumerate(polys):
        if p.intersects(box(*MALTA_BOX)) or not p.intersects(frame) or p.area < 1e-4:
            continue
        p = p.intersection(frame).simplify(0.003)
        for q in (p.geoms if p.geom_type == "MultiPolygon" else [p]):
            feats.append({"type": "Feature", "properties": {"name": f"land_{k}"},
                          "geometry": mapping(q)})
    return {"type": "FeatureCollection", "features": feats}


def stations(case_dir: Path) -> dict:
    out = {}
    for line in (case_dir / "stations_obs.xyn").read_text().splitlines():
        lon, lat, name = line.split()
        name = name.strip("'")
        if name in STATION_NAMES:
            out[name] = {"csv": "", "lon": float(lon), "lat": float(lat)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--root", default="model/tests/longwave_video",
                    help="directory holding the case")
    ap.add_argument("--html-only", action="store_true", help="rewrite the page alone")
    ap.add_argument("--skip-regrid", action="store_true", help="reuse the caches")
    ap.add_argument("--discard-caches", action="store_true",
                    help="remove the regridded caches once the payload is written")
    ap.add_argument("--serve", type=int, default=0, metavar="PORT",
                    help="serve the page locally after building it")
    args = ap.parse_args(argv)
    if not STAGNONE.exists():
        print(f"the portal builder is taken from {STAGNONE}, which is missing", file=sys.stderr)
        return 1
    sys.path.insert(0, str(STAGNONE))
    import build_wetwise_hydrodynamics_demo as bw

    root = Path(args.root)
    case_dir = (root if root.is_absolute() else ROOT / root) / args.case
    sc = json.loads((case_dir / "scenario.json").read_text())
    out_dir = OUT / args.case
    out_dir.mkdir(parents=True, exist_ok=True)

    if not (args.html_only or args.skip_regrid):
        regrid(case_dir, args.case, out_dir)

    # Interval between frames, from the caches or, once they are discarded,
    # from the payload already written.
    import pandas as pd
    import xarray as xr
    if (out_dir / "demo_coarse.nc").exists():
        with xr.open_dataset(out_dir / "demo_coarse.nc") as c:
            t = c["time"].values
            step_s = float((t[1] - t[0]) / np.timedelta64(1, "s"))
    else:
        times = json.loads((out_dir / "data" / "meta.json").read_text(encoding="utf-8"))["times"]
        step_s = (pd.Timestamp(times[1]) - pd.Timestamp(times[0])).total_seconds()
    page = bw.PAGE
    for a, b in PAGE_TEXT:
        if a not in page:
            print(f"text not found in the page of the portal: {a}", file=sys.stderr)
            return 1
        page = page.replace(a, b.replace("__STEP__", f"{step_s / 60:.0f} min")
                            .replace("__STEP_MIN__", f"{step_s / 60:g}"))

    bw.OUT_DIR, bw.DATA_DIR, bw.VEL_DIR = out_dir, out_dir / "data", out_dir / "data" / "vel"
    bw.CACHE = {"coarse": out_dir / "demo_coarse.nc", "fine": out_dir / "demo_fine.nc"}
    bw.HTML = out_dir / "index.html"
    bw.PAGE = page
    bw.ZOOM_FINE = ZOOM_FINE
    bw.DEFAULT_CMAP = DEFAULT_CMAP
    bw.LAGOON_STATS_BOX = HARBOUR_STATS_BOX
    bw.STATIONS = stations(case_dir)
    bw.load_station_obs = lambda: {name: None for name in bw.STATIONS}
    bw.build_land_geojson = land_geojson
    bw.SRC_LABEL = args.case
    bw.SRC_DESC = (f"pressure rise of {sc['rise'] / 100:.0f} hPa at {sc['speed'] * 3.6:.0f} km/h, "
                   f"heading {sc['heading']:.0f}, {sc['sigma_along'] / 1e3:.0f} km long")
    if args.html_only:
        bw.write_html()
    else:
        bw.build()
        # Scale of the particles at harbour zoom, where the currents of a
        # scenario of 2 hPa are of a few centimetres per second.
        meta_path = bw.DATA_DIR / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fine = meta["grids"]["fine"]
        fine["range"]["vel"] = FINE_VELOCITY_RANGE
        fine["range_max"]["vel"] = max(fine["range_max"]["vel"], 4 * FINE_VELOCITY_RANGE)
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        for cache in bw.CACHE.values():
            if args.discard_caches:
                cache.unlink()
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
