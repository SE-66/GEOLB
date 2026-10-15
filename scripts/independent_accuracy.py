#!/usr/bin/env python3
"""Independent ground-truth comparator for Greater Tripoli building footprints.

Reference GeoJSON must be independently surveyed/digitized from imagery with
documented license and acquisition date. Never treat OSM/Overture as ground truth.
Outputs only when supplied with real licensed reference polygons.
"""
import argparse, json, math, statistics
from pathlib import Path
from shapely.geometry import shape, mapping, box
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer

AOI=box(35.80,34.40,35.90,34.48)
ROOT=Path("data/greater-tripoli")
TO_METERS=Transformer.from_crs("EPSG:4326","EPSG:32636",always_xy=True).transform

def load(path):
    data=json.loads(Path(path).read_text())
    if data.get("type")!="FeatureCollection":raise ValueError(f"{path}: expected FeatureCollection")
    records=[]
    for f in data["features"]:
        try:
            g=shape(f["geometry"])
            if g.is_valid and not g.is_empty and g.intersects(AOI) and g.geom_type in ("Polygon","MultiPolygon"):
                records.append((f,g,transform(TO_METERS,g)))
        except (ValueError,KeyError,TypeError):continue
    return records

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",required=True,help="Independent ground-truth building polygon GeoJSON (EPSG:4326)")
    p.add_argument("--source",required=True,help="Source/provider or survey name")
    p.add_argument("--acquired",required=True,help="Acquisition date YYYY-MM-DD")
    p.add_argument("--license",required=True,help="Licensed reuse terms / evidence URL")
    p.add_argument("--reviewer",required=True)
    p.add_argument("--min-iou",type=float,default=.5)
    p.add_argument("--max-centroid-m",type=float,default=10)
    p.add_argument("--output",default=str(ROOT/"independent_accuracy.json"))
    a=p.parse_args()
    if not (0<a.min_iou<=1 and a.max_centroid_m>0):p.error("Invalid thresholds")
    if not a.source.strip() or not a.license.strip() or not a.reviewer.strip():p.error("Provenance is mandatory")
    import datetime
    datetime.date.fromisoformat(a.acquired)
    refs=load(a.reference)
    if not refs:raise SystemExit("No usable reference buildings. No accuracy assertion generated.")
    index=json.loads((ROOT/"index.json").read_text())
    seen=set();mapped=[]
    for tile in index["tiles"]:
        if tile["type"]!="building" or tile["status"]!="ok":continue
        for f,g,metric in load(tile["path"].removeprefix("./")):
            fid=str(f.get("id") or (f.get("properties") or {}).get("id") or "")
            if fid and fid not in seen:seen.add(fid);mapped.append((fid,g,metric))
    if not mapped:raise SystemExit("No mapped buildings")
    indexed=[entry[2] for entry in mapped]
    tree=STRtree(indexed)
    candidates=[]
    for ri,(_,original,reference) in enumerate(refs):
        for mi in tree.query(reference.buffer(a.max_centroid_m)):
            mi=int(mi); target=indexed[mi]
            if not reference.intersects(target):continue
            union=reference.union(target).area
            overlap=reference.intersection(target).area/union if union else 0
            displacement=reference.centroid.distance(target.centroid)
            if overlap>=a.min_iou and displacement<=a.max_centroid_m:
                candidates.append((overlap,-displacement,ri,mi,displacement))
    # Greedy 1:1 matches, highest IoU first: no one-to-many duplication.
    candidates.sort(reverse=True)
    used_ref=set();used_map=set();matches=[]
    for overlap,_,ri,mi,dist in candidates:
        if ri in used_ref or mi in used_map:continue
        used_ref.add(ri);used_map.add(mi)
        matches.append({"reference_index":ri,"mapped_id":mapped[mi][0],"iou":round(overlap,4),"centroid_error_m":round(dist,2)})
    missed=[{"reference_index":i,"geometry":mapping(refs[i][1]),"properties":{"status":"candidate_missing_in_geolb","reference_source":a.source}} for i in range(len(refs)) if i not in used_ref]
    unmatched=[mapped[i][0] for i in range(len(mapped)) if i not in used_map]
    errors=[m["centroid_error_m"] for m in matches]
    result={"status":"measured_against_independent_reference","reference":{"source":a.source,"date":a.acquired,"license":a.license,"reviewer":a.reviewer,"path":a.reference},
       "method":{"match":"one-to-one greedy highest polygon IoU","min_iou":a.min_iou,"max_centroid_error_m":a.max_centroid_m},
       "counts":{"reference_buildings":len(refs),"geolb_buildings_in_regional_dataset":len(mapped),"matched_reference_buildings":len(matches),"unmatched_reference_candidates":len(missed),"unmatched_geolb_ids_whole_region":len(unmatched)},
       "metrics":{"reference_recall":round(len(matches)/len(refs),4),"median_centroid_error_m":round(statistics.median(errors),2) if errors else None,"p95_centroid_error_m":round(sorted(errors)[min(len(errors)-1,math.ceil(.95*len(errors))-1)],2) if errors else None,"mean_iou":round(statistics.mean(m["iou"] for m in matches),4) if matches else None},
       "warning":"Reference may cover only part of region. Whole-region unmatched GeoLB IDs are NOT false positives. Candidates require human confirmation.","matches":matches}
    Path(a.output).write_text(json.dumps(result,indent=2))
    Path(a.output).with_name("candidate_missing_buildings.geojson").write_text(json.dumps({"type":"FeatureCollection","features":[{"type":"Feature","properties":f["properties"],"geometry":f["geometry"]} for f in missed]}))
    print(json.dumps({k:v for k,v in result.items() if k!="matches"},indent=2))
if __name__=="__main__":main()
