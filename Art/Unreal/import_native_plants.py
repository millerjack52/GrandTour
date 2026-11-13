"""NP3 (docs/NATIVE_PLANT_KIT_PLAN.md) + S1 (docs/SOUTHLAND_ASSET_PLAN.md): import the native plant kit to /Game/GrandTour/Environment/NativePlants/v01:
the 20-mesh bush and open sets plus the 15-mesh Southland bush-floor and river set (manifest set 'floor') and, from S2b, the 15-mesh verge set
(manifest set 'verge': gorse, broom, rush, thistle, verge tussock, radiata young/mature, macrocarpa, twig/root/leaf litter) and, from
LP4 (docs/LIDAR_PLACE_PLAN.md), the 11-mesh Southland farm hardware set (manifest set 'farm': fence module, strainer, gate, cattle stop, culvert, trough,
power pole, sign post, give way, letterbox, hay bale; slot Bark on M_NZ_Bark, collision use-simple through the manifest hulls) and, from
GP1 (docs/LIDAR_PLACE_PLAN.md), the 5-mesh grass clump set (manifest set 'grass': PastureClump S/M/L, RankClump A/B; slot Foliage on M_NZ_Foliage, TWO LODs with
screen sizes [1, .25], no hulls and no collision, Nanite off; the vertex alpha is a wind weight and is read back where the editor exposes it) and, from
GP4a (docs/LIDAR_PLACE_PLAN.md), the 3-mesh grass patch set (manifest set 'patch': GrassPatch_A/B/C; slot Foliage on M_NZ_Foliage, THREE LODs with screen sizes [1, .35, .12],
no hulls and no collision, Nanite off; the same wind-weight vertex alpha readback).
Re-runs skip a mesh that already exists with its LOD count (three, two for grass) and the manifest's hull count (reported with skipped=true); GT_NP_REIMPORT=all|bush|open|floor|verge|farm|grass|patch
(comma list, Art/native_plants.ps1 -Reimport) forces a set to import again.

Shrub-library pattern: legacy FBX import, three authored LODs (set_lods then import_lod), screen sizes per family (NP4b: trees .22/.08, crown ferns .18/.065, the rest .12/.04),
Nanite off, dimensions asserted within 2.5 cm. Trees keep their UCX convex hulls (one per UCX, count asserted against
the manifest); meshes without hulls lose all collision. Slots from the manifest: Bark (M_NZ_Bark) and Foliage
(M_NZ_Foliage, dense_tussock_material). Does not load or modify a map. Run through Art/native_plants.ps1 -Mode Import.
"""
import unreal as u, json, traceback, sys, os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/NativePlants/v01'
DEST='/Game/GrandTour/Environment/NativePlants/v01'
ORDER=['Beech_Mature','Beech_Pole','Beech_Edge','DeadSpar','CrownFern_A','CrownFern_B','CrownFern_C','TreeFern_A','TreeFern_B','TreeFern_Young',
       'Harakeke_A','Harakeke_B','Coprosma_A','Coprosma_B','Matagouri_A','Matagouri_B','TiKouka_A','TiKouka_B','Kanuka_A','Kanuka_B']
# NP4b screen sizes: the bush trees keep [1, .22, .08]; the crown ferns (placed 100k times) keep [1, .18, .065]; every other mesh
# (tree ferns, flax, coprosma, matagouri, cabbage tree, kanuka) is [1, .12, .04] so a 5 m plant at 40 m stays on LOD1 instead of the LOD2 cap.
TREES=('Beech_','DeadSpar'); CROWN=('CrownFern_',)
# S1: the floor and river set (kiokio, logs, stump, hummocks, cobbles, bar, driftwood, log jam, boulders) is [1, .18, .065] like the crown ferns.
FLOOR=['Kiokio_A','Kiokio_B','Log_A','Log_B','Stump_A','MossHummock_A','MossHummock_B','Cobble_Cluster_S','Cobble_Cluster_M','Cobble_Cluster_L','CobbleBar',
       'Driftwood_A','LogJam','Boulder_A','Boulder_B']
