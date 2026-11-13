"""Local boundary-edge refinement; preserve coordinates away from window rim."""
import bpy,math
from mathutils import Vector

def fair_body_rim(ring,surface,step=.0025):
 def target_y(x,old_y,z):
  t=max(0.,min(1.,(z-.310)/.006));w=t*t*(3-2*t)
  return old_y+w*(surface(x,z)-.00065-old_y)
 dense=[];subdivisions={};n=len(ring)
 for i,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
  cuts=max(1,math.ceil(math.dist((a[0],a[2]),(b[0],b[2]))/step))
  segment=[]
  for j in range(cuts+1):
   t=j/cuts;x=a[0]+(b[0]-a[0])*t;z=a[2]+(b[2]-a[2])*t;old_y=a[1]+(b[1]-a[1])*t;p=(x,target_y(x,old_y,z),z)
   segment.append(p)
  dense.extend(segment[:-1]);subdivisions[i]=segment
 report=[]
 candidates=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name=='Prado | fixed shell and underbody' or o.name.startswith('Door |'))]
 for ob in candidates:
  me=ob.data;match={}
  for v in me.vertices:
   p=v.co/5
   for i,q in enumerate(ring):
    if (p-Vector(q)).length<.000002:match[v.index]=i;break
  if not match:continue
  verts=[v.co.copy() for v in me.vertices];moved=[]
  for vid,i in match.items():
   target=target_y(ring[i][0],ring[i][1],ring[i][2]);delta=(target-ring[i][1])*5
   verts[vid].y=target*5;moved.append({'old_vertex':vid,'source_ring_point':i,'Y_change_mm':delta*1000})
  cache={};faces=[];loopnorm=[];smooth=[];matids=[];special=set(match)
  for poly in me.polygons:
   ids=list(poly.vertices);pnorms=[me.corner_normals[i].vector.copy() for i in poly.loop_indices];out=[];norms=[];changed=any(i in match for i in ids)
   for k,a in enumerate(ids):
    b=ids[(k+1)%len(ids)];out.append(a);norms.append(pnorms[k]);ai=match.get(a);bi=match.get(b)
    if ai is None or bi is None:continue
    if (ai+1)%n==bi:segment=subdivisions[ai]
    elif (bi+1)%n==ai:segment=list(reversed(subdivisions[bi]))
    else:continue
    key=tuple(sorted((a,b)))
    if key not in cache:
     new=[]
     for p in segment[1:-1]:new.append(len(verts));verts.append(Vector(p)*5);special.add(new[-1])
     cache[key]=(a,new)
    first,new=cache[key];new=new if first==a else list(reversed(new))
    for j,v in enumerate(new):out.append(v);norms.append(pnorms[k].lerp(pnorms[(k+1)%len(ids)],(j+1)/(len(new)+1)).normalized())
   faces.append(out);loopnorm.extend(norms);smooth.append(poly.use_smooth or changed);matids.append(poly.material_index)
  new=bpy.data.meshes.new(ob.name+' faired inner windscreen lip');new.from_pydata(verts,[],faces);new.update()
  for mat in me.materials:new.materials.append(mat)
  for p,sm,mi in zip(new.polygons,smooth,matids):p.use_smooth=sm;p.material_index=mi
  new.update();auto=[c.vector.copy() for c in new.corner_normals]
  for i,loop in enumerate(new.loops):
   if loop.vertex_index in special:loopnorm[i]=auto[i]
  new.normals_split_custom_set(loopnorm);ob.data=new
  report.append({'object':ob.name,'moved_existing_boundary_vertices':moved,'inserted_boundary_vertices':len(verts)-len(me.vertices),'unchanged_off_boundary_vertices':len(me.vertices)-len(match)})
 return dense,report
