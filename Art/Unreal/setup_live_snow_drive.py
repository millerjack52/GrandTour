"""Living mud LM3a + LM3b (docs/LIVING_MUD_PLAN.md LM3a, LM3b, docs/LIVE_SNOW_DRIVE.md): the snow test strip, L_SnowDrive.

140 m along +X: the firm road (the Dirt row) 0-30 m, a Snow section 30-110 m with a drift at 70-80 m, the road again to
140 m. The car starts at 5 m. The drift is a depth curve on the one Snow section (FGTRouteSection::SnowDrifts: 60 cm from
70 to 80 m, blending from the profile's 35 cm over 2 m beyond each end), so the snow is one patch with one taper and no
seam between two patches. The strip has its own landscape material, a copy of M_GT_Landscape whose Snow row is flat white
(albedo 0.85, roughness 0.7: M_GT_Snow's fresh snow). The snow materials come from live_snow_style.py (M_GT_Snow and
M_GT_Clod_Snow). Clear weather; the check sets it.
LM3b: the landscape takes M_GT_Snow's fresh-snow response (live_snow_style.APRON_HLSL: the same noise, shade tint and glint,
the same numbers) at the patch box's border, fading to its own over a 3 m apron outside it and wherever its Snow layer
lies, through three wrapper nodes on its Base Color, Normal and Roughness (as setup_live_mud_drive.py's clay apron).
"""
import unreal as u,json,sys,traceback,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LiveSnowDrive';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from live_snow_style import apply_snow,stats,APRON_HLSL,FRESH_SCALARS,FRESH_VECTORS,APRON_DETAIL,detail_node
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
DEST='/Game/GrandTour/ArtTests/LiveSnowDrive';LEVEL=DEST+'/L_SnowDrive';LANDSCAPE=DEST+'/M_SnowLandscape';report={'ok':False}
SNOW_ROW_ALBEDO=.85;SNOW_ROW_ROUGH=.7
SNOW_START_M,SNOW_END_M=30.,110.;DRIFT=(70.,80.,60.,2.)
# LM3b: the snow patch's box as LM3a's check measured it (x 23.8-116.3 m, y -6.2..6.3 m: 740 x 100 cells of 12.5 cm); the
# check compares it with the patch's own and reports a mismatch. The apron fades over APRON_CM outside it.
APRON_MIN=(2380.,-620.);APRON_MAX=(11630.,630.);APRON_CM=300.
def setprops(obj,**values):
    for key,value in values.items():obj.set_editor_property(key,value)
    return obj
def spawn(cls,label,pos,rot=None):
    a=act.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label(label);return a
def snow_row(landscape):
    # The Snow layer's constant in the colour and roughness layer blends (nothing is wired to the Snow pins).
    done=[]
    for e in mel.get_material_expressions(landscape):
        if not isinstance(e,u.MaterialExpressionLandscapeLayerBlend):continue
        desc=str(e.get_editor_property('desc'))
        if desc not in ('Landscape:colour','Landscape:roughness'):continue
        value=SNOW_ROW_ALBEDO if desc=='Landscape:colour' else SNOW_ROW_ROUGH
        layers=list(e.get_editor_property('layers'))
        for entry in layers:
            if str(entry.get_editor_property('layer_name'))=='Snow':
                entry.set_editor_property('const_layer_input',u.Vector(value,value,value));done.append(desc)
        e.set_editor_property('layers',layers)
    assert sorted(done)==['Landscape:colour','Landscape:roughness'],done
    return done