# S2b: the verge set (shrubs, litter, tussock) is [1, .18, .065] like the floor set; its three trees keep the kit's small-tree rule [1, .12, .04].
VERGE=['Gorse_A','Gorse_B','Broom_A','Rush_A','Rush_B','Thistle_A','VergeTussock_A','VergeTussock_B','Radiata_Young','Radiata_Mature','Macrocarpa',
       'TwigLitter_A','TwigLitter_B','RootTangle_A','LeafLitter_A']
VERGE_TREES=('Radiata_Young','Radiata_Mature','Macrocarpa'); VERGE_HULLS={'Radiata_Young':1,'Radiata_Mature':2,'Macrocarpa':2}
# LP4 / S2a: the farm hardware set, [1, .18, .065] like the floor and verge sets; hull counts as the S2a brief (the rest are one hull each).
FARM=['Fence_4m','Strainer','Gate_3m6','CattleStop','Culvert','Trough','PowerPole','SignPost','GiveWay','Letterbox','HayBale']
FARM_HULLS={'Fence_4m':1,'Strainer':2,'Gate_3m6':3,'CattleStop':3,'Culvert':1,'Trough':1,'PowerPole':1,'SignPost':1,'GiveWay':1,'Letterbox':1,'HayBale':1}
# GP1: the grass clumps (placed by the thousand): two authored LODs, screen sizes [1, .25], no hulls.
GRASS=['PastureClump_S','PastureClump_M','PastureClump_L','RankClump_A','RankClump_B']
# GP4a: the grass patches (placed ten thousand at a time): three authored LODs, screen sizes [1, .35, .12], no hulls.
PATCH=['GrassPatch_A','GrassPatch_B','GrassPatch_C']
def screens_for(short):
    if short in GRASS:return [1.,.25]
    if short in PATCH:return [1.,.35,.12]
    if short in VERGE_TREES:return [1.,.12,.04]
    return [1.,.22,.08] if short.startswith(TREES) else [1.,.18,.065] if short.startswith(CROWN) or short in FLOOR or short in VERGE or short in FARM else [1.,.12,.04]
def set_of(short):return 'floor' if short in FLOOR else 'verge' if short in VERGE else 'farm' if short in FARM else 'grass' if short in GRASS else 'patch' if short in PATCH else 'bush' if short in ORDER[:10] else 'open'
def lods_for(short):return len(screens_for(short))
REIMPORT=set(x for x in os.environ.get('GT_NP_REIMPORT','').lower().replace(' ','').split(',') if x)
eal=u.EditorAssetLibrary; mel=u.MaterialEditingLibrary; assets=u.AssetToolsHelpers.get_asset_tools()
report={'ok':False,'destination':DEST,'meshes':[],'failed':[]}
TINT_LOG={}   # LP3c readback of what add_tint wired, per material
UNITS={'variant':'shrub'}   # 'shrub' = the shrub importer's defaults; 'convert' = setup_benmore_scenery's convert_scene/convert_scene_unit

def material(name):
    path=DEST+'/'+name
    return eal.load_asset(path) if eal.does_asset_exist(path) else assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())

def add_tint(m,properties):
    """LP3c: a VectorParameter 'Tint' (default 1,1,1,1) multiplies the vertex colour that feeds each listed material property, so a material
    instance can darken or recolour the whole kit under one map's light. The default leaves every existing look unchanged.
    Works on whatever node feeds each property (asserted to be a vertex colour), not on a count of nodes in the graph."""
    sources=[]
    for prop in properties:
        src=mel.get_material_property_input_node(m,prop); assert src and isinstance(src,u.MaterialExpressionVertexColor),(m.get_name(),prop,'is not fed by a vertex colour',src)
        sources.append((prop,src,mel.get_material_property_input_node_output_name(m,prop)))
    tint=mel.create_material_expression(m,u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name','Tint'); tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
    for prop,src,out in sources:
        mul=mel.create_material_expression(m,u.MaterialExpressionMultiply)
        assert mel.connect_material_expressions(src,out,mul,'A'),(m.get_name(),prop,'tint A')
        assert mel.connect_material_expressions(tint,'',mul,'B'),(m.get_name(),prop,'tint B')
        assert mel.connect_material_property(mul,'',prop),(m.get_name(),prop)
    TINT_LOG[m.get_name()]=dict(expressions=sorted(e.get_class().get_name() for e in mel.get_material_expressions(m)),sources=[(str(prop),src.get_class().get_name(),out) for prop,src,out in sources])
    assert not mel.recompile_material(m),(m.get_name(),'recompile'); eal.save_loaded_asset(m)

def bark_material():
    m=material('M_NZ_Bark')
    mel.delete_all_material_expressions(m)
    m.set_editor_property('two_sided',False)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for usage in [u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,u.MaterialUsage.MATUSAGE_NANITE]:
        mel.set_base_material_usage(m,usage,True)
    vc=mel.create_material_expression(m,u.MaterialExpressionVertexColor)
    assert mel.connect_material_property(vc,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.9),(u.MaterialProperty.MP_SPECULAR,.1)]:
        c=mel.create_material_expression(m,u.MaterialExpressionConstant); c.set_editor_property('r',value)
        assert mel.connect_material_property(c,'',prop)
    mel.recompile_material(m); eal.save_loaded_asset(m)
    add_tint(m,[u.MaterialProperty.MP_BASE_COLOR])
    return m

