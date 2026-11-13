"""Interactive design controls. No automatic apply, editor launch, or process termination."""
from pathlib import Path
import array
import json
import math
import shutil
import struct
import sys
import time
import uuid
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/tools')) if str(ROOT/'Art/tools') not in sys.path else None
import lidar_authoring as design
LEVEL='/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy'
BASE=ROOT/'Art/Export/LidarStudy'
ACTORS=u.get_editor_subsystem(u.EditorActorSubsystem)


def require_level():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0] != LEVEL:
        raise RuntimeError('Open L_LidarStudy before using LiDAR design tools')
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Stop Play before editing designs')
    return world


def paths():
    return [a for a in ACTORS.get_all_level_actors() if isinstance(a,u.GTLidarAuthoringPath)]


def water_reference():
    # Preparation writes the original course and surface, even after bed edits.
    path=BASE/'Place/authoring-reference.json'
    if not path.exists():
        raise RuntimeError('Run Art/lidar_place.ps1 -Mode Prepare once to create the water reference')
    return json.loads(path.read_text())['river_points_cm']


def surface_at(x,y,reference=None):
    points=reference if reference is not None else water_reference()
    best=min(points,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)
    if math.hypot(best[0]-x,best[1]-y)>2000:
        raise ValueError('Bed control point is more than 20 m from the existing river course')
    return best[2]


def source_height(x,y):
    raw=array.array('H');raw.frombytes((BASE/'height.r16').read_bytes())
    fx=max(0,min(2015.999,(x+185000)/370000*2016));fy=max(0,min(2015.999,(y+185000)/370000*2016))
    i,j=int(fx),int(fy);a,b=fx-i,fy-j
    q,r,v,w=(raw[k]/65535*32768 for k in (j*2017+i,j*2017+i+1,(j+1)*2017+i,(j+1)*2017+i+1))
    return q+(r-q)*a+(w-r)*b if a>=b else q+(w-v)*a+(v-q)*b


def current_height(x,y):
    author=next((a for a in ACTORS.get_all_level_actors() if isinstance(a,u.GTProceduralGround)),None)
    if author:
        xy=u.Vector2D(x,y)
        for tile in author.relief_tiles.values():
            origin=tile.get_actor_location()
            if origin.x<=x<=origin.x+tile.span_cm and origin.y<=y<=origin.y+tile.span_cm:return tile.height_at(xy)
        return author.base_height_at(xy)
    return source_height(x,y)


def set_points(actor,points):
    sp=actor.control_points;sp.clear_spline_points(False)
    for i,p in enumerate(points):
        sp.add_spline_point(u.Vector(*p),u.SplineCoordinateSpace.WORLD,False)
        sp.set_spline_point_type(i,u.SplinePointType.LINEAR,False)
    sp.update_spline()


def new_track():
    require_level()
    location,rotation=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_level_viewport_camera_info()
    x,y=location.x,location.y
    with u.ScopedEditorTransaction('New LiDAR mud track'):
        a=ACTORS.spawn_actor_from_class(u.GTLidarAuthoringPath,u.Vector(x,y,current_height(x,y)))
        a.design_id=str(uuid.uuid4());a.width_metres=2.4;a.design_name='Logging mud track '+a.design_id[:4]
        a.set_actor_label(a.design_name);a.set_folder_path('LiDAR Designs')
        angle=math.radians(rotation.yaw);dx,dy=math.cos(angle)*1000,math.sin(angle)*1000
        set_points(a,[[x+t*dx,y+t*dy,current_height(x+t*dx,y+t*dy)] for t in (0,1,2)])
        ACTORS.set_selected_level_actors([a])
    u.log('Mud draft created. Edit its spline, then Tools > LiDAR Place > Save designs. No terrain changed.')


