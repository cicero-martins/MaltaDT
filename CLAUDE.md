# MaltaDT: working context

Coupled wave-hydrodynamic Delft3D FM and SWAN model of the Valletta harbour system (Grand Harbour and Marsamxett), Malta. Conducted during a research period at the Oceanography Malta Research Group, University of Malta, September 2026 to March 2027, within the Interreg VI-A Italia-Malta WETWISE project (deliverable D.3.3.3, WP3, RCO116).

Distinct from, but methodologically dependent on, `../StagnoneDT`. The scientific contribution of this project is the transfer of the StagnoneDT framework across archetype, from a shallow vegetated micro-tidal lagoon to a deep engineered seiche-dominated harbour.

## Where the inherited knowledge lives

Claude Code keys its memory to the working directory, so the StagnoneDT store does not load here. **It holds roughly half of what this project depends on** and is to be read on demand at

```
C:\Users\Unipa\.claude\projects\c--Users-Unipa-Documents-StagnoneDT\memory\MEMORY.md
```

That index is to be consulted **before proposing anything** touching the solver, the forcing chain, mesh construction, coordinate systems, the Lagrangian pipeline or the EDITO infrastructure. The groups on vegetation, sediment and the `v04*` setups are lagoon-specific and do not transfer. The decision not to copy the files is deliberate, since two copies diverge as soon as either project learns something new about the solver. Local memory carries a pointer entry with the mapping from subject to group.

Cross-cutting rules, namely the register, the prose style, the tool traps and the commit cadence, live in `~/.claude/CLAUDE.md` and load in every session.

**The milghuba is a meteotsunami, not a seiche in general**, alongside the rissaga of the Balearics and the marrobbio of Sicily. **The principal question of the study is the renewal and circulation of the harbours, and the milgħuba is a component of it.** For that component the question is the partition of amplification between Proudman resonance over the Malta Plateau, shoaling on the approach, and resonance of the basins. Prior work already treats Maltese coastal seiches in 2D with prescribed offshore forcing, so the generation side remains unaddressed. The hazard is documented: the milghuba floods Msida, at the head of Msida Creek inside Marsamxett, together with Marsaskala, Xemxija, Marsaxlokk and Sliema. Climate change is a bounded discussion element, since the parametric sweep yields a transfer function of the geometry and climate acts on the input distribution, so the two separate and no climate scenario need be run through the model. See [docs/research_question_and_literature.md](docs/research_question_and_literature.md).

## Register

All generated text, in documents, code comments and commit messages, is written in an academic register. Impersonal construction, measured claims, and descriptive rather than rhetorical section titles. Em dashes are not used, explanatory colons are avoided, and semicolons are used sparingly.

`scripts/check_register.py` flags departures. Run it over the repository before a document is circulated. Its patterns come from departures actually found here rather than from a stylebook, and it reports rather than enforces, since some hits are legitimate.

## Current state

- **Site fixed** 2026-09-22 with Prof. Adam Gauci. The Valletta harbours.
- **Bathymetry obtained** 2026-09-22. CDI `4036_MEPA`, 10 m LiDAR and sonar grids covering the Maltese Islands. Merged product in `data/processed/`. See [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md).
- **Coastline obtained** 2026-09-23. 26 polygons, 315.4 km2, WGS84 / UTM 33N. See [docs/coastline_dataset.md](docs/coastline_dataset.md).
- **No field campaign planned.** The study proceeds on existing observations. Deferred rather than cancelled.
- **Working mesh is v02**, built 1 October ahead of B3 by `scripts/build_mesh_v02.py`. 26 766 faces, 15 m in the narrow harbour channels, 120 m within 1 km and 480 m within 5 km of the coast, 1920 m offshore, accepted by FM 2026.01. It replaced v01 (2 km and 15 km, 41 353 faces) after measured runs showed the time step, 3.7 s under a resonant wave, set by the 15 m channels alone, the cost falling 37 per cent and the harbour response unchanged. See [docs/mesh_v02.md](docs/mesh_v02.md) and [docs/mesh_v01.md](docs/mesh_v01.md). **Build in UTM 33N and transform the nodes to WGS84**: refined directly in degrees, the quadtree transitions reach orthogonality 1 and FM rejects the network as not orthogonal. See [docs/mesh_v01.md](docs/mesh_v01.md).

