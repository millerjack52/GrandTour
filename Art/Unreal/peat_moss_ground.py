"""Photo-led peat and mask-aligned moss on the existing RS7 bank only."""
import unreal as u
import sys,json,shutil,time,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
import lidar_first_section as section
BASE=section.DEST;DEST=BASE+'/PeatMoss';OUT=section.OUT/'PeatMoss'
QA=ROOT/'Saved/LidarAuthoringQA/PeatMoss'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

def enabled():
    p=OUT/'recipe.json'
    return p.exists() and json.loads(p.read_text()).get('enabled',False)

SURFACE=r'''
float3 n=normalize(N),w=pow(abs(n),4);w/=max(.001,w.x+w.y+w.z);
float3 q=P-float3(-45800,-31600,4800);
float2 uv[3]={q.yz,q.xz,q.xy};
float4 peat=0,data=0,rn=0;float3 stone=0;
for(int i=0;i<3;i++){
 float weight=i==0?w.x:i==1?w.y:w.z;
 [branch] if(weight<.005) continue;
 peat+=Texture2DSample(Soil,SoilSampler,uv[i]/150)*weight;
 data+=Texture2DSample(SoilNH,SoilNHSampler,uv[i]/150)*weight;
 stone+=Texture2DSample(Rock,RockSampler,uv[i]/110).rgb*weight;
 rn+=Texture2DSample(RockNH,RockNHSampler,uv[i]/110)*weight;
}
float2 ab=float2(.6*q.x-.8*q.y,-.8*q.x-.6*q.y);
float2 bankUV=float2(ab.x/2200+.5,.5-ab.y/1560);
float2 cover=Texture2DSample(Coverage,CoverageSampler,bankUV).rg;
float rock=smoothstep(.47,.73,C.b/max(C.r,.001));
float moss=saturate(cover.r)*(1-rock);
float wet=cover.g*(1-moss)*(1-rock);
float micro=smoothstep(.15,.85,peat.a);
float3 mossColour=lerp(float3(.042,.063,.014),float3(.132,.170,.036),micro);
float3 earth=peat.rgb*(1-wet*.22);
float3 ground=lerp(earth,mossColour,moss);
float soilHeight=lerp(data.r*2.2,peat.a*.85,moss);
float rv=dot(stone,float3(.3,.5,.2));
float rockDetail=clamp((rv-.38)*3.2+1,.38,1.58);
float rockWet=(1-smoothstep(4400,4660,P.z))*(.65+.35*(1-rn.a));
float3 rockColour=C*rockDetail*lerp(.96,1.06,smoothstep(.12,.8,rn.b))*(1-rockWet*.08);
Height=lerp(soilHeight,rv*8+rn.b*.8,rock);
Rough=lerp(lerp(data.g,.92,moss)-wet*.22,clamp(.76+(1-rn.a)*.12-rockWet*.17,.56,.96),rock);
AO=lerp(lerp(data.b,data.a,moss),lerp(.82,1,rn.a),rock);
return lerp(ground,rockColour,rock);
'''

CONTACT=r'''
float2 q=P.xy-float2(-45800,-31600);
float2 ab=float2(.6*q.x-.8*q.y,-.8*q.x-.6*q.y);
float2 uv=float2(ab.x/2200+.5,.5-ab.y/1560);
float inside=(abs(ab.x)<1100 && abs(ab.y)<780)?1:0;
float occ=lerp(1,Texture2DSample(Contact,ContactSampler,uv).r,inside);
occ=lerp(1,occ,Strength);OutAO=min(OldAO,occ);
return OldColour*(.84+.16*occ);
'''

