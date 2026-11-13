"""GS3 focused install on the saved LiDAR map; also reapplied by Polish.
New map-owned grass assets, existing wheel-contact shader retained in the near layer.
"""
import unreal as u
import json, hashlib, math
from pathlib import Path
from benmore_river_life_materials import Graph,props
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/LidarStudy/Place'; SRC=OUT/'GrassGS3'
BASE='/Game/GrandTour/ArtTests/LidarStudy'; DEST=BASE+'/GrassGS3'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary
VERSION='vq2-1'
# Shared field-scale colour variation; geometry and ground use the same coordinates.
FIELD='float field=.5+.30*sin(P.x*.00083+P.y*.00037)+.20*sin(P.y*.00131-P.x*.00023);'
NOISE='''struct GS3N {
float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
}; GS3N gn;'''
SWAY='''float2 m=P.xy*.01;
float w1=sin(6.2831853*(dot(m,float2(.9063,.4226))-1.2*Time)/4.5);
float w2=sin(6.2831853*(dot(m,float2(.7071,.7071))-2.2*Time)/13.);
float push=(5+5*w1+2*w2);
float3 sway=float3(.8192,.5736,-.12)*push;'''
NEAR_WIND=SWAY+'''
// GP4Wind applies the second alpha weight; keep removed patches/contact displacement intact.
return Removed>.5 ? Base : Base+sway*(.7*Scale*saturate(Parameters.VertexColor.a));'''
FAR_COLOUR=FIELD+'return C*lerp(.92,1.06,field);'
FAR_FADE=NOISE+'''float d=length(P.xy-Camera.xy)*.01;
float edge=(gn.n(P.xy*.001)-.5)*16;
float amount=smoothstep(25,38,d)*(1-smoothstep(90+edge,147,d))*saturate(Fade);
float ign=frac(52.9829189*frac(dot(Pixel.xy,float2(.06711056,.00583715))));
return amount>ign?1:0;'''
FAR_WIND=SWAY+'''float a=saturate(Parameters.VertexColor.a);
float d=length(P.xy-Camera.xy)*.01;
float range=1-smoothstep(100,140,d);
// Shrink into the textured ground before disappearing; no upright silhouette ring.
float settle=smoothstep(85,145,d);
return sway*.85*a*a*range+float3(0,0,-42*a*settle);'''
NEAR_CODE='''// GS3 grounded grass: authored blade colour, soft upward lighting, no artificial rim/glow.
float3 vc=Parameters.VertexColor.rgb;
'''+FIELD+'''
Normal=normalize(lerp(normalize(VN),float3(0,0,1),.85));
float3 col=vc*lerp(.92,1.06,field);
Sub=col*.12;Emissive=float3(0,0,0);
return col;'''
GROUND_CODE=NOISE+'''// GS3 shared pasture palette with flattened-grass/thatch detail.
float4 style=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+185000)/370000),0);
float peatRock=1-smoothstep(.6,.95,style.a);
float peatMask=saturate((style.b-.55)*3)*(1-style.g)*peatRock;
float pasW=smoothstep(.3,.8,style.g)*(1-saturate(style.r))*(1-peatMask);
'''+FIELD+'''
// Existing tile texture detail is normalised by its measured linear luminance,
// then compressed so pale baked highlights do not read as separate clumps.
float detail=dot(lerp(GrassA,GrassB,.20),float3(.2126,.7152,.0722))/.1864;
detail=clamp(1+(detail-1)*.38,.72,1.28);
float dryDetail=clamp(1+(dot(Dry,float3(.2126,.7152,.0722))/.2975-1)*.30,.78,1.22);
// World-space tuft/thatch variation survives the source texture's averaged mip.
// Filter the fine strand contrast as it falls below a pixel to avoid distant shimmer.
float2 m=P.xy*.01;
float footprint=max(length(ddx(m)),length(ddy(m)));
float tufts=gn.n(m/1.6)*.6+gn.n(m/0.45)*.4;
float strands=gn.n(float2(m.x/.12+m.y/.25,m.y/.7));
float textureVariation=lerp(.74,1.22,tufts)*lerp(1,lerp(.68,1.25,strands),1-smoothstep(.08,.4,footprint));
float3 green=float3(.15,.20,.078)*detail*textureVariation*lerp(.92,1.06,field);
float3 straw=float3(.285,.275,.15)*dryDetail;
float dryW=(1-smoothstep(.62,.82,style.g))*.65;
// Compensate only the existing downstream LidarCoverTint multiplier.
float3 cover=lerp(float3(1,1,1),float3(.85,1,.70),saturate(style.g));
return lerp(Native,lerp(green,straw,dryW)/cover,pasW);'''