def new_bed():
    require_level();ref=water_reference()
    location,_=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_level_viewport_camera_info()
    index=min(range(len(ref)),key=lambda k:math.hypot(ref[k][0]-location.x,ref[k][1]-location.y))
    if math.hypot(ref[index][0]-location.x,ref[index][1]-location.y)>10000:
        raise ValueError('Move the editor camera within 100 m of the river first')
    ids=sorted(set([max(0,index-20),max(0,index-10),index,min(len(ref)-1,index+10),min(len(ref)-1,index+20)]))
    points=[[ref[k][0],ref[k][1],ref[k][2]-35] for k in ids]
    with u.ScopedEditorTransaction('New LiDAR river bed'):
        a=ACTORS.spawn_actor_from_class(u.GTLidarAuthoringPath,u.Vector(*points[0]))
        a.kind=u.GTLidarPathKind.RIVER_BED;a.design_id=str(uuid.uuid4());a.width_metres=8
        a.design_name='River bed '+a.design_id[:4];a.set_actor_label(a.design_name);a.set_folder_path('LiDAR Designs')
        set_points(a,points);ACTORS.set_selected_level_actors([a])
    u.log('Bed controls are actual bed elevations. Move Z to raise/lower the bed; the river course and water level remain fixed.')


def fit_bed():
    require_level();ref=water_reference()
    selected=[a for a in ACTORS.get_selected_level_actors() if isinstance(a,u.GTLidarAuthoringPath) and a.kind==u.GTLidarPathKind.RIVER_BED]
    if not selected: raise ValueError('Select a LiDAR River Bed design first')
    with u.ScopedEditorTransaction('Set river bed depth'):
        for a in selected:
            a.modify();a.control_points.modify();points=[]
            for k in range(a.control_points.get_number_of_spline_points()):
                p=a.control_points.get_location_at_spline_point(k,u.SplineCoordinateSpace.WORLD)
                points.append([p.x,p.y,surface_at(p.x,p.y,ref)-a.target_depth_metres*100])
            set_points(a,points)
    inspect_selected()


def selected_track_pairs():
    """Return (selected spline, export design), preserving the selected route as input."""
    selected=[];drafts=paths()
    for actor in ACTORS.get_selected_level_actors():
        target=None
        if isinstance(actor,u.GTLidarAuthoringPath) and actor.kind==u.GTLidarPathKind.MUD_TRACK:
            target=actor
        elif isinstance(actor,u.GTProceduralRoad) and 'LidarMudTrack' in [str(t) for t in actor.tags]:
            ids=[str(t).removeprefix('LidarDesign:') for t in actor.tags if str(t).startswith('LidarDesign:')]
            # Existing installed maps predate the ID tag. Resolve their exact generated
            # label through build metadata; never infer a route from proximity.
            if not ids:
                built=BASE/'Place/roads.json'
                rows=json.loads(built.read_text(encoding='utf-8')) if built.exists() else []
                ids=[r['authoring']['id'] for r in rows if r.get('authoring') and
                     actor.get_actor_label()=='LidarStudy_'+r['name']]
            matches=[a for a in drafts if a.kind==u.GTLidarPathKind.MUD_TRACK and a.design_id in ids]
            if len(ids)==1 and len(matches)==1:target=matches[0]
        if target is None:
            raise ValueError('Cannot snap "'+actor.get_actor_label()+'". Select the logging track under '
                             'LiDAR Designs in the Outliner (its DesignPoints spline), or its linked built mud-track actor. '
                             'Terrain tiles, foliage and gravel roads are not track designs.')
        if any(prior==target and source!=actor for source,prior in selected):
            raise ValueError('Select either the design or its built road, not both: they may contain different edits.')
        if (actor,target) not in selected:selected.append((actor,target))
    if not selected:raise ValueError('Select the logging track under LiDAR Designs in the Outliner, then use Snap selected track to ground.')
    return selected


def selected_tracks():
    return [target for source,target in selected_track_pairs()]


