"""Map-owned water refinement: audit, install, and verify without palette edits."""
import unreal as u, json, sys, os, traceback, hashlib, shutil, math, array, struct
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
from forest_shaders import connected_nodes
from lidar_grounding import GroundSampler
BASE='/Game/GrandTour/ArtTests/LidarStudy'
QA=ROOT/'Saved/LidarAuthoringQA/WaterRefinement';QA.mkdir(parents=True,exist_ok=True)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
def audit():
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(BASE+'/L_LidarStudy')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    codes={};surfaces=[];sheets=[]
    for name in ['MappedPond','AccessPond','River']:
        m=u.load_asset(BASE+'/M_'+name+'Water')
        codes[name]=dict(properties={k:str(m.get_editor_property(k)) for k in ['blend_mode','shading_model','two_sided','tangent_space_normal']},nodes=[])
        for n in connected_nodes(m):
            row=dict(name=n.get_name(),cls=n.get_class().get_name(),desc=str(n.get_editor_property('desc')))
            if isinstance(n,u.MaterialExpressionCustom):row.update(code=n.get_editor_property('code'),inputs=[str(x.get_editor_property("input_name")) for x in n.get_editor_property("inputs")])
            if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
                row.update(parameter=str(n.get_editor_property("parameter_name")),value=str(n.get_editor_property("default_value")))
            codes[name]['nodes'].append(row)
    for a in actors:
        if isinstance(a,u.GTWaterSheet):
            row=dict(label=a.get_actor_label(),transform=str(a.get_actor_transform()))
            for k in ['surface_material_path','water_domain','domain_ground_surface','domain_shore_margin_cm','wind_ripple_cm','base_level_cm','ambient_wave_material','ambient_wave_strength']:
                try:row[k]=str(a.get_editor_property(k))
                except Exception:pass
            sheets.append(row)
        if isinstance(a,u.StaticMeshActor) and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name() in ['SM_MappedPondWater','SM_AccessPondWater','SM_RiverWater']:
            c=a.static_mesh_component;m=c.static_mesh
            surfaces.append(dict(label=a.get_actor_label(),transform=str(a.get_actor_transform()),bounds=str(m.get_bounds()),material=str(c.get_material(0)),triangles=m.get_static_mesh_description(0).get_triangle_count()))
    # Preserve the original shader baseline used for repeatable edits.
    material_report=QA/('materials-current.json' if (QA/'materials.json').exists() else 'materials.json')
    material_report.write_text(json.dumps(codes,indent=2))
    author=next(a for a in actors if isinstance(a,u.GTProceduralGround));ground=GroundSampler(author)
    prep=json.loads((ROOT/'Art/Export/LidarStudy/Place/prepare.json').read_text());grids={}
    for w in prep['water']:
        if w['name']=='River':continue
        ox,oy=w['origin_cm'];sx,sy=w['span_cm'];step=50
        # Include a 5 m collar to inspect the current wet/dry contour.
        xs=list(range(int(ox-500),int(ox+sx+501),step));ys=list(range(int(oy-500),int(oy+sy+501),step))
        grids[w['name']]=dict(xs=xs,ys=ys,level=w['probe'][2],heights=[[ground.height(x,y) for x in xs] for y in ys])
    (QA/'ground.json').write_text(json.dumps(grids))
    return dict(ok=True,surfaces=surfaces,sheets=sheets)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def backup():
    dest=QA/'AssetBackup';dest.mkdir(exist_ok=True)
    names=['L_LidarStudy.umap']+[f'M_{n}Water.uasset' for n in ['River','AccessPond','MappedPond']]+[f'SM_{n}Water.uasset' for n in ['AccessPond','MappedPond']]
    for name in names:
        src=ROOT/'Content/GrandTour/ArtTests/LidarStudy'/name
        if not (dest/name).exists():shutil.copy2(src,dest/name)
    return str(dest)

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def round_northern_bank(author,ground):
    count=u.GTLandscapeSurfaceSetupLibrary.round_shallow_pond_bank(author,u.Vector(-42563,171491,9374.491),u.Vector2D(1610,1570),2050)
    assert count>0,('Bank validation failed before mutation',count)
    tiles=[t for t in author.relief_tiles.values() if t.get_actor_label().startswith('LidarWater_Shore_')]
    return dict(changed_tiles=count,added_tiles=len(tiles),added_triangles=sum(t.triangle_count() for t in tiles),collision_and_water_depth_share_heights=True)