def snow_apron(landscape):
    # One node computes the fresh-snow response and the apron's blend; three wrappers lerp the landscape's own Base Color,
    # Normal and Roughness toward it. Found by desc on a rerun, so nothing nests and their Old pins keep the originals.
    exprs=list(mel.get_material_expressions(landscape))
    def find(desc):return next((e for e in exprs if isinstance(e,u.MaterialExpressionCustom) and str(e.get_editor_property('desc'))==desc),None)
    node=find('SnowApron')
    if node is None:
        node=mel.create_material_expression(landscape,u.MaterialExpressionCustom,-900,2600);exprs.append(node)
        setprops(node,desc='SnowApron',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    names=['WorldPos','VertexNormal','CamVec','SunDir','SnowLayer','ApronMin','ApronMax','ApronCm']+list(FRESH_SCALARS)+list(FRESH_VECTORS)+(['SnowDetail'] if APRON_DETAIL else [])
    slots=[]
    for name in names:
        slot=u.CustomInput();slot.set_editor_property('input_name',name);slots.append(slot)
    node.set_editor_property('inputs',slots)
    outs=[]
    for name,kind in [('SnowN',u.CustomMaterialOutputType.CMOT_FLOAT3),('SnowRough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Blend',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        o=u.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',kind);outs.append(o)
    node.set_editor_property('additional_outputs',outs)
    node.set_editor_property('code',APRON_HLSL)
    ys=[2600]
    def place():
        ys[0]+=100;return ys[0]
    def param(cls,name,value):
        e=next((x for x in exprs if isinstance(x,cls) and str(x.get_editor_property('parameter_name'))==name),None)
        if e is None:e=mel.create_material_expression(landscape,cls,-1300,place());exprs.append(e)
        e.set_editor_property('parameter_name',name)
        e.set_editor_property('default_value',u.LinearColor(value[0],value[1],value[2],1.0) if cls is u.MaterialExpressionVectorParameter else value)
        assert mel.connect_material_expressions(e,'',node,name),name
    for name,value in FRESH_SCALARS.items():param(u.MaterialExpressionScalarParameter,name,value)
    for name,value in FRESH_VECTORS.items():param(u.MaterialExpressionVectorParameter,name,value)
    param(u.MaterialExpressionVectorParameter,'ApronMin',(APRON_MIN[0],APRON_MIN[1],0.))
    param(u.MaterialExpressionVectorParameter,'ApronMax',(APRON_MAX[0],APRON_MAX[1],0.))
    param(u.MaterialExpressionScalarParameter,'ApronCm',APRON_CM)
    if APRON_DETAIL:
        # LM4b: the snow-clump detail map, M_GT_Snow's fresh-snow crumbs (the shared wrap sampler: no landscape sampler slot).
        assert mel.connect_material_expressions(detail_node(landscape,exprs,-1300,place()),'',node,'SnowDetail'),'SnowDetail'
    def single(cls,label,**props):
        e=next((x for x in exprs if isinstance(x,cls) and str(x.get_editor_property('desc'))==label),None)
        if e is None:
            e=mel.create_material_expression(landscape,cls,-1300,place());exprs.append(e);e.set_editor_property('desc',label)
        for k,v in props.items():e.set_editor_property(k,v)
        return e
    assert mel.connect_material_expressions(single(u.MaterialExpressionWorldPosition,'SnowApron:wpos'),'',node,'WorldPos')
    assert mel.connect_material_expressions(single(u.MaterialExpressionVertexNormalWS,'SnowApron:vnormal'),'',node,'VertexNormal')
    assert mel.connect_material_expressions(single(u.MaterialExpressionCameraVectorWS,'SnowApron:camvec'),'',node,'CamVec')
    assert mel.connect_material_expressions(single(u.MaterialExpressionSkyAtmosphereLightDirection,'SnowApron:sun',light_index=0),'',node,'SunDir')
    assert mel.connect_material_expressions(single(u.MaterialExpressionLandscapeLayerSample,'SnowApron:snowlayer',parameter_name='Snow',preview_weight=0.0),'',node,'SnowLayer')
    wrapped=[]
    for label,prop,code,kind,out in [
        ('SnowApronColor',u.MaterialProperty.MP_BASE_COLOR,'return lerp(Old,Snow,Blend);',u.CustomMaterialOutputType.CMOT_FLOAT3,''),
        ('SnowApronNormal',u.MaterialProperty.MP_NORMAL,'return normalize(lerp(Old,Snow,Blend));',u.CustomMaterialOutputType.CMOT_FLOAT3,'SnowN'),
        ('SnowApronRoughness',u.MaterialProperty.MP_ROUGHNESS,'return lerp(Old,Snow,Blend);',u.CustomMaterialOutputType.CMOT_FLOAT1,'SnowRough')]:
        wrap=find(label)
        if wrap is None:
            old=mel.get_material_property_input_node(landscape,prop);old_out=mel.get_material_property_input_node_output_name(landscape,prop)
            assert old is not None,'nothing on '+str(prop)
            wrap=mel.create_material_expression(landscape,u.MaterialExpressionCustom,-200,place());exprs.append(wrap)
            setprops(wrap,desc=label,code=code,output_type=kind)
            slots=[]
            for name in ['Old','Snow','Blend']:
                slot=u.CustomInput();slot.set_editor_property('input_name',name);slots.append(slot)
            wrap.set_editor_property('inputs',slots);assert mel.connect_material_expressions(old,str(old_out),wrap,'Old'),label
            wrapped.append(dict(wrapper=label,old=old.get_name(),old_output=str(old_out)))
        else:wrapped.append(dict(wrapper=label,kept=True))
        assert mel.connect_material_expressions(node,out,wrap,'Snow'),label
        assert mel.connect_material_expressions(node,'Blend',wrap,'Blend'),label
        assert mel.connect_material_property(wrap,'',prop),label
    return dict(box_min=APRON_MIN,box_max=APRON_MAX,apron_cm=APRON_CM,snow_layer='Snow',wrappers=wrapped)
try:
    report['materials']=apply_snow()
    # The setup wrapper reads the log for shader errors after this line only (the edits above compile half-wired graphs).
    u.log('LM3B_SNOW_MATERIALS_BUILT')
    if eal.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
    else:assert les.new_level(LEVEL)
    for a in act.get_all_level_actors():
        if not isinstance(a,(u.WorldSettings,u.Brush)):act.destroy_actor(a)
    spec=u.GTTerrainSpec()
    setprops(spec,components_per_side=3,subsections_per_component=1,quads_per_subsection=63,quad_size_cm=100.,origin_x_cm=-2000.,origin_y_cm=-9400.,base_amplitude_m=1.2,base_wavelength_m=90.,octaves=2,slope_m_per_km=0.,road_half_width_m=3.,shoulder_m=8.,route_m=[u.Vector2D(0,0),u.Vector2D(140,0)],alt_routes=[],planes=[],stations=[],features=[])
    drift=setprops(u.GTSnowDrift(),start_m=DRIFT[0],end_m=DRIFT[1],depth_cm=DRIFT[2],ramp_m=DRIFT[3])
    snow=setprops(u.GTRouteSection(),start_m=SNOW_START_M,end_m=SNOW_END_M,kind=u.GTRouteSectionKind.SNOW,snow_drifts=[drift])
    spec.sections=[snow]
    spec.spans=[setprops(u.GTSurfaceSpan(),start_m=0.,end_m=140.,layer=1)]
    profile=spec.snow_profile
    report['snow_profile']=dict(medium=str(profile.medium),snow_depth_cm=profile.snow_depth_cm,snow_edge_cm=profile.snow_edge_cm,max_sinkage_m=profile.max_sinkage_m,sinkage_rate=profile.sinkage_rate,ridge_return=profile.ridge_return,snow_plough=profile.snow_plough,plough_return=profile.plough_return,refill_cm_per_min=profile.refill_cm_per_min,snow_width_scale=spec.snow_width_scale)
    spec_asset=eal.load_asset(DEST+'/DA_SnowDrive') or assets.create_asset('DA_SnowDrive',DEST,u.GTTerrainSpecAsset,u.DataAssetFactory())
    setprops(spec_asset,display_name='Road - deep snow - drift',spec=spec);eal.save_loaded_asset(spec_asset)
    # Its own landscape material: M_GT_Landscape with the Snow row flat white (M_GT_Snow's fresh values), no OW grass.
    landscape=eal.load_asset(LANDSCAPE)
    if landscape is None:landscape=eal.duplicate_asset('/Game/GrandTour/Materials/M_GT_Landscape',LANDSCAPE)
    for e in list(mel.get_material_expressions(landscape)):
        if isinstance(e,u.MaterialExpressionLandscapeGrassOutput):mel.delete_material_expression(landscape,e)
    report['snow_row']=snow_row(landscape)
    report['apron']=snow_apron(landscape)
    errors=mel.recompile_material(landscape);assert not errors,str(errors);eal.save_loaded_asset(landscape)
    u.log('LM3B_SNOW_LANDSCAPE_BUILT')
    builder=spawn(u.GTTerrainBuilder,'TerrainBuilder',(0,-2500,500));builder.spec_asset=spec_asset;builder.landscape_material_path=LANDSCAPE;assert builder.rebuild_landscape(),builder.last_message
    for dressing in act.get_all_level_actors():
        if isinstance(dressing,u.GTTerrainDressing):
            for component in dressing.get_components_by_class(u.InstancedStaticMeshComponent):
                if component.get_name()=='Foliage':component.clear_instances()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    def height(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x*100,y*100)
    spawn(u.PlayerStart,'PlayerStart',(500,0,height(5,0)+150))
    sun=spawn(u.DirectionalLight,'Sun',(0,0,1000));sky=spawn(u.SkyLight,'SkyLight',(0,0,1000));sky.light_component.set_editor_property('real_time_capture',True)
    spawn(u.SkyAtmosphere,'SkyAtmosphere',(0,0,0));spawn(u.ExponentialHeightFog,'HeightFog',(0,0,0))
    from tussock_style_lighting import configure
    report['lighting']=configure(world)
    # Winch posts beside the drift's approach and exit, outside the snow patch's box (half width 4.2 m + 2 m).
    for x in [62,92]:
        a=spawn(u.GTWinchAnchor,'WinchPost_'+str(x),(x*100,800,height(x,8.)));a.get_anchor().set_editor_property('strength_n',200000.)
    overview=spawn(u.CameraActor,'Live_Overview',(5000,1600,900),u.Rotator(pitch=-18,yaw=-25));overview.camera_component.set_field_of_view(65)
    world.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    assert les.save_current_level()
    # LM3b: representative shader instruction counts of the snow and the clay patch materials (a synchronous compile).
    try:report['material_stats']=[stats('/Game/GrandTour/Materials/M_GT_Snow'),stats('/Game/GrandTour/Materials/M_GT_Mud'),stats('/Game/GrandTour/Materials/M_GT_Clod_Snow')]
    except Exception:report['material_stats_error']=traceback.format_exc()
    # LM3c item 5: what Substrate compiled each to (its material type and lighting tile, closures, BSDF feature bits, the
    # blendable GBuffer's legacy pass-through), for the diagnosis of the snow material's deferred lighting cost.
    try:
        lib=getattr(u,'GTSubstrateInfoLibrary',None)
        report['substrate_info']=[lib.get_substrate_material_info(eal.load_asset(path)) if lib else 'GTSubstrateInfoLibrary missing' for path in
            ['/Game/GrandTour/Materials/M_GT_Snow','/Game/GrandTour/Materials/M_GT_Mud','/Game/GrandTour/Materials/M_GT_Clod_Snow','/Game/GrandTour/Materials/M_GT_Clod']]
    except Exception:report['substrate_info_error']=traceback.format_exc()
    report.update(ok=True,level=LEVEL,route_m=140,road_m=[[0,SNOW_START_M],[SNOW_END_M,140]],snow_m=[SNOW_START_M,SNOW_END_M],drift=dict(start_m=DRIFT[0],end_m=DRIFT[1],depth_cm=DRIFT[2],ramp_m=DRIFT[3],how='FGTRouteSection::SnowDrifts on the one Snow section (a depth curve)'),start_m=5,landscape_material=LANDSCAPE,snow_row=dict(albedo=SNOW_ROW_ALBEDO,rough=SNOW_ROW_ROUGH))
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:(OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
