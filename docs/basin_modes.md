# Fundamental long-wave mode of the two harbours from the measured geometry

*Computed 30 September 2026 by `scripts/estimate_basin_modes.py` from the aligned working pair in EPSG:4326, the inputs from which the mesh will be interpolated. Figure at `figures/basin_modes.png`. Supersedes the Helmholtz estimate of Section 2 of [domain_and_discretisation.md](domain_and_discretisation.md) and the scoping of Section 4.4 of [research_question_and_literature.md](research_question_and_literature.md).*

---

## 1. Method

The sizing exercise bracketed the basin period with a quarter-wave and a Helmholtz idealisation, both on nominal dimensions and on an unobstructed mouth 400 m wide. Both are replaced here by the one-dimensional long-wave eigenproblem of a channel of varying section, the Webster equation,

g d/dx ( a(x) dη/dx ) + ω² b(x) η = 0,

with η = 0 at the mouth and no flux at the head. The quarter-wave resonator is its limit for a uniform channel and the Helmholtz resonator its limit for a narrow neck ahead of a wide basin, so the choice between the two idealisations is made by the geometry rather than in advance.

The coordinate x is the geodesic distance through the water from a section line closing each harbour from the sea, computed by Dijkstra on the 8-connected grid of wet cells. The surface width b(x) = dA/dx and the cross-section a(x) = dV/dx follow from the area and the volume enclosed within each distance. Branches at a common distance are summed, which treats them as oscillating in phase, an assumption that holds for the fundamental mode and not for the higher ones, which are therefore not reported. The solver returns 4L/√(gh) for a uniform channel to within 0.5 per cent, and the period changes by less than 0.1 minute between distance bins of 10, 25 and 50 m.

Two section lines are carried for each harbour. For the Grand Harbour the outer line encloses the St Elmo breakwater, so that the restriction falls inside the computed profile, and the inner line runs along the breakwater axis and across the opening to the Ricasoli shore. Radiation through the mouth is represented by the length correction of Rabinovich (2009, eq. 9.16), derived for a fully open rectangular basin and applied here at the section line. T₀ denotes the period without it and T the period with it, and the two bound the estimate from below and above.

The breakwater is removed by filling its polygon with water at the depth of the nearest wet cells, a median of 13.5 m, which isolates the structure from every other element of the geometry.

---

## 2. Periods

| Basin | Section line | Variant | Area | Length | Neck section | Median section | T₀ | T | f |
|---|---|---|---|---|---|---|---|---|---|
| Grand Harbour | outer | as supplied | 2.26 km² | 3.73 km | 8 780 m² | 9 360 m² | 16.5 min | 18.4 min | 3.26 cph |
| Grand Harbour | outer | no breakwater | 2.27 km² | 3.73 km | 8 050 m² | 9 060 m² | 16.6 min | 18.4 min | 3.25 cph |
| Grand Harbour | inner | as supplied | 2.02 km² | 3.45 km | 12 340 m² | 8 620 m² | 14.5 min | 16.8 min | 3.58 cph |
| Marsamxett | outer | as supplied | 1.18 km² | 2.53 km | 7 310 m² | 7 630 m² | 10.7 min | 12.8 min | 4.70 cph |
| Marsamxett | inner | as supplied | 1.08 km² | 2.41 km | 6 330 m² | 7 560 m² | 10.4 min | 12.3 min | 4.89 cph |

The neck section is the smallest a(x) within 600 m of the section line and the median section is taken over the whole basin.

The fundamental period of the Grand Harbour lies between 14.5 and 18.4 minutes and that of Marsamxett between 10.4 and 12.8 minutes. The Grand Harbour figure agrees with the earlier bracket of 12.4 to 17.5 minutes. The Marsamxett figure is shorter than the earlier 13.3 to 17.8 minutes, since the basin measured through the water is 2.4 to 2.5 km long, against the 3.15 km diagonal of the rectangle on which the earlier estimate rested, and it shoals toward the heads of its creeks.