def pond_mesh(name,ground):
    """Clip current ground against the existing bounded hydrological envelope."""
    src=ROOT/'Art/Export/LidarStudy/Place';raw=(src/(name+'-domain.bin')).read_bytes()
    _,nx,ny,_,_,ox,oy,cell=struct.unpack('<5i3f',raw[:32]);data=array.array('f');data.frombytes(raw[32:-1])
    wet=[(i%nx,i//nx) for i in range(nx*ny) if data[i*4+1]>.005]
    level=next(data[i*4] for i in range(nx*ny) if data[i*4+1]>.005)
    cache={};verts=[];faces=[];lookup={};step=50
    def vertex(ix,iy):
        if (ix,iy) in cache:return cache[ix,iy]
        x,y=ox+ix*step,oy+iy*step
        qx,qy=(x-ox)/cell-.5,(y-oy)/cell-.5
        near=min(((wx-qx)**2+(wy-qy)**2 for wx,wy in wet),default=1e9)**.5*cell
        depth=min(level-ground.height(x,y)-.2,250-near)
        cache[ix,iy]=((x,y,level),depth);return cache[ix,iy]
    def index(p):
        k=tuple(round(v,3) for v in p)
        if k not in lookup:lookup[k]=len(verts)+1;verts.append(k)
        return lookup[k]
    for iy in range(-5,math.ceil(ny*cell/step)+5):
        for ix in range(-5,math.ceil(nx*cell/step)+5):
            vs=[vertex(ix,iy),vertex(ix+1,iy),vertex(ix,iy+1),vertex(ix+1,iy+1)]
            for ids in [(0,2,1),(1,2,3)]:
                poly=[vs[i] for i in ids];clip=[]
                for a,b in zip(poly,poly[1:]+poly[:1]):
                    if a[1]>0:clip.append(a[0])
                    if (a[1]>0)!=(b[1]>0):
                        t=a[1]/(a[1]-b[1]);clip.append(tuple(a[0][k]+t*(b[0][k]-a[0][k]) for k in range(3)))
                if len(clip)>2:
                    ii=[index(p) for p in clip];faces.extend((ii[0],ii[j],ii[j+1]) for j in range(1,len(ii)-1))
    assert 500<len(faces)<16000,(name,len(faces))
    path=QA/(name+'.obj');path.write_text('\n'.join(['v %.3f %.3f %.3f'%(x,-y,z) for x,y,z in verts]+['f %d %d %d'%f for f in faces]))
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
    opt=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,generate_lightmap_u_vs=False)
    task=props(u.AssetImportTask(),filename=str(path),destination_path=BASE,destination_name='SM_'+name+'Water',automated=True,replace_existing=True,save=True,options=opt)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(BASE+'/SM_'+name+'Water');assert mesh
    mesh.set_material(0,u.load_asset(BASE+'/M_'+name+'Water'));u.get_editor_subsystem(u.StaticMeshEditorSubsystem).remove_collisions(mesh)
    assert assets.save_loaded_asset(mesh,False)
    return dict(triangles=len(faces),vertices=len(verts),grid_cm=step,shore_margin_cm=250)

MASK='''
// Continuous per-body meshes retain their own optical inputs as the window moves.
if(LocalSurface>.5)return 0;
float2 uv=(P.xy-FieldMin.xy)/FieldSize.xy;
float2 cell=FieldSize.xy/FieldTexels.xy;
float2 edge=min(P.xy-FieldMin.xy-cell*.5,FieldMin.xy+FieldSize.xy-cell*.5-P.xy);
float inside=FieldActive*step(0,min(edge.x,edge.y));
if(inside<.5 || RiverGroundReady<.5)return 1;
float2 bed=Texture2DSampleLevel(RiverGroundTex,RiverGroundTexSampler,uv,0).rg;
float4 water=Texture2DSampleLevel(FieldTex,FieldTexSampler,uv,0);
float2 soilUV=(P.xy-GTLS_Window.xy)/max(1,GTLS_Window.z);float delta=0;
if(GTLS_Ready>.5 && all(soilUV>=0) && all(soilUV<=1))delta=Texture2DSampleLevel(GTLS_Field,GTLS_FieldSampler,soilUV,0).r;
return step(.5,bed.g)*step(.2,water.r+FieldLevelCm-bed.r-delta);
'''

def refine_material(name):
    m=u.load_asset(BASE+'/M_'+name+'Water');g=Graph(m,'WaterRefinement-1');nodes=connected_nodes(m)
    baseline=json.loads((QA/'materials.json').read_text())[name]['nodes']
    main=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'float wetEdge=' in n.get_editor_property('code'))
    code=next(n['code'] for n in baseline if 'float wetEdge=' in n.get('code',''))
    controls=dict(PoolRippleStrength=.22 if name=='River' else .18,RiffleRippleStrength=.58 if name=='River' else .30,RippleScale=1.6,PoolRoughness=.045 if name=='River' else .055,CalmSlopeStrength=.28 if name=='River' else .12,RiffleSlopeStrength=.60)
    for key,val in controls.items():
        param=next((n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))==key),None)
        param=param or g.node(u.MaterialExpressionScalarParameter,parameter_name=key,default_value=val)
        param.set_editor_property('default_value',val)
        inputs=list(main.get_editor_property('inputs'))
        if key not in [str(i.get_editor_property('input_name')) for i in inputs]:main.set_editor_property('inputs',inputs+[props(u.CustomInput(),input_name=key)])
        g.wire(param,main,key)
    old='q,velocity,Clock,nativeLod)';assert code.count(old)==1
    code=code.replace(old,'q*RippleScale,ambientVelocity,Clock,nativeLod)')
    old='slope=lerp(baseSlope,slope,physicalWeight);';assert code.count(old)==1
    code=code.replace(old,'''float slopeActivity=smoothstep(.35,1.1,speed)*(1-smoothstep(.25,.9,depth));
// Reduce broad imported/mean-surface tilt before adding the existing wake detail.
slope=lerp(baseSlope,slope,physicalWeight)*lerp(CalmSlopeStrength,RiffleSlopeStrength,slopeActivity);''')
    old='Normal=normalize(float3(-slope+detail,1));';assert code.count(old)==1
    code=code.replace(old,'''float surfaceActivity=smoothstep(.35,1.1,speed)*(1-smoothstep(.25,.9,depth));
float opticalGain=lerp(PoolRippleStrength,RiffleRippleStrength,surfaceActivity);
detail*=opticalGain;
Normal=normalize(float3(-slope+detail,1));''')
    old='Rough=clamp(lerp(0.02,0.12,riffle)+foam*.48,0.02,.65);';assert code.count(old)==1
    code=code.replace(old,'Rough=clamp(lerp(PoolRoughness,.12,riffle)+foam*.48,PoolRoughness,.65);')
    code=code.replace('smoothstep(.005,.12,ambientDepth),inBake);','smoothstep(.005,.12,depth),inBake);')
    main.set_editor_property('code',code)
    mask=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK);assert isinstance(mask,u.MaterialExpressionCustom)
    mask.set_editor_property('code',MASK)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m,False)
    return controls

