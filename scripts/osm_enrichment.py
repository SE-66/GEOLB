#!/usr/bin/env python3
"""Extract source-attributed OSM address, entrance, and multilingual road metadata for Greater Tripoli.
Uses a Geofabrik Lebanon extract. Does not invent house numbers or replace Overture buildings.
"""
import json,subprocess,tempfile,urllib.request,collections
from pathlib import Path
ROOT=Path('data/greater-tripoli'); ROOT.mkdir(parents=True,exist_ok=True)
BBOX='35.80,34.40,35.90,34.48'
features=[]; seen=set();counts=collections.Counter()
def point_of(g):
 t=g.get('type');c=g.get('coordinates')
 if t=='Point':return c
 if t=='LineString' and c:return c[len(c)//2]
 if t=='Polygon' and c and c[0]:return c[0][0]
 if t=='MultiPolygon' and c and c[0] and c[0][0]:return c[0][0][0]
 return None
with tempfile.TemporaryDirectory() as tmp:
 from pathlib import Path
 d=Path(tmp);p=d/'lebanon.pbf';clip=d/'tripoli.pbf';seq=d/'tripoli.geojsonseq'
 urllib.request.urlretrieve('https://download.geofabrik.de/asia/lebanon-latest.osm.pbf',p)
 subprocess.run(['osmium','extract','--overwrite','-b',BBOX,'-o',str(clip),str(p)],check=True)
 subprocess.run(['osmium','export','--overwrite','-f','geojsonseq','-o',str(seq),str(clip)],check=True)
 for line in seq.open(encoding='utf8'):
  try:
   f=json.loads(line.lstrip('\x1e').strip());props=f.get('properties') or {};tags=props.get('tags') if isinstance(props.get('tags'),dict) else props
   geom=f.get('geometry') or {};pt=point_of(geom)
   if not pt or len(pt)<2:continue
   lon,lat=pt[:2]
   if not (35.8<=lon<=35.9 and 34.4<=lat<=34.48):continue
   ident=str(f.get('id') or tags.get('@id') or tags.get('id') or (geom.get('type'),str(pt)))
   house=str(tags.get('addr:housenumber') or '').strip()
   entrance=str(tags.get('entrance') or '').strip()
   names={k:v for k,v in tags.items() if k in ('name','name:ar','name:en','name:fr','official_name','alt_name') and isinstance(v,str)}
   road=bool(tags.get('highway')) and geom.get('type') in ('LineString','MultiLineString')
   if not house and not entrance and not (road and names):continue
   kind='address' if house else 'entrance' if entrance else 'road_name'
   key=kind+':'+ident
   if key in seen:continue
   seen.add(key)
   record={'type':'Feature','geometry':{'type':'Point','coordinates':[lon,lat]},'properties':{'source':'OpenStreetMap / Geofabrik','license':'ODbL-1.0','source_id':ident,'kind':kind,'housenumber':house,'street':str(tags.get('addr:street') or ''),'entrance':entrance,'name':str(tags.get('name') or ''),'name_ar':str(tags.get('name:ar') or ''),'name_en':str(tags.get('name:en') or ''),'name_fr':str(tags.get('name:fr') or ''),'review_status':'source_record_unverified'}}
   features.append(record);counts[kind]+=1
  except (ValueError,TypeError,KeyError,IndexError):
   continue
out={'type':'FeatureCollection','features':features}
(ROOT/'osm_enrichment.geojson').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
(ROOT/'osm_enrichment_audit.json').write_text(json.dumps({'source':'Geofabrik latest Lebanon OpenStreetMap extract','license':'ODbL-1.0','bounds':[35.8,34.4,35.9,34.48],'counts':dict(counts),'total':len(features),'status':'source_records_not_independently_verified','note':'Point anchors for polygons/roads are approximate, not authoritative entrances or address parcel centroids.'},indent=2))
print('Enrichment counts',dict(counts))
