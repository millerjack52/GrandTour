from pathlib import Path
p=Path('C:/GrandTour/Art/VehicleTools/build_prado_cabin_v05.py')
s=p.read_text().replace('prado-cabin-v05','prado-cabin-v06')
s=s.replace("source_tree=BVHTree.FromPolygons(rawv,rawf)","""source_tree=BVHTree.FromPolygons(rawv,rawf)
dg=bpy.context.evaluated_depsgraph_get()
normal_ref=bpy.data.objects.new('TEMP source normal reference',bpy.data.meshes.new_from_object(body.evaluated_get(dg)))
sc.collection.objects.link(normal_ref);normal_ref.hide_render=True
""")
s=s.replace(".323,.35,.38,.419]",".323,.35,.353]")
s=s.replace("return hit.x+.0004 if hit and hit.x>.14 else .179","return min(.179,hit.x-.0012) if hit and hit.x>.14 else .170")
s=s.replace("[(-.178,.419,.184),(.178,.419,.184),(.177,.419,.268),(-.177,.419,.268)]","[(-.169,.353,.184),(.169,.353,.184),(.167,.353,.313),(-.167,.353,.313)]")
s=s.replace("z=.222 if not rear else .258","z=.222 if not rear else .238")
s=s.replace("floor=basez(y);width=", "floor=max(basez(y-.05),basez(y+.05));width=")
s=s.replace("for dy in [-.042,.042]:cb(label+' attached floor foot',(x+dx,y+dy,floor+.003),(.016,.014,.006),'Metal',.0006)","""for dy in [-.042,.042]:
   fz=basez(y+dy)
   cb(label+' attached floor foot',(x+dx,y+dy,(fz+floor+.009)/2),(.016,.014,floor+.009-fz),'Metal',.0006)""")
s=s.replace("cb(label+' backrest insert',(x,backy-.016,z+.070),(width*.69,.004,.094),'Insert',.003)","insert=cb(label+' backrest insert',(x,backy-.016,z+.070),(width*.69,.004,.094),'Insert',.003);insert.data.transform(Matrix.Translation(center)@Matrix.Rotation(-.10,4,'X')@Matrix.Translation(-center))")
s=s.replace("(0,.313,.190),(.212,.177,.010)","(0,.269,.190),(.212,.154,.010)")
s=s.replace("for y in [.245,.383]", "for y in [.208,.332]")
s=s.replace("box('CAB | Headliner',(0,.136,.424),(.267,.438,.003),TRIM,'Insert',.008)","""hv=[];hf=[];hxs=[-.137,-.10,-.05,0,.05,.10,.137];hys=[-.065,-.025,.03,.09,.15,.21,.27,.32,.345]
for y in hys:
 for x in hxs:
  # Roof features can sit above the panel: sample from below first to find the cabin roof.
  loc=source_tree.ray_cast(Vector((x,y,.40)),Vector((0,0,1)),.07)[0]
  if loc is None:loc=source_tree.ray_cast(Vector((x,y,.48)),Vector((0,0,-1)),.08)[0]
  assert loc is not None,(x,y)
  hv.append((x,y,min(loc.z-.0035,.436)))
for j in range(len(hys)-1):
 for i in range(len(hxs)-1):
  a=j*len(hxs)+i;hf.append((a,a+len(hxs),a+len(hxs)+1,a+1))
make('CAB | Headliner',hv,hf,TRIM,'Insert',thick=.001)
""")
s=s.replace("(0,.073,.419),(.021,.032,.008)","(0,.073,.432),(.021,.032,.008)")
s=s.replace("for x in [-.085,.085]:cb('Sun visor',(x,-.086,.408),(.077,.028,.006),'Fabric',.002,TRIM)","""for x in [-.085,.085]:
 cb('Sun visor',(x,-.04,.413),(.077,.028,.006),'Fabric',.002,TRIM)
 tube('Visor hinge',[(x-.033,-.047,.419),(x-.033,-.047,.427)],.0015,TRIM,'Cabin')""")
s=s.replace("[(0,-.098,.409),(0,-.114,.392)]","[(0,-.051,.427),(0,-.067,.396)]")
s=s.replace("(0,-.114,.388)","(0,-.067,.392)").replace("(0,-.111,.388)","(0,-.064,.392)")
marker="# Use a thin-sheet transmission shader"
s=s.replace(marker,"""# Transfer the accepted source's evaluated corner normals onto exact split surfaces.
# This modifies shading only. Thickness wall normals remain the new fitted normals.
for ob in [fixed,hood]+door_objects:
 bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Preserved source exterior normals','DATA_TRANSFER');mod.object=normal_ref
 mod.use_loop_data=True;mod.data_types_loops={'CUSTOM_NORMAL'};mod.loop_mapping='POLYINTERP_NEAREST'
 mod.use_max_distance=True;mod.max_distance=.0002
 # Keep the modifier live with a hidden, named reference in a non-export collection.
normal_ref.name='REFERENCE | exterior normals only'
refcol=bpy.data.collections.new('99 Source normals reference - exclude from export');sc.collection.children.link(refcol)
for col in list(normal_ref.users_collection):col.objects.unlink(normal_ref)
refcol.objects.link(normal_ref);normal_ref.hide_set(True)

"""+marker)
s=s.replace("render('dashboard',(0,-.115,.283),(.3,3,1.6),.41)","""seathidden=[]
for o in cols['13 Seats'].objects:
 if not o.hide_render:seathidden.append(o);o.hide_render=True
render('dashboard',(0,-.11,.282),(.3,3,1.6),.37)
for o in seathidden:o.hide_render=False""")
Path('C:/GrandTour/Art/VehicleTools/build_prado_cabin_v06.py').write_text(s)
