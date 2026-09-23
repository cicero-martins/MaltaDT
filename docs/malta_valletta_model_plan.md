# Valletta harbours model — specific plan

*Site decision taken with Prof. Adam Gauci during B1, September 2026.*
*Supersedes Sections 2, 3 and 4 of [malta_period_plan_2026-2027.md](malta_period_plan_2026-2027.md). The block calendar and the parallel UNIPA commitments in that document remain in force.*
*Section 5b is superseded in part by [mepa_4036_dataset.md](mepa_4036_dataset.md), which records the bathymetry subsequently obtained from the host group.*
*Drafted 2026-09-22, mid-B1, four working days before the block closes.*

---

## 1. What the site change does to the thesis argument

Grand Harbour and Marsamxett are not shallow vegetated lagoons. They are deep drowned river valleys, roughly 12 to 20 m, heavily engineered, with quay walls, breakwaters, an active commercial port and no seagrass canopy worth resolving. Three things the Stagnone framework is built around do not apply here: the `[veg]` canopy drag, the Random-Forest bottom-class classifier (which needs optically visible bottom), and the hypersaline evaporation-driven density field.

That is a real cost and it has to be stated rather than smoothed over. It is also, on balance, worth paying, because it converts a weak research question into a strong one.

The April abstract asked whether the framework transfers to another shallow vegetated lagoon. That is a same-archetype test, and a reviewer is entitled to answer "obviously it does" before reading the results. The Valletta site asks instead whether the framework transfers **across archetype**, from a micro-tidal, wind-driven, sub-metre vegetated lagoon to a deep, engineered, seiche-dominated harbour. Same solver, same pipeline, opposite forcing hierarchy. That is a reusability claim with something at stake.

The porting log stays the core deliverable and gains a third column. Every pipeline stage is classified as **transferred unchanged**, **re-parameterised**, or **not applicable**. The third column is a finding about where the framework's generality ends, not an admission of failure, and it is the part a methods paper can actually defend.

Expected shape of that log, to be confirmed by doing it:

| Transferred unchanged | Re-parameterised | Not applicable |
|---|---|---|
| dfm_tools mesh generation workflow | Open boundary (Riemann instead of prescribed level) | `[veg]` canopy drag |
| CMEMS MED-MFC boundary chain | Vertical discretisation (deep, stratified, not sub-metre) | RF bottom-class classifier over the harbour |
| Anchored-offset datum methodology | SWAN nested grids and resolution | Hypersaline initial condition |
| ERA5 plus station wind blending | Output intervals (seiche band, not tidal band) | ERA5 evaporation forcing |
| DIMR coupling and the whole gotcha catalogue | Bed roughness (quay walls, hard bottom) | D-Morph sediment configuration |
| Validation methodology (raw plus anomaly, post-spinup) | Mesh resolution targets | Satellite-derived bathymetry over the harbour |
| OpenDrift regrid and Lagrangian scoring | | |
| Containerised EDITO deployment | | |

---

## 2. The scientific question

The local phenomenon is the **milgħuba**, the seiche oscillation of the Maltese harbours. Sea level fluctuations in the 0.2 to 2 cph band carry enough energy to mask the tidal signal completely, and they drive swift alternating currents at the harbour entrances that are a known nuisance to navigation and a principal mechanism of water exchange between the harbours and the open sea. Sir George Airy described the phenomenon in the Grand Harbour in 1878. The host group owns the modern scientific treatment of it through Drago's work on the northern-coast seiches.

This sets up the transferability test precisely. At the Stagnone the tide is the boundary signal and the wind drives the circulation. At Valletta a long-wave resonance dominates both. The question, scoped to fit 86 working days:

> Given observed atmospheric forcing from the PORTO coastal network and observed offshore conditions from the BLUE buoy, does the coupled Delft3D FM plus SWAN framework reproduce the observed seiche response of Grand Harbour and Marsamxett, in period, amplitude and inter-basin phase, and what does that response imply for harbour flushing and residence time?

The resonant periods are a property of the basin geometry, which the model has. This is well posed and answerable.