def fit_track():
    require_level()
    try:selected=selected_track_pairs()
    except ValueError as error:
        u.log_warning(str(error))
        u.EditorDialog.show_message('Snap track to ground',str(error),u.AppMsgType.OK)
        return
    # Sample everything before starting the transaction; a failed query must not
    # leave half a selection snapped. The selected spline's XY is authoritative:
    # a built road may have been moved or extended since the design was exported.
    plans=[];moved=0;largest=0.
    for a,target in selected:
        points=[]
        for k in range(a.control_points.get_number_of_spline_points()):
            p=a.control_points.get_location_at_spline_point(k,u.SplineCoordinateSpace.WORLD)
            z=current_height(p.x,p.y)
            if not math.isfinite(z):raise ValueError('Ground height is not finite; no controls changed')
            delta=abs(z-p.z);moved+=int(delta>.1);largest=max(largest,delta)
            points.append(u.Vector(p.x,p.y,z))
        widths=[a.width_cm/100*a.control_points.get_scale_at_spline_point(k).y for k in range(len(points))] if a!=target else []
        plans.append((a,target,points,widths))
    with u.ScopedEditorTransaction('Project mud track to ground'):
        for a,target,points,widths in plans:
            a.modify();a.control_points.modify()
            for k,p in enumerate(points):
                a.control_points.set_location_at_spline_point(k,p,u.SplineCoordinateSpace.WORLD,False)
                if a!=target:
                    # Show the exported control polygon, not an unrelated Unreal
                    # Hermite curve that can loop/overshoot between ground points.
                    a.control_points.set_spline_point_type(k,u.SplinePointType.LINEAR,False)
            a.control_points.update_spline()
            if a!=target:
                target.modify();target.control_points.modify()
                set_points(target,[[p.x,p.y,p.z] for p in points])
                for k,width in enumerate(widths):
                    target.control_points.set_scale_at_spline_point(k,u.Vector(1,width/target.width_metres,1),False)
                target.control_points.update_spline()
    ACTORS.set_selected_level_actors([source for source,target in selected])
    message=f'Snapped {len(selected)} selected track spline(s): {moved} points moved, largest height change {largest:.1f} cm. '
    message+='The selected route is retained and its design synchronized; Save all designs and ApplyDesign rebuild the drivable surface.'
    u.log(message)
    u.SystemLibrary.print_string(require_level(),message,True,False,u.LinearColor(.2,1,.3,1),8.)


def add_condition():
    require_level()
    selected=[a for a in ACTORS.get_selected_level_actors() if isinstance(a,u.GTLidarAuthoringPath) and a.kind==u.GTLidarPathKind.MUD_TRACK]
    if not selected:raise ValueError('Select a LiDAR mud-track design first')
    with u.ScopedEditorTransaction('Add local mud condition'):
        for a in selected:
            row=serialize(a);pts=row['points_cm'];length=sum(math.dist(p,q) for p,q in zip(pts,pts[1:]))/100
            c=u.GTRoadCondition()
            for key,value in dict(name='Local mud stretch',start_metres=0.,end_metres=min(40.,length),blend_metres=4.,mud_depth_cm=a.mud_depth_cm,rut_depth_cm=0.,firmness=a.firmness,wetness=a.wetness,grass_cover=.1,water_fill_cm=0.,track_spread_cm=0.,churn=0.,crossing_tracks=0.,breakup_cm=0.).items():c.set_editor_property(key,value)
            a.modify();a.conditions=list(a.conditions)+[c]
    u.log('Local condition added with no old ruts. Set its Start/End Metres and soil controls in Details > LiDAR > Mud > Conditions.')


