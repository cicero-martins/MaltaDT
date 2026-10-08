// Deck, short version: Valletta harbour system, preliminary results and open
// questions. Nine slides drawn from the full deck of build_concept_deck.js.
//
// Requires pptxgenjs, installed in a scratch directory as for the full deck:
//     npm install pptxgenjs && node build_concept_deck_short.js out.pptx
//
// The cover is a placeholder. The cover of the full deck carries a photograph
// recoloured in PowerPoint, which pptxgenjs does not reproduce, and it is copied
// over the placeholder by copy_deck_cover.ps1.
const pptx = require("pptxgenjs");
const path = require("path");

const FIG = "C:/Users/Unipa/Documents/MaltaDT/figures";
const OUT = process.argv[2] || "valletta_model_concept_short.pptx";

const MID = "21295C";
const BLUE = "065A82";
const TEAL = "1C7293";
const ORANGE = "EB6834";
const WHITE = "FFFFFF";
const INK = "1A1A1A";
const MUTED = "5F6368";
const TINT = "EEF3F6";
const PALE = "CADCFC";

const HEAD = "Cambria";
const BODY = "Calibri";

const p = new pptx();
p.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
p.author = "Cicero Martins Jr";
p.title = "Valletta harbour system: preliminary results and open questions";

const W = 13.33, H = 7.5, M = 0.62;

function titleSlide(s, kicker, title, sub) {
  s.addText(kicker, { x: M, y: 0.48, w: 9, h: 0.3, fontSize: 12, bold: true,
    color: ORANGE, fontFace: BODY, charSpacing: 2, isTextBox: true, margin: 0 });
  s.addText(title, { x: M, y: 0.82, w: 12.0, h: 0.72, fontSize: 32, bold: true,
    color: INK, fontFace: HEAD, isTextBox: true, margin: 0 });
  if (sub) s.addText(sub, { x: M, y: 1.54, w: 11.9, h: 0.64, fontSize: 14,
    color: MUTED, fontFace: BODY, isTextBox: true, margin: 0 });
}

function badge(s, n, x, y, col) {
  s.addShape(p.ShapeType.ellipse, { x, y, w: 0.44, h: 0.44, fill: { color: col } });
  s.addText(String(n), { x, y, w: 0.44, h: 0.44, fontSize: 15, bold: true,
    color: WHITE, align: "center", valign: "middle", fontFace: BODY, isTextBox: true, margin: 0 });
}

function note(s, txt) {
  s.addText(txt, { x: M, y: H - 0.88, w: W - 2 * M, h: 0.34, fontSize: 10.5,
    color: MUTED, italic: true, fontFace: BODY, isTextBox: true, margin: 0 });
}

function box(s, x, y, w, h, heading, body, dark) {
  s.addShape(p.ShapeType.roundRect, { x, y, w, h,
    fill: { color: dark ? MID : TINT }, rectRadius: 0.06 });
  s.addText(heading, { x: x + 0.3, y: y + 0.18, w: w - 0.6, h: 0.3, fontSize: 13.5,
    bold: true, color: dark ? ORANGE : BLUE, fontFace: HEAD, isTextBox: true, margin: 0 });
  s.addText(body, { x: x + 0.3, y: y + 0.54, w: w - 0.6, h: h - 0.66, fontSize: 11.5,
    color: dark ? PALE : INK, fontFace: BODY, lineSpacing: 15.5, valign: "top",
    isTextBox: true, margin: 0 });
}

function table(s, rows, opts, align) {
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: c, options: {
    bold: i === 0 || j === 0, color: i === 0 ? WHITE : INK,
    fill: { color: i === 0 ? BLUE : (i % 2 ? WHITE : TINT) },
    fontSize: opts.fontSize || 12, fontFace: BODY, valign: "middle",
    align: align ? align(j) : (j ? "right" : "left"),
  } }))), Object.assign({ border: { type: "solid", color: "E2E8EC", pt: 0.5 } }, opts));
}

