#!/usr/bin/env python3
"""Evaluate external AUB Tripoli building layer against GeoLB without redistributing its geometry.
The AUB service has no explicit reuse license in its metadata; outputs aggregate metrics only.
"""
import json, urllib.parse, urllib.request, math, collections, datetime
from pathlib import Path
from shapely.geometry import shape, box
from shapely.strtree import STRtree
ROOT=Path("data/greater-tripoli")
URL="https://icilgis.aub.edu.lb/server/rest/services/Hosted/tripoliFair_Layers_GDB/FeatureServer/3/query"
def get(params):
    u=URL+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers={"User-Agent":"GeoLB coverage research contact via github.com/SE-66/GEOLB"})
    with urllib.request.urlopen(req,timeout=75) as r:return json.load(r)
def main():
    metadata={"source":"AUB ICILGIS tripoliFair_Layers_GDB BuildingsPoly layer","source_url":URL.rsplit('/query',1)[0],"license":"Not declared on accessible service metadata; analysis only, no geometry republished","coverage":"Tripoli Fair site, not regional coverage"}
    try:
        layer=get({"f":"json"}) if False else None
        with urllib.request.urlopen(urllib.request.Request(URL.rsplit("/query",1)[0]+"?f=json",headers={"User-Agent":"GeoLB source-provenance audit"}),timeout=45) as response: layer=json.load(response)
        total=get({"where":"1=1","returnCountOnly":"true","f":"json"}).get("count",0)
        if total>10000:raise ValueError("Unexpected count; abort large request")
        features=[]
        for offset in range(0,total,1000):
            x=get({"where":"1=1","outFields":"*","returnGeometry":"true","outSR":"4326","f":"geojson","resultOffset":offset,"resultRecordCount":1000})
            if x.get("type")!="FeatureCollection":raise ValueError("ArcGIS did not return GeoJSON")
            features.extend(x.get("features",[]))
        fields=[{"name":f.get("name"),"type":f.get("type")} for f in layer.get("fields",[])]
        temporal_fields=[f["name"] for f in fields if any(term in f["name"].lower() for term in ("date","year","source","credit","image","created","edited"))]
        attribution=layer.get("copyrightText") or ""
        date_values={}
        for key in temporal_fields:
            vals=[str(f.get("properties",{}).get(key)) for f in features if f.get("properties",{}).get(key) not in (None,"")]
            if vals:date_values[key]={"count_present":len(vals),"examples":list(dict.fromkeys(vals))[:5]}
        provenance={"copyrightText":attribution,"description":str(layer.get("description") or "")[:600],"date_source_fields":temporal_fields,"field_values_summary":date_values,"reuse_approved":False,"date_verified":False,"reason":"No explicit grant of reuse in public metadata; feature dates may describe historic structures, not imagery acquisition."}
        reference=[]
        for f in features:
            try:
                g=shape(f["geometry"])
                if g.is_valid and not g.is_empty and g.geom_type in ("Polygon","MultiPolygon"):reference.append(g)
            except Exception:pass
        ix=json.loads((ROOT/"index.json").read_text());seen=set();geos=[]
        extent=(box(*reference[0].bounds) if reference else box(35.8,34.4,35.9,34.48))
        for g in reference[1:]:extent=extent.union(g).envelope
        for t in ix["tiles"]:
            if t["type"]!="building" or t["status"]!="ok" or not box(*t["bbox"]).intersects(extent):continue
            for f in json.loads(Path(t["path"].removeprefix("./")).read_text()).get("features",[]):
                uid=str(f.get("id") or "")
                if uid in seen:continue
                seen.add(uid)
                try:
                    g=shape(f["geometry"])
                    if g.is_valid and g.intersects(extent):geos.append(g)
                except Exception:pass
        tree=STRtree(geos)
        results={"reference_polygons":len(reference),"geolb_polygons_intersecting_source_extent":len(geos),"candidate_missing":0,"possible_shape_disagreement":0,"high_overlap":0}
        for g in reference:
            best=0.0
            for k in tree.query(g):
                h=geos[int(k)]
                if g.intersects(h):
                    union=g.union(h).area
                    if union:best=max(best,g.intersection(h).area/union)
            if best>=.65:results["high_overlap"]+=1
            elif best>=.15:results["possible_shape_disagreement"]+=1
            else:results["candidate_missing"]+=1
        output={**metadata,"provenance":provenance,"integration":{"approved_count":0,"reason":"Await explicit rights and independently dated imagery verification"},"status":"completed","matching":"Best polygon intersection-over-union; high >=0.65, ambiguous >=0.15, candidate missing <0.15","metrics":results,"caveats":["Reference date, accuracy, and rights unknown.","Only applicable to AUB layer spatial coverage.","Candidate missing does not mean confirmed actual missing building.","No source geometry copied or distributed."]}
    except Exception as exc:
        output={**metadata,"status":"source_unavailable","error":str(exc)}
    (ROOT/"aub_fair_audit.json").write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))
    if output["status"]!="completed":raise SystemExit(1)
if __name__=="__main__":main()
