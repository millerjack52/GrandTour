"""Install native continuous banks, matched water and regrounded supports."""
import unreal as u
import sys,json,time,traceback,array,hashlib,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'GaeaCreek'
MORPHOLOGY='-GTMorphology' in u.SystemLibrary.get_command_line()
COURSE_REVISION='-GTCourseRevision' in u.SystemLibrary.get_command_line() or MORPHOLOGY
if COURSE_REVISION:OUT=BASE/'CourseRevision'
if MORPHOLOGY:OUT=BASE/'Morphology'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props,Graph
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/GaeaCreek'
PILOT='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ChannelPilot'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeGaeaCreek'
if COURSE_REVISION:
    DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/CourseRevision'
    BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeCourseRevision'
if MORPHOLOGY:
    DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology'
    BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeMorphology'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.AssetToolsHelpers.get_asset_tools()
before=array.array('f');before.frombytes((BASE/('CourseRevision' if MORPHOLOGY else 'GaeaCreek' if COURSE_REVISION else 'ChannelShape')/'height_local_south_up.f32').read_bytes())
after=array.array('f');after.frombytes((OUT/'height_local_south_up.f32').read_bytes())
BASELINE_ONLY='-GTChannelBaseline' in u.SystemLibrary.get_command_line()
VERIFY_ONLY='-GTChannelVerifyOnly' in u.SystemLibrary.get_command_line()
prepare=None if BASELINE_ONLY else json.loads((OUT/'prepare-report.json').read_text())
if prepare:assert prepare['ok']
report=dict(ok=False,images=[],driving_tested=False,timings_collected=False)
crossings=json.loads((OUT/'crossings.json').read_text());bedpoint=json.loads((OUT/'bed-point.json').read_text())
grid=before;cache={};busy=False
if VERIFY_ONLY:
    report=json.loads((OUT/'install-report.json').read_text());assert report['saved_and_reloaded']
    report.pop('error',None);report['ok']=False;grid=after
u.EditorPythonScripting.set_keep_python_script_alive(True)

def height(a,x,y):
    fx=max(0,min(2015.999999,(x+1250)*2016/2500));fy=max(0,min(2015.999999,(y+1250)*2016/2500));i=int(fx);j=int(fy);s=fx-i;t=fy-j;k=j*2017+i;q,r,v,w=a[k],a[k+1],a[k+2017],a[k+2018]
    return q+(r-q)*s+(w-r)*t if s>=t else q+(w-v)*s+(v-q)*t

def refs():return {a.get_actor_label():a for a in act.get_all_level_actors()}

def clean_saved_water():
    """Persist asset parents, never editor-preview MIDs/transient textures.

    PreviewWaterAt binds transient field/detail textures through component
    overrides. Saving those MIDs leaves broken texture parents on the next load.
    The runtime window will rebuild its own overrides when play starts.
    """
    sheet=refs()['Benmore_RS_WaterDomain'];saved=[]
    expected={'Benmore_RL_Stream':'M_GC_DomainRiver','Benmore_RL_Outlet':'M_GC_DomainRiver','Benmore_Vista_Lake':'M_GC_DomainLake'}
    surfaces=list(sheet.get_editor_property('domain_surfaces'))
    assert {a.get_actor_label() for a in surfaces}==set(expected)
    for a in surfaces:
        material=u.load_asset(DEST+'/'+expected[a.get_actor_label()]);assert material
        old=a.static_mesh_component.get_material(0)
        saved.append(dict(actor=a.get_actor_label(),preview_parent=old.get_path_name() if old else None,saved_parent=material.get_path_name()))
        a.static_mesh_component.set_material(0,material)
    preview=sheet.get_component_by_class(u.ProceduralMeshComponent)
    if preview:
        preview.clear_all_mesh_sections()
        preview.set_material(0,u.load_asset(DEST+'/M_GC_DomainRiver'))
    report['saved_water_materials']=saved

