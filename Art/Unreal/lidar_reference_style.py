"""RS1: coordinated LiDAR colour and a bounded, deterministic access-verge study.

Uses existing native meshes. Never rebuilds terrain or changes physical surfaces.
Run through Art/lidar_reference_style.ps1; reapply after the normal Polish stage.
"""
import json, math, random, time, traceback, shutil, gc, os, sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(u.Paths.project_dir()).resolve()/'Art/Unreal'))
from benmore_river_life_materials import Graph, props
from lidar_grounding import GroundSampler

ROOT=Path(u.Paths.project_dir()).resolve()
BASE='/Game/GrandTour/ArtTests/LidarStudy'
KIT='/Game/GrandTour/Environment/NativePlants/v01'
OUT=ROOT/'Art/Export/LidarStudy/Place'
QA=ROOT/'Saved/LidarAuthoringQA/RS1'
VERSION='rs1-2'
PREFIX='LidarStudy_RS1_'
mel=u.MaterialEditingLibrary
assets=u.EditorAssetLibrary
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
les=u.get_editor_subsystem(u.LevelEditorSubsystem)

# The same continuous field colours near blades, far patches and terrain.
# Linear albedo. Variation is grouped at plant-bed scale, never per-pixel RGB noise.
PALETTE='''
struct RSField {
float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
}; RSField rsn;
float rsField=.70*rsn.n(P.xy*.00055)+.30*rsn.n(P.xy*.0017+float2(13,7));
float rsWarm=smoothstep(.58,.92,rsField);
float rsCool=1-smoothstep(.18,.48,rsField);
float3 rsColour=lerp(float3(.105,.255,.060),float3(.060,.190,.115),rsCool*.65);
rsColour=lerp(rsColour,float3(.285,.295,.105),rsWarm*.72);
'''

def custom(mat,tag):
    hits=[n for n in mel.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))==tag]
    assert len(hits)==1,(mat.get_name(),tag,len(hits))
    return hits[0]

def persist(mat):
    assert not mel.recompile_material(mat),mat.get_name()
    assert assets.save_loaded_asset(mat,False),mat.get_name()

def grass_palette():
    import lidar_grass_gs3 as gs
    near=u.load_asset(gs.DEST+'/M_GS3_Near');far=u.load_asset(gs.DEST+'/M_GS3_Far')
    verge=u.load_asset(gs.DEST+'/M_GS3_Verge')
    assert near and far and verge
    custom(near,'GS1Style').set_editor_property('code',PALETTE+'''
float lightness=dot(Parameters.VertexColor.rgb,float3(.2126,.7152,.0722))/.184;
float3 col=rsColour*lightness;
Normal=normalize(lerp(normalize(VN),float3(0,0,1),.78));
Sub=col*.22;Emissive=float3(0,0,0);return col;
''')
    for mat,is_verge in [(far,False),(verge,True)]:
        nodes=[n for n in mel.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and tuple(str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs'))==('P','C')]
        assert len(nodes)==1,mat.get_name()
        code=PALETTE+'float lum=dot(C,float3(.2126,.7152,.0722))/.184;'
        if is_verge:code+='rsColour=lerp(rsColour,float3(.32,.30,.13),.38);'
        nodes[0].set_editor_property('code',code+'return rsColour*lum;')
        persist(mat)
    persist(near)
    ground=gs.GROUND_CODE.replace('// Existing tile texture',PALETTE+'\n// Existing tile texture')
    old='float3 green=float3(.15,.20,.078)*detail*textureVariation*lerp(.92,1.06,field);'
    assert old in ground
    ground=ground.replace(old,'float3 green=rsColour*detail*textureVariation;')
    for name in ('Terrain','Detail'):
        m=u.load_asset(BASE+'/M_'+name)
        custom(m,'GP2cPasture').set_editor_property('code',ground);persist(m)
    return dict(shared_palette=True,near_far_ground_matched=True,streaming_and_contact_unchanged=True)

def wrap_colour(mat,tag,code):
    hits=[n for n in mel.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))==tag]
    assert len(hits)<=1
    if hits:
        hits[0].set_editor_property('code',code)
    else:
        g=Graph(mat,tag)
        old=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
        output=mel.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR)
        n=g.custom(['Base','P','Rand'],code)
        g.wire(old,n,'Base',output)
        g.wire(g.node(u.MaterialExpressionWorldPosition),n,'P')
        g.wire(g.node(u.MaterialExpressionPerInstanceRandom),n,'Rand')
        g.output(n,u.MaterialProperty.MP_BASE_COLOR)
    persist(mat)

