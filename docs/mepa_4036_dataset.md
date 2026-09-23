# Bathymetric dataset CDI 4036_MEPA: contents, specifications and fitness for purpose

*Received from Prof. Adam Gauci on 22 September 2026 as `4036Mepa.zip` (3.9 MB). Extracted to `data/raw/mepa_4036/`. Assessed 23 September 2026.*

The dataset constitutes the native-resolution source from which the EMODnet Digital Bathymetry is derived in Maltese coastal waters, where it is registered under CDI identifier `4036_MEPA` and attributed to EDMO 708, the Oceanography Malta Research Group of the University of Malta.

---

## 1. Contents

The archive contains two raster datasets in ESRI ArcInfo binary grid format, each accompanied by an `info/` directory and the associated `hdr.adf`, `prj.adf`, `w001001.adf` and `vat.adf` components.

| Grid | Dimensions | Extent (ED50 / UTM 33N) | Value range | Valid cells | Acquisition method |
|---|---|---|---|---|---|
| `lid_sbed` | 3710 x 3397 | E 426754–463854, N 3959860–3993830 | -50 to +150 m | 12.2% | Airborne LiDAR, seabed and terrestrial topography combined |
| `son_sbed` | 4085 x 3727 | E 422872–463722, N 3958364–3995634 | -262 to 0 m | 26.8% | Vessel-mounted sonar, seabed only |

Both grids have a cell size of 10 m, are stored as signed 16-bit integers, and use -32768 to denote absent data. Their combined extent covers Malta, Gozo and Comino.

The two datasets are complementary rather than redundant. The LiDAR survey penetrates shallow water of sufficient clarity and additionally records the land surface, whereas the sonar survey covers navigable and deeper water. Coverage over the Valletta harbours illustrates the complementarity.

| Window | Sonar alone | LiDAR alone | Merged |
|---|---|---|---|
| Grand Harbour | 43.1% | 74.7% | 86.0% |
| Marsamxett | 24.1% | 72.6% | 75.2% |

A merged product is therefore required, with sonar values given precedence where both are present, on the grounds that sonar constitutes a direct measurement of the seabed. Because `lid_sbed` extends to +150 m, the merge also supplies the terrestrial surface required for shoreline and quay representation.

---

## 2. Coordinate reference system

The metadata identifies the projection as `ED_1950_UTM_Zone_33N` on the geographic system `GCS_European_1950`, corresponding to EPSG:23033.

The accompanying `prj.adf` does not encode the datum name. GDAL consequently reports the coordinate system as *"unnamed, Unknown datum based upon the International 1924 ellipsoid (deprecated)"* and attaches no EPSG code. Since the projection parameters of ED50 / UTM 33N and WGS84 / UTM 33N (EPSG:32633) are identical, the two are indistinguishable from the file alone.

The consequence of the substitution was quantified at a point within the Grand Harbour. Interpreting ED50 coordinates as WGS84 displaces the data by 70.7 m in easting and 183.9 m in northing, a total offset of 197 m, equivalent to approximately 20 cells at the native resolution. This exceeds the width of most creeks in both harbours. The resulting field would place bathymetry on the incorrect side of quay structures and would fail to close the shoreline, and no error condition would be raised.

The coordinate reference system must therefore be assigned explicitly as EPSG:23033 on opening, rather than inferred from the file. Reprojection to WGS84 requires a datum transformation and not an affine conversion alone; `pyproj` performs this correctly when both systems are specified by EPSG code.

---

## 3. Resolution relative to the public product

EMODnet publishes the same survey resampled to a grid of 1/16 by 1/16 arc-minute, approximately 115 m. The difference in the number of resolved water cells over the two harbours is given below, together with the representation of creek widths.

| Measure | EMODnet (115 m) | MEPA (10 m) | Ratio |
|---|---|---|---|
| Grand Harbour, water cells | 222 | 38,619 | 174 |
| Marsamxett, water cells | 77 | 19,732 | 256 |
| Creek of 100 m width | 0.9 cells | 10 cells | |
| Creek of 300 m width | 2.6 cells | 30 cells | |

The creeks constitute the resonating elements of the harbour system. At 115 m their modes were absent from any solution that could be constructed, and their absence would not have been signalled by the model. At 10 m they are adequately represented. The principal risk identified in the project plan is accordingly resolved, and the reduced scope that risk had imposed is no longer necessary. Marsamxett can be retained within the modelled domain and the creek-scale modes return to scope.

---

## 4. Processing lineage

The ArcGIS processing history recorded in the respective `metadata.xml` files documents the derivation of both grids.

For `son_sbed`:

```
MosaicToNewRaster  J:\RefDATA\Vessel_Seabed_Pt1_Dec2012\DTM_2m\422_3989.asc; ...
Resample           Sonar_Seabed_All_2m -> Son_Sbed_10m  10  NEAREST
```

For `lid_sbed`:

```
MosaicToNewRaster  J:\RefDATA\LIDAR_Terr_Seabed\Seabed_Topography\DSM_2m\426_3989_seabed_and_topo_2m.asc; ...
Resample           Lidar_Seabed_Topo_2m -> lid_sbed_10m  10  NEAREST
```

Three observations follow. First, both grids derive from mosaics at 2 m resolution and the supplied products are nearest-neighbour resamples of those mosaics. A 2 m dataset therefore exists for both. Second, the sonar campaign is identified as a vessel survey designated Part 1 and dated December 2012, which raises the question of whether a subsequent part exists and whether any resurvey has been undertaken in an actively dredged commercial port over the intervening period. Third, the compilation path `AMicallef_Bathydata` attributes the assembly to Aaron Micallef, which is relevant both for citation and for locating the original survey documentation.

Processing was performed under ArcGIS 10.0 on Windows Server 2008 R2, placing the compilation in the early to middle part of the 2010s.

---

## 5. Limitations

**Residual coverage gaps.** The merged product leaves 14.0% of the Grand Harbour window and 24.8% of the Marsamxett window without data in either grid. A substantial proportion of this lies inland, beyond the coastal strip covered by the LiDAR survey, and is immaterial. A further proportion is not: gaps are visible at the inner extremity of Marsamxett in the vicinity of Msida and Pietà. Prior to mesh construction the gaps must be intersected with an independent coastline so that unmapped water is distinguished from ordinary land, after which the need for and extent of interpolation can be established.

**Resampling method.** Nearest-neighbour resampling from 2 m preserves individual values rather than averaging them, so isolated spikes present in the source mosaics propagate unchanged into the 10 m product. A despiking pass is advisable before the field is used for mesh generation.

**Depth extremes.** The Grand Harbour extraction window reaches 53 m and the full sonar grid reaches 262 m, both attributable to water beyond the harbour entrances. Windows must be clipped to the basins before any summary statistic is computed, since otherwise the resulting values describe the open shelf rather than the harbour.

---

## 6. Outstanding queries for the host group

1. **Vertical datum.** The metadata does not record one. Chart datum, mean sea level and the ED50 ellipsoid are all plausible and the differences between them are material to a study whose principal variable is water level. This is the most consequential remaining unknown about the dataset.
2. **Availability of the 2 m products**, from which both supplied grids were resampled.
3. **Existence of a Part 2** of the December 2012 vessel survey, and of any resurvey undertaken since.
4. **Survey accuracy**, in the horizontal and the vertical, and the depth penetration limit achieved by the LiDAR survey in these waters.
5. **Licensing and attribution**, specifically what may be published and how MEPA, the University of Malta and the compiler should be credited in a manuscript and in a data availability statement.
