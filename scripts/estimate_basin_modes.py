"""Fundamental long-wave mode of the two harbours from the measured geometry.

The sizing document bracketed the basin period with two idealisations, a
quarter-wave resonator and a Helmholtz resonator, both built on nominal
dimensions and on an unobstructed 400 m mouth. The Grand Harbour entrance is in
fact partly closed by the 1910 St Elmo breakwater, and the Helmholtz figure was
to be recomputed once the geometry of the mouth could be measured.

This script replaces both idealisations by the one-dimensional long-wave
eigenproblem of a channel of varying section (the Webster equation),

    g d/dx( a(x) d(eta)/dx ) + omega^2 b(x) eta = 0,

with eta = 0 at the mouth and no flux at the head. The quarter-wave resonator is
its uniform-channel limit and the Helmholtz resonator its limit for a narrow
neck ahead of a wide basin, so the choice between the two no longer arises.

The coordinate x is the geodesic distance through the water from the mouth,
computed by Dijkstra on the 8-connected grid of wet cells. The surface width
b(x) = dA/dx and the cross-section a(x) = dV/dx follow from the area and the
volume enclosed within each distance, so branching inlets at a common distance
are summed, which treats them as oscillating in phase. That assumption holds
for the fundamental mode and fails for the higher ones, which are therefore not
reported.

Geometry comes from the aligned working pair in EPSG:4326, the same inputs from
which the mesh will be interpolated. The breakwater variant fills the detached
polygon with water at the depth of its neighbours, which isolates the effect of
the structure from every other element of the geometry.

Radiation through the mouth is represented by the length correction of
Rabinovich (2009, eq. 9.16), which is derived for a fully open rectangular
basin and is here applied at the seaward section line. Periods are reported
with and without it, since for a partly closed entrance it is an approximation.

Usage:
    python estimate_basin_modes.py [--figure]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BATHY = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84.tif"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
FIGURE = ROOT / "figures" / "basin_modes.png"

G = 9.81
EULER_GAMMA = 0.5772156649
MILGHUBA = (0.2, 2.0)           # cycles per hour, Drago (2009)
WINDOW = (14.488, 35.872, 14.545, 35.915)
# Distance bin for a(x) and b(x). At 10 m the chamfer steps of the 8-connected
# distance alias into a comb of spurious oscillations in a(x) near the mouth,
# and 25 m removes it. The period is reported at 10 and 50 m as well.
BIN = 25.0
BIN_SENSITIVITY = (10.0, 50.0)
MOUTH_ZONE = 600.0              # m, extent over which the neck section is sought

# The detached polygon identified as the St Elmo breakwater in
# docs/domain_and_discretisation.md, located by its bounds.
BREAKWATER_BOUNDS = (14.5211, 35.9026, 14.5253, 35.9033)

# Section lines closing each harbour from the sea, as lon, lat vertices. Two
# lines are carried for the Grand Harbour. The outer line encloses the
# breakwater so that the restriction appears inside the computed section, and
# the inner line runs across the opening between the breakwater head and the
# Ricasoli shore, which is the narrowest section. Their difference measures the
# sensitivity to a choice that the one-dimensional reduction cannot make.
#
# Both ends of every line lie inside land, so that the line closes the basin
# whether or not the breakwater is present. The inner Grand Harbour line runs
# along the breakwater axis, and where the breakwater is removed it therefore
# closes the full entrance between St Elmo and Ricasoli.
BASINS = {
    "Grand Harbour": dict(
        interior=(14.515, 35.893),
        mouths={
            "outer": [(14.5185, 35.9025), (14.5188, 35.9042), (14.5268, 35.9040),
                      (14.5290, 35.8985), (14.5265, 35.8980)],
            "inner": [(14.5200, 35.9022), (14.5215, 35.9030), (14.5250, 35.9030),
                      (14.5236, 35.8992), (14.5240, 35.8983)],
        },
    ),
    "Marsamxett": dict(
        interior=(14.505, 35.900),
        mouths={
            "outer": [(14.5130, 35.9062), (14.5145, 35.9052), (14.5178, 35.9040),
                      (14.5185, 35.9028)],
            "inner": [(14.5120, 35.9062), (14.5150, 35.9018)],
        },
    ),
}
MAX_BASIN_AREA = 4.0e6          # m2, a larger component means the line leaks


def load_window():
    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds

    src = rasterio.open(BATHY)
    w = from_bounds(*WINDOW, transform=src.transform)
    t = rasterio.windows.transform(w, src.transform)
    z = src.read(1, window=w).astype(float)
    if src.nodata is not None:
        z[z == src.nodata] = np.nan

    coast = gpd.read_file(COAST)
    bw = coast.cx[BREAKWATER_BOUNDS[0]:BREAKWATER_BOUNDS[2],
                  BREAKWATER_BOUNDS[1]:BREAKWATER_BOUNDS[3]]
    # The mainland polygon also intersects the box, and is excluded by extent.
    b = bw.geometry.bounds
    bw = bw[(b.maxx - b.minx) < 0.01]
    if len(bw) != 1:
        raise RuntimeError(f"expected one breakwater polygon, found {len(bw)}")

    def burn(geoms):
        return rasterize(((g, 1) for g in geoms), out_shape=z.shape, transform=t,
                         fill=0, dtype="uint8", all_touched=False).astype(bool)

    land = burn(coast.geometry)
    breakwater = burn(bw.geometry)

    mid = (WINDOW[1] + WINDOW[3]) / 2
    cx = abs(t.a) * 111320 * math.cos(math.radians(mid))
    cy = abs(t.e) * 110570
    return z, t, land, breakwater, cx, cy


def fill_breakwater_depth(z, land, breakwater):
    """Depth under the breakwater footprint, from the nearest wet neighbours."""
    from scipy.ndimage import distance_transform_edt

    z = z.copy()
    good = (~land) & np.isfinite(z) & (z < 0)
    _, (ri, ci) = distance_transform_edt(~good, return_indices=True)
    z[breakwater] = z[ri[breakwater], ci[breakwater]]
    return z


def rasterize_line(vertices, t, shape):
    from rasterio.features import rasterize
    from shapely.geometry import LineString

    return rasterize([(LineString(vertices), 1)], out_shape=shape, transform=t,
                     fill=0, dtype="uint8", all_touched=True).astype(bool)


def geodesic_distance(wet, seeds, cx, cy):
    """Distance through the water from the seed cells, 8-connected Dijkstra."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra

    idx = -np.ones(wet.shape, dtype=np.int64)
    idx[wet] = np.arange(wet.sum())
    rows, cols, wts = [], [], []
    ny, nx = wet.shape
    for di, dj in ((0, 1), (1, 0), (1, 1), (1, -1)):
        step = math.hypot(di * cy, dj * cx)
        # di is never negative, so only the column offset changes sign.
        a = idx[0:ny - di, max(0, -dj):nx - max(0, dj)]
        b = idx[di:ny, max(0, dj):nx - max(0, -dj)]
        m = (a >= 0) & (b >= 0)
        rows.append(a[m]); cols.append(b[m]); wts.append(np.full(m.sum(), step))
    n = int(wet.sum())
    graph = coo_matrix((np.concatenate(wts), (np.concatenate(rows),
                        np.concatenate(cols))), shape=(n, n)).tocsr()
    d = dijkstra(graph, directed=False, indices=idx[seeds], min_only=True)
    out = np.full(wet.shape, np.nan)
    out[wet] = d
    return out


