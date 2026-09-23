# Model domain, horizontal resolution and vertical layering: a sizing exercise

*Prepared 23 September 2026 for discussion with the host group. Computed by `scripts/domain_design_estimate.py` from the bathymetry obtained on 22 September and the coastline obtained on 23 September. Figure at `figures/domain_design.png`.*

The exercise settles three questions that precede mesh construction. The conclusions rest on measurement of the supplied bathymetry rather than on nominal figures, and each is stated so that it can be contested.

---

## 1. Measured geometry of the two basins

| | Grand Harbour | Marsamxett |
|---|---|---|
| Water area | 1.64 km² | 1.32 km² |
| Volume | 26.1 × 10⁶ m³ | 17.6 × 10⁶ m³ |
| Mean depth | 15.9 m | 13.3 m |
| Median depth | 16.0 m | 13.0 m |
| Maximum depth | 28 m | 30 m |
| Axis length | 3.22 km | 3.15 km |

Channel width was measured along the ridge of the distance transform of the water mask, which is where the distance to land equals the local half-width and the doubled value is therefore the true width. Measured anywhere else the distance transform reports proximity to the shore rather than the width of the channel, and understates it.

| Percentile of channel length | Grand Harbour | Marsamxett |
|---|---|---|
| p10 | 55 m | 29 m |
| p25 | 126 m | 45 m |
| p50 | 193 m | 135 m |
| p75 | 316 m | 271 m |
| p90 | 367 m | 361 m |

Half the channel length of Marsamxett lies in water narrower than 135 m and a third of it narrower than 50 m. The Grand Harbour is the broader of the two, with a fifth of its channel length narrower than 100 m.

---

## 2. Domain extent

### The question is where the seiche energy originates

Quarter-wave periods were computed for each element of the system as T = 4L/√(gh) and set against the milgħuba band of 0.2 to 2 cph reported by Drago (2009), corresponding to periods between 30 minutes and 5 hours.

| Element | L | h | Period | Frequency | Relative to the band |
|---|---|---|---|---|---|
| Malta Plateau to Sicily, quarter wave | 90 km | 150 m | 156 min | 0.38 cph | **within** |
| Malta Plateau to Sicily, half wave | 90 km | 150 m | 78 min | 0.77 cph | **within** |
| Near plateau | 25 km | 120 m | 49 min | 1.24 cph | **within** |
| Grand Harbour | 3.2 km | 16 m | 17 min | 3.49 cph | outside |
| Marsamxett | 3.2 km | 13 m | 18 min | 3.26 cph | outside |
| A 1 km inlet | 1.0 km | 12 m | 6 min | 9.76 cph | outside |
| A 600 m inlet | 0.6 km | 10 m | 4 min | 14.86 cph | outside |

The plateau geometry was verified rather than assumed. A transect north along 14.50°E from Malta to the Sicilian coast returns depths between 99 and 190 m continuously over some 90 km, and a transect east along 35.95°N remains between 70 and 137 m as far as 15.25°E, so the Malta Escarpment lies beyond that meridian at this latitude.

**The harbours and their inlets resonate above the observed band. The plateau resonates within it.** The harbours therefore respond to a shelf-scale oscillation rather than generating one, which is consistent with Drago's interpretation of the milgħuba as the expression of shelf-scale resonance amplified within the embayments.

The consequence for the model is direct. A domain confined to the harbours contains no resonator in the band and cannot produce the signal under study. It could only receive that signal through its open boundary, and the available boundary product, CMEMS MED-MFC at hourly resolution, carries no energy in the band. Such a domain would have to be driven by the Portomaso record, which is a single coastal station outside both basins, and validating the harbour response against a signal imposed from a neighbouring gauge is close to circular.

### The extent costs almost nothing

