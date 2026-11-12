"""Agreement of the runs with the CALYPSO HF radar by day of run.

The comparison of `hfr_skill.py` over the corridor of the drifter tracks is
repeated without the exclusion of the first 72 hours and split by day counted
from the start of each run, so that a dependence of the agreement on the time
elapsed since the start from rest can be read. For each day the series of the
totals averaged over the corridor gives the mean northward current of each
source, the root mean square of the vector difference and the complex
correlation, and the radials of Ta' Barkat in the corridor give the Pearson
correlation and the root mean square difference over bins and hours.

The velocity of the July 2026 drifters and of each field at their positions,
from `hfr_drifter_collocation.py`, is split by the same days.

Output: data/processed/hfr_skill_by_day.csv, data/processed/hfr_drifter_by_day.csv,
figures/hfr_skill_by_day.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import hfr_skill as hs  # noqa: E402

OUT = ROOT / "data" / "processed" / "hfr_skill_by_day.csv"
FIGURE = ROOT / "figures" / "hfr_skill_by_day.png"
COLLOCATION = ROOT / "data" / "processed" / "hfr_drifter_collocation.csv"
OUT_DRIFTERS = ROOT / "data" / "processed" / "hfr_drifter_by_day.csv"
RUNS = ("jul25", "jul26")


def by_day(window: str) -> tuple[pd.DataFrame, dict]:
    cfg = hs.WINDOWS[window]
    fm = xr.open_dataset(ROOT / "model" / "hindcast" / cfg["case"] / "output" / f"{cfg['case']}_surface_map.nc")
    t_model = pd.to_datetime(fm.time.values)
    t_ok = set(t_model[t_model.minute == 0].to_numpy())
    area = hs.domain(fm)

    tot = hs.totals(window, area, t_ok)
    times = pd.to_datetime(tot["times"])
    mask = np.isfinite(tot["u"])
    fields = {"hfr": (tot["u"], tot["v"]), "model": hs.model_at(fm, tot["times"], tot["lon"], tot["lat"])}
    if cfg["cmems"]:
        fields["cmems"] = hs.cmems_at(cfg["cmems"], tot["times"], tot["lon"], tot["lat"])
    for s in fields:
        fields[s] = tuple(np.where(mask, f, np.nan) for f in fields[s])
    box = hs.in_box(window, tot["lon"], tot["lat"])
    series = {s: hs.box_series(*fields[s], box) for s in fields}
    day = ((times - t_model[0]) / pd.Timedelta(days=1)).astype(int) + 1

    rad = hs.radials(window, area, t_ok)
    if rad:
        th = np.radians(rad["dir"])
        rtimes = pd.to_datetime(rad["times"])
        rday = ((rtimes - t_model[0]) / pd.Timedelta(days=1)).astype(int) + 1
        rbox = hs.in_box(window, rad["lon"], rad["lat"])
        rfields = {}
        um, vm = hs.model_at(fm, rad["times"], rad["lon"], rad["lat"])
        rfields["model"] = um * np.sin(th) + vm * np.cos(th)
        if cfg["cmems"]:
            uc, vc = hs.cmems_at(cfg["cmems"], rad["times"], rad["lon"], rad["lat"])
            rfields["cmems"] = uc * np.sin(th) + vc * np.cos(th)

    rows = []
    for d in np.unique(day):
        sel = day == d
        for s in fields:
            if s == "hfr":
                continue
            st = hs.vector_stats(series["hfr"][0][sel], series["hfr"][1][sel], series[s][0][sel], series[s][1][sel])
            row = dict(window=window, day=int(d), date=str(times[sel][0].date()), source=s,
                       n=st.get("n", 0), vo=st.get("vo"), vm=st.get("vm"), rmse=st.get("rmse"),
                       rho=st.get("rho"), phase=st.get("phase"))
            if rad and s in rfields:
                rs = rday == d
                if rs.any():
                    rst = hs.scalar_stats(rad["r"][rs][:, rbox].ravel(), rfields[s][rs][:, rbox].ravel())
                    row.update(n_rad=rst.get("n", 0), r_rad=rst.get("r"), rmse_rad=rst.get("rmse"))
            rows.append(row)
    return pd.DataFrame(rows), dict(times=times, series=series, start=t_model[0])


def drifters_by_day() -> pd.DataFrame:
    """Mean northward velocity of the July 2026 units and of each field at their positions, by day of run."""
    d = pd.read_csv(COLLOCATION, parse_dates=["time"])
    d = d[d.window == "jul26"]
    fm_case = hs.WINDOWS["jul26"]["case"]
    fm = xr.open_dataset(ROOT / "model" / "hindcast" / fm_case / "output" / f"{fm_case}_surface_map.nc")
    start = pd.to_datetime(fm.time.values[0])
    d = d.assign(day=((d.time - start) / pd.Timedelta(days=1)).astype(int) + 1)
    rows = []
    for day, g in d.groupby("day"):
        row = dict(day=int(day), n=len(g), v_drifter=g.v.mean())
        w = g.u + 1j * g.v
        for s in ("model", "cmems"):
            m = g[f"{s}_u"] + 1j * g[f"{s}_v"]
            row[f"v_{s}"] = g[f"{s}_v"].mean()
            row[f"rmse_{s}"] = np.sqrt((np.abs(m - w) ** 2).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    dd = drifters_by_day()
    dd.to_csv(OUT_DRIFTERS, index=False, float_format="%.3f")
    print(dd.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    frames, keep = [], {}
    for w in RUNS:
        df, keep[w] = by_day(w)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(OUT, index=False, float_format="%.3f")
    print(out.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    fig, axes = plt.subplots(3, 2, figsize=(12, 8.5), sharex="col")
    for j, w in enumerate(RUNS):
        k = keep[w]
        days = (k["times"] - k["start"]) / pd.Timedelta(days=1) + 1
        ax = axes[0, j]
        for s, (_, v) in k["series"].items():
            ax.plot(days, v, color=hs.COLOURS[s], lw=1.2, label=hs.LABELS[s])
        ax.axvspan(1, 4, color="0.92", zorder=0)
        ax.axhline(0, color="0.7", lw=0.5)
        ax.set_ylabel("northward current (m/s)")
        ax.set_title(f"({'ab'[j]}) Run started {k['start']:%d %B %Y}, corridor mean", loc="left", fontsize=10)
        ax.legend(fontsize=8, loc="upper right")
        d = out[out.window == w]
        for s, g in d.groupby("source"):
            axes[1, j].plot(g.day + 0.5, g.rmse, "o-", color=hs.COLOURS[s], label=hs.LABELS[s])
            if "r_rad" in g:
                axes[2, j].plot(g.day + 0.5, g.r_rad, "o-", color=hs.COLOURS[s], label=hs.LABELS[s])
        axes[1, j].axvspan(1, 4, color="0.92", zorder=0)
        axes[2, j].axvspan(1, 4, color="0.92", zorder=0)
        axes[2, j].axhline(0, color="0.7", lw=0.5)
        axes[1, j].set_ylabel("rms vector difference (m/s)")
        axes[1, j].set_title(f"({'cd'[j]}) Totals, corridor mean, by day", loc="left", fontsize=10)
        axes[2, j].set_ylabel("correlation")
        axes[2, j].set_ylim(-0.6, 1)
        axes[2, j].set_title(f"({'ef'[j]}) Radials of Ta' Barkat in the corridor, by day", loc="left", fontsize=10)
        axes[2, j].set_xlabel("day of run")
        axes[2, j].set_xlim(1, np.ceil(days.max()) + 1)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150)
    print(FIGURE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
