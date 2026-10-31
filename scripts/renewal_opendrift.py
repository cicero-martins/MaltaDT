"""Renewal of the Valletta harbours by particles released in the 3D currents of a hindcast.

Particles fill the water column of each harbour at the start of the window and
are advected by OpenDrift (OceanDrift) in the horizontal 3D currents written
by extract_harbour_currents_3d.py, with a random walk for the vertical mixing.
The vertical velocity of FM is left out by default. Interpolated from the
sigma layers onto a 40 m grid at fixed depths it is no longer consistent with
the horizontal components, and in a test of 6 h it carried a tenth of the
particles to the surface, where they remain wherever it is upward and are then
held against the shore by the surface current, some 97 per cent of those still
in the harbours after 4 days. The fraction remaining in the harbour of release, r(t),
gives the e-folding time tau at which r falls to 1/e and the mean residence
time theta = integral of r dt after Takeoka (1984), truncated at the end of the
window. Particles that leave and return are counted again on return.

Each particle stands for the volume of its share of the column, the column
being divided into N_LEVELS equal parts of a grid cell of fixed area, so that
r(t) is a fraction of the volume of the harbour.

The vertical diffusivity is not in the map output of the hindcast and is
prescribed as a constant, a working value run at the two bounds given by
--kz. The horizontal diffusivity is a working value for the motions below the
grid of some 40 m.

Usage:
    python renewal_opendrift.py v03_3d20s_0722_0801_uv_thd [--kz 1e-4 1e-2]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.path import Path as MplPath

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "model" / "hindcast"
OUT = ROOT / "outputs" / "renewal"

# Each polygon closes its harbour at the mouth and runs over land elsewhere,
# the Valletta and Floriana ridge dividing the two. Only wet grid points are
# seeded, so the course of a polygon over land is immaterial.
HARBOURS = {
    "Grand Harbour": [(14.5195, 35.9022), (14.5262, 35.8990), (14.5300, 35.8900),
                      (14.5200, 35.8760), (14.4950, 35.8740), (14.4880, 35.8830),
                      (14.4930, 35.8875), (14.5030, 35.8925), (14.5110, 35.8975)],
    "Marsamxett": [(14.5195, 35.9022), (14.5160, 35.9080), (14.5100, 35.9110),
                   (14.4950, 35.9080), (14.4860, 35.9000), (14.4880, 35.8900),
                   (14.4930, 35.8875), (14.5030, 35.8925), (14.5110, 35.8975)],
}
N_LEVELS = 5                      # particles per column, at the centres of equal parts
MIN_DEPTH = 1.0                   # m, columns shallower than this are not seeded
HORIZONTAL_DIFFUSIVITY = 0.1      # m2/s, working value
TIME_STEP = 300                   # s
VERTICAL_STEP = 60                # s, random walk of the mixing


def seeds(currents: xr.Dataset):
    """Positions, depths, volume weights and harbour of each particle."""
    L, A = np.meshgrid(currents.lon.values, currents.lat.values)
    H = currents.sea_floor_depth_below_sea_level.values
    wet = (currents.land_binary_mask.values == 0) & (H >= MIN_DEPTH)
    lon, lat, z, w, harbour = [], [], [], [], []
    for n, (name, poly) in enumerate(HARBOURS.items()):
        inside = MplPath(poly).contains_points(np.c_[L.ravel(), A.ravel()]).reshape(L.shape) & wet
        for f in (np.arange(N_LEVELS) + 0.5) / N_LEVELS:
            lon.append(L[inside]); lat.append(A[inside])
            z.append(-f * H[inside]); w.append(H[inside] / N_LEVELS)
            harbour.append(np.full(inside.sum(), n))
        print(f"{name}: {inside.sum()} columns, volume {H[inside].sum() * 0.0016:.2f} hm3 at 40 m")
    return [np.concatenate(a) for a in (lon, lat, z, w, harbour)]


def run(path: Path, kz: float, out: Path, vertical_advection: bool = False) -> Path:
    from opendrift.models.oceandrift import OceanDrift
    from opendrift.readers import reader_netCDF_CF_generic

    currents = xr.open_dataset(path)
    lon, lat, z, w, harbour = seeds(currents)
    start = pd.Timestamp(currents.time.values[0]).to_pydatetime()
    stop = pd.Timestamp(currents.time.values[-1]).to_pydatetime()
    o = OceanDrift(loglevel=30)
    o.add_reader(reader_netCDF_CF_generic.Reader(str(path)))
    for key, value in {"general:use_auto_landmask": False,
                       "general:coastline_action": "previous",
                       "general:seafloor_action": "previous",
                       "drift:advection_scheme": "runge-kutta4",
                       "drift:vertical_advection": vertical_advection,
                       "drift:vertical_mixing": kz > 0,
                       # OpenDrift 1.14 reads both diffusivities as environment
                       # variables and accepts drift:horizontal_diffusivity
                       # without applying it; the fallback of the vertical one
                       # does not reach the profile used by the mixing
                       "environment:constant:horizontal_diffusivity": HORIZONTAL_DIFFUSIVITY,
                       "vertical_mixing:diffusivitymodel": "environment",
                       "vertical_mixing:timestep": VERTICAL_STEP,
                       "environment:constant:ocean_vertical_diffusivity": kz,
                       "seed:wind_drift_factor": 0.0}.items():
        o.set_config(key, value)
    o.seed_elements(lon=lon, lat=lat, z=z, time=start, wind_drift_factor=0.0)
    path_out = out / f"particles_kz{kz:.0e}.nc"
    o.run(end_time=stop - timedelta(seconds=TIME_STEP), time_step=TIME_STEP,
          time_step_output=3600, outfile=str(path_out), export_variables=["lon", "lat", "z"])
    np.savez(out / "seeds.npz", w=w, harbour=harbour)
    return path_out


def remaining(particles: Path, seeds_file: Path) -> pd.DataFrame:
    """Volume fraction of each harbour still inside it, hour by hour."""
    s = np.load(seeds_file)
    with xr.open_dataset(particles) as ds:
        lon, lat = ds.lon.values, ds.lat.values          # (trajectory, time)
        times = pd.to_datetime(ds.time.values)
    rows = {}
    for n, (name, poly) in enumerate(HARBOURS.items()):
        own = s["harbour"] == n
        x, y = lon[own], lat[own]
        ok = np.isfinite(x)
        inside = np.zeros(x.shape, bool)
        inside[ok] = MplPath(poly).contains_points(np.c_[x[ok], y[ok]])
        rows[name] = (inside * s["w"][own, None]).sum(0) / s["w"][own].sum()
    return pd.DataFrame(rows, index=times)


def summary(r: pd.Series) -> dict:
    """tau at 1/e, truncated theta, and the exponential fitted after the first day."""
    t = (r.index - r.index[0]).total_seconds() / 86400
    below = np.flatnonzero(r.values < np.exp(-1))
    tau = float(t[below[0]]) if below.size else None
    late = (t >= 1) & (r.values > 0)
    b, a = np.polyfit(t[late], np.log(r.values[late]), 1)
    tau_fit = -1 / b if b < 0 else None
    t95 = tau_fit * np.log(np.exp(a) / 0.05) if tau_fit else None
    t99 = tau_fit * np.log(np.exp(a) / 0.01) if tau_fit else None
    return dict(tau_days=tau, theta_truncated_days=float(np.trapezoid(r.values, t)),
                r_end=float(r.values[-1]), tau_fit_days=tau_fit,
                t95_days=t95, t99_days=t99, window_days=float(t[-1]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--kz", type=float, nargs="+", default=[1e-4, 1e-2],
                    help="vertical diffusivity, m2/s, working values")
    ap.add_argument("--vertical-advection", action="store_true",
                    help="advect with the interpolated vertical velocity of FM")
    ap.add_argument("--analyse-only", action="store_true",
                    help="summarise particle files already written")
    args = ap.parse_args(argv)
    path = CASES / args.case / "output" / "currents_3d.nc"
    out = OUT / args.case
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for kz in args.kz:
        p = out / f"particles_kz{kz:.0e}.nc" if args.analyse_only else \
            run(path, kz, out, args.vertical_advection)
        r = remaining(p, out / "seeds.npz")
        r.to_csv(out / f"remaining_kz{kz:.0e}.csv")
        results[f"{kz:.0e}"] = {h: summary(r[h]) for h in r}
        print(json.dumps(results[f"{kz:.0e}"], indent=1))
    (out / "summary.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