**The honest limitation, stated up front rather than discovered by a reviewer.** ERA5 at 0.25 degrees and hourly cannot resolve the atmospheric gravity waves that trigger the milgħuba. The model therefore tests the harbour's **response** to observed forcing, not the prediction of the trigger. The 1-minute pressure records from the coastal stations are the route to a better forcing field, and whether a moving pressure disturbance can be reconstructed from them is a secondary question worth one experiment, not a work package.

**Why the September to March window is the right one anyway.** Milgħuba events are favoured by particular atmospheric conditions, often associated with upper-air flow from the southeast, and they concentrate in the autumn and winter storm season. With no instruments of our own this matters for a different reason than it would have: by B6 the BLUE and PORTO archives will span a full winter of events that can be analysed as they accumulate, and the host group already publishes event-based analyses of their own network. A storm case study is the natural spine of the results section.

---

## 3. The observing system, and what it changes

This is the reason the site is worth the reframe. The data situation is the inverse of the earlier plan, where an unmapped lagoon had to be surveyed from a kayak before anything could be modelled.

| Asset | What it gives | Role in this work |
|---|---|---|
| **BLUE buoy**, 2.1 nm (3.7 km) off Grand Harbour, operating since 4 Jul 2025, 10-min transmission | Wind, waves, currents, T, S, turbidity, DO, pH, CO2 | Offshore validation point inside the domain. Plays the Marettimo role, far better instrumented and much closer. Roughly 14 months of archive already exists |
| **PORTO network**, 7 coastal meteo stations at 1-min sampling plus 4 sea level stations | Wind, air T, pressure, humidity, heat flux; sea level and sea T | Atmospheric forcing and sea level validation. The 1-min pressure is the only realistic route to resolving seiche triggering |
| **HF radar**, 4 stations over the Malta Channel | Surface currents and waves | Direct validation of modelled surface currents, and the third abstract line |
| **Tide gauges**: Portomaso (MedGLOSS, real-time since 2001), Cirkewwa (IDSL, NEAMTWS), Transport Malta at Marsaxlokk and Mgarr | Sea level | Independent sea level, and long records for the seiche climatology |
| **CDI `4036_MEPA`**, a coastal survey ringing the islands, contributed by the host group itself (EDMO 708). Plus UKHO and the Admiralty ENCs | Bathymetry for the whole coastal domain, published by EMODnet flattened to 115 m | The native-resolution original is the single highest-value ask in B1. See Section 5b |
| **BathMalta** (UM, Sentinel-2/3 nearshore SDB) | Satellite bathymetry over Maltese nearshore | The natural home for the SDB and classifier line, outside the harbours |
| **ocean.mt/bluedata** portal | Public live charts, AI bulletin | Dissemination route that already exists. Portal work becomes integration, not construction |

Two consequences follow.

**What the network covers and what it does not.** Water level, waves and meteorology are measured offshore and along the coast, which is what makes modelling without a campaign viable at all. Inside the harbours there is no published current, stratification or seiche-amplification record, and the nearest sea level station sits outside both basins. Whether that interior gap is real or merely unpublished is an open question for the host group, handled in Section 5.

**The WetWise portal architecture has somewhere to land.** They have a working public portal with an audience and stakeholders. Integrating model output into an existing portal is a much better deliverable than standing up a second one, and it maps directly onto WETWISE D.3.3.3.

---

## 4. Model configuration, and where it departs from the Stagnone

**Domain.** A single FM domain covering Grand Harbour and Marsamxett together, since they share the Valletta peninsula and open onto the same stretch of coast, extended offshore past the BLUE mooring so that BLUE is an interior validation point rather than a boundary. Open boundary from CMEMS MED-MFC further out. Nested SWAN grids following the Stagnone pattern.

**Mesh.** The creeks are the resonators, so resolution follows them rather than the open water. Marsa, French Creek, Dockyard Creek, Kalkara and Rinella on the Grand Harbour side; Msida, Pieta, Lazzaretto and Sliema on the Marsamxett side. Under-resolving a creek removes its mode from the solution, which is a silent failure mode with no error message. Quay walls and the St Elmo breakwater need explicit treatment as thin dams or fixed weirs.

