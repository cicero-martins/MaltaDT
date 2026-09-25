"""Sensitivity of the harbour long-wave response to a restriction of the mouth.

The pumping mode of a harbour and the volume it exchanges with the sea are both
governed by the cross-section of its mouth. This script sweeps a restriction of
that cross-section and reports what it does to the mode, as an academic
sensitivity on the class of basin.

The exercise is not an assessment of any particular design. A wave protection
scheme for the Grand Harbour is in design and public consultation (Mazas and
Farrugia, ICCE; Grand Harbour Revival Plan, February 2026), and it enters here
only as evidence that restrictions of this order are realistic rather than
arbitrary. Nothing below represents its geometry, which is not public at the
precision a model would need, and the output is a curve rather than a verdict.

It is a scoping calculation and not a result. The basin is idealised as a
Helmholtz resonator and the mouth as a rectangle, whereas the entrance is in
fact partly closed by the 1910 breakwaters. It establishes the order of the
sensitivity and nothing further.

Geometry is taken from `domain_design_estimate.py`, which measured it from the
supplied bathymetry and coastline. The mouth cross-section follows the value
already used for the Helmholtz estimate in docs/domain_and_discretisation.md,
400 m wide over 15 m of depth.

Usage:
    python estimate_entrance_restriction.py
"""

from __future__ import annotations

import math

G = 9.81

# Measured by domain_design_estimate.py from the 10 m merged bathymetry.
BASINS = {
    "Grand Harbour": dict(area=1.64e6, width=400.0, depth=15.0),
    "Marsamxett": dict(area=1.32e6, width=350.0, depth=13.0),
}

# The length of the connecting channel is the least constrained parameter. The
# sizing document carries it as a range and the same range is kept here, since
# the quantity of interest is a ratio in which it cancels.
CHANNEL_LENGTHS = (500.0, 1000.0)

# The band within which the milghuba is observed, Drago (2009).
BAND_CPH = (0.2, 2.0)


def helmholtz_period(area: float, mouth_area: float, channel: float) -> float:
    """Period in seconds of the pumping mode, T = 2*pi*sqrt(L*A/(g*a))."""
    return 2 * math.pi * math.sqrt(channel * area / (G * mouth_area))


def main() -> None:
    print(__doc__.split("Usage:")[0].strip())
    print()

    # A restriction acts on the period only through the mouth cross-section, and
    # T scales as a**-0.5, so the shift is independent of every other parameter.
    print("Shift in the pumping period for a given restriction of the mouth")
    print("(independent of basin area and channel length, since T ~ a^-1/2)")
    print()
    print(f"  {'restriction':>12}  {'open fraction':>14}  {'period':>10}")
    for restriction in (0.0, 0.10, 0.25, 0.40, 0.50, 0.66):
        open_fraction = 1.0 - restriction
        shift = 1.0 / math.sqrt(open_fraction) - 1.0
        print(f"  {restriction:>11.0%}  {open_fraction:>14.2f}  {shift:>+9.1%}")
    print()

    for name, geom in BASINS.items():
        mouth = geom["width"] * geom["depth"]
        print(f"{name}: area {geom['area']/1e6:.2f} km2, "
              f"mouth {geom['width']:.0f} m x {geom['depth']:.0f} m "
              f"= {mouth:.0f} m2")
        print(f"  {'restriction':>12}  {'T (Lc=500 m)':>14}  {'T (Lc=1000 m)':>15}"
              f"  {'frequency range':>18}")
        for restriction in (0.0, 0.25, 0.50, 0.66):
            periods = [helmholtz_period(geom["area"], mouth * (1 - restriction), c)
                       for c in CHANNEL_LENGTHS]
            cph = [3600.0 / t for t in periods]
            flag = "" if min(cph) > BAND_CPH[1] else "  <- enters the band"
            print(f"  {restriction:>11.0%}  {periods[0]/60:>13.1f} min"
                  f"  {periods[1]/60:>14.1f} min"
                  f"  {cph[1]:>7.2f}-{cph[0]:.2f} cph{flag}")

        # How severe a restriction would be required to reach the observed band.
        for channel, label in zip(CHANNEL_LENGTHS, ("shortest", "longest")):
            t_band = 3600.0 / BAND_CPH[1]
            t_now = helmholtz_period(geom["area"], mouth, channel)
            # T scales as a^-1/2, so a_needed/a = (T_now/T_band)^2.
            needed = 1.0 - (t_now / t_band) ** 2
            print(f"  To reach {BAND_CPH[1]:.0f} cph on the {label} channel, "
                  f"the mouth would have to lose {needed:.0%} of its section.")
        print()

    # The comparison that gives the figure its meaning. A metre of sea level
    # rise displaces these same modes by a few per cent, computed in
    # docs/research_question_and_literature.md section 6.3.
    slr_shift = 0.036  # Marsamxett, the largest of the two, for +1.0 m
    for restriction in (0.25, 0.50):
        shift = 1.0 / math.sqrt(1 - restriction) - 1.0
        print(f"A {restriction:.0%} restriction shifts the mode "
              f"{shift / slr_shift:.0f} times as far as a metre of sea level "
              f"rise does.")


if __name__ == "__main__":
    main()
