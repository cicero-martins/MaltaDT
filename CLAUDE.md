# MaltaDT — context for Claude

Coupled wave-hydrodynamic Delft3D FM and SWAN model of the Valletta harbour system (Grand Harbour and Marsamxett), Malta. Conducted during a research period at the Oceanography Malta Research Group, University of Malta, September 2026 to March 2027, within the Interreg VI-A Italia-Malta WETWISE project (deliverable D.3.3.3, WP3, RCO116).

Distinct from, but methodologically dependent on, `../StagnoneDT`. The scientific contribution of this project is the transfer of the StagnoneDT framework across archetype, from a shallow vegetated micro-tidal lagoon to a deep engineered seiche-dominated harbour.

## Register

All generated text, in documents, code comments and commit messages, is written in an academic register. Impersonal construction, measured claims, descriptive rather than rhetorical section titles. Em dashes are not used, explanatory colons are avoided, and semicolons are used sparingly.

## Current state

- **Site fixed** 2026-09-22 with Prof. Adam Gauci: Valletta harbours.
- **Bathymetry obtained** 2026-09-22: CDI `4036_MEPA`, 10 m LiDAR and sonar grids covering the Maltese Islands. See [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md).
- **No field campaign planned.** The study proceeds on existing observations. Deferred rather than cancelled.
- **No model built yet.** Mesh construction is scheduled for B3, 27 October to 21 November.

Planning documents: [docs/malta_valletta_model_plan.md](docs/malta_valletta_model_plan.md) is the operative plan; [docs/malta_period_plan_2026-2027.md](docs/malta_period_plan_2026-2027.md) holds the block calendar and the parallel UNIPA commitments.

## Critical configuration facts

**Bathymetry is EPSG:23033 (ED50 / UTM 33N) and the file does not say so.** GDAL reports "unnamed, Unknown datum based upon the International 1924 ellipsoid". Treating it as EPSG:32633 displaces the data by 197 m, approximately 20 cells, without raising an error. The CRS must be assigned explicitly on every read.

**The open boundary must be weakly reflective (Riemann), not a prescribed water level.** A prescribed level reflects outgoing long waves back into the domain and contaminates the seiche signal while producing plausible output. This is the principal configuration departure from StagnoneDT. A synthetic long-wave pulse test is required before any production run.

**History output at approximately 1 minute.** The milgħuba seiche band is 0.2 to 2 cph. Coarser output aliases the target signal. Map output may remain coarse.

**Mesh resolution follows the creeks.** Marsa, French, Dockyard, Kalkara and Rinella in the Grand Harbour; Msida, Pietà, Lazzaretto and Sliema in Marsamxett. The creeks are the resonating elements and an under-resolved creek loses its mode silently.

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
- DIMR and SWAN coupling, including the full gotcha catalogue in `StagnoneDT/docs/fm_2026_gotchas.md`
- Validation methodology: raw and anomaly metrics reported together, post-spinup window, cell-based extraction for offshore points
- OpenDrift regridding and Lagrangian scoring
- Containerised EDITO deployment

The following do not apply at this site and their inapplicability is itself a result: the `[veg]` canopy drag module, the Random-Forest bottom-class classifier, the hypersaline initial condition, ERA5 evaporation forcing, and the D-Morph sediment configuration.

**A porting log is maintained**, classifying every pipeline stage as transferred unchanged, re-parameterised, or not applicable, with the effort expended. This log is the primary evidence base for the methodological contribution and is not administrative overhead.

## Conventions

Directory layout follows StagnoneDT. Scripts are named `<verb>_<scope>_<version?>.py`, with throwaway work under `scripts/_*` and excluded from version control. Notebooks use the numeric blocks `00-09` input forcing, `10-19` model build, `20-29` validation, `30-39` analysis. Durable analyses are written to `docs/<topic>.md`. Commits are granular and use Conventional Commits prefixes.

Python environment is `dfm_tools_env` at `C:/Users/Unipa/.conda/envs/dfm_tools_env/python.exe`, shared with StagnoneDT.

## Key literature

Drago (2009), Phys. Chem. Earth 34, 948–970, establishes the milgħuba phenomenon. Drago, Sorgente and Ribotti (2003), Ann. Geophys. 21, 323–344, provide the regional shelf circulation. Capodici et al. (2019), Remote Sens. Environ. 225, 65–76, validate the HF radar surface currents and constitute an existing UNIPA–UMalta collaboration. Orasi et al. (2018), Measurement 128, 446–454, cover the wave observations. Romeo et al. (2015), Environ. Monit. Assess. 187(12), document the environmental state of the Grand Harbour. Airy (1878) described seiches in this harbour and serves as the historical anchor. Full annotation in the plan document.
