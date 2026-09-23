"""Size the model domain, the horizontal resolution and the vertical layering.

The exercise answers three questions that have to be settled before a mesh is
built, and settles them from the bathymetry rather than from rules of thumb.

Where does the seiche energy come from, and therefore how far offshore must the
domain reach. Quarter-wave periods are computed for the harbours, for their
inlets and for the Malta Plateau. The harbours and inlets resonate well above
the observed milghuba band of 0.2 to 2 cph, whereas the plateau resonates
inside it. The harbours therefore respond to a shelf-scale oscillation rather
than generating one, and a domain that excludes the shelf has no mechanism to
produce the signal under study.

What resolution the interior requires. Channel width is measured along the
ridge of the distance transform of the water mask, which is where the distance
to land equals the local half-width. The distribution of that width, not a
nominal figure, sets the cell size.

How many layers. Driven by the flushing and residence-time question rather than
by the seiche, which is barotropic. Layer thicknesses are reported against the
measured depth distribution so that the choice can be seen rather than asserted.

Usage:
    python domain_design_estimate.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BATHY = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84.tif"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
SHELF = ROOT / "data" / "external" / "emodnet_shelf.tif"

G = 9.81
MILGHUBA = (0.2, 2.0)          # cycles per hour, Drago 2009

HARBOURS = {
    "Grand Harbour": (14.502, 35.880, 14.528, 35.900),
    "Marsamxett": (14.490, 35.892, 14.518, 35.909),
}

# Candidate domains, as lon0, lat0, lon1, lat1.
DOMAINS = {
    "A, harbours and approaches": (14.44, 35.83, 14.62, 35.97),
    "B, Malta and the near plateau": (14.05, 35.70, 15.00, 36.30),
    "C, plateau to Sicily": (13.90, 35.60, 15.30, 36.75),
}

# Resolution zones, as a target cell size against distance from the harbours.
# The transition ratio between neighbouring cells is held near 1.25, which is
# what inflates the count beyond the naive area division.
ZONES = [
    ("inlets and entrances, width below 150 m", 15.0),
    ("harbour basins", 30.0),
    ("nearshore, within 2 km", 100.0),
    ("coastal, 2 to 15 km", 300.0),
    ("open shelf, beyond 15 km", 1500.0),
]
TRANSITION_OVERHEAD = 1.5


def quarter_wave(length_m: float, depth_m: float, n: int = 4) -> tuple[float, float]:
    """Period and frequency of a resonator open at one end, or at both for n=2."""
    celerity = math.sqrt(G * depth_m)
    period = n * length_m / celerity
    return period, 3600.0 / period


def in_band(cph: float) -> str:
    return "within" if MILGHUBA[0] <= cph <= MILGHUBA[1] else "outside"


def load_harbour_grids():
    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds
    from scipy.ndimage import distance_transform_edt, label, maximum_filter

    src = rasterio.open(BATHY)
    window = (14.488, 35.872, 14.545, 35.915)
    w = from_bounds(*window, transform=src.transform)
    t = rasterio.windows.transform(w, src.transform)
    z = src.read(1, window=w).astype(float)

    coast = gpd.read_file(COAST)
    land = rasterize(((g, 1) for g in coast.geometry), out_shape=z.shape,
                     transform=t, fill=0, dtype="uint8").astype(bool)
    wet = (~land) & np.isfinite(z) & (z < 0)
    lab, _ = label(wet)
    wet = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)

    mid = (window[1] + window[3]) / 2
    cx = abs(t.a) * 111320 * math.cos(math.radians(mid))
    cy = abs(t.e) * 110570

    dt = distance_transform_edt(wet, sampling=(cy, cx))
    # The ridge of the distance transform is where distance to land equals the
    # local half-width, so twice the distance there is the channel width.
    ridge = wet & (dt >= maximum_filter(dt, size=3) - 1e-9) & (dt > (cx + cy) / 2)
    return z, t, wet, dt * 2, ridge, cx, cy


def main(argv=None) -> int:
    for p in (BATHY, COAST):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 1

    z, t, wet, width, ridge, cx, cy = load_harbour_grids()
    cell_area = cx * cy

    print("=" * 74)
    print("1. BASIN GEOMETRY")
    print("=" * 74)
    geom = {}
    for name, (a, b, c, d) in HARBOURS.items():
        r0, c0 = ~t * (a, d)
        r1, c1 = ~t * (c, b)
        c0, r0, c1, r1 = int(c0), int(r0), int(c1), int(r1)
        sub = wet[r0:r1, c0:c1]
        zz = z[r0:r1, c0:c1][sub]
        ww = width[r0:r1, c0:c1][ridge[r0:r1, c0:c1]]
        mid = (b + d) / 2
        L = math.hypot((c - a) * 111320 * math.cos(math.radians(mid)),
                       (d - b) * 110570)
        h = float(-zz.mean())
        geom[name] = dict(area=sub.sum() * cell_area, depth=h, length=L,
                          volume=float((-zz).sum() * cell_area), widths=ww)
        print(f"\n{name}")
        print(f"  area        {sub.sum() * cell_area / 1e6:6.2f} km2")
        print(f"  volume      {(-zz).sum() * cell_area / 1e6:6.1f} x10^6 m3")
        print(f"  depth       mean {h:4.1f} m, median {-np.median(zz):4.1f}, max {-zz.min():4.1f}")
        print(f"  axis length {L / 1000:6.2f} km")
        print("  channel width on the ridge, percentiles")
        print("    " + "  ".join(f"p{q}={np.percentile(ww, q):.0f}" for q in (10, 25, 50, 75, 90)))

    print("\n" + "=" * 74)
    print("2. RESONANT PERIODS AGAINST THE OBSERVED BAND")
    print("=" * 74)
    print(f"  milghuba band {MILGHUBA[0]} to {MILGHUBA[1]} cph, "
          f"periods {60 / MILGHUBA[1]:.0f} min to {60 / MILGHUBA[0]:.0f} min\n")
    rows = [("Malta Plateau to Sicily, quarter wave", 90000, 150, 4),
            ("Malta Plateau to Sicily, half wave", 90000, 150, 2),
            ("Near plateau, 25 km", 25000, 120, 4)]
    for name, g in geom.items():
        rows.append((name, g["length"], g["depth"], 4))
    rows += [("A typical inlet, 1 km", 1000, 12, 4),
             ("A short inlet, 600 m", 600, 10, 4)]
    for name, L, h, n in rows:
        T, f = quarter_wave(L, h, n)
        print(f"  {name:38s} L={L / 1000:5.1f} km  h={h:5.0f} m  "
              f"T={T / 60:6.1f} min  {f:5.2f} cph  {in_band(f)}")

    print("\n  The harbours and their inlets resonate above the band. The plateau")
    print("  resonates inside it. The forcing is therefore shelf-scale and the")
    print("  harbours respond to it rather than generating it.")

    print("\n" + "=" * 74)
    print("3. HORIZONTAL RESOLUTION")
    print("=" * 74)
    print("\n  Cells across a channel, by channel width and cell size")
    header = "    width".ljust(12) + "".join(f"{d:>9.0f} m" for _, d in ZONES[:3])
    print(header)
    for wv in (50, 75, 100, 150, 200, 300):
        line = f"    {wv:>4d} m   "
        for _, dx in ZONES[:3]:
            line += f"{wv / dx:>9.1f}  "
        print(line)
    print("\n  Four to five cells carry the conveyance of a channel, eight to ten")
    print("  resolve the flow across it.")

    for name, g in geom.items():
        ww = g["widths"]
        print(f"\n  {name}, fraction of channel length narrower than")
        for thr in (50, 100, 150, 200, 300):
            print(f"    {thr:3d} m : {100 * np.mean(ww < thr):5.1f}%")

    print("\n" + "=" * 74)
    print("4. MESH SIZE AND TIME STEP")
    print("=" * 74)
    harbour_area = sum(g["area"] for g in geom.values())
    narrow_frac = np.mean(np.concatenate([g["widths"] for g in geom.values()]) < 150)
    areas = {
        ZONES[0][0]: harbour_area * narrow_frac,
        ZONES[1][0]: harbour_area * (1 - narrow_frac),
        ZONES[2][0]: 60e6,
        ZONES[3][0]: 350e6,
        ZONES[4][0]: None,
    }
    print(f"\n  narrow fraction of the harbours, width below 150 m: {100 * narrow_frac:.0f}%\n")
    for label_, (lon0, lat0, lon1, lat1) in DOMAINS.items():
        midlat = (lat0 + lat1) / 2
        w_km = (lon1 - lon0) * 111.320 * math.cos(math.radians(midlat))
        h_km = (lat1 - lat0) * 110.570
        total = w_km * h_km * 1e6
        shelf = max(total - 410e6 - harbour_area, 0.0) * 0.75   # 0.75 allows for land
        cells = 0.0
        for zone, dx in ZONES:
            a = shelf if areas[zone] is None else areas[zone]
            cells += a / (dx * dx)
        cells *= TRANSITION_OVERHEAD
        # A quarter-wave resonator of this along-shelf extent
        Ls = max(w_km, h_km) * 1000
        T, f = quarter_wave(Ls, 150)
        print(f"  {label_}")
        print(f"    extent      {w_km:.0f} x {h_km:.0f} km, {total / 1e6:.0f} km2")
        print(f"    cells       approximately {cells:,.0f}")
        print(f"    longest resonator it can hold: {T / 60:.0f} min, {f:.2f} cph, {in_band(f)}")

    dx_min = ZONES[0][1]
    for h in (15.0, 20.0):
        c = math.sqrt(G * h)
        print(f"\n  At {dx_min:.0f} m cells in {h:.0f} m of water, celerity {c:.1f} m/s,")
        print(f"    Courant 1 needs dt = {dx_min / c:.1f} s; the implicit solver tolerates")
        print(f"    Courant 5 to 10, so dt = {5 * dx_min / c:.0f} to {10 * dx_min / c:.0f} s.")

    print("\n" + "=" * 74)
    print("5. VERTICAL LAYERS")
    print("=" * 74)
    zz = -z[wet]
    print("\n  Depth distribution over the water of the harbour window")
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 30), (30, 50), (50, 100)):
        m = (zz >= lo) & (zz < hi)
        if m.any():
            print(f"    {lo:3d} to {hi:3d} m : {100 * m.mean():5.1f}%")
    print(f"    median {np.median(zz):.0f} m, p90 {np.percentile(zz, 90):.0f} m")

    print("\n  Uniform sigma layer thickness, by layer count and depth")
    depths = [13, 16, 30, 100, 150]
    print("    layers   " + "".join(f"{d:>8d} m" for d in depths))
    for n in (8, 10, 12, 15, 20):
        print(f"    {n:>6d}   " + "".join(f"{d / n:>8.2f}  " for d in depths))
    print("\n  A near-bed layer of roughly 1 m in the harbours is the target for the")
    print("  flushing question. Stretching toward the bed and the surface reaches it")
    print("  at a lower count than a uniform distribution does.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
