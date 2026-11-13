import bpy, hashlib, json, math, argparse, sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

p=argparse.ArgumentParser();p.add_argument('--source',default='C:/GrandTour/Art/Export/VehicleTools/pathfinder-2002-shape-v03/Pathfinder_2002_Shape.blend');p.add_argument('--output',default='C:/GrandTour/Art/Export/VehicleTools/pathfinder-2002-orthographic-v01')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
source=Path(args.source);out=Path(args.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Choose an empty review folder; preserve prior review edits.')
out.mkdir(parents=True,exist_ok=True)
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
sc=bpy.context.scene
def geometry_hash():
    h=hashlib.sha256()
    for o in sorted(bpy.data.objects,key=lambda o:o.name):
        if o.type not in {'MESH','CURVE'}:continue
        h.update(o.name.encode());h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode())
        if o.type=='MESH':
            for v in o.data.vertices:h.update(str(tuple(v.co)).encode())
            for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
        else:
            for s in o.data.splines:
                for p in s.points:h.update(str(tuple(p.co)).encode())
    return h.hexdigest()
before=geometry_hash()
# Presentation only: preserve mesh data, transforms and component boundaries.
for m in bpy.data.materials:
    if not m.use_nodes:continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if not p:continue
    if 'burgundy' in m.name: rgb=(.40,.42,.43)
    elif 'glazing' in m.name: rgb=(.068,.082,.088)
    elif 'rubber' in m.name or 'charcoal' in m.name: rgb=(.045,.048,.05)
    elif 'lens' in m.name or 'amber' in m.name: rgb=(.36,.37,.38)
    elif 'alloy' in m.name: rgb=(.27,.29,.30)
    else:continue
    p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Metallic'].default_value=0
    p.inputs['Roughness'].default_value=.72
bpy.data.objects['Ground'].hide_render=True
sc.render.film_transparent=True
sc.render.image_settings.color_mode='RGBA'
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.threads_mode='FIXED';sc.render.threads=12
sc.render.resolution_percentage=100
col=bpy.data.collections.new('09 | Matched orthographic review');sc.collection.children.link(col)
configs={
 'side':((8,.03,.95),(0,.03,.95),(1560,660),5.2),
 'front':((0,-8,.95),(0,0,.95),(750,660),2.5),
 'rear':((0,8,.95),(0,0,.95),(750,660),2.5),
 'top':((0,.03,8),(0,.03,0),(750,1560),5.2),
}
report={'source':str(source),'source_sha256':source_hash,'geometry_sha256':before,'pixels_per_metre':300,'geometry_changed':False,'model_shape_approved':False,'views':{}}
for name,(loc,target,res,scale) in configs.items():
    d=bpy.data.cameras.new('Ortho diagnostic | '+name);o=bpy.data.objects.new(d.name,d);col.objects.link(o)
    o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    if name=='top':o.rotation_euler.z+=math.pi # front at top
    d.type='ORTHO';d.ortho_scale=scale;d.lens=50
    sc.camera=o;sc.render.resolution_x,sc.render.resolution_y=res
    sc.render.filepath=str(out/(name+'-raw.png'))
    bpy.context.view_layer.update()
    def project(p):
        q=world_to_camera_view(sc,o,Vector(p));return [q.x*res[0],(1-q.y)*res[1]]
    landmarks={'front_axle':project((0,-1.35,.369)),'rear_axle':project((0,1.35,.369)),'ground':project((0,0,0)),'roof_height':project((0,0,1.685)),'origin':project((0,0,0))}
    report['views'][name]={'resolution':res,'camera_location':loc,'target':target,'ortho_scale':scale,'landmarks':landmarks}
    bpy.ops.render.render(write_still=True)
    print('ORTHO_FINISHED '+name,flush=True)
assert geometry_hash()==before,'Review modified geometry'
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'Source changed'
sc.camera=bpy.data.objects['Ortho diagnostic | side'];sc.render.resolution_x=1560;sc.render.resolution_y=660
sc['stage']='Unapproved shape. Diagnostic cameras/materials only; original mesh unchanged.'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pathfinder_Orthographic_Review.blend'))
(out/'review-metadata.json').write_text(json.dumps(report,indent=2))
print('ORTHOGRAPHIC_REVIEW_COMPLETE',flush=True)
