"""Section cage for the estate: distinct roof, belt, haunch and rocker shapes.

Deforms shared source surfaces and their fitted details through the same field.
Station cuts are essential: otherwise long faces shortcut the designed outline.
"""
import bmesh, math
from mathutils import Vector

def lerp_table(x, rows):
 if x<=rows[0][0]:return rows[0][1]
 for (a,va),(b,vb) in zip(rows,rows[1:]):
  if x<=b:return va+(vb-va)*(x-a)/(b-a)
 return rows[-1][1]

def stations(s):
 f=s['front_u'];a=s['front_axle_u'];r=s['rear_axle_u'];back=s['section_end_u']
 return [back,back+.18,s['roof_rear_u'],r,s['c_pillar_u'],s['b_pillar_u'],s['roof_front_u'],s['scuttle_u'],a,f-.20,f]

def map_point(s,p):
 x,y,z=p;u=-y;w=s['width']/2;ax=abs(x)
 f=s['front_u'];r=s['rear_axle_u'];back=s['section_end_u'];front=s['front_axle_u']
 # Broad fender volumes, a visible door waist, and narrowed end caps.
 body=lerp_table(u,[(back,.89),(back+.18,.97),(r,1.055),(s['c_pillar_u'],1.035),
    (s['b_pillar_u'],.975),(s['scuttle_u'],1.015),(front,1.055),(f-.20,.985),(f,.91)])
 # Roof width is independent of the shoulder outline. Corners turn inward.
 roof=lerp_table(u,[(s['roof_rear_u'],.89),(r,.95),(s['b_pillar_u'],.98),
    (s['roof_front_u']-.12,.97),(s['roof_front_u'],.92),(s['scuttle_u'],.92)])
 # Rocker tuck, a broad mid-door plane, shoulder roll, then narrower glazing.
 height=lerp_table(z,[(0,.90),(s['sill_z']+.07,.90),(.58,.975),(.82,1.0),
    (.92,1.0),(s['scuttle_z'],.97),(s['roof_z']-.055,.94),(s['roof_z'],.94)])
 roof_blend=max(0,min(1,(z-s['scuttle_z'])/(s['roof_z']-s['scuttle_z'])))
 scale=body*height*(1-roof_blend)+roof*roof_blend
 xx=x*scale
 # Retracted outer corners; the fascia and bumper follow the same angled nose.
 front_blend=max(0,min(1,(u-(f-.32))/.32))
 rear_blend=max(0,min(1,((back+.30)-u)/.30))
 corner=max(0,(ax/w-.68)/.32)
 uu=u-front_blend*.13*corner+rear_blend*.11*corner
 # Slightly bowed windscreen/cowl and a shallow crown through bonnet/roof.
 center=max(0,1-(ax/(w-.13))**2)
 hood_weight=max(0,min(1,(u-s['scuttle_u'])/.18))*max(0,min(1,(f-u)/.16))
 hood_height=max(0,min(1,(z-.78)/.12))
 zz=z+.030*center*hood_weight*hood_height*(1-roof_blend)
 if z>s['scuttle_z']:
  roof_center=max(0,min(1,(s['roof_half_width']-ax)/(s['roof_half_width']-.48)))
  zz+=roof_blend*(.024*roof_center-.020*(1-roof_center))
  uu+=roof_blend*.04*roof_center*max(0,min(1,(u-s['b_pillar_u'])/.35))
 return Vector((xx,-uu,zz))

def apply(s,ob):
 if ob['gt_part']=='wheels':return
 bm=bmesh.new();bm.from_mesh(ob.data)
 axes=[(1,[-u for u in stations(s)]),(2,[s['sill_z']+.07,.58,.82,.92,s['scuttle_z'],s['roof_z']-.055]),
       (0,[-s['roof_half_width'],-.55,0,.55,s['roof_half_width']])]
 for axis,positions in axes:
  for value in positions:
   if min(v.co[axis] for v in bm.verts)+1e-6<value<max(v.co[axis] for v in bm.verts)-1e-6:
    co=Vector((0,0,0));co[axis]=value;normal=Vector((0,0,0));normal[axis]=1
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=normal)
 for v in bm.verts:
  if ob['gt_role'] in {'Bumper','RearBumper'}:
   z=v.co.z;v.co=map_point(s,Vector((v.co.x,v.co.y,.74)));v.co.z=z
  else:v.co=map_point(s,v.co)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if ob['gt_part']=='cabin':
  for face in bm.faces:
   if face.material_index==1:face.smooth=True
 bm.to_mesh(ob.data);bm.free();ob.data.update()
