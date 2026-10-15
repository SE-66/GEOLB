# GeoLB — Independent building verification

**Status: NOT independently verified.** Existing OSM/Overture overlap is cross-source corroboration, not survey accuracy.

## Reference data requirements

For an accuracy claim, obtain dated, legally reusable, orthorectified imagery at <=0.5–1 m ground sampling distance or independently surveyed vector footprints. Digitize a ground-truth reference GeoJSON (EPSG:4326) with building polygon annotations across all nine Greater Tripoli tiles. Do not copy or scrape Google Maps imagery or geometry. Record imagery provider, original acquisition date, licensing terms and reviewer. Confirm imagery allows creation and publication of derivative building geometries. Sentinel-2 10 m pixels are not suitable for individual-building ground truth.

## Run

```bash
pip install "shapely>=2.0" pyproj
python scripts/independent_accuracy.py --reference reference_buildings.geojson --source "Your licensed orthophoto or field survey" --acquired 2026-01-01 --license "Actual licensed terms and provenance" --reviewer "Reviewer ID"
```

The command refuses to produce an accuracy report without a real reference. The generated `data/greater-tripoli/independent_accuracy.json` contains measured IoU, centroid error and reference recall; `candidate_missing_buildings.geojson` contains reference footprints with no suitable GeoLB match. Both are candidate measures, not field-confirmed conclusions.

## Quality limitations

* Report separately by tile and neighborhood before asserting regional completeness.
* The reference must be systematically sampled or geographically exhaustive. Otherwise, reference recall applies only to the labeled sample.
* Building edges may represent roofs rather than ground-level wall outlines. Off-nadir imagery, occlusion and shadows cause apparent displacements.
* Overture uses Microsoft ML footprint sources in some Tripoli records; comparing two copies of the same source is not independent.
* Imagery itself must be georeferenced against surveyed control points before interpreting small centroid offsets.
* A single IoU threshold can reject split/merged buildings. Have a human adjudicate those and candidate missing buildings.
* Current GeoLB dataset status remains **unverified for positional accuracy and building completeness**.

## Candidate verification statuses

`corroborated_by_osm`: polygon similarity only.
`independently_measured`: compared against dated, licensed ground truth.
`field_confirmed`: verified independently onsite.
`disputed`: conflicting source or uncertain geometry.
`unverified`: no adequate reference.