def import_base(row,variant):
    name=row['asset']
    task=u.AssetImportTask(); task.filename=str(OUT/(row['name']+'.fbx')); task.destination_path=DEST; task.destination_name=name
    task.automated=True; task.replace_existing=True; task.save=True
    opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False; opt.import_materials=False; opt.import_textures=False; opt.import_animations=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data
    d.combine_meshes=True; d.auto_generate_collision=False; d.one_convex_hull_per_ucx=True
    d.generate_lightmap_u_vs=False; d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    if variant=='convert':d.convert_scene=True; d.convert_scene_unit=True
    task.options=opt; assets.import_asset_tasks([task])
    mesh=eal.load_asset(DEST+'/'+name); assert mesh,('Import failed',name)
    return mesh

def dims(mesh):
    size=mesh.get_bounds().box_extent*2
    return [size.x/100,size.y/100,size.z/100]

def slot_index(mesh,name):
    for i,s in enumerate(mesh.get_editor_property('static_materials')):
        if str(s.get_editor_property('material_slot_name')).lower()==name.lower():return i
    for i,s in enumerate(mesh.get_editor_property('static_materials')):
        if name.lower() in str(s.get_editor_property('material_slot_name')).lower():return i
    return None

def convex_count(mesh):
    return len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems'))

def existing(row,sm):
    """The row of an asset that is already imported with three LODs, the manifest's hull count and the manifest's size; None when it needs importing."""
    name=row['asset']; short=name.replace('SM_NZ_',''); path=DEST+'/'+name
    if 'all' in REIMPORT or set_of(short) in REIMPORT or not eal.does_asset_exist(path):return None
    mesh=eal.load_asset(path)
    nl=lods_for(short)
    if not mesh or sm.get_lod_count(mesh)!=nl or convex_count(mesh)!=row['hulls']:return None
    actual=dims(mesh)
    if not all(abs(a-b)<.025 for a,b in zip(sorted(actual),sorted(row['size_m']))):return None
    mats=[]
    for i,s in enumerate(mesh.get_editor_property('static_materials')):
        m=s.get_editor_property('material_interface'); mats.append(dict(slot=i,name=str(s.get_editor_property('material_slot_name')),material=m.get_path_name() if m else None))
    tris=[r['triangles'] for r in sorted((r for r in data['models'] if r['asset']==name),key=lambda r:r['lod'])]
    sections=mesh.get_num_sections(0); complexity=None
    if short in FLOOR or short in VERGE or short in FARM or short in GRASS or short in PATCH:complexity=flag_name(mesh.get_editor_property('body_setup'))+(' (hulls %d)'%row['hulls'] if row['hulls'] else ' (no collision)')
    return dict(ok=True,set=set_of(short),skipped=True,name=short,path=path,lods=nl,manifest_tris=tris,unreal_verts=[sm.get_number_verts(mesh,l) for l in range(nl)],collision=complexity,bounds=bounds_cm(mesh),
                screens=[round(x,4) for x in sm.get_lod_screen_sizes(mesh)],sections=sections,
                lod_section_slots=[[sm.get_lod_material_slot(mesh,l,k) for k in range(mesh.get_num_sections(l))] for l in range(nl)],materials=mats,
                hulls=row['hulls'],manifest_hulls=row['hulls'],size_m=[round(x,4) for x in actual],manifest_size_m=row['size_m'],
                notes=['already imported with %d LODs, the manifest hull count and size; not re-imported'%nl])

