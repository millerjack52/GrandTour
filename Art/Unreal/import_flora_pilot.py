"""Build an isolated purchased-foliage trial; production maps and materials are untouched."""
import unreal as u
import json,random,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LidarStudy/FloraPilot'
DEST='/Game/GrandTour/ArtTests/FloraPilot';LEVEL=DEST+'/L_FloraPilot'
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools()
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
report={'ok':False,'level':LEVEL,'meshes':[],'performance_verified':False,'production_level_modified':False}
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def expr(m,c,**kw):return props(mel.create_material_expression(m,c),**kw)
def wire(a,b,p,out=''):assert mel.connect_material_expressions(a,out,b,p),(p,out)
def output(n,p,out=''):assert mel.connect_material_property(n,out,p)
def scalar(m,name,value):return expr(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def fresh(name):
    m=u.load_asset(DEST+'/'+name) or at.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m);return m
def multiply(m,a,b,ao='',bo=''):
    n=expr(m,u.MaterialExpressionMultiply);wire(a,n,'A',ao);wire(b,n,'B',bo);return n
def foliage(name,tex,tint,gain):
    m=fresh(name);props(m,two_sided=True,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,opacity_mask_clip_value=.333)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    vc=expr(m,u.MaterialExpressionVertexColor)
    col=expr(m,u.MaterialExpressionVectorParameter,parameter_name='FoliageTint',default_value=u.LinearColor(*tint,1))
    base=multiply(m,col,vc);output(base,u.MaterialProperty.MP_BASE_COLOR)
    back=multiply(m,base,scalar(m,'Backlight',.4));output(back,u.MaterialProperty.MP_SUBSURFACE_COLOR)
    sample=expr(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='LeafMask',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    mask=multiply(m,sample,scalar(m,'MaskGain',gain),'R');output(mask,u.MaterialProperty.MP_OPACITY_MASK)
    output(scalar(m,'Roughness',.87),u.MaterialProperty.MP_ROUGHNESS);output(scalar(m,'Specular',.1),u.MaterialProperty.MP_SPECULAR)
    # Pinned root, inexpensive world-space sway; zero by default for this still-image comparison.
    wind=expr(m,u.MaterialExpressionCustom,code='float a=sin(T*Speed+P.x*.003+P.y*.002); return float3(a,a*.37,0)*Strength*Weight;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
              inputs=[props(u.CustomInput(),input_name=n) for n in ['T','Speed','P','Strength','Weight']])
    wire(expr(m,u.MaterialExpressionTime),wind,'T');wire(scalar(m,'WindSpeed',1.4),wind,'Speed');wire(expr(m,u.MaterialExpressionWorldPosition),wind,'P');wire(scalar(m,'WindStrengthCm',0.),wind,'Strength');wire(vc,wind,'Weight','A');output(wind,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(m);assert eal.save_loaded_asset(m);return m
def spawn(cls,label,pos=(0,0,0),rot=None):
    a=actors.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label('FloraPilot_'+label);return a
def place(mesh,label,pos,scale=1.,yaw=0.):
    a=spawn(u.StaticMeshActor,label,pos,u.Rotator(yaw=yaw));a.static_mesh_component.set_static_mesh(mesh);a.set_actor_scale3d(u.Vector(scale,scale,scale));a.static_mesh_component.set_collision_profile_name('NoCollision');return a
def run():
    eal.make_directory(DEST)
    assert les.load_level(LEVEL) if eal.does_asset_exist(LEVEL) else les.new_level(LEVEL)
    for a in actors.get_all_level_actors():
        if a.get_actor_label().startswith('FloraPilot_') or isinstance(a,u.GTDistanceStyleController):actors.destroy_actor(a)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    textures={}
    for filename in ['plant_0.png','shrubbery_0.png','grass_0.png']:
        name='T_Flora_'+Path(filename).stem
        task=props(u.AssetImportTask(),filename=str(OUT/filename),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        at.import_asset_tasks([task]);tex=u.load_asset(DEST+'/'+name);assert tex
        props(tex,srgb=True,compression_settings=u.TextureCompressionSettings.TC_DEFAULT,max_texture_size=2048)
        eal.save_loaded_asset(tex);textures[filename]=tex
    mats={
        'Leaf_0':foliage('M_Flora_Leaves',textures['plant_0.png'],(.0793,.1488,.0237),2.48),
        'Shrubbery':foliage('M_Flora_Shrub',textures['shrubbery_0.png'],(.0609,.1201,.0129),1.084),
        'Grass':foliage('M_Flora_Grass',textures['grass_0.png'],(.0759,.1512,.0155),1.264),
        'Grass.003':foliage('M_Flora_GrassClump',textures['grass_0.png'],(.0644,.1264,.0135),1.264),
        'Plant_0.001':foliage('M_Flora_Groundleaf',textures['plant_0.png'],(.0759,.1512,.0155),1.),
    }
    bark=fresh('M_Flora_Bark');vc=expr(bark,u.MaterialExpressionVertexColor)
    tint=expr(bark,u.MaterialExpressionVectorParameter,parameter_name='BarkTint',default_value=u.LinearColor(1,1,1,1));output(multiply(bark,vc,tint),u.MaterialProperty.MP_BASE_COLOR)
    output(scalar(bark,'Roughness',.94),u.MaterialProperty.MP_ROUGHNESS);output(scalar(bark,'Specular',.08),u.MaterialProperty.MP_SPECULAR)
    mel.set_material_usage(bark,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);mel.recompile_material(bark);eal.save_loaded_asset(bark);mats['Wood_material']=bark
    # Map-specific instances keep tint, mask, backlight and wind adjustable without editing masters.
    for key,master in list(mats.items()):
        name=master.get_name().replace('M_','MI_',1)+'_Trial'
        instance=u.load_asset(DEST+'/'+name) or at.create_asset(name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(instance,master);eal.save_loaded_asset(instance);mats[key]=instance
    models={}
    data=json.loads((OUT/'manifest.json').read_text())
    for row in data['meshes']:
        name=row['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=u.VertexColorImportOption.REPLACE)
        task.options=opt;at.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
        assert len(mesh.get_editor_property('static_materials'))==len(row['materials'])
        for idx,key in enumerate(row['materials']):mesh.set_material(idx,mats[key])
        ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True);sm.remove_collisions(mesh)
        build=sm.get_lod_build_settings(mesh,0);props(build,recompute_normals=False,recompute_tangents=True);sm.set_lod_build_settings(mesh,0,build)
        assert eal.save_loaded_asset(mesh);models[name]=mesh
        size=mesh.get_bounds().box_extent*2;actual=[size.x/100,size.y/100,size.z/100]
        assert all(abs(a-b)<.04 for a,b in zip(sorted(actual),sorted(row['size_m']))),(name,actual,row['size_m'])
        report['meshes'].append({'name':name,'triangles':mesh.get_static_mesh_description(0).get_triangle_count(),'sections':mesh.get_num_sections(0),'size_m':actual})
    floor=fresh('M_Flora_TrialFloor');output(expr(floor,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.10,.115,.08,1)),u.MaterialProperty.MP_BASE_COLOR);output(scalar(floor,'Roughness',.95),u.MaterialProperty.MP_ROUGHNESS);mel.recompile_material(floor);eal.save_loaded_asset(floor)
    plane=place(u.load_asset('/Engine/BasicShapes/Plane'),'Floor',(0,0,-2),100);plane.static_mesh_component.set_material(0,floor)
    tree=models['SM_Flora_Tree_E_001'];place(tree,'Tree',(0,0,0))
    rng=random.Random(619)
    for i in range(14):
        x=rng.uniform(-440,370);y=rng.uniform(-620,-260)
        place(models['SM_Flora_Shrubbery_003'],f'Shrub_{i}',(x,y,0),rng.uniform(.65,1.1),rng.uniform(0,360))
    for i in range(32):
        place(models['SM_Flora_Grass_003'],f'Grass_{i}',(rng.uniform(-470,470),rng.uniform(-680,-250),0),rng.uniform(.55,1.0),rng.uniform(0,360))
    for i in range(48):
        place(models['SM_Flora_Small_Plants_002'],f'Groundleaf_{i}',(rng.uniform(-400,400),rng.uniform(-740,-380),0),rng.uniform(1.,2.),rng.uniform(0,360))
    spawn(u.SkyAtmosphere,'Sky')
    sun=spawn(u.DirectionalLight,'Sun',(0,0,1500),u.Rotator(pitch=-38,yaw=115));props(sun.light_component,intensity=65000.,atmosphere_sun_light=True,light_source_angle=1.5)
    sky=spawn(u.SkyLight,'SkyLight',(0,0,900));props(sky.light_component,real_time_capture=True,intensity=1.2)
    pp=spawn(u.PostProcessVolume,'Exposure');props(pp,unbound=True,priority=500.,blend_weight=1.)
    ps=pp.get_editor_property('settings')
    for k,v in dict(auto_exposure_min_brightness=13.,auto_exposure_max_brightness=13.,auto_exposure_bias=0.,bloom_intensity=.05,lens_flare_intensity=0.,local_exposure_highlight_contrast_scale=1.,local_exposure_shadow_contrast_scale=1.).items():
        ps.set_editor_property('override_'+k,True);ps.set_editor_property(k,v)
    pp.set_editor_property('settings',ps)
    spawn(u.GTDistanceStyleController,'ReviewCamera')
    spawn(u.PlayerStart,'Start',(0,-1800,160))
    assert les.save_current_level()
    report.update(ok=True,wind_default=0,source='Purchased Flora Paint by Casey Sheep',status='Conversion pilot; no distant LODs or map rollout yet')
try:run()
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
def finish(dt):
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(finish)