| Domain | Extent | Area | Cells | Longest resonator it holds |
|---|---|---|---|---|
| A, harbours and approaches | 16 × 15 km | 251 km² | ~25,900 | 28 min, 2.13 cph, outside |
| **B, Malta and the near plateau** | **86 × 66 km** | **5,676 km²** | **~28,500** | **149 min, 0.40 cph, within** |
| C, plateau to Sicily | 126 × 127 km | 15,997 km² | ~33,700 | 221 min, 0.27 cph, within |

Cell counts assume the graded scheme of Section 3 and include a factor of 1.5 for the transition zones required to keep the size ratio between neighbouring cells near 1.25.

**Domain B costs a tenth more cells than domain A while covering twenty-two times the area.** The additional area is entirely offshore and coarsely resolved, so it is nearly free. This is the principal argument for the unstructured approach over the structured nesting used by ROSARIO-I, and it is worth stating in the paper as such, since a single graded mesh spanning from 1.5 km on the plateau to 15 m in an inlet is the capability the framework brings.

**Recommendation: domain B**, extending west and north over the plateau and east to approximately 15.0°E, short of the escarpment. Domain C is available if the half-wave mode between Malta and Sicily proves to matter, at a further 18 per cent in cells.

### What remains unresolved

The trigger. ERA5 at 0.25 degrees and hourly resolution does not resolve the atmospheric gravity waves that initiate the milgħuba. Domain B can support the shelf response but will not spontaneously generate it from ERA5 forcing. Three routes exist and the choice is a question for the host group.

1. Reconstruct a propagating pressure disturbance from the one-minute records of the PORTO network and impose it over the domain. This is the physically complete route and the most demanding.
2. Force the model with a synthetic pressure disturbance of prescribed speed and amplitude and ask whether the shelf and harbour system reproduces the observed periods and the mouth-to-head amplification. The model then tests the response of the geometry, which is the well-posed question already adopted.
3. Impose the observed sea level at the offshore boundary from a tide gauge or an HF-radar-derived surface, accepting the limitations discussed above.

Route 2 is the one the current plan assumes.

---

## 3. Horizontal resolution

Cells across a channel, by channel width and candidate cell size:

| Channel width | Δ = 15 m | Δ = 30 m | Δ = 100 m |
|---|---|---|---|
| 50 m | 3.3 | 1.7 | 0.5 |
| 100 m | 6.7 | 3.3 | 1.0 |
| 150 m | 10.0 | 5.0 | 1.5 |
| 200 m | 13.3 | 6.7 | 2.0 |
| 300 m | 20.0 | 10.0 | 3.0 |

Four to five cells carry the conveyance of a channel and eight to ten resolve the flow across it.

**The binding constraint is geometry, not the wave.** A long wave of 17-minute period in 16 m of water has a wavelength of 12.8 km, which twenty cells per wavelength would resolve at 640 m. The wave imposes no meaningful requirement at these scales. What the resolution must capture is the planform and the cross-section of the inlets and the entrances, because those control the exchange and the storage.

**Proposed grading**

| Zone | Target Δ | Justification |
|---|---|---|
| Inlets and entrances, width below 150 m | 15 m | Gives 4 cells at 60 m width and 10 at 150 m. Equals the source data resolution, so no further refinement adds information |
| Harbour basins | 30 m | 5 cells at the 150 m width, 10 at the 300 m p90 |
| Nearshore, within 2 km | 100 m | |
| Coastal, 2 to 15 km | 300 m | |
| Open plateau, beyond 15 km | 1500 m | 60 cells across the 90 km resonator |

The 10 m of the source bathymetry is the floor. A mesh finer than 15 m would interpolate rather than resolve, and the additional cells would buy nothing.

**Time step.** At 15 m cells in 15 m of water the celerity is 12.1 m/s and a Courant number of unity requires 1.2 s. The implicit solver tolerates Courant numbers between five and ten, giving a time step of 6 to 12 s. A seiche of 17-minute period is then sampled at roughly 100 steps per cycle, which is ample.

**On coupling.** SWAN is not required for the seiche experiments and its omission roughly halves the cost of the long runs needed for a climatology. It is required for the storm case study and for validation against the wave record at BLUE and the HF radar. The recommendation is to run uncoupled for the seiche work and coupled for the events.