def verify_saved_water():
    expected={'Benmore_RL_Stream':'M_GC_DomainRiver','Benmore_RL_Outlet':'M_GC_DomainRiver','Benmore_Vista_Lake':'M_GC_DomainLake'}
    values=[]
    for a in refs()['Benmore_RS_WaterDomain'].get_editor_property('domain_surfaces'):
        m=a.static_mesh_component.get_material(0)
        assert isinstance(m,u.Material) and m.get_path_name()==DEST+'/'+expected[a.get_actor_label()]+'.'+expected[a.get_actor_label()]
        values.append(dict(actor=a.get_actor_label(),material=m.get_path_name()))
    report['reloaded_water_asset_parents']=values

def set_ford_camera():
    camera=refs()['Benmore_RL_Camera_Ford'];name,pos,target,focus=views()[0]
    camera.set_actor_location(u.Vector(*pos),False,False)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)

def signature(xy_only=False,labels=None):
    h=hashlib.sha256();count=0
    for a in sorted(act.get_all_level_actors(),key=lambda a:a.get_actor_label()):
        if labels and a.get_actor_label() not in labels:continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            h.update((a.get_actor_label()+'|'+c.get_name()).encode())
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);p=t.translation
                values=[p.x,p.y] if xy_only else [p.x,p.y,p.z]
                h.update(array.array('d',values if xy_only else values+list(t.rotation.to_tuple())+list(t.scale3d.to_tuple())).tobytes());count+=1
    return dict(count=count,sha256=h.hexdigest())

def queries():
    sheet=refs()['Benmore_RS_WaterDomain']
    pts=[(c['name'].replace('Footbridge','Bridge'),[v*100 for v in c['center_m'][:2]]) for c in crossings]
    pts+=[('Bed',[v*100 for v in bedpoint]),('Lake',[-166800,-2700])]
    return [dict(name=name,covers=sheet.covers(u.Vector2D(*p)),surface_cm=sheet.surface_cm_at(u.Vector2D(*p)),flow_cmps=sheet.flow_cm_per_s_at(u.Vector2D(*p)).to_tuple()) for name,p in pts]

def profiles():
    provider=refs()['Benmore_RL_CrossingProfiles'];sections=provider.get_editor_property('spec_asset').get_editor_property('spec').get_editor_property('sections')
    return [dict(start_m=s.get_editor_property('start_m'),end_m=s.get_editor_property('end_m'),deform={k:s.get_editor_property('deform').get_editor_property(k) for k in ['max_sinkage_m','sinkage_rate','cell_cm','ridge_width_cm','max_ridge_cm','repose_deg','slump_rate']}) for s in sections]

def native_support():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)];results=[]
    points=[(-661.25,177.5),(-660,179),(-666,177),(-605,230),(-609,227),(-601,234),(-690,145),(-570,263),(-406.25,438.75)]
    if (OUT/'support-checks.json').exists():points+=json.loads((OUT/'support-checks.json').read_text())
    for x,y in points:
        z=height(grid,x,y)*100
        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,z+20000),u.Vector(x*100,y*100,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit
        actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
        assert abs(actual-z)<5,(x,y,z,actual)
        results.append(dict(xy_m=[x,y],expected_z_cm=z,collision_z_cm=actual,error_cm=abs(actual-z)))
    return results

def outlet_support():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();bed=refs()['Benmore_RL_MouthBed']
    ignore=[a for a in act.get_all_level_actors() if a!=bed];results=[]
    for x,y,z in prepare['outlet']['support_points_m']:
        assert x<-1250
        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,z*100+1000),u.Vector(x*100,y*100,z*100-1000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit
        actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z
        assert abs(actual-z*100)<5,(x,y,z,actual)
        results.append(dict(xy_m=[x,y],expected_z_cm=z*100,collision_z_cm=actual,error_cm=abs(actual-z*100)))
    return results

def texture(name,exact=False):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST if exact else u.TextureFilter.TF_BILINEAR,never_stream=True)
    assert eal.save_loaded_asset(t);return t

