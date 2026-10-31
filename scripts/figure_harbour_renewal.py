"""Figures of the renewal of the Valletta harbours by particles in the hindcast currents.

Five files are written to figures/ from the output of renewal_opendrift.py:

- renewal_setup.png: bed depth of the box of extract_harbour_currents_3d.py,
  the two harbour polygons and the seeded columns, with the volume of each
  harbour by depth;
- renewal_remaining.png: wind at the BLUE buoy and the fraction of the volume
  of each harbour remaining in it, for both vertical diffusivities, with the
  exponential fitted after the first day;
- renewal_fate.png: the volume of each harbour by position over the window,
  in its own harbour, in the other, in the approach or out of the box;
- renewal_local_residence.png: the share of the window that the particles
  seeded in each column spend in their harbour of release;
- renewal_particles.gif: the particles of both runs hour by hour, coloured by
  harbour of release.

Usage:
    python figure_harbour_renewal.py [v03_3d20s_0722_0801_uv_thd] [--no-gif]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import renewal_opendrift as ro  # noqa: E402
from extract_harbour_currents_3d import BOX_LAT, BOX_LON  # noqa: E402

ROOT = ro.ROOT
FIG = ROOT / "figures"
INK, MUTED, GRID, SURFACE, LAND = "#0b0b0b", "#52514e", "#e8e7e3", "#fcfcfb", "#d9d6cf"
C_HARBOUR = {"Grand Harbour": "#2a78d6", "Marsamxett": "#eb6834"}
KZ = ("1e-04", "1e-02")
KZ_LABEL = {"1e-04": r"$K_z = 10^{-4}$ m$^2$/s", "1e-02": r"$K_z = 10^{-2}$ m$^2$/s"}
BLUE = (14.5388, 35.9294)
ASPECT = 1 / np.cos(np.radians(35.9))


def style(ax):
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def map_axes(ax, coast):
    coast.plot(ax=ax, color=LAND, edgecolor="#9a978f", lw=0.4, zorder=1)
    ax.set_xlim(*BOX_LON)
    ax.set_ylim(*BOX_LAT)
    ax.set_aspect(ASPECT)
    ax.tick_params(labelsize=7)


def load(case: str):
    out = ro.OUT / case
    currents = xr.open_dataset(ro.CASES / case / "output" / "currents_3d.nc")
    seeds = dict(np.load(out / "seeds.npz"))
    # the grid points of the seeds, before OpenDrift moves to the nearest water the
    # few that its interpolated land mask places on land
    seeds["lon0"], seeds["lat0"] = ro.seeds(currents)[:2]
    runs = {}
    for k in KZ:
        with xr.open_dataset(out / f"particles_kz{k}.nc") as ds:
            runs[k] = dict(lon=ds.lon.values, lat=ds.lat.values, z=ds.z.values,
                           time=pd.to_datetime(ds.time.values))
    remaining = {k: pd.read_csv(out / f"remaining_kz{k}.csv", index_col=0, parse_dates=True)
                 for k in KZ}
    summary = json.loads((out / "summary.json").read_text())
    coast = gpd.read_file(ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg").cx[
        BOX_LON[0] - 0.01:BOX_LON[1] + 0.01, BOX_LAT[0] - 0.01:BOX_LAT[1] + 0.01]
    return currents, seeds, runs, remaining, summary, coast


def inside(name, x, y):
    ok = np.isfinite(x)
    res = np.zeros(x.shape, bool)
    res[ok] = MplPath(ro.HARBOURS[name]).contains_points(np.c_[x[ok], y[ok]])
    return res


def figure_setup(currents, seeds, runs, coast):
    H = currents.sea_floor_depth_below_sea_level.values
    H = np.where(currents.land_binary_mask.values == 1, np.nan, H)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4.6), gridspec_kw=dict(width_ratios=[1.6, 1]))
    pc = ax.pcolormesh(currents.lon, currents.lat, H, cmap="Blues", vmin=0, vmax=80,
                       shading="nearest", zorder=0)
    map_axes(ax, coast)
    r = runs[KZ[0]]
    top = seeds["w"] > 0
    for n, (name, poly) in enumerate(ro.HARBOURS.items()):
        p = np.array(poly + [poly[0]])
        ax.plot(p[:, 0], p[:, 1], color=C_HARBOUR[name], lw=1.2, zorder=3)
        sel = (seeds["harbour"] == n) & top
        ax.scatter(seeds["lon0"][sel], seeds["lat0"][sel], s=0.3, color=C_HARBOUR[name], zorder=2,
                   label=name)
    ax.plot(*BLUE, marker="^", color=INK, ms=6, zorder=4)
    ax.annotate("BLUE buoy", BLUE, xytext=(-6, -10), textcoords="offset points", ha="right",
                fontsize=7, color=INK)
    ax.legend(loc="upper left", fontsize=7, markerscale=12, frameon=False)
    cb = fig.colorbar(pc, ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("bed depth (m)", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_title("(a) box of the currents and seeded columns", fontsize=9, loc="left")

    bins = np.arange(0, 32, 2)
    for n, name in enumerate(ro.HARBOURS):
        own = seeds["harbour"] == n
        depth = -r["z"][own, 0]
        vol = seeds["w"][own] * 1600 / 1e6               # hm3, grid cell of some 40 by 40 m
        h, _ = np.histogram(depth, bins=bins, weights=vol)
        bx.step(h, bins[:-1] + 1, where="mid", color=C_HARBOUR[name],
                label=f"{name}, {vol.sum():.1f} hm³")
    bx.invert_yaxis()
    bx.set_xlabel("volume per 2 m of depth (hm³)", fontsize=8)
    bx.set_ylabel("depth of the seed (m)", fontsize=8)
    bx.tick_params(labelsize=7)
    bx.legend(fontsize=7, frameon=False, loc="lower right")
    style(bx)
    bx.set_title("(b) volume by depth below the surface", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "renewal_setup.png", dpi=170, facecolor=SURFACE)
    plt.close(fig)


def blue_wind(t0, t1):
    b = pd.read_csv(ROOT / "data" / "processed" / "blue_buoy_10min.csv", index_col=0,
                    parse_dates=True)[["wind_speed", "wind_direction"]]
    return b.loc[t0:t1].resample("1h").mean()


def figure_remaining(remaining):
    r0 = remaining[KZ[0]]
    wind = blue_wind(r0.index[0], r0.index[-1])
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True,
                                 gridspec_kw=dict(height_ratios=[1, 2.4]))
    ax.plot(wind.index, wind.wind_speed, color=INK, lw=1)
    every = wind.iloc[::6]
    # direction from which the wind blows, drawn as the direction toward which it goes
    rad = np.radians(every.wind_direction.values)
    ax.quiver(every.index, np.full(len(every), 15.5), -np.sin(rad), -np.cos(rad),
              color=MUTED, scale=40, width=0.002, headwidth=4)
    ax.set_ylim(0, 18)
    ax.set_ylabel("wind at BLUE (m/s)", fontsize=8)
    style(ax)
    ax.tick_params(labelsize=7)

    t_days = (r0.index - r0.index[0]).total_seconds() / 86400
    for name in ro.HARBOURS:
        for k, ls in zip(KZ, ("-", "--")):
            r = remaining[k][name]
            bx.plot(r.index, r.values, color=C_HARBOUR[name], ls=ls, lw=1.4,
                    label=f"{name}, {KZ_LABEL[k]}")
            # the exponential of renewal_opendrift.summary, fitted after day 1
            late = t_days >= 1
            b, a = np.polyfit(t_days[late], np.log(r.values[late]), 1)
            bx.plot(r.index[late], np.exp(a + b * t_days[late]), color=C_HARBOUR[name],
                    ls=ls, lw=0.6, alpha=0.6)
    bx.axhline(np.exp(-1), color=MUTED, lw=0.8, ls=":")
    bx.annotate("1/e", (r0.index[0], np.exp(-1)), xytext=(2, 2), textcoords="offset points",
                fontsize=7, color=MUTED)
    bx.set_ylim(0, 1.02)
    bx.set_ylabel("fraction of the volume remaining, r(t)", fontsize=8)
    bx.legend(fontsize=7, frameon=False, loc="upper right", ncol=2)
    style(bx)
    bx.tick_params(labelsize=7)
    import matplotlib.dates as mdates
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.tight_layout()
    fig.savefig(FIG / "renewal_remaining.png", dpi=170, facecolor=SURFACE)
    plt.close(fig)


def fate(run, seeds, n):
    """Volume fraction of harbour n in its own harbour, the other, the approach and out of the box."""
    own = seeds["harbour"] == n
    x, y, w = run["lon"][own], run["lat"][own], seeds["w"][own, None]
    names = list(ro.HARBOURS)
    in_own = inside(names[n], x, y)
    in_other = inside(names[1 - n], x, y)
    gone = ~np.isfinite(x)
    approach = ~(in_own | in_other | gone)
    tot = w.sum()
    return {k: (m * w).sum(0) / tot for k, m in
            (("own harbour", in_own), ("other harbour", in_other),
             ("approach", approach), ("out of the box", gone))}


def figure_fate(runs, seeds):
    colours = ("#2a78d6", "#eb6834", "#1baf7a", "#b9b6ae")
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.4), sharex=True, sharey=True)
    for i, name in enumerate(ro.HARBOURS):
        for j, k in enumerate(KZ):
            ax = axes[i, j]
            f = fate(runs[k], seeds, i)
            t = runs[k]["time"]
            labels = list(f)
            labels[0] = name
            labels[1] = list(ro.HARBOURS)[1 - i]
            cols = list(colours)
            if i == 1:
                cols[0], cols[1] = cols[1], cols[0]
            ax.stackplot(t, *f.values(), colors=cols, labels=labels, lw=0)
            ax.set_ylim(0, 1)
            ax.set_xlim(t[0], t[-1])
            ax.set_title(f"released in {name}, {KZ_LABEL[k]}", fontsize=8, loc="left")
            ax.tick_params(labelsize=7)
            end = {kk: v[-1] for kk, v in f.items()}
            print(f"{name} {k} at day 7: " + ", ".join(f"{kk} {v:.2f}" for kk, v in end.items()))
            if j == 1:
                ax.legend(fontsize=7, frameon=False, loc="center left", bbox_to_anchor=(1, 0.5))
    import matplotlib.dates as mdates
    for ax in axes[1]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for ax in axes[:, 0]:
        ax.set_ylabel("fraction of the volume", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "renewal_fate.png", dpi=170, facecolor=SURFACE)
    plt.close(fig)


def figure_local(currents, runs, seeds, coast):
    names = list(ro.HARBOURS)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, k in zip(axes, KZ):
        run = runs[k]
        share = np.zeros(seeds["w"].size)
        for n, name in enumerate(names):
            own = seeds["harbour"] == n
            share[own] = inside(name, run["lon"][own], run["lat"][own]).mean(1)
        # the column value weights the N_LEVELS particles of a column by their volume
        glon, glat = currents.lon.values, currents.lat.values
        ix = np.rint((seeds["lon0"] - glon[0]) / (glon[1] - glon[0])).astype(int)
        iy = np.rint((seeds["lat0"] - glat[0]) / (glat[1] - glat[0])).astype(int)
        num, den = np.zeros((glat.size, glon.size)), np.zeros((glat.size, glon.size))
        np.add.at(num, (iy, ix), share * seeds["w"])
        np.add.at(den, (iy, ix), seeds["w"])
        with np.errstate(invalid="ignore"):
            col_share = np.where(den > 0, num / den, np.nan)
        sc = ax.pcolormesh(glon, glat, col_share, cmap="viridis_r", vmin=0, vmax=1,
                           shading="nearest", zorder=0)
        map_axes(ax, coast)
        for name, poly in ro.HARBOURS.items():
            p = np.array(poly + [poly[0]])
            ax.plot(p[:, 0], p[:, 1], color=MUTED, lw=0.6, zorder=3)
        ax.set_xlim(14.484, 14.535)
        ax.set_ylim(35.872, 35.913)
        ax.set_title(f"{KZ_LABEL[k]}", fontsize=9, loc="left")
    cb = fig.colorbar(sc, ax=axes, shrink=0.85, pad=0.02)
    cb.set_label("share of the 7 days in the harbour of release", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.savefig(FIG / "renewal_local_residence.png", dpi=170, facecolor=SURFACE,
                bbox_inches="tight")
    plt.close(fig)


def animation(runs, seeds, remaining, coast, every=2):
    from PIL import Image
    names = list(ro.HARBOURS)
    colour = np.array([C_HARBOUR[names[h]] for h in seeds["harbour"]])
    wind = blue_wind(runs[KZ[0]]["time"][0], runs[KZ[0]]["time"][-1])
    t = runs[KZ[0]]["time"]
    frames = []
    for i in range(0, t.size, every):
        fig = plt.figure(figsize=(9.6, 6.0), dpi=90)
        gs = fig.add_gridspec(2, 2, height_ratios=[4.2, 1], hspace=0.22, wspace=0.04,
                              left=0.07, right=0.99, top=0.91, bottom=0.07)
        for j, k in enumerate(KZ):
            ax = fig.add_subplot(gs[0, j])
            map_axes(ax, coast)
            run = runs[k]
            ok = np.isfinite(run["lon"][:, i])
            ax.scatter(run["lon"][ok, i], run["lat"][ok, i], s=0.6, c=colour[ok], lw=0, zorder=2)
            for name, poly in ro.HARBOURS.items():
                p = np.array(poly + [poly[0]])
                ax.plot(p[:, 0], p[:, 1], color=MUTED, lw=0.5, zorder=3)
            ax.set_title(KZ_LABEL[k], fontsize=9, loc="left")
            if j:
                ax.set_yticklabels([])
            if j == 0:
                w = wind.reindex([t[i]], method="nearest").iloc[0]
                rad = np.radians(w.wind_direction)
                ax.annotate("", xy=(14.478 - 0.006 * np.sin(rad), 35.921 - 0.006 * np.cos(rad)),
                            xytext=(14.478, 35.921),
                            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2))
                ax.text(14.473, 35.913, f"wind at BLUE\n{w.wind_speed:.0f} m/s", fontsize=7,
                        color=INK, va="top")
        bx = fig.add_subplot(gs[1, :])
        for name in names:
            for k, ls in zip(KZ, ("-", "--")):
                r = remaining[k][name]
                bx.plot(r.index, r.values, color=C_HARBOUR[name], ls=ls, lw=1.1,
                        label=f"{name}, {KZ_LABEL[k]}")
        bx.axvline(t[i], color=INK, lw=0.8)
        bx.axhline(np.exp(-1), color=MUTED, lw=0.6, ls=":")
        bx.set_ylim(0, 1.02)
        bx.set_xlim(t[0], t[-1])
        bx.set_ylabel("r(t)", fontsize=8)
        bx.tick_params(labelsize=7)
        bx.legend(fontsize=6, frameon=False, ncol=4, loc="lower left")
        style(bx)
        import matplotlib.dates as mdates
        bx.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        fig.suptitle(f"Particles released 25 July 2025 00:00 UTC, {t[i]:%d %b %H:%M} UTC",
                     fontsize=10, x=0.06, ha="left")
        fig.canvas.draw()
        img = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba())
        frames.append(img.convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT))
        plt.close(fig)
    path = FIG / "renewal_particles.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=120, loop=0,
                   optimize=True)
    print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB, {len(frames)} frames)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", nargs="?", default="v03_3d20s_0722_0801_uv_thd")
    ap.add_argument("--no-gif", action="store_true")
    args = ap.parse_args(argv)
    currents, seeds, runs, remaining, summary, coast = load(args.case)
    figure_setup(currents, seeds, runs, coast)
    figure_remaining(remaining)
    figure_fate(runs, seeds)
    figure_local(currents, runs, seeds, coast)
    if not args.no_gif:
        animation(runs, seeds, remaining, coast)
    return 0


if __name__ == "__main__":
    sys.exit(main())