def serialize(a):
    if not a.design_id:a.modify();a.design_id=str(uuid.uuid4())
    points=[]
    sp=a.control_points
    for k in range(sp.get_number_of_spline_points()):
        # Reject curved points: the exported control polygon is what the prepared surface uses.
        if sp.get_spline_point_type(k)!=u.SplinePointType.LINEAR:
            raise ValueError(a.design_name+': set spline point type to Linear (curved tangents are not exported)')
        q=sp.get_location_at_spline_point(k,u.SplineCoordinateSpace.WORLD);points.append([q.x,q.y,q.z])
    row=dict(id=a.design_id,name=a.design_name,kind='river_bed' if a.kind==u.GTLidarPathKind.RIVER_BED else 'mud_track',enabled=a.enabled,points_cm=points,width_m=a.width_metres,max_cut_fill_m=a.maximum_cut_fill_metres)
    if row['kind']=='mud_track':
        # Spline scales are float32; quantize to 0.1 mm so export/load is stable.
        row['widths_m']=[round(a.width_metres*sp.get_scale_at_spline_point(k).y,4) for k in range(len(points))]
    if row['kind']=='river_bed':row.update(bank_blend_m=a.bank_blend_metres,target_depth_m=a.target_depth_metres)
    else:
        row.update(mud_depth_cm=a.mud_depth_cm,rut_depth_cm=a.rut_depth_cm,firmness=a.firmness,wetness=a.wetness,relief_strength=a.relief_strength)
        row['conditions']=[{k:c.get_editor_property(k) for k in CONDITION_KEYS} for c in a.conditions]
    return row


def inspect_selected():
    require_level();rows=[serialize(a) for a in ACTORS.get_selected_level_actors() if isinstance(a,u.GTLidarAuthoringPath)]
    if not rows:raise ValueError('Select a LiDAR design first')
    for row in rows:
        design.validate(dict(version=1,coordinate_system=design.COORDINATES,paths=[row]))
        pts=row['points_cm'];length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))/100
        grades=[abs(b[2]-a[2])/math.dist(a[:2],b[:2])*100 for a,b in zip(pts,pts[1:])]
        message=f'{row["name"]}: {length:.1f} m, width {row["width_m"]:.1f} m, maximum control grade {max(grades):.1f}%'
        if 'widths_m' in row:message+=f', local width {min(row["widths_m"]):.2f}–{max(row["widths_m"]):.2f} m'
        if row['kind']=='river_bed':
            ref=water_reference();depths=[(surface_at(p[0],p[1],ref)-p[2])/100 for p in pts]
            if min(depths)<.10 or max(depths)>1.5:raise ValueError('Bed depth must be 0.10..1.50 m at each control')
            message+=f', depth {min(depths):.2f}–{max(depths):.2f} m'
        u.log(message)


def preview_selected():
    world=require_level()
    selected=[serialize(a) for a in ACTORS.get_selected_level_actors() if isinstance(a,u.GTLidarAuthoringPath)]
    if not selected:raise ValueError('Select a LiDAR design first')
    for row in selected:
        color=u.LinearColor(.2,.8,1,1) if row['kind']=='river_bed' else u.LinearColor(.8,.45,.15,1)
        points=row['points_cm'];widths=row.get('widths_m',[row['width_m']]*len(points))
        for k,(a,b) in enumerate(zip(points,points[1:])):
            length=math.dist(a[:2],b[:2]);nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
            for side in (-1,1):
                pa=u.Vector(a[0]+nx*widths[k]*50*side,a[1]+ny*widths[k]*50*side,a[2]+10)
                pb=u.Vector(b[0]+nx*widths[k+1]*50*side,b[1]+ny*widths[k+1]*50*side,b[2]+10)
                u.SystemLibrary.draw_debug_line(world,pa,pb,color,60,3)
        for p in points:
            u.SystemLibrary.draw_debug_sphere(world,u.Vector(*p),20,8,color,60,2)
            if row['kind']=='river_bed':
                surf=surface_at(p[0],p[1]);u.SystemLibrary.draw_debug_line(world,u.Vector(*p),u.Vector(p[0],p[1],surf),u.LinearColor(0,.4,1,1),60,2)
                u.SystemLibrary.draw_debug_string(world,u.Vector(p[0],p[1],surf+30),f'{(surf-p[2])/100:.2f} m',None,u.LinearColor(1,1,1,1),60)
    inspect_selected()