def clone_material(source,name,textures):
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(source,DEST+'/'+name);assert m
    for n in mel.get_material_expressions(m):
        if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSampleParameter2D)):
            t=n.get_editor_property('texture')
            if t and t.get_name() in textures:n.set_editor_property('texture',textures[t.get_name()])
    for n in mel.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionCustom):
            code=n.get_editor_property('code');code=code.replace('(P.xy*.01-float2(-725,105)+.125)/float2(175.25,205.25)','(P.xy*.01-float2(-1250,-1250)+.62004)/float2(2501.24008,2501.24008)')
            code=code.replace('aggregate=lerp(aggregate,grey*float3(1.10,1.035,.90),.18);','aggregate=lerp(aggregate,grey*float3(1.08,1.10,1.12),.78)*1.20;')
            if COURSE_REVISION and (OUT/'bed-atlas.json').exists():
                native_uv='(P.xy*.01-float2(-1250,-1250)+.62004)/float2(2501.24008,2501.24008)'
                if 'ZonesSampler' in code and 'maskUV=' in code:
                    code=code.replace(native_uv,bed_atlas_uv())
                else:
                    # Only the gravel atlas extends. Shore/deformation masks
                    # still describe the native 2017 grid and keep their UVs.
                    code=code.replace(bed_atlas_uv(),native_uv)
            # Static shading reads quantized baked depth/current; the local
            # window reads exact field data. Fade between them at its perimeter
            # rather than expose the rectangular solver cutout in the optics.
            code=code.replace('if(Local>.5){velocity=live.ba*.01;depth=live.g*.01;}',
                'float windowBlend=Local>.5 ? smoothstep(0,600,min(edge.x,edge.y)) : 0;\nvelocity=lerp(velocity,live.ba*.01,windowBlend);depth=lerp(depth,live.g*.01,windowBlend);')
            code=code.replace('trail=Texture2DSampleLevel(Detail,DetailSampler,uv,0).rg;',
                'trail=Texture2DSampleLevel(Detail,DetailSampler,uv,0).rg*windowBlend;')
            n.set_editor_property('code',code)
    if name in ['M_GC_DomainRiver','M_GC_DomainLake']:
        codes=[n.get_editor_property('code') for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
        assert any('velocity=lerp(velocity,live.ba*.01,windowBlend)' in code and 'rg*windowBlend;' in code for code in codes)
        if COURSE_REVISION:
            shore_codes=[code for code in codes if 'ShoreSampler' in code]
            if name=='M_GC_DomainRiver':assert len(shore_codes)==1
            for code in codes:
                if 'ShoreSampler' in code:
                    assert '(P.xy*.01-float2(-1250,-1250)+.62004)/float2(2501.24008,2501.24008)' in code
                    assert bed_atlas_uv() not in code
            if name=='M_GC_DomainRiver':report['water_shore_mask_native_uv_verified']=True
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert eal.save_loaded_asset(m);return m

def bed_atlas_uv():
    a=json.loads((OUT/'bed-atlas.json').read_text());x,y=a['origin_m'];w,h=a['span_m']
    return '(P.xy*.01-float2(%.10f,%.10f)+%.10f)/float2(%.10f,%.10f)'%(x,y,a['half_cell_m'],w,h)

def extend_bed_materials(textures):
    atlas=texture('T_GC_ExtendedBedZones');textures.update(T_CP_BedZones=atlas,T_GC_ExtendedBedZones=atlas)
    return textures

def match_outlet_gravel(textures):
    import benmore_channel_pilot_materials as pilot
    previous=pilot.DEST;pilot.DEST=DEST
    try:
        ground=pilot.bed(DEST+'/M_GC_MouthBed','M_GC_MouthBed',zone_texture=textures['T_CP_BedZones'],rock_root=PILOT,mask_uv=bed_atlas_uv())
    finally:pilot.DEST=previous
    ground=clone_material(ground.get_path_name().split('.')[0],'M_GC_MouthBed',textures)
    refs()['Benmore_RL_MouthBed'].static_mesh_component.set_material(0,ground)
    report['continuous_bed_gravel_atlas']=json.loads((OUT/'bed-atlas.json').read_text())

def import_mesh(name,water):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
    mesh.set_material(0,water);assert eal.save_loaded_asset(mesh);return mesh

def reground():
    # Integral image makes the changed-ground support test inexpensive over 90k
    # authored instances. Only changed footprints require vertex-level seating.
    prefix=array.array('I');prefix.frombytes((OUT/'changed-prefix.u32').read_bytes());side=2018
    def touched(tr,mesh):
        p=tr.translation;b=mesh.get_bounds();scale=tr.scale3d
        radius=math.sqrt(b.box_extent.x**2+b.box_extent.y**2+b.box_extent.z**2)*max(abs(scale.x),abs(scale.y),abs(scale.z))
        radius+=math.sqrt(b.origin.x**2+b.origin.y**2+b.origin.z**2)*max(abs(scale.x),abs(scale.y),abs(scale.z))
        lo=[int(math.floor((v-radius+125000)/250000*2016)) for v in [p.x,p.y]];hi=[int(math.ceil((v+radius+125000)/250000*2016))+1 for v in [p.x,p.y]]
        if hi[0]<0 or hi[1]<0 or lo[0]>2017 or lo[1]>2017:return False
        x0,y0=[max(0,min(2017,v)) for v in lo];x1,y1=[max(0,min(2017,v)) for v in hi]
        return prefix[y1*side+x1]-prefix[y1*side+x0]-prefix[y0*side+x1]+prefix[y0*side+x0]>0
    def seat(tr,mesh,label):
        key=mesh.get_path_name()
        if key not in cache:
            b=mesh.get_bounds();desc=mesh.get_static_mesh_description(0);cut=b.origin.z-b.box_extent.z*.5
            cache[key]=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count()) if desc.get_vertex_position(u.VertexID(i)).z<=cut]
        points=cache[key];assert points,key
        oldlimits=[];newlimits=[];oz=tr.translation.z
        for point in points:
            v=u.MathLibrary.transform_location(tr,point);relative=v.z-oz
            oldlimits.append(height(before,v.x/100,v.y/100)*100-relative);newlimits.append(height(after,v.x/100,v.y/100)*100-relative)
        sink=.7 if label.startswith('Benmore_CP_') else 6
        nz=min(oz+min(newlimits)-min(oldlimits),min(newlimits)-sink)
        tr.translation=u.Vector(tr.translation.x,tr.translation.y,nz)
        return tr,nz-oz,nz-min(newlimits)
    shifted=[];basal=[];max_rotation=0.;max_scale=0.;max_xy=0.
    for a in act.get_all_level_actors():
        label=a.get_actor_label()
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            mesh=c.get_editor_property('static_mesh')
            if not mesh:continue
            for i in range(c.get_instance_count()):
                tr=c.get_instance_transform(i,True)
                if not touched(tr,mesh):continue
                oldxy=(tr.translation.x,tr.translation.y);oldrotation=tr.rotation.to_tuple();oldscale=tr.scale3d.to_tuple()
                tr,dz,gap=seat(tr,mesh,label)
                if abs(dz)<.01:continue
                assert c.update_instance_transform(i,tr,True,True,True)
                actual=c.get_instance_transform(i,True)
                max_xy=max(max_xy,abs(actual.translation.x-oldxy[0]),abs(actual.translation.y-oldxy[1]))
                # ISM stores matrices; decomposing/recomposing them can round
                # rotation and scale despite preserving the supplied transform.
                max_rotation=max(max_rotation,max(abs(v-w) for v,w in zip(actual.rotation.to_tuple(),oldrotation)))
                max_scale=max(max_scale,max(abs(v-w) for v,w in zip(actual.scale3d.to_tuple(),oldscale)))
                shifted.append(dict(actor=label,index=i,shift_cm=dz));basal.append(gap)
        if isinstance(a,u.StaticMeshActor) and label.startswith(('Benmore_Scenery_','Benmore_Composition_SchistExposure_')):
            tr=a.get_actor_transform();mesh=a.static_mesh_component.static_mesh
            if mesh and touched(tr,mesh):
                tr,dz,gap=seat(tr,mesh,label);a.set_actor_transform(tr,False,True);shifted.append(dict(actor=label,index=-1,shift_cm=dz));basal.append(gap)
    assert basal and max(basal)<=-.69
    (OUT/'regrounded-supports.json').write_text(json.dumps(shifted,indent=2))
    report['regrounding']=dict(count=len(shifted),maximum_basal_gap_cm=max(basal),z_shift_range_cm=[min(p['shift_cm'] for p in shifted),max(p['shift_cm'] for p in shifted)],maximum_xy_change_cm=max_xy,maximum_quaternion_component_change=max_rotation,maximum_scale_component_change=max_scale)
    assert max_xy==0 and max_rotation<1e-5 and max_scale<1e-5,report['regrounding']