**Open boundary type is the main technical departure.** A prescribed water level boundary reflects outgoing long waves back into the domain and will contaminate exactly the signal being studied. This needs a weakly reflective or Riemann boundary, which the Stagnone configuration never required. Budget time for getting this right, and test it with a synthetic long-wave pulse before trusting any seiche result.

**Output intervals.** The seiche band is 0.2 to 2 cph, so periods of 30 minutes to 5 hours. History output at stations needs roughly 1-minute resolution. Map output can stay coarse. Getting this wrong aliases the entire target signal.

**Vertical.** Deep and potentially stratified rather than sub-metre and wind-sheared. Wetting and drying largely stops being a problem. Whether sigma layers remain appropriate or z-layers serve better is an open configuration question for B3, and the inner creeks at Marsa are the likely place stratification matters.

**Gotchas that still apply unchanged.** Explicit `ComInterval`, `ncFormat=3` for the SWAN HDF re-open, `uxuyadvectionvelocitybnd` for offshore stability, `bedLevType=3`. The whole of `../../StagnoneDT/docs/fm_2026_gotchas.md` transfers, and that transfer is itself evidence for the reuse claim.

**Unresolved forcing, to be named in the paper rather than modelled.** Ship traffic in an active commercial port. Not tractable at this scope.

---

## 5. Modelling on existing data. No campaign planned for now.

**Working assumption from 2026-09-22: proceed on data that already exists, with no field campaign planned.** This keeps port authority clearance, instrument procurement and weather dependency off the critical path and frees the eight working days of B2 along with the download and recovery time in B4, B5 and B6.

This is a deferral rather than a cancellation. If the work reaches a point where an interior measurement is genuinely the blocker, a small deployment can be requested then, on evidence of what is missing rather than in anticipation of it.

**The interior gap is a question to put to the host group, not a settled loss.** Nobody currently publishes currents inside the harbours, stratification in the inner creeks, or the mouth-to-head amplification of the seiche, and the nearest sea level station, Portomaso, sits in St Julian's outside both basins. Before treating that as a fixed constraint, three things are worth asking, in order:

1. **Do they already hold interior data in some form?** Historic ADCP deployments, student dissertations, port engineering or dredging surveys, water quality monitoring, or anything gathered for the harbours' status as heavily modified water bodies under the Water Framework Directive.
2. **Is there an alternative route to it?** Transport Malta, the port operators, the cruise terminal, the ferry operators or the shipyard may hold operational records. A sensor already moored for another purpose may be possible to piggyback on.
3. **If neither, would a small deployment be feasible later?** Two or three pressure loggers at the creek heads is a far smaller ask than a full campaign, and it can be raised once the model shows precisely where the uncertainty bites.

Until those are answered the plan proceeds as if interior validation is unavailable, and Section 6 says what that implies. That assumption is meant to be revisited, not inherited.

**The validation set becomes:**

| Source | What it validates | Where |
|---|---|---|
| BLUE buoy, 10-min, since Jul 2025 | Offshore waves, wind, currents, T and S | Interior point, 3.7 km off the Grand Harbour mouth |
| PORTO sea level stations | Sea level, including the seiche band if sampling allows | Coastal, outside the harbours |
| Portomaso tide gauge, real-time since 2001 | Long sea level record, seiche climatology | St Julian's |
| HF radar, 4 stations, hourly, 3 km | Surface currents and waves | Malta Channel, offshore |
| PORTO meteo, 1-min | Atmospheric forcing, and the pressure signature of seiche events | 7 coastal stations |

**The first task is not modelling, it is characterising the target.** Before the mesh exists, the observed seiche climatology has to be extracted from the Portomaso and PORTO records: dominant periods, amplitude distribution, seasonality, the atmospheric conditions that accompany events, and the relationship between offshore conditions at BLUE and coastal response. That defines what the model has to reproduce, and it can be done in G1 with no model at all. If the sea level stations sample too coarsely to resolve the 0.2 to 2 cph band, that is discovered in G1 rather than in March, and the study re-scopes then.

