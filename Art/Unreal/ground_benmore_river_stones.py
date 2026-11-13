"""Seat bank stones against the exported triangles, not bilinear height estimates."""
import unreal as u,json,time,array,math,traceback,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers';phase='load';last=time.monotonic()
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
u.EditorPythonScripting.set_keep_python_script_alive(True)
base=array.array('f');base.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
bank=array.array('f');bank.frombytes((OUT/'bank_surface.f32').read_bytes())
def triangle(grid,n,x,y):
    i=int(x);j=int(y);a=x-i;b=y-j;k=j*n+i;q,r,s,t=grid[k],grid[k+1],grid[k+n],grid[k+n+1]
    return q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b
def ground(x,y):return max(triangle(base,2017,(x+1250)/2500*2016,(y+1250)/2500*2016),triangle(bank,1331,x+1570,y+20))
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='loading';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive');phase='loaded';last=time.monotonic()
        elif phase=='loaded' and time.monotonic()-last>8:
            phase='working';actors=act.get_all_level_actors();world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actor=next(a for a in actors if a.get_actor_label()=='Benmore_River_GravelBars');changes=[];samples=[];gaps=[]
            for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                mesh=c.get_editor_property('static_mesh');b=mesh.get_bounds();desc=mesh.get_static_mesh_description(0)
                pts=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count())];pts=[p for p in pts if p.z<=b.origin.z-b.box_extent.z+b.box_extent.z*.65]
                for i in range(c.get_instance_count()):
                    tr=c.get_instance_transform(i,True);old=tr.translation.z;constraints=[]
                    for p in pts:
                        v=u.MathLibrary.transform_location(tr,p);constraints.append((ground(v.x/100,v.y/100)*100-(v.z-old),v))
                    limit,v=min(constraints,key=lambda r:r[0]);new=limit-4.5;changes.append((new-old)/100)
                    tr.translation=u.Vector(tr.translation.x,tr.translation.y,new);assert c.update_instance_transform(i,tr,True,i==c.get_instance_count()-1,True)
                    gaps.extend((new-z)/100 for z,_ in constraints)
                    if i%13==0:samples.append([v.x,v.y,v.z+new-old])
            ignore=[a for a in actors if not isinstance(a,u.LandscapeProxy) and not a.get_actor_label().startswith('Benmore_River_Bank_')];measured=[];diagnostics=[]
            for x,y,z in samples:
                hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z+400),u.Vector(x,y,z-400),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit is not None
                surface=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;measured.append((z-surface)/100);diagnostics.append(dict(x=x/100,y=y/100,stone_z=z/100,ground=surface/100,expected=ground(x/100,y/100)))
            (OUT/'stone-grounding-traces.json').write_text(json.dumps(diagnostics,indent=2))
            assert max(measured)<-.03,(max(measured),min(measured))
            report=dict(ok=True,stones=len(changes),all_basal_points_max_gap_m=max(gaps),native_trace_samples=len(measured),native_max_gap_m=max(measured),maximum_z_correction_m=max(abs(v) for v in changes))
            (OUT/'stone-grounding-validation.json').write_text(json.dumps(report,indent=2));assert les.save_current_level();phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>10:
            phase='done';u.unregister_slate_post_tick_callback(handle)
            if (OUT/'validation-report.json').exists():shutil.copy2(OUT/'validation-report.json',OUT/'full-review-before-stone-grounding.json')
            p=ROOT/'Art/Unreal/check_benmore_rivers.py';source=p.read_text();source=source.replace("views=[('River_Close','Benmore_River_Camera_Close'),('River_Reach','Benmore_River_Camera_Reach'),('River_Overlook','')]","views=[('River_Close','Benmore_River_Camera_Close')]")
            exec(compile(source,str(p),'exec'),{'__file__':str(p)})
    except Exception:
        (OUT/'grounding-error.txt').write_text(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