def reconcile_dressing():
    """Move review-owned bank assets; remove ordinary plants from active water.

    Roads are excluded. Geographic masks decide clearance, and actual mesh basal
    vertices decide seating. Instance counts cannot be a geometry requirement.
    """
    shore=array.array('f');shore.frombytes((OUT/'shore_distance.f32').read_bytes())
    placements=json.loads((OUT/'dressing-positions.json').read_text())
    moved=0;removed=0;basal=[];group_index={}
    for actor in act.get_all_level_actors():
        label=actor.get_actor_label()
        if label in ['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']:continue
        owned=label.startswith(('Benmore_RL_tree_','Benmore_RL_rock_','Benmore_RL_gravel_','Benmore_RL_shrub_','Benmore_RL_tussock_','Benmore_CP_Aggregate'))
        nature=any(w in label.lower() for w in ['tree','willow','tussock','grass','scrub','shrub'])
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(comp,u.GrassInstancedStaticMeshComponent):continue
            mesh=comp.get_editor_property('static_mesh')
            if not mesh:continue
            erase=[]
            for index in range(comp.get_instance_count()):
                tr=comp.get_instance_transform(index,True);p=tr.translation
                if owned:
                    kind='aggregate' if label.startswith('Benmore_CP_') else label.split('_')[2]
                    counter=group_index.get(kind,0);xy=placements[kind][counter];group_index[kind]=counter+1
                    tr.translation=u.Vector(xy[0]*100,xy[1]*100,p.z)
                    key=mesh.get_path_name()
                    if key not in cache:
                        bounds=mesh.get_bounds();desc=mesh.get_static_mesh_description(0);cut=bounds.origin.z-bounds.box_extent.z*.5
                        cache[key]=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count()) if desc.get_vertex_position(u.VertexID(i)).z<=cut]
                    limits=[];oz=tr.translation.z
                    for v in cache[key]:
                        v=u.MathLibrary.transform_location(tr,v);limits.append(height(after,v.x/100,v.y/100)*100-(v.z-oz))
                    sink=1.5 if kind in ['aggregate','gravel'] else 7
                    tr.translation=u.Vector(tr.translation.x,tr.translation.y,min(limits)-sink)
                    assert comp.update_instance_transform(index,tr,True,True,True);moved+=1;basal.append(-sink)
                elif nature and abs(p.x)<125000 and abs(p.y)<125000 and height(shore,p.x/100,p.y/100)<1.4:
                    erase.append(index)
            for index in reversed(erase):assert comp.remove_instance(index);removed+=1
    assert basal and max(basal)<0
    report['bank_dressing']=dict(relocated_review_instances=moved,removed_plants_in_water=removed,maximum_basal_gap_cm=max(basal))