def ground():
    import lidar_bank_material_polish as polish
    m=u.load_asset(BASE+'/M_BankSurface');assert m
    mel.delete_all_material_expressions(m);g=Graph(m,'PMG');props(m,tangent_space_normal=False)
    p=g.node(u.MaterialExpressionWorldPosition);n=g.node(u.MaterialExpressionVertexNormalWS);vc=g.node(u.MaterialExpressionVertexColor)
    paths={'Soil':(DEST+'/T_PM_PeatColour',False),'SoilNH':(DEST+'/T_PM_PeatData',True),
           'Rock':('/Game/GrandTour/ArtTests/BenmoreWoodland/T_tiles_rock_slope__d_a',True),
           'RockNH':(BASE+'/PerceivedDetail/T_PD_RockNH',True),'Coverage':(DEST+'/T_PM_Coverage',True)}
    textures={}
    for key,(path,linear) in paths.items():
        texture=u.load_asset(path);assert texture,path
        textures[key]=g.node(u.MaterialExpressionTextureObject,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    surface=g.custom(['C','P','N',*paths],SURFACE,outputs=[(k,u.CustomMaterialOutputType.CMOT_FLOAT1) for k in ['Height','Rough','AO']])
    for key,node in dict(C=vc,P=p,N=n,**textures).items():g.wire(node,surface,key)
    g.output(surface,u.MaterialProperty.MP_BASE_COLOR);g.output(surface,u.MaterialProperty.MP_ROUGHNESS,'Rough');g.output(surface,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')
    bump=g.custom(['H','P','N','Camera'],polish.BUMP)
    g.wire(surface,bump,'H','Height');g.wire(p,bump,'P');g.wire(n,bump,'N');g.wire(g.node(u.MaterialExpressionCameraPositionWS),bump,'Camera');g.output(bump,u.MaterialProperty.MP_NORMAL)
    g.output(g.scalar(.18),u.MaterialProperty.MP_SPECULAR)
    mask=g.custom(['A','P','EdgeTex'],'float n=Texture2DSample(EdgeTex,EdgeTexSampler,(P.xy-float2(-45800,-31600))*.032).g;return A-n*.98;',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(vc,mask,'A','A');g.wire(p,mask,'P');g.wire(textures['Rock'],mask,'EdgeTex');g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
    contact=g.custom(['P','Contact','OldColour','OldAO','Strength'],CONTACT,outputs=[('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    g.wire(p,contact,'P');g.wire(surface,contact,'OldColour');g.wire(surface,contact,'OldAO','AO');g.wire(g.scalar(1),contact,'Strength')
    g.wire(g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/T_PM_Contact'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),contact,'Contact')
    g.output(contact,u.MaterialProperty.MP_BASE_COLOR);g.output(contact,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'OutAO')
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
    return m

def floor_material():
    m=u.load_asset(DEST+'/M_PM_Floor') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_PM_Floor',DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m);props(m,two_sided=True,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,tangent_space_normal=False,dithered_lod_transition=True)
    g=Graph(m,'PMFloor');vc=g.node(u.MaterialExpressionVertexColor);p=g.node(u.MaterialExpressionWorldPosition);n=g.node(u.MaterialExpressionVertexNormalWS)
    tex=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/T_PM_PeatColour'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    detail=g.custom(['C','P','N','Tex','AO'],r'''
float moss=smoothstep(1.1,1.3,C.g/max(C.r,.001));
float3 w=pow(abs(N),4);w/=max(.001,w.x+w.y+w.z);
float3 q=(P-float3(-45800,-31600,4800))/150;
float micro=Texture2DSample(Tex,TexSampler,q.yz).a*w.x+Texture2DSample(Tex,TexSampler,q.xz).a*w.y+Texture2DSample(Tex,TexSampler,q.xy).a*w.z;
Height=micro*.85*moss;
return C*lerp(1,lerp(.65,1.30,micro),moss)*(.72+.28*AO);
''',outputs=[('Height',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for key,value,out in [('C',vc,''),('P',p,''),('N',n,''),('Tex',tex,''),('AO',vc,'A')]:g.wire(value,detail,key,out)
    g.output(detail,u.MaterialProperty.MP_BASE_COLOR);g.output(vc,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'A')
    import lidar_bank_material_polish as polish
    bump=g.custom(['H','P','N','Camera'],polish.BUMP);g.wire(detail,bump,'H','Height');g.wire(p,bump,'P');g.wire(n,bump,'N');g.wire(g.node(u.MaterialExpressionCameraPositionWS),bump,'Camera');g.output(bump,u.MaterialProperty.MP_NORMAL)
    g.output(g.scalar(.91),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.12),u.MaterialProperty.MP_SPECULAR)
    assert not mel.recompile_material(m);assets.save_loaded_asset(m,False);return m

def protect():
    QA.mkdir(parents=True,exist_ok=True)
    if (QA/'backup.json').exists():return json.loads((QA/'backup.json').read_text())
    folder=ROOT/'Saved/LidarAuthoringBackups'/('PeatMoss-'+str(time.time_ns()));hashes={}
    paths=list((ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection').rglob('*.uasset'))
    paths.extend([ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',ROOT/'Config/DefaultEngine.ini',ROOT/'Art/lidar_performance.json'])
    for src in paths:
        rel=src.relative_to(ROOT);dst=folder/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);hashes[str(rel)]=hashlib.sha256(src.read_bytes()).hexdigest()
    record=dict(folder=str(folder),hashes=hashes);(QA/'backup.json').write_text(json.dumps(record,indent=2));return record

def run():
    backup=protect();before=section.snapshot();outside=section.outside_snapshot();assets.make_directory(DEST)
    bake=json.loads((OUT/'bake.json').read_text());placement=json.loads((section.QA/'placement.json').read_text())['placement']
    assert hashlib.sha256(json.dumps(placement,sort_keys=True).encode()).hexdigest()==bake['source_placement_sha256']
    for name in ['T_PM_PeatColour','T_PM_PeatData','T_PM_Coverage','T_PM_Contact']:
        task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=u.load_asset(DEST+'/'+name)
        props(texture,srgb=name.endswith('Colour'),compression_settings=u.TextureCompressionSettings.TC_DEFAULT if name.endswith('Colour') else u.TextureCompressionSettings.TC_MASKS,never_stream=True,max_texture_size=2048,lod_bias=0)
        if name.endswith(('Coverage','Contact')):props(texture,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
        assets.save_loaded_asset(texture,False)
    ground();mat=floor_material()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    task=props(u.AssetImportTask(),filename=str(OUT/'SM_PM_Floor.fbx'),destination_path=DEST,destination_name='SM_PM_Floor',automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);task.options=opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/SM_PM_Floor');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);sm.remove_collisions(mesh)
    for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,mat)
    assert 800<mesh.get_bounds().box_extent.x<1600
    # Two authored reductions preserve the large moss silhouettes at distance.
    for lod in [1,2]:
        path=OUT/f'SM_PM_Floor_LOD{lod}.fbx'
        if path.exists():assert sm.import_lod(mesh,lod,str(path))==lod
    if sm.get_lod_count(mesh)>1:sm.set_lod_screen_sizes(mesh,[1.,.35,.15])
    assert assets.save_loaded_asset(mesh,False)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem);actor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_RS7_FernFloor')
    c=actor.static_mesh_component;map_changed=c.static_mesh!=mesh
    if map_changed:actor.modify();c.set_static_mesh(mesh)
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);props(c,cast_shadow=True,cast_shadow_as_two_sided=True,affect_distance_field_lighting=False,visible_in_ray_tracing=False)
    assert section.snapshot()==before and section.outside_snapshot()==outside
    validation=section.validate()
    for rel,sha in backup['hashes'].items():
        if rel.endswith(('M_BankSurface.uasset','L_LidarStudy.umap')):continue
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==sha,rel
    if map_changed:assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    recipe=dict(enabled=True,status='local_candidate',source='Art/Unreal/peat_moss_ground.py',geometry='Art/Blender/build_peat_moss_floor.py',textures='Art/tools/build_peat_moss_textures.py',rebuild='powershell -NoProfile -File Art/rebuild_peat_moss.ps1',owner_visual_acceptance='PENDING',performance_acceptance='PENDING')
    (OUT/'recipe.json').write_text(json.dumps(recipe,indent=2))
    report=dict(ok=True,local=before,outside=outside,bake=bake,validation=validation,backup=backup['folder'],map_saved_this_run=map_changed,unchanged='Underlying bank mesh/collision, plants, other materials, renderer and exposure',lod_vertices=[sm.get_number_verts(mesh,i) for i in range(sm.get_lod_count(mesh))])
    (QA/'installed.json').write_text(json.dumps(report,indent=2));print('PEAT_MOSS_INSTALLED',json.dumps(report))
