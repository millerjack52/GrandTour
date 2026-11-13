"""Conservative Prado preparation. Source body positions are authoritative.
No generic body reconstruction, shrinkwrap or voxel remesh. Protected output.
"""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v01')
OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'Prado_Prepared.blend').exists(),'Output exists; choose a new revision'
S=5.0 # working scale only, not a claim of measured factory dimensions
A=json.loads((P/'islands.json').read_text());G=json.loads((P/'glass-selections.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC'
cols={}
for n in ['01 Body','02 Glass','03 Road wheels','04 Spare wheel','05 Front equipment','06 Roof rack and cargo','07 Side equipment','08 Underbody','09 Small fittings','90 Source reference','99 Review']:
 c=bpy.data.collections.new(n);sc.collection.children.link(c);cols[n]=c
M={}
for n,c in {'Paint':(.40,.43,.31,1),'Rubber':(.032,.038,.036,1),'Metal':(.12,.145,.14,1),'Wheel':(.32,.35,.31,1),'Glass':(.105,.175,.195,1),'Lens':(.68,.75,.73,1),'Case':(.49,.43,.31,1),'Board':(.40,.29,.15,1),'Amber':(.82,.30,.035,1),'Red':(.47,.042,.025,1)}.items():
 m=bpy.data.materials.new('Prado | '+n);m.diffuse_color=c;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.48
 if n in ['Metal','Wheel']:p.inputs['Metallic'].default_value=.55;p.inputs['Roughness'].default_value=.35
 if n=='Rubber':p.inputs['Roughness'].default_value=.8
 if n=='Glass':p.inputs['Transmission Weight'].default_value=.88;p.inputs['Roughness'].default_value=.14;p.inputs['IOR'].default_value=1.46
 M[n]=m
root=bpy.data.objects.new('PRADO | working assembly',None);cols['01 Body'].objects.link(root)
root['working_scale_note']='Uniform 5x normalized source; factory dimensions not verified.'
root['status']='Source-preserving exterior preparation. No interior, UV, collision, rig, LOD or engine validation.'
manifest=[];objects=[]
def mesh(n,v,f,col,mat='Paint',cleanup=True,weighted=True):
 me=bpy.data.meshes.new(n);me.from_pydata([Vector(p)*S for p in v],[],f);me.update()
 before=(len(me.vertices),len(me.polygons))
 bm=bmesh.new();bm.from_mesh(me)
 if cleanup:
  bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6*S)
  bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7*S)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for face in bm.faces:face.smooth=True
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle()<math.radians(35)
 bm.to_mesh(me);bm.free();me.update()
 o=bpy.data.objects.new(n,me);cols[col].objects.link(o);o.parent=root;me.materials.append(M[mat]);o.color=M[mat].diffuse_color
 if weighted:
  mod=o.modifiers.new('Surface normals — no vertex movement','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
 objects.append(o);return o
def subset(n,a,faceids,col,mat):
 fs=[a['polys'][i] for i in faceids];ids=sorted({i for f in fs for i in f});remap={a:i for i,a in enumerate(ids)}
 return mesh(n,[a['verts'][i] for i in ids],[[remap[i] for i in f] for f in fs],col,mat)
glassids={i for d in G.values() for i in d['faces']}
body=subset('Prado | source-fitted body',A[0],[i for i in range(len(A[0]['polys'])) if i not in glassids],'01 Body','Paint')
body['source_component']=0;body['shape_policy']='Original positions retained; panes extracted at shared edges. Retopology not claimed.'
for name,g in G.items():
 o=subset('Glass | '+name,A[0],g['faces'],'02 Glass','Glass');o['source_component']=0;o['source_faces']=json.dumps(g['faces'])
 sol=o.modifiers.new('Pane thickness inside existing aperture','SOLIDIFY');sol.thickness=.00065*S;sol.offset=-1
 # Boundary vertices are copied from the body exactly, not re-fitted to a rectangle.
 o['boundary_policy']='Exact source boundary; no hull or approximate window shape'
named={6:'Recovery board',7:'Roof basket',8:'Snorkel',10:'Bullbar center',13:'Bullbar left',14:'Bullbar right',15:'Front axle',18:'Driveline',19:'Recovery shackle',23:'Mirror right',24:'Mirror left',26:'Grille badge',27:'Jerrycan left',28:'Jerrycan right',29:'Rear axle left',30:'Rear axle right',37:'Auxiliary lamp left',38:'Auxiliary lamp right',49:'Running board right',50:'Running board left',51:'Winch',58:'Roof lamp right',59:'Roof lamp left',72:'Headlamp left',73:'Headlamp right'}
skip={0,1,2,3,4,5,20,21,22,25,67,77}
for i,a in enumerate(A):
 if i in skip:continue
 lo,hi=Vector(a['min']),Vector(a['max']);c=(lo+hi)/2
 # Remaining tiny rim hardware inside the old wheel envelopes is replaced too.
 if i>60 and abs(c.x)>.14 and any(abs(c.y-y)<.052 and abs(c.z-z)<.050 for y,z in [(-.289,.092),(.251,.091)]):
  skip.add(i);continue
 if c.z>.432:col,mat='06 Roof rack and cargo',('Case' if i in [9,16,17,32,34,45,52,56] else 'Metal')
 elif c.z<.115 or i in [15,18,29,30,74]:col,mat='08 Underbody','Metal'
 elif c.y<-.395:col,mat='05 Front equipment','Metal'
 elif abs(c.x)>.14:col,mat='07 Side equipment','Metal'
 else:col,mat='09 Small fittings','Metal'
 if i in [23,24]:mat='Paint'
 if i in [27,28,41,42]:mat='Case'
 if i==6:mat='Board'
 if i in [37,38,47,48,58,59,72,73]:mat='Lens'
 if i==8:mat='Rubber'
 o=mesh(f'{named.get(i,col[3:])} | source {i:03d}',a['verts'],a['polys'],col,mat);o['source_component']=i
 manifest.append({'component':i,'object':o.name,'policy':'source vertex coordinates retained; normals corrected'})

def at_origin(o,origin):
 p=Vector(origin)*S;o.data.transform(Matrix.Translation(-p));o.location=p
def revolve(n,profile,col,mat,transform,segments=48):
 v=[transform((x,r*math.cos(t*2*math.pi/segments),r*math.sin(t*2*math.pi/segments))) for x,r in profile for t in range(segments)]
 f=[(j*segments+k,j*segments+(k+1)%segments,((j+1)%len(profile))*segments+(k+1)%segments,((j+1)%len(profile))*segments+k) for j in range(len(profile)) for k in range(segments)]
 return mesh(n,v,f,col,mat)
wheelreports=[]
def wheel(name,idx,spare=False):
 a=A[idx];lo,hi=Vector(a['min']),Vector(a['max']);c=(lo+hi)/2
 axis=1 if spare else 0;sign=1 if spare else (1 if c.x>0 else -1)
 r=((hi.x-lo.x)+(hi.z-lo.z))/4 if spare else ((hi.y-lo.y)+(hi.z-lo.z))/4
 width=hi[axis]-lo[axis];h=width/2
 def xf(p):
  x,y,z=p
  return c+Vector((y,x,z)) if spare else c+Vector((sign*x,y,z))
 col='04 Spare wheel' if spare else '03 Road wheels'
 hub=bpy.data.objects.new('Wheel pivot | '+name,None);cols[col].objects.link(hub);hub.parent=root;hub.location=c*S;hub.empty_display_size=.10;hub['axle']='Y' if spare else 'X'
 start=len(objects)
 p=[(-h*.79,r*.49),(-h*.98,r*.60),(-h,r*.72),(-h*.93,r*.86),(-h*.72,r*.961),(0,r*.97),(h*.72,r*.961),(h*.93,r*.86),(h,r*.72),(h*.98,r*.60),(h*.79,r*.49),(h*.65,r*.47),(-h*.65,r*.47)]
 tyre=revolve(name+' | tyre carcass',p,col,'Rubber',xf,64)
 # Tread is a closed chamfered wedge, with roots inside the carcass.
 verts=[];faces=[];rows=[(-.68,-.25),(-.22,.22),(.25,.68)]
 for station in range(36):
  for row,(xa,xb) in enumerate(rows):
   angle=2*math.pi*(station+(row%2)*.5)/36;half=math.pi/36*.77
   y0,y1=angle-half,angle+half;bottom=r*.948;top=r
   a0,a1=h*xa,h*xb;ch=(a1-a0)*.13;ct=half*.15
   profile=[(a0,y0+ct),(a0+ch,y0),(a1-ch,y0),(a1,y0+ct),(a1,y1-ct),(a1-ch,y1),(a0+ch,y1),(a0,y1-ct)]
   k=len(verts)
   for rr in [bottom,top]:verts.extend(xf((x,rr*math.cos(t),rr*math.sin(t))) for x,t in profile)
   faces += [tuple(k+i for i in reversed(range(8))),tuple(k+8+i for i in range(8))]+[(k+i,k+(i+1)%8,k+8+(i+1)%8,k+8+i) for i in range(8)]
 mesh(name+' | all-terrain tread',verts,faces,col,'Rubber',weighted=False)
 rim=revolve(name+' | rolled rim and barrel',[(-h*.79,r*.482),(-h*.79,r*.508),(-h*.70,r*.529),(-h*.63,r*.508),(h*.65,r*.508),(h*.72,r*.535),(h*.82,r*.525),(h*.84,r*.487),(h*.74,r*.466),(-h*.70,r*.466)],col,'Wheel',xf,64)
 # Dish with actual radial vent openings. A spoke annulus divided into six
 # sectors leaves six rounded rectangular vents, not black discs on a face.
 vv=[];ff=[]
 for sector in range(6):
  t=2*math.pi*sector/6;ang0=t-.19;ang1=t+.19
  outer=[];inner=[]
  for k in range(9):
   a=t-math.pi/6+k*math.pi/24;outer.append((h*.59,r*.475*math.cos(a),r*.475*math.sin(a)));inner.append((h*.48,r*.21*math.cos(a),r*.21*math.sin(a)))
  # outer and inner full rings are separate; bridges form broad curved spokes
  for ra,rb,x in [(r*.41,r*.48,h*.58),(r*.14,r*.24,h*.47)]:
   for k in range(8):
    a=t-math.pi/6+k*math.pi/24;b=a+math.pi/24;st=len(vv)
    vv += [xf((x,rr*math.cos(tt),rr*math.sin(tt))) for rr,tt in [(ra,a),(rb,a),(rb,b),(ra,b)]];ff.append(tuple(range(st,st+4)))
  st=len(vv);vv += [xf((x,rr*math.cos(tt),rr*math.sin(tt))) for x,rr,tt in [(h*.47,r*.235,ang0),(h*.58,r*.415,ang0),(h*.58,r*.415,ang1),(h*.47,r*.235,ang1)]];ff.append(tuple(range(st,st+4)))
 dish=mesh(name+' | vented dish',vv,ff,col,'Wheel');sol=dish.modifiers.new('Cast web thickness','SOLIDIFY');sol.thickness=.002*S;sol.offset=-1
 bevel=dish.modifiers.new('Vent edge rounding','BEVEL');bevel.width=.0006*S;bevel.segments=2
 revolve(name+' | hub',[(h*.4,0),(h*.4,r*.15),(h*.87,r*.15),(h*.92,r*.125),(h*.92,0)],col,'Metal',xf,24)
 # Recessed brake drum, clear of the tyre's inner envelope.
 revolve(name+' | brake drum',[(-h*.25,0),(-h*.25,r*.425),(h*.22,r*.425),(h*.22,0)],col,'Metal',xf,32)
 for k in range(6):
  ang=2*math.pi*k/6;off=Vector((0,r*.205*math.cos(ang),r*.205*math.sin(ang)))
  revolve(name+f' | lug {k+1}',[(h*.52,0),(h*.52,r*.034),(h*.66,r*.034),(h*.66,0)],col,'Wheel',lambda p:xf(Vector(p)+off),6)
 for o in objects[start:]:
  at_origin(o,c);o.parent=hub;o.location=(0,0,0)
 wheelreports.append({'name':name,'source_component':idx,'center_raw':list(c),'radius_raw':r,'width_raw':width,'outside_rim_below_tyre_mm':(h-h*.84)*S*1000,'source_bounds':[list(lo),list(hi)]})
for name,i in [('Front left',2),('Front right',3),('Rear right',4),('Rear left',5)]:wheel(name,i)
wheel('Rear spare',1,True)

# Preserve exact imported source separately, at the same working scale.
bpy.ops.import_scene.gltf(filepath='C:/Users/mille/Downloads/pradotripo.glb')
refs=[o for o in bpy.context.selected_objects if o.type=='MESH']
for o in refs:
 for col in list(o.users_collection):col.objects.unlink(o)
 cols['90 Source reference'].objects.link(o);o.name='REFERENCE | original Tripo — unmodified';o.scale*=S;o.hide_render=True;o.hide_set(True);o.hide_select=True
cols['90 Source reference'].hide_render=True;cols['90 Source reference'].hide_viewport=True

sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('Neutral review');sc.world.color=(.12,.14,.16)
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';sh.show_specular_highlight=True
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='REVIEW';sc.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=200
for col in list(cam.users_collection):col.objects.unlink(cam)
cols['99 Review'].objects.link(cam)
def render(name,center,d,scale=1.2):
 center=Vector(center)*S;cam.location=center+Vector(d)*S;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*S;sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
for name,d in [('side',(3,0,0)),('opposite-side',(-3,0,0)),('front',(0,-3,0)),('rear',(0,3,0)),('quarter',(2,-3,1.1)),('rear-quarter',(-2,3,1.0)),('top',(0,0,3)),('underside',(1,-1,-2))]:render(name,(0,0,.27),d)
for c in ['03 Road wheels','04 Spare wheel','06 Roof rack and cargo','07 Side equipment']:cols[c].hide_render=True
render('body-wheel-off',(0,.0,.27),(3,0,.4),1.07)
for c in ['03 Road wheels','04 Spare wheel','06 Roof rack and cargo','07 Side equipment']:cols[c].hide_render=False
render('window-close',(0,-.1,.355),(2,-3,.7),.53)
render('rear-close',(0,.32,.27),(-2,3,.45),.65)
render('quarter',(0,0,.27),(2,-3,1.1))
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.color_type='MATERIAL';area.spaces.active.overlay.show_overlays=False
   rv=area.spaces.active.region_3d;rv.view_distance=7;rv.view_location=Vector((0,0,1.3));rv.view_rotation=cam.rotation_euler.to_quaternion()
report={'source_sha256':hashlib.sha256(Path('C:/Users/mille/Downloads/pradotripo.glb').read_bytes()).hexdigest(),'uniform_scale':S,'body_policy':'No vertex displacement; source glazing extracted with shared boundary coordinates','wheels':wheelreports,'source_components_replaced':sorted(skip-{0}),'retained_components':manifest,'status':'Exterior preparation, not game ready','remaining':['Detailed body topology and boundary review','Interior','UV and texture work','Wheel steering/suspension clearance','Rig, collision and LODs','Unreal validation']}
(OUT/'preparation-report.json').write_text(json.dumps(report,indent=2))
bpy.data.texts.new('README — Prado stage and limitations').write(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prado_Prepared.blend'))
print('SAVED',OUT,'meshes',len(objects))
