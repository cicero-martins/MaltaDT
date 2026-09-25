# Model plan for the Valletta harbour system

*Site selected with Prof. Adam Gauci during block B1, September 2026. Drafted 22 September 2026, revised 23 September 2026 following receipt of the bathymetric dataset.*

*This document supersedes Sections 2, 3 and 4 of [malta_period_plan_2026-2027.md](malta_period_plan_2026-2027.md). The block calendar and the parallel commitments at UNIPA recorded there remain in force. Section 6 below is superseded in part by [mepa_4036_dataset.md](mepa_4036_dataset.md), which documents the bathymetry subsequently obtained.*

---

## 1. Implications of the site selection for the thesis argument

The Grand Harbour and Marsamxett are not shallow vegetated lagoons. They are drowned river valleys of approximately 12 to 20 m depth, extensively engineered, bounded by quay walls and breakwaters, in active commercial use, and without seagrass canopy of a density warranting representation. Three components around which the Stagnone framework is constructed are consequently inapplicable, namely the `[veg]` canopy drag module, the Random-Forest bottom-class classifier, which requires an optically visible bed, and the hypersaline evaporation-driven density field.

The cost is real and is stated rather than elided. It is nonetheless justified, since the substitution converts a weak research question into a stronger one.

The proposal submitted in April asked whether the framework transfers to a second shallow vegetated lagoon. Such a test remains within a single archetype, and a reviewer would be entitled to anticipate the outcome before consulting the results. The Valletta site instead tests whether the framework transfers **across archetype**, from a micro-tidal wind-driven lagoon of sub-metre depth beneath a seagrass canopy to a deep engineered harbour dominated by seiche. The solver and the pipeline are unchanged and the hierarchy of forcings is inverted. The reusability claim is correspondingly less certain of confirmation and therefore more informative.

The porting log remains the principal deliverable and acquires a third category. Each stage of the pipeline is classified as **transferred unchanged**, **re-parameterised**, or **not applicable**. The third category records where the generality of the framework terminates, which constitutes a result rather than a deficiency, and is the element a methodological paper is able to defend.

The anticipated structure of that log, subject to confirmation in execution:

| Transferred unchanged | Re-parameterised | Not applicable |
|---|---|---|
| `dfm_tools` mesh generation sequence | Open boundary, Riemann in place of prescribed level | `[veg]` canopy drag |
| CMEMS MED-MFC boundary chain | Vertical discretisation, deep and stratified rather than sub-metre | Random-Forest bottom-class classifier within the harbours |
| Anchored-offset datum methodology | SWAN nested grids and resolution | Hypersaline initial condition |
| ERA5 and station wind blending | Output intervals, seiche band rather than tidal band | ERA5 evaporation forcing |
| DIMR coupling and the associated configuration catalogue | Bed roughness, quay walls and hard bottom | D-Morph sediment configuration |
| Validation methodology, raw and anomaly metrics, post-spinup window | Mesh resolution targets | Satellite-derived bathymetry within the harbours |
| OpenDrift regridding and Lagrangian scoring | | |
| Containerised EDITO deployment | | |

---

## 2. Research question

The governing phenomenon is the **milgħuba**, the seiche oscillation of the Maltese harbours. Sea level fluctuations in the band 0.2 to 2 cph carry sufficient energy to mask the tidal signal in its entirety, and they generate rapid alternating currents at the harbour entrances that constitute both a recognised impediment to navigation and a principal mechanism of exchange between the harbours and the open sea. Airy described the phenomenon in the Grand Harbour in 1878. Its modern treatment is due to Drago, of the host group.

The configuration establishes the transferability test precisely. At the Stagnone the tide supplies the boundary signal and the wind drives the circulation. At Valletta a long-wave resonance governs both. The question, scoped to the 86 working days available, is as follows.

> Given observed atmospheric forcing from the PORTO coastal network and observed offshore conditions from the BLUE buoy, does the coupled Delft3D FM and SWAN framework reproduce the observed seiche response of the Grand Harbour and Marsamxett in period, amplitude and inter-basin phase, and what does that response imply for harbour flushing and residence time?

The resonant periods are a property of basin geometry, which the model represents. The question is therefore well posed and answerable within the period.

> **Superseded 2026-09-24.** The question above is retained as the point of departure. It was found to be verification presented as research, and the prior literature was found to include a two-dimensional numerical treatment of Maltese coastal seiches that the formulation does not clear. See [research_question_and_literature.md](research_question_and_literature.md) for the reframing, which moves the question to the partition of amplification between the plateau, the approach and the basins.

**Limitation of the atmospheric forcing.** ERA5, at 0.25 degrees and hourly resolution, does not resolve the atmospheric gravity waves that trigger the milgħuba. The model accordingly tests the **response** of the harbours to observed forcing rather than the prediction of the triggering mechanism. The one-minute pressure records from the coastal stations offer a route to an improved forcing field, and whether a propagating pressure disturbance can be reconstructed from them constitutes a secondary question meriting a single experiment rather than a work package. The limitation is stated at the outset rather than left for a reviewer to identify.