/* ---------------- 1. cover placeholder ---------------- */
{
  const s = p.addSlide();
  s.background = { color: MID };
  s.addText("The Valletta harbour system", { x: M, y: 1.95, w: 8.6, h: 0.95,
    fontSize: 40, bold: true, color: WHITE, fontFace: HEAD, isTextBox: true, margin: 0 });
  s.addText("Model concept, first results and open questions", { x: M, y: 2.95, w: 8.6,
    h: 0.5, fontSize: 19, color: PALE, fontFace: BODY, isTextBox: true, margin: 0 });
}

/* ---------------- 2. scope and question ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "SCOPE", "The milgħuba and the proposed question",
    "The milgħuba is treated as a meteotsunami, an atmospherically generated long wave comparable to the rissaga of the Balearics and the marrobbio of the Sicilian shelf.");

  const stages = [
    ["Proudman resonance", "Over the Malta Plateau, 99 to 190 m deep, disturbances of 94 to 155 km h⁻¹ would travel at the celerity of the long wave beneath them."],
    ["Shoaling", "Green's law gives a factor of 1.75 to 1.84 from 150 m on the plateau into the harbours."],
    ["Basin resonance", "First-order estimates place the fundamental modes at 14.5 to 18.4 minutes in the Grand Harbour and 10.4 to 12.8 in Marsamxett."],
  ];
  stages.forEach((st, i) => {
    const x = M + i * 4.12;
    s.addShape(p.ShapeType.roundRect, { x, y: 2.62, w: 3.85, h: 1.85,
      fill: { color: TINT }, rectRadius: 0.06 });
    badge(s, i + 1, x + 0.28, 2.4, i === 0 ? ORANGE : BLUE);
    s.addText(st[0], { x: x + 0.28, y: 2.95, w: 3.3, h: 0.36, fontSize: 15.5,
      bold: true, color: INK, fontFace: HEAD, isTextBox: true, margin: 0 });
    s.addText(st[1], { x: x + 0.28, y: 3.36, w: 3.3, h: 1.0, fontSize: 12,
      color: INK, fontFace: BODY, lineSpacing: 16, valign: "top", isTextBox: true, margin: 0 });
  });

  s.addShape(p.ShapeType.roundRect, { x: M, y: 4.72, w: 12.09, h: 1.5,
    fill: { color: MID }, rectRadius: 0.06 });
  s.addText("Proposed question", { x: M + 0.35, y: 4.86, w: 6, h: 0.3, fontSize: 13.5,
    bold: true, color: ORANGE, fontFace: HEAD, isTextBox: true, margin: 0 });
  s.addText("Of the amplification between the open sea and the heads of the Valletta harbours, how is it partitioned between Proudman resonance over the plateau, shoaling on the approach, and resonance of the basins, and which disturbance speeds and directions maximise that chain?",
    { x: M + 0.35, y: 5.2, w: 11.4, h: 0.9, fontSize: 13.5, italic: true, color: WHITE,
      fontFace: HEAD, lineSpacing: 19, valign: "top", isTextBox: true, margin: 0 });

  note(s, "The modelling framework is that of the Stagnone di Marsala digital twin, Delft3D FM and SWAN, and its transfer to a deep engineered harbour is the methodological test of the thesis.");
  s.addNotes("The formulation is a proposal submitted for discussion. Published work on Maltese coastal seiches imposes the long wave at the offshore boundary, so the generation side appears to be open, which is to be confirmed within the group.");
}

/* ---------------- 3. natural periods ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "NATURAL PERIODS", "First-order estimates of the natural periods",
    "Quarter-wave periods for the shelf and the inlets, and eigenmodes of the measured profile for the harbours, against the 0.2 to 2 cph band reported by Drago (2009).");

  const rows = [
    ["Element", "Basis", "Period", "Frequency", ""],
    ["Plateau to Sicily, quarter wave", "90 km, 150 m", "156 min", "0.38 cph", "within"],
    ["Plateau to Sicily, half wave", "90 km, 150 m", "78 min", "0.77 cph", "within"],
    ["Near plateau", "25 km, 120 m", "49 min", "1.24 cph", "within"],
    ["Grand Harbour", "measured profile", "14.5 to 18.4 min", "3.3 to 4.1 cph", "outside"],
    ["Marsamxett", "measured profile", "10.4 to 12.8 min", "4.7 to 5.8 cph", "outside"],
    ["A 1 km inlet", "1.0 km, 12 m", "6 min", "9.76 cph", "outside"],
  ];
  s.addTable(rows.map((r, i) => r.map((c, j) => {
    const head = i === 0;
    const inBand = c === "within";
    return { text: c, options: {
      bold: head || j === 0 || inBand,
      color: head ? WHITE : (inBand ? ORANGE : (c === "outside" ? MUTED : INK)),
      fill: { color: head ? BLUE : (i <= 3 ? "FDF0E9" : WHITE) },
      fontSize: 12, fontFace: BODY, valign: "middle",
      align: j === 0 ? "left" : (j === 4 ? "left" : "right"),
    } };
  })), { x: M, y: 2.5, w: 8.5, colW: [2.85, 1.5, 1.65, 1.55, 0.95], rowH: 0.375,
         border: { type: "solid", color: "E2E8EC", pt: 0.5 } });

  box(s, 9.45, 2.5, 3.26, 2.85,"Reading for the domain", [
    { text: "On these estimates the plateau has natural periods within the band and the harbours above it, which suggests that the harbours respond to a shelf-scale oscillation.", options: { breakLine: true, paraSpaceAfter: 8 } },
    { text: "A domain extending over the plateau, roughly 86 by 66 km, is therefore proposed.", options: { bold: true, color: WHITE } },
  ], true);

  note(s, "Bathymetry at 10 m from CDI 4036_MEPA, co-registered with the national coastline. The harbour estimates are one-dimensional and await confirmation on the mesh.");
  s.addNotes("The harbour rows come from the long-wave eigenproblem of a channel of varying section, solved on the cross-section and surface width measured along the geodesic distance from the mouth. The upper edge of the band corresponds to 30 minutes, 1.6 times the upper estimate for the Grand Harbour. The estimate treats branches as oscillating in phase and borrows its mouth correction from an open rectangular basin, so it is first-order.");
}

/* ---------------- 4. estimated and observed modes ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "BASIN MODES", "Estimated and observed modes of the Grand Harbour",
    "The one-dimensional estimate against the spectrum of the Senglea radar gauge, inside the basin, over the nine months of the public record admitted to the analysis.");

  s.addImage({ path: path.join(FIG, "senglea_spectrum.png"), x: M, y: 2.3, w: 6.3, h: 4.3 });

  table(s, [
    ["Observed period", "Peak ∕ background", "Relation to the estimate"],
    ["23.0 min", "23.8", "longer than estimated"],
    ["16.8 min", "10.1", "within 14.5 to 18.4 min"],
    ["10.0 min", "7.6", ""],
    ["6.9 min", "15.2", "near the inlet estimate"],
  ], { x: 7.2, y: 2.3, w: 5.51, colW: [1.5, 1.66, 2.35], rowH: 0.34, fontSize: 11.5 },
  (j) => (j === 1 ? "right" : "left"));

  box(s, 7.2, 4.14, 5.51, 2.46, "Preliminary reading", [
    { text: "The observed peaks lie above the milgħuba band, in agreement with the estimate.", options: { bullet: true, breakLine: true, paraSpaceAfter: 5 } },
    { text: "The dominant peak, at 23 minutes, is longer than estimated. It may be the fundamental, underestimated by the calculation, or a mode of the approach shared by the two harbours.", options: { bullet: true, breakLine: true, paraSpaceAfter: 5 } },
    { text: "On the supplied coastline, removing the St Elmo breakwater changes the estimate by 0.1 minute.", options: { bullet: true } },
  ], true);

  note(s, "A single gauge does not separate the two readings of the 23-minute peak. The modal structure computed on the mesh, or a second gauge, would.");
  s.addNotes("Panels, from the upper left. The mean spectrum with its background, the milgħuba band shaded grey and the estimated basin band shaded blue. The ratio of the spectrum to the background. The largest oscillation of the admitted windows, 8 November 2021, with a range of 0.35 m. The amplitude ratio against the gauges outside the harbour. The peaks recur on practically every day of both windows, which points to the geometry rather than to the forcing. The section at the entrance is within 6 per cent of the median section of the basin, which suggests that the inertia of the mode is distributed along the harbour. Whether the Ricasoli arm narrows the real opening is unresolved, and a narrower opening would alter that reading.");
}

/* ---------------- 5. mesh and boundary ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "MODEL CONFIGURATION", "Working mesh and open boundary",
    "A domain over the Malta Plateau with quadtree refinement toward the harbour inlets, tested in D-Flow FM 2026.01 at rest and under a forced long wave.");

  s.addImage({ path: path.join(FIG, "mesh_v02.png"), x: M, y: 2.25, w: 7.7, h: 3.08 });

  const stats = [
    ["26,766", "faces, from 1920 m on the plateau\nto 15 m in the harbour channels"],
    ["3.7 s", "time step under a 25-minute wave,\nset by the 15 m cells"],
    ["611 s", "wall time per simulated day,\ntwo-dimensional, serial"],
  ];
  stats.forEach((st, i) => {
    const y = 2.25 + i * 1.05;
    s.addText(st[0], { x: 8.75, y, w: 3.9, h: 0.46, fontSize: 23, bold: true,
      color: i === 1 ? ORANGE : BLUE, fontFace: HEAD, isTextBox: true, margin: 0 });
    s.addText(st[1], { x: 8.75, y: y + 0.46, w: 3.9, h: 0.5, fontSize: 11.5,
      color: MUTED, fontFace: BODY, valign: "top", isTextBox: true, margin: 0 });
  });

  box(s, M, 5.5, 5.95, 1.45, "Open boundary",
    "In an idealised pulse test a Riemann boundary reflected 0.3 to 1.3 per cent at normal incidence and 5 to 9 per cent up to 30°, against 94 to 100 per cent for a prescribed level. A residual current and a CMEMS signal remain to be tested.", false);
  box(s, 6.76, 5.5, 5.95, 1.45, "Indicative cost",
    "Some 16 h for the two-dimensional sweep and of the order of 45 h on 8 processes for the three-dimensional runs, the latter scaled from the Stagnone configuration and uncertain by a factor of two.", true);

  s.addNotes("The left panel shows the face size over the domain and the right panel the two harbours. Sigma layers, 12 to 15, are foreseen for the three-dimensional runs, the count being set by residence time. The pulse test releases a Gaussian hump on a flat bed at 150 m and compares each boundary type with a reference domain without a boundary. Corners reflected 24 to 29 per cent, which is why they are kept more than 40 km from the harbours. Open matters on the mesh are one edge near the orthogonality threshold and the gaps of the 10 m grid at the heads of Msida and Pietà Creeks.");
}

/* ---------------- 6. proposed design ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "PROPOSED DESIGN", "A parametric sweep and its test against observations",
    "ERA5 does not resolve the atmospheric gravity waves associated with the phenomenon, so a hindcast of individual events is not attempted.");

  const steps = [
    ["Sweep", "A moving pressure disturbance is imposed, and its speed, direction, width and duration are varied."],
    ["Response surface", "The output would be a transfer function of the geometry, independent of any particular storm."],
    ["Test against the observations", "Recorded events would then be located on the surface, to examine whether they occur under the conditions identified as resonant."],
  ];
  steps.forEach((st, i) => {
    const y = 2.55 + i * 1.28;
    badge(s, i + 1, M, y, i === 2 ? ORANGE : BLUE);
    s.addText(st[0], { x: M + 0.68, y: y - 0.02, w: 5.0, h: 0.32, fontSize: 14.5,
      bold: true, color: INK, fontFace: HEAD, isTextBox: true, margin: 0 });
    s.addText(st[1], { x: M + 0.68, y: y + 0.32, w: 5.9, h: 0.72, fontSize: 12.5,
      color: MUTED, fontFace: BODY, lineSpacing: 17, valign: "top", isTextBox: true, margin: 0 });
  });

  box(s, 7.6, 2.4, 5.11, 3.35,"Two extensions under consideration", [
    { text: "Climate. ", options: { bold: true, color: WHITE } },
    { text: "The response surface would be a property of the geometry, so projected changes in the forcing could be applied to it without repeating the hydrodynamics.\n", options: { breakLine: true } },
    { text: "Geometry of the mouth. ", options: { bold: true, color: WHITE } },
    { text: "On the measured profile a restriction of a quarter lengthens the estimated mode by 1.5 to 4 per cent, of the same order as a metre of sea level rise. The effect on exchange is expected to be larger. The exercise is a sensitivity on the class of basin and represents no particular design.", options: {} },
  ], true);

  note(s, "The milgħuba is reported to flood Msida, at the head of Msida Creek inside Marsamxett, together with Marsaskala, Xemxija, Marsaxlokk and Sliema.");
  s.addNotes("Six speeds by eight directions by two widths, twelve hours each, barotropic and uncoupled. Whether the sensitivity on the mouth is appropriate, given the public project on the Grand Harbour entrance, is among the open questions. A third line, the renewal of harbour water under long-wave exchange, exercises the three-dimensional and Lagrangian components.");
}

/* ---------------- 7. events and record ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "OBSERVATIONS", "Reported events against the public record",
    "The public copy of the Senglea record covers 43 per cent of the span from June 2021 to December 2024, and transmission ceased on 13 December 2024.");

  table(s, [
    ["Date", "Type", "Reported effects", "Senglea, public copy"],
    ["25 Oct 2018", "seismic tsunami", "excursions of some 25 cm at Portomaso", "before installation"],
    ["18 Jun 2019", "milgħuba", "sea bed exposed and quay overtopped in St Paul's Bay", "before installation"],
    ["30 Jun 2022", "milgħuba", "flooding at Marsaskala, St Julian's and Qawra", "no data, record resumes on 1 July"],
    ["1 Jul 2023", "milgħuba", "flooding at Marsaskala and Xemxija", "displaced level, not usable"],
    ["13 Jun 2024", "meteotsunami", "flooding of the main square of Msida", "displaced level, not usable"],
  ], { x: M, y: 2.4, w: 12.09, colW: [1.5, 1.8, 4.9, 3.89], rowH: 0.38 }, () => "left");

  box(s, M, 4.92, 5.95, 1.62, "State of the record",
    "Two windows are provisionally admitted to the analysis, 24 June to 31 December 2021 and 1 December 2022 to 31 March 2023. From April 2023 the level appears displaced by some 2 m and the gauge transmits by day only.", false);
  box(s, 6.76, 4.92, 5.95, 1.62, "Consequence for the study",
    "None of the three events since installation is resolved in the public copy. The archive of the group, sea level and one-minute pressure, would therefore be the record against which the response surface is tested.", true);

  s.addNotes("Sources. University of Malta Newspoint for 2018 and 2019, Newsbook for 2022, MaltaToday for 2023 and 2024, the last citing the Oceanography Malta Research Group. The choice of windows rests on monthly coverage and stability of the level and is to be confirmed within the group.");
}

/* ---------------- 8. open questions ---------------- */
{
  const s = p.addSlide();
  titleSlide(s, "OPEN QUESTIONS", "Open questions for the continuation", null);

  const qs = [
    ["Sea level and one-minute pressure from the archive of the group on the dates of the events",
     "Senglea and Delimara for 29 June to 2 July 2022, 30 June to 2 July 2023 and 12 to 14 June 2024, with PORTO pressure at Elmo, Kordin and Msida."],
    ["History of the Senglea installation, and Portomaso at one minute",
     "Confirmation of the windows admitted and the cause of the displacement from April 2023. A gauge outside both basins would help separate the readings of the 23-minute peak."],
    ["Appropriateness of the sensitivity exercise on the harbour mouth",
     "The exercise is a response curve over the class of basin and carries no assessment of the project in consultation. The present geometry of the entrance, the Ricasoli arm in particular, bears on the estimate."],
    ["Prior work on the generation of the wave",
     "Published work imposes the long wave at the offshore boundary. Unpublished material may have treated its generation over the shelf, in which case the question would be reformulated."],
    ["Elements of ROSARIO-SHYFEM to be reflected in the configuration",
     "The treatment of the open boundary and the bathymetry inside the harbours, in particular at the heads of Msida and Pietà Creeks, where the 10 m grid has gaps."],
    ["Data for validation",
     "Currents and stratification inside the harbours, waves beyond the BLUE buoy, the levelling datum of the bathymetry against the gauge zeros, and Storm Harry, January 2026, as a possible case."],
  ];
  qs.forEach((q, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.08, y = 2.05 + row * 1.62;
    badge(s, i + 1, x, y, col === 0 ? BLUE : TEAL);
    s.addText(q[0], { x: x + 0.62, y: y - 0.03, w: 5.28, h: 0.52, fontSize: 12.8,
      bold: true, color: INK, fontFace: BODY, lineSpacing: 16, isTextBox: true, margin: 0 });
    s.addText(q[1], { x: x + 0.62, y: y + 0.5, w: 5.28, h: 0.98, fontSize: 11,
      color: MUTED, fontFace: BODY, lineSpacing: 14.5, valign: "top", isTextBox: true, margin: 0 });
  });
  s.addNotes("The first two determine whether the response surface can be tested against events at all. The remainder shape the scope and the configuration.");
}