def install_assets():
    bylabel=refs();land=next(a for a in bylabel.values() if isinstance(a,u.Landscape))
    textures={name:texture(name) for name in ['T_CP_BedZones','T_CP_Shore','T_RL_Ecology','T_RL_Vegetation','T_RL_WaterMask','T_RS_DomainFlow','T_RS_DomainMask']+(['T_RL_Mouth'] if COURSE_REVISION else [])}
    if COURSE_REVISION:textures=extend_bed_materials(textures)
    terrain=clone_material(PILOT+'/M_CP_Terrain','M_GC_Terrain',textures)
    field=clone_material(PILOT+'/M_CP_DeformField','M_GC_DeformField',textures)
    water=clone_material(PILOT+'/M_CP_DomainRiver','M_GC_DomainRiver',textures)
    lake=clone_material('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale/M_RS_DomainLake','M_GC_DomainLake',textures)
    land.set_editor_property('landscape_material',terrain)
    provider=bylabel['Benmore_RL_CrossingProfiles'];old=provider.get_editor_property('spec_asset')
    profile=u.load_asset(DEST+'/DA_GC_CrossingProfiles') or eal.duplicate_asset(old.get_path_name().split('.')[0],DEST+'/DA_GC_CrossingProfiles')
    spec=old.get_editor_property('spec');sections=list(spec.get_editor_property('sections'))
    for section in sections:
        deform=section.get_editor_property('deform');deform.set_editor_property('surface_material_path',field.get_path_name());section.set_editor_property('deform',deform)
    c=crossings[0];p=c['center_m'];n=c['cross_direction'];spec.set_editor_property('route_m',[u.Vector2D(p[0]-n[0]*30,p[1]-n[1]*30),u.Vector2D(p[0]+n[0]*30,p[1]+n[1]*30)])
    spec.set_editor_property('sections',sections);profile.set_editor_property('spec',spec);assert eal.save_loaded_asset(profile);provider.set_editor_property('spec_asset',profile)
    ref=u.load_asset(DEST+'/DA_GC_WaterDomain') or eal.duplicate_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale/DA_RS_WaterDomain',DEST+'/DA_GC_WaterDomain')
    assert ref.import_bake(str(OUT/'water-domain.bin'));assert eal.save_loaded_asset(ref)
    for label,name in [('Benmore_RL_Stream','SM_GC_RiverSurface'),('Benmore_RL_Outlet','SM_GC_OutletSurface')]:
        mesh=import_mesh(name,water);bylabel[label].static_mesh_component.set_static_mesh(mesh);bylabel[label].static_mesh_component.set_material(0,water)
    bylabel['Benmore_Vista_Lake'].static_mesh_component.set_material(0,lake)
    if COURSE_REVISION:
        hills=[a for label,a in bylabel.items() if label.startswith('Benmore_Hills_') and isinstance(a,u.StaticMeshActor)]
        assert hills
        source=hills[0].static_mesh_component.get_material(0)
        hillmat=clone_material(source.get_path_name().split('.')[0],'M_GC_Hills',textures)
        for actor in hills:actor.static_mesh_component.set_material(0,hillmat)
        apron=bylabel['Benmore_RL_MouthBed'];source=apron.static_mesh_component.get_material(0)
        ground=clone_material(source.get_path_name().split('.')[0],'M_GC_MouthBed',textures)
        mesh=import_mesh('SM_GC_MouthBed',ground)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        assert eal.save_loaded_asset(mesh);apron.static_mesh_component.set_static_mesh(mesh);apron.static_mesh_component.set_material(0,ground)
        report['outlet_scope']='Existing scenery apron only, x<=-1250 m; native riverbed remains Landscape'
        match_outlet_gravel(textures)
    sheet=bylabel['Benmore_RS_WaterDomain'];sheet.set_editor_property('water_domain',ref);sheet.set_editor_property('surface_material_path',water.get_path_name())
    reground()
    reconcile_dressing()
    oldbridge=bylabel['Benmore_RL_Footbridge'];timber=oldbridge.static_mesh_component.get_material(0);mesh=import_mesh('SM_GC_Footbridge',timber)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);assert eal.save_loaded_asset(mesh);oldbridge.static_mesh_component.set_static_mesh(mesh)
    report['placement_after_dressing']=signature(True);assert signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail'])==report['roads_before']
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    report['saved_and_reloaded']=True;report['placement_after']=signature(True);report['roads_after']=signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail'])
    report['queries_after']=queries();report['native_support_after']=native_support()
    if COURSE_REVISION:report['outlet_support_after']=outlet_support()
    assert report['placement_after_dressing']==report['placement_after'];assert report['roads_before']==report['roads_after']
    assert all(q['covers'] for q in report['queries_after'])
    for q in report['queries_after']:
        if q['name'] in prepare['queries']:assert abs(q['surface_cm']-prepare['queries'][q['name']]['surface_m']*100)<.01
    provider=refs()['Benmore_RL_CrossingProfiles'];report['deformation_materials']=[s.get_editor_property('deform').get_editor_property('surface_material_path') for s in provider.get_editor_property('spec_asset').get_editor_property('spec').get_editor_property('sections')]
    assert all('M_GC_DeformField' in p for p in report['deformation_materials'])
    report['profiles_after']=profiles();assert report['profiles_after']==report['profiles_before']
    assert mel.get_material_property_input_node(u.load_asset(DEST+'/M_GC_DeformField'),u.MaterialProperty.MP_WORLD_POSITION_OFFSET)

