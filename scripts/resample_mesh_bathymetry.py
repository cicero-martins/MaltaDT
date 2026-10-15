"""Resample the node bed levels of an existing mesh on the cleaned harbour field.

The geometry of the mesh is kept and only mesh2d_node_z changes. Each node takes
the bilinear sample of the field written by clean_harbour_bathymetry.py for
sampling, in which pontoon and vessel returns are replaced by interpolated bed
levels and land cells beside water carry the bed of the nearest water cell.
Where that field has no value, outside the MEPA coverage, the node keeps the
level it had, so that the EMODnet levels offshore and the minimum depth of the
outer domain are unchanged.

Usage:
    python resample_mesh_bathymetry.py --mesh v02 --out v02b
    python resample_mesh_bathymetry.py --mesh outer01 --out outer01b
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_mesh_v02 as v2  # noqa: E402
import clean_harbour_bathymetry as cb  # noqa: E402

ROOT = v2.ROOT
PROCESSED = ROOT / "data" / "processed"
REPORT_BOX = cb.HARBOUR_BOX


def main(argv=None) -> int:
    import xugrid as xu

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    src_dir, out_dir = PROCESSED / f"mesh_{args.mesh}", PROCESSED / f"mesh_{args.out}"
    src_net = src_dir / f"malta_{args.mesh}_net.nc"
    uds = xu.open_dataset(src_net)
    grid = uds.grid
    old = uds["mesh2d_node_z"].values.astype(float)
    new = v2.sample_raster(cb.OUT_MESH, grid.node_x, grid.node_y)
    z = np.where(np.isfinite(new), new, old)

    out_dir.mkdir(parents=True, exist_ok=True)
    uds = uds.load()
    uds["mesh2d_node_z"] = (grid.node_dimension, z)
    uds["mesh2d_node_z"].attrs.update(standard_name="altitude", long_name="bed level at nodes",
                                      units="m", mesh="mesh2d", location="node")
    net = out_dir / f"malta_{args.out}_net.nc"
    uds.ugrid.to_netcdf(net)
    uds.close()
    for f in src_dir.glob(f"malta_{args.mesh}_bnd.pli"):
        text = f.read_text().replace(f"malta_{args.mesh}_bnd", f"malta_{args.out}_bnd", 1)
        (out_dir / f"malta_{args.out}_bnd.pli").write_text(text)

    fn = grid.face_node_connectivity
    def face_mean(v):
        return np.array([v[r[r >= 0]].mean() for r in fn])
    fo, fz = face_mean(old), face_mean(z)
    b = REPORT_BOX
    inb = (grid.face_x > b[0]) & (grid.face_x < b[2]) & (grid.face_y > b[1]) & (grid.face_y < b[3])
    changed = np.isfinite(new) & (np.abs(z - old) > 0.01)
    print(f"{args.mesh} -> {args.out}: {grid.n_node} nodes, {changed.sum()} changed by more than 1 cm")
    print(f"  harbour faces {inb.sum()}: mean bed at or above 0 m before {(inb & (fo >= 0)).sum()}, "
          f"after {(inb & (fz >= 0)).sum()}")
    d = (fz - fo)[inb]
    print(f"  harbour face level change: median {np.median(d):+.2f} m, 5 to 95 per cent "
          f"{np.percentile(d, 5):+.2f} to {np.percentile(d, 95):+.2f} m")
    outside = ~inb
    print(f"  faces outside the harbours changed by more than 0.5 m: "
          f"{(outside & (np.abs(fz - fo) > 0.5)).sum()} of {outside.sum()}")
    print(f"written {net}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
