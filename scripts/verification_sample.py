#!/usr/bin/env python3
"""Create deterministic, stratified geographic review samples. NOT a ground-truth certification."""
import json,random,math
from pathlib import Path
from shapely.geometry import shape
ROOT=Path("data/greater-tripoli")
index=json.loads((ROOT/"index.json").read_text())
rng=random.Random(20261015)
items=[];seen=set();issues=[]
for t in index["tiles"]:
 if t["type"]!="building" or t["status"]!="ok":continue
 features=json.loads(Path(t["path"].removeprefix("./")).read_text())["features"]
 candidates=[]
 for f in features:
  fid=str(f.get("id") or (f.get("properties") or {}).get("id") or "")
  if not fid or fid in seen:continue
  seen.add(fid)
  try:
   g=shape(f["geometry"]);c=g.representative_point()
   if g.area<=0:continue
   area_m2=g.area*111320**2*math.cos(math.radians(c.y))
   priority=("review_large" if area_m2>1200 else "review_tiny" if area_m2<12 else "sample")
   candidates.append({"id":fid,"tile":t["tile"],"lat":round(c.y,7),"lon":round(c.x,7),"area_m2_approx":round(area_m2,1),"priority":priority,"verification":"unverified","geometry":f["geometry"]})
  except Exception as e:issues.append(str(e))
 rng.shuffle(candidates)
 # 30 per tile, prioritize unusual footprints.
 selected=[c for c in candidates if c["priority"]!="sample"][:10]
 selected+= [c for c in candidates if c["priority"]=="sample"][:max(0,30-len(selected))]
 items.extend(selected)
report={"method":"reproducible stratified sampling, 30 or fewer footprints per tile; oversample extreme areas","scope":"Greater Tripoli approximate rectangular pilot, not a municipal boundary","sample_size":len(items),"tiles":len(set(i["tile"] for i in items)),"ground_truth_verified":0,"issues":issues[:20],"fields_to_review":["building_exists","outline_alignment","building_missing_nearby","imagery_source","imagery_date","reviewer","evidence","notes"],"features":items}
(ROOT/"verification_sample.json").write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
print("Sample",len(items),"tiles",report["tiles"],"errors",len(issues))
