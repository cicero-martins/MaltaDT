"""Face bed levels of mesh v02 before and after the harbour cleaning.

The face level is the mean of its node levels, as D-Flow FM computes it under
bedLevType = 3. Faces whose mean level is at or above zero, dry at mean sea
level, are drawn in grey.

Usage:
    python figure_mesh_bathymetry_cleaning.py [--before v02] [--after v02b]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIGURE = ROOT / "figures" / "mesh_bathymetry_cleaning.png"
VIEWS = [("Marsamxett", (14.488, 35.893, 14.512, 35.912)),
         ("Grand Harbour", (14.494, 35.874, 14.530, 35.898)),
         ("Manoel Island bridge", (14.4945, 35.9025, 14.4985, 35.9060))]


def faces(name):
    import xugrid as xu

    uds = xu.open_dataset(ROOT / "data" / "processed" / f"mesh_{name}" / f"malta_{name}_net.nc")
    g = uds.grid
    z = uds["mesh2d_node_z"].values
    fn = g.face_node_connectivity
    polys = [np.c_[g.node_x[r[r >= 0]], g.node_y[r[r >= 0]]] for r in fn]
    fz = np.array([z[r[r >= 0]].mean() for r in fn])
    return polys, fz, g.face_x, g.face_y


def main(argv=None) -> int:
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before", default="v02")
    ap.add_argument("--after", default="v03")
    args = ap.parse_args(argv)
    coast = gpd.read_file(ROOT / "data" / "processed" / "malta_coastline_wgs84_open.gpkg")
    data = {k: faces(k) for k in (args.before, args.after)}
    fig, axes = plt.subplots(3, 2, figsize=(13, 16))
    for row, (title, b) in zip(axes, VIEWS):
        for ax, key in zip(row, (args.before, args.after)):
            polys, fz, fx, fy = data[key]
            sel = np.where((fx > b[0]) & (fx < b[2]) & (fy > b[1]) & (fy < b[3]))[0]
            p = [polys[k] for k in sel]
            v = fz[sel]
            ax.add_collection(PolyCollection(p, array=np.where(v < 0, v, np.nan), cmap="viridis",
                                             clim=(-20, 0), edgecolor=(1, 1, 1, 0.3), lw=0.2))
            dry = [q for q, w in zip(p, v) if w >= 0]
            ax.add_collection(PolyCollection(dry, facecolor="#9b968a", edgecolor="#6d685e", lw=0.3))
            coast.boundary.plot(ax=ax, color="k", lw=0.5)
            ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3])
            ax.set_title(f"{title}, mesh {key}: {len(dry)} faces at or above 0 m", fontsize=10, loc="left")
            ax.tick_params(labelsize=8)
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(-20, 0))
    fig.colorbar(sm, ax=axes, shrink=0.6, label="face bed level, m")
    fig.savefig(FIGURE, dpi=130, facecolor="white", bbox_inches="tight")
    print(f"figure written to {FIGURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
