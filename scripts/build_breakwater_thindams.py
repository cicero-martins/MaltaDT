"""Thin dams along the breakwaters of the Grand Harbour mouth.

The St Elmo breakwater is some 12 m wide in the coastline and the Ricasoli
breakwater a little wider, against faces of 35 to 45 m at the harbour mouth.
The mesh is cut from the coastline by deleting the faces whose circumcentre
lies on land, so a structure narrower than a face leaves the faces on both
sides wet and a flow link between them passes through it.

Each thin dam is the boundary of the land within a box drawn around one
structure. A flow link crosses that boundary only where it passes through
land inside the box, so the thin dam closes the links through the breakwater
and leaves the gap under the St Elmo bridge open. The floating pontoons of the
Msida marina are left open, a working assumption to be confirmed with the
group.

The thin dams are written as malta_<mesh>_thd.pli beside the network, where
build_hindcast_v02.py and build_longwave_scenario.py pick them up.

Usage:
    python build_breakwater_thindams.py [--mesh v03 outer03] [--figure]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84_open.gpkg"

# Boxes around each structure, lon_min, lat_min, lon_max, lat_max. The St Elmo
# box stops short of the shore west of the breakwater, which keeps the gap open.
STRUCTURES = {
    "st_elmo_breakwater": (14.5209, 35.9024, 14.5256, 35.9035),
    "ricasoli_breakwater": (14.5226, 35.8985, 14.5240, 35.8996),
}


def thin_dams() -> dict[str, np.ndarray]:
    import geopandas as gpd
    import shapely

    coast = gpd.read_file(COAST).to_crs(4326)
    land = shapely.union_all(coast.geometry.values)
    out = {}
    for name, box in STRUCTURES.items():
        piece = land.intersection(shapely.box(*box))
        parts = list(piece.geoms) if piece.geom_type == "MultiPolygon" else [piece]
        if len(parts) != 1 or piece.is_empty:
            raise RuntimeError(f"{name}: expected one land polygon in the box, found {len(parts)}")
        out[name] = np.asarray(parts[0].exterior.coords)
    return out


def closed_links(net: Path, dams: dict[str, np.ndarray]) -> dict[str, int]:
    """Flow links whose centre-to-centre segment crosses each thin dam."""
    import shapely
    import xugrid as xu

    g = xu.open_dataset(net).grid
    efc = g.edge_face_connectivity
    ok = (efc[:, 0] >= 0) & (efc[:, 1] >= 0)
    a, b = efc[ok, 0], efc[ok, 1]
    segs = shapely.linestrings(np.stack([np.c_[g.face_x[a], g.face_y[a]],
                                         np.c_[g.face_x[b], g.face_y[b]]], axis=1))
    return {name: int(shapely.intersects(segs, shapely.LineString(xy)).sum())
            for name, xy in dams.items()}


def write_pli(path: Path, dams: dict[str, np.ndarray]) -> None:
    with open(path, "w") as f:
        for name, xy in dams.items():
            f.write(f"{name}\n{len(xy):6d} {2:4d}\n")
            for x, y in xy:
                f.write(f"{x:.7f} {y:.7f}\n")


def figure(net: Path, dams: dict[str, np.ndarray], out: Path) -> None:
    """Mesh at the harbour mouth with the coastline, the thin dams and the links they close."""
    import math

    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    import xugrid as xu
    from matplotlib.collections import LineCollection

    box = (14.5195, 35.8975, 14.5270, 35.9045)
    g = xu.open_dataset(net).grid
    efc = g.edge_face_connectivity
    ok = (efc[:, 0] >= 0) & (efc[:, 1] >= 0)
    a, b = efc[ok, 0], efc[ok, 1]
    links = np.stack([np.c_[g.face_x[a], g.face_y[a]], np.c_[g.face_x[b], g.face_y[b]]], axis=1)
    hit = np.zeros(len(a), bool)
    for xy in dams.values():
        hit |= shapely.intersects(shapely.linestrings(links), shapely.LineString(xy))
    fig, ax = plt.subplots(figsize=(7.5, 7))
    gpd.read_file(COAST).plot(ax=ax, color="#e7e6e1", edgecolor="#8a8984", linewidth=0.6)
    ax.add_collection(LineCollection(np.c_[g.node_x, g.node_y][g.edge_node_connectivity],
                                     colors="#52514e", linewidths=0.4))
    ax.add_collection(LineCollection(links[hit], colors="#eb6834", linewidths=2.0,
                                     label="flow links closed"))
    for i, xy in enumerate(dams.values()):
        ax.plot(xy[:, 0], xy[:, 1], color="#2a78d6", lw=1.6, label="thin dam" if i == 0 else None)
    ax.annotate("St Elmo breakwater", (14.5232, 35.9034), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=8.5)
    ax.annotate("Ricasoli breakwater", (14.5229, 35.8994), xytext=(-8, 6), textcoords="offset points",
                ha="right", fontsize=8.5)
    ax.annotate("gap under the\nSt Elmo bridge", (14.5209, 35.9030), xytext=(-6, -22),
                textcoords="offset points", ha="center", fontsize=8)
    ax.set_xlim(box[0], box[2])
    ax.set_ylim(box[1], box[3])
    ax.set_aspect(1 / math.cos(math.radians(35.9)))
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=7.5)
    fig.savefig(out, dpi=170, facecolor="#fcfcfb", bbox_inches="tight")
    print(f"figure written to {out}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mesh", nargs="+", default=["v03", "outer03"])
    ap.add_argument("--figure", action="store_true", help="draw the harbour mouth on the first mesh")
    args = ap.parse_args(argv)
    dams = thin_dams()
    for mesh in args.mesh:
        d = ROOT / "data" / "processed" / f"mesh_{mesh}"
        out = d / f"malta_{mesh}_thd.pli"
        write_pli(out, dams)
        counts = closed_links(d / f"malta_{mesh}_net.nc", dams)
        print(f"{out.name}: " + ", ".join(f"{k} closes {n} links" for k, n in counts.items()))
    if args.figure:
        mesh = args.mesh[0]
        figure(ROOT / "data" / "processed" / f"mesh_{mesh}" / f"malta_{mesh}_net.nc", dams,
               ROOT / "figures" / "breakwater_thindams.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