def bounds_cm(mesh):
    b=mesh.get_bounds();return dict(origin=[round(b.origin.x,2),round(b.origin.y,2),round(b.origin.z,2)],extent=[round(b.box_extent.x,2),round(b.box_extent.y,2),round(b.box_extent.z,2)])

def flag_name(body_setup):
    return str(body_setup.get_editor_property('collision_trace_flag')).strip('<>').split(':')[0].split('.')[-1]

def alpha_readback(mesh):
    """GP1 best effort: the imported LOD0 vertex colour alpha (wind weight, 0 at the blade base, 1 at the tip) through the mesh description, when the
    editor's Python API exposes it; otherwise records what it could and could not read. Never raises."""
    out={}
    try:
        out['has_vertex_colors']=bool(mesh.get_editor_property('has_vertex_colors'))
    except Exception as e:out['has_vertex_colors']='unavailable: '+str(e)[:80]
    try:
        d=mesh.get_static_mesh_description(0)
        out['description']=type(d).__name__ if d else None
        if d:
            n=d.get_vertex_instance_count(); out['vertex_instances']=n
            al=[]
            for i in range(n):
                vid=u.VertexInstanceID(); vid.set_editor_property('id_value',i); al.append(d.get_vertex_instance_color(vid).a)
            out['alpha_min']=round(min(al),3); out['alpha_max']=round(max(al),3)
    except Exception as e:out['alpha']='not readable through the Python API in this editor (StaticMeshDescription has no vertex-instance colour getter): '+str(e)[:80]
    return out