def save_designs():
    require_level();rows=[serialize(a) for a in paths()]
    if not rows and design.DEFAULT.exists() and design.load(design.DEFAULT)['paths']:
        raise ValueError('No design actors are loaded, but saved designs exist. Load them first; disable a design with Enabled instead of accidentally clearing the saved file.')
    data=design.validate(dict(version=1,coordinate_system=design.COORDINATES,paths=sorted(rows,key=lambda p:p['id'])))
    ref=water_reference() if design.enabled(data,'river_bed') else None
    for p in design.enabled(data,'river_bed'):
        for x,y,z in p['points_cm']:
            if not .1<=(surface_at(x,y,ref)-z)/100<=1.5:raise ValueError(p['name']+': bed depth must be 0.10..1.50 m')
    destination=design.DEFAULT;destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        backup=ROOT/'Saved/LidarAuthoringBackups'/str(time.time_ns());backup.mkdir(parents=True)
        shutil.copy2(destination,backup/'edits.json')
    temporary=destination.with_suffix('.tmp');temporary.write_text(json.dumps(data,indent=2)+'\n');temporary.replace(destination)
    u.log(f'Saved {len(rows)} designs to {destination}. Close Unreal, then run Art/lidar_place.ps1 -Mode ApplyDesign. This applies prepare → Install → Polish → Water → Check.')


def load_designs():
    require_level();data=design.load()
    if paths():raise RuntimeError('Design actors already exist. Loading is refused to protect unsaved work; delete them deliberately before reloading.')
    with u.ScopedEditorTransaction('Load LiDAR designs'):
        for p in data['paths']:
            a=ACTORS.spawn_actor_from_class(u.GTLidarAuthoringPath,u.Vector(*p['points_cm'][0]));a.design_id=p['id'];a.design_name=p['name'];a.enabled=p['enabled']
            a.kind=u.GTLidarPathKind.RIVER_BED if p['kind']=='river_bed' else u.GTLidarPathKind.MUD_TRACK
            a.width_metres=p['width_m'];a.maximum_cut_fill_metres=p['max_cut_fill_m']
            for key,prop in [('bank_blend_m','bank_blend_metres'),('target_depth_m','target_depth_metres'),('mud_depth_cm','mud_depth_cm'),('rut_depth_cm','rut_depth_cm'),('firmness','firmness'),('wetness','wetness')]:
                if key in p:a.set_editor_property(prop,p[key])
            if p['kind']=='mud_track':
                a.relief_strength=p.get('relief_strength',0);conditions=[]
                for row in p.get('conditions',[]):
                    c=u.GTRoadCondition()
                    for key,value in row.items():c.set_editor_property(key,value)
                    conditions.append(c)
                a.conditions=conditions
            a.set_actor_label(p['name']);a.set_folder_path('LiDAR Designs');set_points(a,p['points_cm'])
            for k,width in enumerate(p.get('widths_m',[])):
                a.control_points.set_scale_at_spline_point(k,u.Vector(1,width/a.width_metres,1),False)
            a.control_points.update_spline()


def register_menu():
    menus=u.ToolMenus.get();parent=menus.extend_menu('LevelEditor.MainMenu.Tools')
    menu=parent.add_sub_menu('LidarPlace','Tools','LiDARPlace','LiDAR Place','Design the mud track and river bed')
    for key,label,fn in [('Track','New mud track here','new_track'),('Bed','New river bed near camera','new_bed'),('Ground','Snap selected track to ground','fit_track'),('Condition','Add local mud condition','add_condition'),('Depth','Fit selected bed to target depth','fit_bed'),('Preview','Preview selected width and depth','preview_selected'),('Inspect','Inspect selected profile','inspect_selected'),('Save','Save all designs','save_designs'),('Load','Load saved designs','load_designs')]:
        entry=u.ToolMenuEntry(name='Lidar'+key,type=u.MultiBlockType.MENU_ENTRY);entry.set_label(label)
        entry.set_string_command(u.ToolMenuStringCommandType.PYTHON,'',f'import lidar_authoring_editor; lidar_authoring_editor.{fn}()')
        menu.add_menu_entry('Design',entry)
    menus.refresh_all_widgets()


CONDITION_KEYS=('name','start_metres','end_metres','blend_metres','mud_depth_cm','rut_depth_cm','wetness','firmness','grass_cover','water_fill_cm','basin_depth_cm','track_spread_cm','churn','crossing_tracks','breakup_cm')
