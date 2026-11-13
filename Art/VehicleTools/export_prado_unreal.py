"""Read-only export of Prado v15 into the established Grand Tour static FBX contract.

Run headless Blender with --factory-startup. The source blend is never written.
Outputs refuse replacement. Export makes no claim of finished UVs, LODs or rigging.
"""
import bpy, bmesh, json, re, math, hashlib
from pathlib import Path
from mathutils import Matrix, Vector

SOURCE=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-v15/Prado_Corrected.blend')
OUT=Path('C:/GrandTour/Art/Export/VehicleTools/prado-unreal-v01')
PACKAGE=OUT/'Prado'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(s): return re.sub('[^A-Za-z0-9_]+','_',s).strip('_')
def unreal_point(p): return [-p[1]*100,-p[0]*100,p[2]*100]
def bounds(points): return [[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]

def compact_surface(src, keep_faces=None):
    """Copy only referenced surface vertices and retain corner shading/UVs.

    Source panel extraction deliberately retains some unused body vertices.
    Unreal discards those, so both export bounds and FBX must use triangle
    references, never the complete original vertex array.
    """
    faces=list(src.polygons) if keep_faces is None else [src.polygons[i] for i in keep_faces]
    ids=sorted({vi for p in faces for vi in p.vertices});remap={vi:i for i,vi in enumerate(ids)}
    normals=[src.corner_normals[li].vector.copy() for p in faces for li in p.loop_indices]
    uvdata={uv.name:[uv.data[li].uv.copy() for p in faces for li in p.loop_indices] for uv in src.uv_layers}
    dst=bpy.data.meshes.new(src.name+'_surface')
    dst.from_pydata([src.vertices[i].co for i in ids],[],[[remap[i] for i in p.vertices] for p in faces]);dst.update()
    for mat in src.materials:dst.materials.append(mat)
    for p,q in zip(dst.polygons,faces):p.material_index=q.material_index;p.use_smooth=q.use_smooth
    for name,uvs in uvdata.items():
        layer=dst.uv_layers.new(name=name)
        for loop,value in zip(layer.data,uvs):loop.uv=value
    dst.normals_split_custom_set(normals)
    return dst,len(src.vertices)-len(ids)

assert bpy.app.background,'Background only'
assert not PACKAGE.exists(),'Output already exists; choose a new revision, never replace it'
OUT.mkdir(parents=True,exist_ok=True);PACKAGE.mkdir()
before=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
sc=bpy.context.scene;sc.frame_set(1);bpy.context.view_layer.update()
pivot_names={'Front left':'Wheel_FL','Front right':'Wheel_FR','Rear left':'Wheel_RL','Rear right':'Wheel_RR','Rear spare':'SpareWheel'}
pivots={v:bpy.data.objects['Wheel pivot | '+k].matrix_world.translation.copy() for k,v in pivot_names.items()}
sources=[];excluded=[]
for ob in list(sc.objects):
    if ob.type not in {'MESH','CURVE','FONT','SURFACE'} or ob.hide_render or any(c.hide_render or c.name.startswith(('90 ','99 ')) for c in ob.users_collection):
        excluded.append(ob.name);continue
    sources.append(ob)

def group(ob):
    # Only actual panes use the translucent window material. The small radio
    # display shares Blender Glass and is exported with panes for matching slots.
    if any(m and m.name=='Prado | Glass' for m in ob.data.materials):return 'Glass'
    parent=ob.parent
    while parent:
        if parent.name.startswith('Wheel pivot | '):return pivot_names[parent.name.removeprefix('Wheel pivot | ')]
        parent=parent.parent
    cols={c.name for c in ob.users_collection}
    if cols & {'12 Cabin structure','13 Seats','14 Dashboard','15 Controls','16 Cabin trim'}:return 'Cabin'
    if '17 Rear lighting' in cols:return 'RearLighting'
    if '08 Underbody' in cols:return 'Underbody'
    if '05 Front equipment' in cols:return 'FrontEquipment'
    if '06 Roof rack and cargo' in cols:return 'RoofEquipment'
    if '07 Side equipment' in cols:return 'SideEquipment'
    if '10 Doors and closures' in cols:
        # Detached but static; no hinge articulation is implied.
        return {'Door | Front_L':'DoorFrontL','Door | Front_R':'DoorFrontR','Door | Rear_L':'DoorRearL','Door | Rear_R':'DoorRearR','Bonnet | original surface':'Bonnet'}[ob.name]
    if cols & {'09 Small fittings','17 Glazing correction','18 Windscreen wipers'}:return 'ExteriorTrim'
    return 'Body'

# Resolve before renaming material datablocks.
membership={ob.name:group(ob) for ob in sources}
material_specs={};materials={m for ob in sources for m in ob.data.materials if m}
for mat in sorted(materials,key=lambda m:m.name):
    original=mat.name;name='M_Prado_'+clean(original)
    bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if mat.node_tree else None
    def val(key,default):return bs.inputs[key].default_value if bs and key in bs.inputs else default
    linked=[i.name for i in bs.inputs if i.is_linked] if bs else []
    assert not linked,(original,'requires baking',linked)
    material_specs[name]=dict(source=original,base_color=list(val('Base Color',mat.diffuse_color)),roughness=float(val('Roughness',.5)),metallic=float(val('Metallic',0)),specular=float(val('Specular IOR Level',.5)),transmission=float(val('Transmission Weight',0)),alpha=float(val('Alpha',1)),ior=float(val('IOR',1.5)),emission=list(val('Emission Color',[0,0,0,1])),emission_strength=float(val('Emission Strength',0)))
    mat.name=name

dg=bpy.context.evaluated_depsgraph_get()
col=bpy.data.collections.new('EXPORT_ONLY');sc.collection.children.link(col)
groups={};all_points=[];wheel_points={};source_stats={}
for old in sources:
    ev=old.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
    if not me.polygons:continue
    me,loose=compact_surface(me)
    me.transform(ev.matrix_world);g=membership[old.name]
    points=[v.co.copy() for v in me.vertices]
    assert all(math.isfinite(x) for p in points for x in p),old.name
    all_points.extend(unreal_point(p) for p in points)
    if g in pivots:wheel_points.setdefault(g,[]).extend(points)
    source_stats[old.name]={'group':g,'vertices':len(me.vertices),'triangles':sum(len(p.vertices)-2 for p in me.polygons),'loose_vertices_removed':loose}
    ob=bpy.data.objects.new('EXPORT_'+old.name,me);col.objects.link(ob);groups.setdefault(g,[]).append((ob,old.name))
for ob in bpy.context.view_layer.objects:ob.select_set(False)
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
T=Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z')
report=dict(car='Prado',source=str(SOURCE),source_sha256=before,axis='centimetres, +X forward, -Y left, +Z up',bounds_cm=bounds(all_points),materials=material_specs,parts=[],excluded=excluded,static_only=True,source_objects=len(source_stats),source_stats=source_stats,wheels={})
for g,entries in sorted(groups.items()):
    for ob in bpy.context.selected_objects:ob.select_set(False)
    for ob,_ in entries:ob.select_set(True)
    bpy.context.view_layer.objects.active=entries[0][0];bpy.ops.object.join()
    ob=bpy.context.object;ob.name='SM_Prado_'+g;pivot=pivots.get(g,Vector((0,0,0)))
    ob.data.transform(T@Matrix.Translation(-pivot))
    tri=ob.modifiers.new('Stable export triangulation','TRIANGULATE');tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    # Drop collapsed modifier triangles only, preserving every vertex position,
    # per-corner normal, UV and material assignment of every retained triangle.
    src=ob.data;keep=[p.index for p in src.polygons if p.area>1e-8]
    removed=len(src.polygons)-len(keep)
    if removed:ob.data,unused_after_pruning=compact_surface(src,keep)
    assert len({vi for p in ob.data.polygons for vi in p.vertices})==len(ob.data.vertices),(ob.name,'Loose export vertices')
    # A flat-colour asset still needs nondegenerate UV derivatives for Unreal's
    # tangent construction. This deliberately overlapping per-triangle UV0 is
    # an import/shading aid, not an authored texture atlas or lightmap unwrap.
    def uv_area(layer, poly):
        a,b,c=[layer.data[i].uv for i in poly.loop_indices]
        return abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
    active_uv=ob.data.uv_layers.active
    valid_uv=bool(active_uv) and all(uv_area(active_uv,p)>1e-12 for p in ob.data.polygons)
    generated_uv=not valid_uv
    if generated_uv:
        for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer)
        active_uv=ob.data.uv_layers.new(name='GeneratedTangentUV')
        for p in ob.data.polygons:
            for li,uv in zip(p.loop_indices,((0,0),(1,0),(0,1))):active_uv.data[li].uv=uv
    assert all(uv_area(active_uv,p)>1e-12 for p in ob.data.polygons),(ob.name,'Degenerate UV derivatives')
    old=list(ob.data.materials);used=sorted({p.material_index for p in ob.data.polygons});unique=[];mapping={};fallback_faces=0
    for idx in used:
        mat=old[idx] if idx<len(old) else None
        if mat is None:
            # Source wheel Solidify sometimes leaves an unused null slot; if
            # assigned, match the wheel alloy rather than introduce grey filler.
            if g in pivots:mat=bpy.data.materials['M_Prado_Prado_Wheel']
            else:raise AssertionError((ob.name,'Unassigned surface',idx))
            fallback_faces+=sum(p.material_index==idx for p in ob.data.polygons)
        if mat not in unique:unique.append(mat)
        mapping[idx]=unique.index(mat)
    ids=[mapping[p.material_index] for p in ob.data.polygons];ob.data.materials.clear()
    for mat in unique:ob.data.materials.append(mat)
    for poly,idx in zip(ob.data.polygons,ids):poly.material_index=idx
    mesh_bounds=bounds([[v.co.x,-v.co.y,v.co.z] for v in ob.data.vertices])
    counts={m.name:0 for m in unique}
    for poly in ob.data.polygons:counts[unique[poly.material_index].name]+=1
    tiny=sum(p.area<=1e-8 for p in ob.data.polygons)
    filename=PACKAGE/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,bake_anim=False,path_mode='AUTO',use_custom_props=False)
    report['parts'].append(dict(name=ob.name,file=str(filename),group=g,source_objects=[n for _,n in entries],pivot_cm=unreal_point(pivot),bounds_local_cm=mesh_bounds,triangles=len(ob.data.polygons),vertices=len(ob.data.vertices),materials=[m.name for m in unique],material_triangle_counts=counts,null_material_faces_resolved=fallback_faces,degenerate_triangles=tiny,collapsed_triangles_removed=removed,uv0=active_uv.name,generated_tangent_uv=generated_uv,minimum_uv_triangle_area=min(uv_area(active_uv,p) for p in ob.data.polygons),sha256=sha(filename)))