---

## 4. Vertical layering

Depth distribution over the water of the harbour window:

| Depth | Share of water area |
|---|---|
| 0 to 5 m | 5.6% |
| 5 to 10 m | 10.4% |
| 10 to 20 m | 26.2% |
| 20 to 30 m | 16.4% |
| 30 to 50 m | 21.8% |
| 50 to 100 m | 19.6% |

Median 23 m, ninetieth percentile 65 m.

**The layer count is driven by the flushing question rather than by the seiche.** A seiche is barotropic and two or three layers would reproduce it. Residence time is not: the Mediterranean microtidal harbour literature reports bottom renewal times of 32 and 61 days at Barcelona and Tarragona against much shorter times at the surface, so vertical structure is where the answer lives.

Uniform sigma layer thickness:

| Layers | 13 m | 16 m | 30 m | 100 m | 150 m |
|---|---|---|---|---|---|
| 8 | 1.62 | 2.00 | 3.75 | 12.50 | 18.75 |
| 10 | 1.30 | 1.60 | 3.00 | 10.00 | 15.00 |
| **12** | **1.08** | **1.33** | **2.50** | **8.33** | **12.50** |
| 15 | 0.87 | 1.07 | 2.00 | 6.67 | 10.00 |
| 20 | 0.65 | 0.80 | 1.50 | 5.00 | 7.50 |

**Recommendation: sigma, 12 to 15 layers, stretched toward the bed and the surface.**

Sigma rather than z, because domain B remains entirely on the plateau where the gradient is of order one part in a thousand, 100 to 190 m over 90 km, and the pressure-gradient error that afflicts sigma over steep topography does not arise. This is a second reason to stop the domain short of the escarpment. Should domain C or an eastward extension be adopted, the question reopens and a z-sigma hybrid becomes necessary.

Twelve to fifteen layers rather than more, because the harbours are unlikely to be strongly stratified. The seasonal thermocline in the central Mediterranean lies below 20 m through the summer, while the mean depth of the two basins is 13 and 16 m, so the harbour water column sits largely above it and responds to surface heating rather than to an internal density interface. Fifteen layers give a near-bed thickness of 0.87 m at Marsamxett and 1.07 m at the Grand Harbour before stretching, which is the resolution the bottom boundary layer requires for a residence-time calculation.

**This assumption is testable and should be tested first.** The BLUE buoy measures temperature and salinity through the water column and its archive extends to July 2025. Extracting the seasonal stratification there, as part of the G1 climatology, would confirm or refute the argument before the mesh is built.

---

## 5. Summary for the meeting

| Question | Proposal | Basis |
|---|---|---|
| Domain | B, approximately 86 × 66 km over the plateau, east to 15.0°E | Only a domain containing the plateau holds a resonator in the observed band. It costs a tenth more cells than the harbours alone |
| Resolution | 15 m in the inlets and entrances, 30 m in the basins, grading to 1.5 km offshore | Measured channel widths. Half of Marsamxett is narrower than 135 m and a third narrower than 50 m |
| Mesh size | Approximately 28,500 cells | Graded scheme with a transition allowance |
| Time step | 6 to 12 s | Courant 5 to 10 at the finest cells |
| Layers | 12 to 15 sigma, stretched | Flushing rather than seiche. Sigma is safe because the domain stays on the plateau |
| Coupling | Uncoupled for the seiche work, coupled for the events | Cost |

**Three matters to put to the host group.**

Whether the interpretation in Section 2 is right, namely that the harbours respond to a shelf-scale oscillation rather than resonating themselves. Drago's own records would settle it, since a spectrum of harbour sea level would show whether energy appears near 17 minutes as well as in the milgħuba band.

Which of the three routes to the trigger, listed at the end of Section 2, the group considers realistic given what the PORTO network can supply.

Whether observed stratification at BLUE supports the layer count, and whether any earlier work exists on stratification inside the two basins.
