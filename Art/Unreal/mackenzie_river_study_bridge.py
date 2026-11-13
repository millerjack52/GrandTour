"""Reuse installed Benmore water and approved mud in the isolated river reach."""
import array,hashlib,json,math,re,struct,zlib,shutil,time
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph,props
from mackenzie_river_study_shape import height,centre
from mackenzie_river_study_materials import DEST
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MackenzieRiverStudy'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
UV='(P.xy-float2(-4000,-2000))/float2(8025,4025)'
reference={}

def verify_reference():
    path=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==reference['map_sha256'],'Benmore map changed during study build'

def survey_collision(world):
    """Trace in Play, where static mesh physics bodies are initialized."""
    rows=[];ignore=list(u.GameplayStatics.get_all_actors_of_class(world,u.Pawn))
    for x in [-1200,-1100,-1000]:
        for y in [-1100,-500,0,600,1100]:
            hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,2000),u.Vector(x,y,-1000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
            assert hit is not None,('Missing bed collision',x,y)
            p=next(v for v in hit.to_tuple() if isinstance(v,u.Vector))
            rows.append(dict(x=x,y=y,authored_cm=height(x,y),collision_cm=p.z,error_cm=p.z-height(x,y)))
    return rows

def repair_bed_collision():
    assert u.EditorLevelLibrary.get_game_world() is None,'Repair only with Play stopped'
    mesh=u.load_asset(DEST+'/SM_MRS_Bed');ns=mesh.get_editor_property('nanite_settings')
    path=ROOT/'Content/GrandTour/ArtTests/MackenzieRiverStudy/SM_MRS_Bed.uasset'
    backup=ROOT/'Saved/MackenzieRiverStudy'/str(time.time_ns());backup.mkdir(parents=True);shutil.copy2(path,backup/path.name)
    # A relative simplification tolerance on the 1.2 km context mesh can
    # flatten the small ford in its fallback, which also supplies collision.
    props(ns,fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES,fallback_percent_triangles=1.,fallback_relative_error=0.)
    u.get_editor_subsystem(u.StaticMeshEditorSubsystem).set_nanite_settings(mesh,ns,True)
    assert assets.save_loaded_asset(mesh)
    return str(backup/path.name)

def inspect_reference():
    global reference
    path=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    sheet=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='Benmore_RS_WaterDomain')
    reference={'source':sheet.get_editor_property('surface_material_path'),'ambient':sheet.get_editor_property('ambient_wave_material').get_path_name(),
               'map_sha256':digest,'settings':{k:sheet.get_editor_property(k) for k in ['field_cell_cm','max_sim_cells','wind_ripple_cm','rain_drop_cm','dry_cut_cm']}}
    m=u.load_asset(reference['source']);assert isinstance(m,u.Material)
    reference['custom_code']=[str(n.get_editor_property('code')) for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
    (OUT/'benmore-water-reference.json').write_text(json.dumps(reference,indent=2))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    return {k:v for k,v in reference.items() if k!='custom_code'}

def numeric_data():
    nx,ny=321,161;flow=bytearray();shore=bytearray();samples=array.array('f')
    for j in range(ny):
        flow.append(0);shore.append(0)
        for i in range(nx):
            x=-4000+(i+.5)*25;y=-2000+(j+.5)*25;z=height(x,y);depth=max(0,-z*.01)
            slope=math.hypot((height(x+5,y)-height(x-5,y))/10,(height(x,y+5)-height(x,y-5))/10)
            distance=-z*.01/max(.08,slope)
            speed=(.55+.38*math.exp(-((x+200)/550)**2))*min(1,depth/.18)
            dy=(centre(x+5)-centre(x-5))/10;vx=speed/math.sqrt(1+dy*dy);vy=vx*dy
            samples.extend((0,depth if depth>.005 else -1,vx,vy))
            def b(v):return round(max(0,min(1,v))*255)
            flow.extend((b(.5+vx/4),b(.5+vy/4),b(depth/2),b(.14 if depth<.30 else .025)))
            shore.extend((b(.5+distance/4),b(.5+distance/4),0,255))
    def png(name,raw):
        def chunk(k,data):return struct.pack('>I',len(data))+k+data+struct.pack('>I',zlib.crc32(k+data)&0xffffffff)
        path=OUT/(name+'.png');path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',nx,ny,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
        task=props(u.AssetImportTask(),filename=str(path),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
        props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True)
        assert assets.save_loaded_asset(t);return t
    textures={'flow':png('T_MRS_Flow',flow),'shore':png('T_MRS_Shore',shore)}
    path=OUT/'water-domain.bin';path.write_bytes(struct.pack('<5i3f',0x47545744,nx,ny,1,1,-4000,-2000,25)+samples.tobytes()+b'\0')
    domain=u.load_asset(DEST+'/DA_MRS_WaterDomain')
    if not domain:
        factory=props(u.DataAssetFactory(),data_asset_class=u.GTWaterDomain)
        domain=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_MRS_WaterDomain',DEST,u.GTWaterDomain,factory)
    assert domain.import_bake(str(path));assert assets.save_loaded_asset(domain)
    return textures,domain

def water():
    textures,domain=numeric_data();path=DEST+'/M_MRS_BenmoreWater'
    source=u.load_asset(reference['source']);m=u.load_asset(path) or assets.duplicate_asset(reference['source'].split('.')[0],path);assert m
    originals=[n for n in mel.get_material_expressions(source) if isinstance(n,u.MaterialExpressionCustom)]
    copies=[n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
    assert len(originals)==len(copies)
    replacements=0
    for a,b in zip(originals,copies):
        code=str(a.get_editor_property('code'))
        # Localize authored data coordinates. The study bake is much shorter
        # than Benmore's: soften its edge instead of showing a straight strip
        # where current-driven waves meet the visual-only outer reach.
        code,count=re.subn(r'float2 (buv|bankUV|shapeBankUV)=[^;]+;',lambda q:'float2 '+q.group(1)+'='+UV+';',code)
        code=code.replace('float inBake=step(0,min(buv.x,buv.y))*step(max(buv.x,buv.y),1);',
            'float2 bakeEdge=min(buv,1-buv)*float2(8025,4025);\nfloat inBake=smoothstep(0,600,min(bakeEdge.x,bakeEdge.y));')
        replacements+=count;b.set_editor_property('code',code)
    assert replacements>=3,replacements
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='RiverStudyBindings':mel.delete_material_expression(m,n)
    g=Graph(m,'RiverStudyBindings');pixel=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
    g.wire(g.scalar(1),pixel,'OldMask')
    for n in mel.get_material_expressions(m):
        if isinstance(n,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
            t=n.get_editor_property('texture')
            if t and ('DomainFlow' in t.get_name() or t.get_name()=='T_RL_Flow'):n.set_editor_property('texture',textures['flow'])
            if t and t.get_name() in ('T_SR_Shore','T_CP_Shore'):n.set_editor_property('texture',textures['shore'])
    errors=mel.recompile_material(m);assert not errors,list(errors);assert assets.save_loaded_asset(m)
    return m,domain,u.load_asset(reference['ambient'])

def mud_margin(m):
    from benmore_mud_materials import CODE,SOURCE
    g=Graph(m,'RiverStudyApprovedMud');f1=u.CustomMaterialOutputType.CMOT_FLOAT1
    inputs={}
    for pin,prop,default in [('Base',u.MaterialProperty.MP_BASE_COLOR,0),('OldN',u.MaterialProperty.MP_NORMAL,0),('OldR',u.MaterialProperty.MP_ROUGHNESS,.9),('OldS',u.MaterialProperty.MP_SPECULAR,.3),('OldAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION,1)]:
        n=mel.get_material_property_input_node(m,prop);out=mel.get_material_property_input_node_output_name(m,prop)
        passthrough=g.custom(['Value'],'return Value;',u.CustomMaterialOutputType.CMOT_FLOAT3 if pin in ('Base','OldN') else f1)
        g.wire(n or g.scalar(default),passthrough,'Value',out);inputs[pin]=passthrough
    for pin,cls in [('P',u.MaterialExpressionWorldPosition),('N',u.MaterialExpressionVertexNormalWS),('Eye',u.MaterialExpressionCameraVectorWS),('Camera',u.MaterialExpressionCameraPositionWS)]:inputs[pin]=g.node(cls)
    for prefix,asset in [('Wet','brown_mud_02'),('Dry','mud_cracked_dry_03')]:
        for suffix,kind in [('Color','Diffuse'),('Height','Displacement'),('Normal','nor_dx'),('Rough','Rough'),('AO','AO')]:
            t=u.load_asset(SOURCE+'/T_'+asset+'_'+kind);assert t
            sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='Color' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
            inputs[prefix+suffix]=g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=sampler)
    start=CODE.index('[branch] if(coverage');code='''
Normal=OldN;Rough=OldR;Specular=OldS;AO=OldAO;
float pocket=exp(-pow((P.x-640)/490,2)-pow((P.y+425)/250,2));
float margin=exp(-pow((P.x+900)/460,2)-pow((P.y+530)/220,2))*.78;
float coverage=smoothstep(.16,.78,max(pocket,margin))*smoothstep(-8,12,P.z);
float silt=coverage;
'''+CODE[start:]
    code=code.replace('float wet=.9*smoothstep(.10,.55,silt);','float wet=lerp(.93,.20,smoothstep(3,65,P.z));')
    n=g.custom(list(inputs),code,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',f1),('Specular',f1),('AO',f1)])
    for pin,node in inputs.items():g.wire(node,n,pin)
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'Normal'),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_SPECULAR,'Specular'),(u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')]:g.output(n,prop,out)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
