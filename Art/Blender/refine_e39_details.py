"""E39 exterior refinement; separate review asset, no Unreal writes.
Builds on the accepted continuous shell. Panel surfaces are extracted, not overlaid.
"""
from pathlib import Path
SOURCE=Path(__file__).with_name('refine_e39_shell.py')
source=SOURCE.read_text()
source=source.replace('if k==8 and u<-2.12:sideglass=False','if False:sideglass=False').replace('(F,.792)', '(F,.845)').replace('(F,.744)', '(F,.772)')
exec(compile(source[:source.index('# Neutral studio.')],str(SOURCE),'exec'),globals())
from mathutils.bvhtree import BVHTree
dark=material('Rubber and recessed seams',(.014,.017,.020),.78)
silver=material('Satin aluminium',(.34,.37,.39),.3)
lamp=material('Headlamp lens',(.55,.61,.65),.22)
red=material('Tail lamp red',(.22,.012,.009),.28)
amber=material('Indicator amber',(.50,.16,.018),.3)
white=material('Reversing lens',(.39,.43,.42),.32)
body.data.materials.append(dark)
for mod in list(body.modifiers):body.modifiers.remove(mod)
# Shape bumper crowns and lower returns in the common surface itself.
for ob in [body,bpy.data.objects['CONTROL_UncutSharedShell']]:
 bm=bmesh.new();bm.from_mesh(ob.data)
 for z in [.28,.36,.44,.50,.56,.61,.73]:
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,z),plane_no=(0,0,1))
 for v in bm.verts:
  u=-v.co.y;z=v.co.z
  if u>2.05:
   delta=interp(z,[(.215,-.055),(.28,-.025),(.36,-.005),(.47,0),(.52,-.004),(.55,-.018),(.62,-.028),(.74,-.025),(.9,0)])
   v.co.y-=delta*min(1,(u-2.05)/.22)
  if u<-2.38:
   delta=interp(z,[(.215,-.06),(.33,-.015),(.48,0),(.57,-.018),(.8,-.024),(.95,0)])
   v.co.y+=delta*min(1,(-u-2.38)/.155)
 bm.to_mesh(ob.data);bm.free();ob.data.update()
panel_objects=[];panel_report={}
def partition_panels():
 # Bisect shared faces first: every moving panel inherits the same surface.
 bm=bmesh.new();bm.from_mesh(body.data)
 for co,no in [((0,-u,0),(0,1,0)) for u in [.83,-1.98]]+[((x,0,0),(1,0,0)) for x in [-.72,.72]]+[((0,0,z),(0,0,1)) for z in [.33,.56,.965]]:
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=no)
 # Above the belt, seams follow the pillar angles rather than slicing glass.
 for u,slope in [(.83,-1.55),(-.365,-.20),(-1.20,.35)]:
  for v in bm.verts:v.co.y+=slope*max(0,v.co.z-.965)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,-u,0),plane_no=(0,1,0))
  for v in bm.verts:v.co.y-=slope*max(0,v.co.z-.965)
 # Tailgate perimeter widens below the rear glass, following the rear pillars.
 for v in bm.verts:v.co.x/=max(.62,.80-.40*max(0,v.co.z-.965))
 for x in [-1,1]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(x,0,0),plane_no=(1,0,0))
 for v in bm.verts:v.co.x*=max(.62,.80-.40*max(0,v.co.z-.965))
 bm.normal_update()
 groups={n:[] for n in ['Bonnet','Door_FL','Door_FR','Door_RL','Door_RR','Tailgate']}
 for f in bm.faces:
  c=f.calc_center_median();u=-c.y;v=c.x;z=c.z
  side='L' if v>0 else 'R'
  if .831<u and abs(v)<.719 and f.normal.z>.65:groups['Bonnet'].append(f)
  elif u+.20*max(0,z-.965)>-.3649 and u+1.55*max(0,z-.965)<.8299 and z>.331 and abs(v)>.60 and abs(f.normal.x)>.55:groups['Door_F'+side].append(f)
  elif u-.35*max(0,z-.965)>-1.1999 and u+.20*max(0,z-.965)<-.3651 and z>.331 and abs(v)>.60 and abs(f.normal.x)>.55:groups['Door_R'+side].append(f)
  elif u<-1.981 and abs(v)<max(.62,.80-.40*max(0,z-.965))-.0001 and z>.561 and f.normal.y>.4:groups['Tailgate'].append(f)
 
 for name,fs in groups.items():
  if not fs:raise RuntimeError('Empty panel '+name)
  # The 3mm perimeter remains on the shell as a recessed dark reveal.
  result=bmesh.ops.inset_region(bm,faces=fs,thickness=.003,depth=0,use_even_offset=True,use_boundary=True)
  for f in result['faces']:f.material_index=2
  verts=list({v for f in fs for v in f.verts});lookup={v:i for i,v in enumerate(verts)}
  me=bpy.data.meshes.new(name+'_SharedSurface');me.from_pydata([v.co.copy() for v in verts],[],[[lookup[v] for v in f.verts] for f in fs]);me.update()
  for m in body.data.materials:me.materials.append(m)
  for p,f in zip(me.polygons,fs):p.material_index=f.material_index;p.use_smooth=True
  ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);panel_objects.append(ob)
  ob['Construction']='Faces extracted from continuous body; 3mm shared perimeter reveal'
  panel_report[name]={'faces':len(fs),'nominal_reveal_mm':3.0}
  bmesh.ops.delete(bm,geom=fs,context='FACES_ONLY')
  # Delete vertices no longer used by the fixed shell.
  loose=[v for v in bm.verts if not v.link_faces]
  if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bm.to_mesh(body.data);bm.free();body.data.update()

