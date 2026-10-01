"""Sea level spectrum inside the Grand Harbour, from the Senglea radar gauge.

The basin mode calculation of docs/basin_modes.md places the fundamental mode
of the Grand Harbour between 14.5 and 18.4 minutes, 3.3 to 4.1 cph, above the
milghuba band of 0.2 to 2 cph. A spectrum of sea level inside the basin tests
both statements: a peak should stand above the background within 3.3 to 4.1
cph, and energy in the band, where present, should not coincide with it.

The record is IDSL-42 on the JRC TAD server, at Senglea between Dockyard Creek
and French Creek, downloaded at 5 s by `download_jrc_tad_wl.py`, cleared of
radar echoes and averaged to one minute by `despike_tad_5s.py`. Only the two
windows in CLEAN_WINDOWS are analysed, for the reasons recorded there. Two gauges outside the harbour, Marsaxlokk (IDSL-43)
and the device at Cirkewwa (IDSL-34), overlap the first months and give a
spectral ratio. Both stand in embayments with modes of their own, so the ratio
compares two coastal sites and is not a transfer function from the open sea.

Steps
1. Quality control. Stuck values, jumps and spikes are removed, as set out in
   quality_control(), and gaps up to MAX_GAP_MIN are interpolated.
2. Mean spectrum by Welch's method over segments of SEGMENT_MIN minutes free of
   gaps, Hann window, half overlap, linear detrend per segment.
3. Peaks between 2 and 10 cph are located against a smoothed background, the
   running median of the log spectrum over a factor of two in frequency, and
   maxima within 15 per cent of each other in frequency are merged.
4. Events are the days of largest range in the 0.2 to 10 cph band. For each the
   spectrum over a 12 h window centred on the maximum is computed, and the
   fraction of the band-passed variance falling in the milghuba band and in the
   predicted basin band is reported.

Usage:
    python analyse_senglea_spectrum.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "insitu"
FIGURE = ROOT / "figures" / "senglea_spectrum.png"

# Windows of the Senglea record admitted to the analysis, to be confirmed with
# Prof. Gauci. Outside them the record fails on one or both of two counts,
# measured on the despiked one-minute series.
# - Coverage. Monthly coverage is 84 to 100 per cent inside the windows and
#   58 per cent or less between and after them.
# - Reference. The daily median level stays between -0.53 and -0.83 m inside
#   the windows. In July 2022 and from April 2023 to September 2024 it sits
#   near +1.5 m, a shift of some 2.1 m that indicates a change of installation
#   or configuration of the radar, and possibly of its position.
# The first three days after installation, 21 to 23 June 2021, carry level
# steps and plateaus held for hours and are excluded as well.
# Matters to confirm: the cause of the gaps of 2022, the cause of the shift,
# and whether the gauge was moved, since a different position would change the
# local expression of the basin modes.
CLEAN_WINDOWS = (("2021-06-24", "2021-12-31 23:59"),
                 ("2022-12-01", "2023-03-31 23:59"))

MILGHUBA = (0.2, 2.0)           # cph, Drago (2009)
BASIN_PREDICTED = (3.26, 4.14)  # cph, docs/basin_modes.md, Grand Harbour T and T0
DESPIKE_M = 0.25
STUCK_WINDOW_MIN = 30
STUCK_STD_M = 0.002
JUMP_M = 0.30
JUMP_PAD_MIN = 30
STEP_M = 0.5
STEP_MAX_GAP_MIN = 15
STEP_MATCH = 0.3
STEP_MAX_EPISODE_H = 24
DEPARTURE_M = 0.6
DEPARTURE_WINDOW_H = 73
MAX_GAP_MIN = 5
SEGMENT_MIN = 2048
EVENT_WINDOW_MIN = 720
N_EVENTS = 10
MIN_DAY_COVERAGE = 0.9

# Reference palette of the dataviz skill, light surface.
C_SERIES = ("#2a78d6", "#eb6834", "#1baf7a")
C_TEXT2 = "#52514e"
C_BAND = "#f0efec"


def load(name: str) -> pd.Series | None:
    """One-minute series cleared of radar echoes by despike_tad_5s.py."""
    path = RAW / f"{name}_wl_1min_despiked.csv"
    if not path.exists():
        return None
    s = pd.read_csv(path, index_col=0, parse_dates=True)["level_m"]
    return s[~s.index.duplicated()].sort_index()


def in_windows(x: pd.Series, windows=CLEAN_WINDOWS) -> pd.Series:
    """The series with every value outside the admitted windows set missing."""
    keep = np.zeros(len(x), dtype=bool)
    for a, b in windows:
        keep |= (x.index >= pd.Timestamp(a)) & (x.index <= pd.Timestamp(b))
    return x.where(keep)


def quality_control(s: pd.Series) -> tuple[pd.Series, dict]:
    """Remove stuck values, jumps and spikes, then fill short gaps on a regular grid.

    Stuck: the standard deviation over STUCK_WINDOW_MIN falls below STUCK_STD_M.
    The record carries plateaus held for hours without tide during the days
    after installation, whereas on valid days the background oscillation alone
    is of several centimetres.
    Jump: a change above JUMP_M within one minute, masked JUMP_PAD_MIN either
    side. A milghuba of 0.5 m at 20 minutes changes by at most 0.16 m per
    minute, so the threshold does not reach a physical event.
    Spike: a departure above DESPIKE_M from the 31-minute running median.
    """
    full = s.reindex(pd.date_range(s.index[0], s.index[-1], freq="1min"))
    std = full.rolling(STUCK_WINDOW_MIN, center=True, min_periods=STUCK_WINDOW_MIN // 2).std()
    stuck = std < STUCK_STD_M
    stuck = stuck.rolling(STUCK_WINDOW_MIN, center=True, min_periods=1).max().astype(bool)
    jump = full.diff().abs() > JUMP_M
    jump = jump.rolling(2 * JUMP_PAD_MIN + 1, center=True, min_periods=1).max().astype(bool)
    offset = offset_episodes(full.mask(stuck)) | level_departure(full.mask(stuck))
    clean = full.mask(stuck | jump | offset)
    med = clean.rolling(31, center=True, min_periods=10).median()
    spikes = (clean - med).abs() > DESPIKE_M
    clean = clean.mask(spikes)
    filled = clean.interpolate(limit=MAX_GAP_MIN, limit_area="inside")
    stats = dict(span=len(full), raw=int(s.size), stuck=int((stuck & full.notna()).sum()),
                 jump=int((jump & full.notna()).sum()), spikes=int(spikes.sum()),
                 offset=int((offset & full.notna()).sum()), valid=int(filled.notna().sum()))
    return filled, stats


def level_departure(x: pd.Series) -> pd.Series:
    """Mask of hours whose median departs from the three-day median by DEPARTURE_M.

    Catches offset episodes whose bounding steps are not both found, because
    one falls in a long gap or more than STEP_MAX_EPISODE_H away. The offsets
    observed are 1.3 to 2.1 m, whereas the tide reaches some 0.15 m and a surge,
    developing over a day, departs from a three-day median by much less than
    DEPARTURE_M.
    """
    hourly = x.resample("1h").median()
    ref = hourly.rolling(DEPARTURE_WINDOW_H, center=True, min_periods=12).median()
    bad = (hourly - ref).abs() > DEPARTURE_M
    return bad.reindex(x.index, method="ffill").fillna(False).astype(bool)


def offset_episodes(x: pd.Series) -> pd.Series:
    """Mask of reference offsets, plateaus bounded by a step up and a step down.

    The record carries episodes of hours during which the level is displaced by
    1 to 1.5 m with the basin oscillation still riding on it, entered and left
    within a minute or two and often beside a gap, so that a difference between
    consecutive minutes does not see the step. Steps are therefore sought
    between consecutive valid values up to STEP_MAX_GAP_MIN apart. A step above
    STEP_M paired with the next step of opposite sign, of magnitude within
    STEP_MATCH and within STEP_MAX_EPISODE_H, bounds an offset episode, masked
    whole with JUMP_PAD_MIN either side. An unpaired step is masked
    JUMP_PAD_MIN either side.
    """
    v = x.dropna()
    dt = v.index.to_series().diff().dt.total_seconds().div(60)
    dv = v.diff()
    steps = v.index[(dv.abs() > STEP_M) & (dt <= STEP_MAX_GAP_MIN)]
    sizes = dv[steps]
    mask = pd.Series(False, index=x.index)
    pad = pd.Timedelta(minutes=JUMP_PAD_MIN)
    used = set()
    for i, t in enumerate(steps):
        if t in used:
            continue
        paired = False
        for t2 in steps[i + 1:]:
            if t2 - t > pd.Timedelta(hours=STEP_MAX_EPISODE_H):
                break
            if np.sign(sizes[t2]) != np.sign(sizes[t]) and \
                    abs(abs(sizes[t2]) / abs(sizes[t]) - 1) <= STEP_MATCH:
                mask[t - pad:t2 + pad] = True
                used.update((t, t2))
                paired = True
                break
        if not paired:
            mask[t - pad:t + pad] = True
    return mask


def segments(x: pd.Series, n: int):
    """Start positions of gap-free segments of length n, with half overlap."""
    ok = x.notna().to_numpy()
    starts, i = [], 0
    run = np.zeros(ok.size + 1, dtype=int)
    run[1:] = np.cumsum(ok)
    while i + n <= ok.size:
        if run[i + n] - run[i] == n:
            starts.append(i)
            i += n // 2
        else:
            # Jump past the last gap inside the window.
            bad = np.flatnonzero(~ok[i:i + n])
            i += int(bad[-1]) + 1
    return starts


def welch(x: pd.Series, n: int = SEGMENT_MIN):
    from scipy.signal import detrend

    starts = segments(x, n)
    if not starts:
        return None, None, 0
    w = np.hanning(n)
    scale = 1.0 / (w ** 2).sum()
    v = x.to_numpy()
    acc = np.zeros(n // 2 + 1)
    for s0 in starts:
        seg = detrend(v[s0:s0 + n]) * w
        acc += np.abs(np.fft.rfft(seg)) ** 2
    psd = 2 * scale * acc / len(starts)              # m2 per cycle per minute
    f = np.fft.rfftfreq(n, d=1.0) * 60.0             # cph
    return f, psd / 60.0, len(starts)                # m2 per cph


def background(f, psd):
    """Running median of log PSD over a factor of two in frequency."""
    logp = np.log(psd)
    out = np.full_like(psd, np.nan)
    for k in range(1, f.size):
        sel = (f >= f[k] / np.sqrt(2)) & (f <= f[k] * np.sqrt(2))
        out[k] = np.exp(np.median(logp[sel]))
    return out


def peaks(f, psd, lo=2.0, hi=10.0, min_ratio=2.0, merge=0.15):
    """Local maxima of PSD / background, merged within a relative frequency span.

    A broad peak carries several local maxima at the resolution of the segment,
    so maxima closer than `merge` in relative frequency are reported once, at
    the largest.
    """
    from scipy.signal import find_peaks

    bg = background(f, psd)
    idx = np.flatnonzero((f >= lo) & (f <= hi))
    k, _ = find_peaks(psd[idx] / bg[idx], height=min_ratio)
    found = sorted(((f[idx[j]], psd[idx[j]] / bg[idx[j]]) for j in k),
                   key=lambda p: -p[1])
    kept = []
    for fp, r in found:
        if all(abs(fp / fk - 1) > merge for fk, _ in kept):
            kept.append((fp, r))
    return sorted(kept)


def bandpass(x: pd.Series, lo_cph: float, hi_cph: float) -> pd.Series:
    from scipy.signal import butter, sosfiltfilt

    sos = butter(4, [lo_cph / 30.0, hi_cph / 30.0], btype="band", output="sos")
    v = x.interpolate(limit_area="inside").to_numpy()
    ok = np.isfinite(v)
    out = np.full_like(v, np.nan)
    # Filter each continuous run separately.
    edges = np.flatnonzero(np.diff(np.r_[0, ok.astype(int), 0]))
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a > 200:
            out[a:b] = sosfiltfilt(sos, v[a:b])
    return pd.Series(out, index=x.index)


def band_fraction(f, psd, band):
    sel = (f >= band[0]) & (f <= band[1])
    tot = (f >= MILGHUBA[0]) & (f <= 10.0)
    return float(np.trapezoid(psd[sel], f[sel]) / np.trapezoid(psd[tot], f[tot]))


def events(x: pd.Series):
    """Days of largest band-passed range, on days with near-complete coverage.

    A day is admitted when at least MIN_DAY_COVERAGE of its minutes survive
    quality control, and an event when the window around its maximum is free
    of gaps, so that fragments left by the quality control are not ranked.
    """
    bp = bandpass(x, MILGHUBA[0], 10.0)
    cover = x.notna().resample("1D").mean()
    daily = (bp.resample("1D").max() - bp.resample("1D").min()).where(cover >= MIN_DAY_COVERAGE)
    rows = []
    for day, rng in daily.dropna().sort_values(ascending=False).items():
        d = bp[day:day + pd.Timedelta(days=1)]
        t_max = d.abs().idxmax()
        win = x[t_max - pd.Timedelta(minutes=EVENT_WINDOW_MIN // 2):
                t_max + pd.Timedelta(minutes=EVENT_WINDOW_MIN // 2 - 1)]
        if len(win) < EVENT_WINDOW_MIN or win.isna().any():
            continue
        f, psd, _ = welch(win, n=EVENT_WINDOW_MIN)
        hi = f[np.argmax(np.where(f >= MILGHUBA[0], psd, 0))]
        rows.append((t_max, rng, band_fraction(f, psd, MILGHUBA),
                     band_fraction(f, psd, BASIN_PREDICTED), hi))
        if len(rows) == N_EVENTS:
            break
    return rows, bp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)

    series = {}
    for name in ("senglea", "marsaxlokk", "cirkewwa"):
        s = load(name)
        if s is None:
            if name == "senglea":
                print("missing senglea_wl_1min.csv, run download_jrc_tad_wl.py", file=sys.stderr)
                return 1
            continue
        x, st = quality_control(s)
        print(f"{name:10s} {x.index[0]:%Y-%m-%d} to {x.index[-1]:%Y-%m-%d}  "
              f"valid {st['valid'] / st['span']:.1%} of {st['span']} min; removed "
              f"stuck {st['stuck']}, jumps {st['jump']}, offset episodes {st['offset']}, "
              f"spikes {st['spikes']} min")
        if name == "senglea":
            x = in_windows(x)
            for a, b in CLEAN_WINDOWS:
                w = x[a:b]
                print(f"{'':10s} window {a} to {b[:10]}: {w.notna().mean():.1%} valid")
        series[name] = x
    print()

    f, psd, nseg = welch(series["senglea"])
    print(f"Senglea mean spectrum from {nseg} segments of {SEGMENT_MIN} min "
          f"({SEGMENT_MIN / 60:.1f} h), resolution {60 / SEGMENT_MIN:.3f} cph\n")
    print("Peaks between 2 and 10 cph standing at least twice above the background,")
    print("maxima within 15 per cent in frequency merged")
    print(f"  {'f, cph':>7s} {'period, min':>12s} {'peak / background':>18s}")
    for fp, ratio in peaks(f, psd):
        flag = "  <- predicted basin band" if BASIN_PREDICTED[0] <= fp <= BASIN_PREDICTED[1] else ""
        print(f"  {fp:7.2f} {60 / fp:12.1f} {ratio:18.2f}{flag}")
    print()

    print(f"Share of the 0.2-10 cph variance, mean spectrum: milghuba band "
          f"{band_fraction(f, psd, MILGHUBA):.0%}, predicted basin band "
          f"{band_fraction(f, psd, BASIN_PREDICTED):.0%}\n")

    rows, bp = events(series["senglea"])
    print(f"The {N_EVENTS} days of largest range in the 0.2-10 cph band, "
          f"spectrum over {EVENT_WINDOW_MIN // 60} h around the maximum")
    print(f"  {'time of maximum (UTC)':22s} {'range, m':>9s} {'milghuba':>9s} "
          f"{'basin':>7s} {'peak f, cph':>12s} {'period, min':>12s}")
    for t, rng, fm, fb, fp in rows:
        print(f"  {t:%Y-%m-%d %H:%M}       {rng:9.3f} {fm:9.0%} {fb:7.0%} "
              f"{fp:12.2f} {60 / fp:12.1f}")
    print()

    ratios = {}
    for other in ("marsaxlokk", "cirkewwa"):
        if other not in series:
            continue
        a, b = series["senglea"].align(series[other], join="inner")
        both = a.where(b.notna())
        fo, po, no = welch(b.where(a.notna()))
        fs, ps, ns = welch(both)
        if fo is None or fs is None:
            print(f"no common gap-free segment with {other}")
            continue
        ratios[other] = (fs, ps / po)
        print(f"Senglea / {other}, {ns} common segments, amplitude ratio sqrt(PSD)")
        for lo, hi in ((0.2, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 3.0), BASIN_PREDICTED, (5.0, 8.0)):
            sel = (fs >= lo) & (fs < hi)
            print(f"  {lo:4.2f} to {hi:4.2f} cph  {np.sqrt(np.median(ps[sel] / po[sel])):5.2f}")
        print()

    if args.figure:
        plot(f, psd, rows, bp, series, ratios)
    return 0


def plot(f, psd, rows, bp, series, ratios) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "xtick.color": C_TEXT2, "ytick.color": C_TEXT2})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))

    def bands(ax):
        ax.axvspan(*MILGHUBA, color=C_BAND, zorder=0)
        ax.axvspan(*BASIN_PREDICTED, color="#cde2fb", zorder=0)

    ax = axes[0, 0]
    bands(ax)
    ax.loglog(f[1:], psd[1:], color=C_SERIES[0], lw=1.5, label="Senglea, mean spectrum")
    ax.loglog(f[1:], background(f, psd)[1:], color=C_TEXT2, lw=1, ls="--",
              label="background, running median")
    ax.set_xlim(0.03, 30)
    ax.set_xlabel("frequency, cph")
    ax.set_ylabel("PSD, m² cph⁻¹")
    ax.set_title("Mean spectrum inside the Grand Harbour", fontsize=9, loc="left")
    ax.text(0.45, 0.04, "milgħuba band", transform=ax.transAxes, color=C_TEXT2, fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")

    ax = axes[0, 1]
    bands(ax)
    ax.semilogx(f[1:], (psd / background(f, psd))[1:], color=C_SERIES[0], lw=1.5)
    ax.axhline(1, color=C_TEXT2, lw=0.8)
    ax.set_xlim(0.5, 30)
    ax.set_xlabel("frequency, cph")
    ax.set_ylabel("PSD / background")
    ax.set_title("Peaks above the background, shaded blue the predicted basin band",
                 fontsize=9, loc="left")

    ax = axes[1, 0]
    t0 = rows[0][0]
    seg = bp[t0 - pd.Timedelta(hours=6):t0 + pd.Timedelta(hours=6)]
    ax.plot((seg.index - t0).total_seconds() / 3600, seg, color=C_SERIES[0], lw=1.2)
    ax.axhline(0, color="#d6d5d0", lw=0.8)
    ax.set_xlabel(f"hours from {t0:%Y-%m-%d %H:%M} UTC")
    ax.set_ylabel("band-passed level, 0.2 to 10 cph, m")
    ax.set_title("Largest event in the record", fontsize=9, loc="left")

    ax = axes[1, 1]
    if ratios:
        bands(ax)
        for (name, (fr, r)), c in zip(ratios.items(), C_SERIES[1:]):
            ax.semilogx(fr[1:], np.sqrt(r[1:]), color=c, lw=1.5,
                        label=f"Senglea / {name.capitalize()}")
        ax.axhline(1, color=C_TEXT2, lw=0.8)
        ax.set_xlim(0.1, 30)
        ax.set_xlabel("frequency, cph")
        ax.set_ylabel("amplitude ratio")
        ax.set_title("Senglea against gauges outside the harbour", fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=8)
    else:
        ax.axis("off")

    for ax in axes.ravel():
        ax.grid(color="#e8e7e3", lw=0.6, which="both")
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb")
    print(f"figure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())
