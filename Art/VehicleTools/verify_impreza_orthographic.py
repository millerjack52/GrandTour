"""Reopen and inspect actual saved reference rebuild; no inherited fit claims."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
out=Path(sys.argv[sys.argv.index('--')+1]);bpy.ops.wm.open_mainfile(filepath=str(out/'Impreza_Orthographic_Rebuild.blend'))
dg=bpy.context.evaluated_depsgraph_get();cache={}
def geo(o):
 if o.name in cache:return cache[o.name]
 e=o.evaluated_get(dg);me=e.to_mesh();vs=[e.matrix_world@v.co for v in me.vertices];fs=[tuple(p.vertices) for p in me.polygons];e.to_mesh_clear();r=(vs,fs,BVHTree.FromPolygons(vs,fs));cache[o.name]=r;return r
checks=[]
def check(name,ok,details):checks.append({'name':name,'passed':bool(ok),'details':details})
objects=[o for o in bpy.data.objects if o.type=='MESH' and not any(c.name.startswith(('90','91','92')) for c in o.users_collection)]
check('Finite saved geometry',all(all(math.isfinite(q) for q in v) for o in objects for v in geo(o)[0]),{'mesh_count':len(objects)})
floor=bpy.data.objects['Floor | full fitted pan'];fv,ff,ft=geo(floor)
seats=[o for o in objects if 'seat' in o.name and '| cushion' in o.name];miss=[];rays=0
for o in seats:
 vv=geo(o)[0];xmin,xmax=min(v.x for v in vv),max(v.x for v in vv);ymin,ymax=min(v.y for v in vv),max(v.y for v in vv)
 for i in range(15):
  for j in range(15):
   x=xmin+(xmax-xmin)*i/14;y=ymin+(ymax-ymin)*j/14;rays+=1
   if ft.ray_cast(Vector((x,y,.8)),Vector((0,0,-1)),1)[0] is None:miss.append([o.name,x,y])
check('Seat bases fully covered by pan',bool(seats) and not miss,{'rays':rays,'misses':miss[:20]})
# Negative control: previous undersized-floor failure must be detectable.
small=[Vector((-0.2,-1,.3)),Vector((.2,-1,.3)),Vector((.2,2,.3)),Vector((-.2,2,.3))];bad=BVHTree.FromPolygons(small,[(0,1,2,3)])
check('Floor negative control detects exposed seats',any(bad.ray_cast(Vector((s*.395,-.17,.8)),Vector((0,0,-1)),1)[0] is None for s in [-1,1]),'Deliberately narrow floor, not a modified delivery mesh')
tyres=[o for o in objects if 'tyre carcass' in o.name];clear=[];axles=[-1.2675,1.2675]
for t in tyres:
 g=t.name.split(' | ')[0];tv=geo(t)[0];rim=bpy.data.objects[g+' | dished barrel'];rv=geo(rim)[0];margin=min(max(v.x for v in tv)-max(v.x for v in rv),min(v.x for v in rv)-min(v.x for v in tv));clear.append({'wheel':g,'axial_rubber_margin_m':margin})
check('Tyres cover both rim flanges',len(clear)==4 and all(r['axial_rubber_margin_m']>.008 for r in clear),clear)
skin=[o for o in objects if o.users_collection[0].name.startswith('01') or 'fitted arch return' in o.name or 'closed inner tub' in o.name]
collisions=[]
for t in tyres:
 tb=geo(t)[2]
 for o in skin:
  if tb.overlap(geo(o)[2]):collisions.append([t.name,o.name])
check('Static tyre to body and wheelhouse clearance',not collisions,collisions)
seat_intersections=[]
for o in [o for o in objects if 'seat' in o.name]:
 vv=geo(o)[0]
 for v in vv:
  if abs(v.x)>.50 and any(abs(v.y-c)<.40 and v.z<.82 for c in axles):seat_intersections.append(o.name);break
check('Seats outside occupied rear wheelhouses',not seat_intersections,sorted(set(seat_intersections)))
# Catch the newly observed conformal-graphics and bumper-guard defects.
panels=[o for o in objects if o.users_collection[0].name.startswith('01')]
bad_graphics=[];bad_guards=[]
for o in [o for o in objects if 'cream graphic' in o.name or 'folded skid guard' in o.name]:
 for p in panels:
  if geo(o)[2].overlap(geo(p)[2]):
   (bad_graphics if 'cream graphic' in o.name else bad_guards).append([o.name,p.name])
check('Graphics clear curved painted panels',not bad_graphics,bad_graphics)
check('Skid guards clear bumper skins',not bad_guards,bad_guards)
attachments=[]
for sn in ['L','R']:
 for j in [0,1]:
  flap=bpy.data.objects[sn+f' | fitted red mudflap {j}'];clamp=bpy.data.objects[sn+f' | mudflap clamp {j}'];hanger=bpy.data.objects[sn+f' | mudflap hanger {j}'];anchor=bpy.data.objects[sn+f' | mudflap body anchor {j}']
  for aa,bb in [(flap,clamp),(flap,hanger),(hanger,anchor)]:attachments.append({'parts':[aa.name,bb.name],'contact':bool(geo(aa)[2].overlap(geo(bb)[2]))})
  attachments.append({'parts':[anchor.name,'painted fixed body'],'contact':any(geo(anchor)[2].overlap(geo(p)[2]) for p in panels)})
check('Mudflap clamp hanger and body contact chain',all(r['contact'] for r in attachments),attachments)
feet=[o for o in objects if 'Wing | deck foot' in o.name];boot=bpy.data.objects['Boot | rounded deck and rear return']
check('Wing feet seated on shaped boot',len(feet)==2 and all(geo(o)[2].overlap(geo(boot)[2]) for o in feet),[o.name for o in feet])
# Actual geometry distance to independently read intermediate contour positions.
holdouts={'Bonnet | traced crown and rolling shoulders':[(350,338),(490,329)],'Roof | traced long soft crown':[(880,117),(1040,117),(1150,121)],'Boot | rounded deck and rear return':[(1630,300)]}
errs=[]
for name,pts in holdouts.items():
 vv=geo(bpy.data.objects[name])[0];k=KDTree(len(vv))
 for i,v in enumerate(vv):k.insert(v,i)
 k.balance()
 for px,py in pts:
  p=Vector((0,(px-893)/400,(757-py)/400));near,idx,d=k.find(p);errs.append({'surface':name,'reference_px':[px,py],'nearest_mesh_m':d,'equivalent_reference_pixels':d*400})
check('Independent sampled upper contour within 6 reference pixels',all(r['equivalent_reference_pixels']<6 for r in errs),errs)
# All saved reference images must actually be packed for portable review.
check('Approved reference images packed',all(any(im.name==name and im.packed_file for im in bpy.data.images) for name in ['01-four-view-sheet.png','02-side-profile.png']),'Two approved images')
report={'passed':all(c['passed'] for c in checks),'checks':checks,'scope':'Static authoring assembly and sampled contour audit only. Not a global likeness score, continuous motion test, watertight certification or game export validation.'}
(out/'static-review-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if not report['passed']:raise RuntimeError('Saved assembly checks need repair; see report.')
