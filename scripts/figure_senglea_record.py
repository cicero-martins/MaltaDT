"""Figures for visual inspection of the Senglea sea level record.

Three plates, sharing the quality control and the filters of
`analyse_senglea_spectrum.py` so that what is seen is what is analysed, and a
fourth, compact, of the coverage of the record against the reported events.

1. Record overview. The one-minute level over the whole record, the daily
   coverage, and the daily range of the 0.2 to 10 cph band with the largest
   events marked.
2. Spectrogram. The spectrum of each day, normalised by the background of the
   mean spectrum, against time. A peak present on every day is a property of
   the geometry, whereas one appearing in episodes belongs to the forcing.
3. Events. The largest events of the record, each as the level over 24 h with
   the tide, and as the band-passed signal over 12 h around the maximum.

Usage:
    python figure_senglea_record.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_senglea_spectrum as an  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
N_EVENT_PANELS = 6
DAY_MIN = 1440
MIN_DAY_COVERAGE = an.MIN_DAY_COVERAGE

C_LINE = an.C_SERIES[0]
C_TEXT2 = an.C_TEXT2
C_GRID = "#e8e7e3"
C_EVENT = "#eb6834"
SURFACE = "#fcfcfb"

# Milghuba events reported since the installation of the gauge, as tabulated in
# docs/senglea_spectrum.md.
REPORTED_EVENTS = (("2022-06-30", "30 Jun 2022"),
                   ("2023-07-01", "1 Jul 2023"),
                   ("2024-06-13", "13 Jun 2024"))


def save(fig, out: Path) -> Path:
    """Save, falling back to a sibling file when the target is locked.

    On Windows a PNG open in an editor preview cannot be overwritten, and
    matplotlib reports it only as an invalid argument.
    """
    try:
        fig.savefig(out, dpi=150, facecolor=SURFACE)
        return out
    except OSError:
        alt = out.with_suffix(".new.png")
        fig.savefig(alt, dpi=150, facecolor=SURFACE)
        print(f"{out.name} is locked, probably open in a viewer; written {alt.name}")
        return alt


def style(ax):
    ax.grid(color=C_GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "xtick.color": C_TEXT2, "ytick.color": C_TEXT2})
    return plt


def daily_range(bp: pd.Series) -> pd.Series:
    cover = bp.notna().resample("1D").mean()
    rng = bp.resample("1D").max() - bp.resample("1D").min()
    return rng.where(cover >= MIN_DAY_COVERAGE)


def plate_overview(plt, x: pd.Series, bp: pd.Series, events) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True,
                             gridspec_kw=dict(height_ratios=[2, 0.8, 1.6]))
    ax = axes[0]
    ax.plot(x.index, x, color=C_LINE, lw=0.3)
    ax.set_ylabel("level, m")

    ax = axes[1]
    cover = x.notna().resample("1D").mean() * 100
    ax.fill_between(cover.index, cover, step="mid", color=C_LINE, alpha=0.5, lw=0)
    ax.set_ylabel("daily\ncoverage, %")
    ax.set_ylim(0, 105)

    ax = axes[2]
    rng = daily_range(bp)
    ax.plot(rng.index, rng, color=C_LINE, lw=0.8)
    # Numbered as in the events plate, since dates of nearby events overlap.
    for k, (t, r, *_) in enumerate(events[:N_EVENT_PANELS], start=1):
        ax.plot(t, r, "o", ms=7, color="#eb6834", mec=SURFACE, mew=2)
        ax.annotate(str(k), (t, r), xytext=(0, 6), textcoords="offset points",
                    fontsize=7, color=C_TEXT2, ha="center")
    ax.set_ylabel("daily range,\n0.2 to 10 cph, m")
    ax.set_title(f"Daily range of the short-period band, days with at least "
                 f"{MIN_DAY_COVERAGE:.0%} coverage; numbered the {N_EVENT_PANELS} "
                 f"largest within the windows", fontsize=9, loc="left")
    for ax in axes:
        for a, b in an.CLEAN_WINDOWS:
            ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color="#cde2fb", alpha=0.5,
                       zorder=0, lw=0)
        style(ax)
    axes[0].set_title("Senglea (IDSL-42), one-minute level after despiking and quality "
                      "control; shaded, the windows admitted to the analysis",
                      fontsize=9, loc="left")
    fig.tight_layout()
    out = FIG / "senglea_record_overview.png"
    out = save(fig, out)
    plt.close(fig)
    return out


def plate_coverage(plt, x: pd.Series) -> Path:
    """Coverage of the record against the dates of the reported events.

    A compact plate for presentation. The level shows the displaced regime and
    the daily coverage shows the gaps, with the admitted windows shaded and the
    reported events marked, none of which falls on a usable stretch.
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 4.6), sharex=True,
                             gridspec_kw=dict(height_ratios=[1.3, 1]))
    ax = axes[0]
    ax.plot(x.index, x, color=C_LINE, lw=0.3)
    ax.set_ylabel("level, m", fontsize=11)

    ax = axes[1]
    cover = x.notna().resample("1D").mean() * 100
    ax.fill_between(cover.index, cover, step="mid", color=C_LINE, alpha=0.6, lw=0)
    ax.set_ylabel("daily\ncoverage, %", fontsize=11)
    ax.set_ylim(0, 105)

    for ax in axes:
        for a, b in an.CLEAN_WINDOWS:
            ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color="#cde2fb", alpha=0.6,
                       zorder=0, lw=0)
        for date, _ in REPORTED_EVENTS:
            ax.axvline(pd.Timestamp(date), color=C_EVENT, lw=1.6, zorder=5)
        ax.tick_params(labelsize=10)
        style(ax)
    top = axes[0].get_ylim()[1]
    for date, label in REPORTED_EVENTS:
        axes[0].annotate(label, (pd.Timestamp(date), top), xytext=(4, -2),
                         textcoords="offset points", fontsize=10, color=C_EVENT,
                         ha="left", va="top", fontweight="bold")
    axes[0].set_title("Senglea, one-minute level and daily coverage of the public record. "
                      "Shaded, the windows admitted. Orange, the reported events.",
                      fontsize=11, loc="left")
    fig.tight_layout()
    out = save(fig, FIG / "senglea_coverage_events.png")
    plt.close(fig)
    return out