def foliage_palette():
    # Authored beech/fern shapes and bark are retained. Lift and cool leaf pigment.
    leaf=u.load_asset(BASE+'/M_LP6_Foliage');assert leaf
    code='''float patch=.5+.5*sin(P.x*.00043+P.y*.00031);
float3 cool=float3(.84,1.04,1.17),warm=float3(1.08,1.04,.85);
return Base*lerp(cool,warm,smoothstep(.35,.8,patch)) * lerp(.94,1.08,Rand);'''
    wrap_colour(leaf,'RS1LeafColour',code)
    for n in mel.get_material_expressions(leaf):
        if isinstance(n,u.MaterialExpressionCustom) and 'float3 radial=' in str(n.get_editor_property('code')):
            n.set_editor_property('code','float3 radial=normalize(float3((P.xy-Centre.xy)*.012,.65));return normalize(lerp(N,radial,.32));')
    persist(leaf)
    for name,tint in [('MI_NZ_Foliage_Canopy',(.74,.94,.84)),('MI_NZ_Foliage_Bush',(.76,.94,.72))]:
        mi=u.load_asset(BASE+'/'+name);assert mi
        mel.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*tint,1))
        mel.update_material_instance(mi);assert assets.save_loaded_asset(mi,False)
    import lidar_canopy_assets as canopy
    from forest_shaders import connected_nodes
    for k in range(3):
        canopy.tint_far_card(k,(.74,.94,.84))
        far=u.load_asset(BASE+'/CanopyKit/M_FirFar_'+str(k))
        # The distance shader already includes this palette. Repeated Polish
        # passes must not compound its tint or warm/cool variation.
        if not any(str(n.get_editor_property('desc'))=='ForestShaderTint' for n in connected_nodes(far)):
            wrap_colour(far,'RS1LeafColour',code)
    return dict(canopy_tint=[.74,.94,.84],understory_tint=[.76,.94,.72])

