# MaltaDT: working context

Coupled wave-hydrodynamic Delft3D FM and SWAN model of the Valletta harbour system (Grand Harbour and Marsamxett), Malta. Conducted during a research period at the Oceanography Malta Research Group, University of Malta, September 2026 to March 2027, within the Interreg VI-A Italia-Malta WETWISE project (deliverable D.3.3.3, WP3, RCO116).

Distinct from, but methodologically dependent on, `../StagnoneDT`. The scientific contribution of this project is the transfer of the StagnoneDT framework across archetype, from a shallow vegetated micro-tidal lagoon to a deep engineered seiche-dominated harbour.

**The milghuba is a meteotsunami, not a seiche in general**, alongside the rissaga of the Balearics and the marrobbio of Sicily. The governing question is the partition of amplification between Proudman resonance over the Malta Plateau, shoaling on the approach, and resonance of the basins. Prior work already treats Maltese coastal seiches in 2D with prescribed offshore forcing, so the generation side remains unaddressed. The hazard is documented: the milghuba floods Msida, at the head of Msida Creek inside Marsamxett, together with Marsaskala, Xemxija, Marsaxlokk and Sliema. Climate change is a bounded discussion element, since the parametric sweep yields a transfer function of the geometry and climate acts on the input distribution, so the two separate and no climate scenario need be run through the model. See [docs/research_question_and_literature.md](docs/research_question_and_literature.md).

## Register

All generated text, in documents, code comments and commit messages, is written in an academic register. Impersonal construction, measured claims, and descriptive rather than rhetorical section titles. Em dashes are not used, explanatory colons are avoided, and semicolons are used sparingly.

`scripts/check_register.py` flags departures. Run it over the repository before a document is circulated. Its patterns come from departures actually found here rather than from a stylebook, and it reports rather than enforces, since some hits are legitimate.

## Current state

- **Site fixed** 2026-09-22 with Prof. Adam Gauci. The Valletta harbours.
- **Bathymetry obtained** 2026-09-22. CDI `4036_MEPA`, 10 m LiDAR and sonar grids covering the Maltese Islands. Merged product in `data/processed/`. See [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md).
- **Coastline obtained** 2026-09-23. 26 polygons, 315.4 km2, WGS84 / UTM 33N. See [docs/coastline_dataset.md](docs/coastline_dataset.md).
- **No field campaign planned.** The study proceeds on existing observations. Deferred rather than cancelled.
- **No model built yet.** Mesh construction is scheduled for B3, 27 October to 21 November.

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

**The open boundary must be weakly reflective (Riemann), not a prescribed water level.** A prescribed level reflects outgoing long waves back into the domain and contaminates the seiche signal while producing plausible output. This is the principal configuration departure from StagnoneDT. A synthetic long-wave pulse test is required before any production run.

**History output at approximately 1 minute.** The milgħuba seiche band is 0.2 to 2 cph. Coarser output aliases the target signal. Map output may remain coarse.

**Domain B is proposed, roughly 86 x 66 km over the Malta Plateau, east to 15.0 degrees.** The harbours resonate at 17 and 18 minutes and their inlets at 4 to 6, all above the milghuba band, while the plateau resonates at 78 to 156 minutes, within it. A harbour-only domain holds no resonator in the band. Domain B costs 28,500 cells against 25,900 for the harbours alone. Stopping short of the escarpment is also what keeps sigma layers defensible. See [docs/domain_and_discretisation.md](docs/domain_and_discretisation.md).

**Mesh resolution follows the inlets.** French Creek, Dockyard Creek, Kalkara Creek and Rinella Creek in the Grand Harbour, with the head at Marsa. Sliema Creek, Lazzaretto Creek, Msida Creek and Pietà Creek in Marsamxett. These are the resonating elements and an under-resolved inlet loses its mode silently. The name creek is nautical, denoting a tidal inlet, not a watercourse.

## Observational basis

| Asset | Sampling | Role |
|---|---|---|
| BLUE buoy, 3.7 km off the Grand Harbour, since 4 Jul 2025 | 10 min | Offshore validation. Waves, wind, currents, T, S and biogeochemistry |
| PORTO network, 7 coastal meteo stations | 1 min | Atmospheric forcing, including the pressure signature of seiche events |
| PORTO sea level stations (4) | to be confirmed | Coastal sea level. Sampling interval determines whether the seiche band is resolved |
| HF radar, 4 stations, Malta Channel | 1 h, 3 km | Surface current validation |
| Portomaso tide gauge, since 2001 | real time | Long record for seiche climatology |

Portal: `ocean.mt/bluedata`. Model output is to be integrated into this existing portal rather than served through a second one.

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
