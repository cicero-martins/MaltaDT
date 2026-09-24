# MaltaDT: model of the Valletta harbour system

Coupled wave-hydrodynamic model of the Grand Harbour and Marsamxett Harbour, Malta, constructed with Delft3D FM and SWAN coupled through DIMR.

Undertaken during a research period at the Oceanography Malta Research Group, Department of Geosciences, University of Malta, from September 2026 to March 2027, and contributing to deliverable D.3.3.3 of the Interreg VI-A Italia-Malta WETWISE project.

## Scientific framing

The project tests whether a coupled-physics modelling framework developed for a shallow vegetated micro-tidal lagoon transfers to a hydrodynamically dissimilar setting. The framework originates in the Stagnone di Marsala digital twin (`../StagnoneDT`), where tidal forcing sets the boundary signal and wind drives the circulation over sub-metre depths across a seagrass canopy. The Valletta harbours invert that hierarchy. They are drowned river valleys of 12 to 20 m depth, heavily engineered, without significant canopy, and dominated by the milgħuba, a seiche oscillation in the 0.2 to 2 cph band carrying sufficient energy to mask the tidal signal entirely.

The transfer is therefore across archetype rather than within it, which constitutes a stronger test of framework reusability than the transfer to a second lagoon originally proposed.

The governing question is whether the framework, forced by observed atmospheric conditions from the PORTO coastal network and observed offshore conditions from the BLUE buoy, reproduces the seiche response of the two harbours in period, amplitude and inter-basin phase, and what that response implies for harbour flushing and residence time.

## Status

| Component | State |
|---|---|
| Site selection | Fixed 22 September 2026 with the host group |
| Bathymetry | Obtained. CDI `4036_MEPA`, 10 m LiDAR and sonar, Maltese Islands. Merged. See [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md) |
| Coastline | Obtained. 26 polygons, 315.4 km2, WGS84 / UTM 33N, verified against the bathymetry. See [docs/coastline_dataset.md](docs/coastline_dataset.md) |
| Aligned basemap | Bathymetry and coastline co-registered in EPSG:4326 in `data/processed/`. 99.51% land and water agreement, median disagreement one cell |
| Observational basis | Identified. BLUE buoy, PORTO network, HF radar, Portomaso tide gauge. Access terms pending |
| Field campaign | Not planned. The study proceeds on existing observations |
| Research question | Reframed 24 September from model verification to attribution of amplification. See [docs/research_question_and_literature.md](docs/research_question_and_literature.md) |
| Domain and discretisation | Sized 23 September. Domain B over the plateau, 15 m in the inlets, 12 to 15 sigma layers. See [docs/domain_and_discretisation.md](docs/domain_and_discretisation.md) |
| Mesh | Not started. Scheduled for late October |
| Model | Not started |
| Seiche climatology | Not started. Scheduled for late September, from the Portomaso and PORTO archives |

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
reference/         third-party material
```

## Documents

- [docs/malta_valletta_model_plan.md](docs/malta_valletta_model_plan.md), the operative plan: scientific question, model configuration, block allocation, risks
- [docs/malta_period_plan_2026-2027.md](docs/malta_period_plan_2026-2027.md), the block calendar and the parallel commitments at UNIPA
- [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md), assessment of the bathymetric dataset
- [docs/coastline_dataset.md](docs/coastline_dataset.md), assessment of the coastline, including the inference establishing the vertical datum
- [docs/domain_and_discretisation.md](docs/domain_and_discretisation.md), sizing of the domain, the horizontal resolution and the vertical layering
- [docs/research_question_and_literature.md](docs/research_question_and_literature.md), the research question, the prior work it must clear, and the reading list
- [CLAUDE.md](CLAUDE.md), working context and critical configuration facts

## Tooling

`scripts/build_merged_bathymetry.py` combines the LiDAR and sonar components of the bathymetric dataset and writes the merged field in its native and geographic coordinate systems. `scripts/prepare_coastline.py` brings the coastline onto the working coordinate system and reports its registration against that field.

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
