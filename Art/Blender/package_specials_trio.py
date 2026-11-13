"""Bake/rig/export a reviewed specials vehicle using the checked LC packaging contract.
The LC script is used as an explicitly checked template; LC files are never opened/written.
"""
import sys,argparse,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--car',required=True);ap.add_argument('--source',default='R6');ap.add_argument('--package',default='Package_v01')
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
car=args.car;source=args.source;package=args.package
text=(ROOT/'Art/Blender/package_landcruiser.py').read_text()
def replace(old,new):
 global text
 assert old in text,old
 text=text.replace(old,new)
replace("args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])",f"args=parser.parse_args(['--source',{source!r},'--package',{package!r}])")
replace("ROOT/'Art/Export/LandCruiser'",f"ROOT/'Art/Export/SpecialsTrio'/{car!r}")
replace('LandCruiser80',car);replace('LC80',car);replace('LC_','GT_')
start=text.index("MOVING=['Wheel_FL'");end=text.index("heads={'Root'",start)
text=text[:start]+"MOVING=list(json.loads(scene['Pivots']))\n"+text[end:]
replace("old.name in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']","False")
replace("'GT_Glass'","'GT_Glass'")
replace("'GT_Markings' or old.type=='FONT'","'GT_Markings' or old.type=='FONT'")
replace("report={'source_revision':args.source,", "report={'car':"+repr(car)+",'spec':json.loads(scene['Spec']),'source_revision':args.source,")
replace("scene.cycles.samples=24","scene.cycles.samples=24")
start=text.index("views={'front':");end=text.index("scene.cycles.samples=24",start)
text=text[:start]+"views=json.loads(scene['ReviewViews'])\n"+text[end:]
replace("cam.data.type='PERSP'","cam.data.type='ORTHO' if name=='side' else 'PERSP';cam.data.ortho_scale=report['spec']['front']-report['spec']['rear']+1")
# Do not accidentally export helper collision/QA collections.
replace("SKIP={'Studio','Reference','Pivots'}","SKIP={'Studio','Reference','Pivots','PhysicsProxies'}")
replace("bpy.ops.object.modifier_apply(modifier=tri.name)","""bpy.ops.object.modifier_apply(modifier=tri.name)
    bm=bmesh.new();bm.from_mesh(o.data)
    dead=[f for f in bm.faces if f.calc_area()<=1e-12]
    report['validation'][o.name+'_zero_area_faces_removed']=len(dead)
    if dead:bmesh.ops.delete(bm,geom=dead,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(o.data);bm.free();o.data.update()
""")
replace("bpy.ops.wm.save_as_mainfile(filepath=str(OUT/", "bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/")
# Correct brittle group-naming assumptions in the material classification.
replace("('DoorCard','DoorInsert','Armrest','InnerHandle','Speaker')","('DoorCard','DoorInsert','Armrest','InnerHandle','Speaker')")
compile(text,str(__file__),'exec')
exec(compile(text,str(__file__),'exec'),{'__file__':str(__file__),'__name__':'__main__'})
