"""LODs, articulated rig checks and fresh FBX roundtrips for specials vehicles."""
import sys,argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--car',required=True);ap.add_argument('--package',default='Package_v01');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
car=args.car;package=args.package;folder=ROOT/'Art/Export/SpecialsTrio'/car/package
asset=json.loads((folder/'asset_report.json').read_text());spec=asset['spec']
text=(ROOT/'Art/Blender/validate_landcruiser.py').read_text()
def replace(old,new):
 global text
 assert old in text,old
 text=text.replace(old,new)
replace("args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])",f"args=parser.parse_args(['--package',{package!r}])")
replace("ROOT/'Art/Export/LandCruiser'",f"ROOT/'Art/Export/SpecialsTrio'/{car!r}")
replace('LandCruiser80',car)
# The visual review rejected collapsing wheel dishes/spokes: keep the exterior
# intact and reduce hidden interior geometry until an engine-specific LOD pass.
replace("if 'Glass' not in o.name and 'Markings' not in o.name:","if 'Glass' not in o.name and 'Markings' not in o.name and 'Exterior' not in o.name:")
replace('abs(wb-285)',f"abs(wb-{spec['wb']*100})");replace('abs(track-160)',f"abs(track-{spec['track']*100})");replace("abs(pts['Wheel_FL'].z-41.5)",f"abs(pts['Wheel_FL'].z-{spec['r']*100})")
replace("objects=[o for o in bpy.data.collections['GAME_ASSET'].objects if o.type=='MESH'];arm=bpy.data.objects['Armature']", """objects=[o for o in bpy.data.collections['GAME_ASSET'].objects if o.type=='MESH'];arm=bpy.data.objects['Armature']
    source_points=[T@(o.matrix_world@v.co) for o in objects for v in o.data.vertices]
    source_bounds=[max(p[i] for p in source_points)-min(p[i] for p in source_points) for i in range(3)]
""")
replace('470<bounds[0]<500 and 200<bounds[1]<240 and 185<bounds[2]<200','all(abs(a-b)<.1 for a,b in zip(bounds,source_bounds))')
# Build proxy dimensions from this vehicle, never reuse the LC dimensions.
start=text.index("spec=[('Root'");end=text.index('proxy_report=[]',start)
centre=(spec['front']+spec['rear'])/2;length=spec['front']-spec['rear']
proxy=[('Root',(0,-centre,(spec['belt']+spec['sill'])/2),(spec['w']*2-.12,length-.16,spec['belt']-spec['sill'])),('Root',(0,-(spec['ft']+spec['rt'])/2,(spec['belt']+spec['roof'])/2),(spec['w']*2-.26,spec['ft']-spec['rt'],spec['roof']-spec['belt']))]
text=text[:start]+f'spec={proxy!r}\n'+text[end:]
exec(compile(text,str(__file__),'exec'),{'__file__':str(__file__),'__name__':'__main__'})
