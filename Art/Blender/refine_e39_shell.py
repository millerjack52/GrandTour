"""BMW-specific shape study. Continuous welded shell; no assembled door skins.
Reference: BMW 1999 owner's manual, sport wagon dimension drawing, printed p200.
Axes retained from the source: front -Y, left +X, metres. Review only, no import.
"""
import bpy,bmesh,math,json,sys,argparse
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--revision',default='01');ap.add_argument('--views',default='three_quarter,side,front,rear');ap.add_argument('--samples',type=int,default=32)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT=ROOT/'Art/Export/E39Refinement'/args.revision;OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC'
def P(v):return Vector((v[1],-v[0],v[2]))
def material(name,c,rough=.6):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=rough
 return m
clay=material('Review_Clay',(.30,.32,.34));glazing=material('Review_Glazing',(.028,.040,.05),.65);tyre=material('Review_Tyre',(.065,.071,.075));rim=material('Review_Wheel',(.27,.29,.30));ground=material('Studio',(.105,.12,.135))
glazing.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.12
def interp(x,pts):
 if x<=pts[0][0]:return pts[0][1]
 for (a,b),(c,d) in zip(pts,pts[1:]):
  if x<=c:return b+(d-b)*(x-a)/(c-a)
 return pts[-1][1]
F=2.270;R=F-4.805;WB=2.830;RAD=.323
# Longitudinal silhouette landmarks, read from the dimension drawing and fitted
# to the published wheelbase. These are authored shape estimates, not scan data.
tops=[(R,.805),(-2.45,.93),(-2.38,1.005),(-2.17,1.245),(-1.96,1.405),(-1.79,1.432),(-1.35,1.44),(-.65,1.44),(-.12,1.435),(.10,1.402),(.25,1.321),(.55,1.132),(.83,1.001),(1.15,.95),(1.65,.872),(2.05,.792),(F,.736)]
belts=[(R,.76),(-2.40,.954),(-1.9,.985),(-1.3,.979),(-.3,.966),(.83,.956),(1.5,.832),(2.0,.750),(F,.661)]
widths=[(R,.810),(-2.43,.877),(-2.12,.896),(-1.6,.900),(-.6,.893),(.5,.884),(1.45,.896),(1.90,.886),(2.12,.855),(F,.792)]
roofwidths=[(R,.755),(-2.4,.790),(-1.96,.639),(-1.6,.632),(-.4,.636),(.10,.642),(.83,.822),(1.6,.817),(F,.744)]
us=sorted(set([round(R+i*(F-R)/52,6) for i in range(53)]+[p[0] for p in tops]+[-2.30,-2.20,-2.12,-1.22,-1.12,-.41,-.32,.14,.73,WB/2,-WB/2]))
def upper_station(u):
 return interp(u,[(R,R),(-2.38,-2.30),(-2.20,-1.98),(-1.22,-1.08),(-1.12,-.99),(-.41,-.50),(-.32,-.41),(.14,.14),(.73,.73),(F,F)])
vs=[];faces=[];matids=[]
for u in us:
 w=interp(u,widths);h=interp(u,tops);b=min(interp(u,belts),h-.06)
 uu=upper_station(u);hh=interp(uu,tops);rw=min(interp(uu,roofwidths),w-.073)
 half=[(u,v,z) for v,z in [(0,.215),(.56,.215),(w-.08,.245),(w-.022,.31),(w-.002,.46),(w,.535),(w-.009,b-.055),(w-.027,b),(w-.055,b+.022)]]
 for t in [.14,.86,1.]:half.append((u*(1-t)+uu*t,(w-.055)*(1-t)+rw*t,(b+.022)*(1-t)+(hh-.04)*t))
 half.extend([(uu,rw-.025,hh-.014),(uu,rw*.52,hh-.002),(uu,0,hh)])
 profile=half+ [(x,-v,z) for x,v,z in half[-2:0:-1]]
 vs.extend(P(p) for p in profile)
N=len(profile)
for i in range(len(us)-1):
 u=(us[i]+us[i+1])/2
 for j in range(N):
  faces.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
  k=j if j<14 else N-j-1
  sideglass=(8<=k<=10 and ((-.32<u<.73) or (-1.12<u<-.41) or (-2.20<u<-1.22)))
  if k==8 and u<-2.12:sideglass=False
  roof_u=(upper_station(us[i])+upper_station(us[i+1]))/2
  foreglass=(k>=12 and .14<roof_u<.73)
  aftglass=(k>=12 and -2.30<roof_u<-2.02)
  matids.append(1 if sideglass or foreglass or aftglass else 0)
faces.extend([tuple(range(N-1,-1,-1)),tuple((len(us)-1)*N+j for j in range(N))]);matids.extend([0,0])
me=bpy.data.meshes.new('E39_SharedSurface');me.from_pydata(vs,[],faces);me.materials.append(clay);me.materials.append(glazing);me.update()
body=bpy.data.objects.new('E39_ContinuousBodyShell',me);scene.collection.objects.link(body)
for p,mi in zip(me.polygons,matids):p.material_index=mi;p.use_smooth=True
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
# Keep the uncut control cage, hidden, so downstream doors derive from this surface.
master=body.copy();master.data=body.data.copy();master.name='CONTROL_UncutSharedShell';scene.collection.objects.link(master);master.hide_render=True;master.hide_viewport=True
# Four wheel openings cut into the shared body, never independently shaped fenders.
for u,axle in [(WB/2,'F'),(-WB/2,'R')]:
 for s,side in [(1,'L'),(-1,'R')]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=.378,depth=.68,location=P((u,s*.875,RAD)),rotation=(0,math.pi/2,0))
  cut=bpy.context.object;cut.name='ArchTool_'+axle+side
  bpy.context.view_layer.objects.active=body
  mod=body.modifiers.new('Shared arch '+axle+side,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
  bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
  track=1.512 if axle=='F' else 1.526
  bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=RAD,depth=.215,location=P((u,s*track/2,RAD)),rotation=(0,math.pi/2,0))
  o=bpy.context.object;o.name='ReviewWheel_'+axle+side;o.data.materials.append(tyre)
  bevel=o.modifiers.new('Tyre shoulders','BEVEL');bevel.width=.021;bevel.segments=2
  for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.202,depth=.006,location=P((u,s*(track/2+.109),RAD)),rotation=(0,math.pi/2,0))
  o=bpy.context.object;o.name='ReviewRim_'+axle+side;o.data.materials.append(rim)