def mesh_obj(name,verts,faces,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 return ob

def tube(name,points,r,mat):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r;cu.bevel_resolution=1
 sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
 for p,v in zip(sp.points,points):p.co=(*v,1)
 ob=bpy.data.objects.new(name,cu);scene.collection.objects.link(ob);cu.materials.append(mat);return ob

# Sample the complete control surface (without cut seams) for fitted components.
control=bpy.data.objects['CONTROL_UncutSharedShell']
bvh=BVHTree.FromPolygons([v.co for v in control.data.vertices],[list(p.vertices) for p in control.data.polygons])
def surface(end,v,z,offset=0):
 direction=Vector((0,1 if end=='front' else -1,0))
 hit,normal,_,_=bvh.ray_cast(Vector((v,-8 if end=='front' else 8,z)),direction)
 if hit is None:raise RuntimeError('Surface miss '+str((end,v,z)))
 return hit-direction*offset

def outline(cx,cz,w,h,r=.018):
 out=[]
 for x,z,a in [(cx+w/2-r,cz+h/2-r,0),(cx-w/2+r,cz+h/2-r,90),(cx-w/2+r,cz-h/2+r,180),(cx+w/2-r,cz-h/2+r,270)]:
  for i in range(4):
   t=math.radians(a+i*30);out.append((x+r*math.cos(t),z+r*math.sin(t)))
 return out

def recess(name,end,poly,depth=.025):
 # Cutter follows the actual shell and removes its underlying faces.
 pts=[surface(end,x,z) for x,z in poly];sgn=-1 if end=='front' else 1
 outer=sgn*max(sgn*p.y for p in pts)+sgn*.02
 inner=sgn*min(sgn*p.y for p in pts)-sgn*depth
 front=[Vector((x,outer,z)) for x,z in poly];back=[Vector((x,inner,z)) for x,z in poly];n=len(poly)
 cut=mesh_obj(name+'_CUT',front+back,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],dark)
 for target in [body]+panel_objects:
  bpy.context.view_layer.objects.active=target
  mod=target.modifiers.new(name+' recess','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
  bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cut,do_unlink=True)
 # Shallow interior tray, with edges flush to the shell.
 verts=[surface(end,x,z,.0005) for x,z in poly]+[surface(end,x,z,-depth+.001) for x,z in poly]
 ob=mesh_obj(name+'_Housing',verts,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],dark)
 face_patch(name+'_Backing',end,poly,dark,-depth+.001)
 return ob