**Temporal coverage of the research period.** Milgħuba events are favoured by particular atmospheric conditions, frequently associated with upper-air flow from the southeast, and they concentrate in the autumn and winter storm season. Since no instruments are to be deployed, the relevance of the period differs from that originally envisaged. By block B6 the BLUE and PORTO archives will span a complete winter of events available for analysis as they accumulate, and the host group already publishes event-based analyses of its own network. A storm case study accordingly provides the natural organising structure for the results.

---

## 3. Observational infrastructure

The availability of observations is the principal justification for the site. The situation inverts that of the earlier plan, in which an unsurveyed lagoon would have required a bathymetric campaign before any model could be constructed.

| Asset | Measurements | Function in the present work |
|---|---|---|
| **BLUE buoy**, 2.1 nm (3.7 km) off the Grand Harbour, operating since 4 July 2025, transmitting at 10 min | Wind, waves, currents, temperature, salinity, turbidity, dissolved oxygen, pH, CO2 | Offshore validation point within the domain, equivalent in function to Marettimo at the Stagnone but more comprehensively instrumented and considerably closer. Approximately 14 months of archive already exist |
| **PORTO network**, 7 coastal meteorological stations at 1 min, 4 sea level stations | Wind, air temperature, pressure, humidity, heat flux; sea level and sea temperature | Atmospheric forcing and sea level validation. The one-minute pressure record is the only realistic route to resolving seiche triggering |
| **PORTO stations at Elmo and Kordin**, two of the seven | As above | Both lie on the Grand Harbour, Elmo at the entrance and Kordin on the southern shore, and they are therefore the closest atmospheric record to the basin under study. Identified from the station map in Drago (2018) |
| **HF radar**, 4 stations over the Malta Channel | Surface currents and waves | Validation of modelled surface currents |
| **Tide gauges**: Portomaso (MedGLOSS, real time since 2001), Ċirkewwa (IDSL, NEAMTWS), Transport Malta at Marsaxlokk and Mġarr | Sea level | Independent sea level and long records for the seiche climatology |
| **CDI `4036_MEPA`**, a coastal survey encircling the islands, contributed by the host group (EDMO 708) | Bathymetry at 10 m over the whole coastal domain | Obtained 22 September 2026. See [mepa_4036_dataset.md](mepa_4036_dataset.md) |
| **`MaltaCoastline.shp`**, 26 polygons, 315.4 km2, WGS84 / UTM 33N | Land and water boundary for the Maltese Islands | Obtained 23 September 2026. See [coastline_dataset.md](coastline_dataset.md) |
| **BathMalta**, University of Malta, Sentinel-2 and Sentinel-3 nearshore satellite-derived bathymetry | Satellite bathymetry over the Maltese nearshore | Appropriate destination for the classifier and SDB line, outside the harbours |
| **ocean.mt/bluedata** portal | Public live charts and automated bulletins | Existing dissemination route. Portal work becomes integration rather than construction |

Two consequences follow.

**Coverage of the network.** Water level, waves and meteorology are measured offshore and along the coast, which is what renders modelling without a campaign viable. Within the harbours no current, stratification or seiche-amplification record is published, and the nearest sea level station lies outside both basins. Whether that interior gap is genuine or merely unpublished remains an open question for the host group, addressed in Section 5.

**Applicability of the WetWise portal architecture.** The host group operates a public portal with an established audience. Integration of model output into that portal constitutes a more appropriate deliverable than the construction of a second one, and corresponds directly to WETWISE deliverable D.3.3.3.

### 3.1 The modelling system the host group already operates

Drago (2018), the group's design report for Action A.7 of the LIFE RBMP project, records what exists and what was intended. The document is held at `reference/` and its contents bear on the position of the present work more than any other item found in the literature search.

| Component | Configuration as reported in 2018 |
|---|---|
| ROSARIO, Princeton Ocean Model | Eddy-resolving, 1/64° and 1/96°, hourly and three-hourly output of temperature, salinity and velocity |
| WAM | 1/8° over the central Mediterranean |
| SWAN | Downscaling of the wave forecast to the embayments on a regular grid of **1/500°**, approximately 200 m |
| SHYFEM | Finite-element, unstructured, over the **Maltese Islands and the Malta Channel to a substantial part of the southern Sicilian coast**, under development for coastal hydrodynamics |

The published record on the last of these carries further detail. ROSARIO-SHYFEM is reported as operational, running daily to a four-day forecast of the three-dimensional fields, with **resolution grading from a few kilometres to 50 m** at the coast, and coupled to a Lagrangian particle-tracking component applied to jellyfish trajectories and, with BFM, to water quality within a marine protected area.

Three matters follow.

**The SHYFEM domain is the domain proposed here, and the resolutions differ by a factor of two to three inside the harbours.**

| | ROSARIO-SHYFEM | Proposed here |
|---|---|---|
| Extent | Maltese Islands and the Malta Channel to southern Sicily | 86 × 66 km over Malta and the near plateau |
| Coarsest | a few km | 1.5 km |
| Finest | 50 m at the coast | 15 m in the inlets, 30 m in the basins |
| Dimensionality | 3D | 3D |
| Waves | Separate SWAN downscaling at 1/500° | Coupled through DIMR |
| Lagrangian | Present, with BFM in some applications | OpenDrift, ported from the Stagnone |
| Mode | Operational, daily, four-day forecast | Process study and hindcast |

The difference is one of resolution inside the basins, of coupling, and of frequency band, rather than of capability. A Lagrangian tool already exists in the group and the renewal question should be positioned accordingly rather than as the provision of something missing.

