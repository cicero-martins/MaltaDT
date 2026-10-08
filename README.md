# MaltaDT: model of the Valletta harbour system

Coupled wave-hydrodynamic model of the Grand Harbour and Marsamxett Harbour, Malta, constructed with Delft3D FM and SWAN coupled through DIMR.

Undertaken within the Oceanography Malta Research Group, Department of Geosciences, University of Malta, during a research period from the Università degli Studi di Palermo, September 2026 to March 2027, and contributing to deliverable D.3.3.3 of the Interreg VI-A Italia-Malta WETWISE project.

## Scientific framing

The project tests whether a coupled-physics modelling framework developed for a shallow vegetated micro-tidal lagoon transfers to a hydrodynamically dissimilar setting. The framework originates in the Stagnone di Marsala digital twin (`../StagnoneDT`), where tidal forcing sets the boundary signal and wind drives the circulation over sub-metre depths across a seagrass canopy. The Valletta harbours invert that hierarchy. They are drowned river valleys of 12 to 20 m depth, heavily engineered, without significant canopy, and subject to the milgħuba, a meteotsunami known as rissaga in the Balearics and as marrobbio in Sicily, an atmospherically generated long wave in the 0.2 to 2 cph band.

The transfer is therefore across archetype rather than within it, which constitutes a stronger test of framework reusability than a transfer to a second lagoon.

The governing question is how the amplification between the open sea and the heads of the harbours is partitioned between Proudman resonance over the Malta Plateau, shoaling on the approach and resonance of the basins, and which atmospheric disturbance speeds and directions maximise that chain. Three accompanying questions concern the exposure by inlet and quay, the renewal of harbour water, and the sensitivity of both to the geometry of the harbour mouth. See [docs/research_question_and_literature.md](docs/research_question_and_literature.md).

The results reported below are preliminary. The period estimates are one-dimensional, the observational test rests on a single gauge, and no production run has been made.

## Status

| Component | State |
|---|---|
| Site | The Valletta harbours, Grand Harbour and Marsamxett |
| Bathymetry | CDI `4036_MEPA`, 10 m LiDAR and sonar, Maltese Islands, merged. See [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md) |
| Coastline | 26 polygons, 315.4 km2, WGS84 / UTM 33N, verified against the bathymetry. See [docs/coastline_dataset.md](docs/coastline_dataset.md) |
| Aligned basemap | Bathymetry and coastline co-registered in EPSG:4326 in `data/processed/`. 99.51% land and water agreement, median disagreement one cell |
| Observational basis | BLUE buoy, PORTO network, HF radar, and the Senglea IDSL gauge inside the Grand Harbour at 5 s. The public copy of the Senglea record covers 43 per cent of June 2021 to December 2024 and resolves none of the milgħuba events reported in that span |
| Research question | Attribution of amplification along the generation chain, with three accompanying questions. See [docs/research_question_and_literature.md](docs/research_question_and_literature.md) |
| Domain and discretisation | Domain B over the Malta Plateau, roughly 86 by 66 km, 15 m in the inlets, 12 to 15 sigma layers foreseen. See [docs/domain_and_discretisation.md](docs/domain_and_discretisation.md) |
| Basin modes | First-order estimate from the measured profile. Grand Harbour 14.5 to 18.4 min, Marsamxett 10.4 to 12.8 min, both above the milgħuba band. See [docs/basin_modes.md](docs/basin_modes.md) |
| Senglea spectrum | Two windows provisionally admitted. Peaks at 23.0, 16.8, 10.0 and 6.9 min, all above the band, the dominant one longer than estimated. See [docs/senglea_spectrum.md](docs/senglea_spectrum.md) |
| Open boundary | Idealised pulse test. A Riemann boundary reflects 0.3 to 1.3 per cent at normal incidence and 5 to 9 per cent up to 30 degrees, a prescribed level nearly all of it. A residual current, a CMEMS signal and a pressure disturbance crossing the boundary remain to be tested. See [docs/open_boundary_pulse_test.md](docs/open_boundary_pulse_test.md) |
| Mesh | Version 02. 26 766 faces, 15 m in the narrow harbour channels to 1920 m offshore, built in UTM 33N and transformed to WGS84, accepted by D-Flow FM 2026.01. See [docs/mesh_v02.md](docs/mesh_v02.md) and [docs/mesh_v01.md](docs/mesh_v01.md) |
| Experimental design | A sweep of 96 idealised pressure disturbances, two-dimensional and barotropic, for the long wave, and a three-dimensional hindcast for validation. Proposed, not yet run |
| Model runs | Acceptance runs of the mesh only, at rest and under a forced long wave. A pilot scenario and the sweep are planned for October 2026 and the three-dimensional runs for November |
| Field campaign | Not planned. The study proceeds on existing observations |

## Layout

```
data/raw/          source datasets as received, not under version control
data/processed/    derived products
data/external/     CMEMS, ERA5 and other downloads
docs/              planning documents and durable analyses
scripts/           reusable tooling
notebooks/         pipelines, numbered by role
model/             model configurations and runs
figures/           generated figures
reference/         third-party material, listed in reference/README.md
```

## Documents