/* ---------------- 9. sequence ---------------- */
{
  const s = p.addSlide();
  s.background = { color: MID };
  s.addShape(p.ShapeType.ellipse, { x: -1.9, y: 4.2, w: 5.2, h: 5.2,
    fill: { color: BLUE, transparency: 60 } });

  s.addText("SEQUENCE", { x: M, y: 0.7, w: 9, h: 0.3, fontSize: 12,
    bold: true, color: ORANGE, charSpacing: 2, fontFace: BODY, isTextBox: true, margin: 0 });
  s.addText("Planned sequence to the first production runs", { x: M, y: 1.05, w: 11.5, h: 0.7, fontSize: 30,
    bold: true, color: WHITE, fontFace: HEAD, isTextBox: true, margin: 0 });

  const tl = [
    ["To date", "First-order basin modes, pulse test of the boundary, Senglea spectrum, working mesh."],
    ["October", "Bathymetry at the heads of Msida and Pietà Creeks, remaining boundary tests, response of the mesh to a broadband impulse."],
    ["2 to 4 November", "Delft3D User Days at Deltares, with the configuration questions."],
    ["November", "Parametric sweep in two dimensions, first three-dimensional runs."],
  ];
  tl.forEach((t, i) => {
    const y = 2.25 + i * 1.02;
    s.addShape(p.ShapeType.ellipse, { x: M + 0.05, y: y + 0.1, w: 0.17, h: 0.17,
      fill: { color: PALE } });
    s.addText(t[0], { x: M + 0.45, y, w: 2.2, h: 0.33, fontSize: 13, bold: true,
      color: WHITE, fontFace: BODY, valign: "top", isTextBox: true, margin: 0 });
    s.addText(t[1], { x: M + 2.7, y, w: 4.0, h: 0.8, fontSize: 12,
      color: "9FB3D1", fontFace: BODY, lineSpacing: 15, valign: "top", isTextBox: true, margin: 0 });
  });

  s.addShape(p.ShapeType.roundRect, { x: 7.5, y: 2.15, w: 5.21, h: 2.35,
    fill: { color: BLUE, transparency: 30 }, rectRadius: 0.06 });
  s.addText("Beyond the period", { x: 7.8, y: 2.38, w: 4.6, h: 0.3, fontSize: 14,
    bold: true, color: ORANGE, fontFace: HEAD, isTextBox: true, margin: 0 });
  s.addText([
    { text: "The Stagnone twin runs containerised on the EDITO Datalab and publishes to its object storage.", options: { breakLine: true, paraSpaceAfter: 9 } },
    { text: "A Valletta configuration could take the same route, should it prove stable in time, which would correspond to the relocatable setup requested in the design report of the group (Drago, 2018).", options: {} },
  ], { x: 7.8, y: 2.78, w: 4.6, h: 2.2, fontSize: 11.5, color: "DCE7F5",
       fontFace: BODY, lineSpacing: 15.5, valign: "top", isTextBox: true, margin: 0 });

  s.addText("Documents, figures and the reproducible analysis are in the project repository.",
    { x: M, y: 6.78, w: 6.4, h: 0.3, fontSize: 11, italic: true, color: "7F93B3",
      fontFace: BODY, isTextBox: true, margin: 0 });
  s.addNotes("The broadband impulse yields the modal structure of the harbours on the mesh, which bears on the two readings of the 23-minute peak. The remaining boundary tests are the residual current and the non-zero incoming signal from CMEMS.");
}

p.writeFile({ fileName: OUT }).then(() => console.log("written", OUT));
