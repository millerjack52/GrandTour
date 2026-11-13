"""Small, bounded bank/outcrop trial using baked purchased Rock Master assets."""
import unreal as u,json,random,math
from pathlib import Path
from benmore_river_life_materials import props,Graph
from flora_drive_ground import floor_z
from make_mud_road import centre
O=Path('C:/GrandTour/Art/Export/FloraDrive/RockMaster');D='/Game/GrandTour/ArtTests/FloraDrive/RockMaster'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def install(world,spawn):
    data=json.loads((O/'export-report.json').read_text());assert data['ok']
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);at=u.AssetToolsHelpers.get_asset_tools();models=[];report={'assets':[],'placements':[]}
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for row in data['meshes']:
        name=row['mesh'];mesh=u.load_asset(D+'/'+name)
        if not mesh:
            job=props(u.AssetImportTask(),filename=str(O/(name+'.fbx')),destination_path=D,automated=True,save=True)
            opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
            props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=True,generate_lightmap_u_vs=False);job.options=opt;at.import_asset_tasks([job]);mesh=u.load_asset(D+'/'+name)
        assert mesh
        if sm.get_convex_collision_count(mesh)==0:assert sm.set_convex_decomposition_collisions(mesh,4,24,50000)
        if sm.get_lod_count(mesh)==1:
            opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False;opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in [(1.,1.),(.45,.16),(.18,.05)]];assert sm.set_lods(mesh,opts)==3
        textures={}
        for channel,file in row['textures'].items():
            t=u.load_asset(D+'/T_'+name+'_'+channel)
            if not t:
                job=props(u.AssetImportTask(),filename=str(O/file),destination_path=D,destination_name='T_'+name+'_'+channel,automated=True,save=True);at.import_asset_tasks([job]);t=u.load_asset(D+'/T_'+name+'_'+channel)
            assert t
            props(t,srgb=channel=='Colour',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if channel=='Colour' else u.TextureCompressionSettings.TC_MASKS,max_texture_size=row['texture_size'])
            if channel=='Normal':props(t,flip_green_channel=True)
            E.save_loaded_asset(t);textures[channel]=t
        m=u.load_asset(D+'/M_'+name) or at.create_asset('M_'+name,D,u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(m);g=Graph(m,'RockMasterTrial')
        c=g.node(u.MaterialExpressionTextureSample,texture=textures['Colour'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        n=g.node(u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        r=g.node(u.MaterialExpressionTextureSample,texture=textures['Roughness'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        tint=g.node(u.MaterialExpressionVectorParameter,parameter_name='RockTint',default_value=u.LinearColor(.82,.84,.75,1))
        col=g.custom(['C','Tint'],'float l=dot(C,float3(.2126,.7152,.0722));return lerp(l.xxx,C,.75)*Tint;');g.wire(c,col,'C');g.wire(tint,col,'Tint')
        rough=g.custom(['R'],'return clamp(R.r,.68,.96);',u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(r,rough,'R')
        g.output(col,u.MaterialProperty.MP_BASE_COLOR);g.output(n,u.MaterialProperty.MP_NORMAL);g.output(rough,u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.18),u.MaterialProperty.MP_SPECULAR)
        M.recompile_material(m);E.save_loaded_asset(m);mesh.set_material(0,m);E.save_loaded_asset(mesh);models.append(mesh)
        report['assets'].append(dict(name=name,triangles=row['triangles'],source_triangles=row['source_triangles'],lods=sm.get_lod_count(mesh),texture_size=row['texture_size'],collision_hulls=sm.get_convex_collision_count(mesh)))
    rng=random.Random(88431)
    # Three coherent exposures rather than isolated, evenly spaced boulders.
    groups=[(-1150,centre(-1150)+1350,820,0),(-350,centre(-350)+1500,970,1),(1150,centre(1150)-1450,930,2),(1550,1750,640,0)]
    count=0
    for cx,cy,width,variant in groups:
        for j in range(5):
            hero=j==0;mesh=models[variant if hero else (3+j%2)];b=mesh.get_bounds();span=width if hero else rng.uniform(120,330)
            x=cx+(0 if hero else rng.uniform(-width*.55,width*.55));y=cy+(0 if hero else rng.uniform(-width*.35,width*.35))
            if abs(y-centre(x))<520:continue
            scale=span/(2*max(b.box_extent.x,b.box_extent.y));z=floor_z(x,y)-(b.origin.z-b.box_extent.z)*scale-2*b.box_extent.z*scale*(.32 if hero else .42)
            a=spawn(u.StaticMeshActor,'RockMaster_'+str(count),(x,y,z),u.Rotator(yaw=rng.uniform(-25,25)+25*variant));a.static_mesh_component.set_static_mesh(mesh);a.set_actor_scale3d(u.Vector(scale,scale,scale))
            a.static_mesh_component.set_collision_profile_name('BlockAll');a.static_mesh_component.set_cast_shadow(True)
            props(a.static_mesh_component,visible_in_ray_tracing=False,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
            report['placements'].append(dict(mesh=mesh.get_name(),x=x,y=y,z=z,width_cm=span,hero=hero));count+=1
    report['instances']=count;report['source']='MeiU / Rock Master Tools';return report
