#!/usr/bin/env python3
"""GeoLB geographic integrity audit. Non-destructive: never edits source features.
Hard failures are malformed data, invalid coordinates/geometry, incomplete tiles or
incorrect manifest counts. Coverage and positional accuracy require separate review.
"""
import json, collections, math, sys
from pathlib import Path
from shapely.geometry import shape, box
ROOT=Path("data/greater-tripoli")
EXPECTED=(35.80,34.40,35.90,34.48)
def main():
 index=json.loads((ROOT/"index.json").read_text())
 issues=[];warnings=[];counts=collections.Counter();unique=collections.defaultdict(set);duplicates=collections.Counter()
 expected_cells={(f"r{r}c{c}",k) for r in range(3) for c in range(3) for k in ("building","segment","place")}
 found={(t["tile"],t["type"]) for t in index["tiles"]}
 if found!=expected_cells:issues.append(f"Expected 27 tile/type records; missing={sorted(expected_cells-found)} unexpected={sorted(found-expected_cells)}")
 if tuple(index.get("bbox",[]))!=EXPECTED:issues.append("Unexpected regional bounding box")
 for t in index["tiles"]:
  name=f'{t["tile"]}_{t["type"]}'
  if t.get("status")!="ok":issues.append(f"{name}: extraction not successful");continue
  path=Path(t["path"].removeprefix("./"))
  if not path.exists():issues.append(f"{name}: missing file");continue
  try:payload=json.loads(path.read_text())
  except Exception as exc:issues.append(f"{name}: cannot parse GeoJSON {exc}");continue
  if payload.get("type")!="FeatureCollection" or not isinstance(payload.get("features"),list):issues.append(f"{name}: invalid FeatureCollection");continue
  features=payload["features"];counts[t["type"]]+=len(features)
  if len(features)!=t.get("count"):issues.append(f"{name}: manifest count {t.get('count')} != file {len(features)}")
  bounds=box(*t["bbox"])
  for i,f in enumerate(features):
   geom=f.get("geometry")
   if not isinstance(geom,dict):issues.append(f"{name}:{i} missing geometry");continue
   try:g=shape(geom)
   except Exception as exc:issues.append(f"{name}:{i} geometry error {exc}");continue
   if g.is_empty or not g.is_valid:issues.append(f"{name}:{i} invalid/empty geometry");continue
   minx,miny,maxx,maxy=g.bounds
   if not all(map(math.isfinite,g.bounds)) or minx < 35 or maxx > 37 or miny < 33 or maxy > 35:issues.append(f"{name}:{i} coordinates outside Lebanon")
   if not bounds.intersects(g):issues.append(f"{name}:{i} outside designated tile")
   if t["type"]=="building" and (g.geom_type not in ("Polygon","MultiPolygon") or g.area<=0):issues.append(f"{name}:{i} invalid building geometry type or area")
   if t["type"]=="segment" and "LineString" not in g.geom_type:issues.append(f"{name}:{i} non-line segment")
   if t["type"]=="place" and g.geom_type!="Point":warnings.append(f"{name}:{i} nonpoint POI")
   fid=str(f.get("id") or (f.get("properties") or {}).get("id") or "")
   if not fid:warnings.append(f"{name}:{i} missing stable feature ID")
   elif fid in unique[t["type"]]:duplicates[t["type"]]+=1
   else:unique[t["type"]].add(fid)
 summary={"region_bbox":EXPECTED,"result":"FAIL" if issues else "PASS","scope":"geometry/topology and manifest integrity only; not field verified","record_counts":dict(counts),"unique_id_counts":{k:len(v) for k,v in unique.items()},"cross_tile_duplicate_records":dict(duplicates),"hard_issue_count":len(issues),"warnings_count":len(warnings),"issues":issues[:200],"warnings":warnings[:50],"limitations":["Dataset coverage is not evidence that every physical building is mapped.","Coordinates and geometry validity do not demonstrate positional accuracy.","OSM and Overture footprints can differ in acquisition time and generalization."]}
 (ROOT/"validation.json").write_text(json.dumps(summary,indent=2))
 print(json.dumps({k:v for k,v in summary.items() if k not in ("issues","warnings")},indent=2))
 if issues:sys.exit(1)
if __name__=="__main__":main()
