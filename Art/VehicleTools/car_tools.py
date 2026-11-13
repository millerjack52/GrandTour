"""Editable stylized-car construction primitives. Blender Python, metres, front -Y.

Supports a front module and an optional whole-estate shape study. Never clears a scene on import.
Generated components have ownership and edit fingerprints; rebuilds are staged.
"""
import bpy, bmesh, json, math, hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path

OWNER='GT_CAR_TOOLS_V1'
PARTS={'body','wheels','cabin','fittings'}
DEPENDENCIES={
 'wheels':{'front_axle_u','track','wheel_radius','wheel_width'},
 'body':{'front_u','section_end_u','front_axle_u','scuttle_u','width','wheel_radius','arch_clearance','sill_z','nose_z','scuttle_z','gap','skin'},
 'cabin':{'scuttle_u','section_end_u','roof_front_u','width','scuttle_z','roof_z','roof_half_width','skin'},
 'fittings':{'front_u','width','nose_z','scuttle_u','scuttle_z','roof_z','roof_half_width'},
}
SHAPE_KEYS={'rear_axle_u','roof_rear_u','b_pillar_u','c_pillar_u','shape_study'}
TAPER_KEYS={'nose_width_ratio','tail_width_ratio'}

def P(u,v,z):return Vector((v,-u,z))

def validate_spec(s):
 if s.get('schema')!=1 or s.get('units')!='metres':raise ValueError('Unsupported specification')
 numeric=set().union(*DEPENDENCIES.values())
 for key in numeric:
  if not isinstance(s.get(key),(int,float)) or not math.isfinite(s[key]):raise ValueError('Invalid '+key)
 if not s['section_end_u']<s['roof_front_u']<s['scuttle_u']<s['front_axle_u']<s['front_u']:raise ValueError('Invalid longitudinal landmarks')
 if not 0.002<=s['gap']<=0.008 or not 0.001<=s['skin']<=0.01:raise ValueError('Gap/skin outside prototype range')
 if not .28<=s['wheel_radius']<=.35:raise ValueError('Wheel radius outside tested template range')
 if s['track']/2+s['wheel_width']/2>s['width']/2+.01:raise ValueError('Tyres protrude through fenders')
 if s['roof_half_width']>=s['width']/2-.10:raise ValueError('Cabin needs a narrower roof')
 if hood_z(s,s['front_axle_u'])-.075 < 2*s['wheel_radius']+s['arch_clearance']+.035:raise ValueError('Insufficient material above wheel opening')
 if s.get('shape_study'):
  for key in SHAPE_KEYS-{'shape_study'}:
   if not isinstance(s.get(key),(int,float)) or not math.isfinite(s[key]):raise ValueError('Invalid '+key)
  if not s['section_end_u']<s['roof_rear_u']<s['rear_axle_u']<s['c_pillar_u']<s['b_pillar_u']<s['roof_front_u']:raise ValueError('Invalid estate landmarks')
 for key in TAPER_KEYS:
  if key in s and not .80<=s[key]<=1:raise ValueError('Taper outside supported range: '+key)

def width_ratio(s,u):
 """Shared plan-view envelope: full cabin, narrowing shoulders, clipped nose corners."""
 if not s.get('shape_study'):return 1.0
 nose=s.get('nose_width_ratio',1.0);tail=s.get('tail_width_ratio',1.0)
 knots=[(s['section_end_u'],tail),(s['rear_axle_u'],1.0),(s['scuttle_u'],1.0),
        (s['front_axle_u'],1-(1-nose)*.16),(s['front_u']-.16,1-(1-nose)*.62),(s['front_u'],nose)]
 if u<=knots[0][0]:return tail
 for (a,x),(b,y) in zip(knots,knots[1:]):
  if u<=b:return x+(y-x)*(u-a)/(b-a)
 return nose

