import bpy,json,math,sys
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreGaea/GaeaCreek'
if '--course-revision' in sys.argv:OUT=ROOT/'Art/Export/BenmoreGaea/CourseRevision'
if '--morphology' in sys.argv:OUT=ROOT/'Art/Export/BenmoreGaea/Morphology'
for name in ['SM_GC_RiverSurface','SM_GC_OutletSurface']+(['SM_GC_MouthBed'] if any(k in sys.argv for k in ['--course-revision','--morphology']) else []):
    data=json.loads((OUT/(name+'.json')).read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in data['vertices']],[],[list(reversed(t)) for t in data['faces']]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    for p in mesh.polygons:p.use_smooth=True
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
print('CHANNEL_SHAPE_MESH_EXPORTED')

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
c=next(c for c in json.loads((OUT/'crossings.json').read_text()) if c['name']=='Footbridge');ends=c['ends_m'];a=Vector((ends[0][0],-ends[0][1],ends[0][2]));b=Vector((ends[1][0],-ends[1][1],ends[1][2]))
direction=b-a;direction.z=0;length=direction.length+.9;direction.normalize();side=Vector((-direction.y,direction.x,0));mid=(a+b)/2
deck_z=max(a.z,b.z,c['surface_z_m']+.42)+.12
pieces=[]

def beam(center,dimensions,yaw=0,bevel=.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.dimensions=dimensions;o.rotation_euler.z=yaw
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('soft timber edges','BEVEL');mod.width=bevel;mod.segments=1
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name);pieces.append(o)
    return o

yaw=math.atan2(direction.y,direction.x)
for sign in [-1,1]:beam(Vector((mid.x,mid.y,deck_z-.20))+side*sign*.58,(length,.19,.32),yaw)
planks=math.ceil(length/.26)
for i in range(planks):
    p=Vector((mid.x,mid.y,deck_z))+direction*((i+.5)*length/planks-length/2)
    beam(p,(length/planks-.013,1.72,.105),yaw)
for t in [-.5,-.25,0,.25,.5]:
    for sign in [-1,1]:
        p=Vector((mid.x,mid.y,deck_z+.48))+direction*t*length+side*sign*.81
        beam(p,(.12,.12,1.05),yaw)
for sign in [-1,1]:
    for height in [.5,.99]:beam(Vector((mid.x,mid.y,deck_z+height))+side*sign*.81,(length+.14,.09,.10),yaw)
# End sleepers bury into the two banks, leaving the channel unobstructed.
for endpoint in [a,b]:
    bottom=endpoint.z-.20;top=deck_z-.03
    beam(Vector((endpoint.x,endpoint.y,(bottom+top)/2)),(.55,1.95,top-bottom),yaw,.02)
# Short timber ramps meet each bank rather than leaving a tall step at one end.
for endpoint,raw in zip([a,b],c['approach_anchors_m']):
    start=Vector((raw[0],-raw[1],raw[2]+.07));end=Vector((endpoint.x,endpoint.y,deck_z));axis=end-start;ramp_length=axis.length;rotation=axis.to_track_quat('X','Z')
    for i in range(math.ceil(ramp_length/.26)):
        count=math.ceil(ramp_length/.26);center=start+axis*((i+.5)/count)
        o=beam(center,(ramp_length/count-.012,1.72,.105),0);o.rotation_mode='QUATERNION';o.rotation_quaternion=rotation
bpy.ops.object.select_all(action='DESELECT')
for p in pieces:p.select_set(True)
bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();bridge=bpy.context.object;bridge.name='SM_RL_Footbridge'
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_GC_Footbridge.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
