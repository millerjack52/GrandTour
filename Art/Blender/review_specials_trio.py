"""Review the actual textured rig and distance mesh, including opening the hatch."""
import bpy,sys,json,math,argparse
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--car',required=True);ap.add_argument('--package',default='Package_v01');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);car=args.car
OUT=ROOT/'Art/Export/SpecialsTrio'/car/args.package
def P(v):return Vector((v[1],-v[0],v[2]))
for name in ['lod2','articulation','rear_open']:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/(car+('_LOD2' if name=='lod2' else '_Rigged')+'.blend')))
 scene=bpy.context.scene;views=json.loads(scene['ReviewViews']);pos,target,lens=views['rear' if name=='rear_open' else 'front'];cam=scene.camera
 cam.location=P(pos)*(1.22 if name=='rear_open' else 1);cam.rotation_euler=(P(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=lens
 bpy.data.objects['CabinReviewFill'].hide_render=True;bpy.data.objects['StudioGround'].hide_render=False;scene.cycles.device='CPU';scene.cycles.samples=24
 if name!='lod2':
  arm=bpy.data.objects['Armature'];poses=[('Door_FL','Z',-48),('Door_RL','Z',-42),('Hood','X',-38)] if name=='articulation' else [('Tailgate','Z' if car=='SJ413' else 'X',65 if car=='SJ413' else 55),('Trunk','X',45)]
  for bone,axis,angle in poses:
   pb=arm.pose.bones.get(bone)
   if pb:p=pb.bone.head_local;pb.matrix=Matrix.Translation(p)@Matrix.Rotation(math.radians(angle),4,axis)@Matrix.Translation(-p)@pb.bone.matrix_local
  bpy.context.view_layer.update()
  bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(car+'_'+name+'.blend')))
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
 print('TRIO_REVIEW_OK '+car+' '+name,flush=True)
