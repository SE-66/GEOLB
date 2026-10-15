#!/usr/bin/env python3
"""Generate focused building review inventory for municipal stadium / Abdul Latif El Bissar Road.
Bounding box is preliminary and must be refined using an exact map pin.
These are existing Overture footprints, not confirmed missing buildings.
"""
import json
from pathlib import Path
from shapely.geometry import shape,box
ROOT=Path("data/greater-tripoli")
BBOX=[35.840,34.429,35.864,34.449]
aoi=box(*BBOX);index=json.loads((ROOT/"index.json").read_text());seen=set();features=[]
for t in index["tiles"]:
 if t["type"]!="building" or not box(*t["bbox"]).intersects(aoi):continue
 for f in json.loads(Path(t["path"].removeprefix("./")).read_text()).get("features",[]):
  fid=str(f.get("id") or ""); 
  if not fid or fid in seen:continue
  g=shape(f["geometry"])
  if not g.is_valid or not g.intersects(aoi):continue
  seen.add(fid)
  p=g.representative_point()
  features.append({"type":"Feature","geometry":f["geometry"],"properties":{"id":fid,"review_status":"unverified","source":"Overture","area":"Municipal Stadium / Abdul Latif El Bissar Road","lat":p.y,"lon":p.x}})
out={"type":"FeatureCollection","metadata":{"bbox":BBOX,"classification":"existing footprints requiring local verification","note":"Do not count as missing-building candidates; independent imagery required to detect omissions."},"features":features}
(ROOT/"stadium_review.geojson").write_text(json.dumps(out,separators=(",",":")))
print("Stadium-area existing footprints for review:",len(features))
