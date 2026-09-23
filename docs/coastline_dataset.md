# Maltese coastline: contents, coordinate reference system and relation to the bathymetry

*Received from Prof. Adam Gauci on 23 September 2026 as `MaltaCoastline.zip` (692 kB). Extracted to `data/raw/coastline/`. Assessed the same day.*

---

## 1. Contents

An ESRI shapefile comprising **26 polygons** covering the Maltese Islands, with a single attribute `Id` carrying no further information.

| Property | Value |
|---|---|
| Geometry | Polygon |
| Features | 26 |
| Total area | 315.4 km² |
| Extent (UTM 33N) | E 426464–461761, N 3962563–3993351 |
| Declared CRS | `WGS_1984_UTM_Zone_33N`, EPSG:32633 |

The total area corresponds closely to the 316 km² of the Maltese Islands, confirming that the polygons represent the complete land area rather than a subset.

---

## 2. Coordinate reference system

The shapefile declares WGS84 / UTM Zone 33N. Since the bathymetric dataset [4036_MEPA](mepa_4036_dataset.md) originates from the same compiler and declares its datum incorrectly, the declaration was not accepted without verification.

The two interpretations were tested by rasterising the coastline polygons onto the merged bathymetry grid and comparing the resulting land mask against the sign of the elevation field.

| Interpretation | Land and water agreement | Water cells within the land polygon | Land cells outside |
|---|---|---|---|
| **WGS84 / UTM 33N (EPSG:32633), as declared** | **99.26%** | 16,358 | 19,465 |
| ED50 / UTM 33N (EPSG:23033), as the bathymetry | 94.54% | 135,014 | 129,519 |

The declaration is therefore correct. The coastline is in WGS84 / UTM 33N.

**The two datasets consequently occupy different datums.** The coastline is WGS84 and the bathymetry is ED50, and at Malta the difference amounts to approximately 197 m. Neither may be overlaid on the other without an explicit datum transformation. This is the same hazard documented for the bathymetry, now arising between two datasets rather than within one, and it is the more dangerous form because both files declare a coordinate system and neither declaration is wrong.

The residual 0.74% disagreement is consistent with the discretisation of a vector boundary onto a 10 m raster, together with genuine differences in epoch between a coastline compiled in 2010 and a bathymetric survey of December 2012.

---

## 3. Provenance

The FGDC metadata accompanying the shapefile is an unfilled template. The abstract, purpose, originator, publication date, access constraints and use constraints all retain their placeholder text. No attribution or licensing statement is available from the file.

The processing history is nonetheless recorded and is informative.

```
Select             "ContoursMalta Line"
                   C:\...\Micallef\...\Coastline\coastline.shp
FeatureToPolygon   coastline -> coastline_polygon.shp
```

Created 27 May 2010 under ArcCatalog 9.2, modified 25 May 2017. The compilation path identifies Aaron Micallef, the same source as the bathymetric compilation.

**The coastline is therefore the zero contour of a terrestrial contour dataset**, selected from a layer named `ContoursMalta` and converted to polygon. It is not a tidally defined shoreline such as mean high water, and it carries no independent survey of its own. This bears directly on the vertical datum question addressed below.

---

## 4. Consistency with the bathymetry, and the vertical datum

The two datasets were supplied independently and share a vertical reference, which permits the vertical datum of the bathymetry to be established by inference.

The elevation of the merged bathymetric product was sampled at 12,604 points spaced approximately 25 m along the coastline boundary, of which 11,884 fell within the data extent.

| Statistic | Value |
|---|---|
| Median | **+0.00 m** |
| Mean | -1.39 m |
| 25th and 75th percentiles | -5.00 and +2.00 m |
| Proportion within 2 m of zero | 29.0% |
| Proportion within 5 m of zero | 59.2% |

The median is exactly zero. The dispersion is expected and does not weaken the result, since a 10 m cell spanning a coastal cliff takes a value from either the clifftop or its foot, and the Maltese coast is substantially cliffed.

**The bathymetry and the coastline therefore share the same vertical zero.** Since the coastline is the zero contour of a national terrestrial contour dataset, which would be referenced to a levelling datum rather than to an ellipsoid, the zero of the bathymetry is that same surface. The implications for the declared vertical coordinate system are set out in Section 3 of [mepa_4036_dataset.md](mepa_4036_dataset.md).

---

## 5. Use in the present work

The coastline serves three purposes.

**Distinguishing unmapped water from land within the bathymetry gaps.** The merged bathymetric product leaves 14.0% of the Grand Harbour window and 24.8% of the Marsamxett window without data. Intersection with the coastline separates the portion lying inland, which is immaterial, from the portion lying in water, which requires interpolation. This was identified as a prerequisite to mesh construction and is now possible.

**Supplying the planform for mesh generation.** The mesh boundary follows the coastline rather than the zero contour of the interpolated depth field, which would inherit the 10 m discretisation.

**Independent verification of the bathymetry.** The 99.26% agreement between two datasets supplied separately constitutes a check on both.

**Before any of these**, the coastline must be reprojected from EPSG:32633 to the working coordinate system. It is not in the same datum as the bathymetry.

---

## 6. Outstanding queries

1. **What is the source contour dataset**, `ContoursMalta`, and what is its contour interval and levelling datum? This determines the vertical datum of the bathymetry by the argument in Section 4 and is the more precise form of the question previously recorded.
2. **Licensing and attribution.** The metadata template is unfilled and the file carries no statement of either.
3. **Epoch.** The coastline was compiled in 2010 and modified in 2017. Whether the 2017 modification altered geometry or metadata alone is not recorded, and the harbours have been subject to construction over the interval.