**The present work is an independent exercise tied to the research period and does not stand in relation to that system as an alternative to it.** The comparison above is recorded so that the claims made here are correctly bounded, not because the scope depends on it. The operational system is a useful point of reference, and a comparison of the two over the shared extent would be informative if the group had an interest in it, but nothing in the plan requires that comparison to take place.

**The boundary condition remains CMEMS, which is also what the host group uses.** The ROSARIO system is itself nested into CMEMS, and the group derives the boundary conditions for its meteo-marine forecasting models from that source. Taking CMEMS MED-MFC for the open boundary is therefore the same practice as the host group's rather than a departure from it, and it keeps the configuration continuous with the Stagnone. Should that boundary prove limiting in the long-wave band, the ROSARIO output resolves the Malta Channel more finely and can be examined at that point, but the question does not arise at the outset.

**The SWAN resolution proposed in the sizing exercise agrees with the group's own.** Arrangement C in [domain_and_discretisation.md](domain_and_discretisation.md) proposes a nest at 250 m, arrived at from the width of the harbour entrances. The group operates its downscaling at approximately 200 m. The agreement is independent and it supports the choice.

**Harbour flushing is a stated objective of the design rather than an incidental interest.** The report sets out an intention to establish local-scale models in proximity to and inside the five principal harbours, with process models for flushing, siltation, water quality and coastal engineering impact linked to them, in support of Water Framework Directive and Marine Strategy Framework Directive obligations. It names the Deltares suite among the model families to be reviewed for that role and carries three Deltares staff on its international working group. The renewal question recorded as a fallback in the research-question document is accordingly an institutional objective of the host group, and the framework arriving with this project is one of the candidates that document names.

### 3.2 Relocatability, and the EDITO-hosted pilot

The design report states a requirement that had not previously been connected to this project. Among the points listed for the numerical modelling component it asks for a review of

> the adaptability of the various local scale models to be used in a relocatable model setup so as to be able to monitor ad hoc local scale marine domains within the coastal area of the Maltese Islands,

and elsewhere envisages that the suite of local models be deployed as a relocatable version applicable to any area of interest with the same setup and modelling infrastructure.

Relocatability is the thesis argument of this project stated in the host group's own terms. The framework transfer from the Stagnone to Valletta is a demonstration of exactly that property, and the porting log is the evidence for it. The correspondence is close enough that the transfer log should be presented to the group in that language rather than only as a methodological result for the thesis.

**The infrastructure element is available and is a differentiator.** The Stagnone twin is already containerised and hosted on European public infrastructure rather than running only on local machines.

| Component | Present state at the Stagnone |
|---|---|
| Model execution | `delft3dfmrun-docker` on the EDITO Datalab, with input and output on the project S3 bucket |
| Post-processing | Two-stage regrid producing a compact binary payload, executed where the partitioned output lives |
| Dissemination | Static portal published to EDITO object storage at `minio.dive.edito.eu`, no server to maintain |
| Maturity | L2 on the five-level scale recorded in the scaling roadmap, with the step to L3 and L4 identified as chiefly a matter of operational engineering rather than of physics |

A Valletta configuration could therefore be stood up on the same infrastructure without constructing anything new, which converts the deliverable from a set of result figures into a running pilot that outlives the research period. It also supplies a concrete answer to the relocatability requirement above, since the same container and the same publication route would serve a second domain.

**This is recorded as a possibility conditional on progress rather than as a commitment.** It depends on the model reaching a stable configuration early enough in the period, and it should be raised with the host group only once there is something to show. Its natural place is block B6, alongside the integration into the existing ocean.mt portal, and the two are complementary rather than alternatives, since the portal reaches the group's established audience while the EDITO deployment carries the execution.

### 3.3 The sea level network, and the gap inside the harbours

The same report states the design of the sea level network as one permanent coastal station at PortoMaso, with two further stations then planned at Marsaxlokk and at Mġarr Harbour, to be integrated into GLOSS and MedGLOSS and combined with seabed pressure sensors for tsunami early warning. Anomalous sea level phenomena are named explicitly among the purposes.

No station inside the Valletta basins appears in that design. The interior gap recorded in Section 5 is therefore a property of the network as designed rather than an omission in what has been published, which raises the value of establishing whether an older Grand Harbour installation exists in the archive.

---

## 4. Model configuration and departures from the Stagnone

**Domain.** A single Delft3D FM domain encompassing the Grand Harbour and Marsamxett together, since the two share the Valletta peninsula and open onto the same stretch of coast, extended offshore beyond the BLUE mooring so that the buoy constitutes an interior validation point rather than a boundary. The open boundary is taken from CMEMS MED-MFC further offshore. Nested SWAN grids follow the Stagnone configuration.

**Mesh.** The inlets constitute the resonating elements, so resolution follows them in preference to the open water. On the Grand Harbour side these are French Creek, Dockyard Creek, Kalkara Creek and Rinella Creek, together with the head of the harbour at Marsa. On the Marsamxett side they are Sliema Creek, Lazzaretto Creek, Msida Creek and Pietà Creek. The word creek carries here its British nautical sense of a narrow tidal inlet, these being arms of a drowned river valley rather than watercourses. Under-resolution of an inlet removes its mode from the solution, a failure mode that produces no diagnostic message. Quay walls and the St Elmo breakwater require explicit treatment as thin dams or fixed weirs.

