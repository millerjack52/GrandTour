"""Map-wide woodland materials plus bounded camera-local fitted floor details."""
import unreal as u,json,sys,hashlib,shutil,time
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
import lidar_first_section as section
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/ForestGround'
OUT=ROOT/'Art/Export/LidarStudy/Place/ForestGround';QA=ROOT/'Saved/LidarAuthoringQA/ForestGround'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enabled():
    p=OUT/'recipe.json';return p.exists() and json.loads(p.read_text()).get('enabled',False)
def protect():
    QA.mkdir(parents=True,exist_ok=True);p=QA/'backup.json'
    if p.exists():return json.loads(p.read_text())
    folder=ROOT/'Saved/LidarAuthoringBackups'/('ForestGround-'+str(time.time_ns()));files={}
    content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
    paths=[content/'L_LidarStudy.umap',content/'M_Terrain.uasset',content/'M_Detail.uasset',ROOT/'Config/DefaultEngine.ini',ROOT/'Art/lidar_performance.json']
    paths+=list((content/'FirstSection').rglob('*.uasset'))
    for src in paths:
        rel=src.relative_to(ROOT);dst=folder/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);files[str(rel)]=sha(src)
    result=dict(folder=str(folder),files=files);p.write_text(json.dumps(result,indent=2));return result

SURFACE=r'''
float2 uv=(P.xy+185000)/370000;
float inside=(uv.x>0&&uv.x<1&&uv.y>0&&uv.y<1)?1:0;
Weight=Texture2DSample(Cover,View.MaterialTextureBilinearClampedSampler,uv).r*inside;
// Native worked mud and tyre colour/roughness retain precedence off the roads too.
float worked=saturate(State.a)*smoothstep(.05,1.5,max(0,-State.r));
Weight*=1-worked;
Height=0;Rough=OldRough;AO=OldAO;
[branch] if(Weight<.001)return Base;
float4 macro=Texture2DSample(Moss,View.MaterialTextureBilinearWrapedSampler,P.xy/2560);
float moss=macro.r,dist=length(Camera-P);
// Resolve small patches to their area average at distance, avoiding a spotted
// hillside once neither their relief nor fine texture can be read.
moss=lerp(moss,.230587,smoothstep(2200,6000,dist));
float3 colour=lerp(float3(.065,.042,.024),float3(.082,.116,.027),moss);
float rough=lerp(.86,.93,moss),occlusion=1;
[branch] if(dist<5000){
 float3 q=(P-float3(-45800,-31600,4800))/150;
 float3 w=pow(abs(normalize(N)),4);w/=max(.001,w.x+w.y+w.z);
 float4 peat=0,data=0;
 float2 coords[3]={q.yz,q.xz,q.xy};
 for(int i=0;i<3;i++){
  float a=i==0?w.x:i==1?w.y:w.z;
  [branch] if(a<.005)continue;
  peat+=Texture2DSample(Peat,View.MaterialTextureBilinearWrapedSampler,coords[i])*a;
  data+=Texture2DSample(Data,View.MaterialTextureBilinearWrapedSampler,coords[i])*a;
 }
 float near=1-smoothstep(3000,5000,dist);
 float3 green=lerp(float3(.042,.063,.014),float3(.132,.170,.036),smoothstep(.15,.85,peat.a));
 colour=lerp(colour,lerp(peat.rgb,green,moss),near);
 rough=lerp(rough,lerp(data.g,.92,moss),near);
 occlusion=lerp(1,lerp(data.b,data.a,moss),near);
 Height=lerp(data.r*2.2,peat.a*.85+macro.g*3,moss)*near;
}
Rough=lerp(OldRough,rough,Weight);AO=lerp(OldAO,occlusion,Weight);
return lerp(Base,colour,Weight);
'''