**Check first, in B1:** the sampling interval of the PORTO sea level stations. The meteo stations are documented at 1 minute. If the sea level stations are also at 1 minute the seiche band is fully resolved and the absence of our own loggers costs much less than feared. If they are at 10 minutes or coarser, only the long end of the band survives and the study leans on the model's internal consistency plus the Portomaso record instead.

---

## 5b. Bathymetry: EMODnet, and the honest limit

**EMODnet Digital Bathymetry DTM 2024** is the baseline. It is open, covers the Central Mediterranean, and is served by OGC web services (WMS, WFS, WCS, WMTS) as well as by tile download. Grid resolution is 1/16 by 1/16 arc-minute, **about 115 m**.

**That resolution is a problem inside the harbours and it has to be faced directly.** French Creek, Dockyard Creek, Kalkara and Rinella on the Grand Harbour side, and Msida, Pieta and Lazzaretto on the Marsamxett side, are roughly 100 to 300 m wide. At 115 m a creek is one to three cells across. The creeks are the resonators. A creek resolved by one cell has no mode, and the model will not complain about it.

Refining the mesh does not fix this. A mesh finer than the source data interpolates, it does not add information. Building a 20 m mesh on a 115 m depth field produces a smooth-bottomed caricature of a creek with the right planform and the wrong geometry, which is worth knowing but is not the same as resolving it.

**What rescues a reduced scope is that the coastline is good and the physics is forgiving at basin scale.** For a quarter-wave resonator open at the mouth, the period goes as T ≈ 4L/√(gh). The length L comes from the planform, which a high-resolution coastline gives directly. The depth h enters as a basin-mean, which is far better constrained than creek-scale detail. So the **main-basin modes of Grand Harbour and Marsamxett are recoverable from EMODnet plus a good coastline**, while the creek modes are not.

That is the defensible scope: target the main-basin response, state the creek limitation in the methods rather than the discussion, and turn the uncertainty into a result by running an explicit **sensitivity of modelled seiche period to the depth field**. Perturbing the basin-mean depth and reporting how the modes move is a better answer than a single deterministic period that quietly depends on an interpolation.

### What the CDI check actually returned (done 2026-09-22)

The check was run rather than deferred, with `scripts/probe_emodnet_bathymetry.py`. Three EMODnet services were queried and two of them disagree, which is itself the most useful part of the result.

**Grid, from WCS `emodnet__mean`.** Cell size over the harbours is **94 m by 115 m**, as expected.

| | Grand Harbour | Marsamxett |
|---|---|---|
| Grid over the basin | 32 x 19 cells | 25 x 16 cells |
| Water cells | 222 of 608 (37%) | 77 of 400 (19%) |
| Water width per row | 7 to 13 cells in the main body, 25 at the mouth | mostly 4 to 8 cells, several rows at 1 to 4 |
| Depth | mean 18.4 m, max 36.0 m | mean 14.3 m, max 32.3 m |

So the **main basin of Grand Harbour is marginally resolvable**, roughly 7 to 13 cells across, which is crude but not hopeless for a basin-scale mode. **Marsamxett is not.** At 19 percent water and typically 4 to 8 cells across, and with two points chosen inside the harbour returning **positive elevation, that is, land**, the basin is barely present in the data at all. The creeks in both are 1 to 3 cells and are absent as resonators, exactly as feared.

**Provenance, and the finding that matters.** The WFS `source_references` layer returns only **GEBCO2024** over the whole Maltese area, which would say no survey exists anywhere. That layer is simply wrong, or at least badly incomplete. The REST `depth_sample` service, which reports what the DTM actually used at a point and whether it was interpolated, finds **at least six contributing sources** around the islands. Sampling 144 points on a 0.04 degree grid over Malta, Gozo and Comino:

| Source | Points | Where |
|---|---|---|
| `UKHO` | 41 | dominant regionally, UK Hydrographic Office |
| `DTM_CNR-ISMAR-127` | 28 | regional DTM, mostly east and northeast |
| **`4036_MEPA`** | **17** | **a coastal ring around the Maltese Islands**, Gozo through to southern Malta |
| `LifeBAHAR` | 14 | west and southwest, from the LIFE BaĦAR for N2K habitat mapping |
| `GEBCO2024` | 10 | fallback in the corners |
| `CNR-ISMAR-21` | 1 | |