**Open boundary specification, the principal technical departure.** A prescribed water level boundary reflects outgoing long waves back into the domain and contaminates the signal under study. A weakly reflective or Riemann boundary is required, which the Stagnone configuration never was. Time must be allocated to establishing it correctly, and it must be verified with a synthetic long-wave pulse before any seiche result is relied upon. The requirement now has a precedent in the same basin. Laksono et al. (2026) apply Delft3D to tsunami propagation over the Sicilian Channel on a domain of comparable extent and state that the Riemann condition is applied specifically to prevent artificial wave reflection at the model boundaries.

**Output intervals.** The seiche band of 0.2 to 2 cph corresponds to periods between 30 minutes and 5 hours. History output at stations therefore requires approximately one-minute resolution. Map output may remain coarse. An incorrect setting aliases the entire target signal.

**Vertical discretisation.** The setting is deep and potentially stratified rather than sub-metre and wind-sheared, and wetting and drying largely ceases to be a consideration. Whether sigma layers remain appropriate or z-layers are preferable is an open configuration question for block B3. Stratification is most likely to be material at Marsa, at the head of the Grand Harbour.

**Configuration constraints transferring unchanged.** Explicit `ComInterval`, `ncFormat=3` for the SWAN HDF re-open, `uxuyadvectionvelocitybnd` for offshore stability, and `bedLevType=3`. The catalogue at `../../StagnoneDT/docs/fm_2026_gotchas.md` transfers in its entirety, and that transfer constitutes evidence for the reuse claim.

**Unresolved forcing.** Vessel traffic within an active commercial port is not tractable at this scope and is to be identified as a limitation in the manuscript rather than represented.

---

## 5. Data basis and the status of field observation

**Working assumption adopted 22 September 2026.** The study proceeds on existing observations, with no field campaign planned. This removes port authority clearance, instrument procurement and weather dependency from the critical path and releases the eight working days of block B2 together with the download and recovery time otherwise required in blocks B4, B5 and B6.

The decision constitutes a deferral rather than a cancellation. Should the work reach a point at which an interior measurement is demonstrably the limiting factor, a limited deployment may be requested at that stage, on evidence of what is missing rather than in anticipation of it.

**The interior gap is a question for the host group rather than a settled loss.** No current record within the harbours, stratification record for the inner inlets, or measurement of the mouth-to-head amplification of the seiche is presently published, and the nearest sea level station, Portomaso, lies in St Julian's outside both basins. Before that is treated as a fixed constraint, three enquiries are warranted, in order.

1. **Whether interior data exist in some form.** Historic ADCP deployments, student dissertations, port engineering or dredging surveys, water quality monitoring, or material gathered in connection with the status of the two harbours as heavily modified water bodies under the Water Framework Directive.
2. **Whether an alternative route exists.** Transport Malta, the port operators, the cruise terminal, the ferry operators and the shipyard may hold operational records. A sensor already moored for another purpose may admit of a secondary use.
3. **Whether a limited deployment would be feasible subsequently.** Two or three pressure loggers at the heads of the inlets constitute a considerably smaller request than a full campaign, and may be raised once the model has identified where the uncertainty is consequential.

Pending those answers the plan proceeds as though interior validation were unavailable, and Section 8 states the implications. The assumption is intended to be revisited rather than inherited.

**The validation set is accordingly as follows.**

| Source | Quantity validated | Location |
|---|---|---|
| BLUE buoy, 10 min, since July 2025 | Offshore waves, wind, currents, temperature, salinity | Interior point, 3.7 km off the Grand Harbour entrance |
| PORTO sea level stations | Sea level, including the seiche band if the sampling interval permits | Coastal, outside the harbours |
| Portomaso tide gauge, real time since 2001 | Long sea level record, seiche climatology | St Julian's |
| HF radar, 4 stations, hourly, 3 km | Surface currents and waves | Malta Channel, offshore |
| PORTO meteorological stations, 1 min | Atmospheric forcing and the pressure signature of seiche events | 7 coastal stations |

**The first task is characterisation of the target rather than modelling.** Before the mesh exists, the observed seiche climatology is to be extracted from the Portomaso and PORTO records, comprising dominant periods, amplitude distribution, seasonality, the atmospheric conditions accompanying events, and the relation between offshore conditions at BLUE and the coastal response. That analysis defines what the model is required to reproduce and requires no model to conduct. It is scheduled for block G1. Should the sea level stations prove to sample too coarsely to resolve the band 0.2 to 2 cph, the limitation is established in October rather than in March and the study is rescoped accordingly.

**The sampling interval of the PORTO sea level stations requires confirmation in block B1.** The meteorological stations are documented at one minute; the sea level stations are not documented. Should they also sample at one minute, the seiche band is fully resolved and the absence of dedicated instruments is of limited consequence. Should they sample at ten minutes or coarser, only the long end of the band survives and the study relies instead on the internal consistency of the model together with the Portomaso record.

---

## 6. Bathymetry

The bathymetric basis has changed materially since this plan was first drafted. This section records the assessment of the public product that motivated the request to the host group, and the outcome of that request.