def node_by_tag(mat,tag):
    nodes=[e for e in mel.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))==tag]
    assert len(nodes)==1,(mat.get_name(),tag,len(nodes))
    return nodes[0]

def configure(grass):
    """Optional override used by Install/Polish after the legacy grass setup."""
    near=[u.load_asset(DEST+'/SM_GS3_Near_'+c) for c in 'ABC']
    far=u.load_asset(DEST+'/SM_GS3_Far')
    mat=u.load_asset(DEST+'/M_GS3_Near');fm=u.load_asset(DEST+'/M_GS3_Far')
    verge=u.load_asset(DEST+'/SM_GS3_Verge');vm=u.load_asset(DEST+'/M_GS3_Verge')
    if not all(near) or not far or not mat or not fm or not verge or not vm:return None
    desired=dict(pasture_clump_mesh=near[0],pasture_clump_mesh_b=near[1],pasture_clump_mesh_c=near[2],
          grass_material=mat,rank_clump_mesh=verge,rank_material=vm,distant_pasture_mesh=far,distant_pasture_material=fm,
          distant_pasture_spacing_cm=200.,distant_pasture_end_cm=15000.,independent_grass_lod_scale=True,
          clump_spacing_cm=55.,clump_scale_min=.9,clump_scale_max=1.15,
          clump_stream_radius_cm=4600.,grass_cull_start_cm=3200.,grass_cull_end_cm=4000.,
          clump_lod1_distance_cm=700.,clump_lod2_distance_cm=1600.)
    changed={}
    for k,v in desired.items():
        old=grass.get_editor_property(k)
        same=math.isclose(old,v,rel_tol=1e-6,abs_tol=1e-5) if isinstance(v,float) else old==v
        if not same:changed[k]=v
    if changed:props(grass,**changed)
    return dict(actor_changed=bool(changed),near_lod_m=[7,16],near_fade_m=[32,40],far_fade_in_m=[25,38],far_fade_out_m=[90,150],far_height_blend_m=[85,145],far_spacing_m=2.,far_stream_guard_m=30)

def import_meshes():
    manifest=json.loads((SRC/'manifest.json').read_text());sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);result=[]
    for row in manifest['assets']:
        name=row['asset'];path=DEST+'/'+name
        digest=hashlib.sha256(b''.join((SRC/lod['file']).read_bytes() for lod in row['lods'])).hexdigest()
        mesh=u.load_asset(path)
        if not mesh or assets.get_metadata_tag(mesh,'GS3Source')!=digest:
            task=props(u.AssetImportTask(),filename=str(SRC/row['lods'][0]['file']),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
            opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
            props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,vertex_color_import_option=u.VertexColorImportOption.REPLACE,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path);assert mesh,path
            sizes=[1.,.35] if row['far'] else [1.,.35,.35*7/16]
            options=props(u.StaticMeshReductionOptions(),auto_compute_lod_screen_size=False,reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=1.,screen_size=s) for s in sizes])
            assert sm.set_lods(mesh,options)==len(sizes)
            for i,lod in enumerate(row['lods'][1:],1):assert sm.import_lod(mesh,i,str(SRC/lod['file']))==i
            assert sm.set_lod_screen_sizes(mesh,sizes)
            ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
            sm.remove_collisions(mesh)
            assets.set_metadata_tag(mesh,'GS3Source',digest);assets.save_loaded_asset(mesh,False)
        extent=mesh.get_bounds().box_extent*2
        assert 20<extent.z<100,(name,'height cm',extent.z)
        counts=[mesh.get_num_triangles(i) for i in range(sm.get_lod_count(mesh))]
        assert counts==[l['triangles'] for l in row['lods']],(name,counts)
        result.append(dict(asset=path,triangles=counts,dimensions_cm=[extent.x,extent.y,extent.z]))
    return result