def basin_profile(z, land, t, cx, cy, interior, mouth):
    """Surface width b(x), section a(x) and bin centres for one basin."""
    from scipy.ndimage import binary_dilation, label

    # Three cells thick, so that no diagonal step of the 8-connected graph
    # crosses it.
    line = binary_dilation(rasterize_line(mouth, t, z.shape), structure=np.ones((3, 3)))
    wet = (~land) & np.isfinite(z) & (z < 0) & (~line)
    lab, _ = label(wet, structure=np.ones((3, 3)))
    r, c = ~t * interior
    basin = lab == lab[int(r), int(c)]
    cell = cx * cy
    if basin.sum() * cell > MAX_BASIN_AREA:
        raise RuntimeError(f"section line does not close the basin, "
                           f"{basin.sum() * cell / 1e6:.2f} km2 connected")
    seeds = basin & binary_dilation(line, structure=np.ones((3, 3)))
    if not seeds.any():
        raise RuntimeError("no wet cell adjoins the section line")
    dist = geodesic_distance(basin, seeds, cx, cy)

    x = dist[basin]
    depth = -z[basin]
    # Open width of the section, the part of the line crossing water.
    on_line = rasterize_line(mouth, t, z.shape)
    open_cells = on_line & (~land) & np.isfinite(z) & (z < 0)
    frac = open_cells.sum() / max(on_line.sum(), 1)
    geom = dict(area=float(basin.sum() * cell), volume=float((depth * cell).sum()),
                length=float(x.max()), mouth_width=mouth_length(mouth) * frac,
                mouth_depth=float(np.mean(depth[x < 30.0])), dist=dist,
                x=x, depth=depth, cell=cell)
    return geom