### 6.1 Assessment of the EMODnet product

The EMODnet Digital Bathymetry DTM 2024 is open, covers the Central Mediterranean, and is served through OGC web services as well as by tile download. Its resolution is 1/16 by 1/16 arc-minute, approximately 115 m, measured at 94 m by 115 m over the harbours.

An interrogation of three EMODnet services was conducted on 22 September 2026 using `scripts/probe_emodnet_bathymetry.py`.

| | Grand Harbour | Marsamxett |
|---|---|---|
| Grid over the basin | 32 x 19 cells | 25 x 16 cells |
| Water cells | 222 of 608 (37%) | 77 of 400 (19%) |
| Water width per row | 7 to 13 cells in the main body, 25 at the entrance | 4 to 8 cells, several rows at 1 to 4 |
| Depth | mean 18.4 m, maximum 36.0 m | mean 14.3 m, maximum 32.3 m |

The main basin of the Grand Harbour was therefore marginally resolvable at 7 to 13 cells across, which is crude but adequate for a basin-scale mode. Marsamxett was not. The inlets in both were represented by 1 to 3 cells and were absent as resonating elements.

A transect across the Marsamxett entrance, from the Tignè side to St Elmo, returned a sequence of cells at elevations between -0.04 and -1.08 m with no associated source record, situated between cells of -25 to -29 m. Meshed as supplied, those cells constitute a near-closing sill across the entrance, or a wetting and drying front where a channel exceeding ten metres in depth is present. Either outcome removes the exchange on which the seiche depends. The artefact arises from gridding and coastline registration rather than from survey failure, and it is the feature most likely to compromise a model constructed directly from the public product without detection.

### 6.2 Provenance, and the basis of the request

The WFS `source_references` layer returns only GEBCO2024 across the whole Maltese area, which would indicate that no survey exists. That layer is incomplete. The REST `depth_sample` service, which reports the source actually used at a given point together with whether the value was interpolated, identifies at least six contributing sources. Sampling 144 points on a 0.04 degree grid over Malta, Gozo and Comino returned the following distribution.

| Source | Points | Distribution |
|---|---|---|
| `UKHO` | 41 | Regionally dominant, UK Hydrographic Office |
| `DTM_CNR-ISMAR-127` | 28 | Regional DTM, principally east and northeast |
| **`4036_MEPA`** | **17** | **A coastal ring around the Maltese Islands**, from Gozo to southern Malta |
| `LifeBAHAR` | 14 | West and southwest, from the LIFE BaĦAR for N2K habitat mapping |
| `GEBCO2024` | 10 | Fallback at the margins |
| `CNR-ISMAR-21` | 1 | |

`4036_MEPA` is not a survey of the Valletta harbours but a national coastal survey encircling the island fringe. A denser probe over the Valletta area at approximately 450 m spacing confirmed it as the dominant source there, covering 32 of 130 sampled points against 12 for the regional CNR-ISMAR product, the remainder being land. It is attributed to EDMO 708, the Oceanography Malta Research Group of the University of Malta.

Requesting the dataset at native resolution therefore constituted a request serving the entire coastal domain rather than a single basin, addressed to the host group's own holding. This established it as the highest-value action available within block B1.

### 6.3 Outcome

The request was made on 22 September 2026 and met the same day. The dataset comprises two grids at **10 m**, LiDAR and sonar, covering Malta, Gozo and Comino, derived from 2 m mosaics. Over the harbours it resolves between 174 and 256 times more water cells than the public product, and inlets of 100 m width are represented by 10 cells rather than by fewer than one.

**The resolution constraint described in Section 6.1 is accordingly removed.** Marsamxett is retained within the modelled domain, the inlet-scale modes return to scope, and the reduced scope that the constraint had imposed is no longer required. A merged product has been constructed and is documented, together with the coordinate reference system hazard attaching to the source files, in [mepa_4036_dataset.md](mepa_4036_dataset.md).

The UKHO contributions and the Admiralty electronic navigational charts remain relevant as an independent check on the harbour entrances, which is where the gridded product was shown to fail.

---

## 7. Literature

Five works establish the basis for the present study. Their relevance is indicated in each case.

1. **Drago, A. (2009).** *Sea level variability and the 'Milgħuba' seiche oscillations in the northern coast of Malta, Central Mediterranean.* Physics and Chemistry of the Earth 34, 948–970. The phenomenon itself, from 43 months of densely sampled sea level at Mellieħa Bay between 1993 and 1996. The work establishes the band 0.2 to 2 cph, the masking of the tidal signal, the interpretation as shelf-scale resonance amplified within the embayments, and the atmospheric triggering. The present study answers to this work, whose author belongs to the host group.

2. **Drago, A., Sorgente, R. & Ribotti, A. (2003).** *A high resolution hydrodynamic 3-D model simulation of the Malta shelf area.* Annales Geophysicae 21(1), 323–344. ROSARIO-I, a POM-based shelf model at 1.6 km with 15 sigma layers, nested one-way within a coarser Sicily Channel model. The work describes the regional circulation inherited by the open boundary and represents the modelling lineage of the host group, which warrants explicit acknowledgement when a different solver is proposed.