def apply_envelope(s,ob):
 if ob['gt_part']=='wheels':return
 if s.get('coachwork_profile'):
  from coachwork import apply
  apply(s,ob);return
 if s.get('shape_study') and (s.get('nose_width_ratio',1)!=1 or s.get('tail_width_ratio',1)!=1):
  # Every adjoining surface crosses the same taper stations, including long glass edges.
  bm=bmesh.new();bm.from_mesh(ob.data)
  for u in [s['rear_axle_u'],s['scuttle_u'],s['front_axle_u'],s['front_u']-.16,s['front_u']]:
   if min(v.co.y for v in bm.verts)+1e-6 < -u < max(v.co.y for v in bm.verts)-1e-6:
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,-u,0),plane_no=(0,1,0))
  bm.to_mesh(ob.data);bm.free()
 for v in ob.data.vertices:v.co.x*=width_ratio(s,-v.co.y)
 ob.data.update()

def hood_z(s,u):
 t=max(0,min(1,(u-s['scuttle_u'])/(s['front_u']-s['scuttle_u'])))
 return s['scuttle_z']*(1-t)+s['nose_z']*t

def arch_z(s,u):
 r=s['wheel_radius']+s['arch_clearance'];q=min(abs(u-a) for a in axles(s))/r
 if q>1:return s['sill_z']
 if q<=.55:h=r
 elif q<=.85:h=r*(1-(q-.55)*.32/.30)
 else:h=r*(.68-(q-.85)*.68/.15)
 return max(s['sill_z'],s['wheel_radius']+h)

def axles(s):return [s['front_axle_u']]+([s['rear_axle_u']] if s.get('shape_study') else [])

def mat(name,color,rough=.75):
 name='GTCT_'+name;m=bpy.data.materials.get(name)
 if m:return m
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
 return m

def palette():
 return [mat('Terracotta',(.48,.145,.045)),mat('Charcoal',(.027,.035,.042)),mat('Glass',(.085,.16,.19),.35),mat('Hub',(.23,.27,.29)),mat('CreamLamp',(.71,.65,.43)),mat('Amber',(.69,.30,.025))]

def mesh(name,verts,faces,collection,material,part):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);collection.objects.link(ob);me.materials.append(material)
 ob['gt_owner']=OWNER;ob['gt_part']=part;ob['gt_role']=name
 return ob

def skin(ob,thickness):
 mod=ob.modifiers.new('Inward skin','SOLIDIFY');mod.thickness=thickness;mod.offset=-1

def box(name,center,size,coll,material,part,bevel=0):
 c=Vector(center);dx,dy,dz=[v/2 for v in size]
 vs=[c+Vector((x,y,z)) for x,y,z in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]]
 ob=mesh(name,vs,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],coll,material,part)
 if bevel:
  mod=ob.modifiers.new('Deliberate chamfer','BEVEL');mod.width=bevel;mod.segments=1
 return ob

def extract_panel(shell,face_ids,name,coll,s):
 """Extract actual source faces. Perimeter ring stays on fixed shell as a reveal."""
 if not face_ids:raise ValueError('No source faces for '+name)
 bm=bmesh.new();bm.from_mesh(shell.data);bm.faces.ensure_lookup_table()
 faces=[bm.faces[i] for i in face_ids]
 result=bmesh.ops.inset_region(bm,faces=faces,thickness=s['gap'],depth=0,use_even_offset=True,use_boundary=True)
 for f in result['faces']:f.material_index=1
 bm.verts.index_update()
 verts=sorted({v for f in faces for v in f.verts},key=lambda v:v.index);ids={v:i for i,v in enumerate(verts)}
 ob=mesh(name,[v.co.copy() for v in verts],[[ids[v] for v in f.verts] for f in faces],coll,shell.data.materials[0],'body')
 ob['gt_source']='Shared body surface';ob['gt_gap_m']=s['gap'];skin(ob,s['skin'])
 bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY')
 loose_edges=[e for e in bm.edges if not e.link_faces]
 if loose_edges:bmesh.ops.delete(bm,geom=loose_edges,context='EDGES')
 unused=[v for v in bm.verts if not v.link_faces]
 if unused:bmesh.ops.delete(bm,geom=unused,context='VERTS')
 bm.to_mesh(shell.data);bm.free();shell.data.update();return ob

