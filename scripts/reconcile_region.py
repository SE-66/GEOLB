#!/usr/bin/env python3
"""Reconcile Overture and OSM building polygons for the GeoLB Greater Tripoli pilot.
Only overlaps with IoU >= .80 are merged automatically. Ambiguous overlaps remain distinct.
Outputs per-tile unique OSM buildings + classification overlays and a summary.
"""
import json, subprocess, tempfile, urllib.request, collections, math
from pathlib import Path
from shapely.geometry import shape, mapping, box
from shapely.strtree import STRtree

ROOT=Path("data/greater-tripoli")
BBOX=(35.80,34.40,35.90,34.48)
FC=lambda features:{"type":"FeatureCollection","features":features}
def write(path,features):path.write_text(json.dumps(FC(features),ensure_ascii=False,separators=(',',':')))
def osm_features(directory):
    pbf=directory/"lebanon.osm.pbf"; clip=directory/"region.osm.pbf";seq=directory/"region.geojsonseq"
    urllib.request.urlretrieve("https://download.geofabrik.de/asia/lebanon-latest.osm.pbf",pbf)
    subprocess.run(["osmium","extract","--overwrite","-b",','.join(map(str,BBOX)),"-o",str(clip),str(pbf)],check=True)
    subprocess.run(["osmium","export","--overwrite","-f","geojsonseq","-o",str(seq),str(clip)],check=True)
    with seq.open(encoding="utf-8") as stream:
        for raw in stream:
            try:f=json.loads(raw.lstrip("\x1e").strip())
            except (ValueError,TypeError):continue
            props=f.get("properties") or {}
            tags=props.get("tags") if isinstance(props.get("tags"),dict) else props
            if tags.get("building") in (None,"no",False):continue
            if (f.get("geometry") or {}).get("type") not in ("Polygon","MultiPolygon"):continue
            yield f

def main():
    index=json.loads((ROOT/"index.json").read_text())
    tiles=[t for t in index["tiles"] if t["type"]=="building" and t["status"]=="ok"]
    overture={}
    tile_bounds={t["tile"]:box(*t["bbox"]) for t in tiles}
    for t in tiles:
        data=json.loads(Path(t["path"].replace("./","")).read_text())
        for f in data["features"]:
            try:
                geom=shape(f["geometry"])
                if geom.is_empty or not geom.is_valid or geom.area<=0:continue
                uid=str(f.get("id") or f.get("properties",{}).get("id") or "")
                if not uid:uid=geom.wkb_hex[:72]
                overture.setdefault(uid,(f,geom))
            except Exception:continue
    overture_items=list(overture.values())
    ov_geoms=[g for _,g in overture_items]
    tree=STRtree(ov_geoms)
    categorized=collections.defaultdict(list)
    counts=collections.Counter()
    osm_seen=set()
    overture_best=[0.0]*len(overture_items)
    overture_best=[0.0]*len(overture_items)
    osm_results=[]
    with tempfile.TemporaryDirectory() as td:
        for f in osm_features(Path(td)):
            try:
                g=shape(f["geometry"])
                if not g.is_valid or g.is_empty or g.area<=0:continue
                props=f.get("properties") or {}
                sid=str(f.get("id") or props.get("@id") or props.get("id") or "")
                if not sid:sid=g.wkb_hex[:72]
                if sid in osm_seen:continue
                osm_seen.add(sid)
                best=(-1,-1.0)
                for k in tree.query(g):
                    k=int(k); other=ov_geoms[k]
                    if not g.intersects(other):continue
                    union=g.union(other).area
                    iou=(g.intersection(other).area/union) if union else 0
                    if iou>best[1]:best=(k,iou)
                    if iou>overture_best[k]:overture_best[k]=iou
                    if iou>overture_best[k]:overture_best[k]=iou
                osm_results.append({"id":sid,"best_iou":round(max(best[1],0),4),"matched_overture_id":str(overture_items[best[0]][0].get("id","")) if best[0]>=0 else None})
                if best[1]>=.80:
                    counts["matched"]+=1
                    continue
                state="possible_match" if best[1]>=.20 else "osm_only"
                properties={"source":"OpenStreetMap","reconciliation":state,"source_id":sid,"best_iou":round(max(best[1],0),3),"building":True,"name":props.get("name","")}
                obj={"type":"Feature","geometry":f["geometry"],"properties":properties}
                for tile,extent in tile_bounds.items():
                    if extent.intersects(g):categorized[tile].append(obj)
                counts[state]+=1
            except Exception:counts["processing_errors"]+=1
    for tile in tile_bounds:write(ROOT/f"{tile}_osm_reconciled.geojson",categorized[tile])
    counts["overture_unique"]=len(overture)
    counts["osm_unique"]=len(osm_seen)
    counts["retained_osm_only"]=counts["osm_only"]
    counts["ambiguous_not_merged"]=counts["possible_match"]
    corroborated=sum(v>=.8 for v in overture_best)
    uncertain=sum(.2<=v<.8 for v in overture_best)
    uncorroborated=sum(v<.2 for v in overture_best)
    assessments=[{"id":str(item[0].get("id","")),"best_osm_iou":round(overture_best[i],4),"cross_source_status":"corroborated" if overture_best[i]>=.8 else "ambiguous" if overture_best[i]>=.2 else "unmatched"} for i,item in enumerate(overture_items)]
    (ROOT/"building_evidence.json").write_text(json.dumps({"method":"spatial polygon overlap with independent OSM footprints","threshold":.8,"warning":"Corroborated means similar OSM geometry, not ground-truth verified.","counts":{"corroborated":corroborated,"ambiguous":uncertain,"unmatched":uncorroborated},"buildings":assessments},separators=(",",":")))
    corroborated=sum(v>=.8 for v in overture_best)
    uncertain=sum(.2<=v<.8 for v in overture_best)
    uncorroborated=sum(v<.2 for v in overture_best)
    assessments=[{"id":str(item[0].get("id","")),"best_osm_iou":round(overture_best[i],4),"cross_source_status":"corroborated" if overture_best[i]>=.8 else "ambiguous" if overture_best[i]>=.2 else "unmatched"} for i,item in enumerate(overture_items)]
    (ROOT/"building_evidence.json").write_text(json.dumps({"method":"spatial polygon overlap with independent OSM footprints","threshold":.8,"warning":"Corroborated means similar OSM geometry, not ground-truth verified.","counts":{"corroborated":corroborated,"ambiguous":uncertain,"unmatched":uncorroborated},"buildings":assessments},separators=(",",":")))
    result={"method":"polygon IoU","auto_match_threshold":.8,"possible_match_threshold":.2,"limitations":"Polygon agreement is not proof of the same real-world building. Source-only means missing from the other dataset, not necessarily missing physically. OSM-only and ambiguous polygons remain separately visible.","counts":dict(counts),"files":[f"./data/greater-tripoli/{tile}_osm_reconciled.geojson" for tile in tile_bounds]}
    (ROOT/"reconciliation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
