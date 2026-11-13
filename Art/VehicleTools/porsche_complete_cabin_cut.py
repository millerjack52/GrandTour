"""Remove the old interior fused into the donor body; preserve exterior skins."""
def split_plane(poly,axis,value,sign):
 inside=[];outside=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  a=(p[axis]-value)*sign;b=(q[axis]-value)*sign;ip=a>=0;iq=b>=0;(inside if ip else outside).append(p)
  if ip!=iq:
   h=p.lerp(q,a/(a-b));inside.append(h);outside.append(h)
 return inside,outside
me=body.data;me.calc_loop_triangles();visible_body=tree(body);pane_trees=[tree(o) for o in GLASS.objects if o.type=='MESH'];vs=[];fs=[];mats=[];removed=0;protected=0
for t in me.loop_triangles:
 ps=[me.vertices[i].co.copy() for i in t.vertices];pieces=[];work=ps
 # Closed glazing occludes the cabin when identifying the actual exterior.
 # Protect visible cowl/bonnet triangles before subtracting the old interior.
 centre=sum(ps,Vector())/3;external=False
 if centre.z>1.0 and -.95<centre.y<-.30:
  for direction in [Vector((0,0,1)),Vector((1,0,0)),Vector((-1,0,0))]:
   origin=centre+direction*3;hit=visible_body.ray_cast(origin,-direction,3.01)
   if hit[0] is None or (hit[0]-centre).length>.001:continue
   occluded=False
   for pane in pane_trees:
    gh=pane.ray_cast(origin,-direction,2.999)
    if gh[0] is not None:occluded=True;break
   if not occluded:external=True;break
 if external:
  fs.append(tuple(range(len(vs),len(vs)+3)));vs.extend(ps);mats.append(me.polygons[t.polygon_index].material_index);protected+=1;continue
 for axis,value,sign in [(0,-.72,1),(0,.72,-1),(1,-1.0,1),(1,1.14,-1),(2,.476,1),(2,1.18,-1)]:
  if not work:break
  work,outside=split_plane(work,axis,value,sign)
  if len(outside)>2:pieces.append(outside)
 # Cabin front follows the windscreen rake, rather than a vertical box wall.
 if work:
  inside=[];outside=[]
  for p,q in zip(work,work[1:]+work[:1]):
   a=p.y-1.4*p.z+2.21;b=q.y-1.4*q.z+2.21;ip=a>=0;iq=b>=0;(inside if ip else outside).append(p)
   if ip!=iq:h=p.lerp(q,a/(a-b));inside.append(h);outside.append(h)
  work=inside
  if len(outside)>2:pieces.append(outside)
 if len(work)>2:removed+=1
 for poly in pieces:
  for i in range(1,len(poly)-1):
   fs.append((len(vs),len(vs)+1,len(vs)+2));vs.extend([poly[0],poly[i],poly[i+1]]);mats.append(me.polygons[t.polygon_index].material_index)
new=bpy.data.meshes.new('Original exterior with clear cabin volume');new.from_pydata(vs,[],fs);new.update()
for m in me.materials:new.materials.append(m)
for f,mi in zip(new.polygons,mats):f.material_index=mi
bm=bmesh.new();bm.from_mesh(new);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bm.to_mesh(new);bm.free();body.data=new;finish(body,1.5)
report['repairs'].append({'part':'Fused donor interior','source_triangles_clipped':removed,'exterior_cowl_triangles_protected':protected,'reason':'Remove interior sheets behind closed glazing while preserving externally visible cowl geometry'})