Planning documents. [docs/malta_valletta_model_plan.md](docs/malta_valletta_model_plan.md) is the operative plan. [docs/malta_period_plan_2026-2027.md](docs/malta_period_plan_2026-2027.md) holds the block calendar and the parallel commitments at UNIPA.

## Critical configuration facts

**The bathymetry and the coastline are in different datums, and both declarations must be handled deliberately.**

- Bathymetry `4036_MEPA` is **EPSG:23033** (ED50 / UTM 33N) and the file does not say so. GDAL reports "unnamed, Unknown datum based upon the International 1924 ellipsoid". The CRS must be assigned explicitly on every read.
- Coastline `MaltaCoastline.shp` is **EPSG:32633** (WGS84 / UTM 33N), and that declaration is correct, verified at 99.26% land and water agreement against 94.54% under the alternative.

The two differ by approximately 197 m at Malta, some 20 cells at 10 m. Overlaying either on the other without a datum transformation produces no error and a displaced result.

**The aligned working pair is in geographic WGS84 (EPSG:4326)**, following the FM convention that the mesh and the roughness assignment file share a coordinate system. Use `data/processed/mepa_4036_merged_10m_wgs84.tif` with `data/processed/malta_coastline_wgs84.gpkg`, not the raw files. Registration is 99.51% land and water agreement with a median disagreement of one cell, and no water lies inside the land polygons beyond 500 m from the coast, which is the test a systematic offset would fail.

**The datum transformation is chosen explicitly, not left to PROJ.** The reprojection uses **ED50 to WGS 84 (12)**, Helmert -107 -88 -149, the operation whose area of use names Malta, declared accuracy 44 m. PROJ would otherwise default to ED50 to WGS 84 (1), which declares the better 10 m but over an area of use listing northern and western European states that excludes Malta. An accuracy declaration ranks operations within their own area of use, not across areas. Under (12) the registration improves from 99.33 to 99.51 per cent and disagreeing cells fall by 27 per cent. The two differ by 19.4 m at Valletta.

Passing a pipeline to GDAL through `COORDINATE_OPERATION` requires the **authority axis order**, so for EPSG:4326 it must end with `+step +proj=axisswap +order=2,1`. The pipeline pyproj emits under `always_xy` omits that step and yields a transposed raster with no error raised. The constant in `build_merged_bathymetry.py` carries the correct form.

Two caveats remain. The declared 44 m is a floor on co-registration even though the empirical result is better. And **Filfla is present in the bathymetry and absent from the coastline**, which does not affect the Valletta domain but bears on island-wide use.

**Vertical datum. The files declare ETRS89 ellipsoidal and the data are orthometric.** Both `prj.adf` files carry `Zunits METERS /* ETRS_1989 - VCS# = 115701` and the `peXml` WKT carries the matching `VERTCS`. That declaration is a mislabel. Control points at Valletta and Floriana, and a median of +0.00 m sampled along the coastline, establish that the values are heights above a surface approximating mean sea level. **No geoid correction is to be applied.** What remains open is the relation between this zero and the tide gauge zeros used for validation.