def materials():
    # Duplicate only once; retain the native wheel/contact/deformation graph.
    path=DEST+'/M_GS3_Near';near=u.load_asset(path) or assets.duplicate_asset(BASE+'/M_LidarClump',path);assert near
    node_by_tag(near,'GS1Style').set_editor_property('code',NEAR_CODE)
    node_by_tag(near,'GS1Wind').set_editor_property('code',NEAR_WIND)
    g=Graph(near,'GS3Lighting')
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.88),(u.MaterialProperty.MP_SPECULAR,.06)]:
        node=mel.get_material_property_input_node(near,prop)
        if isinstance(node,u.MaterialExpressionConstant):node.set_editor_property('r',value)
        else:g.output(g.scalar(value),prop)
    assert not mel.recompile_material(near);assets.save_loaded_asset(near,False)
    far=u.load_asset(DEST+'/M_GS3_Far') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_GS3_Far',DEST,u.Material,u.MaterialFactoryNew())
    props(far,two_sided=True,tangent_space_normal=False,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mel.set_base_material_usage(far,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    nodes=list(mel.get_material_expressions(far))
    if nodes:
        # Stable input signatures allow updates in place, including the original GS3 graph.
        # Avoid deleting/recreating editor expression objects on every install.
        codes={('P','C'):FAR_COLOUR,('P','Camera','Fade','Pixel'):FAR_FADE,('P','Time','Camera'):FAR_WIND}
        found=set()
        for node in nodes:
            if isinstance(node,u.MaterialExpressionCustom):
                signature=tuple(str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs'))
                if signature in codes:
                    assert signature not in found,('duplicate GS3 far node',signature)
                    node.set_editor_property('code',codes[signature]);found.add(signature)
        assert found==set(codes),('incomplete GS3 far graph',found)
    else:
        g=Graph(far,'GS3Far');p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        cam=g.node(u.MaterialExpressionCameraPositionWS);vc=g.node(u.MaterialExpressionVertexColor)
        col=g.custom(['P','C'],FAR_COLOUR);g.wire(p,col,'P');g.wire(vc,col,'C');g.output(col,u.MaterialProperty.MP_BASE_COLOR)
        g.output(g.vector((0,0,1)),u.MaterialProperty.MP_NORMAL);g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.04),u.MaterialProperty.MP_SPECULAR)
        fade=g.custom(['P','Camera','Fade','Pixel'],FAR_FADE,u.CustomMaterialOutputType.CMOT_FLOAT1)
        for n,pin,out in [(p,'P',''),(cam,'Camera',''),(g.node(u.MaterialExpressionPerInstanceFadeAmount),'Fade',''),(g.node(u.MaterialExpressionScreenPosition),'Pixel','PixelPosition')]:g.wire(n,fade,pin,out)
        g.output(fade,u.MaterialProperty.MP_OPACITY_MASK)
        wind=g.custom(['P','Time','Camera'],FAR_WIND)
        g.wire(p,wind,'P');g.wire(g.node(u.MaterialExpressionTime),wind,'Time');g.wire(cam,wind,'Camera');g.output(wind,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    assert not mel.recompile_material(far);assets.save_loaded_asset(far,False)
    for name in ['Terrain','Detail']:
        mat=u.load_asset(BASE+'/M_'+name);assert mat
        node_by_tag(mat,'GP2cPasture').set_editor_property('code',GROUND_CODE)
        assert not mel.recompile_material(mat);assets.save_loaded_asset(mat,False)
    verge=verge_material()
    if (OUT/'reference-style.json').exists():
        import lidar_reference_style
        lidar_reference_style.grass_palette()
    return dict(near=near.get_path_name(),far=far.get_path_name(),verge=verge.get_path_name())

def verge_material():
    """Fine irregular blades use the same palette and travelling wind as pasture.
    Rank instances have no contact custom data, so their shader is self-contained.
    """
    path=DEST+'/M_GS3_Verge'
    m=u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_GS3_Verge',DEST,u.Material,u.MaterialFactoryNew())
    if assets.get_metadata_tag(m,'VQ2Verge')=='1':return m
    mel.delete_all_material_expressions(m);g=Graph(m,'VQ2Verge')
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    vc=g.node(u.MaterialExpressionVertexColor);vn=g.node(u.MaterialExpressionVertexNormalWS)
    col=g.custom(['P','C'],NOISE+FIELD+"float patches=gn.n(P.xy*.0025);return C*lerp(.85,1.08,patches)*lerp(.92,1.06,field);")
    g.wire(p,col,'P');g.wire(vc,col,'C');g.output(col,u.MaterialProperty.MP_BASE_COLOR)
    normal=g.custom(['N'],'return normalize(lerp(normalize(N),float3(0,0,1),.72));');g.wire(vn,normal,'N');g.output(normal,u.MaterialProperty.MP_NORMAL)
    wind=g.custom(['P','Time','Alpha'],NOISE+SWAY+"float patch=gn.n(P.xy*.0025);return (sway+float3(0,0,lerp(-10,8,patch)))*Alpha*Alpha;")
    g.wire(p,wind,'P');g.wire(g.node(u.MaterialExpressionTime),wind,'Time');g.wire(vc,wind,'Alpha','A');g.output(wind,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    fade=g.custom(['Fade','Pixel'],'float ign=frac(52.9829189*frac(dot(Pixel.xy,float2(.06711056,.00583715))));return Fade>ign?1:0;',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(g.node(u.MaterialExpressionPerInstanceFadeAmount),fade,'Fade');g.wire(g.node(u.MaterialExpressionScreenPosition),fade,'Pixel','PixelPosition');g.output(fade,u.MaterialProperty.MP_OPACITY_MASK)
    g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.04),u.MaterialProperty.MP_SPECULAR)
    props(m,two_sided=True,tangent_space_normal=False,blend_mode=u.BlendMode.BLEND_MASKED,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,dithered_lod_transition=True)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not mel.recompile_material(m);assets.set_metadata_tag(m,'VQ2Verge','1');assert assets.save_loaded_asset(m)
    return m

def install(import_assets=False):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    grass=next(a for a in actors if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
    author=next(a for a in actors if isinstance(a,u.GTProceduralGround))
    digest=str(author.output_digest)
    meshes=import_meshes() if import_assets else []
    mats=materials();cfg=configure(grass);assert cfg
    assert str(author.output_digest)==digest
    result=dict(ok=True,version=VERSION,meshes=meshes,materials=mats,ranges=cfg,ground_digest=digest,owner_accepted=False)
    (OUT/'grass.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    import time,traceback,gc
    report=dict(ok=False);busy=False
    def run():
        global report
        les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy');yield 1
        report=install(True);report['ok']=False
        if report['ranges']['actor_changed']:assert les.save_current_level()
        report.update(ok=True,saved=True,map_resaved=report['ranges']['actor_changed'])
        (OUT/'grass.json').write_text(json.dumps(report,indent=2));yield 2
        gc.collect();les.load_level('/Engine/Maps/Entry');yield 4
    steps=run();deadline=0;began=time.monotonic()
    def tick(dt):
        global busy,deadline,steps
        if busy:return
        busy=True
        try:
            assert time.monotonic()-began<1000
            if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
        except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
        except Exception:
            report.update(ok=False,error=traceback.format_exc());(OUT/'grass.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        finally:busy=False
    u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
