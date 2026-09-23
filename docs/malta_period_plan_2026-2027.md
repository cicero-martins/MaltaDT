# Malta research period — operational plan (Sep 2026 to Mar 2027)

*Host: Oceanography Malta Research Group, University of Malta. Technical host: Prof. Adam Gauci.*
*Home: UNIPA, PhD in coupled-physics modelling of shallow vegetated Mediterranean lagoons (Stagnone DT).*
*Frame: Interreg VI-A Italia-Malta WETWISE, deliverable D.3.3.3 (WP3, RCO116), due 06.2027.*
*Drafted 2026-09-14, three days before the first block. Supersedes the schedule implied by the abstract frozen 2026-04-28.*

> **Partially superseded 2026-09-22.** The site was decided with Prof. Gauci during B1 and it is the **Valletta harbours** (Grand Harbour and Marsamxett), not a shallow vegetated lagoon. Sections 2, 3 and 4 below are replaced by [malta_valletta_model_plan.md](malta_valletta_model_plan.md). Section 1 (the block arithmetic), Section 5 (the parallel UNIPA track) and Section 6 (the generic risks) still hold. The site selection criteria in Section 3 are kept as the record of how the decision was framed, not as a live decision.

---

## 1. The arithmetic of the period

The period is six calendar months but it is not six months of work.

| Block | Dates | Calendar days | Working days |
|---|---|---|---|
| B1 | Thu 17 Sep to Sat 26 Sep 2026 | 10 | 7 |
| B2 | Wed 7 Oct to Sat 17 Oct 2026 | 11 | 8 |
| B3 | Tue 27 Oct to Sat 21 Nov 2026 | 26 | 19 |
| B4 | Tue 1 Dec to Sat 19 Dec 2026 | 19 | 14 |
| B5 | Tue 19 Jan to Sat 6 Feb 2027 | 19 | 14 |
| B6 | Tue 23 Feb to Sat 27 Mar 2027 | 33 | 24 |
| **Total** | | **118** | **86** |

Presence covers 61 percent of the 192-day window. Five gaps fall in Palermo.

| Gap | Dates | Days | Working days |
|---|---|---|---|
| G1 | 27 Sep to 6 Oct | 10 | 7 |
| G2 | 18 Oct to 26 Oct | 9 | 6 |
| G3 | 22 Nov to 30 Nov | 9 | 6 |
| G4 | 20 Dec to 18 Jan | 30 | 21 (holidays reduce this to roughly 12 effective) |
| G5 | 7 Feb to 22 Feb | 16 | 11 |

Three consequences follow directly and they shape everything below.

B3 and B6 hold 43 of the 86 working days. All heavy model building belongs in B3 and all closure belongs in B6. Nothing structural should be planned for the short blocks.

B1 has 7 working days and sits three days from now. It cannot be a technical block. It is the block where every item with a lead time longer than two weeks gets triggered, and the October campaign depends entirely on it.

The gaps are not dead time. They are where the long simulations run unattended and where the parallel UNIPA obligations fit without competing for host-group contact hours.

---

## 2. Objective hierarchy

The April abstract opened three lines. With 86 fragmented working days they do not fit at equal depth, so they are ranked.

**Core, non-negotiable.** Port the coupled FM plus SWAN framework to a Maltese site and measure what the port actually cost. The transfer effort is itself the measurement. A structured log of what was reused unchanged, what needed site-specific adjustment and what had to be written from scratch is the primary evidence for the reproducibility claim. Without that log the chapter is an anecdote.

**Supporting, feeds the core.** Retrain and stress-test the Random-Forest bottom-class classifier on Maltese scenes using October ground-truth. This is the natural joint contribution with the host group, it is the input the vegetation drag needs, and it is the piece that most clearly carries the host group expertise in remote sensing and machine learning.

**Bounded side-analysis.** CALYPSO and i-WaveNET HF-radar surface currents cross-checked against the model and against the Stagnone offshore boundary. This is data analysis rather than new model construction, so it fits a single block (B4) and degrades gracefully if squeezed.

**Reduce to a paragraph.** Vertical land movement in the long-term scenario layer. Keep it as a discussion point in the paper and the thesis, not as an executed work package. It was the weakest of the three in the abstract and it is the one with no path to a result inside the window.

---

## 3. Site selection criteria (the B1 decision)

The site is the single decision that everything downstream inherits, and it is due by 24 September. Criteria, in order of veto power.

