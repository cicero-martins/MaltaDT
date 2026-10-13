"""Illustration of atmospheric pressure as the forcing of the long wave.

Three panels share one axis, the distance from the centre of a pressure rise of
Gaussian shape, the one of build_proudman_channel_test.py:

- the pressure rise, the quantity given to the model;
- the level the sea takes if the rise stands still, the inverse barometer or
  static response, a depression of one centimetre for each hectopascal;
- the level when the same rise travels over a flat bed at 150 m, at 0.6 and at
  1.0 times the long-wave celerity, after 100 and 300 km, from the closed form
  of analyse_proudman_channel_test.py.

Usage:
    python figure_pressure_forcing.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_proudman_channel_test as ac  # noqa: E402
import build_proudman_channel_test as bp  # noqa: E402

FIGURE = bp.ROOT / "figures" / "pressure_forcing.png"
C_INK = "#0b0b0b"
C_STATIC = "#52514e"
C_SLOW = "#2a78d6"
C_RES_NEAR = "#f0a37f"
C_RES_FAR = "#eb6834"


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xi = np.linspace(-70e3, 70e3, 1401)          # distance from the centre of the rise
    rise = bp.P_RISE * np.exp(-xi ** 2 / (2 * bp.SIGMA_X ** 2))
    static = ac.eta_s(xi)

    def moving(froude, travelled):
        t = travelled / (froude * bp.CELERITY)
        return ac.closed_form(travelled + xi, t, froude)

    plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": C_INK, "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig, axes = plt.subplots(3, 1, figsize=(8.6, 9.2), sharex=True,
                             gridspec_kw=dict(height_ratios=[1, 1, 1.5]))

    ax = axes[0]
    ax.fill_between(xi / 1e3, rise / 100, color="#c9d6e8", lw=0)
    ax.plot(xi / 1e3, rise / 100, color=C_INK, lw=1.8)
    k = int(np.argmin(np.abs(xi - bp.SIGMA_X)))
    ax.annotate("steepest slope, 1 hPa in 9.5 km,\nwhere the air pushes the\nwater sideways most",
                xy=(xi[k] / 1e3, rise[k] / 100), xytext=(30, 1.4), fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#52514e", lw=0.9), color="#52514e")
    ax.set_ylabel("pressure rise, hPa")
    ax.set_title("1. The input: pressure above its surroundings", fontsize=10, loc="left")

    ax = axes[1]
    ax.fill_between(xi / 1e3, static * 100, color="#d9d8d3", lw=0)
    ax.plot(xi / 1e3, static * 100, color=C_STATIC, lw=1.8)
    ax.annotate("2 hPa press the sea down by 2 cm", xy=(0, static.min() * 100),
                xytext=(22, -1.6), fontsize=8.5, color="#52514e",
                arrowprops=dict(arrowstyle="->", color="#52514e", lw=0.9))
    ax.set_ylabel("water level, cm")
    ax.set_title("2. If the rise stands still: the static response, 1 cm for each hPa",
                 fontsize=10, loc="left")

    ax = axes[2]
    ax.plot(xi / 1e3, static * 100, color=C_STATIC, lw=1.3, ls="--", label="standing still")
    ax.plot(xi / 1e3, moving(0.6, 300e3) * 100, color=C_SLOW, lw=1.8,
            label="travelling at 0.6 of the wave speed, any distance")
    ax.plot(xi / 1e3, moving(1.0, 100e3) * 100, color=C_RES_NEAR, lw=1.8,
            label="travelling at the wave speed, after 100 km")
    ax.plot(xi / 1e3, moving(1.0, 300e3) * 100, color=C_RES_FAR, lw=2.0,
            label="travelling at the wave speed, after 300 km")
    ax.set_ylabel("water level, cm")
    ax.set_xlabel("distance from the centre of the pressure rise, km")
    ax.set_title("3. If the rise travels: the response depends on its speed and on the "
                 "distance travelled", fontsize=10, loc="left")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_xlim(-70, 70)

    for ax in axes:
        ax.axhline(0, color="#d6d5d0", lw=0.8, zorder=0)
        ax.grid(color="#e8e7e3", lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb")
    slope = bp.P_RISE * np.exp(-0.5) / bp.SIGMA_X
    print(f"steepest pressure slope {slope * 1e3:.1f} Pa per km, equal to a sea surface slope of "
          f"{slope / (bp.RHO * bp.G) * 1e6:.2f} mm per km")
    print(f"peaks, cm: static {abs(static).max() * 100:.2f}, Fr 0.6 "
          f"{np.abs(moving(0.6, 300e3)).max() * 100:.2f}, Fr 1 at 100 km "
          f"{np.abs(moving(1.0, 100e3)).max() * 100:.2f}, at 300 km "
          f"{np.abs(moving(1.0, 300e3)).max() * 100:.2f}")
    print(f"figure written to {FIGURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