def wrap(name):
    m=u.load_asset(BASE+'/'+name);assert m and not m.get_editor_property('tangent_space_normal')
    from forest_shaders import connected_nodes
    def finish():
        import valley_ground
        if valley_ground.enabled():valley_ground.wrap(name)
        else:
            assert not mel.recompile_material(m);assets.save_loaded_asset(m,False)
    existing=[n for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FGSurface']
    if existing:
        assert len(existing)==1;existing[0].set_editor_property('code',SURFACE);finish();return
    properties=[u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialProperty.MP_NORMAL]
    sources=[(mel.get_material_property_input_node(m,p),str(mel.get_material_property_input_node_output_name(m,p))) for p in properties]
    keep={str(p):[mel.get_material_property_input_node(m,p),str(mel.get_material_property_input_node_output_name(m,p))] for p in [u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK,u.MaterialProperty.MP_EMISSIVE_COLOR]}
    g=Graph(m,'FGSurface');p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS);n=g.node(u.MaterialExpressionVertexNormalWS);cam=g.node(u.MaterialExpressionCameraPositionWS)
    paths={'Cover':(DEST+'/T_FG_Coverage',True),'Moss':(DEST+'/T_FG_Moss',True),'Peat':(section.DEST+'/PeatMoss/T_PM_PeatColour',False),'Data':(section.DEST+'/PeatMoss/T_PM_PeatData',True)}
    textures={key:g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(path),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR) for key,(path,linear) in paths.items()}
    state_sources=[x for x in mel.get_material_expressions(m) if isinstance(x,u.MaterialExpressionCustom) and 'RR1State' in [str(o.get_editor_property('output_name')) for o in x.get_editor_property('additional_outputs')]]
    assert len(state_sources)==1,(name,'native soil state')
    surf=g.custom(['P','N','Camera','Base','OldRough','OldAO','State',*paths],SURFACE,outputs=[(k,u.CustomMaterialOutputType.CMOT_FLOAT1) for k in ['Height','Rough','AO','Weight']])
    g.wire(state_sources[0],surf,'State','RR1State')
    for key,node in dict(P=p,N=n,Camera=cam,**textures).items():g.wire(node,surf,key)
    for key,(node,pin),default in zip(['Base','OldRough','OldAO'],sources[:3],[0,.9,1]):g.wire(node or g.scalar(default),surf,key,pin if node else '')
    g.output(surf,u.MaterialProperty.MP_BASE_COLOR);g.output(surf,u.MaterialProperty.MP_ROUGHNESS,'Rough');g.output(surf,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')
    import lidar_bank_material_polish as polish
    b=Graph(m,'FGBump');bump=b.custom(['H','P','N','Camera'],polish.BUMP)
    for key,node,pin in [('H',surf,'Height'),('P',p,''),('N',n,''),('Camera',cam,'')]:b.wire(node,bump,key,pin)
    blend=b.custom(['Old','New','Weight'],'return normalize(lerp(Old,New,Weight));')
    b.wire(sources[3][0] or n,blend,'Old',sources[3][1] if sources[3][0] else '');b.wire(bump,blend,'New');b.wire(surf,blend,'Weight','Weight');b.output(blend,u.MaterialProperty.MP_NORMAL)
    for prop,old in keep.items():
        pp=next(p for p in [u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK,u.MaterialProperty.MP_EMISSIVE_COLOR] if str(p)==prop)
        assert [mel.get_material_property_input_node(m,pp),str(mel.get_material_property_input_node_output_name(m,pp))]==old
    finish()

def stamp_material():
    m=u.load_asset(DEST+'/M_FG_Stamp')
    if not m:m=assets.duplicate_asset(section.DEST+'/PeatMoss/M_PM_Floor',DEST+'/M_FG_Stamp')
    assert m;g=Graph(m,'FGFit')
    # Rebuild only this wrapper, including recovery from an interrupted import.
    for node in list(mel.get_material_expressions(m)):
        if str(node.get_editor_property('desc'))=='FGFit':mel.delete_material_expression(m,node)
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    custom=[g.node(u.MaterialExpressionPerInstanceCustomData,data_index=i,const_default_value=0.) for i in range(4)]
    offset=g.custom(['P','X','Y','GX','GY'],'return float3(0,0,GX*(P.x-X)+GY*(P.y-Y));')
    for key,node in zip(['P','X','Y','GX','GY'],[p,*custom]):g.wire(node,offset,key)
    g.output(offset,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    normal=g.custom(['N','GX','GY'],'return normalize(float3(N.x-GX*N.z,N.y-GY*N.z,N.z));')
    g.wire(g.node(u.MaterialExpressionVertexNormalWS),normal,'N')
    # Non-Nanite ISMs expose custom data in the vertex shader; interpolate the
    # two slopes explicitly for the pixel normal correction.
    for key,source in [('GX',custom[2]),('GY',custom[3])]:
        interp=g.node(u.MaterialExpressionVertexInterpolator);g.wire(source,interp,'');g.wire(interp,normal,key)
    for node in mel.get_material_expressions(m):
        if isinstance(node,u.MaterialExpressionCustom) and str(node.get_editor_property('desc'))=='PMFloor':
            inputs=[str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs')]
            if 'N' in inputs:g.wire(normal,node,'N')
    fade=g.custom(['P','Fade'],'return Fade-frac(sin(dot(floor(P.xy*.3),float2(12.9898,78.233)))*43758.5453);',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(p,fade,'P');g.wire(g.node(u.MaterialExpressionPerInstanceFadeAmount),fade,'Fade');g.output(fade,u.MaterialProperty.MP_OPACITY_MASK)
    # The slope shear can move edge vertices by up to 1.15m. Explicit material
    # bounds prevent instance/shadow culling against the original flat mesh.
    props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.001,max_world_position_offset_displacement=120.)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False);return m

def prepare_views():
    protect();actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    from lidar_grounding import GroundSampler
    ground=GroundSampler(next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround)))
    existing=json.loads((ROOT/'Saved/LidarAuthoringQA/PerceivedDetail/cameras-proof.json').read_text())
    views=[v for v in existing if v['view'] in ['G01','B04','F01','F02']]
    for name,x,y in [('W01',-62058,6955),('W02',90061,60070),('W03',39655,-129987),('W04',-122219,82834)]:
        label='ForestGround_'+name;cam=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
        pos=[x,y,ground.height(x,y)+175];target=[x+260,y+320,ground.height(x+260,y+320)+15]
        if not cam:cam=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*pos))
        cam.set_actor_label(label);cam.set_actor_location(u.Vector(*pos),False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False);cam.camera_component.set_field_of_view(68.)
        views.append(dict(view=name,actor=cam.get_name(),position=pos,target=target,fov=68))
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    (QA/'cameras.json').write_text(json.dumps(views,indent=2))