def build_body(s,c,m):
 w=s['width']/2;r=s['wheel_radius']+s['arch_clearance'];ax=s['front_axle_u']
 us=sorted(set([s['section_end_u'],s['scuttle_u'],s['front_u']]+[a+r*q for a in axles(s) for q in [-1,-.85,-.55,0,.55,.85,1]]+([s['b_pillar_u'],s['c_pillar_u']] if s.get('shape_study') else [])+([s['front_u']-.16] if s.get('nose_width_ratio',1)!=1 else [])))
 vs=[];faces=[]
 # Shared cross-sections: centre underside -> wheel-well inner wall -> arch lip
 # -> flank -> shoulder -> bonnet. Mirrored vertices close the other side.
 for u in us:
  h=hood_z(s,u);a=arch_z(s,u)
  shoulder_drop=.018*max(0,min(1,(u-s['scuttle_u'])/(s['front_u']-s['scuttle_u'])))
  q=min(abs(u-a) for a in axles(s))/r
  lip=.05*max(0,min(1,(1-q)/.15))
  half=[(0,s['sill_z']),(.52,s['sill_z']),(.56,a),(w-.045,a),(w+lip*.5,a+.012),(w,a+.012+lip),(w,h-.07),(w-.065,h-shoulder_drop),(w-.145,h),(0,h)]
  section=half+[(-v,z) for v,z in half[-2:0:-1]]
  vs.extend(P(u,v,z) for v,z in section)
 n=len(section)
 for i in range(len(us)-1):
  for j in range(n):faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
 faces.extend([tuple(range(n-1,-1,-1)),tuple((len(us)-1)*n+j for j in range(n))])
 body=mesh('FixedBody',vs,faces,c,m[0],'body');body.data.materials.append(m[1])
 # Boolean aperture tools are confined to the broad planar nose, while still closed.
 for sign in ([0] if s.get('shape_study') else [-1,1]):
  center=sign*(w*.65)
  size=(s['width']-.12,.085,.218) if s.get('shape_study') else (.42,.085,.135)
  cutter=box('ApertureTool',P(s['front_u']-.01,center,s['nose_z']-(.134 if s.get('shape_study') else .105)),size,c,m[1],'body')
  bpy.context.view_layer.objects.active=body
  mod=body.modifiers.new('Headlamp opening','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE';mod.solver='EXACT'
  bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
 # Locate faces geometrically after apertures. Extraction consumes them, so recalc IDs.
 ids=[p.index for p in body.data.polygons if -p.center.y>s['scuttle_u']+.0001 and p.normal.z>.7 and abs(p.center.x)<w-.14]
 extract_panel(body,ids,'Bonnet',c,s)
 for sign,label in [(1,'L'),(-1,'R')]:
  ids=[p.index for p in body.data.polygons if p.material_index==0 and s.get('b_pillar_u',s['section_end_u'])< -p.center.y<s['scuttle_u']-.0001 and p.normal.x*sign>.9 and p.center.z>s['sill_z']+.012 and all(abs(body.data.vertices[i].co.x-sign*w)<1e-5 for i in p.vertices)]
  extract_panel(body,ids,'DoorSkin_'+label,c,s)
  if s.get('shape_study'):
   ids=[p.index for p in body.data.polygons if p.material_index==0 and s['c_pillar_u']< -p.center.y<s['b_pillar_u']-.0001 and p.normal.x*sign>.9 and p.center.z>s['sill_z']+.012 and all(abs(body.data.vertices[i].co.x-sign*w)<1e-5 for i in p.vertices)]
   extract_panel(body,ids,'RearDoorSkin_'+label,c,s)
 skin(body,s['skin'])
 body['gt_arch_peak_m']=2*s['wheel_radius']+s['arch_clearance']

def wheel(name,center,r,width,c,m):
 # One welded tyre/rim profile, no co-located disks or overlapping cylinders.
 rings=[(.010,.24*r),(0,.29*r),(0,.57*r),(.005,.65*r),(-.015,.92*r),(-width*.22,r),(-width*.78,r),(-width+.015,.92*r),(-width,.65*r),(-width,.18*r)]
 sign=1 if center.x>0 else -1;vs=[]
 for x,rr in rings:
  vs.extend(center+Vector((sign*(width/2+x),rr*math.cos(i*math.tau/16),rr*math.sin(i*math.tau/16))) for i in range(16))
 fs=[]
 for j in range(len(rings)-1):
  for i in range(16):fs.append((j*16+i,j*16+(i+1)%16,(j+1)*16+(i+1)%16,(j+1)*16+i))
 fs.extend([tuple(range(15,-1,-1)),tuple((len(rings)-1)*16+i for i in range(16))])
 ob=mesh(name,vs,fs,c,m[1],'wheels');ob.data.materials.append(m[3])
 for p in ob.data.polygons:p.material_index=1 if p.index<48 or p.index>=len(fs)-2 else 0
 return ob

def build_wheels(s,c,m):
 for sign,label in [(1,'L'),(-1,'R')]:wheel('Wheel_'+label,P(s['front_axle_u'],sign*s['track']/2,s['wheel_radius']),s['wheel_radius'],s['wheel_width'],c,m)
 if s.get('shape_study'):
  for sign,label in [(1,'L'),(-1,'R')]:wheel('RearWheel_'+label,P(s['rear_axle_u'],sign*s['track']/2,s['wheel_radius']),s['wheel_radius'],s['wheel_width'],c,m)

def framed(name,pts,c,m,s):
 # A single inset operation constructs the frame and glazing boundary together.
 ob=mesh(name,pts,[tuple(range(len(pts)))],c,m[0],'cabin');ob.data.materials.append(m[2])
 bm=bmesh.new();bm.from_mesh(ob.data);original=list(bm.faces)
 bmesh.ops.inset_region(bm,faces=original,thickness=.043,depth=0,use_even_offset=True,use_boundary=True)
 for f in original:f.material_index=1
 bm.to_mesh(ob.data);bm.free();skin(ob,s['skin'])

def build_cabin(s,c,m):
 u=s['scuttle_u'];r=s['roof_front_u'];back=s['section_end_u'];lo=s['scuttle_z'];hi=s['roof_z'];w=s['width']/2-.065;rw=s['roof_half_width']
 framed('Windscreen',[P(u,w,lo),P(u,-w,lo),P(r,-rw,hi),P(r,rw,hi)],c,m,s)
 if s.get('shape_study'):
  b=s['b_pillar_u'];cc=s['c_pillar_u'];tail=back;back=s['roof_rear_u']
  for sign,label in [(1,'L'),(-1,'R')]:
   framed('DoorWindow_'+label,[P(b,sign*w,lo),P(u,sign*w,lo),P(r,sign*rw,hi),P(b,sign*rw,hi)],c,m,s)
   framed('RearDoorWindow_'+label,[P(cc,sign*w,lo),P(b,sign*w,lo),P(b,sign*rw,hi),P(cc,sign*rw,hi)],c,m,s)
   framed('CargoWindow_'+label,[P(tail,sign*w,lo),P(cc,sign*w,lo),P(cc,sign*rw,hi),P(back,sign*rw,hi)],c,m,s)
  framed('RearWindow',[P(tail,-w,lo),P(tail,w,lo),P(back,rw,hi),P(back,-rw,hi)],c,m,s)
 else:
  for sign,label in [(1,'L'),(-1,'R')]:framed('DoorWindow_'+label,[P(back,sign*w,lo),P(u,sign*w,lo),P(r,sign*rw,hi),P(back,sign*rw,hi)],c,m,s)
 roof=mesh('RoofSection',[P(back,rw,hi),P(r,rw,hi),P(r,-rw,hi),P(back,-rw,hi)],[(0,1,2,3)],c,m[0],'cabin');skin(roof,s['skin'])

def build_fittings(s,c,m):
 F=s['front_u'];w=s['width']/2;z=s['nose_z']-.105
 if s.get('shape_study'):
  z=s['nose_z']-.134
  box('NoseRecess',P(F-.037,0,z),(s['width']-.126,.023,.212),c,m[1],'fittings')
 if s.get('shape_study'):
  outline=[(-w+.025,F+.122),(w-.025,F+.122),(w+.025,F+.072),(w+.025,F-.26),(w-.025,F-.26),(w-.025,F-.098),(-w+.025,F-.098),(-w+.025,F-.26),(-w-.025,F-.26),(-w-.025,F+.072)]
  vs=[P(u,v,z) for z in [.345,.575] for v,u in outline];nn=len(outline)
  faces=[tuple(range(nn-1,-1,-1)),tuple(range(nn,2*nn))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
  bumper=mesh('Bumper',vs,faces,c,m[1],'fittings')
  bevel=bumper.modifiers.new('Connected bumper chamfer','BEVEL');bevel.width=.010;bevel.segments=1
 else:bumper=box('Bumper',P(F+.012,0,.46),(s['width']+.025,.22,.23),c,m[1],'fittings',.028)
 bumper['gt_mount_overlap']='FixedBody: bumper attachment'
 for sign,label in [(1,'L'),(-1,'R')]:
  shaped=s.get('shape_study',False);center=sign*w*.65
  if not shaped:box('LampTray_'+label,P(F-.031,center,z),(.413,.025,.128),c,m[1],'fittings')
  for i,d in enumerate([-.092,.092]):box('Lamp_'+label+str(i),P(F-.012,center+d,z),(.172,.013,.18 if shaped else .103),c,m[4],'fittings',.006)
  box('Indicator_'+label,P(F-.012 if shaped else F+.004,sign*(w-.105 if shaped else w-.043),z),(.052 if shaped else .07,.013 if shaped else .018,.18 if shaped else .136),c,m[5],'fittings',.003 if shaped else 0)
  kw=.292 if shaped else .224;kh=.212 if shaped else .146;kc=.158 if shaped else .132
  box('Kidney_'+label,P(F+.001,sign*kc,z),(kw,.030,kh),c,m[3],'fittings',.009)
  box('Grille_'+label,P(F+.018,sign*kc,z),(kw-.026,.010,kh-.023),c,m[1],'fittings',.005)
  for i in range(6):box('GrilleBar_'+label+str(i),P(F+.025,sign*kc-(kw-.06)/2+i*(kw-.06)/5,z),(.009,.009,kh-.041),c,m[3],'fittings')
  # Mirror base is fitted to the cabin at the same sampled height.
  u=s['scuttle_u']-.09;zz=s['scuttle_z']+.065
  surface_v=w-.065-(w-.065-s['roof_half_width'])*(.065/(s['roof_z']-s['scuttle_z']))
  mount=box('MirrorMount_'+label,P(u,sign*(surface_v+.020),zz),(.055,.075,.045),c,m[1],'fittings')
  mount['gt_mount_overlap']='DoorWindow_'+label+': mounting foot'
  box('Mirror_'+label,P(u-.02,sign*(surface_v+.088),zz+.020),(.12,.15,.10),c,m[1],'fittings',.007)
 if s.get('shape_study'):
  # Wrap bumper ends around the body; integrated low-detail silhouette fittings.
  for sign,label in [(1,'L'),(-1,'R')]:
   for name,uu in [('Front',s['b_pillar_u']+.14),('Rear',s['c_pillar_u']+.14)]:
    box(name+'Handle_'+label,P(uu,sign*(w+.006),s['scuttle_z']-.14),(.027,.14,.039),c,m[1],'fittings',.007)
   arch_radius=s['wheel_radius']+s['arch_clearance']
   trim_back=s['rear_axle_u']+arch_radius+.035;trim_front=s['front_axle_u']-arch_radius-.035
   trim=box('SillTrim_'+label,P((trim_front+trim_back)/2,sign*(w+.005),s['sill_z']+.021),(.026,trim_front-trim_back,.060),c,m[1],'fittings',.004)
   trim['gt_mount_overlap']='FixedBody: 8 mm trim backing attachment; ends clear wheel-arch feet'
   for i,material in enumerate([m[4],m[5],mat('TailRed',(.35,.025,.015))]):
    box('TailLamp_'+label+str(i),P(s['section_end_u']-.008,sign*(w-.10),.70+i*.075),(.12,.027,.068),c,material,'fittings')
  box('RearBumper',P(s['section_end_u']-.04,0,.46),(s['width']+.025,.22,.23),c,m[1],'fittings',.028)

def fingerprint(ob):
 dg=bpy.context.evaluated_depsgraph_get();eo=ob.evaluated_get(dg);me=eo.to_mesh()
 data={'v':[[round(float(x),7) for x in v.co] for v in me.vertices], 'f':[(list(p.vertices),p.material_index,p.use_smooth) for p in me.polygons], 'matrix':[round(float(x),7) for row in ob.matrix_world for x in row], 'materials':[m.name if m else None for m in me.materials]}
 eo.to_mesh_clear();return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

def owned():return [o for o in bpy.data.objects if o.get('gt_owner')==OWNER and o.type=='MESH']

def rebuild(s,parts=None):
 validate_spec(s)
 previous=json.loads(bpy.context.scene.get('gt_car_spec','{}'))
 changed={k for k in set(s)|set(previous) if previous.get(k)!=s.get(k)}
 affected={p for p,keys in DEPENDENCIES.items() if changed & keys}
 if changed & SHAPE_KEYS:affected|=PARTS
 if changed & TAPER_KEYS:affected|={'body','cabin','fittings'}
 if 'coachwork_profile' in changed:affected|={'body','cabin','fittings'}
 if s.get('coachwork_profile') and changed & set().union(*DEPENDENCIES.values(),SHAPE_KEYS):affected|={'body','cabin','fittings'}
 if s.get('shape_study') and changed & {'section_end_u','front_axle_u','sill_z','wheel_radius','arch_clearance'}:affected|={'fittings'}
 if (s.get('nose_width_ratio',1)!=1 or s.get('tail_width_ratio',1)!=1) and changed & {'front_u','scuttle_u','front_axle_u','section_end_u'}:affected|={'body','cabin','fittings'}
 selected=PARTS.copy() if not previous else affected | set(parts or [])
 if not selected<=PARTS:raise ValueError('Unknown component')
 if not selected:return []
 old=[o for o in owned() if o['gt_part'] in selected]
 edited=[o.name for o in old if o.get('gt_fingerprint')!=fingerprint(o)]
 if edited:raise RuntimeError('Manual edits preserved; rebuild refused for: '+', '.join(edited))
 coll=bpy.data.collections.new('GT_Car_Staging');bpy.context.scene.collection.children.link(coll)
 try:
  m=palette()
  for part in sorted(selected):globals()['build_'+part](s,coll,m)
  for ob in coll.objects:
   if ob.type=='MESH':
    apply_envelope(s,ob)
    ob['gt_fingerprint']=fingerprint(ob)
 except Exception:
  for ob in list(coll.objects):bpy.data.objects.remove(ob,do_unlink=True)
  bpy.data.collections.remove(coll);raise
 # No existing component is removed until all replacements have built successfully.
 for ob in old:bpy.data.objects.remove(ob,do_unlink=True)
 coll.name='GT_Car_'+('_'.join(sorted(selected)))
 for ob in coll.objects:ob.name=ob['gt_role']
 bpy.context.scene['gt_car_spec']=json.dumps(s,sort_keys=True)
 refresh_landmarks(s)
 return sorted(selected)

def setup_references(s,root):
 """Packed source board and named landmarks; guides, not live mesh handles."""
 if bpy.data.collections.get('GT_Car_References'):return
 c=bpy.data.collections.new('GT_Car_References');bpy.context.scene.collection.children.link(c)
 img=bpy.data.images.load(str(Path(root)/s['reference']),check_existing=True);img.pack()
 ob=bpy.data.objects.new('Approved_Orthographic_Board',None);c.objects.link(ob);ob.empty_display_type='IMAGE';ob.data=img;ob.empty_display_size=4.5;ob.location=(3.5,0,1.5);ob.rotation_euler=(math.pi/2,0,0);ob.hide_render=True
 landmarks={'FrontAxle_L':P(s['front_axle_u'],s['track']/2,s['wheel_radius']),'FrontAxle_R':P(s['front_axle_u'],-s['track']/2,s['wheel_radius']),'BonnetRear':P(s['scuttle_u'],0,s['scuttle_z']),'RoofFront':P(s['roof_front_u'],0,s['roof_z']),'Nose':P(s['front_u'],0,s['nose_z'])}
 for name,point in landmarks.items():
  ob=bpy.data.objects.new('Guide_'+name,None);c.objects.link(ob);ob.empty_display_type='PLAIN_AXES';ob.empty_display_size=.065;ob.location=point;ob.hide_render=True
 c.hide_render=True

def refresh_landmarks(s):
 points={'FrontAxle_L':P(s['front_axle_u'],s['track']/2,s['wheel_radius']),'FrontAxle_R':P(s['front_axle_u'],-s['track']/2,s['wheel_radius']),'BonnetRear':P(s['scuttle_u'],0,s['scuttle_z']),'RoofFront':P(s['roof_front_u'],0,s['roof_z']),'Nose':P(s['front_u'],0,s['nose_z'])}
 for name,point in points.items():
  ob=bpy.data.objects.get('Guide_'+name)
  if ob:ob.location=point

def fit_report():
 report={'stage':'front-module-tool-test','objects':{},'panel_intersections':{},'limits':['Static assembly only; no steering/suspension/hinge travel validation','No UVs, interior, rig or Unreal export','Reference guides are not live mesh handles']}
 trees={}
 for ob in owned():
  if ob['gt_part'] not in {'body','wheels'}:continue
  eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();bm=bmesh.new();bm.from_mesh(me)
  report['objects'][ob['gt_role']]={'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'loose_vertices':sum(not v.link_faces for v in bm.verts)}
  trees[ob['gt_role']]=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons])
  bm.free();eo.to_mesh_clear()
 names=[n for n in trees if n=='Bonnet' or 'DoorSkin' in n]
 for i,a in enumerate(names):
  for b in names[i+1:]:report['panel_intersections'][a+'/'+b]=len(trees[a].overlap(trees[b]))
 report['wheel_body_intersections']={name:len(trees[name].overlap(trees['FixedBody'])) for name in trees if 'Wheel_' in name}
 if 'RearWheel_L' in trees:report['stage']='whole-estate-shape-study'
 report['ok']=all(not any(v.values()) for v in report['objects'].values()) and not any(report['panel_intersections'].values()) and not any(report['wheel_body_intersections'].values())
 s=json.loads(bpy.context.scene.get('gt_car_spec','{}'))
 if s.get('shape_study'):
  report['detail_checks']=detail_checks(s)
  report['ok']=report['ok'] and all(report['detail_checks'].values())
 return report

def detail_checks(s):
 """Checks for the user's reported indicator overhang and visible sill/arch clashes."""
 objects={o['gt_role']:o for o in owned()};checks={};dg=bpy.context.evaluated_depsgraph_get()
 body=objects['FixedBody'].evaluated_get(dg)
 def vertices(role):
  ob=objects[role];eo=ob.evaluated_get(dg);me=eo.to_mesh()
  result=[ob.matrix_world@v.co for v in me.vertices];eo.to_mesh_clear();return result
 for sign,label in [(1,'L'),(-1,'R')]:
  lamp=vertices('Indicator_'+label);z=s['nose_z']-.134
  recess=vertices('NoseRecess')
  checks['indicator_inside_recess_'+label]=all(abs(v.x)<max(abs(p.x) for p in recess)-.005 and min(p.z for p in recess)+.005<v.z<max(p.z for p in recess)-.005 for v in lamp)
  checks['indicator_behind_front_face_'+label]=all(-v.y<s['front_u'] for v in lamp)
  trim=vertices('SillTrim_'+label);us=[-v.y for v in trim];r=s['wheel_radius']+s['arch_clearance']
  checks['trim_clear_of_arch_feet_'+label]=min(us)>=s['rear_axle_u']+r+.03 and max(us)<=s['front_axle_u']-r-.03
  clear=True
  for t in [.02,.1,.3,.5,.7,.9,.98]:
   u=min(us)+(max(us)-min(us))*t
   for dz in [-.020,0,.020]:
    zz=s['sill_z']+.021+dz
    outer=(s['width']/2+.018)*width_ratio(s,u)
    if s.get('coachwork_profile'):
     from coachwork import map_point
     mapped=map_point(s,P(u,sign*(s['width']/2+.018),zz));outer=abs(mapped.x);zz=mapped.z
    origin=P(u,sign*2,zz)
    if body.ray_cast(origin,Vector((-sign,0,0)),distance=2-outer-.001)[0]:clear=False
  checks['no_body_in_front_of_sill_trim_'+label]=clear
 return checks