def daily_spectra(x: pd.Series, f_ref):
    """PSD of each day with near-complete coverage, on the frequency grid of one day."""
    from scipy.signal import detrend

    days, rows = [], []
    w = np.hanning(DAY_MIN)
    scale = 2.0 / (w ** 2).sum() / 60.0
    for day, d in x.groupby(x.index.floor("D")):
        if len(d) < DAY_MIN or d.notna().mean() < 0.98:
            continue
        v = d.interpolate(limit_direction="both").to_numpy()[:DAY_MIN]
        rows.append(scale * np.abs(np.fft.rfft(detrend(v) * w)) ** 2)
        days.append(day)
    f = np.fft.rfftfreq(DAY_MIN, d=1.0) * 60.0
    return f, pd.DatetimeIndex(days), np.array(rows)


def plate_spectrogram(plt, x: pd.Series, f_mean, psd_mean) -> Path:
    from matplotlib.colors import LogNorm

    f, days, S = daily_spectra(x, f_mean)
    bg = np.interp(f, f_mean[1:], an.background(f_mean, psd_mean)[1:])
    sel = (f >= 0.1) & (f <= 15)
    R = S[:, sel] / bg[sel]

    fig, (ax, axm) = plt.subplots(1, 2, figsize=(12, 7), sharey=True,
                                  gridspec_kw=dict(width_ratios=[4, 1]))
    # Days absent from the record are left blank rather than interpolated.
    full = pd.date_range(days[0], days[-1], freq="D")
    grid = np.full((full.size, R.shape[1]), np.nan)
    grid[full.get_indexer(days)] = R
    m = ax.pcolormesh(full, f[sel], grid.T, cmap="Blues",
                      norm=LogNorm(vmin=0.3, vmax=30), shading="nearest")
    for lo, hi in (an.MILGHUBA, an.BASIN_PREDICTED):
        for v in (lo, hi):
            ax.axhline(v, color="#eb6834", lw=0.8, ls="--")
    ax.set_yscale("log")
    ax.set_ylabel("frequency, cph")
    ax.set_title("Daily spectrum divided by the background of the mean spectrum; dashed, "
                 "the milgħuba band and the predicted basin band", fontsize=9, loc="left")
    fig.colorbar(m, ax=axm, label="PSD / background", shrink=0.8)

    med = np.nanmedian(R, axis=0)
    axm.semilogx(med, f[sel], color=C_LINE, lw=1.5, label="median day")
    axm.axvline(1, color=C_TEXT2, lw=0.8)
    for lo, hi in (an.MILGHUBA, an.BASIN_PREDICTED):
        axm.axhspan(lo, hi, color="#f0efec", zorder=0)
    for fp, r in an.peaks(f_mean, psd_mean):
        axm.annotate(f"{60 / fp:.1f} min", (med[np.argmin(abs(f[sel] - fp))], fp),
                     xytext=(4, 0), textcoords="offset points", fontsize=7,
                     color=C_TEXT2, va="center")
    axm.set_xlim(0.04, 200)
    axm.set_xlabel("median PSD / background")
    axm.set_title("Median day", fontsize=9, loc="left")
    style(axm)
    fig.tight_layout()
    out = FIG / "senglea_spectrogram.png"
    out = save(fig, out)
    plt.close(fig)
    return out