def one(row,sm,bark,foliage):
    name=row['asset']; short=name.replace('SM_NZ_',''); path=DEST+'/'+name; notes=[]
    mesh=import_base(row,UNITS['variant'])
    actual=dims(mesh); expected=row['size_m']
    ratio=max(actual)/max(expected)
    if not UNITS.get('settled') and (ratio>50 or ratio<.02):
        UNITS['variant']='convert' if UNITS['variant']=='shrub' else 'shrub'
        notes.append('dimensions %.3gx off; reimported with the %s unit flags'%(ratio,UNITS['variant']))
        mesh=import_base(row,UNITS['variant'])
    UNITS['settled']=True
    screens=screens_for(short); nl=len(screens)
    options=u.StaticMeshReductionOptions(); options.auto_compute_lod_screen_size=False; settings=[]
    for screen in screens:
        s=u.StaticMeshReductionSettings(); s.percent_triangles=1.; s.screen_size=screen; settings.append(s)
    options.reduction_settings=settings; assert sm.set_lods(mesh,options)==nl,(name,'set_lods')
    for lod in range(1,nl):
        assert sm.import_lod(mesh,lod,str(OUT/(name+'_LOD'+str(lod)+'.fbx')))==lod,(name,'import_lod',lod)
    assert sm.get_lod_count(mesh)==nl,(name,'lods',sm.get_lod_count(mesh))
    assert sm.set_lod_screen_sizes(mesh,screens),(name,'screens')
    ns=mesh.get_editor_property('nanite_settings'); ns.enabled=False; sm.set_nanite_settings(mesh,ns,True)
    # materials from the manifest's slots
    slots=row['slots']; names=row.get('slot_names') or (['Bark','Foliage'] if slots==2 else ['Foliage'])
    sections=mesh.get_num_sections(0); statics=len(mesh.get_editor_property('static_materials'))
    if slots==2:
        bi=slot_index(mesh,names[0]); fi=slot_index(mesh,names[1])
        if bi is None:bi=sm.get_lod_material_slot(mesh,0,0); notes.append('Bark slot found by section order')
        if short=='DeadSpar' and sections==1:
            mesh.set_material(bi,bark); notes.append('Unreal dropped the empty Foliage section; Bark only (%d static material slots)'%statics)
        else:
            assert sections==2,(name,'sections',sections)
            if fi is None:fi=sm.get_lod_material_slot(mesh,0,1); notes.append('Foliage slot found by section order')
            assert bi!=fi,(name,'slots',bi,fi)
            mesh.set_material(bi,bark); mesh.set_material(fi,foliage)
    else:
        assert sections==1,(name,'sections',sections)
        mesh.set_material(sm.get_lod_material_slot(mesh,0,0),bark if names[0].lower()=='bark' else foliage)
    used={sm.get_lod_material_slot(mesh,0,s) for s in range(sections)}
    lod_sections=[]
    for lod in range(nl):
        slots_used=[sm.get_lod_material_slot(mesh,lod,s) for s in range(mesh.get_num_sections(lod))]
        lod_sections.append(slots_used)
        assert set(slots_used)<=used,(name,'LOD',lod,'uses a material slot LOD0 does not',slots_used,sorted(used))
    # collision
    if row['hulls']>0:
        hulls=convex_count(mesh); assert hulls==row['hulls'],(name,'hulls',hulls,row['hulls'])
    else:
        sm.remove_collisions(mesh); hulls=convex_count(mesh); assert hulls==0,(name,'hulls left',hulls)
    complexity=None
    if short in FLOOR or short in VERGE or short in FARM or short in GRASS or short in PATCH:   # S1/S2b/S2a/GP1/GP4a: collision complexity "use simple" (UCX hulls are the only collision) where hulls exist; with none left it is no collision at all
        bs=mesh.get_editor_property('body_setup'); bs.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        complexity=flag_name(bs)+(' (hulls %d)'%hulls if hulls else ' (no collision)')
    actual=dims(mesh)
    assert all(abs(a-b)<.025 for a,b in zip(sorted(actual),sorted(expected))),(name,'size',actual,expected)
    assert eal.save_loaded_asset(mesh),(name,'save')
    mats=[]
    for i,s in enumerate(mesh.get_editor_property('static_materials')):
        m=s.get_editor_property('material_interface')
        mats.append(dict(slot=i,name=str(s.get_editor_property('material_slot_name')),material=m.get_path_name() if m else None))
    tris=[r['triangles'] for r in sorted((r for r in data['models'] if r['asset']==name),key=lambda r:r['lod'])]
    verts=[sm.get_number_verts(mesh,l) for l in range(sm.get_lod_count(mesh))]
    if short in GRASS or short in PATCH:notes.append('vertex alpha readback: '+json.dumps(alpha_readback(mesh)))
    return dict(ok=True,set=set_of(short),skipped=False,name=short,path=path,lods=sm.get_lod_count(mesh),manifest_tris=tris,unreal_verts=verts,collision=complexity,
                screens=[round(x,4) for x in sm.get_lod_screen_sizes(mesh)],
                sections=sections,lod_section_slots=lod_sections,materials=mats,hulls=hulls,manifest_hulls=row['hulls'],bounds=bounds_cm(mesh),
                size_m=[round(x,4) for x in actual],manifest_size_m=expected,units=UNITS['variant'],notes=notes)

