"""Import only the new road study and create an isolated review map. No shared masters or tuned maps changed."""
import json,sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
SRC=ROOT/'Art/Export/RoadFordStyle'
DEST='/Game/GrandTour/ArtTests/RoadFordStyle'
LEVEL=DEST+'/L_RoadFordStyle'
eal=u.EditorAssetLibrary; mel=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((SRC/'manifest.json').read_text())
report={'assets':[], 'instances':0, 'level':LEVEL,'source_revision':manifest.get('revision','unversioned')}
assert manifest.get('vertex_color_encoding')=='LINEAR','Rebuild FBXs with linear vertex colours before importing'
report['vertex_color_encoding']=manifest['vertex_color_encoding']
report['environment_ism_flag_before']=bool(u.load_asset('/Game/GrandTour/Materials/M_GT_Environment').get_editor_property('used_with_instanced_static_meshes'))

def task(path,name,mesh=False):
    t=u.AssetImportTask(); t.filename=str(path); t.destination_path=DEST; t.destination_name=name
    t.automated=True; t.replace_existing=True; t.save=True
    if mesh:
        opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False
        opt.import_materials=False; opt.import_textures=False; opt.import_animations=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data; d.combine_meshes=True; d.convert_scene=True; d.convert_scene_unit=True
        d.auto_generate_collision='GrassCarpet' not in name; d.generate_lightmap_u_vs=False
        d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        entry=next((a for a in manifest['assets'] if a['name']==name),None)
        if entry and 'M_RF_TerrainBlend' in entry['materials']:
            d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
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
painted=[]
for file,name in [('T_Gravel_Painted_v1.png','T_RF_GravelPainted'),('T_Meadow_Painted_v1.png','T_RF_MeadowPainted')]:
    texture=task(ROOT/'Art/Textures/GroundPainterly'/file,name)
    texture.set_editor_property('srgb',True)
    texture.set_editor_property('max_texture_size',2048)
    texture.set_editor_property('compression_no_alpha',True)
    texture.set_editor_property('never_stream',False)
    texture.set_editor_property('power_of_two_mode',u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
    painted.append(texture); eal.save_loaded_asset(texture)
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from ground_surface_material import build as build_ground_surface

def expr(m,cls,x=0,y=0): return mel.create_material_expression(m,cls,x,y)
def make_material(name,color,ground=False,textured=False,roughness=.9,vertex=False,mud_blend=False,surface_blend=False):
    path=DEST+'/'+name
    m=u.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    mel.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    mel.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE,True)
    m.set_editor_property('two_sided','Grass' in name or 'WillowLeaf' in name)
    if surface_blend:
        return build_ground_surface(m,painted[0],painted[1],normal)
    if textured:
        c=expr(m,u.MaterialExpressionCustom)
        c.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs=[]
        for key in ['Fine','Coarse','UV','VCol'] + (['Moisture'] if mud_blend or surface_blend else []):
            ci=u.CustomInput(); ci.set_editor_property('input_name',key); inputs.append(ci)
        c.set_editor_property('inputs',inputs)
        c.set_editor_property('code',
            'float lane=saturate((VCol.r-0.7)/0.27); '
            'float3 a=Texture2DSample(Coarse,CoarseSampler,UV).rgb; '
            'float3 b=Texture2DSample(Fine,FineSampler,UV).rgb; '
            'float v=dot(lerp(a,b,lane),float3(.2126,.7152,.0722)); '
            'float3 tint=float3(%f,%f,%f); return lerp(tint*.48,tint*1.45,saturate((v-.025)/.455))*VCol.rgb'%color
            + ('*lerp(float3(1,1,1),float3(.44,.37,.29),Moisture);' if mud_blend else ';'))
        if surface_blend:
            c.set_editor_property('code',
                'float3 tex=Texture2DSample(Coarse,CoarseSampler,UV).rgb; '
                'float value=dot(tex,float3(.2126,.7152,.0722)); '
                'float detail=lerp(.58,1.48,saturate((value-.025)/.455)); '
                'return VCol.rgb*lerp(1.0,detail,Moisture);')
        for key,tex in [('Fine',fine),('Coarse',coarse)]:
            n=expr(m,u.MaterialExpressionTextureObjectParameter,-600,0)
            n.set_editor_property('parameter_name',key); n.set_editor_property('texture',tex); mel.connect_material_expressions(n,'',c,key)
        uv=expr(m,u.MaterialExpressionTextureCoordinate,-600,300)
        vc=expr(m,u.MaterialExpressionVertexColor,-600,400)
        assert mel.connect_material_expressions(uv,'',c,'UV')
        assert mel.connect_material_expressions(vc,'',c,'VCol')
        if mud_blend or surface_blend: assert mel.connect_material_expressions(vc,'A',c,'Moisture')
        ns=expr(m,u.MaterialExpressionTextureSample,-400,600); ns.set_editor_property('texture',normal)
        ns.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        mel.connect_material_expressions(uv,'',ns,'UVs')
        # Low normal strength keeps aggregate legible without forcing photographic highlights.
        nm=expr(m,u.MaterialExpressionCustom,0,500)
        ci=u.CustomInput(); ci.set_editor_property('input_name','N'); nm.set_editor_property('inputs',[ci])
        nm.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        nm.set_editor_property('code','return normalize(lerp(float3(0,0,1),N,0.4));')
        if surface_blend:
            strength=u.CustomInput(); strength.set_editor_property('input_name','Strength')
            nm.set_editor_property('inputs',[ci,strength])
            nm.set_editor_property('code','return normalize(lerp(float3(0,0,1),N,0.48*Strength));')
            assert mel.connect_material_expressions(vc,'A',nm,'Strength')
        mel.connect_material_expressions(ns,'RGB',nm,'N'); mel.connect_material_property(nm,'',u.MaterialProperty.MP_NORMAL)
    else:
        c=expr(m,u.MaterialExpressionConstant3Vector)
        c.set_editor_property('constant',u.LinearColor(*color,1))
    if vertex and not textured:
        vc=expr(m,u.MaterialExpressionVertexColor)
        mul=expr(m,u.MaterialExpressionMultiply)
        mel.connect_material_expressions(c,'',mul,'A'); mel.connect_material_expressions(vc,'',mul,'B')
        c=mul
    mel.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    if name=='M_RF_GrassCarpet':
        # Opaque geometry recedes into the ground before culling: no alpha overdraw.
        fade=expr(m,u.MaterialExpressionPerInstanceFadeAmount)
        vc=expr(m,u.MaterialExpressionVertexColor)
        wpo=expr(m,u.MaterialExpressionCustom)
        wpo.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs=[]
        for key in ['Fade','Height']:
            ci=u.CustomInput(); ci.set_editor_property('input_name',key); inputs.append(ci)
        wpo.set_editor_property('inputs',inputs)
        # 1.25 covers the maximum 1.12 instance scale, burying tips before cull.
        wpo.set_editor_property('code','return float3(0,0,-125.0*Height*(1.0-Fade));')
        mel.connect_material_expressions(fade,'',wpo,'Fade')
        mel.connect_material_expressions(vc,'A',wpo,'Height')
        mel.connect_material_property(wpo,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    r=expr(m,u.MaterialExpressionConstant,0,200); r.set_editor_property('r',roughness)
    mel.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
    s=expr(m,u.MaterialExpressionConstant,0,300); s.set_editor_property('r',.15)
    mel.connect_material_property(s,'',u.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(m); eal.save_loaded_asset(m)
    return m

mats={'M_RB_Dirt':make_material('M_RB_Dirt',(.55,.45,.31),textured=True),
      'M_RB_Ground':make_material('M_RB_Ground',(.43,.39,.20),textured=True)}
for i,c in enumerate([(.30,.32,.32),(.41,.39,.33),(.22,.25,.27)]): mats['M_RB_Stone'+str(i)]=make_material('M_RB_Stone'+str(i),c)
for i,c in enumerate([(.40,.29,.10),(.57,.43,.17),(.29,.27,.11)]): mats['M_RB_Grass'+str(i)]=make_material('M_RB_Grass'+str(i),c)

for spec in manifest['materials']:
    mats[spec['name']]=make_material(spec['name'],tuple(spec['color']),textured=spec['textured'],roughness=spec['roughness'],vertex=spec['vertex'],mud_blend=spec.get('mud_blend',False),surface_blend=spec.get('surface_blend',False))

meshes={}
for entry in manifest['assets']:
    name=entry['name']; m=task(SRC/(name+'.fbx'),name,True)
    for i,mat in enumerate(entry['materials']): m.set_material(i,mats[mat])
    if entry['static'] and entry['physical']:
        m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    carpet='GrassCarpet' in name
    ns=m.get_editor_property('nanite_settings'); ns.enabled=not carpet; m.set_editor_property('nanite_settings',ns)
    if carpet:
        # The StaticMeshEditorSubsystem is unavailable in Python commandlets.
        body=m.get_editor_property('body_setup')
        aggregate=body.get_editor_property('agg_geom')
        for shape in ['convex_elems','box_elems','sphere_elems','sphyl_elems']:
            aggregate.set_editor_property(shape,[])
        body.set_editor_property('agg_geom',aggregate)
    eal.save_loaded_asset(m)
    b=m.get_bounds(); dims=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2]
    hull_count=len(m.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems')) if entry.get('collision_hulls') else 0
    if entry.get('collision_hulls'): assert hull_count==entry['collision_hulls'], 'Missing trunk-only collision: '+name
    report['assets'].append(dict(name=name,bounds_cm=dims,triangles_source=entry['triangles'],verified_collision_hulls=hull_count))
    meshes[name]=m
assert 2599<report['assets'][0]['bounds_cm'][0]<2601, 'Dry road must measure 26 metres'

les=u.get_editor_subsystem(u.LevelEditorSubsystem); act=u.get_editor_subsystem(u.EditorActorSubsystem)
if eal.does_asset_exist(LEVEL):
    if not les.load_level(LEVEL): raise RuntimeError('Could not open '+LEVEL)
    for a in list(act.get_all_level_actors()):
        if a.get_actor_label().startswith('RF_'): act.destroy_actor(a)
elif not les.new_level(LEVEL,False): raise RuntimeError('Could not create '+LEVEL)

def spawn(cls,label,xyz,rotation=None):
    a=act.spawn_actor_from_class(cls,u.Vector(*xyz),rotation or u.Rotator())
    a.set_actor_label('RF_'+label); return a

for entry in manifest['assets']:
    if not entry['static']: continue
    a=spawn(u.StaticMeshActor,entry['name'],(0,0,0))
    a.static_mesh_component.set_static_mesh(meshes[entry['name']])
    a.static_mesh_component.set_collision_profile_name('BlockAll' if entry['physical'] else 'NoCollision')
    if entry['physical']:
        pm=u.load_asset('/Game/GrandTour/Terrain/Surfaces/PM_'+entry['physical'])
        assert pm, 'Physical material missing'
        a.static_mesh_component.set_phys_material_override(pm)
    else:
        a.static_mesh_component.set_cast_shadow(False)
group=spawn(u.Actor,'Dressing',(0,0,0))
for entry in manifest['assets']:
    if entry['static']: continue
    for solid in [False,True]:
        rows=[p for p in manifest['placements'] if p['mesh']==entry['name'] and p['collision']==solid]
        if not rows: continue
        transforms=[]
        for p in rows:
            x,y,z=p['location_m']; sc=p['scale']
            transforms.append(u.Transform(u.Vector(x*100,-y*100,z*100),u.Rotator(yaw=-p['yaw_deg']),u.Vector(sc,sc,sc)))
        carpet='GrassCarpet' in entry['name']
        comp=u.GTVegetationSubsystem.add_tagged_instances(group,meshes[entry['name']],transforms,'GrassCoverage' if carpet else 'RoadFordStyle','BlockAll' if solid else 'NoCollision',not carpet)
        if carpet:
            comp.set_cull_distances(2500,4200)
            comp.set_editor_property('affect_distance_field_lighting',False)
            comp.set_editor_property('visible_in_ray_tracing',False)
            comp.set_editor_property('receives_decals',False)
            report.setdefault('grass',[]).append(dict(mesh=entry['name'],instances=len(rows),start_cull_cm=comp.get_editor_property('instance_start_cull_distance'),end_cull_cm=comp.get_editor_property('instance_end_cull_distance'),cast_shadow=comp.get_editor_property('cast_shadow'),nanite=meshes[entry['name']].get_editor_property('nanite_settings').enabled))
        assert comp.get_instance_count()==len(rows)
        report['instances']+=len(rows)
sun=spawn(u.DirectionalLight,'Sun',(0,0,3000),u.Rotator(pitch=-40,yaw=-35))
lc=sun.get_component_by_class(u.DirectionalLightComponent); lc.set_intensity(9.5); lc.set_editor_property('atmosphere_sun_light',True)
sky=spawn(u.SkyLight,'Sky',(0,0,3000)); sky.get_component_by_class(u.SkyLightComponent).set_editor_property('real_time_capture',True)
sky.get_component_by_class(u.SkyLightComponent).set_intensity(1.25)
spawn(u.SkyAtmosphere,'Atmosphere',(0,0,0))
spawn(u.PlayerStart,'PlayerStart',(200,-21,170),u.Rotator(yaw=-6))
spawn(u.CameraActor,'DriverReview',(3000,-137,205),u.Rotator(pitch=-3,yaw=5)).camera_component.set_field_of_view(65)
spawn(u.CameraActor,'Overview',(2100,2800,2300),u.Rotator(pitch=-35,yaw=-52)).camera_component.set_field_of_view(55)
vol=spawn(u.PostProcessVolume,'Exposure',(0,0,0)); vol.set_editor_property('unbound',True)
settings=vol.get_editor_property('settings')
for k,v in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',.25),('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',.25),('override_auto_exposure_bias',True),('auto_exposure_bias',0.)]: settings.set_editor_property(k,v)
vol.set_editor_property('settings',settings)
assert les.save_current_level(), 'Save failed'
report.update(ok=report['instances']==len(manifest['placements']),water='STATIC ART PREVIEW',mud='STATIC ART PREVIEW; physical material assigned, deformation not connected')
(SRC/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
assert report['ok']
u.log('ROAD_FORD_STYLE_IMPORT_OK '+json.dumps(report))

