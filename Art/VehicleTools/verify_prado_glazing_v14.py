import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,Point
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-v14')
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Corrected.blend'));dg=bpy.context.evaluated_depsgraph_get();sc=bpy.context.scene
def tree(obs):
 vv=[];ff=[]
 for ob in obs:
  ev=ob.evaluated_get(dg);me=ev.to_mesh();k=len(vv);vv.extend(ev.matrix_world@v.co for v in me.vertices);ff.extend([k+i for i in p.vertices] for p in me.polygons);ev.to_mesh_clear()
 return BVHTree.FromPolygons(vv,ff)
meshstats=[]
for n in ['Glass | Windscreen','Glass | RearWindow']:
 ob=bpy.data.objects[n];bm=bmesh.new();bm.from_mesh(ob.data)
 stats={'object':n,'boundary_edges':sum(e.is_boundary for e in bm.edges),'overconnected_edges':sum(len(e.link_faces)>2 for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-11 for f in bm.faces),'volume_m3':bm.calc_volume()}
 meshstats.append(stats);bm.free()
 assert stats['boundary_edges']==0 and stats['overconnected_edges']==0 and stats['degenerate_faces']==0,stats
report=json.loads((P/'repair-report.json').read_text());coverage=[]
for name,field,outerkey,sgn in [('Windscreen','windscreen','fixed_outer_ring_raw',-1),('RearWindow','rear_window','outer_ring_raw',1)]:
 coords=report[field][outerkey];poly=Polygon([(p[0],p[2]) for p in coords]);xmin,zmin,xmax,zmax=poly.bounds
 obs=[bpy.data.objects['Glass | '+name]]+list(bpy.data.collections['17 Glazing correction'].objects)
 bb=tree(obs);miss=[];tested=0
 for i in range(100):
  for j in range(40):
   x=xmin+(xmax-xmin)*(i+.5)/100;z=zmin+(zmax-zmin)*(j+.5)/40
   if not poly.contains(Point(x,z)):continue
   tested+=1;h=bb.ray_cast(Vector((x*5,sgn*4,z*5)),Vector((0,-sgn,0)),8)[0]
   if h is None:miss.append([x,z])
 coverage.append({'aperture':name,'samples':tested,'misses':miss})
 assert not miss,coverage[-1]
gt=tree([bpy.data.objects['Glass | Windscreen']]);contact=[]
for path in report['wipers']['new_contact_paths']:
 ds=[gt.find_nearest(Vector(p)*5)[3] for p in path['glass_contact_samples_raw']]
 contact.append({'blade':path['name'],'samples':len(ds),'max_contact_distance_m':max(ds),'mean_contact_distance_m':sum(ds)/len(ds)})
 assert max(ds)<.0015,contact[-1]
interior=[o for o in sc.objects if o.type=='MESH' and any(c.name in ['13 Seats','14 Dashboard','15 Controls','16 Cabin trim'] for c in o.users_collection)]
intersections=[]
for n in ['Glass | Windscreen','Glass | RearWindow']:
 tt=tree([bpy.data.objects[n]])
 for ob in interior:
  hits=tt.overlap(tree([ob]))
  if hits:intersections.append({'glass':n,'interior':ob.name,'triangle_pairs':len(hits)})
res={'closed_panes':meshstats,'window_surface_coverage':coverage,'wiper_contact':contact,'glass_interior_intersections':intersections,'scope':'Static corrected front/rear glazing and parked wipers only; visual review required separately.'}
(P/'glazing-verification.json').write_text(json.dumps(res,indent=2))
assert not intersections,intersections
print(json.dumps(res,indent=2))