def views():
    p=crossings[0]['center_m'];b=bedpoint;z=height(after,*b)
    # Identical world cameras for before and after, centered on the Gaea reach.
    def view(name,pos,target,focus):return (name,tuple(v*100 for v in pos),tuple(v*100 for v in target),tuple(v*100 for v in focus))
    result=[view('Ford',[p[0]+9,p[1]-12,height(after,p[0]+9,p[1]-12)+2.5],[p[0],p[1],p[2]+.2],p[:2]),
            view('Bed',[b[0]+7,b[1]-3,height(after,b[0]+7,b[1]-3)+2.4],[b[0],b[1],z+.15],b),
            view('Reach',[-625,170,55],[-635,245,21],[-635,245]),
            view('Plan',[-655,235,155],[-655,237,22],[-655,235])]
    if COURSE_REVISION:
        result.extend([view('Lower',[-1025,-5,165],[-1025,-5,4],[-1025,-5]),
            view('FullCourse',[-800,325,1250],[-800,325,15],[-1000,-35])])
    if MORPHOLOGY:
        result.extend([view('Bars',[-1000,-77,95],[-1000,-77,4],[-1000,-77]),
            view('BarGround',[-991,-102,height(after,-991,-102)+2.8],[-1009,-72,height(after,-1009,-72)+.2],[-1005,-79])])
    return result