def inside(x,y,poly):
    hit=False
    for (ax,ay),(bx,by) in zip(poly,poly[1:]+poly[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:hit=not hit
    return hit

def segdist(x,y,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
    return math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)

def dressing(author):
    # Bounded first study: 160 m of the existing access route, outside pasture.
    roads=json.loads((OUT/'roads.json').read_text())
    points=next(r['points'] for r in roads if r['name']=='Riverside access')
    anchor=(-45504.85,27841.17)
    segments=[(a,b) for r in roads for a,b in zip(r['points'],r['points'][1:])
              if min(math.dist(a,anchor),math.dist(b,anchor))<22000]
    polygons=[p['polygon_cm'] for p in json.loads((OUT/'prepare.json').read_text())['paddocks']['polygons']]
    ground=GroundSampler(author);rng=random.Random(20261105)
    species=['SM_NZ_Coprosma_A','SM_NZ_Coprosma_B','SM_NZ_Gorse_A','SM_NZ_Broom_A','SM_NZ_VergeTussock_A','SM_NZ_VergeTussock_B','SM_NZ_Thistle_A']
    meshes={n:u.load_asset(KIT+'/'+n) for n in species};assert all(meshes.values())
    groups={};rejected=0
    # Each island has a woody middle and a low, looser skirt. Alternate sides;
    # leave gaps between islands and retain an unobstructed road corridor.
    for j,(a,b) in enumerate(zip(points,points[1:])):
        if j%3 or math.dist(a,anchor)>16000 or a[1]>anchor[1]+500:continue
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
        if length<1:continue
        nx=-dy/length;ny=dx/length
        side=1 if j%2 else -1
        offset=rng.uniform(360,510)
        cx=a[0]+nx*side*offset;cy=a[1]+ny*side*offset
        for i in range(15):
            angle=rng.random()*math.tau;rad=math.sqrt(rng.random())*(170 if i<4 else 340)
            x=cx+math.cos(angle)*rad;y=cy+math.sin(angle)*rad
            if min(segdist(x,y,p,q) for p,q in segments)<240 or any(inside(x,y,p) for p in polygons):rejected+=1;continue
            z=ground.height(x,y)
            slope=max(abs(ground.height(x+80,y)-ground.height(x-80,y)),abs(ground.height(x,y+80)-ground.height(x,y-80)))/160
            if slope>.65:rejected+=1;continue
            name=species[(j//3)%4] if i<4 else species[4+(i%3)]
            height=rng.uniform(70,130) if i<4 else rng.uniform(35,65)
            mesh=meshes[name];scale=height/(2*mesh.get_bounds().box_extent.z)
            tf=u.Transform(location=u.Vector(x,y,z-3),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(scale,scale,scale*rng.uniform(.9,1.1)))
            groups.setdefault(name,[]).append(tf)
    assert 60<=sum(map(len,groups.values()))<=600,[(n,len(v)) for n,v in groups.items()]
    for a in list(actors.get_all_level_actors()):
        if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
    result=[]
    for name,tfs in groups.items():
        a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+name);a.tags=['LidarReferenceStyle',VERSION]
        c=u.GTVegetationSubsystem.add_tagged_instances(a,meshes[name],tfs,'LidarReferenceStyle','NoCollision',False)
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cull_distances(10000,16000)
        props(c,cast_shadow=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),cast_shadow_as_two_sided=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),visible_in_ray_tracing=False,affect_distance_field_lighting=False)
        for i,slot in enumerate(meshes[name].get_editor_property('static_materials')):
            m=slot.get_editor_property('material_interface')
            if m and m.get_name()=='M_NZ_Foliage':c.set_material(i,u.load_asset(BASE+'/MI_NZ_Foliage_Bush'))
        result.append(dict(mesh=name,instances=len(tfs)))
    return dict(groups=result,total=sum(len(v) for v in groups.values()),rejected=rejected,minimum_road_clearance_cm=240,pastures_excluded=True)

def snapshot():
    refs=actors.get_all_level_actors()
    author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
    grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
    return dict(ground_digest=str(author.output_digest),
        foliage={a.get_actor_label()+'/'+c.get_name():c.get_instance_count() for a in refs if a.get_actor_label() in ('LidarStudy_Forest','LidarStudy_Understory') for c in a.get_components_by_class(u.InstancedStaticMeshComponent)},
        grass={k:float(grass.get_editor_property(k)) for k in ('clump_spacing_cm','clump_stream_radius_cm','grass_cull_start_cm','grass_cull_end_cm','distant_pasture_end_cm')})

def apply():
    before=snapshot()
    result=dict(version=VERSION,grass=grass_palette(),foliage=foliage_palette())
    refs=actors.get_all_level_actors();author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
    result['dressing']=dressing(author)
    result['lighting']=[]
    for a in refs:
        if isinstance(a,u.SkyLight):
            c=a.get_component_by_class(u.SkyLightComponent)
            old=float(c.get_editor_property('intensity'));c.set_intensity(2.0)
            result['lighting'].append(dict(actor=a.get_actor_label(),before=old,after=2.0))
    assert before==snapshot(),'Terrain, original plants or grass streaming changed'
    result['preserved']=before
    if (OUT/'road-style.json').exists():
        import lidar_road_style
        result['road_style']=lidar_road_style.apply()
    if (OUT/'river-plant-variety.json').exists():
        import lidar_river_plant_variety
        result['river_plant_variety']=lidar_river_plant_variety.apply()
        # RS3 deliberately replaces selected original low plants in its reach.
        # The reload check must compare against that final, authorised inventory.
        result['preserved']=snapshot()
    if (OUT/'slope-style.json').exists():
        import lidar_slope_style
        result['slope_style']=lidar_slope_style.apply()
    return result

def backup():
    dest=ROOT/'Saved/LidarAuthoringBackups'/('RS1-'+str(time.time_ns()));dest.mkdir(parents=True)
    content=ROOT/'Content/GrandTour/ArtTests/LidarStudy'
    for name in ('L_LidarStudy.umap','M_Terrain.uasset','M_Detail.uasset','M_LP6_Foliage.uasset','MI_NZ_Foliage_Canopy.uasset','MI_NZ_Foliage_Bush.uasset'):
        shutil.copy2(content/name,dest/name)
    for folder in ('CanopyKit','GrassGS3'):shutil.copytree(content/folder,dest/folder)
    return str(dest)

if __name__=='__main__':
    QA.mkdir(parents=True,exist_ok=True)
    report=dict(ok=False);busy=False;deadline=0
    def save():(QA/'install.json').write_text(json.dumps(report,indent=2))
    def run():
        report['backup']=backup();save()
        assert les.load_level(BASE+'/L_LidarStudy');yield 2
        report.update(apply());save();yield 8
        assert les.save_current_level();report['saved']=True;save()
        # Discard Python UObject references before unloading the large map.
        gc.collect();assert les.load_level('/Engine/Maps/Entry');yield 3
        assert les.load_level(BASE+'/L_LidarStudy');yield 2
        assert snapshot()==report['preserved'],'Saved map differs from pre-edit invariants'
        rows=[c.get_instance_count() for a in actors.get_all_level_actors() if a.get_actor_label().startswith(PREFIX) for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
        assert sum(rows)==report['dressing']['total']
        report.update(ok=True,reloaded=True,owner_accepted=False);save()
        (OUT/'reference-style.json').write_text(json.dumps(dict(version=VERSION,enabled=True,report=str(QA/'install.json')),indent=2))
        gc.collect();les.load_level('/Engine/Maps/Entry');yield 4
    steps=run()
    def tick(dt):
        global busy,deadline,steps
        if busy:return
        busy=True
        try:
            if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
        except StopIteration:
            u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
        except Exception:
            report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
            u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        finally:busy=False
    u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
