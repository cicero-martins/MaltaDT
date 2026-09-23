"""Reproject the Maltese coastline onto the working coordinate system and
report its registration against the merged bathymetry.

The two supplied datasets occupy different datums. The coastline is WGS84 /
UTM 33N (EPSG:32633), verified rather than assumed, and the bathymetry is
ED50 / UTM 33N (EPSG:23033), which its files do not declare. At Malta the
difference is approximately 197 m. Neither may be overlaid on the other
without a datum transformation, and no error is raised in either direction.

The working coordinate system is geographic WGS84 (EPSG:4326), following the
Delft3D FM convention established at the Stagnone, where the mesh is
geographic and the roughness assignment file must share its coordinate
system. Reaching it from the coastline is a change of projection alone,
within a single datum, and therefore exact. Reaching it from the bathymetry
requires a datum transformation, which is performed once in
`build_merged_bathymetry.py --to-wgs84` rather than repeatedly here.

On the choice of datum transformation. The bathymetry is reprojected with
ED50 to WGS 84 (12), the operation whose area of use names Malta, rather than
with the operation PROJ selects by default. The default, ED50 to WGS 84 (1),
declares the better accuracy of 10 m against 44 m, but that figure describes
the residual of its parameters over a list of northern and western European
states which does not include Malta. Accuracy declarations rank operations
within their own area of use and not across areas.

The choice was tested rather than assumed. Under operation (12) the
registration reported below improves from 99.33 to 99.51 per cent and the
count of disagreeing cells falls by 27 per cent, and the elevation sampled
along the coastline concentrates more tightly on zero. The two operations
differ by 19.4 m at Valletta, close to two cells, so the choice is not
cosmetic. The declared 44 m nonetheless remains a floor on how well the two
datasets can be co-registered, and the candidates are reported by this script
for that reason.

Usage:
    python prepare_coastline.py
    python prepare_coastline.py --no-check
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "coastline" / "MaltaCoastline.shp"
OUT = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
BATHY = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84.tif"

# The shapefile declares this and the declaration was verified at 99.26 per
# cent land and water agreement, against 94.54 per cent under EPSG:23033.
SOURCE_EPSG = 32633
WORKING_EPSG = 4326


def report_transformation_accuracy() -> None:
    """State what PROJ can and cannot offer for ED50 to WGS84 over Malta."""
    from pyproj import CRS
    from pyproj.transformer import TransformerGroup

    malta = (14.14, 35.76, 14.60, 36.11)
    group = TransformerGroup(CRS.from_epsg(23033), CRS.from_epsg(4326))
    print("ED50 to WGS84 operations relevant to Malta")
    for t in group.transformers:
        aoi = t.area_of_use
        if not aoi:
            continue
        covers = (aoi.west <= malta[0] and aoi.east >= malta[2]
                  and aoi.south <= malta[1] and aoi.north >= malta[3])
        named = "malta" in (aoi.name or "").lower()
        if covers or named:
            flag = ("named for Malta, USED" if named
                    else "bounding box covers Malta, PROJ default, not used")
            print(f"  accuracy {t.accuracy} m, {flag}")
            print(f"    {aoi.name[:90]}")


def reproject(check: bool = True) -> int:
    import geopandas as gpd

    if not RAW.exists():
        print(f"coastline not found at {RAW}", file=sys.stderr)
        return 1

    gdf = gpd.read_file(RAW)
    # Assign rather than trust, consistent with the treatment of the bathymetry.
    gdf = gdf.set_crs(SOURCE_EPSG, allow_override=True)
    print(f"Source: {len(gdf)} polygons, {gdf.geometry.area.sum() / 1e6:.1f} km2, "
          f"EPSG:{SOURCE_EPSG}")

    out = gdf.to_crs(epsg=WORKING_EPSG)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(OUT, driver="GPKG", layer="coastline")
    print(f"Written {OUT} in EPSG:{WORKING_EPSG}")

    if not check:
        return 0
    if not BATHY.exists():
        print(f"\nbathymetry not found at {BATHY}, registration check skipped")
        return 0

    import numpy as np
    import rasterio
    from rasterio.features import rasterize
    from scipy.ndimage import distance_transform_edt

    src = rasterio.open(BATHY)
    z = src.read(1)
    known = np.isfinite(z)
    land_raster = known & (z >= 0)
    mask = rasterize(((g, 1) for g in out.geometry), out_shape=z.shape,
                     transform=src.transform, fill=0, dtype="uint8").astype(bool)

    disagree = known & (mask != land_raster)
    mid = (src.bounds.bottom + src.bounds.top) / 2
    cell = (src.res[0] * 111320 * math.cos(math.radians(mid))
            + src.res[1] * 110570) / 2

    print("\nRegistration against the merged bathymetry")
    print(f"  agreement          {100 * (~disagree & known).sum() / known.sum():.2f}%")
    print(f"  disagreeing cells  {int(disagree.sum()):,}")

    edge = mask ^ np.pad(mask, ((0, 1), (0, 0)))[1:, :]
    edge |= mask ^ np.pad(mask, ((0, 0), (0, 1)))[:, 1:]
    dist = distance_transform_edt(~edge) * cell
    d = dist[disagree]
    print(f"  distance of disagreeing cells from the coastline, cell ~{cell:.0f} m")
    for q in (50, 75, 90, 95):
        print(f"    p{q}: {np.percentile(d, q):.0f} m")

    # A systematic datum offset would appear as a band of uniform thickness
    # along the entire coast. A short median with a sparse tail indicates
    # discretisation and epoch difference instead.
    far_water = known & (z < 0) & mask & (dist > 500)
    far_land = known & (z >= 0) & ~mask & (dist > 500)
    print(f"  beyond 500 m from the coastline:")
    print(f"    water inside the land polygons  {int(far_water.sum()):,}")
    print(f"    land outside the land polygons  {int(far_land.sum()):,}")
    if far_land.any():
        rr, cc = np.where(far_land)
        lon, lat = src.xy(int(rr.mean()), int(cc.mean()))
        print(f"      centred near {lon:.4f}, {lat:.4f}. Filfla is present in the "
              f"bathymetry and absent from the coastline")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-check", action="store_true",
                    help="skip the registration check against the bathymetry")
    args = ap.parse_args(argv)
    report_transformation_accuracy()
    print()
    return reproject(check=not args.no_check)


if __name__ == "__main__":
    sys.exit(main())