1. **The sea connection must be representable as an open boundary.** If exchange happens through a culvert or sluice the model becomes a hydraulic-structure problem and transferability is no longer what is being tested. This is what removed Il-Maghluq in April and the same test applies to every candidate.
2. **Sub-metre to few-metre depth with a vegetated bed.** Without a canopy the `[veg]` module has nothing to do and half the framework sits idle, which defeats the purpose.
3. **Scale genuinely different from the Stagnone but not degenerate.** A site 5 to 50 times smaller tests transfer. A site a thousand times smaller turns into a mesh-resolution exercise rather than a physics one.
4. **At least one water-level source independent of our own campaign**, so that logger failure does not take the validation down with it.
5. **Access and authorisation achievable within three weeks.** Natura 2000 status implies an ERA permit and that lead time is the campaign critical path.
6. **Recognised as the WETWISE Maltese pilot.** If the site is not the one the project recognises, the output does not count towards D.3.3.3 and the institutional argument for the period weakens.

Candidates to put to the host group, all to be verified rather than assumed: Is-Salini and Salina Bay, Il-Ballut ta' Marsaxlokk (the April default), and shallow vegetated embayments such as Marsaxlokk, Mellieha or St Paul's. Il-Maghluq stays excluded on criterion 1 unless the group argues otherwise.

---

## 4. Block-by-block plan

### B1, 17 to 26 September. Decide and trigger.

Leave Malta with the site fixed, the permit filed, the instruments identified and the data inventory closed. Nothing else in this block matters as much.

- **17 to 18 Sep.** Opening meeting with the host group. Present the Stagnone DT in thirty minutes, reusing the LaTeX status report and the eight Paper 1 figures rather than building anything new. The output wanted from the meeting is a shortlist of sites and a name in the group attached to each work line.
- **19 to 20 Sep, weekend.** Field reconnaissance of the shortlisted sites. Access, mooring points for loggers, kayak launch, photographs.
- **21 to 23 Sep.** Data inventory. Bathymetry (EMODnet, any UM survey, the national LiDAR or DTM held by the Planning Authority, nautical charts), nearest tide gauge in the UM network, HF-radar coverage over each candidate, PlanetScope and Sentinel-2 archive availability, and any existing habitat mapping from ERA or MSFD reporting.
- **24 Sep.** Site decision, written down and agreed with the group.
- **25 Sep.** ERA permit application filed. Equipment list agreed and ownership settled. Campaign dates locked against the tide and the weather window.

### G1, 27 September to 6 October. Palermo.

- **Submit Stagnone Paper 1.** The blockers are known and small: the `[REF-wave-current-lagoon]` placeholder, CRediT roles, and one end-to-end read of the PDF. This is days of work on a manuscript that is otherwise finished, and it is the highest-value lowest-effort item in the whole six months. If it does not go out here it will rot until April.
- Download CMEMS and ERA5 forcing for the Maltese domain. Notebooks 00-09 already do this, only the bounding box changes.
- Build a first mesh skeleton from existing bathymetry, following the sequence recorded in the StagnoneDT memory entry `mesh_generation_workflow`.
- Campaign logistics. Logger calibration, batteries, field sheets, weather contingency.

### B2, 7 to 17 October. Field campaign.

Five products, in fixed priority order, because the wind decides how many get done.

1. **Pressure loggers.** Two or three in water plus one barometric on land, moored in the first two days and left until March. Partial downloads in December and January. This is the dataset that validates everything else.
2. **Habitat ground-truth.** Sixty to a hundred and twenty GPS points with a drop-camera, stratified by class. Feeds the RF retraining, costs little, needs no large boat.
3. **Bathymetry.** Single-beam echo sounder plus RTK-GNSS from a kayak on parallel lines, two to three days. Satellite-derived bathymetry is the fallback if the water is clear and shallow enough.
4. **GPS drifters.** Repeat the Stagnone protocol. Needs one or two days of usable wind. This is what makes the Maltese paper directly comparable to Paper 1.
5. **CTD profiles.** Stratification, initial condition and validation.

Also request PlanetScope tasking or confirm archive coverage for a cloud-free scene within three days of the ground-truth work, so that classification and validation share an acquisition.

### G2, 18 to 26 October. Palermo.

Process the survey into a site DTM and a first real mesh. Turn the ground-truth into an RF training table. **Submit the SWOT paper**, or finish Paper 1 if it overran G1.

### B3, 27 October to 21 November. Build the model. The main block.

- **Week 1.** Final mesh and bathymetry, open boundary from CMEMS, following notebooks 10-19. First FM-only run.
- **Week 2.** SWAN coupling through DIMR. Nested grids, explicit `ComInterval`, `ncFormat=3`. Every gotcha is already documented in `../../StagnoneDT/docs/fm_2026_gotchas.md` and in the associated memory entries, which is precisely the reuse the transferability claim rests on. First coupled run.
- **Week 3.** Retrain the classifier on a Maltese scene with October ground-truth, generate the site `.arl` and `[veg]` configuration. Watch the two known traps, nine decimal places in the `.arl` and CRS matching the mesh.
- **Week 4.** First calibration against the logger record, and close the ensemble design.
- **Throughout, keep the porting log.** One row per pipeline stage recording reused, adjusted or rewritten, plus the hours spent. This is the paper data, not bookkeeping.

