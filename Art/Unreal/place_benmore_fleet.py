"""Place one latest assembly per car beside Benmore's start, preserving the scene.

Run in the editor with PIE stopped. Reuses driving Blueprints where available;
the six art-only assemblies remain static. Only the current map and missing
ModelStudies assets are saved. All placements carry an ownership tag.
"""
import unreal as u
import json, math, shutil, hashlib, traceback, datetime
from pathlib import Path

ROOT=Path('C:/GrandTour')
OUT=ROOT/'Art/Export/BenmoreFleet';OUT.mkdir(exist_ok=True)
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
TAG='GT.BenmoreFleet.20261010'
E=u.EditorAssetLibrary
ACT=u.get_editor_subsystem(u.EditorActorSubsystem)
LES=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
V=u.GTVehicleSetupLibrary
report={'ok':False,'map':MAP,'cars':[],'limitations':['Art-only assemblies have no driving setup.','Placement validation is not a new handling or performance certification.']}

def spawn(cls,label,pos,rot):
    a=V.spawn_actor_of_class(world,cls,u.Transform(pos,rot,u.Vector(1,1,1)),label)
    assert a,label
    a.set_folder_path('GrandTour Fleet')
    a.set_editor_property('tags',[u.Name(TAG)])
    return a

def ground(x,y):
    hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,100000),u.Vector(x,y,-100000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
    assert hit is not None,('No terrain',x,y)
    return [v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z

try:
    assert not u.EditorLevelLibrary.get_game_world(),'Stop Play before placing the fleet'
    world=UE.get_editor_world()
    assert world.get_path_name().startswith(MAP+'.'),'Open Benmore Gaea first'
    original=list(ACT.get_all_level_actors())
    assert not any(TAG in [str(t) for t in a.tags] for a in original),'Fleet already installed; inspect rather than duplicate'
    mapfile=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=OUT/('L_Benmore_GaeaReview_before_fleet_'+stamp+'.umap')
    shutil.copy2(mapfile,backup)
    report['backup']=str(backup)
    report['original_sha256']=hashlib.sha256(backup.read_bytes()).hexdigest()
    report['original_actor_count']=len(original)
    report['original_actors']={a.get_path_name():{'label':a.get_actor_label(),'location':a.get_actor_location().to_tuple(),'rotation':a.get_actor_rotation().to_tuple()} for a in original}
    report['game_mode']=str(world.get_world_settings().get_editor_property('default_game_mode'))
    (OUT/'placement-report.json').write_text(json.dumps(report,indent=2))

    # Complete the interrupted import using its original validated FBX importer.
    importer=ROOT/'Art/Unreal/import_new_cars.py'
    ns={'__file__':str(importer)}
    exec(compile(importer.read_text().split('\ntry:\n')[0],str(importer),'exec'),ns)
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for name in ['CraftedUtility','Pathfinder2002','Impreza2003']:
        path='/Game/GrandTour/Vehicles/ModelStudies/'+name+'/BP_'+name+'_Review'
        if not E.does_asset_exist(path):
            _,_,r=ns['import_car'](name)
            report.setdefault('completed_imports',[]).append(r)
            (OUT/'placement-report.json').write_text(json.dumps(report,indent=2))

    base='/Game/GrandTour/Vehicles/'
    specs=[
        ('Ferrari288',base+'Ferrari288Good/BP_Ferrari288','drive'),
        ('E39Touring',base+'Bodies/E39Touring/BP_E39Touring','drive'),
        ('KadettA',base+'Bodies/KadettA/BP_KadettA','drive'),
        ('SJ413',base+'Bodies/SJ413/BP_SJ413','drive'),
        ('GraphicAdventure',base+'GraphicAdventure/Rounded/BP_GraphicAdventure','drive'),
        ('RangeRoverClassic',None,'native'),
        ('Panda1990',base+'Panda/Panda1990/BP_Panda1990_Review','static'),
        ('Prado',base+'Prado/Prado/BP_Prado_Review','static'),
        ('CraftedUtility',base+'ModelStudies/CraftedUtility/BP_CraftedUtility_Review','static'),
        ('Pathfinder2002',base+'ModelStudies/Pathfinder2002/BP_Pathfinder2002_Review','static'),
        ('Impreza2003',base+'ModelStudies/Impreza2003/BP_Impreza2003_Review','static'),
        ('LandCruiser80',base+'Bodies/LandCruiser80/SK_LandCruiser80','skeletal_static'),
    ]
    starts=[a for a in original if isinstance(a,u.PlayerStart)]
    assert len(starts)==1,[(a.get_actor_label(),str(a.get_actor_location())) for a in starts]
    start=starts[0];origin=start.get_actor_location();yaw=start.get_actor_rotation().yaw
    f=u.Vector(math.cos(math.radians(yaw)),math.sin(math.radians(yaw)),0)
    r=u.Vector(-f.y,f.x,0)
    ignore=[a for a in original if not isinstance(a,u.LandscapeProxy)]
    report['start']={'location':origin.to_tuple(),'yaw':yaw}
    # Two rows beside the route, with space to walk between and drive out.
    sites=[]
    for i in range(12):
        p=origin+f*(1100+(i%6)*700)+r*(850+(i//6)*1150)
        z=ground(p.x,p.y)
        # Fit the wheel plane to local terrain; reject sharp or steep ground.
        front=ground(p.x+f.x*160,p.y+f.y*160)
        rear=ground(p.x-f.x*160,p.y-f.y*160)
        right=ground(p.x+r.x*85,p.y+r.y*85)
        left=ground(p.x-r.x*85,p.y-r.y*85)
        sf=(front-rear)/320;sr=(right-left)/170
        residual=max(abs((front+rear)/2-z),abs((right+left)/2-z))
        assert math.hypot(sf,sr)<.22 and residual<16,('Uneven parking site',i,sf,sr,residual)
        normal=u.Vector(-f.x*sf-r.x*sr,-f.y*sf-r.y*sr,1)
        rot=u.MathLibrary.make_rot_from_xz(u.Vector(f.x,f.y,sf),normal)
        sites.append((u.Vector(p.x,p.y,z),rot,residual))

    with u.ScopedEditorTransaction('Add the Grand Tour fleet to Benmore'):
        for (name,path,kind),(pos,rot,residual) in zip(specs,sites):
            if kind=='native':cls=u.GTCarPawn
            elif kind=='skeletal_static':cls=u.SkeletalMeshActor
            else:
                bp=E.load_asset(path);assert bp,path
                cls=bp.generated_class();assert cls,path
            # Probe native local bounds with the complete actual assembly.
            a=spawn(cls,'Benmore_Fleet_'+name,u.Vector(pos.x,pos.y,pos.z),u.Rotator())
            if kind=='skeletal_static':
                c=a.get_component_by_class(u.SkeletalMeshComponent)
                c.set_skeletal_mesh_asset(E.load_asset(path));c.set_simulate_physics(False)
                c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
            meshes=[c for c in a.get_components_by_class(u.MeshComponent) if isinstance(c,(u.StaticMeshComponent,u.SkeletalMeshComponent))]
            assert meshes,name+' has no meshes'
            for c in meshes:
                asset=c.static_mesh if isinstance(c,u.StaticMeshComponent) else c.get_editor_property('skeletal_mesh_asset')
                if asset:
                    assert all(c.get_material(k) for k in range(c.get_num_materials())),(name,c.get_name(),'missing material')
            if kind in ('drive','native'):
                a.set_editor_property('auto_possess_player',u.AutoReceiveInput.DISABLED)
                a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
                a.get_chaos_movement().set_handbrake_input(True)
                setups=a.get_chaos_movement().get_editor_property('wheel_setups');assert len(setups)==4
                c=a.get_component_by_class(u.SkeletalMeshComponent)
                bottoms=[]
                for setup in setups:
                    wc=u.get_default_object(setup.get_editor_property('wheel_class'))
                    bone=str(setup.get_editor_property('bone_name'))
                    local=c.get_socket_transform(bone,u.RelativeTransformSpace.RTS_ACTOR).translation
                    bottoms.append(local.z-wc.get_editor_property('wheel_radius'))
                bottom=min(bottoms)
            elif kind=='skeletal_static':
                # Physics-asset bounds omit the tyres. Use the LC80's verified
                # 41.5 cm tyre radius and actual reference wheel bones.
                bottom=min(c.get_socket_transform(b,u.RelativeTransformSpace.RTS_ACTOR).translation.z-41.5 for b in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR'])
            else:
                bounds=a.get_actor_bounds(False)
                bottom=bounds[0].z-bounds[1].z-pos.z
            location=pos+u.MathLibrary.get_up_vector(rot)*(2-bottom)
            a.set_actor_rotation(rot,False);a.set_actor_location(location,False,True)
            if name=='Ferrari288':
                assert any(c.static_mesh and 'Expedition' in c.static_mesh.get_name() for c in a.get_components_by_class(u.StaticMeshComponent)),'Missing expedition kit'
            row={'name':name,'label':a.get_actor_label(),'class':a.get_class().get_path_name(),'asset':path,'type':'drivable' if kind in ('drive','native') else 'static art model','location':location.to_tuple(),'rotation':rot.to_tuple(),'mesh_components':len(meshes),'local_bottom_cm':bottom,'terrain_residual_cm':residual}
            report['cars'].append(row)
        target=origin+f*2850+r*1400;target.z=ground(target.x,target.y)+100
        camera_pos=target-f*3000-r*2800+u.Vector(0,0,2100)
        camera=spawn(u.CameraActor,'Benmore_Fleet_Overview',camera_pos,u.MathLibrary.find_look_at_rotation(camera_pos,target))
        camera.camera_component.set_field_of_view(65)
        UE.set_level_viewport_camera_info(camera_pos,camera.get_actor_rotation())
    for a in original:
        prev=report['original_actors'][a.get_path_name()]
        assert tuple(prev['location'])==a.get_actor_location().to_tuple()
        assert tuple(prev['rotation'])==a.get_actor_rotation().to_tuple()
    assert str(world.get_world_settings().get_editor_property('default_game_mode'))==report['game_mode']
    assert LES.save_current_level(),'Map save failed'
    report['ok']=True;report['saved_sha256']=hashlib.sha256(mapfile.read_bytes()).hexdigest()
    report['saved_actor_count']=len(ACT.get_all_level_actors())
    report['existing_scene_preserved']=True
    u.log('BENMORE_FLEET_SAVED '+str(len(report['cars']))+' cars')
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'placement-report.json').write_text(json.dumps(report,indent=2))