try:
    data=json.loads((OUT/'manifest.json').read_text())
    lod0={r['asset']:r for r in data['models'] if r['lod']==0}
    missing=[n for n in ORDER+FLOOR+VERGE+FARM+GRASS+PATCH if 'SM_NZ_'+n not in lod0]; assert not missing,('Manifest lacks',missing)
    floor_rows=[r['asset'].replace('SM_NZ_','') for r in data['models'] if r['lod']==0 and r.get('set')=='floor']
    assert sorted(floor_rows)==sorted(FLOOR) and len(floor_rows)==15,('Manifest set floor differs from FLOOR',floor_rows)
    verge_rows=[r['asset'].replace('SM_NZ_','') for r in data['models'] if r['lod']==0 and r.get('set')=='verge']
    assert sorted(verge_rows)==sorted(VERGE) and len(verge_rows)==15,('Manifest set verge differs from VERGE',verge_rows)
    for r in data['models']:   # S2b hull counts asserted against the brief: the three trees 1/2/2, every other verge mesh 0
        if r['lod']==0 and r.get('set')=='verge':
            n=r['asset'].replace('SM_NZ_',''); assert r['hulls']==VERGE_HULLS.get(n,0),('Manifest hulls differ from the S2b brief',n,r['hulls'])
    farm_rows=[r['asset'].replace('SM_NZ_','') for r in data['models'] if r['lod']==0 and r.get('set')=='farm']
    assert sorted(farm_rows)==sorted(FARM) and len(farm_rows)==11,('Manifest set farm differs from FARM',farm_rows)
    for r in data['models']:   # S2a hull counts asserted against the brief
        if r['lod']==0 and r.get('set')=='farm':
            n=r['asset'].replace('SM_NZ_',''); assert r['hulls']==FARM_HULLS[n],('Manifest hulls differ from the S2a brief',n,r['hulls'])
    grass_rows=[r['asset'].replace('SM_NZ_','') for r in data['models'] if r['lod']==0 and r.get('set')=='grass']
    assert sorted(grass_rows)==sorted(GRASS) and len(grass_rows)==5,('Manifest set grass differs from GRASS',grass_rows)
    for r in data['models']:   # GP1: two LODs per grass mesh, no hulls
        if r.get('set')=='grass':assert r['lod'] in (0,1) and r['hulls']==0,('Grass manifest row',r['name'],r['lod'],r['hulls'])
    patch_rows=[r['asset'].replace('SM_NZ_','') for r in data['models'] if r['lod']==0 and r.get('set')=='patch']
    assert sorted(patch_rows)==sorted(PATCH) and len(patch_rows)==3,('Manifest set patch differs from PATCH',patch_rows)
    for r in data['models']:   # GP4a: three LODs per patch mesh, no hulls, a declared wind-weight alpha
        if r.get('set')=='patch':assert r['lod'] in (0,1,2) and r['hulls']==0 and r.get('vertex_alpha'),('Patch manifest row',r['name'],r['lod'],r['hulls'])
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    assert sm,'Run through the full editor with -ExecutePythonScript; commandlets do not provide StaticMeshEditorSubsystem.'
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')   # legacy FBX path: UCX hulls and import_lod
    eal.make_directory(DEST)
    foliage=material('M_NZ_Foliage')
    sys.path.insert(0,str(ROOT/'Art/Unreal'))
    from dense_tussock_material import configure
    configure(foliage)
    add_tint(foliage,[u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_SUBSURFACE_COLOR])   # LP3c
    bark=bark_material()
    report['materials']=dict(bark=bark.get_path_name(),foliage=foliage.get_path_name(),
        vector_parameters={n:[str(x) for x in mel.get_vector_parameter_names(mm)] for n,mm in (('M_NZ_Bark',bark),('M_NZ_Foliage',foliage))},tint_wiring=TINT_LOG)
    for short in ORDER+FLOOR+VERGE+FARM+GRASS+PATCH:
        row=lod0['SM_NZ_'+short]
        try:
            kept=existing(row,sm)
            report['meshes'].append(kept or one(row,sm,bark,foliage))
            u.log(('NATIVE_PLANTS_SKIPPED_EXISTING ' if kept else 'NATIVE_PLANTS_IMPORTED ')+short)
        except Exception:
            err=traceback.format_exc(); report['failed'].append(dict(name=short,error=err)); u.log_error(err)
    report['units']=UNITS['variant']
    report['imported']=[m['name'] for m in report['meshes'] if not m['skipped']]; report['skipped']=[m['name'] for m in report['meshes'] if m['skipped']]
    report['floor_ok']=sum(1 for m in report['meshes'] if m['set']=='floor' and m['ok'])
    report['verge_ok']=sum(1 for m in report['meshes'] if m['set']=='verge' and m['ok'])
    report['farm_ok']=sum(1 for m in report['meshes'] if m['set']=='farm' and m['ok'])
    report['grass_ok']=sum(1 for m in report['meshes'] if m['set']=='grass' and m['ok'])
    report['patch_ok']=sum(1 for m in report['meshes'] if m['set']=='patch' and m['ok'])
    report['ok']=len(report['meshes'])==len(ORDER+FLOOR+VERGE+FARM+GRASS+PATCH) and report['floor_ok']==15 and report['verge_ok']==15 and report['farm_ok']==11 and report['grass_ok']==5 and report['patch_ok']==3 and not report['failed']
    if not report['ok'] and 'error' not in report:report['error']='Failed: '+', '.join(f['name'] for f in report['failed'])
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'unreal-import-report.json').write_text(json.dumps(report,indent=2))
    u.log('NATIVE_PLANTS_IMPORT_RESULT ok=%s meshes=%d failed=%d'%(report['ok'],len(report['meshes']),len(report['failed'])))
    u.SystemLibrary.quit_editor()