3. **Capodici, F., Cosoli, S., Ciraolo, G., Nasello, C., Maltese, A., Poulain, P.-M., Drago, A., Azzopardi, J. & Gauci, A. (2019).** *Validation of HF radar sea surface currents in the Malta-Sicily Channel.* Remote Sensing of Environment 225, 65–76. The work establishes the accuracy of the surface current field against which the model is to be validated, assessed by comparison with drifters, near-surface ADCP measurements and site-to-site baselines. The authorship spans UNIPA and the University of Malta and includes Ciraolo and Maltese, establishing a precedent for the intended joint publication.

4. **Orasi, A., Picone, M., Drago, A., Capodici, F., Gauci, A., Nardone, G., et al. (2018).** *HF radar for wind waves measurements in the Malta-Sicily Channel.* Measurement 128, 446–454. Significant wave height from the CALYPSO network compared against numerical models and satellite altimetry, constituting the first analysis of the wave data from the four radars installed between 2012 and 2015. The work establishes the accuracy of the radar wave product itself. It does not supply a validation standard, and the distinction matters, since the radar reports a derived quantity whose own accuracy was assessed against models rather than an independent measurement of the sea state.

5. **Romeo, T., D'Alessandro, M., Esposito, V., Scotti, G., Berto, D., … Mazzola, A., … Deidun, A. & Renzi, M. (2015).** *Environmental quality assessment of Grand Harbour (Valletta, Maltese Islands): a case study of a busy harbour in the Central Mediterranean Sea.* Environmental Monitoring and Assessment 187(12). Contaminants, plastic debris and macrobenthic diversity within the soft bottoms of the Grand Harbour. The work is not concerned with hydrodynamics and is included deliberately, since it establishes the environmental significance of flushing and residence time and supplies the framing required by the WETWISE deliverable. Deidun is based at the Department of Geosciences of the University of Malta and Mazzola at UNIPA, constituting a second existing link between the two institutions.

**Historical antecedent.** Airy described seiche oscillations in the Grand Harbour in 1878, among the earliest scientific treatments of the phenomenon. The present study would constitute the first three-dimensional coupled wave-hydrodynamic representation of the same basin.

**Material added on 25 September 2026.** A second pass over the literature, prompted by documents supplied to `reference/`, added four items. Their assessment is carried in [research_question_and_literature.md](research_question_and_literature.md) and only their bearing on this plan is recorded here.

- **Mazas, F. and Farrugia, C.** *Protecting Valletta's Grand Harbour against adverse wave conditions.* Coastal Engineering Proceedings 154. ARTELIA and Infrastructure Malta. The Grand Harbour has been modelled for wind-wave agitation in PHAROS, and a protection scheme comprising an outer breakwater, a detached submerged breakwater and two revetments is before the planning authorities. The paper also supplies the directional wave climate off Valletta and records significant damage in the port from the storms of February 2019 and February 2023.
- **Drago, A.F. (2018).** *Designing an observing and forecasting system for the Maltese Islands.* Progress report, Action A.7, LIFE 16 IPE MT 008. The host group's design document, treated in Section 3.1 above.
- **Laksono, F.A.T. et al. (2026).** *Exploring the tsunami generation potential of major faults in the Sicilian Channel using 3D numerical modeling.* Ocean Modelling 199, 102625. Delft3D applied to long-wave propagation over the same channel, and the precedent for the Riemann boundary treatment recorded in `CLAUDE.md`.
- **Balzan, M.V. et al. (2022).** *Assessing nature-based solutions uptake in a Mediterranean climate: insights from the case-study of Malta.* Nature-Based Solutions 2, 100029. A stakeholder and governance analysis, relevant to the framing of the WETWISE deliverable rather than to the physics.

**A geometry that is not fixed.** The scheme described by Mazas and Farrugia would alter the mouth of the Grand Harbour. Any statement this study makes about the harbour describes the present configuration, and the distinction between the present and the proposed geometry should be carried explicitly from the outset rather than introduced later.

**Methodological analogues**, relevant to the flushing and residence-time analysis rather than to the site.

- **Samper, Y., Liste, M., Mestres, M., Espino, M., Sánchez-Arcilla, A., Sospedra, J., González-Marco, D., Ruiz, M.I. & Álvarez Fanjul, E. (2022).** *Water exchanges in Mediterranean microtidal harbours.* Water 14, 2012. Lagrangian renewal time in Barcelona, Tarragona and Gijón, reporting bottom renewal times of 32 and 61 days in the two microtidal Mediterranean ports. The study provides the closest available template for the output expected from the OpenDrift pipeline at this site.
- **Spatial variability analysis of renewal time in harbour environments using a Lagrangian model.** Journal of Marine Science and Engineering 13(2), 341 (2025). The work treats the spatial variability of the same quantity.

---

## 8. Status of the three lines of the original proposal

**Framework transfer.** Strengthened and extended to a transfer across archetype. It remains the principal deliverable, unchanged in weight.

**Random-Forest bottom-class classifier.** The method does not survive application to a deep harbour of limited optical clarity. Rather than being abandoned it is relocated. BathMalta, the University of Malta project on Sentinel-2 and Sentinel-3 nearshore bathymetry, constitutes the natural collaboration, applied to the Maltese nearshore outside the harbours. The line becomes a parallel joint output with the host group rather than an input to the harbour model. The reduction is genuine and the text of the proposal should be corrected accordingly rather than left to imply otherwise.

