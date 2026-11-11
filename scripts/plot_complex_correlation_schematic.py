"""Schematic of the complex correlation of Kundu (1976) for the HF radar comparison.

A synthetic hourly current stands for the radar, and a second series formed
from it by a rotation, a change of amplitude and added noise stands for the
model. The figure shows the two series as vectors, their fluctuations in the
(u, v) plane, and the complex correlation in the complex plane for a set of
cases, with the value found over the corridor of the drifter tracks in 2025.

Output: figures/complex_correlation_schematic.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "complex_correlation_schematic.png"


def complex_correlation(w1, w2):
    """Kundu (1976) complex correlation of two demeaned vector series w = u + iv."""
    a = w1 - w1.mean()
    b = w2 - w2.mean()
    return np.mean(np.conj(a) * b) / np.sqrt(np.mean(np.abs(a) ** 2) * np.mean(np.abs(b) ** 2))


def main():
    rng = np.random.default_rng(3)
    t = np.arange(72.0)  # hours
    # Reference series: a mean southward drift, an inertial rotation (~21 h at
    # 36 N) and a slower wind-driven pulse.
    radar = (-0.10j
             + 0.12 * np.exp(-2j * np.pi * t / 21.0)
             + 0.15 * np.exp(-((t - 36.0) / 10.0) ** 2) * np.exp(-1j * np.pi / 2.5))
    theta = np.radians(30.0)
    model_clean = 0.6 * radar * np.exp(1j * theta)
    noise = 0.02 * (rng.standard_normal(t.size) + 1j * rng.standard_normal(t.size))
    model = model_clean + noise

    cases = {
        "identical": radar,
        "rotated 30°": radar * np.exp(1j * theta),
        "rotated 30°, amplitude ×0.6": model_clean,
        "rotated 30°, ×0.6, with noise": model,
        "unrelated": 0.1 * (rng.standard_normal(t.size) + 1j * rng.standard_normal(t.size)),
    }
    rho = {k: complex_correlation(radar, v) for k, v in cases.items()}
    for k, r in rho.items():
        print(f"{k:32s} |rho| = {abs(r):.2f}  phase = {np.degrees(np.angle(r)):+.0f} deg")

    fig = plt.figure(figsize=(13, 4.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.5, 1, 1], wspace=0.32)

    # (a) stick plot
    ax = fig.add_subplot(gs[0])
    step = 4
    for w, y0, c, lab in ((radar, 0.0, "k", "radar"), (model, -0.2, "tab:red", "model")):
        tt = t[::step]
        ww = w[::step]
        ax.quiver(tt, np.full(tt.size, y0), ww.real, ww.imag, color=c, angles="uv",
                  scale_units="y", scale=3.0, width=0.005, headwidth=2, headlength=2.5)
        ax.text(-2, y0 + 0.07, lab, color=c, fontsize=9)
    ax.set(xlim=(-4, 74), ylim=(-0.32, 0.12), xlabel="time (h)", yticks=[])
    ax.set_title("(a) Hourly current vectors", loc="left", fontsize=10)

    # (b) fluctuations in the (u, v) plane
    ax = fig.add_subplot(gs[1])
    a = radar - radar.mean()
    b = model - model.mean()
    ax.plot(a.real, a.imag, "k.-", lw=0.6, ms=3, label="radar, w′")
    bc = model_clean - model_clean.mean()
    ax.plot(bc.real, bc.imag, "-", color="tab:red", lw=0.8, label="model without noise")
    ax.plot(b.real, b.imag, ".", color="tab:red", ms=3, label="model, w′")
    i = int(np.argmax(np.abs(a)))
    for w, c in ((a, "k"), (bc, "tab:red")):
        ax.annotate("", xy=(w[i].real, w[i].imag), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.5))
    ax.axhline(0, color="0.8", lw=0.5)
    ax.axvline(0, color="0.8", lw=0.5)
    ax.set(aspect="equal", xlabel="u′ (m/s)", ylabel="v′ (m/s)")
    ax.set_title("(b) Fluctuations about the mean", loc="left", fontsize=10)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False)

    # (c) complex plane
    ax = fig.add_subplot(gs[2])
    phi = np.linspace(0, 2 * np.pi, 361)
    ax.plot(np.cos(phi), np.sin(phi), color="0.6", lw=0.8)
    ax.plot(0.5 * np.cos(phi), 0.5 * np.sin(phi), color="0.85", lw=0.6)
    ax.axhline(0, color="0.8", lw=0.5)
    ax.axvline(0, color="0.8", lw=0.5)
    markers = ["o", "s", "D", "^", "x"]
    for (k, r), m in zip(rho.items(), markers):
        ax.plot(r.real, r.imag, m, ms=7, mfc="none" if m != "x" else None, label=k)
    r25 = 0.74 * np.exp(1j * np.radians(-21.0))
    ax.plot(r25.real, r25.imag, "*", color="tab:blue", ms=12,
            label="model, corridor 2025 (0.74, −21°)")
    r_m = rho["rotated 30°, ×0.6, with noise"]
    ax.annotate("", xy=(r_m.real, r_m.imag), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="0.3", lw=1))
    arc = np.linspace(0, np.angle(r_m), 30)
    ax.plot(0.3 * np.cos(arc), 0.3 * np.sin(arc), color="0.3", lw=0.8)
    ax.text(0.32, 0.07, "phase", fontsize=8, color="0.3")
    ax.text(0.42 * np.cos(np.angle(r_m)) - 0.2, 0.42 * np.sin(np.angle(r_m)) + 0.05,
            "|ρ|", fontsize=9, color="0.3")
    ax.set(aspect="equal", xlim=(-1.1, 1.1), ylim=(-1.1, 1.1), xlabel="Re ρ", ylabel="Im ρ")
    ax.set_title("(c) Complex correlation ρ", loc="left", fontsize=10)
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