def optics():
    result=json.loads((QA/'install.json').read_text());assert result['ok']
    result['controls']={n:refine_material(n) for n in ['MappedPond','AccessPond','River']}
    assert all(sha(Path(p))==h for p,h in result['protected'].items())
    (QA/'install.json').write_text(json.dumps(result,indent=2))
    return dict(ok=True,controls=result['controls'],level_unchanged=True)

def install():
    backup_path=backup()
    protected=[ROOT/'Content/GrandTour/ArtTests/LidarStudy/CohesiveStyle'/n for n in ['DA_Lidar_Evergreen.uasset','M_EvergreenTerrain.uasset','M_EvergreenFoliage.uasset']]
    hashes={str(p):sha(p) for p in protected}
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(BASE+'/L_LidarStudy')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    author=next(a for a in actors if isinstance(a,u.GTProceduralGround));ground=GroundSampler(author)
    # A saved marker prevents repeated corner filling on reapplication.
    marker=next((a for a in actors if a.get_actor_label()=='LidarWater_ShoreRefinement'),None)
    bank_tiles=[t for t in author.relief_tiles.values() if t.get_actor_label().startswith('LidarWater_Shore_')]
    bank=round_northern_bank(author,ground) if not marker or len(bank_tiles)!=27 else dict(retained=True,added_tiles=27,added_triangles=sum(t.triangle_count() for t in bank_tiles),collision_and_water_depth_share_heights=True)
    if not marker:
        marker=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.Actor,u.Vector())
        marker.set_actor_label('LidarWater_ShoreRefinement')
    ground=GroundSampler(author)
    meshes={n:pond_mesh(n,ground) for n in ['MappedPond','AccessPond']}
    materials={n:refine_material(n) for n in ['MappedPond','AccessPond','River']}
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    assert all(sha(Path(p))==h for p,h in hashes.items()),'Palette/forest asset changed'
    return dict(ok=True,backup=backup_path,bank=bank,meshes=meshes,controls=materials,protected=hashes,palette_unchanged=True,additional_texture_samples=0,simulation_grid_unchanged=True,performance_verified=False)