def build_motion():
    import build_perceived_detail_motion as motion
    from lidar_grounding import GroundSampler
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    ground=GroundSampler(next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround)))
    v=next(v for v in json.loads((QA/'cameras.json').read_text()) if v['view']=='W02')
    x,y=v['position'][:2];poses=[]
    for frame,offset in [(0,0),(24,0),(144,1000),(260,0),(287,0)]:
        xx=x+offset*.63;yy=y+offset*.7766
        pos=[xx,yy,ground.height(xx,yy)+175]
        target=[xx+260,yy+320,ground.height(xx+260,yy+320)+15]
        poses.append((frame,pos,target))
    previous=motion.DEST
    try:
        motion.DEST=DEST
        result=motion.build('LS_ForestGroundReview','ForestGround_W02',poses)
    finally:motion.DEST=previous
    (QA/'motion-sequence.json').write_text(json.dumps(result,indent=2))
    return result

def install():
    backup=protect();before=section.snapshot();outside=section.outside_snapshot();assets.make_directory(DEST)
    for name in ['T_FG_Coverage','T_FG_Moss']:
        task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name)
        props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_MASKS,never_stream=True,max_texture_size=2048,lod_bias=0)
        if name.endswith('Coverage'):props(t,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
        assert assets.save_loaded_asset(t,False)
    for name in ['M_Terrain','M_Detail']:wrap(name)
    mat=stamp_material();sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);meshes=[]
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for k in range(3):
        name=f'SM_FG_Stamp_{k}';task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);task.options=opt
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);sm.remove_collisions(mesh)
        for lod in [1,2]:assert sm.import_lod(mesh,lod,str(OUT/(name+f'_LOD{lod}.fbx')))==lod
        # Sub-metre details must reach both reductions before the 30m cull.
        sm.set_lod_screen_sizes(mesh,[1.,.20,.09]);mesh.set_material(0,mat);assets.save_loaded_asset(mesh,False);meshes.append(mesh)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem);a=next((a for a in actors.get_all_level_actors() if isinstance(a,u.GTForestGroundDetails)),None)
    if not a:a=actors.spawn_actor_from_class(u.GTForestGroundDetails,u.Vector())
    a.modify();a.set_actor_label('LidarStudy_ForestGround');props(a,surface=next(x for x in actors.get_all_level_actors() if isinstance(x,u.GTLandscapeSurface)),meshes=meshes,material=mat,radius_cm=3600.,budget_ms=.6)
    assert a.import_coverage(str(OUT/'coverage.bin'))
    assert section.snapshot()==before and section.outside_snapshot()==outside
    protected=[]
    for rel,digest in backup['files'].items():
        if rel.endswith(('L_LidarStudy.umap','M_Terrain.uasset','M_Detail.uasset')):continue
        assert sha(ROOT/rel)==digest,rel;protected.append(rel)
    validation=section.validate();assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    result=dict(ok=True,local=before,outside=outside,validation=validation,protected_packages=len(protected),actor=a.get_name(),coverage=json.loads((OUT/'maps.json').read_text()),backup=backup['folder'],map_sha256=sha(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'))
    (QA/'installed.json').write_text(json.dumps(result,indent=2));(OUT/'recipe.json').write_text(json.dumps(dict(enabled=True,scope='Woodland across L_LidarStudy; forest material and camera-local decorations',source='Art/Unreal/forest_ground.py',runtime='Source/GrandTour/Terrain/GTForestGroundDetails.cpp',status='installed_validation_pending'),indent=2));print('FOREST_GROUND_INSTALLED',json.dumps(result))
