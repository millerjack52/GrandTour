import bpy,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from prado_glazing_repair import make,fit_surface

def repair_wipers(wind_contract):
 old=[]
 for ob in list(bpy.context.scene.objects):
  if ob.get('source_component') in [95,96,107,108,235]:old.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
 ring=[p['co'] for p in wind_contract['outer_ring']];surface=fit_surface(ring,bow=.0007,outsign=-1,offset=-.00065)
 col='18 Windscreen wipers'
 def tube(n,points,r,mat='Metal',segments=8):
  vv=[];ff=[];pp=[Vector(p) for p in points]
  for i,p in enumerate(pp):
   t=(pp[min(i+1,len(pp)-1)]-pp[max(0,i-1)]).normalized();a=t.cross(Vector((0,0,1)))
   if a.length<.01:a=t.cross(Vector((1,0,0)))
   a.normalize();b=t.cross(a)
   vv.extend(p+r*(a*math.cos(j*math.tau/segments)+b*math.sin(j*math.tau/segments)) for j in range(segments))
  for i in range(len(pp)-1):
   for j in range(segments):a=i*segments+j;b=i*segments+(j+1)%segments;ff.append((a,b,b+segments,a+segments))
  ff.extend([tuple(reversed(range(segments))),tuple((len(pp)-1)*segments+j for j in range(segments))])
  return make(n,vv,ff,mat,col=col)
 vv=[];ff=[]
 for fixed in [bpy.data.objects['Prado | fixed shell and underbody'],bpy.data.objects['Bonnet | original surface']]:
  k=len(vv);vv.extend(v.co/5 for v in fixed.data.vertices);ff.extend([i+k for i in p.vertices] for p in fixed.data.polygons)
 tree=BVHTree.FromPolygons(vv,ff)
 contacts=[]
 for label,cx,px in [('left',-.105,-.035),('right',.034,.098)]:
  vv=[];ff=[];samples=[]
  for i in range(33):
   x=cx-.043+i/32*.086;z=.3205+(x-cx)*.013;y=surface(x,z)
   dz=(surface(x,z+.00001)-surface(x,z-.00001))/.00002
   dx=(surface(x+.00001,z)-surface(x-.00001,z))/.00002
   normal=Vector((dx,-1,dz)).normalized();up=Vector((0,dz,1)).normalized();p=Vector((x,y,z))+normal*.00004;samples.append(list(p))
   # Wedge lip touches glass along its continuous edge; raised back holds the arm.
   vv.extend([p-up*.00016,p+up*.00016,p+up*.00065+normal*.0007,p-up*.00065+normal*.0007])
  for i in range(32):
   for j in range(4):a=i*4+j;b=i*4+(j+1)%4;ff.append((a,b,b+4,a+4))
  ff.extend([(3,2,1,0),(128,129,130,131)])
  make('Wiper | '+label+' continuous rubber lip',vv,ff,'Rubber',col=col)
  backbone=[(x,surface(x,.3205+(x-cx)*.013)-.0012,.3205+(x-cx)*.013+.0007) for x in [cx-.041+i*.082/20 for i in range(21)]]
  tube('Wiper | '+label+' curved blade carrier',backbone,.0007,'Metal')
  z=.3205;contact=Vector((cx,surface(cx,z)-.0012,z+.0007));hinge=contact+Vector((0,-.0015,.0003))
  tube('Wiper | '+label+' blade connector',[contact,hinge],.0013,'Metal',12)
  mount=tree.ray_cast(Vector((px,-.195,.34)),Vector((0,0,-1)),.10)[0]
  assert mount is not None,(label,px)
  pivot=mount+Vector((0,0,.0035));tube('Wiper | '+label+' mounted pivot',[mount-Vector((0,0,.0002)),pivot],.0025,'Rubber',16)
  tube('Wiper | '+label+' attached arm',[pivot,pivot.lerp(hinge,.18)+Vector((0,-.001,.002)),hinge],.00105,'Metal',8)
  contacts.append({'name':label,'glass_contact_samples_raw':samples,'mount_raw':list(mount),'continuous_contact_offset_m':.0002})
 return {'removed_source_parts':old,'new_contact_paths':contacts,'method':'Paired curved rubber lips follow the repaired pane; each arm joins a body-mounted pivot and blade connector.'}