Both harbours remain outside the milgħuba band. Reaching 2 cph requires a period of 30 minutes, which is 1.6 times the upper estimate for the Grand Harbour and 2.3 times that for Marsamxett. The conclusion of the sizing exercise, that the harbours respond to a shelf-scale oscillation rather than resonate within the band, is unchanged and its margin for Marsamxett is wider than previously stated.

---

## 3. Effect of the St Elmo breakwater

Removing the breakwater changes the period by 0.1 minute, below the resolution of the method. The neck section with the breakwater in place, 8 780 m², is within 6 per cent of the median section of the basin, so the entrance is not a neck in the sense the Helmholtz idealisation requires. The Grand Harbour behaves as a channel of slowly varying section, in which the inertia of the fundamental mode is distributed over its whole length rather than concentrated at the mouth.

The amendment of 25 September to the sizing document anticipated that the breakwater would lengthen the period toward the observed band, on the reasoning that it reduces the open section of the mouth. The reasoning applies to a Helmholtz resonator, and the measured geometry shows the harbour not to be one. The expected correction is therefore not found.

Two limits apply. The one-dimensional reduction redistributes rather than removes the section where the breakwater is taken out, since the geodesic distance shortens across its footprint, and a two-dimensional contraction at the gap is not represented. And the Ricasoli arm is not carried as a separate feature in the supplied coastline, so that the opening between the breakwater head and the Ricasoli shore measures some 400 m here. A narrower real opening would produce a neck the present geometry lacks, and the sensitivity in Section 4 bounds its effect.

---

## 4. Sensitivity to a restriction of the entrance

A restriction was imposed on the measured Grand Harbour profile over a reach centred on the narrowest section, at 162 m from the outer line, where T₀ = 16.5 minutes.

| Open fraction | Helmholtz scaling | 100 m reach | 250 m reach | 500 m reach |
|---|---|---|---|---|
| 0.75 | +15 % | +1.5 % | +2.7 % | +4.0 % |
| 0.50 | +41 % | +4.4 % | +8.0 % | +11.7 % |
| 0.25 | +100 % | +13.1 % | +23.3 % | +33.1 % |
| 0.10 | +216 % | +37.2 % | +62.5 % | +84.6 % |

For comparison, sea level rise on the same profiles with vertical quay walls gives the following.

| Basin | +0.3 m | +0.5 m | +1.0 m |
|---|---|---|---|
| Grand Harbour | −1.0 % | −1.6 % | −3.1 % |
| Marsamxett | −1.0 % | −1.6 % | −3.2 % |

The Helmholtz scaling T ∝ a^−1/2 of `scripts/estimate_entrance_restriction.py` overstates the sensitivity by a factor of between three and ten for the reaches considered, since it attributes the whole inertia of the system to the neck. A local restriction of a quarter over 100 to 500 m displaces the mode by 1.5 to 4 per cent, comparable to a metre of sea level rise rather than four times larger, and a restriction of a half displaces it by 4 to 12 per cent. Reaching the band from 18.4 minutes requires a lengthening of 63 per cent, which the table places at an open fraction near 0.1 over a reach of several hundred metres.

The geometry of the mouth therefore remains a control on the mode, but a weaker one than the scoping of Section 4.4 of the literature document stated, and of the same order as sea level rise. The effect on exchange, which scales with the open section directly, is unaffected by this correction and becomes the principal quantity of the counterfactual question.

---

## 5. Standing of the figures

The estimate remains first-order. The in-phase treatment of branches, the one-dimensional representation of a contraction and the mouth correction borrowed from an open rectangular basin all shift real modes, and only an eigenvalue analysis on the mesh or the response of the model to a broadband impulse will place them properly. The ordering against the milgħuba band is unlikely to reverse given a margin of a factor of 1.6 or more.

Senglea, inside the Grand Harbour at 5 s sampling, affords a direct test. A spectrum of its record should carry a peak between 3.3 and 4.1 cph if the estimate holds.
