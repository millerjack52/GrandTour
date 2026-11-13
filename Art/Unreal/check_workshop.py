"""Exercise the live workshop on the existing rally map, including GPU previews and reversible state."""
import gc, hashlib, json, time, traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/WorkshopQA';OUT.mkdir(parents=True,exist_ok=True)
report=dict(ok=False,checks=[],images=[])
world=pc=car=work=None
protected=[ROOT/'Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap',ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
slot='GT_Workshop_RangeRover_QA'
save_path=ROOT/'Saved/SaveGames'/(slot+'.sav')
old_save=save_path.read_bytes() if save_path.exists() else None

def save(): (OUT/'check.json').write_text(json.dumps(report,indent=2))
def console(command):u.SystemLibrary.execute_console_command(world,command,pc)
def check(value,description):
    assert value,description
    report['checks'].append(description);save()
def capture(name):
    yield 2
    path=OUT/(name+'.png');stamp=time.time()
    console('Shot SHOWUI -nosuffix filename="'+path.as_posix()+'"')
    deadline=time.monotonic()+40
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<deadline,'Screenshot timeout: '+name
        yield .2
    yield .5
    report['images'].append(str(path));save()
def material(component):return component.get_material(0)
def scalar(mat,param):return mat.get_scalar_parameter_value(param)
def vector(mat,param):
    value=mat.get_vector_parameter_value(param);return (value.r,value.g,value.b,value.a)
def loadout():return [str(e.part_id) for e in car.get_parts().get_loadout()]
def inventory():return [(str(e.item_id),e.count) for e in car.get_boot().items]

def run():
    global world,pc,car,work
    u.GameplayStatics.delete_game_in_slot(slot,0)
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'),'existing rally map loads')
    yield 3; level.editor_set_viewport_realtime(False)
    check(u.GTPlayWindowLibrary.request_play_in_new_window(1600,900),'1600x900 play window starts')
    deadline=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world(); assert time.monotonic()<deadline; yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();work=pc.get_workshop()
    console('t.IdleWhenNotForeground 0');console('Slate.bAllowThrottling 0')
    pc.select_lane(1);car.get_chaos_movement().set_handbrake_input(True)
    yield 5
    deadline=time.monotonic()+60
    while car.get_velocity().length()>20:
        assert time.monotonic()<deadline,'Car did not settle'; yield .2
    body=car.get_body();parts=car.get_parts();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    boot_before=inventory();loadout_before=loadout()
    view=pc.get_view_target()
    check(body.workshop_ready(),'body and actual course tyre material variants load')
    check(body.workshop_wheels_ready(),'all six wheel assets load and four wheel pairs are created')
    check(body.workshop_equipment_ready(),'all three fitted equipment assets load')
    equipment=sorted((c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('WorkshopEquipment_')),key=lambda c:c.get_name())
    check(len(equipment)==3 and body.workshop_equipment==0 and all(not c.is_visible() for c in equipment),'new cosmetic profile starts without equipment')
    for c in equipment:
        check(c.get_attach_parent()==mesh and c.get_editor_property('relative_location').length()<.001,'equipment uses the car-origin mount '+c.get_name())
        check(c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION,'equipment does not introduce extra physics collision '+c.get_name())
    rims=sorted((c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('WorkshopRim_')),key=lambda c:c.get_name())
    tyres=sorted((c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('WorkshopTyre_')),key=lambda c:c.get_name())
    check(len(rims)==len(tyres)==4,'four independent rims and four tyres')
    state=car.get_body_state();state.set_editor_property('tyre_coat',[.2,.35,.5,.65]);state.set_editor_property('wetness',.6);yield .2
    check(state.get_tyre_coat(0)>.1 and state.wetness>.1,'nonzero dirt and wetness test state is active')
    check(all(abs(scalar(c.get_material(0),'Coat')-state.get_tyre_coat(i))<.02 for i,c in enumerate(tyres)),'distinct per-wheel mud coats reach new tyre materials')
    check(all(abs(scalar(c.get_material(0),'Wetness')-state.wetness)<.02 for c in rims),'wetness reaches all new rims')
    state.wash();yield .2
    check(not mesh.is_material_section_shown(mesh.get_material_index('M_Wheel'),0),'original wheel section is hidden without hiding bones')
    for i,c in enumerate(rims):
        check(str(c.get_attach_socket_name())==['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR'][i],'rim attaches to correct animated wheel '+str(i))
        check((c.get_world_location()-mesh.get_socket_location(c.get_attach_socket_name())).length()<.1,'wheel pivot matches socket '+str(i))
        check(c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION,'visual wheel does not add a physics collider '+str(i))
    check(work.open(),'workshop opens while parked');yield 2
    # Every subset previews and commits independently; removal uses the same reversible path.
    saved_mask=0
    for target_mask in [1,3,7,6,2,0,4,5,7]:
        for choice in range(3):
            bit=1<<choice
            if (saved_mask&bit)==(target_mask&bit):continue
            work.select_part(4);work.preview(choice)
            check(body.workshop_equipment==saved_mask^bit,'equipment preview '+str(saved_mask)+' toggle '+str(choice))
            check(loadout()==loadout_before and inventory()==boot_before,'equipment preview preserves mechanical state '+str(saved_mask)+'/'+str(choice))
            work.compare(True);check(body.workshop_equipment==saved_mask,'equipment compare restores fitted set '+str(saved_mask)+'/'+str(choice))
            work.compare(False);check(body.workshop_equipment==saved_mask^bit,'equipment compare release restores preview '+str(saved_mask)+'/'+str(choice))
            work.cancel();check(body.workshop_equipment==saved_mask,'equipment cancel restores fitted set '+str(saved_mask)+'/'+str(choice))
            work.select_part(4);work.preview(choice);check(work.fit(),'equipment commits '+str(saved_mask)+'/'+str(choice));saved_mask^=bit
        check(body.workshop_equipment==target_mask and all(c.is_visible()==bool(target_mask&(1<<i)) for i,c in enumerate(equipment)),'equipment combination '+str(target_mask))
    work.select_part(4);work.preview(1);work.select_part(0)
    check(body.workshop_equipment==7,'switching category discards pending equipment removal');work.cancel()
    work.select_part(4);work.preview(0);work.close();yield .2
    check(body.workshop_equipment==7,'closing workshop discards pending accessory removal')
    check(work.open(),'workshop reopens after equipment close/cancel')
    work.select_part(4);yield from capture('10-equipment-fitted');work.cancel()
    check(u.GameplayStatics.is_game_paused(world),'physics is paused during preview')
    check(pc.is_move_input_ignored() and pc.is_look_input_ignored(),'driving and look input are blocked')
    check(pc.get_view_target()!=view,'workshop owns the camera')
    yield from capture('01-walk-around')
    panel=next(c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name()=='Panel_Bonnet')
    mat=material(panel);original_texture=mat.get_texture_parameter_value('PaintAlbedo')
    check(scalar(mat,'WorkshopPaintAmount')==0,'default paint remains unchanged')
    work.select_part(0);work.preview(1);yield .5
    report['paint_debug']={'parent':mat.get_editor_property('parent').get_path_name(),'colour':vector(mat,'WorkshopPaint'),'amount':scalar(mat,'WorkshopPaintAmount'),'hidden_slots':body.hidden_skeletal_slots}
    check(scalar(mat,'WorkshopPaintAmount')==1 and scalar(mat,'UsePaint')==1,'paint preview retains baked detail')
    check(mat.get_texture_parameter_value('PaintAlbedo')==original_texture,'preview preserves the original albedo texture')
    check(loadout()==loadout_before and inventory()==boot_before,'preview leaves mechanical loadout and inventory untouched')
    yield from capture('02-paint-preview')
    work.compare(True);yield .3
    check(scalar(mat,'WorkshopPaintAmount')==0,'compare shows fitted paint')
    yield from capture('03-compare-fitted')
    work.compare(False);check(scalar(mat,'WorkshopPaintAmount')==1,'releasing compare restores preview')
    work.cancel();check(scalar(mat,'WorkshopPaintAmount')==0,'cancel restores original paint')
    work.select_part(0);work.preview(1);check(work.fit(),'paint fits and saves')
    check(u.GameplayStatics.does_save_game_exist(slot,0),'committed cosmetic save exists')
    work.select_part(1);wheel=mesh.get_material(mesh.get_material_index('M_Wheel'));rim_before=rims[0].static_mesh
    for ri,rname in enumerate(['SM_Rim_Pressed','SM_Rim_Alloy','SM_Rim_Heavy']):
        work.select_part(1);work.preview(ri)
        check(all(c.static_mesh.get_name()==rname for c in rims),'rim model preview '+rname)
        # Switching categories restores fitted rim; set the pair directly for the complete compatibility matrix.
        for ti,tname in enumerate(['SM_Tyre_Road','SM_Tyre_AllTerrain','SM_Tyre_Mud']):
            body.set_workshop_appearance(1,ri,ti)
            check(all(c.static_mesh.get_name()==rname for c in rims) and all(c.static_mesh.get_name()==tname for c in tyres),'visual combination '+str(ri)+'/'+str(ti))
        work.cancel()
    work.select_part(1);work.preview(1)
    check(all(c.static_mesh.get_name()=='SM_Rim_Alloy' for c in rims),'alloy preview changes actual geometry')
    yield from capture('04-wheel-preview')
    work.compare(True);check(rims[0].static_mesh==rim_before,'rim compare restores fitted geometry')
    work.compare(False);check(work.fit(),'rim finish fits and saves')
    work.select_part(2);work.preview(1)
    check(loadout()==loadout_before,'tyre preview does not change physics')
    check(all(c.static_mesh.get_name()=='SM_Tyre_AllTerrain' for c in tyres),'all-terrain preview changes actual tyre geometry')
    yield from capture('05-tyres-preview')
    check(work.fit(),'all-terrain tyre test fit succeeds')
    check(any(str(e.part_id)=='Part.TyreAllTerrain' for e in parts.get_loadout()),'fit updates the real all-terrain tyre slot')
    work.select_part(2);work.preview(2);check(work.fit(),'mud tyres fit')
    check(any(str(e.part_id)=='Part.TyreKnobbly' for e in parts.get_loadout()),'mud uses existing knobbly handling')
    check(all(c.static_mesh.get_name()=='SM_Tyre_Mud' for c in tyres),'mud fit updates all four meshes')
    work.select_part(2);work.preview(0);work.compare(True)
    check(all(c.static_mesh.get_name()=='SM_Tyre_Mud' for c in tyres),'tyre compare restores fitted mud meshes')
    work.cancel();check(body.workshop_tyres==2,'tyre cancel restores fitted selection')
    work.select_part(2);work.zoom(3);yield from capture('07-mud-tyres');work.cancel()
    check(inventory()==boot_before,'test fitting does not grant or remove inventory')
    work.select_part(0);work.preview(3);work.close();yield 1
    check(body.workshop_paint==1,'closing discards only the pending preview')
    check(not u.GameplayStatics.is_game_paused(world) and pc.get_view_target()==view,'close restores pause and driving camera')
    check(not pc.is_move_input_ignored() and not pc.is_look_input_ignored(),'close restores movement and look input')
    check(work.open(),'workshop can reopen after fitting');work.orbit(460,30);work.zoom(1);yield 2
    yield from capture('06-orbit-other-side')
    work.close();yield .5
    # Suspension fitting owns solver configuration per vehicle, including visual travel limits.
    movement=car.get_chaos_movement()
    check(movement.get_suspension_kit()==0,'Range Rover starts on Standard suspension')
    original_suspension=json.loads(movement.suspension_report())
    check([w['raise'] for w in original_suspension['wheels']]==[0,0,2.5,2.5],'physical bump stops match measured arch clearance')
    check(work.open(),'open suspension workshop');work.select_part(3);before=loadout()
    work.preview(2);yield .2
    check(loadout()==before and json.loads(movement.suspension_report())==original_suspension,'suspension preview leaves actual loadout and solver untouched')
    work.compare(True);work.compare(False);work.cancel()
    check(loadout()==before and movement.get_suspension_kit()==0,'suspension compare and cancel are reversible')
    work.select_part(3);yield from capture('08-suspension-menu');work.close()
    other_transform=car.get_actor_transform();other_transform.translation+=u.Vector(0,600,100)
    other=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,other_transform,'IndependentSuspension')
    other.get_chaos_movement().set_handbrake_input(True);yield 3
    report['suspension_samples']=[]
    for choice,part_id in enumerate(['Part.Suspension','Part.SuspensionHD','Part.SuspensionTrail']):
        pc.select_lane(1);movement.set_handbrake_input(True);yield 4
        check(work.open(),'open for suspension test '+part_id);work.select_part(3);work.preview(choice)
        if part_id not in loadout():check(work.fit(),'fit suspension '+part_id)
        work.close();yield 4
        state_report=json.loads(movement.suspension_report())
        check(state_report['kit']==choice,'solver uses selected suspension '+part_id)
        check(all(abs(w['drop']-[16,18,21][choice])<.01 and abs(w['rate']-[34000,41000,36000][choice])<1 for w in state_report['wheels']),'spring rate and droop reach solver '+part_id)
        check(all(abs(w['damping']-[.62,.72,.68][choice])<.001 for w in state_report['wheels']),'damping reaches solver '+part_id)
        centres=[mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation.z for n in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']]
        check(work.open(),'inspect settled stance '+part_id);work.select_part(3)
        yield from capture('09-suspension-'+str(choice));work.close()
        check(inventory()==boot_before,'suspension lab fitting preserves inventory '+part_id)
        independent=json.loads(other.get_chaos_movement().suspension_report())
        check(independent['kit']==0 and all(w['drop']==16 and w['rate']==34000 for w in independent['wheels']),'fitting does not mutate another Range Rover '+part_id)
        movement.set_handbrake_input(False);end=time.monotonic()+2
        while time.monotonic()<end:
            movement.set_throttle_input(.75);movement.set_steering_input(.35);yield .05
        speed=car.get_velocity().length();check(speed>50,'accelerates and steers with '+part_id)
        report['suspension_samples'].append(dict(kit=part_id,solver=state_report,hub_z=centres,speed_cm_s=speed));save()
        car.reset_driving_inputs()
    heights=[-sum(s['hub_z'])/4 for s in report['suspension_samples']]
    check(heights[1]>heights[0]+1 and heights[2]>heights[1]+1,'Touring and Trail produce successively higher actual ride heights')
    # Mechanical loadout persistence uses the existing part system, not a second cosmetic save.
    other.destroy_actor();other_transform.translation+=u.Vector(0,0,600)
    restored=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,other_transform,'SuspensionLoadoutRestore')
    check(restored is not None,'loadout restore fixture spawns clear of other vehicles')
    restored.get_parts().apply_loadout(parts.get_loadout(),False);restored.get_chaos_movement().set_handbrake_input(True);yield .25
    check(restored.get_chaos_movement().get_suspension_kit()==2,'restored mechanical loadout reapplies Trail suspension')
    airborne_mesh=restored.get_component_by_class(u.SkeletalMeshComponent)
    droop=[airborne_mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation.z for n in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']]
    report['airborne_trail_hub_z']=droop;save()
    check(all(16<z<18 for z in droop),'Trail wheel animation reaches 21cm full droop without the old 16cm clamp')
    restored.destroy_actor();pc.select_lane(1);movement.set_handbrake_input(True);yield 4
    # Previously paused sessions must remain paused on exit.
    u.GameplayStatics.set_game_paused(world,True);check(work.open(),'can inspect an already-paused session')
    work.close();check(u.GameplayStatics.is_game_paused(world),'pre-existing pause is restored')
    u.GameplayStatics.set_game_paused(world,False)
    # A fresh pawn reads only committed cosmetics. Destruction also cancels an open session.
    transform=car.get_actor_transform();check(work.open(),'open before pawn replacement')
    car.destroy_actor();yield .5
    check(not work.is_open(),'destroying the vehicle closes the session')
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,transform,'WorkshopReload')
    pc.possess(car);car.get_chaos_movement().set_handbrake_input(True);yield 2
    check(car.get_body().workshop_paint==1 and car.get_body().workshop_rims==1,'fresh pawn restores committed cosmetics')
    check(car.get_body().workshop_equipment==7,'fresh pawn restores committed accessory combination')
    restored_equipment=[c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('WorkshopEquipment_')]
    check(len(restored_equipment)==3 and all(c.is_visible() for c in restored_equipment),'restored equipment geometry is visible')
    car.get_chaos_movement().set_handbrake_input(False)
    rolling=next(c for c in car.get_components_by_class(u.StaticMeshComponent) if c.get_name()=='WorkshopRim_0')
    rotation_before=rolling.get_world_rotation()
    driven_mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    bone_before=driven_mesh.get_socket_transform('Wheel_FL',u.RelativeTransformSpace.RTS_COMPONENT).rotation
    end=time.monotonic()+2
    while time.monotonic()<end:
        car.get_chaos_movement().set_throttle_input(.8);yield .05
    check(car.get_velocity().length()>50,'car drives after leaving workshop')
    check(rolling.get_world_rotation()!=rotation_before,'attached wheel rolls while driving')
    check(driven_mesh.get_socket_transform('Wheel_FL',u.RelativeTransformSpace.RTS_COMPONENT).rotation!=bone_before,'wheel bone animates relative to chassis')
    driven_mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    check((rolling.get_world_location()-driven_mesh.get_socket_location('Wheel_FL')).length()<.1,'wheel stays on animated hub under motion')
    check(all(c.get_editor_property('relative_location').length()<.001 and c.is_visible() for c in restored_equipment),'all accessories remain mounted while driving')
    state=car.get_body_state();state.set_editor_property('wetness',.65);yield .2
    check(all(abs(scalar(c.get_material(0),'Wetness')-state.wetness)<.02 for c in restored_equipment),'equipment wetness follows the vehicle')
    check(not work.open(),'moving car cannot enter workshop')
    car.reset_driving_inputs()
    report['drive_samples']=[]
    for choice,part_id in enumerate(['Part.Tyre','Part.TyreAllTerrain','Part.TyreKnobbly']):
        pc.select_lane(1);car.get_chaos_movement().set_handbrake_input(True);yield 3
        deadline=time.monotonic()+45
        while car.get_velocity().length()>20:
            assert time.monotonic()<deadline,'Drive comparison failed to stop';yield .2
        check(work.open(),'open for drive test '+part_id);work.select_part(2);work.preview(choice)
        if part_id not in loadout():check(work.fit(),'fit for drive test '+part_id)
        work.close();yield .3
        car.get_chaos_movement().set_handbrake_input(False)
        end=time.monotonic()+2
        while time.monotonic()<end:
            car.get_chaos_movement().set_throttle_input(.75);car.get_chaos_movement().set_steering_input(.25);yield .05
        speed=car.get_velocity().length();check(speed>50,'accelerates and steers on '+part_id)
        check(car.get_body().workshop_tyres==choice,'driving keeps fitted geometry '+part_id)
        for c in car.get_components_by_class(u.StaticMeshComponent):
            if c.get_name().startswith(('WorkshopRim_','WorkshopTyre_')):
                assert (c.get_world_location()-driven_mesh.get_socket_location(c.get_attach_socket_name())).length()<.1,'wheel detached while steering'
        state=car.get_body_state();wheelmat=rolling.get_material(0)
        check(abs(scalar(wheelmat,'Coat')-state.get_tyre_coat(0))<.02 and abs(scalar(wheelmat,'Wetness')-state.wetness)<.02,'wheel materials follow surface state '+part_id)
        report['drive_samples'].append({'tyre':part_id,'speed_cm_s':speed,'rotation':str(rolling.get_world_rotation())});save()
        car.reset_driving_inputs()
    # Other fleet cars retain original cosmetics; LayoutCheck covers their mechanical-only workshop.
    car.destroy_actor()
    cls=u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/E39Touring/BP_E39Touring.BP_E39Touring_C')
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,transform,'OtherCar')
    pc.possess(car);yield 1
    check(not car.get_body().workshop_ready(),'other fleet car remains outside Range Rover cosmetic customization')
    check(not any(c.get_name().startswith('WorkshopRim_') for c in car.get_components_by_class(u.StaticMeshComponent)),'other fleet car gets no replacement wheels')
    check(not car.get_body().workshop_equipment_ready() and not any(c.get_name().startswith('WorkshopEquipment_') for c in car.get_components_by_class(u.StaticMeshComponent)),'other fleet car gets no equipment components')
    check(car.get_chaos_movement().get_suspension_kit()==-1,'other fleet car retains authored suspension')
    check(hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},'rally and LiDAR map assets are unchanged')
    report['ok']=True;save()
    world=pc=car=work=panel=mat=mesh=body=parts=wheel=view=None;gc.collect()
    u.EditorLevelLibrary.editor_end_play();yield 3
    level.load_level('/Engine/Maps/Entry');yield 2

steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<480,'Workshop check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle)
        if old_save is not None:save_path.write_bytes(old_save)
        elif save_path.exists():save_path.unlink()
        steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