**The open boundary must be weakly reflective (Riemann), not a prescribed water level.** A prescribed level reflects outgoing long waves back into the domain and contaminates the seiche signal while producing plausible output. This is the principal configuration departure from StagnoneDT. The synthetic pulse test was run 30 September ([docs/open_boundary_pulse_test.md](docs/open_boundary_pulse_test.md)). At 150 m and 1500 m cells the Riemann boundary reflects 0.3 to 1.3 per cent at normal incidence, 5 to 9 per cent up to 30 degrees and 24 to 29 per cent at corners, while a prescribed level reflects −0.94 to −1.00. Residual current, non-zero incoming signal, variable depth and Coriolis remain untested. **A pressure disturbance crossing the Riemann boundary sends back a free wave of a quarter to a third of the static response**, whatever the amplification, and `pavBnd` does not act on it, so in the sweep the disturbance is raised and lowered inside the domain ([docs/moving_pressure_channel_test.md](docs/moving_pressure_channel_test.md), 9 October). **Domain B does not contain the generation of the long wave.** A disturbance of the milgħuba band is 55 to 280 km long, and a basin of the size of domain B crossed by a resonant pressure band retains 15 to 47 per cent of the response of an unbounded sea, since the wave grown outside does not enter. The sweep requires an outer domain, and domain B remains that of the three-dimensional runs. The same test reproduces the closed form of Proudman resonance within 3.5 per cent, with the pressure read from netCDF snapshots and **`Wind_eachstep = 1`**, since the default updates the pressure at the user step alone. **FM reads only the first polyline of a `.pli`**, ignoring the rest with a warning alone, so a boundary spanning several sides is one polyline turning the corners. Precedent in the same basin: Laksono et al. (2026), Delft3D over the Sicilian Channel, applies Riemann for exactly this reason.

**The Grand Harbour entrance is not a single 400 m opening.** The supplied coastline carries the 1910 St Elmo breakwater as a detached polygon, 378 m long, 58 m wide, 42 m from shore, the gap being the bridge span and correctly open water. Recomputed 30 September by a 1D eigenvalue calculation on the measured profile ([docs/basin_modes.md](docs/basin_modes.md)). **The breakwater changes the period by 0.1 minute, because the harbour is not a Helmholtz resonator.** The entrance section is within 6 per cent of the median section, so the inertia is distributed along the basin. Fundamental periods are 14.5 to 18.4 minutes for the Grand Harbour and 10.4 to 12.8 for Marsamxett. The T ∝ a^−1/2 scaling in `estimate_entrance_restriction.py` overstates restriction sensitivity by a factor of 3 to 10 and is not to be reused. Whether the 120 m Ricasoli arm is present is unresolved, since it joins the land and would sit inside the mainland polygon, and a narrower real opening would create the neck the supplied geometry lacks.

**History output at approximately 1 minute.** The milgħuba seiche band is 0.2 to 2 cph. Coarser output aliases the target signal. Map output may remain coarse.

**Domain B is proposed, roughly 86 x 66 km over the Malta Plateau, east to 15.0 degrees.** The harbours resonate at 14.5 to 18.4 and 10.4 to 12.8 minutes and their inlets at 4 to 6, all above the milghuba band, while the plateau resonates at 78 to 156 minutes, within it. A harbour-only domain holds no resonator in the band. Domain B costs 28,500 cells against 25,900 for the harbours alone. Stopping short of the escarpment is also what keeps sigma layers defensible. See [docs/domain_and_discretisation.md](docs/domain_and_discretisation.md).

**Mesh resolution follows the inlets.** French Creek, Dockyard Creek, Kalkara Creek and Rinella Creek in the Grand Harbour, with the head at Marsa. Sliema Creek, Lazzaretto Creek, Msida Creek and Pietà Creek in Marsamxett. These are the resonating elements and an under-resolved inlet loses its mode silently. The name creek is nautical, denoting a tidal inlet, not a watercourse.

## Observational basis

| Asset | Sampling | Role |
|---|---|---|
| BLUE buoy, 3.7 km off the Grand Harbour, since 4 Jul 2025 | 10 min | Offshore validation. Waves, wind, currents, T, S and biogeochemistry. The **only** direct wave observation |
| PORTO network, 7 coastal meteo stations | 1 min | Atmospheric forcing, including the pressure signature of seiche events |
| PORTO sea level stations (4) | to be confirmed | Coastal sea level. Sampling interval determines whether the seiche band is resolved |
| HF radar, 4 stations, Malta Channel | 1 h, 3 km | Surface current validation. Its wave product is derived, not measured, so it is a cross-check and not a reference |
| Portomaso tide gauge, since 2001 | real time | Long record for seiche climatology |

