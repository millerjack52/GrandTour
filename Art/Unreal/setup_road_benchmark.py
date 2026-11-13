"""Import only the new road study and create an isolated review map. No shared masters or tuned maps changed."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
SRC=ROOT/'Art/Export/RoadBenchmark'
DEST='/Game/GrandTour/ArtTests/RoadBenchmark'
LEVEL=DEST+'/L_RoadBenchmark'
eal=u.EditorAssetLibrary; mel=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((SRC/'manifest.json').read_text())
report={'assets':[], 'instances':0, 'level':LEVEL}
report['environment_ism_flag_before']=bool(u.load_asset('/Game/GrandTour/Materials/M_GT_Environment').get_editor_property('used_with_instanced_static_meshes'))

def task(path,name,mesh=False):
    t=u.AssetImportTask(); t.filename=str(path); t.destination_path=DEST; t.destination_name=name
    t.automated=True; t.replace_existing=True; t.save=True
    if mesh:
        opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False
        opt.import_materials=False; opt.import_textures=False; opt.import_animations=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data; d.combine_meshes=True; d.convert_scene=True; d.convert_scene_unit=True
        d.auto_generate_collision=True; d.generate_lightmap_u_vs=False
        d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        t.options=opt
    tools.import_asset_tasks([t])
    a=u.load_asset(DEST+'/'+name)
    if not a: raise RuntimeError('Import missing: '+name)
    return a

texroot=ROOT/'Art/Textures/RoadBenchmark'
fine=task(texroot/'gravel_floor_04_diff_2k.jpg','T_RB_Fine')
coarse=task(texroot/'gravel_floor_02_diff_2k.jpg','T_RB_Coarse')
normal=task(texroot/'gravel_floor_02_nor_dx_2k.jpg','T_RB_Normal')
normal.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
normal.set_editor_property('srgb',False); normal.set_editor_property('flip_green_channel',False)
eal.save_loaded_asset(normal)

def expr(m,cls,x=0,y=0): return mel.create_material_expression(m,cls,x,y)
def make_material(name,color,ground=False,textured=False):
    path=DEST+'/'+name
    m=u.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    mel.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    mel.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE,True)
    m.set_editor_property('two_sided','Grass' in name)
    if textured:
        c=expr(m,u.MaterialExpressionCustom)
        c.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs=[]
        for key in ['Fine','Coarse','UV','VCol']:
            ci=u.CustomInput(); ci.set_editor_property('input_name',key); inputs.append(ci)
        c.set_editor_property('inputs',inputs)
        c.set_editor_property('code',
            'float lane=saturate((VCol.r-0.7)/0.27); '
            'float3 a=Texture2DSample(Coarse,CoarseSampler,UV).rgb; '
            'float3 b=Texture2DSample(Fine,FineSampler,UV).rgb; '
            'float v=dot(lerp(a,b,lane),float3(.2126,.7152,.0722)); '
            'float3 tint=float3(%f,%f,%f); return lerp(tint*.48,tint*1.45,saturate((v-.025)/.455))*VCol.rgb;'%color)
        for key,tex in [('Fine',fine),('Coarse',coarse)]:
            n=expr(m,u.MaterialExpressionTextureObjectParameter,-600,0)
            n.set_editor_property('parameter_name',key); n.set_editor_property('texture',tex); mel.connect_material_expressions(n,'',c,key)
        uv=expr(m,u.MaterialExpressionTextureCoordinate,-600,300)
        vc=expr(m,u.MaterialExpressionVertexColor,-600,400)
        assert mel.connect_material_expressions(uv,'',c,'UV')
        assert mel.connect_material_expressions(vc,'',c,'VCol')
        ns=expr(m,u.MaterialExpressionTextureSample,-400,600); ns.set_editor_property('texture',normal)
        ns.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        mel.connect_material_expressions(uv,'',ns,'UVs')
        # Low normal strength keeps aggregate legible without forcing photographic highlights.
        nm=expr(m,u.MaterialExpressionCustom,0,500)
        ci=u.CustomInput(); ci.set_editor_property('input_name','N'); nm.set_editor_property('inputs',[ci])
        nm.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        nm.set_editor_property('code','return normalize(lerp(float3(0,0,1),N,0.4));')
        mel.connect_material_expressions(ns,'RGB',nm,'N'); mel.connect_material_property(nm,'',u.MaterialProperty.MP_NORMAL)
    else:
        c=expr(m,u.MaterialExpressionConstant3Vector)
        c.set_editor_property('constant',u.LinearColor(*color,1))
    mel.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    r=expr(m,u.MaterialExpressionConstant,0,200); r.set_editor_property('r',.9)
    mel.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
    s=expr(m,u.MaterialExpressionConstant,0,300); s.set_editor_property('r',.15)
    mel.connect_material_property(s,'',u.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(m); eal.save_loaded_asset(m)
    return m

mats={'M_RB_Dirt':make_material('M_RB_Dirt',(.55,.45,.31),textured=True),
      'M_RB_Ground':make_material('M_RB_Ground',(.43,.39,.20),textured=True)}
for i,c in enumerate([(.30,.32,.32),(.41,.39,.33),(.22,.25,.27)]): mats['M_RB_Stone'+str(i)]=make_material('M_RB_Stone'+str(i),c)
for i,c in enumerate([(.40,.29,.10),(.57,.43,.17),(.29,.27,.11)]): mats['M_RB_Grass'+str(i)]=make_material('M_RB_Grass'+str(i),c)

meshes={}
for entry in manifest['assets']:
    name=entry['name']; m=task(SRC/(name+'.fbx'),name,True)
    for i,mat in enumerate(entry['materials']): m.set_material(i,mats[mat])
    bs=m.get_editor_property('body_setup')
    if 'Benchmark' in name: bs.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    ns=m.get_editor_property('nanite_settings'); ns.enabled=True; m.set_editor_property('nanite_settings',ns)
    eal.save_loaded_asset(m)
    b=m.get_bounds(); extent=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2]
    report['assets'].append({'name':name,'bounds_cm':extent,'triangles_source':entry['triangles']})
    meshes[name]=m
(SRC/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
assert 2350 < report['assets'][0]['bounds_cm'][0] < 2700, 'FBX centimetre scale mismatch: '+str(report['assets'][0])

les=u.get_editor_subsystem(u.LevelEditorSubsystem); act=u.get_editor_subsystem(u.EditorActorSubsystem)
if eal.does_asset_exist(LEVEL):
    if not les.load_level(LEVEL): raise RuntimeError('Could not open review map')
    for a in list(act.get_all_level_actors()):
        if a.get_actor_label().startswith(('RB_','RoadBenchmark_','SM_GT_RoadBenchmark_')):
            act.destroy_actor(a)
elif not les.new_level(LEVEL,False): raise RuntimeError('Could not create '+LEVEL)
def spawn(cls,label,xyz,rotation=None):
    a=act.spawn_actor_from_class(cls,u.Vector(*xyz),rotation or u.Rotator())
    a.set_actor_label(label); return a
for name in list(meshes)[:3]:
    a=spawn(u.StaticMeshActor,name,(0,0,0)); a.static_mesh_component.set_static_mesh(meshes[name])
    a.static_mesh_component.set_collision_profile_name('BlockAll')
    surface='Dirt'
    pm=u.load_asset('/Game/GrandTour/Terrain/Surfaces/PM_'+surface)
    if not pm: raise RuntimeError('Missing existing physical material '+surface)
    a.static_mesh_component.set_phys_material_override(pm)
group=spawn(u.Actor,'RoadBenchmark_Instances',(0,0,0))
for name in list(meshes)[3:]:
    for solid in [False,True]:
        rows=[p for p in manifest['placements'] if p['mesh']==name and p['collision']==solid]
        if not rows: continue
        transforms=[]
        for p in rows:
            x,y,z=p['location_m']; sc=p['scale']
            transforms.append(u.Transform(u.Vector(x*100,-y*100,z*100),u.Rotator(yaw=-p['yaw_deg']),u.Vector(sc,sc,sc)))
        comp=u.GTVegetationSubsystem.add_tagged_instances(group,meshes[name],transforms,'RoadBenchmark', 'BlockAll' if solid else 'NoCollision',True)
        assert comp.get_instance_count()==len(rows)
        report['instances']+=len(rows)
sun=spawn(u.DirectionalLight,'RB_Sun',(0,0,3000),u.Rotator(pitch=-40,yaw=-35))
lc=sun.get_component_by_class(u.DirectionalLightComponent); lc.set_intensity(8); lc.set_editor_property('atmosphere_sun_light',True)
sky=spawn(u.SkyLight,'RB_Sky',(0,0,3000)); sky.get_component_by_class(u.SkyLightComponent).set_editor_property('real_time_capture',True)
spawn(u.SkyAtmosphere,'RB_Atmosphere',(0,0,0))
spawn(u.PlayerStart,'RB_PlayerStart',(200,-40,80))
cam=spawn(u.CameraActor,'RB_DriverReview',(10,40,135),u.Rotator(pitch=-3,yaw=-13))
cam.camera_component.set_field_of_view(75)
spawn(u.CameraActor,'RB_Overview',(600,1300,1200),u.Rotator(pitch=-43,yaw=-66)).camera_component.set_field_of_view(60)
vol=spawn(u.PostProcessVolume,'RB_Exposure',(0,0,0)); vol.set_editor_property('unbound',True)
settings=vol.get_editor_property('settings')
for k,v in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',.25),('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',.25),('override_auto_exposure_bias',True),('auto_exposure_bias',0.)]: settings.set_editor_property(k,v)
vol.set_editor_property('settings',settings)
if not les.save_current_level(): raise RuntimeError('Map save failed')
report['ok']=report['instances']==436
(SRC/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
u.log('ROAD_BENCHMARK_IMPORT_OK '+json.dumps(report))
