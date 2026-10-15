# GeoLB data infrastructure

## Included components

- `studio.html`: MapLibre GL JS vector renderer and PMTiles browser protocol with geographic overlays.
- `scripts/refresh_data.py`: reproducible Overture CLI + Geofabrik OSM/PBF ingestion, clipping and GeoJSON conversion into `data/tripoli/`.
- `.github/workflows/refresh-data.yml`: GitHub Actions manual run; downloads pilot datasets and commits the results to `main` if within GitHub repository limits.
- `index.html`: existing Leaflet map and provisional GeoLB address generator; now links to Vector Studio.

## Start the data refresh

GitHub → SE-66/GEOLB → Actions → Refresh Tripoli open geodata → Run workflow.

The workflow imports a rectangular pilot: W 35.837 / S 34.428 / E 35.865 / N 34.448. It is **not** the full Tripoli municipality. It downloads Overture building, segment and place data and the Lebanon Geofabrik PBF, then extracts roads and buildings in the pilot.

Cloudflare Pages needs GitHub branch auto-deploy enabled to publish the committed GeoJSON files. View the Vector Studio, then click **Load available datasets**. The downloader needs outbound network access from GitHub Actions. Check Actions logs for errors: a committed manifest can contain errors, so never interpret missing data as zero buildings.

## PMTiles

GeoLB includes the PMTiles protocol reader, not an already-built archive. To create a self-hosted vector archive, install `tippecanoe` and the `pmtiles` CLI (Protomaps), then generate a small map archive from normalized GeoJSON:

```bash
tippecanoe -o tripoli.mbtiles -Z12 -z16 -l buildings data/tripoli/overture_building.geojson
pmtiles convert tripoli.mbtiles tripoli.pmtiles
```

Upload the resulting archive to Cloudflare R2 (recommended for larger files) or publish under `data/tripoli.pmtiles` if small enough for static hosting. Enable cross-origin access if using R2 on another host. In Vector Studio enter the archive URL and **buildings** as source-layer. PMTiles vector tiles are not the basemap by default; self-hosting a complete roads/labels/land-use basemap requires a separate appropriate tile archive and style.

## Restrictions

No Google Maps API key needed. OSM datasets follow ODbL; other sources have their own licenses and attribution requirements. Public CARTO/OSM basemap tiles, CDN scripts, and live Overpass are still third-party services. Avoid claiming the current deployment is fully offline or entirely self-hosted.

GeoLB's phase-2 building numbering is provisional, viewport-sensitive, and not official. Overture vs OSM records have not been deduplicated, and quality requires local validation.
