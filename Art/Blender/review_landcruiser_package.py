"""Actual geometry review of distance reduction and articulated panels."""
import bpy,math,json,sys,argparse
from pathlib import Path
from mathutils import Matrix,Vector
parser=argparse.ArgumentParser();parser.add_argument('--package',default='Package_v03');parser.add_argument('--views',default='lod2,articulation,side');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/LandCruiser'/args.package
def P(v):return Vector((v[1],-v[0],v[2]))
for review,file in [('lod2','LandCruiser80_LOD2.blend'),('articulation','LandCruiser80_Rigged.blend'),('side','LandCruiser80_Rigged.blend')]:
    if review not in args.views.split(','):continue
    bpy.ops.wm.open_mainfile(filepath=str(OUT/file));scene=bpy.context.scene
    scene.cycles.device='CPU';scene.cycles.samples=24;scene.render.threads_mode='FIXED';scene.render.threads=6
    cam=scene.camera;cam.location=P((6.2,6,3));cam.rotation_euler=(P((-.05,0,.98))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=57;cam.data.type='PERSP'
    bpy.data.objects['CabinReviewFill'].hide_render=True
    if review=='side':
        cam.location=P((0,8,1.1));cam.rotation_euler=(P((0,0,1.1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=5.7
        bpy.data.objects['StudioGround'].hide_render=True
    if review=='articulation':
        arm=bpy.data.objects['Armature']
        for name,axis,degrees in [('Door_FL','Z',-45),('Door_RL','Z',-40),('Hood','X',-38),('Wheel_FL','Z',18),('Wheel_FR','Z',18)]:
            pb=arm.pose.bones[name];p=pb.bone.head_local
            pb.matrix=Matrix.Translation(p)@Matrix.Rotation(math.radians(degrees),4,axis)@Matrix.Translation(-p)@pb.bone.matrix_local
        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LandCruiser80_ArticulationReview.blend'))
    scene.render.filepath=str(OUT/(review+'.png'));bpy.ops.render.render(write_still=True)
    print('LC_REVIEW_OK '+review,flush=True)