**HF radar.** Strengthened. Four stations cover the Malta Channel with the model domain within their footprint, so the network validates the surface currents of the present model rather than serving only as a cross-check on the Stagnone boundary. The Stagnone cross-check remains available at no additional cost.

**Vertical land movement.** Unchanged. It remains a matter for the discussion rather than a work package.

**Claims admissible in the absence of interior validation.** Should Section 5 resolve without interior data, the model is constrained at its offshore boundary by BLUE, along the coast by the sea level and meteorological stations, and over the channel by HF radar, while its behaviour within the basins constitutes a prediction rather than a verified result. Three claims remain admissible on that basis. The transferability claim is unaffected, since the porting log measures the effort of the transfer rather than the accuracy of the interior field. The seiche response claim holds for the coastal signal and for the modal structure of the model, which admits comparison against the periods reported by Drago and against the analytical quarter-wave estimate, and the resulting triangulation constrains the result more tightly than either comparison alone. The flushing and residence-time claim becomes explicitly a model-based estimate accompanied by an uncertainty range rather than a validated quantity, which is the form in which the Mediterranean harbour literature cited in Section 7 reports it. No claim regarding the detailed interior current field would be admissible, and none should be made.

**A secondary opportunity.** The PORTO network includes four stations on the southern coast of Sicily. Should those records be accessible they may be of direct use to StagnoneDT.

---

## 9. Actions for the remainder of block B1, 23 to 26 September

Three working days remain. Each item below has a lead time exceeding them, which is why it belongs to this block rather than the next. All are enquiries to be put to the host group rather than tasks to be executed independently, and most can only be resolved in person.

| Status | Action | Justification |
|---|---|---|
| **Completed 22 Sep** | Request CDI `4036_MEPA` at native resolution from Prof. Gauci | Met the same day. Two grids at 10 m. See Section 6.3 |
| Wed 23 | Establish the **levelling datum of `ContoursMalta`** and its offset against the tide gauge zeros, together with the availability of the 2 m products, the existence of a Part 2 of the December 2012 vessel survey, and the licensing terms for both datasets | The vertical reference is established as orthometric. Its relation to the gauges is what a water-level study requires |
| Wed 23 | Enquire as to **interior data** in any form, including historic ADCP records, student dissertations, port engineering surveys and Water Framework Directive monitoring, and as to alternative routes through the port operators | Section 5 turns on the answer, which determines what the manuscript may claim |
| Wed 23 | Confirm the **sampling interval of the PORTO sea level stations** | Should it prove coarser than the seiche band the study is rescoped, and establishing this now is preferable to establishing it in March |
| Thu 24 | Obtain **data access terms in writing** for BLUE, PORTO, the HF radar and the tide gauges, covering archive extent, formats, latency and licensing for publication | A verbal agreement will not satisfy a journal data availability statement |
| Thu 24 | Agree the **research question and the joint publication** with Prof. Gauci, comprising the seiche response and harbour flushing, authorship and target journal | Everything downstream inherits the decision |
| Thu 24 | Fix the **domain extent** on a chart and agree the coastline source | Block B3 cannot commence without them, and the coastline carries the planform on which the modes depend |
| Fri 25 | Enquire as to the **Sicilian PORTO stations** on behalf of StagnoneDT | Available at no cost if raised now |
| Fri 25 | Produce a **written block handoff** | Three weeks elapse before block B3 |

**Should a deployment subsequently prove necessary**, the permitting authority is Transport Malta, Ports and Yachting Directorate, rather than the Environment and Resources Authority, since both harbours are active commercial ports accommodating cruise traffic, bunkering, ferries and a shipyard. Establishing the lead time now, as information, preserves the option rather than requiring its discovery later.

---

## 10. Block allocation

The calendar is unchanged. The content of each block is revised.

- **G1, 27 September to 6 October.** Submission of Stagnone Paper 1, which remains the priority. Retrieval of the Portomaso, PORTO and BLUE archives and characterisation of the observed seiche climatology in advance of any modelling, since that analysis defines what the model is required to reproduce and requires no model to conduct. Construction of the merged bathymetry over the model domain and intersection of its gaps with a coastline. Retrieval of CMEMS and ERA5 forcing for the Maltese domain.
- **B2, 7 to 17 October.** Released by the decision against a campaign, and best directed to work benefiting from the presence of the host group. Completion of the seiche climatology in collaboration with them, given their familiarity with the events and with the instrumentation. Verification of the harbour planform against local knowledge. First mesh. Resolution of whatever Sections 5 and 6 leave outstanding after block B1.
- **B3, 27 October to 21 November, 15 working days rather than 19.** The Delft3D User Days occupy 2 to 4 November and the block loses four days with travel. Week one, 27 October to 1 November, is directed at the mesh and the first boundary experiments, so that the configuration questions reach Deltares in concrete form. Weeks three and four carry the depth-field sensitivity on the modal periods, the FM-only run, the SWAN coupling and a first comparison against the coastal sea level records and BLUE. The Riemann boundary verified by synthetic long-wave pulse precedes any production run. See Section 2.1 of the period plan.
- **G3, 22 to 30 November.** Extended runs. Review of the GEE manuscript should the referee reports arrive.
- **B4, 1 to 19 December.** Seiche validation against the coastal stations, and comparison of modelled modal periods against those reported by Drago and against the analytical estimate. HF radar surface current comparison. Agreement of the structure of the joint manuscript.
- **G4, 20 December to 18 January.** Background runs, holidays, commitments at UNIPA.
- **B5, 19 January to 6 February.** Flushing and residence-time experiments through the OpenDrift pipeline, reported as a range rather than a single value, following the Mediterranean harbour literature. Methods and Results drafted. Commencement of the Westrade collaboration. Contribution to deliverable D.3.3.3.
- **G5, 7 to 22 February.** Figures and final runs.
- **B6, 23 February to 27 March.** Storm event case study drawing on the BLUE and PORTO records, which by then span a complete winter. Submission of the joint manuscript. Integration of model output into the existing ocean.mt portal. Should the configuration have proved stable, deployment of the Valletta domain on the EDITO infrastructure as a running pilot, per Section 3.2. Closing seminar. Drafting of the thesis chapter from the porting log, presented against the relocatability requirement stated in the group's own design report.

