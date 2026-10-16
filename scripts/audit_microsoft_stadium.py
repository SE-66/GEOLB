#!/usr/bin/env python3
"""Compare permissively licensed Microsoft satellite-derived footprint tiles with GeoLB Stadium.
Candidate geometries are never added to the approved inventory automatically.
"""
import csv,gzip,io,json,math,urllib.request
from pathlib import Path
from shapely.geometry import shape, box, mapping
from shapely.strtree import STRtree

ROOT=Path("data/greater-tripoli")
AOI=box(35.840,34.429,35.864,34.449)
DATASET="https://bfppub.blob.core.windows.net/%24web/2026-08-13/dataset-links.csv"
def quad_bounds(q):
 x=y=0
 for i,c in enumerate(str(q)):
  b=1 << (len(q)-i-1)
  if c in '13':x|=b
  if c in '23':y|=b
 n=2**len(q);west=x/n*360-180;east=(x+1)/n*360-180
 def lat(v):return math.degrees(math.atan(math.sinh(math.pi*(1-2*v/n))))
 return box(west,lat(y+1),east,lat(y))
def urlopen(url):
 return urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"GeoLB-open-building-research/1.0"}),timeout=90)
def main():
 with urlopen(DATASET) as r: raw=r.read().decode('utf-8-sig')
 reader=csv.DictReader(io.StringIO(raw))
 print("Microsoft catalog columns:",reader.fieldnames,flush=True)
 selected=[]
 for rec in reader:
  cols={k.lower().strip().replace(' ','_'):str(v or '') for k,v in rec.items() if k}
  u=next((v for k,v in cols.items() if ('url' in k or k in ('location','link')) and v.startswith('http')),None)
  q=next((v for k,v in cols.items() if ('quadkey' in k or k=='quad_key') and v.isdigit()),None)
  country=' '.join(str(v) for v in rec.values()).lower()
  if u and ((q and quad_bounds(q).intersects(AOI)) or (not q and 'lebanon' in country)):
   selected.append((u,q))
 print("Catalog eligible links:",len(selected),flush=True)
 # A large or ambiguous catalog is not treated as complete coverage.
 candidates=[];seen=set();processed=[];errors=[]
 overture={};ix=json.loads((ROOT/'index.json').read_text())
 for t in ix['tiles']:
  if t['type']!='building' or not box(*t['bbox']).intersects(AOI):continue
  for f in json.loads(Path(t['path'].removeprefix('./')).read_text()).get('features',[]):
   fid=str(f.get('id') or '')
   if fid in overture:continue
   g=shape(f['geometry'])
   if g.is_valid and g.intersects(AOI):overture[fid]=g
 ov=list(overture.values());tree=STRtree(ov)
 for url,q in selected[:15]:
  try:
   print('Reading',url[:140],flush=True)
   with urlopen(url) as r:
    stream=gzip.GzipFile(fileobj=r) if '.gz' in url.lower() else r
    for line in stream:
     try:
      f=json.loads(line)
      if f.get('type')=='Feature': geom=f['geometry'];prop=f.get('properties') or {}
      elif 'geometry' in f:geom=f['geometry'];prop=f.get('properties') or {}
      else:continue
      g=shape(geom)
      if not g.is_valid or g.is_empty or not g.intersects(AOI):continue
      b=g.bounds;key=tuple(round(v,7) for v in b)
      if key in seen:continue
      seen.add(key)
      best=0
      for j in tree.query(g):
       h=ov[int(j)]
       if not g.intersects(h):continue
       iou=g.intersection(h).area/g.union(h).area
       best=max(best,iou)
      if best <.20 and g.area>0:
       candidates.append({'type':'Feature','geometry':mapping(g),'properties':{'source':'Microsoft Global ML Building Footprints','license':'CDLA-Permissive-2.0','best_overture_iou':round(best,3),'status':'candidate_unverified','source_tile_quadkey':q}})
     except (ValueError,TypeError,KeyError):continue
   processed.append(url)
  except Exception as exc:errors.append({'url':url,'error':str(exc)[:250]})
 out={'type':'FeatureCollection','features':candidates}
 (ROOT/'stadium_microsoft_candidates.geojson').write_text(json.dumps(out,separators=(',',':')))
 status='complete_catalog_scan' if len(processed)==len(selected) and not errors else 'partial_or_failed_scan'
 report={'status':status,'source':'Microsoft Global ML Building Footprints 2026-08-13','license':'CDLA Permissive 2.0','source_catalog':DATASET,'area_bbox':list(AOI.bounds),'catalog_matching_links':len(selected),'links_processed':len(processed),'errors':errors,'overture_footprints_in_aoi':len(overture),'candidate_footprints':len(candidates),'integrated_approved':0,'warning':'Low IoU candidates are unverified satellite-derived polygons; needs secondary corroboration and duplicate review before any main map addition.'}
 (ROOT/'stadium_microsoft_audit.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
