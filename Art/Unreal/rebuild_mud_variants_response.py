"""Migrate the driving route to the approved landscape soil response, preserving a package backup."""
import sys,json,time,traceback,shutil,math,struct,zlib
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
BASE='/Game/GrandTour/ArtTests/MudVariants';LEVEL=BASE+'/L_MudVariants'
OUT=ROOT/'Art/Export/MudVariants';OUT.mkdir(parents=True,exist_ok=True)
AUDIT='-GTMudVariantsAudit' in u.SystemLibrary.get_command_line()
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary
report={'ok':False,'level':LEVEL}
from mud_route_profiles import PROFILES,PUDDLES

def props(obj,**kw):
    for k,v in kw.items():obj.set_editor_property(k,v)
    return obj

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)

def setup():
    backup=ROOT/'Saved/MudVariantsResponse'/str(time.time_ns());backup.mkdir(parents=True)
    for rel in ['Content/GrandTour/ArtTests/MudVariants/L_MudVariants.umap','Content/GrandTour/ArtTests/MudVariants/M_ResponseRoute.uasset',
                'Content/GrandTour/ArtTests/MudVariants/T_ResponseRoutePaint.uasset','Content/GrandTour/ArtTests/MudVariants/DA_ResponseRoute.uasset',
                'Content/GrandTour/ArtTests/MudResponse/M_ResponseGround.uasset']:
        p=ROOT/rel
        if p.exists():shutil.copy2(p,backup/p.name)
    report['backup']=str(backup)
    import mud_response_materials
    source=mud_response_materials.ground()
    material=assets.load_asset(BASE+'/M_ResponseRoute') or assets.duplicate_asset(source.get_path_name().split('.')[0],BASE+'/M_ResponseRoute')
    mud_response_materials.improve_rut_water(material)
    land=next(a for a in actors.get_all_level_actors() if isinstance(a,u.LandscapeProxy))
    builder=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTTerrainBuilder))
    original=assets.load_asset(BASE+'/DA_MudVariants');assert original
    original_spec=original.spec
    original_height=lambda x,y:u.GTVehicleSetupLibrary.sample_terrain_height_cm(original_spec,x,y)
    route_spec=assets.load_asset(BASE+'/DA_ResponseRoute') or assets.duplicate_asset(BASE+'/DA_MudVariants',BASE+'/DA_ResponseRoute')
    clean=route_spec.spec;clean.sections=[]
    # The old rigid 12 cm road roughness must not compete with the yielding scan.
    # Level pockets also give the large puddles a common world-space water plane.
    clean.planes=[props(u.GTTerrainPlane(),start_m=u.Vector2D((p['start']-100)/100,0),length_m=(p['end']-p['start']+200)/100,
        half_width_m=6.,base_zm=original_height((p['start']+p['end'])/2,0)/100,grade_percent=0.,cross_slope_degrees=0.,blend_m=6.,roughness_m=.002,layer=1) for p in PROFILES]
    route_spec.set_editor_property('spec',clean)
    route_spec.set_editor_property('display_name','Dry clay / wet mud / deep soft bog / puddled bog')
    builder.spec_asset=route_spec;builder.landscape_material_path=BASE+'/M_ResponseRoute'
    land=builder.rebuild_landscape();assert land,builder.last_message
    spec=route_spec.spec
    height=lambda x,y:u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x,y)
    for a in actors.get_all_level_actors():
        if a.get_actor_label()!='TS_ApprovedTussock':continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            for i in range(c.get_instance_count()):
                tr=c.get_instance_transform(i,True);loc=tr.translation
                if abs(loc.y)>1300:continue
                loc.z=height(loc.x,loc.y);tr.translation=loc;c.update_instance_transform(i,tr,True,True,True)
    pool_levels=[height(x,y)-1.5 for x,y,rx,ry in PUDDLES]
    n=1024;size=25200.;ox=-2000.;oy=-12600.;raw=bytearray()
    for j in range(n):
        raw.append(0);y=oy+(j+.5)*size/n
        for i in range(n):
            x=ox+(i+.5)*size/n;depth=soft=0.;table=50.;gravel=1.
            for p in PROFILES:
                if x<p['start']-180 or x>p['end']+180 or abs(y)>650:continue
                width=430+36*math.sin(x/211)+23*math.sin(x/79)
                edge=smooth(p['start']-150,p['start']+90,x)*(1-smooth(p['end']-90,p['end']+150,x))*(1-smooth(width,width+130,abs(y)))
                variation=.5+.3*math.sin(x/370+y/170)+.2*math.sin(x/137-y/113)
                depth=min(50,p['depth']*(.94+.10*variation))*edge
                soft=min(1,p['soft']*(.94+.08*variation))*edge;table=p['table']
                if p['key']=='PuddledBog':
                    for (cx,cy,rx,ry),level in zip(PUDDLES,pool_levels):
                        q=((x-cx)/rx)**2+((y-cy)/ry)**2
                        if q<1.2:
                            blend=1-smooth(.65,1.2,q)
                            # A common world water level, corrected for the route's gentle grade.
                            pool_table=max(.15,min(50,height(x,y)-level))
                            table=table*(1-blend)+pool_table*blend
                break
            if i in (0,n-1) or j in (0,n-1):depth=soft=gravel=0
            raw.extend((round(depth/50*255),round(table/50*255),round(gravel*255),round(soft*255)))
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    png=OUT/'response-route-paint.png';png.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    task=props(u.AssetImportTask(),filename=str(png),destination_path=BASE,destination_name='T_ResponseRoutePaint',automated=True,replace_existing=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);paint=assets.load_asset(BASE+'/T_ResponseRoutePaint');assert paint
    for a in list(actors.get_all_level_actors()):
        if a.get_actor_label().startswith('ResponseRoute_'):actors.destroy_actor(a)
    s=actors.spawn_actor_from_class(u.GTLandscapeSurface,u.Vector());s.set_actor_label('ResponseRoute_Surface')
    props(s,landscape=land,paint_origin_cm=u.Vector2D(ox,oy),paint_size_cm=size,enable_wheel_support=True,observe_player_wheels=True,follow_player=True)
    basins=[props(u.GTLandscapeMudRegion(),name='Pool_'+str(i+1),centre=u.Vector2D(cx,cy),half_size=u.Vector2D(rx,ry),
        wetness=1.,cohesion=.55,relief=.4,fragment_scale=1.65,basin_depth_cm=7.) for i,(cx,cy,rx,ry) in enumerate(PUDDLES)]
    def regions(p):
        if 'thirds' not in p:
            return [props(u.GTLandscapeMudRegion(),name=p['key'],centre=u.Vector2D((p['start']+p['end'])/2,0),half_size=u.Vector2D(1500,700),
                wetness=p['wet'],cohesion=p['cohesion'],relief=p['relief'],fragment_scale=p['scale'])]
        # CL2: a lane of thirds, one region per third (wetness per third, ClayWeight on all); the outer thirds reach 200 cm past the lane so the paint's edge ramp is inside a region.
        n=len(p['thirds']);third=(p['end']-p['start'])/n;out=[]
        for k,(label,wet) in enumerate(p['thirds']):
            lo=p['start']+k*third-(200 if k==0 else 0);hi=p['start']+(k+1)*third+(200 if k==n-1 else 0)
            out.append(props(u.GTLandscapeMudRegion(),name=p['key']+'_'+label,centre=u.Vector2D((lo+hi)/2,0),half_size=u.Vector2D((hi-lo)/2,700),
                wetness=wet,cohesion=p['cohesion'],relief=p['relief'],fragment_scale=p['scale'],clay_weight=p.get('clay',0.)))
        return out
    s.mud_regions=basins+[r for p in PROFILES for r in regions(p)]
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,paint)
    scans='/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/'
    assert u.GTLandscapeSurfaceSetupLibrary.import_rest_heights(s,assets.load_asset(scans+'T_brown_mud_02_Displacement'),assets.load_asset(scans+'T_mud_cracked_dry_03_Displacement'))
    for e in u.MaterialEditingLibrary.get_material_expressions(material):
        if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_Paint':e.set_editor_property('texture',paint)
        if isinstance(e,u.MaterialExpressionCustom):
            code=str(e.get_editor_property('code'))
            if '// RESPONSE_SOD' in code and '// ROUTE_VERGE' not in code:
                code=code.replace('float3 sod=', '// ROUTE_VERGE\nintact=max(intact,smoothstep(650.,1000.,abs(P.y)));\nfloat3 sod=')
                e.set_editor_property('code',code)
    displacement=next(e for e in u.MaterialEditingLibrary.get_material_expressions(material) if isinstance(e,u.MaterialExpressionCustom) and 'return saturate((h*Enabled+50)/65)' in str(e.get_editor_property('code')))
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(material,displacement,0,100.)
    props(land,landscape_material=material,enable_nanite=True,nanite_skirt_enabled=True,nanite_skirt_depth=100.)
    for p in PROFILES:
        cx=(p['start']+p['end'])/2
        study=actors.spawn_actor_from_class(u.GTMudDetailStudy,u.Vector(cx,0,0));study.set_actor_label('ResponseRoute_Tracks_'+p['key'])
        study.surface=s;study.seed_depth_scale=p['seed']
        sign=actors.spawn_actor_from_class(u.TextRenderActor,u.Vector(p['start']-120,-680,height(p['start']-120,-680)+160),u.Rotator(0,90,0))
        sign.set_actor_label('ResponseRoute_Sign_'+p['key']);text=sign.get_component_by_class(u.TextRenderComponent)
        text.set_text(p['title']);text.set_world_size(34);text.set_text_render_color(u.Color(225,215,175,255))
    for a in actors.get_all_level_actors():
        if isinstance(a,u.DirectionalLight):a.light_component.set_editor_property('forward_shading_priority',1 if a.get_actor_label()=='Sun' else 0)
    assert not u.MaterialEditingLibrary.recompile_material(material)
    for asset in [material,paint,route_spec]:assets.save_loaded_asset(asset)
    assert les.save_current_level()
    report.update(profiles=PROFILES,puddles=PUDDLES,material=material.get_path_name(),paint=paint.get_path_name(),legacy_sections=len(route_spec.spec.sections))
try:
    assert les.load_level(LEVEL)
    report['actors']=[{'class':a.get_class().get_name(),'label':a.get_actor_label(),'position':list(a.get_actor_location().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple())} for a in actors.get_all_level_actors()]
    if not AUDIT:
        setup()
    report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/('response-audit-report.json' if AUDIT else 'response-setup-report.json')).write_text(json.dumps(report,indent=2))
u.SystemLibrary.quit_editor()