def bin_profile(geom, bin_m=BIN):
    """Surface width b = dA/dx and section a = dV/dx on bins of the given size."""
    x, depth, cell = geom["x"], geom["depth"], geom["cell"]
    edges = np.arange(0.0, x.max() + bin_m, bin_m)
    area, _ = np.histogram(x, edges, weights=np.full(x.size, cell))
    vol, _ = np.histogram(x, edges, weights=depth * cell)
    centres = 0.5 * (edges[1:] + edges[:-1])
    keep = area > 0
    return centres[keep], area[keep] / bin_m, vol[keep] / bin_m


def mouth_length(vertices) -> float:
    """Length of a lon, lat polyline in metres, by local scaling."""
    total = 0.0
    for (x0, y0), (x1, y1) in zip(vertices[:-1], vertices[1:]):
        mid = math.radians((y0 + y1) / 2)
        total += math.hypot((x1 - x0) * 111320 * math.cos(mid), (y1 - y0) * 110570)
    return total


def webster_modes(b, a, dx, extension=0.0, n_modes=1):
    """Eigenperiods of g (a eta')' + w^2 b eta = 0, eta(0) = 0, a eta'(L) = 0.

    Finite volumes on a staggered grid. Levels sit at cell centres and fluxes at
    faces. A uniform extension of the first section, of the given length, is
    prepended to carry the mouth correction.
    """
    from scipy.linalg import eigh

    if extension > 0:
        n_ext = max(1, int(round(extension / dx)))
        b = np.concatenate([np.full(n_ext, b[0]), b])
        a = np.concatenate([np.full(n_ext, a[0]), a])
    n = b.size
    # Face sections, harmonic in the interior, the first section at the mouth.
    af = np.empty(n)
    af[0] = a[0]
    af[1:] = 2 * a[1:] * a[:-1] / (a[1:] + a[:-1])
    K = np.zeros((n, n))
    for i in range(n):
        # Mouth face, level held at zero half a cell seaward.
        k_left = G * af[i] / (dx if i else dx / 2)
        K[i, i] += k_left
        if i:
            K[i, i - 1] -= k_left
            K[i - 1, i] -= k_left
            K[i - 1, i - 1] += k_left
    M = np.diag(b * dx)
    w2 = eigh(K, M, eigvals_only=True, subset_by_index=[0, n_modes - 1])
    return 2 * math.pi / np.sqrt(w2)


def mouth_correction(width, period, depth):
    """Rabinovich (2009) eq. 9.16 as a length, with lambda = 4 L."""
    wavelength = math.sqrt(G * depth) * period
    return (width / math.pi) * (1.5 - EULER_GAMMA - math.log(math.pi * width / wavelength))