**The PORTO stations are Mġarr, Ċirkewwa, Qammieħ, Elmo, Kordin, Delimara and Marsaxlokk.** Elmo and Kordin lie on the Grand Harbour, at the entrance and on the southern shore, and are therefore the closest atmospheric record to the basin under study. Station map in Drago (2018), `reference/`.

**A sea level station does lie inside the Grand Harbour: Senglea.** An IDSL radar gauge deployed June 2021, transmitting at **5 s** to the University of Malta and to the JRC TAD server, with sea-state images every 15 min. Senglea sits on the peninsula between Dockyard Creek and French Creek, well inside the basin. The 2018 design report predates it, which is why that document shows no station in Valletta, and an earlier statement here that none existed was drawn from it and is withdrawn.

| Sea level station | From | Sampling | Position |
|---|---|---|---|
| **Senglea**, IDSL | Jun 2021 | 5 s | **Inside the Grand Harbour** |
| Delimara, IDSL | Mar 2021 | 5 s | Southeast coast |
| Marsaxlokk breakwater, Radac WaveGuide | Mar 2021 | 10 Hz | Marsaxlokk |
| Portomaso, MedGLOSS | Feb 2001 | real time | St Julian's, outside both basins |
| Mellieħa Bay | 1993 to 2001 | historical | The series behind Drago (2009) |

Four current stations, matching the seven meteo and four sea level stations the group reports. PORTO acquires at **one-minute** intervals. Senglea and Portomaso give an inside and outside pair for the Grand Harbour, and 5 s over-resolves the 0.2 to 2 cph band by a wide margin. **Senglea is JRC TAD device 555** (IDSL-42), found through `TAD_server/api/Groups/GetGeoJSON?group=IDSL`. **It has been offline since 13 December 2024**, covers 43 per cent of its span, and carries upward radar echoes and reference offsets of 1.3 to 2.1 m. Only two windows are usable, 24 June to 31 December 2021 and 1 December 2022 to 31 March 2023, a choice to be confirmed with Prof. Gauci. The spectrum shows permanent modes at 23.0, 16.8, 10.0 and 6.9 minutes, the 23 minute mode dominant and amplified some 2.8 times against Marsaxlokk (device 556), outside the predicted 14.5 to 18.4 minutes. See [docs/senglea_spectrum.md](docs/senglea_spectrum.md).

**Dated events: 18 Jun 2019, 30 Jun 2022, 1 Jul 2023, 13 Jun 2024** (milgħuba), and 25 Oct 2018 (seismic). None since 2021 is resolved in the public Senglea record, and Portomaso returns nothing from the IOC. The archive of the group, sea level and one-minute PORTO pressure for those dates, is the first request to Prof. Gauci. The PORTO network now lists eight meteorological stations, including Msida.

The interior gap that remains is **currents and stratification**, not sea level. Ċirkewwa does appear on the TAD server as IDSL-34 (device 533), active to November 2021, though with too little coverage for spectral use.

Portal: `ocean.mt/bluedata`. Model output is to be integrated into this existing portal rather than served through a second one.

## Modelling systems of the group

The systems below are described in Drago (2018), the design report of Action A.7 of LIFE 16 IPE MT 008, in `reference/`. Their status is as stated by Prof. Gauci on 9 October 2026.

- **SWAN**, downscaled to the embayments at **1/500°**, about 200 m, from **WAM** at 1/8°. **Active**, and used together with the HF radar data.
- **ROSARIO-SHYFEM**, unstructured, 3D, from a few km to **50 m** at the coast, over the Maltese Islands and the Malta Channel to southern Sicily, with a Lagrangian particle-tracking component. **Not running.**
- **ROSARIO**, Princeton Ocean Model, 1/64° and 1/96°, nested into CMEMS.
- **The design report was not continued.** It asks for a relocatable model setup for ad hoc local domains and names harbour flushing at the five principal harbours among its process-model targets, and neither was carried out.