def capture(suffix):
    bylabel=refs();sheet=bylabel['Benmore_RS_WaterDomain'];camera=bylabel['Benmore_RL_Camera_Ford']
    for name,pos,target,focus in views():
        sheet.preview_water_at(u.Vector2D(*focus),0,True)
        components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
        for c in components:
            m=c.get_material(0)
            if isinstance(m,u.MaterialInstanceDynamic):m.set_scalar_parameter_value('WaterTimeOverride',12)
        camera.set_actor_location(u.Vector(*pos),False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
        u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation());yield 35 if name=='Ford' else 15
        for bare in [False,True] if name in ['Bed','Plan','Lower','Bars','BarGround'] else [False]:
            if bare:
                for c in components:c.set_visibility(False,True)
                yield 2
            path=OUT/(name+('_Bare' if bare else '')+'_'+suffix+'.png');requested=time.time()
            u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);yield 3
            while not path.exists() or path.stat().st_mtime<requested:
                if time.time()-requested>60:raise RuntimeError('Screenshot timeout: '+str(path))
                yield 1
            report['images'].append(str(path))
            if bare:
                for c in components:c.set_visibility(True,True)

def verify_saved_height():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
    rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 10
    assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 10
    assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 5
    pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
    (OUT/'reloaded-native-height.r16').write_bytes(values.tobytes())
    report['reloaded_native_height_sha256']=hashlib.sha256(values.tobytes()).hexdigest();assert report['reloaded_native_height_sha256']==prepare['terrain_height_sha256']

