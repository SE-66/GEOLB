# GeoLB — Tripoli Address Intelligence

Open-source geospatial address discovery and **provisional** addressing prototype for Tripoli, Lebanon.

## Live features
- Leaflet geographic explorer with selectable CARTO/OSM basemap styles.
- Queries roads/building footprints from public Overpass for a **small selected viewport** (no key; public endpoint availability is not guaranteed).
- Named-road and numbered-building **feature counts**. Road segments are not unique streets.
- Provisional OSM-way-based road references and building IDs, editable address records and duplicate/conflict alerts. Algorithmic building numbers are **not official and may change by viewport**.
- Local browser storage of edits and CSV/GeoJSON export.
- **New:** import clipped Overture or Geofabrik GeoJSON, visualize overlay and compare visible raw feature counts. Cross-source deduplication is not yet implemented.
- No Google Maps or commercial map key required.

## Use open data
- OpenStreetMap Lebanon via [Geofabrik](https://download.geofabrik.de/asia/lebanon.html). Geofabrik provides PBF, GeoPackage and other extracts. OpenStreetMap data follows ODbL requirements.
- [Overture Maps](https://docs.overturemaps.org/getting-data/) offers free building, transportation and places data; theme-specific licenses/provenance must be checked.
- [Copernicus Data Space](https://dataspace.copernicus.eu/) for satellite imagery (too coarse for precise individual entrances with Sentinel-2).
- [Protomaps/PMTiles](https://github.com/protomaps/PMTiles) enables keyless vector tile archives in static object storage. GeoLB does **not** yet ship self-hosted PMTiles. Its current basemap styles still request third-party public tiles.

### Download Overture pilot GeoJSON

```bash
python -m pip install overturemaps
python scripts/fetch_tripoli.py
```

The script requests building, transportation segment and place datasets for a rectangular central Tripoli pilot bbox. In GeoLB, use **Import & compare datasets** to load an exported .geojson file. Large downloads should be clipped before importing. The data is **not committed to GitHub**; check dataset licenses and provenance.

## Cloudflare Pages
This is a static HTML app. Connect `SE-66/GEOLB`, branch `main`, no framework, build command `exit 0`, output directory `/`. Cloudflare Pages will publish updates on push.

## Limitations and governance
- No claim that a provisional reference constitutes an authorized Lebanese address.
- AI building detection, automated name reconciliation, official municipal confirmation, authoritative building numbering, and shared persistent database are **not implemented yet**.
- A nearest-road match may not reflect real entrances or road-side access. Validate in the field.
- Public Overpass servers and third-party tile servers have usage limits. Production should ingest source data and self-host tiles, with caching and attribution.
- Geographical coverage and named/addressed percentages reflect only mapped and loaded features, not ground truth.