# Make creases deliberate rather than averaging bonnet, sides and wheel wells.
bm=bmesh.new();bm.from_mesh(body.data)
for e in bm.edges:
 if len(e.link_faces)==2 and e.calc_face_angle()>math.radians(32):e.smooth=False
bm.to_mesh(body.data);bm.free()
bevel=body.modifiers.new('Body edge softening 2mm','BEVEL');bevel.width=.002;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35)
body['Stage']='Untextured proportion study; panel boundaries not cut yet'
body['PublishedTargets']='4805 length, 1800 width, 1440 height, 2830 wheelbase, 1512/1526 track (mm)'
body['Reference']='BMW 1999 owner manual, printed p200; locally archived reference drawing'
# Neutral studio. Lighting stays identical between iterations.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));o=bpy.context.object;o.name='StudioGround';o.data.materials.append(ground)
scene.world=bpy.data.worlds.new('NeutralStudio');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.15,.17,.20,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.4
for name,loc,power,size in [('Key',(4,4,6),1000,5),('Fill',(0,-4,3),600,4),('Rim',(-4,1,4),950,3)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=P(loc);o.rotation_euler=(P((0,0,.6))-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam
views={'three_quarter':((7,7,3.7),(-.10,0,.74),'PERSP',6.),'side':((-.1325,9,.72),(-.1325,0,.72),'ORTHO',5.45),'front':((9,0,.74),(0,0,.74),'ORTHO',2.6),'rear':((-9,0,.74),(0,0,.74),'ORTHO',2.6),'rear_quarter':((-7,-7,3.5),(-.2,0,.74),'PERSP',6.)}
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.65
def view(name):
 pos,target,typ,scale=views[name];cam.location=P(pos);cam.rotation_euler=(P(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.type=typ;cd.ortho_scale=scale;cd.lens=55
 bpy.data.objects['StudioGround'].hide_render=typ=='ORTHO'
view('three_quarter')
# Pack the actual dimensional source alongside the study for later modelling.
reference=ROOT/'Art/References/Vehicles/E39Refinement/BMW_dimensions_page200.png'
if reference.exists():
 ref=bpy.data.images.load(str(reference));ref.pack()
notes=bpy.data.texts.new('READ_ME_ShapeStudy')
notes.write('E39 Touring body proportion checkpoint. Front -Y, left +X, metres.\nOne connected shell; window colours are guides, not separate glazing.\nBMW owner manual printed page 200 is packed as an image.\nPublished overall dimensions anchor the study; intermediate shapes are authored estimates.\nNot a finished vehicle: panel loops, lamps, bumpers, interior, rig and UVs still pending.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'E39_ShellStudy.blend'))
bm=bmesh.new();bm.from_mesh(body.data)
report={'stage':'BODY_PROPORTIONS_REVIEW','revision':args.revision,'vertices':len(bm.verts),'faces':len(bm.faces),'loose_vertices':sum(not v.link_faces for v in bm.verts),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'targets_mm':{'length':4805,'width':1800,'height':1440,'wheelbase':2830,'front_track':1512,'rear_track':1526},'reference_url':'https://www.ge39.com/files/2000Manual-5Sedan-SportWagon.pdf','limitations':['Shape study only; not rigged, UV mapped or exported.','Window regions are face assignments in the common surface; glazing and panels separate after shape review.','Wheel meshes are dimensional placeholders.']}
bm.free();assert report['boundary_edges']==0 and report['nonmanifold_edges']==0,report
body.data.calc_loop_triangles()
coords=[v.co for v in body.data.vertices]
report['shell_triangles_before_bevel']=len(body.data.loop_triangles)
report['measured_shell_mm']={'length':round((max(v.y for v in coords)-min(v.y for v in coords))*1000,3),'width':round((max(v.x for v in coords)-min(v.x for v in coords))*1000,3),'roof_above_ground':round(max(v.z for v in coords)*1000,3)}
report['measured_wheel_centres_mm']={n:round((bpy.data.objects[a].location-bpy.data.objects[b].location).length*1000,3) for n,a,b in [('wheelbase','ReviewWheel_FL','ReviewWheel_RL'),('front_track','ReviewWheel_FL','ReviewWheel_FR'),('rear_track','ReviewWheel_RL','ReviewWheel_RR')]}
# Wheelbase is longitudinal distance; front and rear tracks intentionally differ.
report['measured_wheel_centres_mm']['wheelbase']=round(abs(bpy.data.objects['ReviewWheel_FL'].location.y-bpy.data.objects['ReviewWheel_RL'].location.y)*1000,3)
(OUT/'shape_check.json').write_text(json.dumps(report,indent=2))
(OUT/'refine_e39_shell.py').write_text(Path(__file__).read_text())
for name in args.views.split(','):
 view(name);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('E39_SHELL_REVIEW_SAVED '+str(OUT),flush=True)