- [docs/research_question_and_literature.md](docs/research_question_and_literature.md), the research question, the prior work it must clear, and the reading list
- [docs/malta_valletta_model_plan.md](docs/malta_valletta_model_plan.md), the operative plan, covering the model configuration, the block allocation and the risks
- [docs/malta_period_plan_2026-2027.md](docs/malta_period_plan_2026-2027.md), the block calendar and the parallel commitments at UNIPA
- [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md), assessment of the bathymetric dataset
- [docs/coastline_dataset.md](docs/coastline_dataset.md), assessment of the coastline, including the inference establishing the vertical datum
- [docs/domain_and_discretisation.md](docs/domain_and_discretisation.md), sizing of the domain, the horizontal resolution and the vertical layering
- [docs/basin_modes.md](docs/basin_modes.md), fundamental long-wave modes of the two harbours from the measured geometry
- [docs/senglea_spectrum.md](docs/senglea_spectrum.md), quality control and spectrum of the Senglea gauge, and the reported events against the public records
- [docs/open_boundary_pulse_test.md](docs/open_boundary_pulse_test.md), reflection of the Riemann and prescribed-level boundaries under a synthetic pulse
- [docs/mesh_v02.md](docs/mesh_v02.md) and [docs/mesh_v01.md](docs/mesh_v01.md), the working mesh, its construction and quality, and the measured cost that selected it
- [docs/valletta_model_concept_2026-10-08.pptx](docs/valletta_model_concept_2026-10-08.pptx), sixteen slides on the model concept, the estimated and observed basin modes, the mesh, the open boundary, the experimental design and the open questions, prepared for discussion within the Oceanography Malta Research Group. Regenerated by `scripts/build_concept_deck.js`
- [docs/valletta_model_concept_2026-10-08_short.pptx](docs/valletta_model_concept_2026-10-08_short.pptx), a nine-slide version of the same deck. Regenerated by `scripts/build_concept_deck_short.js`
- [docs/deck_cover.pptx](docs/deck_cover.pptx), the cover of both decks, edited in PowerPoint. `scripts/copy_deck_cover.ps1` places it over the first slide of a generated deck and repeats its photograph behind the last
- [CLAUDE.md](CLAUDE.md), working context and critical configuration facts

## Tooling

`scripts/build_merged_bathymetry.py` combines the LiDAR and sonar components of the bathymetric dataset and writes the merged field in its native and geographic coordinate systems. `scripts/prepare_coastline.py` brings the coastline onto the working coordinate system and reports its registration against that field.

`scripts/domain_design_estimate.py` sizes the domain, the resolution and the layering from the bathymetry, and `scripts/check_register.py` flags departures from the register the project writes in.

`scripts/estimate_basin_modes.py` solves the one-dimensional long-wave eigenproblem on the measured profile of each harbour and reports the sensitivity of the fundamental mode to the breakwater, to a restriction of the entrance and to sea level rise. `scripts/estimate_entrance_restriction.py` holds the Helmholtz scaling of that sensitivity, which the measured profile shows to overstate it, and is kept for comparison only.

`scripts/build_riemann_pulse_test.py` and `scripts/analyse_riemann_pulse_test.py` build and analyse the synthetic pulse test of the open boundary in D-Flow FM.

`scripts/download_jrc_tad_wl.py` retrieves radar gauge records from the JRC TAD server by device, `scripts/despike_tad_5s.py` removes upward radar echoes from the 5 s samples, `scripts/analyse_senglea_spectrum.py` applies the quality control and computes the spectrum of the Senglea record, and `scripts/figure_senglea_record.py` draws the plates used to inspect it.

`scripts/build_mesh_v02.py` builds the mesh of the domain by zone, and `scripts/build_mesh_smoke_test.py` runs it in D-Flow FM at rest and under a forced long wave, reporting the time step and the wall time.

`scripts/probe_emodnet_bathymetry.py` interrogates the EMODnet Bathymetry services over an arbitrary bounding box, reporting grid resolution, wet-cell coverage and the CDI provenance records actually used by the digital terrain model. It was written to establish whether the public product was adequate for this site, and it is applicable to any coastal domain.

## Opening the data in QGIS

### Use the processed pair, not the raw files

```
data/processed/mepa_4036_merged_10m_wgs84.tif      raster, EPSG:4326
data/processed/malta_coastline_wgs84.gpkg          vector, EPSG:4326
```

Both carry their coordinate system correctly and are already co-registered, so
they may be dragged into a blank project and will overlay. Set the project CRS
to EPSG:4326 to match, or to EPSG:32633 when distances are to be measured, since
measurement in degrees is meaningless.

### If a raw file must be opened

The ESRI ArcInfo binary grids are directories rather than single files. Use
**Layer, Add Layer, Add Raster Layer** and select `hdr.adf` inside
`data/raw/mepa_4036/son_sbed/` or `lid_sbed/`.

**The coordinate system must then be assigned by hand.** These grids do not
encode their datum, QGIS reads them as unknown, and an unknown layer is assumed
to share the project CRS. Where the project is WGS84 that assumption displaces
the raster by approximately 197 m with no warning. Correct it through **Layer
Properties, Source, Set Source Coordinate Reference System**, entering
**EPSG:23033**.

The raw coastline at `data/raw/coastline/MaltaCoastline.shp` declares EPSG:32633
correctly and needs no intervention, but it sits in a different datum from the
raw bathymetry and the two will not overlay until both are set.

### Styling the bathymetry

Layer Properties, Symbology, **Singleband pseudocolor**. The field spans roughly
-262 to +150 m about a meaningful zero at sea level, so a diverging ramp with an
explicit stop at 0 reads correctly where a continuous ramp does not. Setting the
minimum and maximum to -45 and +60 renders the harbours legibly, the full range
being dominated by the open shelf.

The Identify tool reports the elevation at a point. Values are orthometric,
referenced to a surface approximating mean sea level, and require no geoid
correction. See Section 3 of [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md).

### Figure

`figures/bathymetry_overview.png` shows the same two datasets at island and
harbour scale, alongside the public EMODnet product at the same extent. It is
regenerated by `scripts/figure_bathymetry_overview.py`.
