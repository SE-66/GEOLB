#!/usr/bin/env python3
"""Download open Overture features for a Tripoli pilot area (no API key).
Requires: pip install overturemaps
Usage: python scripts/fetch_tripoli.py
The bounding box is a rectangular PILOT, not the Tripoli administrative boundary.
Check release licenses and attribution per dataset before publication.
"""
from pathlib import Path
import subprocess
import sys

WEST,SOUTH,EAST,NORTH = 35.837,34.428,35.865,34.448
BBOX = f"{WEST},{SOUTH},{EAST},{NORTH}"
OUT = Path("data/tripoli")
OUT.mkdir(parents=True,exist_ok=True)
for theme in ("building","segment","place"):
    target = OUT / f"overture_{theme}.geojson"
    command = ["overturemaps","download","--bbox",BBOX,"-f","geojson","--type",theme,"-o",str(target)]
    print("Running:", " ".join(command),flush=True)
    try:
        subprocess.run(command,check=True)
    except FileNotFoundError:
        sys.exit("Install the Overture CLI first: pip install overturemaps")
    except subprocess.CalledProcessError as exc:
        print(f"Download failed for {theme}: {exc}",file=sys.stderr)
print("Open GeoLB and import the GeoJSON files individually. Review coverage and licensing.")
