"""Long-range forest-floor treatment, reviewed from valley overlooks."""
import unreal as u,json,sys,shutil,hashlib,time,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/ValleyGround'
OUT=ROOT/'Art/Export/LidarStudy/Place/ValleyGround';QA=ROOT/'Saved/LidarAuthoringQA/ValleyGround'
OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
from benmore_river_life_materials import Graph,props
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enabled():
    path=OUT/'recipe.json'
    return path.exists() and json.loads(path.read_text()).get('enabled',False)

FAR=r'''
// At valley range replace the averaged close-up moss with metre-scale cover.
// The field follows existing trees; it is not a directional shadow bake.
float distant=smoothstep(4500,14000,dist);
[branch] if(distant>.001){
 float4 field=Texture2DSample(Valley,View.MaterialTextureBilinearClampedSampler,uv);
 float3 peatFar=lerp(float3(.042,.031,.020),float3(.080,.060,.034),field.b);
 float3 greenFar=lerp(float3(.043,.067,.020),float3(.095,.125,.038),field.b);
 float3 floorFar=lerp(peatFar,greenFar,smoothstep(.32,.66,field.g));
 // Non-repeating fine cover occupies the same field's alpha channel.
 // Mipmaps resolve subpixel features to an average at the longest ranges.
 floorFar*=lerp(.72,1.30,field.a)*lerp(1.02,.34,field.r);
 colour=lerp(colour,floorFar,distant);
 occlusion=lerp(occlusion,lerp(1,.53,field.r),distant);
 rough=lerp(rough,.91,distant);
 Height=lerp(Height,(field.g-.5)*65+field.r*40+field.a*22,distant);
}
'''

def wrap(name):
    import forest_ground
    from forest_shaders import connected_nodes
    import lidar_bank_material_polish as polish
    m=u.load_asset(BASE+'/'+name);assert m
    nodes=connected_nodes(m)
    surface=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FGSurface')
    inputs=list(surface.get_editor_property('inputs'))
    if not any(str(i.get_editor_property('input_name'))=='Valley' for i in inputs):
        inputs.append(props(u.CustomInput(),input_name='Valley'));surface.set_editor_property('inputs',inputs)
    texture=next((n for n in nodes if isinstance(n,u.MaterialExpressionTextureObject) and str(n.get_editor_property('desc'))=='ValleyFloorTexture'),None)
    g=Graph(m,'ValleyFloorTexture')
    if not texture:texture=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/T_VG_Floor'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.wire(texture,surface,'Valley')
    original=forest_ground.SURFACE
    surface.set_editor_property('code',original.replace('Rough=lerp(OldRough,rough,Weight);',FAR+'\nRough=lerp(OldRough,rough,Weight);'))
    bump=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FGBump' and 'float3 grad=' in n.get_editor_property('code'))
    code=polish.BUMP.replace('grad*=fade*.85;', 'float distant=smoothstep(4500,14000,length(Camera-P))*(1-smoothstep(100,600,footprint));\ngrad*=fade*.85+distant*.55;')
    bump.set_editor_property('code',code)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
    stats=mel.get_statistics(m)
    return dict(material=name,pixel_instructions=stats.num_pixel_shader_instructions,texture_samples=stats.num_pixel_texture_samples)

def install():
    assets.make_directory(DEST)
    task=props(u.AssetImportTask(),filename=str(OUT/'T_VG_Floor.png'),destination_path=DEST,destination_name='T_VG_Floor',automated=True,replace_existing=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=u.load_asset(DEST+'/T_VG_Floor');assert texture
    props(texture,srgb=False,compression_settings=u.TextureCompressionSettings.TC_MASKS,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,never_stream=True,max_texture_size=4096,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
    assert assets.save_loaded_asset(texture,False)
    materials=[wrap(name) for name in ['M_Terrain','M_Detail']]
    prepared=json.loads((QA/'prepared.json').read_text());count=0
    for rel,digest in prepared['protected'].items():
        if rel.endswith(('M_Terrain.uasset','M_Detail.uasset')):continue
        assert sha(ROOT/rel)==digest,rel;count+=1
    result=dict(ok=True,materials=materials,protected_packages=count,map_and_planting_unchanged=True,field=json.loads((OUT/'map.json').read_text()))
    (QA/'installed.json').write_text(json.dumps(result,indent=2));return result
def prepare():
    from lidar_grounding import GroundSampler
    import lidar_first_section as section
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    ground=GroundSampler(next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround)))
    backup=ROOT/'Saved/LidarAuthoringBackups'/('ValleyGround-'+str(time.time_ns()));backup.mkdir(parents=True)
    previous=json.loads((ROOT/'Saved/LidarAuthoringQA/ForestShaders/backup.json').read_text())
    protected={}
    for rel in previous['files']:
        src=ROOT/rel;dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);protected[rel]=sha(src)
    (QA/'backup.json').write_text(json.dumps(dict(folder=str(backup),files=protected),indent=2))
    before=section.snapshot();outside=section.outside_snapshot()
    specifications=[
      ('V01',[-67505,49841,38582],[-45505,841,9582],'Broad woodland valley, roughly 600 m to centre'),
      ('V02',[-88000,-10000,ground.height(-88000,-10000)+14000],[-47000,-32000,ground.height(-47000,-32000)+800],'Across the river valley, roughly 450 m to centre'),
      ('V03',[-110000,70000,ground.height(-110000,70000)+40000],[-35000,-60000,ground.height(-35000,-60000)+1000],'Long valley view, roughly 1.5 km to centre')]
    views=[]
    for name,pos,target,description in specifications:
        label='ValleyGround_'+name
        cam=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
        if not cam:cam=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*pos))
        cam.set_actor_label(label);cam.set_actor_location(u.Vector(*pos),False,True)
        cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
        cam.camera_component.set_field_of_view(68.)
        views.append(dict(view=name,actor=cam.get_name(),position=pos,target=target,fov=68,description=description))
    views += [v for v in json.loads((ROOT/'Saved/LidarAuthoringQA/ForestShaders/cameras.json').read_text()) if v['view']=='G01']
    seeds=[]
    for a in actors.get_all_level_actors():
        if a.get_actor_label()!='LidarStudy_Forest':continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            m=c.static_mesh
            if not m or not m.get_name().startswith('SM_Canopy_') or m.get_name().endswith('_3'):continue
            box=m.get_bounding_box();radius=max(box.max.x-box.min.x,box.max.y-box.min.y)*.5
            for i in range(c.get_instance_count()):
                tf=c.get_instance_transform(i,True);p=tf.translation;s=tf.scale3d
                seeds.append([round(p.x,2),round(p.y,2),round(radius*max(s.x,s.y),2)])
    assert section.snapshot()==before and section.outside_snapshot()==outside
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    (QA/'cameras.json').write_text(json.dumps(views,indent=2));(OUT/'canopy-seeds.json').write_text(json.dumps(seeds,separators=(',',':')))
    protected['Content\\GrandTour\\ArtTests\\LidarStudy\\L_LidarStudy.umap']=sha(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap')
    (QA/'prepared.json').write_text(json.dumps(dict(ok=True,local=before,outside=outside,protected=protected,canopy_count=len(seeds)),indent=2))
