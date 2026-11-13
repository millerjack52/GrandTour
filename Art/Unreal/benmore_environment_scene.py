"""Background, atmospheric depth and terrain-supported rock placement."""
import unreal as u,json,math,array
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment';DEST='/Game/GrandTour/Demo/BenmoreRoads/Environment'
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o

def setup_background(world):
    from benmore_bank_surface import backdrop_material
    material=backdrop_material();act=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.AssetToolsHelpers.get_asset_tools();eal=u.EditorAssetLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for a in act.get_all_level_actors():
        if a.get_actor_label().startswith('Benmore_Backdrop_') or a.get_actor_label()=='Benmore_DistanceHaze':act.destroy_actor(a)
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    result=[]
    for part in json.loads((OUT/'backdrop.json').read_text())['parts']:
        name=part['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
        opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
        props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
        mesh.set_material(0,material);ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;sm.set_nanite_settings(mesh,ns,True);eal.save_loaded_asset(mesh)
        a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(name.replace('SM_',''));c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('NoCollision');props(c,cast_shadow=True,receives_decals=False);a.set_actor_location(u.Vector(0,0,0),False,True);a.set_actor_rotation(u.Rotator(0,0,0),False)
        b=mesh.get_bounds();assert b.box_extent.x>30000 and b.box_extent.y>30000,(name,str(b))
        result.append({'mesh':name,'nanite':True,'collision':'NoCollision','bounds_cm':str(b)})
    fog=act.spawn_actor_from_class(u.ExponentialHeightFog,u.Vector());fog.set_actor_label('Benmore_DistanceHaze')
    fog.set_actor_location(u.Vector(0,0,0),False,True)
    props(fog.component,fog_density=.007,fog_height_falloff=.10,start_distance=28000.,fog_max_opacity=.72,fog_inscattering_luminance=u.LinearColor(.31,.39,.51,1))
    # Lift pitch-black cavities slightly while keeping the sun/colour direction.
    for a in act.get_all_level_actors():
        if isinstance(a,u.SkyLight) and a.get_actor_label()=='Sky':a.light_component.set_intensity(.9)
    return result

def terrain_trace(world,ignore,x,y):
    h=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,100000),u.Vector(x*100,y*100,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
    assert h is not None,('Terrain miss',x,y)
    return [v for v in h.to_tuple() if isinstance(v,u.Vector)][0].z/100

def ground_large_rocks(world):
    act=u.get_editor_subsystem(u.EditorActorSubsystem);allactors=act.get_all_level_actors();ignore=[a for a in allactors if not isinstance(a,u.LandscapeProxy)]
    samples=json.loads((OUT/'rock-undersides.json').read_text());result=[]
    original=json.loads((ROOT/'Art/Export/BenmoreScenery/placements.json').read_text())['rocks']
    for a in allactors:
        if not a.get_actor_label().startswith('Benmore_Scenery_rocks_'):continue
        mesh=a.static_mesh_component.get_editor_property('static_mesh');kind=mesh.get_name()[-1];pts=samples[kind];p=a.get_actor_location();scale=a.get_actor_scale3d().x
        yaw=math.radians(original[int(a.get_actor_label().split('_')[-1])]['yaw']);cs=math.cos(yaw);sn=math.sin(yaw)
        bounds=mesh.get_bounds();bottom=(bounds.origin.z-bounds.box_extent.z)/100;cut=bottom+bounds.box_extent.z*2/100*.32
        pts=[v for v in pts if v[2]<=cut];assert len(pts)>=6
        gx=(terrain_trace(world,ignore,p.x/100+.8,p.y/100)-terrain_trace(world,ignore,p.x/100-.8,p.y/100))/1.6
        gy=(terrain_trace(world,ignore,p.x/100,p.y/100+.8)-terrain_trace(world,ignore,p.x/100,p.y/100-.8))/1.6
        rotation=u.MathLibrary.make_rot_from_xz(u.Vector(cs,sn,cs*gx+sn*gy),u.Vector(-gx,-gy,1))
        transform=u.Transform(u.Vector(p.x,p.y,0),rotation,u.Vector(scale,scale,scale))
        constraints=[]
        for x,y,z in pts:
            point=u.MathLibrary.transform_location(transform,u.Vector(x*100,y*100,z*100));terrain=terrain_trace(world,ignore,point.x/100,point.y/100)
            constraints.append(terrain-point.z/100)
        # Support the basal footprint. Higher overhangs are not ground contacts.
        z=min(constraints)-.065;oldz=p.z/100;a.set_actor_location_and_rotation(u.Vector(p.x,p.y,z*100),rotation,False,True)
        gaps=[z-c for c in constraints];assert max(gaps)<0
        result.append({'actor':a.get_actor_label(),'kind':kind,'samples':len(gaps),'support_region':'lower 32 percent of mesh height','rotation':str(rotation),'z_change_m':z-oldz,'max_underside_gap_m':max(gaps),'xyz_m':[p.x/100,p.y/100,z]})
    assert len(result)==201;return result

def ground_aggregate(world):
    act=u.get_editor_subsystem(u.EditorActorSubsystem);actors=act.get_all_level_actors();ignore=[a for a in actors if not isinstance(a,u.LandscapeProxy)]
    grid=array.array('f');grid.frombytes((OUT/'height_local_south_up.f32').read_bytes())
    def height(x,y,diagonal=0):
        fx=max(0,min(2015.99999,(x+1250)/2500*2016));fy=max(0,min(2015.99999,(y+1250)/2500*2016));i=int(fx);j=int(fy);x=fx-i;y=fy-j;k=j*2017+i
        a,b,c,d=grid[k],grid[k+1],grid[k+2017],grid[k+2018]
        if diagonal==0:return a+(b-a)*x+(d-b)*y if x>=y else a+(d-c)*x+(c-a)*y
        return a+(b-a)*x+(c-a)*y if x+y<=1 else d+(c-d)*(1-x)+(b-d)*(1-y)
    errors=[[],[]]
    for j in range(30):
        x=-900+j*51.31;y=-810+j*42.73;z=terrain_trace(world,ignore,x,y)
        for d in range(2):errors[d].append(abs(height(x,y,d)-z))
    diagonal=min(range(2),key=lambda d:sum(errors[d]));assert max(errors[diagonal])<.03,errors
    moved=0;stones=0;growth_tag='BenmoreEnvironmentSized'
    for a in actors:
        if a.get_actor_label() not in ['Benmore_RoadVergeDetail','Benmore_ReferenceRoadAggregate']:continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh');bounds=mesh.get_bounds();isstone=mesh.get_name().startswith('SM_GR_Stone');tags=list(c.get_editor_property('component_tags'));grow=isstone and growth_tag not in [str(t) for t in tags]
            if isstone and a.get_actor_label()=='Benmore_RoadVergeDetail':props(c,cast_shadow=True,cast_contact_shadow=True)
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);p=t.translation;s=t.scale3d
                if grow:s=u.Vector(s.x*1.35,s.y*1.35,s.z*1.45);t.scale3d=s
                if isstone:
                    radius=max(bounds.box_extent.x*s.x,bounds.box_extent.y*s.y)/100*.65
                    ground=min(height(p.x/100+dx,p.y/100+dy,diagonal) for dx,dy in [(0,0),(radius,0),(-radius,0),(0,radius),(0,-radius)])
                    z=ground*100-(bounds.origin.z-bounds.box_extent.z)*s.z-1.2;stones+=1
                else:z=height(p.x/100,p.y/100,diagonal)*100-2.5
                t.translation=u.Vector(p.x,p.y,z);assert c.update_instance_transform(i,t,True,i==c.get_instance_count()-1,True);moved+=1
            if grow:tags.append(u.Name(growth_tag));c.set_editor_property('component_tags',tags)
    return {'instances':moved,'stones':stones,'diagonal':diagonal,'terrain_interpolation_check_max_error_m':max(errors[diagonal]),'stone_width_multiplier':1.35}