**`4036_MEPA` is not a Valletta harbour survey, it is a national coastal survey.** It forms a ring around the whole island fringe, and a denser probe over the Valletta area at roughly 450 m spacing confirms it is the **dominant source there**, covering 32 of 130 sampled points against 12 for the regional CNR-ISMAR DTM, with the rest land. It was contributed by **EDMO 708**, which is the **Oceanography Malta Research Group, Department of Geosciences, University of Malta**.

That changes what the ask is worth. Requesting `4036_MEPA` at native resolution is not a request for one harbour's bathymetry, it is a request that would serve **the entire coastal model domain**, and it goes to the host group's own data holding. One conversation covers the whole problem.

MEPA is the Malta Environment and Planning Authority, since split into ERA and the Planning Authority, so there is a second possible holder if the group's own copy is not the original.

**What the 115 m gridding does to the harbour entrances, independently of source.** A transect across the Marsamxett mouth, from the Tignè side to St Elmo, returns a string of cells at **z between -0.04 and -1.08 m with no source record at all**, sitting between cells of -25 to -29 m. Meshed as they stand, those cells form a near-closing sill across the entrance, or a wetting and drying front where a ten-metre-plus channel belongs, and either destroys the exchange the seiche depends on. This is a gridding and coastline-registration artefact rather than a survey failure, and it is the thing most likely to silently break a model built straight off the public product.

**The CDI report page is JavaScript-gated** and cannot be read headlessly, so `https://cdi-bathymetry.seadatanet.org/report/edmo/708/4036_MEPA` has to be opened in a browser, or simply asked about directly.

**This reorders the sources.** Asking the host group for `4036_MEPA` at native resolution is the single highest-value question in B1. It is their own data, and because the survey rings the whole island it resolves the bathymetry for the entire domain rather than for one basin.

1. **Ask Gauci for `4036_MEPA` at native resolution**, by that identifier. His own group contributed it and it covers the whole island fringe, so it serves the entire domain. Ask what its native resolution and survey method actually are, since that sets the achievable mesh.
2. **UKHO and the Admiralty ENCs.** UKHO is already the largest contributor around Malta, and both harbours are charted in detail for commercial navigation. Chart soundings are the natural cross-check on the harbour entrances, which is exactly where the gridded product fails.
3. **EMODnet DTM 2024 as the offshore baseline.** Sufficient outside the harbours and around the BLUE mooring, and that part of the domain is not in question.
4. **BathMalta**, for the nearshore outside the harbours rather than inside them.

Note that EMODnet incorporates Sentinel-2 satellite-derived bathymetry in some areas, which will not help here. Harbour water is deep and turbid and SDB has no signal in it.

**If nothing better than EMODnet materialises**, the honest consequence is that the study covers the **Grand Harbour main basin only**, with Marsamxett reduced to a boundary condition or dropped from the modelled domain, and the creeks treated as unresolved in both. That is a smaller paper than the one in Section 2, and it is still a real one, but the decision should be taken deliberately at the end of G1 rather than absorbed silently into a mesh.

---

## 5c. Key literature

Five works establish the basis for the present study. Their relevance is indicated in each case.

1. **Drago, A. (2009).** *Sea level variability and the 'Milgħuba' seiche oscillations in the northern coast of Malta, Central Mediterranean.* Physics and Chemistry of the Earth 34, 948–970. The phenomenon itself, from 43 months of densely sampled sea level at Mellieħa Bay, 1993–1996. Establishes the 0.2 to 2 cph band, the masking of the tidal signal, the interpretation as shelf-scale resonance amplified in the embayments, and the atmospheric triggering. The study answers to this work, whose author belongs to the host group.

2. **Drago, A., Sorgente, R. & Ribotti, A. (2003).** *A high resolution hydrodynamic 3-D model simulation of the Malta shelf area.* Annales Geophysicae 21(1), 323–344. ROSARIO-I, a POM-based shelf model at 1.6 km with 15 sigma layers, one-way nested into a coarser Sicily Channel model. It describes the regional circulation inherited by the open boundary and represents the modelling lineage of the host group, which warrants explicit acknowledgement when a different solver is proposed.

