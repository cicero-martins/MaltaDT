"""Open water passages that the supplied coastline closes under bridges.

The coastline of coastline_dataset.md draws some bridges as land, closing the
water beneath them. At the Manoel Island bridge, between the arm of Gzira and
Lazzaretto Creek in Marsamxett, aerial imagery shows water on both sides of a
bridge deck, while the polygon separates the two water bodies by 11.6 m of land.
Each opening is a rectangle of the stated width along the line joining the
nearest points of the two water bodies, extended by EXTEND_M into each, and is
removed from the land polygons. The width of the span is a working value, to be
replaced by a measurement.

Usage:
    python edit_coastline_openings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
OUT = ROOT / "data" / "processed" / "malta_coastline_wgs84_open.gpkg"
METRIC = "EPSG:32633"
EXTEND_M = 15.0

# name: (box in which the two water bodies are sought, lon0 lat0 lon1 lat1, span width in m)
OPENINGS = {
    "manoel_island_bridge": ((14.4935, 35.9020, 14.4990, 35.9060), 20.0),
}


def main() -> int:
    import geopandas as gpd
    from shapely.geometry import LineString, box
    from shapely.ops import nearest_points, unary_union

    land = gpd.read_file(SRC).to_crs(METRIC)
    union = unary_union(land.geometry)
    cuts = []
    for name, (bounds, width) in OPENINGS.items():
        b = gpd.GeoSeries([box(*bounds)], crs="EPSG:4326").to_crs(METRIC).iloc[0]
        water = b.difference(union)
        parts = sorted(getattr(water, "geoms", [water]), key=lambda g: -g.area)[:2]
        pa, pb = nearest_points(parts[0], parts[1])
        gap = pa.distance(pb)
        line = LineString([pa, pb])
        # extend the line by EXTEND_M at both ends
        dx, dy = (pb.x - pa.x) / gap, (pb.y - pa.y) / gap
        line = LineString([(pa.x - dx * EXTEND_M, pa.y - dy * EXTEND_M),
                           (pb.x + dx * EXTEND_M, pb.y + dy * EXTEND_M)])
        cut = line.buffer(width / 2.0, cap_style="flat")
        cuts.append(cut)
        print(f"{name}: land gap {gap:.1f} m, opening {width:.0f} m wide and {line.length:.0f} m long")
    opened = land.copy()
    opened["geometry"] = land.geometry.difference(unary_union(cuts))
    opened = opened[~opened.geometry.is_empty]
    opened.to_crs("EPSG:4326").to_file(OUT, driver="GPKG")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