def run():
    global grid
    # Work in the destination World after making the backup. These maps retain
    # cross-actor water references, so Save As from the backup cannot reliably
    # overwrite a separately loaded destination package.
    assert les.load_level(LEVEL)
    if VERIFY_ONLY:
        assert signature(True)==report['placement_after_dressing']
        assert signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail'])==report['roads_before']
        assert profiles()==report['profiles_before']
        assert json.loads(json.dumps(queries()))==report['queries_after']
        textures={name:u.load_asset(DEST+'/'+name) for name in ['T_CP_BedZones','T_CP_Shore','T_RL_Ecology','T_RL_Vegetation','T_RL_WaterMask','T_RS_DomainFlow','T_RS_DomainMask']+(['T_RL_Mouth'] if COURSE_REVISION else [])}
        if COURSE_REVISION:textures=extend_bed_materials(textures)
        clone_material(PILOT+'/M_CP_Terrain','M_GC_Terrain',textures)
        clone_material(PILOT+'/M_CP_DeformField','M_GC_DeformField',textures)
        clone_material(PILOT+'/M_CP_DomainRiver','M_GC_DomainRiver',textures)
        clone_material('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale/M_RS_DomainLake','M_GC_DomainLake',textures)
        if COURSE_REVISION:match_outlet_gravel(textures)
        report['aggregate_tint']='Sourced CC0 mineral grain, 78% neutral grey mix, cool RGB 1.08/1.10/1.12, gain 1.20; authored material tint only'
        report['window_optics_transition_m']=6
        clean_saved_water();set_ford_camera()
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
        assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
        verify_saved_water()
        assert json.loads(json.dumps(queries()))==report['queries_after']
        report['native_support_after']=native_support()
        if COURSE_REVISION:report['outlet_support_after']=outlet_support()
        yield from verify_saved_height()
        yield from capture('After')
        # Discard the preview overrides; the saved map retains asset parents.
        assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
        verify_saved_water()
        report['preview_material_reload_verified']=True
        report['drive_map_hash']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest();assert report['drive_map_hash']==prepare['source_original_drive_sha256']
        report['prepare']=prepare;report['ok']=True;return
    if not eal.does_asset_exist(BACKUP):
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),BACKUP);assert les.load_level(LEVEL)
    assert les.load_level(LEVEL);report['backup']=BACKUP;grid=before
    report['placement_before']=signature(True);report['roads_before']=signature(labels=['Benmore_ReferenceRoadAggregate','Benmore_RoadVergeDetail']);report['queries_before']=queries();report['native_support_before']=native_support();report['profiles_before']=profiles()
    baselinepath=OUT/'baseline-report.json'
    if not BASELINE_ONLY and baselinepath.exists():
        baseline=json.loads(baselinepath.read_text());assert baseline['ok']
        # Legacy baseline signatures included decomposed rotation/scale; that
        # hash cannot be compared with the XY-only signature after re-seating.
        assert baseline['placement_before']['count']==report['placement_before']['count'];assert baseline['queries_before']==json.loads(json.dumps(report['queries_before']))
        assert all(Path(p).exists() for p in baseline['images']);report['images']=baseline['images'];report['reused_baseline_capture']=True
    else:
        yield from capture('Before')
        baseline=dict(report);baseline['ok']=True
        baselinepath.write_text(json.dumps(baseline,indent=2))
    if BASELINE_ONLY:
        assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL);report['ok']=True;return
    # The baseline comparison above rejects an already installed course. If a
    # later capture fails after saving, use VerifyOnly rather than re-seating.
    assert les.load_level(LEVEL)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();land=next(a for a in act.get_all_level_actors() if isinstance(a,u.Landscape))
    tex=texture('T_GC_HeightRG',True)
    transfer=u.load_asset(DEST+'/M_GC_HeightTransfer') or assets.create_asset('M_GC_HeightTransfer',DEST,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(transfer)):mel.delete_material_expression(transfer,n)
    props(transfer,shading_model=u.MaterialShadingModel.MSM_UNLIT);g=Graph(transfer);n=g.node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR,'RGB')
    assert not mel.recompile_material(transfer);assert eal.save_loaded_asset(transfer)
    rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 20
    u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);yield 10
    u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);assert land.landscape_import_heightmap_from_render_target(rt,True,0);yield 25
    assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 10
    assert land.landscape_export_heightmap_to_render_target(rt,True,True)
    pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
    checksum=hashlib.sha256(values.tobytes()).hexdigest();assert checksum==prepare['terrain_height_sha256'];report['native_height_sha256']=checksum;grid=after
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0');install_assets()
    # Verify the serialized native bed again after the provider/material changes.
    yield from verify_saved_height()
    u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'grass.FlushCache');yield 20
    yield from capture('After')
    clean_saved_water();set_ford_camera()
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    verify_saved_water()
    assert signature(True)==report['placement_after_dressing']
    report['drive_map_hash']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest();assert report['drive_map_hash']==prepare['source_original_drive_sha256']
    report['prepare']=json.loads((OUT/'prepare-report.json').read_text());report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['ok']=False;report['error']=error;u.log_error(error)
    report['images']=list(dict.fromkeys(report['images']))
    (OUT/('baseline-report.json' if BASELINE_ONLY else 'install-report.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global next_at,busy
    if busy:return
    try:
        if time.monotonic()-started>1500:raise RuntimeError('Channel shape install timeout')
        if time.monotonic()<next_at:return
        busy=True;delay=next(gen);next_at=time.monotonic()+delay
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
if __name__=='__main__':
    gen=run();next_at=time.monotonic();started=next_at
    handle=u.register_slate_post_tick_callback(tick)
