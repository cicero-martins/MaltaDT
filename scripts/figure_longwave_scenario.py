"""Illustration of one scenario of the long-wave sweep, its track and its ramp.

Draws, for one direction of arrival and one speed, the track of the pressure
disturbance over the outer domain with its footprint at five instants, the
amplitude of the disturbance against time, and the pressure rise along the
track at the same instants. The quantities are those of
build_longwave_scenario.py, from which the track, the ramp and the footprint
are taken.

Usage:
    python figure_longwave_scenario.py [--heading 225] [--speed 36]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_longwave_scenario as bl  # noqa: E402
import build_mesh_outer as bo  # noqa: E402

FIGURE = bl.ROOT / "figures" / "longwave_scenario_track_ramp.png"
C_TRACK = "#0b0b0b"
C_INSTANTS = ("#8a8984", "#2a78d6", "#eb6834", "#1baf7a", "#8a8984")
C_LAND = "#d6d5d0"


def main(argv=None) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from matplotlib.patches import Rectangle
    from pyproj import Transformer

    ap = argparse.ArgumentParser()
    ap.add_argument("--heading", type=float, default=225.0,
                    help="direction of travel, degrees clockwise from north")
    ap.add_argument("--speed", type=float, default=36.0, help="m/s")
    args = ap.parse_args(argv)

    speed = args.speed
    t_track = 2 * bl.TRACK_HALF / speed
    (xt, yt), (ex, ey) = bl.track(args.heading)
    back = Transformer.from_crs(bl.METRIC, bl.CRS, always_xy=True)

    def position(s):
        """Longitude and latitude at distance s from the start of the track."""
        return back.transform(xt + (s - bl.TRACK_HALF) * ex, yt + (s - bl.TRACK_HALF) * ey)

    def footprint(s, n=1.0):
        """Ellipse of n standard deviations around the centre at distance s."""
        a = np.linspace(0, 2 * math.pi, 181)
        along = n * bl.SIGMA_ALONG * np.cos(a)
        across = n * bl.SIGMA_ACROSS * np.sin(a)
        x = xt + (s - bl.TRACK_HALF + along) * ex - across * ey
        y = yt + (s - bl.TRACK_HALF + along) * ey + across * ex
        return back.transform(x, y)

    # Five instants: the start, the end of the rise, the passage over the
    # harbours, the beginning of the lowering and the end.
    instants = (0.0, bl.RAMP, bl.TRACK_HALF / speed, t_track - bl.RAMP, t_track)
    labels = ("start, amplitude zero", "end of the rise", "over the harbours",
              "lowering begins", "end, amplitude zero")
    amp = bl.amplitude(np.asarray(instants), t_track)

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig = plt.figure(figsize=(13.5, 6.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], hspace=0.42, wspace=0.2)
    ax = fig.add_subplot(gs[:, 0])

    with rasterio.open(bo.CHANNEL) as src:
        z = src.read(1)
        b = src.bounds
    depth = np.where(z < 0, -z, np.nan)
    ax.imshow(np.where(z >= 0, 1.0, np.nan), extent=(b.left, b.right, b.bottom, b.top),
              cmap="Greys", vmin=0, vmax=4, interpolation="nearest")
    ax.contourf(np.linspace(b.left, b.right, z.shape[1]), np.linspace(b.top, b.bottom, z.shape[0]),
                depth, levels=[70, 190], colors=["#f6c9b5"])
    o = bo.OUTER_LONLAT
    ax.add_patch(Rectangle((o[0], o[1]), o[2] - o[0], o[3] - o[1], fill=False,
                           edgecolor="#52514e", lw=1.4))
    ax.text(o[0] + 0.05, o[3] - 0.12, "outer domain, open boundary", fontsize=8, color="#52514e")
    d = bo.DOMAIN_B_LONLAT
    ax.add_patch(Rectangle((d[0], d[1]), d[2] - d[0], d[3] - d[1], fill=False,
                           edgecolor="#52514e", lw=0.9, ls="--"))
    ax.text(d[0] + 0.03, d[1] - 0.11, "domain B", fontsize=8, color="#52514e")

    lon0, lat0 = position(0.0)
    lon1, lat1 = position(2 * bl.TRACK_HALF)
    ax.annotate("", xy=(lon1, lat1), xytext=(lon0, lat0),
                arrowprops=dict(arrowstyle="-|>", color=C_TRACK, lw=1.6))
    ax.text(lon0 + 0.06, lat0 + 0.06, "track, 400 km", fontsize=8.5, color=C_TRACK)
    for t, a, c, lab in zip(instants, amp, C_INSTANTS, labels):
        lon, lat = footprint(speed * t)
        ax.plot(lon, lat, color=c, lw=0.8 + 2.2 * a, ls="-" if a > 0.01 else ":")
        lon, lat = footprint(speed * t, 2.0)
        ax.plot(lon, lat, color=c, lw=0.6, ls=":", alpha=0.8)
    ax.plot(*bl.TARGET, "o", color="#0b0b0b", ms=5, mec="#fcfcfb", mew=1.2)
    ax.text(bl.TARGET[0] - 0.62, bl.TARGET[1] - 0.2, "Valletta", fontsize=8.5)
    ax.plot([], [], "s", color="#f6c9b5", label="depth of 70 to 190 m")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_xlim(o[0] - 0.25, o[2] + 0.25)
    ax.set_ylim(o[1] - 0.2, o[3] + 0.2)
    ax.set_aspect(1 / math.cos(math.radians(36.0)))
    ax.set_title("Track and footprint of the disturbance, one and two standard deviations",
                 fontsize=9, loc="left")

    ax = fig.add_subplot(gs[0, 1])
    t = np.linspace(0, t_track, 601)
    ax.fill_between([0, bl.RAMP / 3600], 0, 1.05, color="#e8e7e3", lw=0)
    ax.fill_between([(t_track - bl.RAMP) / 3600, t_track / 3600], 0, 1.05, color="#e8e7e3", lw=0)
    ax.plot(t / 3600, bl.amplitude(t, t_track), color=C_TRACK, lw=1.8)
    for ti, a, c in zip(instants, amp, C_INSTANTS):
        ax.plot(ti / 3600, a, "o", color=c, ms=7, mec="#fcfcfb", mew=1.5, zorder=5)
    ax.text(bl.RAMP / 7200, 0.52, "ramp,\nrise", ha="center", fontsize=8, color="#52514e")
    ax.text((t_track - bl.RAMP / 2) / 3600, 0.52, "ramp,\nlowering", ha="center", fontsize=8,
            color="#52514e")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, t_track / 3600)
    ax.set_xlabel("time from the start, h")
    ax.set_ylabel("amplitude, fraction of 2 hPa")
    ax.set_title(f"Amplitude against time, at {speed * 3.6:.0f} km/h", fontsize=9, loc="left")
    top = ax.secondary_xaxis("top", functions=(lambda h: h * 3.6 * speed, lambda s: s / 3.6 / speed))
    top.set_xlabel("distance travelled along the track, km")

    ax = fig.add_subplot(gs[1, 1])
    s = np.linspace(-60e3, 2 * bl.TRACK_HALF + 60e3, 1200)
    for ti, a, c, lab in zip(instants, amp, C_INSTANTS, labels):
        p = bl.P_RISE * a * np.exp(-(s - speed * ti) ** 2 / (2 * bl.SIGMA_ALONG ** 2))
        ax.plot(s / 1e3, p / 100, color=c, lw=1.8, label=f"{ti / 3600:.2f} h, {lab}")
    ax.axvline(bl.TRACK_HALF / 1e3, color="#0b0b0b", lw=0.8, ls="--")
    ax.text(bl.TRACK_HALF / 1e3 + 6, 1.82, "Valletta", fontsize=8)
    ax.set_xlim(s[0] / 1e3, s[-1] / 1e3)
    ax.set_ylim(0, 2.1)
    ax.set_xlabel("distance along the track, km")
    ax.set_ylabel("pressure rise, hPa")
    ax.set_title("Pressure rise along the track at the five instants", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(0.0, -0.28), ncol=2)

    for a in fig.axes[1:]:
        a.grid(color="#e8e7e3", lw=0.6)
        a.set_axisbelow(True)
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb", bbox_inches="tight")
    print(f"figure written to {FIGURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