3. **Capodici, F., Cosoli, S., Ciraolo, G., Nasello, C., Maltese, A., Poulain, P.-M., Drago, A., Azzopardi, J. & Gauci, A. (2019).** *Validation of HF radar sea surface currents in the Malta-Sicily Channel.* Remote Sensing of Environment 225, 65–76. The work establishes the accuracy of the surface current field against which the model is to be validated, assessed by comparison with drifters, near-surface ADCP measurements and site-to-site baselines. The authorship spans UNIPA and the University of Malta and includes Ciraolo and Maltese, which establishes a precedent for the intended joint publication.

4. **Orasi, A., Picone, M., Drago, A., Capodici, F., Gauci, A., Nardone, G., et al. (2018).** *HF radar for wind waves measurements in the Malta-Sicily Channel.* Measurement 128, 446–454. Significant wave height from the CALYPSO network compared against numerical models and satellite altimetry, the first analysis of the wave data from the four radars installed 2012–2015. The observational basis for validating the SWAN side of the coupling.

5. **Romeo, T., D'Alessandro, M., Esposito, V., Scotti, G., Berto, D., ... Mazzola, A., ... Deidun, A. & Renzi, M. (2015).** *Environmental quality assessment of Grand Harbour (Valletta, Maltese Islands): a case study of a busy harbour in the Central Mediterranean Sea.* Environmental Monitoring and Assessment 187(12). Contaminants, plastic debris and macrobenthic diversity in Grand Harbour soft bottoms. The work is not concerned with hydrodynamics and is included deliberately, since it establishes the environmental significance of flushing and residence time and supplies the framing required by the WETWISE deliverable. Deidun is based at the Department of Geosciences of the University of Malta and Mazzola at UNIPA, constituting a second existing link between the two institutions.

**Historical antecedent.** Sir George Airy described seiche oscillations in the Grand Harbour in 1878, among the earliest scientific treatments of the phenomenon. The present study would constitute the first three-dimensional coupled wave-hydrodynamic representation of the same basin.

**Methodological analogues, for the flushing and residence-time analysis rather than for the site:**

- **Samper, Y., Liste, M., Mestres, M., Espino, M., Sánchez-Arcilla, A., Sospedra, J., González-Marco, D., Ruiz, M.I. & Álvarez Fanjul, E. (2022).** *Water exchanges in Mediterranean microtidal harbours.* Water 14, 2012. Lagrangian renewal time in Barcelona, Tarragona and Gijón, reporting bottom renewal times of 32 and 61 days in the two microtidal Mediterranean ports. The study provides the closest available template for the output expected from the OpenDrift pipeline at this site.
- **Spatial variability analysis of renewal time in harbour environments using a Lagrangian model.** Journal of Marine Science and Engineering 13(2), 341 (2025). The work treats the spatial variability of the same quantity.

---

## 6. What happens to the three abstract lines

**Framework transfer.** Strengthened and promoted to cross-archetype. Core deliverable, unchanged in weight.

**Random-Forest bottom-class classifier.** Does not survive contact with a deep turbid harbour. Rather than dropping it, relocate it: **BathMalta**, the UM Sentinel-2/3 nearshore bathymetry project, is the natural collaboration, applied to Maltese nearshore outside the harbours. It becomes a parallel joint output with the host group instead of an input to the harbour model. This is an honest downgrade and the abstract text should be corrected to match rather than left to imply otherwise.

**HF radar.** Strengthened. Four stations over the Malta Channel with the model domain sitting inside their footprint. It now validates the model's own surface currents rather than only cross-checking the Stagnone boundary, and the Stagnone cross-check comes along for free.

**Vertical land movement.** Unchanged, still a discussion paragraph rather than a work package.