def period_with_correction(b, a, geom, bin_m=BIN):
    t0 = webster_modes(b, a, bin_m)[0]
    t = t0
    for _ in range(20):
        dl = mouth_correction(geom["mouth_width"], t, geom["mouth_depth"])
        t_new = webster_modes(b, a, bin_m, extension=dl)[0]
        if abs(t_new - t) < 0.1:
            break
        t = t_new
    return t0, t_new, dl


def self_test() -> None:
    """A uniform channel must return the quarter-wave period 4L/sqrt(gh)."""
    L, h, w = 3000.0, 15.0, 300.0
    n = int(L / BIN)
    t = webster_modes(np.full(n, w), np.full(n, w * h), BIN)[0]
    expected = 4 * L / math.sqrt(G * h)
    if abs(t / expected - 1) > 5e-3:
        raise AssertionError(f"uniform channel {t:.1f} s against {expected:.1f} s")


def cph(period_s: float) -> float:
    return 3600.0 / period_s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    for p in (BATHY, COAST):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 1

    self_test()
    z, t, land, breakwater, cx, cy = load_window()
    z_open = fill_breakwater_depth(z, land, breakwater)
    land_open = land & ~breakwater
    print(f"breakwater footprint {breakwater.sum()} cells, "
          f"{breakwater.sum() * cx * cy:.0f} m2, filled depth "
          f"{-np.median(z_open[breakwater]):.1f} m median")
    print()

    print("T0 is the period with the level node on the section line, T adds the")
    print("mouth correction dl. a_neck is the smallest section within "
          f"{MOUTH_ZONE:.0f} m of the line,")
    print("a_med the median section over the basin.\n")
    header = (f"{'basin':14s} {'mouth':6s} {'variant':13s} {'area':>5s} {'L':>5s} "
              f"{'width':>6s} {'a_neck':>7s} {'a_med':>6s} {'T0':>5s} {'dl':>5s} "
              f"{'T':>5s} {'f':>5s}")
    print(header)
    print(f"{'':14s} {'':6s} {'':13s} {'km2':>5s} {'km':>5s} {'m':>6s} "
          f"{'m2':>7s} {'m2':>6s} {'min':>5s} {'m':>5s} {'min':>5s} {'cph':>5s}")
    profiles = {}
    for name, spec in BASINS.items():
        for mouth_name, mouth in spec["mouths"].items():
            variants = [("as supplied", z, land)]
            if name == "Grand Harbour":
                variants.append(("no breakwater", z_open, land_open))
            for variant, zz, ll in variants:
                geom = basin_profile(zz, ll, t, cx, cy, spec["interior"], mouth)
                x, b, a = bin_profile(geom)
                t0, tc, dl = period_with_correction(b, a, geom)
                neck = float(a[x < MOUTH_ZONE].min())
                profiles[(name, mouth_name, variant)] = (x, b, a, geom["dist"])
                print(f"{name:14s} {mouth_name:6s} {variant:13s} "
                      f"{geom['area'] / 1e6:5.2f} {geom['length'] / 1e3:5.2f} "
                      f"{geom['mouth_width']:6.0f} {neck:7.0f} {np.median(a):6.0f} "
                      f"{t0 / 60:5.1f} {dl:5.0f} {tc / 60:5.1f} {cph(tc):5.2f}")
                if mouth_name == "outer" and variant == "as supplied":
                    sens = []
                    for bin_m in BIN_SENSITIVITY:
                        xs, bs, as_ = bin_profile(geom, bin_m)
                        sens.append(f"{webster_modes(bs, as_, bin_m)[0] / 60:.1f} min "
                                    f"at {bin_m:.0f} m")
                    print(f"{'':36s}T0 by distance bin: " + ", ".join(sens))
    print()

    # A local restriction of the entrance, imposed on the measured profile over
    # a reach centred on the narrowest section. The Helmholtz scaling used in
    # estimate_entrance_restriction.py predicts T ~ (open fraction)^-1/2
    # whatever the length of the reach, which holds only where the neck carries
    # the whole inertia of the system.
    geom = basin_profile(z, land, t, cx, cy, BASINS["Grand Harbour"]["interior"],
                         BASINS["Grand Harbour"]["mouths"]["outer"])
    x, b, a = bin_profile(geom)
    x_neck = x[x < MOUTH_ZONE][np.argmin(a[x < MOUTH_ZONE])]
    t_ref = webster_modes(b, a, BIN)[0]
    print(f"Grand Harbour, restriction of the section over a reach centred at "
          f"x = {x_neck:.0f} m (T0 = {t_ref / 60:.1f} min)")
    print(f"  {'open fraction':>13s} {'Helmholtz':>10s} " +
          " ".join(f"{f'{r:.0f} m reach':>12s}" for r in (100, 250, 500)))
    for frac in (0.75, 0.50, 0.25, 0.10):
        row = f"  {frac:>13.2f} {1 / math.sqrt(frac) - 1:>+10.0%} "
        for reach in (100.0, 250.0, 500.0):
            ar = a.copy()
            ar[np.abs(x - x_neck) <= reach / 2] *= frac
            row += f"{webster_modes(b, ar, BIN)[0] / t_ref - 1:>+12.1%} "
        print(row)
    print()

    # Sea level rise on the same profiles, for a like-for-like comparison with
    # the restriction. Quay walls are taken as vertical, so the surface width is
    # unchanged and the section gains b(x) times the rise.
    print("Sea level rise on the same profiles, vertical walls")
    print(f"  {'basin':14s} " + " ".join(f"{f'+{s:.1f} m':>8s}" for s in (0.3, 0.5, 1.0)))
    for name, spec in BASINS.items():
        geom = basin_profile(z, land, t, cx, cy, spec["interior"], spec["mouths"]["outer"])
        x, b, a = bin_profile(geom)
        t_ref = webster_modes(b, a, BIN)[0]
        shifts = [webster_modes(b, a + b * s, BIN)[0] / t_ref - 1 for s in (0.3, 0.5, 1.0)]
        print(f"  {name:14s} " + " ".join(f"{v:>+8.1%}" for v in shifts))
    print()
    print(f"milghuba band {MILGHUBA[0]} to {MILGHUBA[1]} cph, "
          f"periods {60 / MILGHUBA[1]:.0f} to {60 / MILGHUBA[0]:.0f} min")

    if args.figure:
        plot_profiles(profiles, t, land, z.shape)
    return 0


