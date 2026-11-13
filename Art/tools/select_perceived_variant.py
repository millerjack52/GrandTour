"""Restore exact trial packages only when no Unreal process is running."""
import argparse,subprocess,shutil,json,hashlib
from pathlib import Path
ROOT=Path('C:/GrandTour');QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail';VAR=QA/'Variants'
p=argparse.ArgumentParser();p.add_argument('variant',choices=['baseline','detail','pom','nanite-preserve','nanite-voxel','nanite-ground','ao-preserve','ao-voxel','final']);args=p.parse_args()
check=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
assert check.stdout.strip()=='0','Close Unreal before selecting asset variants'
assert (VAR/'detail').exists() and (VAR/'baseline').exists()
layers=['detail'] if args.variant=='detail' else ['detail',args.variant]
for layer in layers:
 for src in (VAR/layer).rglob('*.uasset'):
  rel=src.relative_to(VAR/layer);dst=(ROOT/rel).resolve();assert dst.is_relative_to(ROOT/'Content');shutil.copy2(src,dst)
state=dict(variant=args.variant,packages={str(src.relative_to(VAR/'detail')):hashlib.sha256((ROOT/src.relative_to(VAR/'detail')).read_bytes()).hexdigest() for src in (VAR/'detail').rglob('*.uasset')})
(QA/'active-variant.json').write_text(json.dumps(state,indent=2));print(json.dumps(state))