**What the claims look like without interior validation.** If Section 5 resolves with no interior data, the model is constrained at its offshore boundary by BLUE, along the coast by the sea level and meteo stations, and over the channel by HF radar, while its behaviour inside the basins is a prediction rather than a verified result. Three claims still stand on that footing. The **transferability claim** is unaffected, because the porting log measures the effort of the port, not the accuracy of the interior field. The **seiche response claim** holds for the coastal signal and for the model's own modal structure, which can be checked against Drago's observed periods and against the analytical quarter-wave estimate, and that triangulation is worth more than it sounds. The **flushing and residence time claim** becomes explicitly a model-based estimate with an uncertainty range rather than a validated number, which is how the Mediterranean harbour literature in Section 5c reports it anyway. What would not survive is any claim about the detailed interior current field, and the paper should simply not make one.

**Bonus worth asking about.** The PORTO network includes four stations on the southern coast of Sicily. If those records are accessible they may be directly useful to StagnoneDT, which would be a free win for the home project.

---

## 7. B1 closing actions, 22 to 26 September

Four working days remain. Everything here has a lead time that exceeds them, which is why it belongs in this block rather than the next.

All of these are questions to put to the host group rather than tasks to execute alone, and most of them can only be answered in the room.

| When | Action | Why it belongs in this block |
|---|---|---|
| Tue 22 | **Ask Gauci for CDI `4036_MEPA` at native resolution**, by that identifier, and for its survey method. The EMODnet check is already done: his own group contributed it (EDMO 708) and it rings the whole island, so it covers the entire domain | Sets the achievable mesh, and decides whether the creeks and the harbour entrances are in scope. Section 5b |
| Wed 23 | **Ask about interior data**: any historic ADCP, student dissertation, port engineering or WFD monitoring inside the basins, and whether an alternative route exists through the port operators | Section 5 turns on the answer, and it changes what the paper can claim |
| Wed 23 | **Confirm the sampling interval of the PORTO sea level stations** | If coarser than the seiche band the study re-scopes, and better now than in March |
| Wed 23 | Data access terms in writing for BLUE, PORTO, HF radar and the tide gauges: archive extent, formats, latency, licensing for publication | Verbal agreement will not survive a journal data-availability statement |
| Thu 24 | Agree the scientific question and the joint paper with Gauci: seiche response plus harbour flushing, authorship, target journal | Everything downstream inherits this |
| Thu 24 | Fix the domain extent on a chart, and agree which coastline source to use | B3 cannot start cold, and the coastline carries the planform the modes depend on |
| Fri 25 | Ask about the Sicilian PORTO stations for StagnoneDT | Free if asked now |
| Fri 25 | Written block handoff, the ten-line discipline from the period plan | Three weeks pass before B3 |

**If a later deployment turns out to be necessary**, the permitting authority is **Transport Malta, Ports and Yachting Directorate**, not ERA, because both harbours are active commercial ports with cruise traffic, bunkering, ferries and a shipyard. Worth establishing the lead time now as information, even with nothing planned, so that the option stays open rather than having to be discovered later.

---

## 8. Revised block allocation

The calendar is unchanged. What each block does is not.

- **G1, 27 Sep to 6 Oct.** Submit Stagnone Paper 1, unchanged and still the priority. Pull the Portomaso, PORTO and BLUE archives and **characterise the observed seiche climatology before touching the model**, because that defines what the model has to reproduce and it needs no model to do. Assemble EMODnet DTM 2024 for the domain and see how the harbours actually look at 115 m. CMEMS and ERA5 for the Maltese domain.
- **B2, 7 to 17 Oct.** Freed by the campaign decision, and best spent on the things that benefit from being in the room. Finish the seiche climatology **with** the host group, since they know the events and the instrument quirks. Assemble the bathymetry and coastline and check the harbour planform against local knowledge. First mesh. Resolve whatever Section 5 and Section 5b left open in B1.
- **B3, 27 Oct to 21 Nov.** The build. Mesh with creek-following resolution as far as the depth data supports it, **Riemann boundary with a synthetic long-wave test before anything else**, depth-field sensitivity on the modal periods, FM-only run, then SWAN coupling, then first comparison against the coastal sea level records and BLUE.
- **G3, 22 to 30 Nov.** Long runs. GEE reviews if they arrive.
- **B4, 1 to 19 Dec.** Seiche validation proper against the coastal stations, and comparison of modelled modal periods against Drago's observed ones and the analytical estimate. HF radar surface current comparison. Joint paper skeleton agreed.
- **G4, 20 Dec to 18 Jan.** Runs in background, holidays, UNIPA obligations.
- **B5, 19 Jan to 6 Feb.** Flushing and residence time experiments through the OpenDrift pipeline, reported as a range rather than a number, following the Mediterranean harbour literature. Methods and Results written. Westrade begins. D.3.3.3 contribution.
- **G5, 7 to 22 Feb.** Figures, final runs.
- **B6, 23 Feb to 27 Mar.** Storm event case study using the BLUE and PORTO records, which by then cover a full winter. Submit the joint paper. Integrate model output into the existing ocean.mt portal rather than building a new one. Closing seminar. Thesis chapter from the porting log.