No hydrodynamic model at harbour scale is therefore in operation within the group, and no work on the generation of the long wave over the shelf exists. The present configuration is a process study conducted within the group. An extension to other bays is of possible interest, conditional on the outcome at Valletta.

## Priorities stated by the group

From the meeting with Prof. Gauci of 9 October 2026, held on the concept presentation of 8 October.

- **Circulation inside the harbours is the principal interest.** The milgħuba is relevant at Msida and causes little damage in the harbours as a whole.
- **Residence time**, for each harbour and by inlet, in particular around Manoel Island in Marsamxett, together with flushing time and temperature.
- **Currents in support of oil spill assessment** in the industrial area of the Grand Harbour.
- **Validation against the BLUE buoy.** Drifter releases inside the harbours are a possibility, limited by vessel traffic to short periods or to hours of low traffic.
- **The principal research question is the renewal and circulation of the harbours**, with the geometry counterfactual and the milgħuba as accompanying components. See [docs/research_question_and_literature.md](docs/research_question_and_literature.md), Section 4.
- **Geometry experiments.** The breakwaters as modified in the planned projects, a closure of the gap under the St Elmo bridge, and the effect of new piers such as the one built at Msida. The sensitivity exercise on the harbour mouth was considered appropriate.
- **Data to be supplied on 12 October 2026.** The archive of sea level and one-minute pressure on the event dates, the history of the Senglea installation with Portomaso, and data for validation.

The two-dimensional sweep of the long wave is retained as the initial test, being inexpensive and informative, and precedes the three-dimensional runs.

## Inherited from StagnoneDT

The following transfer without modification and their reuse constitutes the evidence for the transferability claim. Consult the StagnoneDT repository rather than reimplementing.

- `dfm_tools` mesh generation sequence (`mesh_generation_workflow.md`)
- CMEMS MED-MFC boundary chain and the anchored-offset datum methodology
- ERA5 and station wind blending
- DIMR and SWAN coupling, including the configuration catalogue in `StagnoneDT/docs/fm_2026_gotchas.md`
- Validation methodology, comprising raw and anomaly metrics reported together, a post-spinup window, and cell-based extraction for offshore points
- OpenDrift regridding and Lagrangian scoring
- Containerised EDITO deployment

The following do not apply at this site, and their inapplicability constitutes a result in itself. They are the `[veg]` canopy drag module, the Random-Forest bottom-class classifier, the hypersaline initial condition, ERA5 evaporation forcing, and the D-Morph sediment configuration.

**A porting log is maintained**, classifying every pipeline stage as transferred unchanged, re-parameterised, or not applicable, with the effort expended. This log is the primary evidence base for the methodological contribution and is not administrative overhead.

## Conventions

Directory layout follows StagnoneDT. Scripts are named `<verb>_<scope>_<version?>.py`, with throwaway work under `scripts/_*` and excluded from version control. Notebooks use the numeric blocks `00-09` input forcing, `10-19` model build, `20-29` validation, `30-39` analysis. Durable analyses are written to `docs/<topic>.md`. Commits are granular and use Conventional Commits prefixes.

Python environment is `dfm_tools_env` at `C:/Users/Unipa/.conda/envs/dfm_tools_env/python.exe`, shared with StagnoneDT.

## Key literature

Drago (2009), Phys. Chem. Earth 34, 948–970, establishes the milgħuba phenomenon. Drago, Sorgente and Ribotti (2003), Ann. Geophys. 21, 323–344, provide the regional shelf circulation. Capodici et al. (2019), Remote Sens. Environ. 225, 65–76, validate the HF radar surface currents and constitute an existing UNIPA–UMalta collaboration. Orasi et al. (2018), Measurement 128, 446–454, cover the wave observations. Romeo et al. (2015), Environ. Monit. Assess. 187(12), document the environmental state of the Grand Harbour. Airy (1878) described seiches in this harbour and serves as the historical anchor. Full annotation in the plan document.