def plate_events(plt, x: pd.Series, bp: pd.Series, events) -> Path:
    n = min(N_EVENT_PANELS, len(events))
    fig, axes = plt.subplots(n, 2, figsize=(12, 2.0 * n + 0.6), squeeze=False,
                             gridspec_kw=dict(width_ratios=[1, 1.4]))
    for i, (t, rng, fm, fb, fp) in enumerate(events[:n]):
        raw = x[t - pd.Timedelta(hours=12):t + pd.Timedelta(hours=12)]
        seg = bp[t - pd.Timedelta(hours=6):t + pd.Timedelta(hours=6)]
        ax = axes[i, 0]
        ax.plot((raw.index - t).total_seconds() / 3600, raw, color=C_TEXT2, lw=0.8)
        ax.set_ylabel("level, m")
        ax.set_title(f"{i + 1}. {t:%Y-%m-%d %H:%M} UTC, level with tide", fontsize=8, loc="left")
        ax = axes[i, 1]
        ax.plot((seg.index - t).total_seconds() / 60, seg, color=C_LINE, lw=1.2)
        ax.axhline(0, color="#d6d5d0", lw=0.8)
        ax.set_title(f"band-passed 0.2 to 10 cph, range {rng:.2f} m, dominant period "
                     f"{60 / fp:.1f} min", fontsize=8, loc="left")
        for a in axes[i]:
            style(a)
    axes[-1, 0].set_xlabel("hours from the maximum")
    axes[-1, 1].set_xlabel("minutes from the maximum")
    fig.tight_layout()
    out = FIG / "senglea_events.png"
    out = save(fig, out)
    plt.close(fig)
    return out


def main() -> int:
    s = an.load("senglea")
    if s is None:
        print("missing senglea_wl_1min.csv", file=sys.stderr)
        return 1
    x_all, _ = an.quality_control(s)
    x = an.in_windows(x_all)
    f, psd, _ = an.welch(x)
    events, bp = an.events(x)
    bp_all = an.bandpass(x_all, an.MILGHUBA[0], 10.0)
    plt = setup()
    for out in (plate_overview(plt, x_all, bp_all, events),
                plate_coverage(plt, x_all),
                plate_spectrogram(plt, x, f, psd),
                plate_events(plt, x, bp, events)):
        print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