---

## 9. Risks specific to this site

**Bathymetry resolution, the central risk, now quantified.** Measured rather than feared: EMODnet gives the Grand Harbour main basin 7 to 13 cells across, workable for a basin mode, Marsamxett 4 to 8, and a near-zero sill strung across the Marsamxett entrance that would close the basin if meshed as it stands. Creeks are 1 to 3 cells in both and their modes are absent with no error raised. Mitigated by asking the host group for `4036_MEPA` at native resolution, by scoping to main-basin modes, and by making the depth-field sensitivity an explicit result. **Decision point end of G1**: if nothing better arrives, Marsamxett leaves the modelled domain and the paper narrows to the Grand Harbour.

**The coastal sea level stations sample too coarsely for the seiche band.** Would leave the model with no observational target at all in its own frequency range. Checked on 23 September for that reason, and the fallback is the Portomaso long record plus the modal comparison against Drago's published periods.

**The open boundary reflects.** Would invalidate every seiche result while producing plausible-looking output. Mitigated by the synthetic long-wave test in B3 week 1, before any production run.

**Interior behaviour stays unvalidated.** Accepted as the cost of not running a campaign, and bounded by not making claims that depend on it. Revisit if Section 5 turns up interior data, or if the model reaches a point where a small deployment is demonstrably the blocker.

**The thesis coherence question.** A reviewer or a committee member may ask how a deep engineered harbour belongs in a thesis on shallow vegetated lagoons. The cross-archetype framing in Section 1 is the answer, and it is stronger if stated deliberately in the thesis introduction than if it appears defensive in a viva. Worth raising with De Marchis early rather than late.

---

## 10. Open questions

Most of these are for the host group, and the first four shape what the study can be.

1. **Can we have CDI `4036_MEPA` at native resolution, and what is that resolution?** Their own group contributed it (EDMO 708) and it rings the whole island, so it serves the entire domain rather than one basin. EMODnet publishes it flattened to 115 m. This is the question that sets the achievable mesh and decides whether the creeks and the harbour entrances are in scope. Section 5b.
2. **Is there any interior record, in any form?** Historic ADCP, student dissertations, port engineering or dredging surveys, WFD monitoring of the two heavily modified water bodies, or operational data held by the port operators, the ferries, the cruise terminal or the shipyard. Section 5.
3. **What is the sampling interval of the PORTO sea level stations?** If it resolves the 0.2 to 2 cph band, the absence of our own loggers costs much less than feared.
4. Confirm the BLUE archive actually starts 4 July 2025 and is continuous. Fourteen months of 10-minute data would already cover a full milgħuba season, which is what makes the G1 climatology possible.
5. Are the 8 port-area weather stations mentioned in the BLUE launch the same as the 7 PORTO meteo stations, or an additional set? Which of them sit inside the harbours?
6. Is there an agreed coastline product for the Maltese Islands, and at what resolution? With a coarse depth field the planform carries more of the modal structure than usual.
7. If a small deployment later proves necessary, what is the realistic lead time through Transport Malta, Ports and Yachting? Worth knowing as information even with nothing planned.
8. What is the Westrade collaboration, still unspecified from the previous plan.
9. Does the bando documentation name a site? If it commits to a lagoon, the change needs to be recorded with UNIPA.
