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
| Bathymetry | Obtained. CDI `4036_MEPA`, 10 m LiDAR and sonar, Maltese Islands. See [docs/mepa_4036_dataset.md](docs/mepa_4036_dataset.md) |
| Observational basis | Identified. BLUE buoy, PORTO network, HF radar, Portomaso tide gauge. Access terms pending |
| Field campaign | Not planned. The study proceeds on existing observations |
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
- [CLAUDE.md](CLAUDE.md), working context and critical configuration facts

## Tooling

`scripts/probe_emodnet_bathymetry.py` interrogates the EMODnet Bathymetry services over an arbitrary bounding box, reporting grid resolution, wet-cell coverage and the CDI provenance records actually used by the digital terrain model. It was written to establish whether the public product was adequate for this site, and it is applicable to any coastal domain.
