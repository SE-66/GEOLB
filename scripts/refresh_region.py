#!/usr/bin/env python3
"""Expand GeoLB Overture coverage around greater Tripoli with independently downloadable tiles.
Bounding box is a practical pilot rectangle, NOT a municipal boundary.
No arbitrary feature truncation: every successful tile is preserved; failed tiles are reported.
"""
import json, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
WEST,SOUTH,EAST,NORTH=35.80,34.40,35.90,34.48
COLS,ROWS=3,3
OUT=Path("data/greater-tripoli")
TYPES=("building","segment","place")
OUT.mkdir(parents=True,exist_ok=True)
def task(row,col,kind):
    w=WEST+(EAST-WEST)*col/COLS;e=WEST+(EAST-WEST)*(col+1)/COLS
    s=SOUTH+(NORTH-SOUTH)*row/ROWS;n=SOUTH+(NORTH-SOUTH)*(row+1)/ROWS
    key=f"r{row}c{col}"
    target=OUT/f"{key}_{kind}.geojson"
    bbox=f"{w:.7f},{s:.7f},{e:.7f},{n:.7f}"
    cmd=["overturemaps","download","--bbox",bbox,"-f","geojson","--type",kind,"-o",str(target)]
    try:
        subprocess.run(cmd,check=True,timeout=240,capture_output=True,text=True)
        content=json.loads(target.read_text())
        if content.get("type")!="FeatureCollection":raise ValueError("Expected FeatureCollection")
        return {"tile":key,"type":kind,"path":str(target).replace("data/","./data/"),"count":len(content.get("features",[])),"bbox":[w,s,e,n],"status":"ok"}
    except Exception as error:
        target.unlink(missing_ok=True)
        return {"tile":key,"type":kind,"bbox":[w,s,e,n],"status":"error","message":str(error)}
def main():
    results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks=[pool.submit(task,r,c,k) for r in range(ROWS) for c in range(COLS) for k in TYPES]
        for future in as_completed(tasks):
            result=future.result();results.append(result)
            print(result["tile"],result["type"],result["status"],result.get("count",result.get("message")),flush=True)
    results.sort(key=lambda x:(x["tile"],x["type"]))
    index={"name":"GeoLB Greater Tripoli provisional coverage","bbox":[WEST,SOUTH,EAST,NORTH],"municipal_boundary":False,"tiles":results,"complete":all(r["status"]=="ok" for r in results)}
    (OUT/"index.json").write_text(json.dumps(index,indent=2))
    if not index["complete"]:sys.exit("Incomplete regional data download. Check failed tiles in index.json.")
if __name__=="__main__":main()