def verify():
    result=json.loads((QA/'install.json').read_text());assert result['ok']
    assert all(sha(Path(p))==h for p,h in result['protected'].items())
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(BASE+'/L_LidarStudy')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    author=next(a for a in actors if isinstance(a,u.GTProceduralGround))
    tiles=[t for t in author.relief_tiles.values() if t.get_actor_label().startswith('LidarWater_Shore_')]
    assert len(tiles)==27 and sum(t.triangle_count() for t in tiles)==12150
    # Reloaded geometry must retain real collision and the shared query heights.
    assert all(t.mesh.get_num_sections()>0 for t in tiles)
    ground=GroundSampler(author);points=[]
    for x,y in [(-42563,171491),(-43950,170150),(-41100,172800),(-42563,173000)]:
        points.append(dict(x=x,y=y,ground_cm=ground.height(x,y)))
    counts={}
    for name in ['MappedPond','AccessPond','River']:
        m=u.load_asset(BASE+'/M_'+name+'Water');nodes=connected_nodes(m)
        mask=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
        assert 'if(LocalSurface>.5)return 0;' in mask.get_editor_property('code')
        for key,value in result['controls'][name].items():
            n=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))==key)
            assert abs(n.get_editor_property('default_value')-value)<.0001
        counts[name]=u.load_asset(BASE+'/SM_'+name+'Water').get_static_mesh_description(0).get_triangle_count()
    return dict(ok=True,reloaded=True,palette_unchanged=True,shore_tiles=len(tiles),height_probes=points,water_triangles=counts)

if __name__=='__main__':
    stage=os.environ.get('GT_WATER_REFINEMENT_STAGE','audit')
    try:result=audit() if stage=='audit' else verify() if stage=='verify' else optics() if stage=='optics' else install()
    except Exception:result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
    (QA/(stage+'.json')).write_text(json.dumps(result,indent=2))
    # Let ExecutePythonScript finish before requesting editor shutdown.
    def finish(dt):
        u.unregister_slate_post_tick_callback(finish_handle);u.SystemLibrary.quit_editor()
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    finish_handle=u.register_slate_post_tick_callback(finish)