def plot_profiles(profiles, t, land, shape) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ext = (t.c, t.c + t.a * shape[1], t.f + t.e * shape[0], t.f)
    fig = plt.figure(figsize=(11, 9))
    ax_map = fig.add_subplot(2, 1, 1)
    ax_map.imshow(np.where(land, 0.3, np.nan), extent=ext, cmap="Greys", vmin=0, vmax=1)
    for name, spec in BASINS.items():
        dist = profiles[(name, "outer", "as supplied")][3]
        im = ax_map.imshow(dist, extent=ext, cmap="viridis", vmin=0, vmax=4200)
        for mouth_name, mouth in spec["mouths"].items():
            xs, ys = zip(*mouth)
            ax_map.plot(xs, ys, "r-" if mouth_name == "outer" else "m--", lw=1)
    ax_map.set_xlim(14.495, 14.535)
    ax_map.set_ylim(35.875, 35.912)
    ax_map.set_aspect(1 / math.cos(math.radians(35.89)))
    fig.colorbar(im, ax=ax_map, label="geodesic distance from the outer line, m", shrink=0.8)

    for j, name in enumerate(BASINS):
        ax = fig.add_subplot(2, 2, 3 + j)
        for (n, mouth, variant), (x, b, a, _) in profiles.items():
            if n != name or mouth != "outer":
                continue
            ls = "-" if variant == "as supplied" else "--"
            ax.plot(x, a, ls, lw=1, label=f"a(x), {variant}")
        ax.set_title(f"{name}, outer section line", fontsize=10)
        ax.set_ylabel("cross-section a(x), m²")
        ax.set_xlabel("geodesic distance from the mouth, m")
        ax.legend(frameon=False, fontsize=8)
        ax.grid(lw=0.3)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150)
    print(f"figure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())