def ring(name,end,poly,width,mat,offset=.0015):
 cx=sum(p[0] for p in poly)/len(poly);cz=sum(p[1] for p in poly)/len(poly)
 # Perimeter ring is a mesh strip, not a thick intersecting tube.
 inner=[]
 for x,z in poly:
  dx=x-cx;dz=z-cz;s=max(abs(dx),abs(dz),.001)
  inner.append((x-width*dx/s,z-width*dz/s))
 n=len(poly);ob=mesh_obj(name,[Vector((x,0,z)) for x,z in poly+inner],[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=10 if end=='rear' else 4,use_grid_fill=True)
 for v in bm.verts:v.co=surface(end,v.co.x,v.co.z,offset)
 bm.to_mesh(ob.data);bm.free();return ob

def face_patch(name,end,poly,mat,offset=.001):
 # Tessellate in projection then conform every vertex, avoiding nonplanar caps.
 ob=mesh_obj(name,[Vector((x,0,z)) for x,z in poly],[tuple(range(len(poly)))],mat)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
 bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=10 if end=='rear' else 4,use_grid_fill=True)
 for v in bm.verts:v.co=surface(end,v.co.x,v.co.z,offset)
 bm.to_mesh(ob.data);bm.free();return ob

for s,side in [(1,'L'),(-1,'R')]:
 p=outline(s*.516,.641,.435,.145,.025)
 recess('Headlight_'+side,'front',p,.03);ring('Headlight gasket '+side,'front',p,.009,dark)
 for k,v in enumerate([s*.384,s*.542]):
  circle=[(v+.057*math.cos(a*math.tau/20),.641+.057*math.sin(a*math.tau/20)) for a in range(20)]
  ring('Reflector '+side+str(k),'front',circle,.010,silver,-.012)
  face_patch('Lens '+side+str(k),'front',[(v+.043*math.cos(a*math.tau/20),.641+.043*math.sin(a*math.tau/20)) for a in range(20)],lamp,-.008)
 face_patch('Front indicator '+side,'front',outline(s*.685,.644,.055,.098,.012),amber,-.007)
 kidney=outline(s*.127,.642,.208,.158,.024)
 recess('Kidney_'+side,'front',kidney,.028);ring('Kidney surround '+side,'front',kidney,.012,silver,.002)
 for v in [-.067,-.034,0,.034,.067]:
  face_patch('Grille slat '+side+str(v),'front',outline(s*.127+v,.642,.006,.127,.002),silver,-.004)
 # Rear lamps follow the sloping upper tail surface.
 tail=outline(s*.625,.876,.31,.16,.024)
 recess('TailLight_'+side,'rear',tail,.018);ring('TailLight gasket '+side,'rear',tail,.006,dark)
 face_patch('TailLight red '+side,'rear',outline(s*.625,.899,.291,.094,.015),red,.002)
 face_patch('TailLight reverse '+side,'rear',outline(s*.625,.823,.286,.032,.007),white,.002)
 # Simple side mirrors and handles have explicit mounting stems.
 u=.68;z=1.025
 mount,_,_,_=bvh.ray_cast(P((u,s*3,z)),Vector((-s,0,0)))
 v=mount.x
 tube('Mirror mount '+side,[mount-Vector((s*.006,0,0)),P((u-.018,v+s*.09,z+.006))],.016,dark)
 bpy.ops.mesh.primitive_cube_add(size=1,location=P((u-.035,v+s*.137,z+.024)))
 ob=bpy.context.object;ob.name='Mirror '+side;ob.dimensions=(.14,.19,.10);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(clay)
 be=ob.modifiers.new('Mirror corners','BEVEL');be.width=.023;be.segments=2
 for label,u in [('F',-.22),('R',-1.03)]:
  vv=s*(interp(u,widths)-.01)
  tube('Handle '+label+side,[P((u-.075,vv,.902)),P((u-.055,vv+s*.013,.914)),P((u+.055,vv+s*.013,.914)),P((u+.075,vv,.902))],.008,clay)

# Bumper rubbing strips follow the continuous shell all around the car.
for end,z in [('front',.518),('rear',.555)]:
 p=outline(0,z,1.56,.041,.014);face_patch(end+' bumper rubbing strip',end,p,dark,.002)
