#!/usr/bin/env python3
"""Fetch Overture (buildings/transport/places), Geofabrik OSM and normalize into GeoLB files.
Requires overturemaps, osmium-tool (CLI) and network; designed for CI. No paid API key.
Default bbox covers a central Tripoli pilot, NOT the municipality boundary.
"""
import argparse,json,subprocess,urllib.request,sys
from pathlib import Path
BBOX=(35.837,34.428,35.865,34.448)
def run(*args):
 print("+",*map(str,args),flush=True)
 subprocess.run(list(map(str,args)),check=True)
def fc(path,features):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({"type":"FeatureCollection","features":features},ensure_ascii=False),encoding="utf-8")
def main():
 p=argparse.ArgumentParser();p.add_argument("--bbox",default=",".join(map(str,BBOX)));p.add_argument("--out",default="data/tripoli");p.add_argument("--max-features",type=int,default=15000);p.add_argument("--skip-overture",action="store_true");p.add_argument("--skip-geofabrik",action="store_true");a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 west,south,east,north=map(float,a.bbox.split(","))
 if not (35.0<west<east<37.0 and 33.0<south<north<35.0):sys.exit("Bounding box must be within Lebanon")
 if (east-west)*(north-south)>.003:sys.exit("Bounding box exceeds pilot safety limit")
 report={"bbox":a.bbox,"sources":{}}
 if not a.skip_overture:
  for typ in ("building","segment","place"):
   path=out/f"overture_{typ}.geojson"
   try:
    run("overturemaps","download",f"--bbox={a.bbox}","-f","geojson",f"--type={typ}","-o",path)
    raw=json.loads(path.read_text());features=raw.get("features",[])
    # Limit feature count; record truncated status so coverage isn't misrepresented.
    if len(features)>a.max_features:fc(path,features[:a.max_features])
    report["sources"][typ]={"count":min(len(features),a.max_features),"truncated":len(features)>a.max_features}
   except Exception as exc:report["sources"][typ]={"error":str(exc)};print("Overture error:",exc,file=sys.stderr)
 if not a.skip_geofabrik:
  pbf=out/"lebanon-latest.osm.pbf";clip=out/"tripoli.osm.pbf";seq=out/"tripoli.geojsonseq"
  url="https://download.geofabrik.de/asia/lebanon-latest.osm.pbf"
  try:
   if not pbf.exists():print("Downloading",url);urllib.request.urlretrieve(url,pbf)
   run("osmium","extract","--overwrite","-b",a.bbox,"-o",clip,pbf)
   run("osmium","export","--overwrite","-f","geojsonseq","-o",seq,clip)
   roads=[];buildings=[]
   with seq.open(encoding="utf-8") as stream:
    for line in stream:
     try:f=json.loads(line)
     except json.JSONDecodeError:continue
     props=f.get("properties") or {};g=f.get("geometry") or {};geom=g.get("type","")
     if props.get("building") and "Polygon" in geom:buildings.append(f)
     if props.get("highway") and "LineString" in geom:roads.append(f)
   for name,arr in [("osm_buildings",buildings),("osm_roads",roads)]:
    fc(out/f"{name}.geojson",arr[:a.max_features]);report["sources"][name]={"count":min(len(arr),a.max_features),"truncated":len(arr)>a.max_features}
  except Exception as exc:report["sources"]["geofabrik"]={"error":str(exc)};print("Geofabrik error:",exc,file=sys.stderr)
  finally:
   for temp in (pbf,clip,seq):
    if temp.exists():temp.unlink()
 (out/"manifest.json").write_text(json.dumps(report,indent=2))
 print("Finished:",json.dumps(report,indent=2))
if __name__=="__main__":main()