### G3, 22 to 30 November. Palermo.

Launch long simulations on simit-server or EDITO. Absorb GEE reviews if they have arrived.

### B4, 1 to 19 December. Validate and couple to observations.

- Partial logger download, roughly two months of record, and the first water-level validation.
- Boundary datum calibration. The Marettimo anchored-offset methodology transfers directly and is already documented.
- **HF-radar work.** Extract CALYPSO surface currents over the site, cross-check against the model, and run the same comparison against the Stagnone offshore boundary. This closes the third abstract line inside one block.
- Agree the joint paper skeleton with the host group. Title, figure list, author order, CRediT.

### G4, 20 December to 18 January. Palermo, holidays.

Assume twelve effective days rather than twenty-one. Long runs in the background. GEE revision. Paper 1 revisions if they return.

### B5, 19 January to 6 February. Ensemble and writing.

- Sensitivity ensemble at the Maltese site, mirroring the Paper 1 design at reduced size. The scientific value is the cross-site comparison, not a full factorial repeated.
- Write Methods and Results of the joint paper.
- **Westrade collaboration begins.** Scope to be specified, see open questions.
- Formal contribution to D.3.3.3.

### G5, 7 to 22 February. Palermo.

Final runs, figures, results locked.

### B6, 23 February to 27 March. Closure. Second-largest block.

- Recover the loggers. Roughly five months of continuous record, and the final validation against the complete series.
- Final reference run of the Maltese DT.
- **Finish and submit the joint UNIPA-UMalta paper.**
- Deliver the WETWISE pilot package. Container, data, documentation. Delivering in March leaves three months of margin before the June 2027 deadline.
- Closing seminar at UM.
- Draft the thesis chapter on framework reproducibility, built on the porting log.

---

## 5. Parallel UNIPA track

Three obligations run alongside, two of them reactive.

| Item | Nature | Slot | Note |
|---|---|---|---|
| Stagnone Paper 1 | Own deadline, nearly finished | **G1, by 6 Oct** | Three known blockers, all small |
| SWOT paper | Own deadline, to submit | **G2, by 26 Oct** | Slips to G3 if Paper 1 overruns |
| GEE Paper 1 revision | Reactive, arrives when it arrives | G3, G4 or G5 | Reserve two to three weeks of buffer wherever it lands |
| Westrade | Scheduled, scope unspecified | B5, G5, B6 | Needs a defined share of time before it can be planned |

Only the first two have dates of their own. Everything else is buffer, and the buffer is deliberately kept in the Palermo gaps so that host-group contact time is never spent on UNIPA work.

---

## 6. Risks and decision points

**Authorisation slips past the campaign.** The whole plan hinges on this one. Mitigated by filing on 25 September and by holding a fallback site without Natura 2000 restrictions. Decision point 5 October. If the permit has not moved, the campaign shifts into B3 and model building compresses.

**Bathymetry turns out insufficient.** A shallow vegetated site with no survey produces a mesh that cannot be calibrated. The own survey is priority 3 in the campaign for this reason, with SDB as reserve. Decision point at the end of G2.

**Fragmentation cost.** Each return costs roughly half a day of recontextualisation, which over six blocks is three working days. Mitigated by closing every block with a ten-line written handoff, the same discipline as the progress reports maintained in StagnoneDT.

**Campaign fails outright.** The joint paper then falls back to framework transferability using public data only. Weaker, still publishable, and the porting log survives intact because it does not depend on field data. This is the reason the porting log is the core objective rather than the campaign.

**UNIPA obligations collide with a Malta block.** Accepted rather than mitigated. The rule is that reactive work waits for the next gap unless a journal deadline forbids it.

---

## 7. Open questions before this plan is final

1. What is the Westrade collaboration, what is the expected commitment, and is there a deliverable attached? It is currently a reserved block with no content.
2. Does the bando or the mobility contract assume a continuous six-month stay? If the official document still says October to December, it needs updating to match this fragmentation.
3. Equipment ownership. Do the loggers, echo sounder, RTK and drifters come from UNIPA or from the host group? This sits on the B1 critical path.
4. Has the site been discussed with the host group since April, or does B1 start from the April shortlist?
5. Were the downstream artefacts from the April application ever produced, specifically the acceptance letter, the De Marchis support letter, the budget and the return plan?