# Intake and number plate recess are cut into the surface.
intake=outline(0,.377,.87,.105,.022);recess('Lower intake','front',intake,.024);ring('Intake edge','front',intake,.006,clay)
for z in [.358,.389]:face_patch('Intake horizontal vane '+str(z),'front',outline(0,z,.815,.006,.002),dark,-.006)
for s in [-1,1]:
 fog=outline(s*.627,.385,.154,.084,.018);recess('Fog pocket '+str(s),'front',fog,.021)
 face_patch('Fog lens '+str(s),'front',outline(s*.627,.385,.112,.057,.013),lamp,-.007)
plate=outline(0,.747,.46,.115,.017);recess('Rear plate recess','rear',plate,.022)
face_patch('Rear number plate','rear',outline(0,.742,.39,.073,.007),silver,-.014)
face_patch('Tailgate handle','rear',outline(0,.848,.22,.022,.007),dark,.002)
for side in [-1,1]:
 for a,b in [(-2.35,-1.81),(-1.015,1.015),(1.81,2.1)]:
  points=[P((u,side*(interp(u,widths)+.002),.536)) for u in [a+(b-a)*i/12 for i in range(13)]]
  tube('Side rubbing strip',points,.013,dark)

partition_panels()

# Surface thickness goes inward. The visible panel surfaces remain the shared ones.
for ob in [body]+panel_objects:
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for e in bm.edges:
  if len(e.link_faces)==2 and e.calc_face_angle()>math.radians(38):e.smooth=False
 bm.to_mesh(ob.data);bm.free()
 for p in ob.data.polygons:p.use_smooth=True
 if ob.name=='Tailgate':
  # Preserve deliberate planar tail sections instead of smoothing across recesses.
  for p in ob.data.polygons:p.use_smooth=False
 else:
  wn=ob.modifiers.new('Area weighted surface normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50
 so=ob.modifiers.new('Inward skin thickness','SOLIDIFY');so.thickness=.003;so.offset=-1
 so.material_offset_rim=2
 ob['Stage']='Exterior detail review; no UVs, interior or moving-part rig yet'

# Reuse the verified studio and views, omitting its obsolete shape-only report.
studio=source[source.index('# Neutral studio.'):source.index("view('three_quarter')\n# Pack")]
exec(compile(studio,str(SOURCE),'exec'),globals())
view('three_quarter')
notes=bpy.data.texts.new('READ_ME_ExteriorRefinement')
notes.write('Revision '+args.revision+'; actual Blender exterior refinement.\nBonnet, four door skins and tailgate extracted from the common shell. 3mm nominal reveals.\nRecessed lamps/grilles conform to the control surface. No duplicate body skins beneath panels.\nThis is an exterior review: wheel placeholders, no cabin, UVs, rig or game import.\n')
reference=ROOT/'Art/References/Vehicles/E39Refinement/BMW_dimensions_page200.png'
if reference.exists():bpy.data.images.load(str(reference)).pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'E39_ExteriorStudy.blend'))
report={'revision':args.revision,'stage':'EXTERIOR_DETAIL_REVIEW','panels':panel_report,'limitations':['No interior, UVs, rig or Unreal validation','Wheel placeholders','Panel gaps nominal; full hinge travel not validated'],'objects':{}}
for ob in [body]+panel_objects:
 bm=bmesh.new();bm.from_mesh(ob.data)
 report['objects'][ob.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'loose_vertices':sum(not v.link_faces for v in bm.verts),'wire_edges':sum(e.is_wire for e in bm.edges),'open_skin_edges':sum(e.is_boundary for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces)}
 bm.free()
(OUT/'exterior_check.json').write_text(json.dumps(report,indent=2))
(OUT/'refine_e39_details.py').write_text(Path(__file__).read_text())
(OUT/'refine_e39_shell.py').write_text(SOURCE.read_text())
for name in args.views.split(','):
 view(name);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('E39_EXTERIOR_REVIEW_SAVED '+str(OUT),flush=True)
