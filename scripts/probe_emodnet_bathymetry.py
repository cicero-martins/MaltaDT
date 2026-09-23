"""Probe EMODnet Bathymetry over a bounding box: resolution, wet-cell coverage,
and the CDI source records the DTM actually used.

Answers the question "is the public bathymetry good enough to mesh this site?"
before any mesh work starts. Written 2026-09-22 while evaluating the Valletta
harbours, but the bbox is a parameter, so it serves any site.

Three independent sources are queried because they disagree, and the
disagreement is itself informative:

  * WFS emodnet:source_references  -- survey footprints. Over Malta this returns
    only GEBCO2024, which would suggest no survey exists.
  * REST depth_sample              -- per-point provenance. Over the Grand
    Harbour this DOES return a CDI record, contradicting the WFS layer. Trust
    this one: it reports what the DTM used at that point, including whether the
    value was interpolated.
  * WCS emodnet__mean              -- the actual grid, for counting cells.

Usage:
    python probe_emodnet_bathymetry.py --bbox 14.470 35.870 14.560 35.925
    python probe_emodnet_bathymetry.py --bbox ... --points 14.515,35.893 ...

Requires rasterio and numpy (present in dfm_tools_env).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request

OWS = "https://ows.emodnet-bathymetry.eu"
REST = "https://rest.emodnet-bathymetry.eu"
TIMEOUT = 120


def _get(url: str, params: dict) -> bytes:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=TIMEOUT) as r:
        return r.read()


def source_references(bbox) -> list[dict]:
    """Survey footprints intersecting the bbox.

    The geometry column is `geom`, not the GeoServer default `the_geom`, and
    getting that wrong returns an InvalidParameterValue rather than an empty
    result.
    """
    lon0, lat0, lon1, lat1 = bbox
    raw = _get(
        f"{OWS}/wfs",
        {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": "emodnet:source_references",
            "CQL_FILTER": f"BBOX(geom,{lon0},{lat0},{lon1},{lat1})",
            "outputFormat": "application/json",
            "maxFeatures": 200,
        },
    )
    return json.loads(raw).get("features", [])


def depth_sample(lon: float, lat: float) -> dict:
    """Per-point depth and provenance. `interpolationType` true means the value
    was interpolated rather than measured, which matters more than the number."""
    raw = _get(f"{REST}/depth_sample", {"geom": f"POINT({lon} {lat})"})
    return json.loads(raw)


def footprint(bbox, step: float, workers: int = 4):
    """Map which CDI source covers what, by sampling depth_sample on a grid.

    This is the only reliable way to learn a source's real extent. The WFS
    source_references layer under-reports badly (over Malta it names only
    GEBCO2024 while six sources are actually in use), and two or three sampled
    points are not enough: `4036_MEPA` looks like a Grand Harbour survey from
    inside the harbour and turns out to ring the whole island.

    Keep `workers` low. The service starts returning errors above roughly four
    concurrent requests, and a rate-limited miss is indistinguishable from
    genuine absence of coverage, which is exactly the wrong failure mode here.
    """
    import numpy as np

    lon0, lat0, lon1, lat1 = bbox
    lons = np.round(np.arange(lon0, lon1 + step / 2, step), 4)
    lats = np.round(np.arange(lat0, lat1 + step / 2, step), 4)
    pts = [(float(x), float(y)) for y in lats for x in lons]

    import concurrent.futures as cf
    import time

    def one(pt, tries=4):
        for k in range(tries):
            try:
                return pt, depth_sample(*pt)
            except Exception:
                time.sleep(0.6 * (k + 1))
        return pt, None

    res = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for pt, d in ex.map(one, pts):
            if d is None:
                res[pt] = (None, "ERR")
            else:
                res[pt] = (d.get("avg"), (d.get("reference") or {}).get("identifier"))

    from collections import Counter

    counts = Counter(r for _, r in res.values())
    print(f"  sampled {len(pts)} points at {step} deg")
    for k, v in counts.most_common():
        print(f"    {str(k):26s} {v}")

    order = [k for k, _ in counts.most_common() if k not in (None, "ERR")]
    sym = dict(zip(order, "ABCDEFGH"))
    print("\n  legend: " + ", ".join(f"{v}={k}" for k, v in sym.items())
          + "   . = no source (land or fallback)   ! = error")
    print(f"\n  north up, lon {lons[0]} to {lons[-1]}")
    for y in lats[::-1]:
        row = ""
        for x in lons:
            ref = res[(float(x), float(y))][1]
            row += "!" if ref == "ERR" else ("." if ref is None else sym[ref])
        print(f"   {y:.3f} {row}")
    return res


def fetch_grid(bbox, path: str) -> str:
    lon0, lat0, lon1, lat1 = bbox
    params = [
        ("service", "WCS"),
        ("version", "2.0.1"),
        ("request", "GetCoverage"),
        ("coverageId", "emodnet__mean"),
        ("subset", f"Lat({lat0},{lat1})"),
        ("subset", f"Long({lon0},{lon1})"),
        ("format", "image/tiff"),
    ]
    full = f"{OWS}/wcs?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=TIMEOUT) as r:
        data = r.read()
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def describe_grid(path: str, ascii_map: bool = True) -> None:
    import numpy as np
    import rasterio

    src = rasterio.open(path)
    z = src.read(1).astype(float)
    if src.nodata is not None:
        z = np.where(np.isclose(z, src.nodata), np.nan, z)

    mid_lat = (src.bounds.bottom + src.bounds.top) / 2
    dx = src.res[0] * 111320 * math.cos(math.radians(mid_lat))
    dy = src.res[1] * 110570

    wet = z < 0
    print(f"  grid            {src.width} x {src.height} cells")
    print(f"  cell size       {dx:.0f} m x {dy:.0f} m")
    print(f"  water cells     {int(wet.sum())} of {z.size} ({100 * wet.sum() / z.size:.0f}%)")
    if wet.any():
        d = -z[wet]
        print(f"  depth           min {d.min():.1f}  mean {d.mean():.1f}  max {d.max():.1f} m")
        widths = [int(r.sum()) for r in wet]
        print(f"  water width per row, N to S (cells): {widths}")

    if ascii_map:
        print()
        for i in range(z.shape[0]):
            row = ""
            for j in range(z.shape[1]):
                v = z[i, j]
                if np.isnan(v):
                    row += "?"
                elif v >= 0:
                    row += "#"
                else:
                    d = -v
                    row += ("1" if d < 5 else "2" if d < 10 else "3" if d < 20
                            else "4" if d < 40 else "5" if d < 80 else "6")
            print("   " + row)
        print("   legend: # land, 1 <5m, 2 5-10m, 3 10-20m, 4 20-40m, 5 40-80m, 6 >80m")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", nargs=4, type=float, required=True,
                    metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--points", nargs="*", default=[],
                    help="lon,lat pairs to probe for provenance")
    ap.add_argument("--tif", default="emodnet_probe.tif")
    ap.add_argument("--no-map", action="store_true")
    ap.add_argument("--footprint", type=float, metavar="STEP_DEG",
                    help="map which CDI source covers what, on a grid of this "
                         "spacing in degrees (0.04 for a regional footprint, "
                         "0.005 for a harbour). Skips the WCS grid.")
    args = ap.parse_args(argv)

    bbox = tuple(args.bbox)
    print(f"EMODnet Bathymetry probe over {bbox}\n")

    print("SURVEY FOOTPRINTS (WFS source_references)")
    try:
        feats = source_references(bbox)
        if not feats:
            print("  none")
        for f in feats:
            p = f["properties"]
            print(f"  - {p.get('identifier')} | type {p.get('type')} | "
                  f"device {p.get('device')} | edmo {p.get('edmo_id')}")
            if p.get("metadata_url"):
                print(f"      {p['metadata_url']}")
        print("  NOTE: this layer can under-report. Cross-check with the point "
              "probes below, which reflect what the DTM actually used.")
    except Exception as exc:  # the service 502s under load
        print(f"  query failed: {exc}")

    if args.points:
        print("\nPOINT PROVENANCE (REST depth_sample)")
        for spec in args.points:
            lon, lat = (float(v) for v in spec.split(","))
            try:
                d = depth_sample(lon, lat)
            except Exception as exc:
                print(f"  {spec}: failed, {exc}")
                continue
            ref = d.get("reference") or {}
            interp = d.get("interpolationType")
            print(f"  {spec}: avg {d.get('avg')}  interpolated={interp}")
            if ref:
                print(f"      CDI {ref.get('identifier')} | EDMO {ref.get('organisation_id')}")
                print(f"      {ref.get('metadata_url')}")
            else:
                print("      no CDI reference (fallback grid)")

    if args.footprint:
        print("\nSOURCE FOOTPRINT (REST depth_sample on a grid)")
        footprint(bbox, args.footprint)
        return 0

    print("\nGRID (WCS emodnet__mean)")
    try:
        fetch_grid(bbox, args.tif)
        describe_grid(args.tif, ascii_map=not args.no_map)
    except Exception as exc:
        print(f"  failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