for g,points in wheel_points.items():
    pivot=pivots[g];spare=g=='SpareWheel';axis=1 if spare else 0
    radius=max(math.sqrt((p.x-pivot.x)**2+(p.z-pivot.z)**2) if spare else math.sqrt((p.y-pivot.y)**2+(p.z-pivot.z)**2) for p in points)
    report['wheels'][g]={'pivot_cm':unreal_point(pivot),'radius_cm':radius*100,'width_cm':100*(max(p[axis] for p in points)-min(p[axis] for p in points)),'axle_axis_unreal':'X' if spare else 'Y'}
assert len([x for x in report['wheels'] if x.startswith('Wheel_')])==4
assert any(p['group']=='Glass' and len(p['source_objects'])>=8 for p in report['parts'])
lamps=next(p for p in report['parts'] if p['group']=='RearLighting')
assert all(any(s in m for m in lamps['materials']) for s in ['rear_red','rear_amber','reverse'])
report['triangles']=sum(p['triangles'] for p in report['parts'])
report['source_loose_vertices_removed']=sum(s['loose_vertices_removed'] for s in source_stats.values())
report['uv_convention']='GeneratedTangentUV: overlapping per-triangle UV0 (0,0),(1,0),(0,1), providing nonzero derivatives for flat-colour materials. Not a texture atlas or lightmap UV.'
report['cockpit_camera']={'eye_cm':unreal_point(Vector((.085,-.020,.387))*5),'target_cm':unreal_point(Vector((.04,-.17,.285))*5),'horizontal_fov_degrees':84,'note':'Matches Blender driver-review eye/aim; wider FOV for in-engine cockpit inspection.'}
assert all(p['degenerate_triangles']==0 for p in report['parts'])
report['limitations']=['Static component FBXs with four wheel-centred meshes; not a Chaos skeletal rig.','No new UV atlas or LOD reduction in this import package. Flat source material colours retained.','Source body retains Tripo triangulation and mild source asymmetry; no silhouette changes made.','Wheel radius/centres are measured from the current stylized model, not verified factory dimensions.','Source cabin and glass retained; transparency requires explicit Unreal translucent material setup.','Dynamic wheel clearance, vehicle collision and runtime driving require Unreal validation.']
assert sha(SOURCE)==before,'Source changed during export'
(PACKAGE/'manifest.json').write_text(json.dumps(report,indent=2))
(OUT/'README.txt').write_text('Prado Unreal import package\n\nSource: '+str(SOURCE)+'\nSHA256: '+before+'\n\nEach FBX uses the established Grand Tour centimetres, +X forward convention. Position each mesh at its manifest pivot_cm, not at the bounds centre. All non-wheel meshes use origin (0,0,0); five wheel/spare meshes have local centres. Preserve named material slots; rear lamp bands use three materials.\n\n'+ '\n'.join(report['limitations'])+'\n')
print('PRADO_EXPORT_OK',json.dumps({'parts':len(report['parts']),'source_objects':len(source_stats),'triangles':report['triangles'],'bounds_cm':report['bounds_cm'],'wheels':report['wheels']}),flush=True)