---

## 11. Risks

**Relation between the bathymetric zero and the tide gauge zeros.** The vertical datum question is partly resolved. The files declare ETRS89 ellipsoidal height, that declaration is a mislabel, and the values are orthometric, established by control points and by a median of +0.00 m sampled along the independently supplied coastline. What remains is the relation between that zero and the zeros of the gauges used for validation. Should the two differ by an unquantified amount, the model could be calibrated against a systematically offset bed with the error absorbed into the boundary offset and misattributed. Pursued through the `ContoursMalta` source dataset.

**Coordinate reference systems of the supplied datasets.** The bathymetric grids are ED50 / UTM 33N without the datum encoded in the file, and the coastline is WGS84 / UTM 33N with the datum encoded correctly. The two differ by approximately 197 m at Malta, some 20 cells at 10 m, and neither may be overlaid on the other without a datum transformation. No error is raised in either direction. Mitigated by explicit assignment in `scripts/build_merged_bathymetry.py`, by verification of the bathymetry against seven control points and of the coastline against the land and water agreement test, and recorded in the project CLAUDE.md so that it survives into later sessions.

**Sampling interval of the coastal sea level stations.** Should it prove too coarse for the seiche band, the model would have no observational target within its own frequency range. Enquiry is scheduled for 23 September. The fallback is the long Portomaso record together with comparison of modal periods against those published by Drago.

**Reflection at the open boundary.** Would invalidate every seiche result while producing plausible output. Mitigated by the synthetic long-wave test scheduled for the first week of block B3, in advance of any production run.

**Interior behaviour remains unvalidated.** Accepted as the consequence of not conducting a campaign, and bounded by declining to make claims that depend upon it. To be revisited should Section 5 identify interior data, or should the model reach a point at which a limited deployment is demonstrably the limiting factor.

**Coherence of the thesis.** A reviewer or examiner may enquire how a deep engineered harbour belongs within a thesis concerned with shallow vegetated lagoons. The cross-archetype framing in Section 1 constitutes the answer, and it is more persuasive stated deliberately in the introduction than advanced defensively in a viva. The matter warrants discussion with Prof. De Marchis at an early stage.

---

## 12. Outstanding questions

Most are for the host group. The first three determine what the study can be.

1. **What is the levelling datum of the `ContoursMalta` dataset, and how does its zero relate to the tide gauge zeros?** The vertical datum of the bathymetry is established as orthometric rather than ellipsoidal, the declaration in the file being a mislabel. The remaining question concerns the realisation, and above all the offset against the gauges used for validation. See [coastline_dataset.md](coastline_dataset.md) and Section 3 of [mepa_4036_dataset.md](mepa_4036_dataset.md).
2. **Does any interior record exist, in any form?** Historic ADCP, student dissertations, port engineering or dredging surveys, Water Framework Directive monitoring of the two heavily modified water bodies, or operational data held by the port operators, the ferries, the cruise terminal or the shipyard. Section 5.
3. **What is the sampling interval of the PORTO sea level stations?** Should the band 0.2 to 2 cph be resolved, the absence of dedicated instruments is of limited consequence.
4. Confirmation that the BLUE archive commences on 4 July 2025 and is continuous. Fourteen months of ten-minute data would already span a complete milgħuba season, which is what renders the G1 climatology feasible.
5. Whether the eight port-area weather stations referred to at the BLUE launch are the same as the seven PORTO meteorological stations or an additional set, and which of them lie within the harbours.
6. **Whether any wave record exists beyond the BLUE buoy**, from an earlier deployment, a port authority or a coastal campaign. Wave validation presently rests on a single offshore point, since the radar reports a derived product rather than a measurement.
7. Licensing and attribution for the coastline, whose metadata template is unfilled, and whether the modification recorded in 2017 altered geometry or metadata alone.
8. Availability of the 2 m source mosaics, the existence of a Part 2 of the December 2012 vessel survey, and the survey accuracy. Detailed in [mepa_4036_dataset.md](mepa_4036_dataset.md).
9. Lead time through Transport Malta, Ports and Yachting Directorate, should a limited deployment subsequently prove necessary.
10. The nature of the Westrade collaboration, unspecified since the preceding plan.
11. Whether the bando documentation names a site. Should it commit to a lagoon, the change requires recording with UNIPA.
