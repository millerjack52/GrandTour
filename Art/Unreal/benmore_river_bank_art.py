"""River-owned bank dressing seated on the exact exported surface triangles."""
import unreal as u, json, array, math, hashlib
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Rivers'

def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o

def apply_art(world):
    from benmore_river_material import bank_material,terrain_material
    from benmore_painterly_surface import NOISE
    data=json.loads((OUT/'bank-art-placements.json').read_text())
    assert data['ok'] and hashlib.sha256((OUT/'river_bake.npz').read_bytes()).hexdigest()==data['bake_sha256']
    act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary
    mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
    base=array.array('f');base.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
    bank=array.array('f');bank.frombytes((OUT/'bank_surface.f32').read_bytes())
    shore=array.array('f');shore.frombytes((OUT/'bank_distance.f32').read_bytes())
    def triangle(grid,n,x,y):
        i=int(x);j=int(y);a=x-i;b=y-j;k=j*n+i;q,r,s,t=grid[k],grid[k+1],grid[k+n],grid[k+n+1]
        return q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b
    def ground(x,y):return max(triangle(base,2017,(x+1250)/2500*2016,(y+1250)/2500*2016),triangle(bank,1331,x+1570,y+20))
    task=props(u.AssetImportTask(),filename=str(OUT/'T_Benmore_RiverBankArt.png'),destination_path=DEST,destination_name='T_Benmore_RiverBankArt',automated=True,replace_existing=True,save=True)
    assets.import_asset_tasks([task]);tex=u.load_asset(DEST+'/T_Benmore_RiverBankArt');assert tex
    props(tex,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True);assert eal.save_loaded_asset(tex)
    banks=u.load_asset(DEST+'/T_Benmore_RiverBanks');mat=bank_material(banks);terrain=terrain_material(banks,u.load_asset(DEST+'/T_Benmore_VegetationMask'))
    for a in act.get_all_level_actors():
        if a.get_actor_label().startswith('Benmore_River_Art_'):act.destroy_actor(a)
        elif a.get_actor_label().startswith('Benmore_River_Bank_'):a.static_mesh_component.set_material(0,mat)
        elif isinstance(a,u.LandscapeProxy):a.set_editor_property('landscape_material',terrain)
    # Reuse the rock shapes without changing their shared materials. A local
    # mineral treatment unifies the exposed fragments with the bank surface.
    name='M_Benmore_RiverSchist';rockmat=u.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    for old in list(mel.get_material_expressions(rockmat)):mel.delete_material_expression(rockmat,old)
    mel.set_base_material_usage(rockmat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    col=props(mel.create_material_expression(rockmat,u.MaterialExpressionCustom),inputs=[props(u.CustomInput(),input_name=n) for n in ['P','N']],output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code=NOISE+'''
float vein=f.n(float2((q.x*.78+q.y*.22)/2.2,(P.z*.01+q.x*.14)/.18));
float3 rock=lerp(float3(.105,.126,.135),float3(.257,.250,.213),field);
rock*=1+(smoothstep(.25,.75,vein)-.5)*.20;
return lerp(rock,rock*float3(1.10,1.03,.83),smoothstep(.55,.95,N.z)*.30);
''')
    for cls,pin in [(u.MaterialExpressionWorldPosition,'P'),(u.MaterialExpressionVertexNormalWS,'N')]:assert mel.connect_material_expressions(mel.create_material_expression(rockmat,cls),'',col,pin)
    mel.connect_material_property(col,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,val in [(u.MaterialProperty.MP_ROUGHNESS,.91),(u.MaterialProperty.MP_SPECULAR,.12)]:mel.connect_material_property(props(mel.create_material_expression(rockmat,u.MaterialExpressionConstant),r=val),'',prop)
    assert not mel.recompile_material(rockmat);assert eal.save_loaded_asset(rockmat)
    groups={
        'tussocks':[u.load_asset('/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'+s) for s in ['Straw','Rust']],
        'shrubs':[u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Composition/SM_Composition_Scrub_'+s) for s in ['Open','Dense']],
        'rocks':[u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Benmore_Rock'+str(k)) for k in [1,2,3]],
        'trees':[u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_Young')]
    }
    samples=[];counts={};gaps=[];footprint_clearances=[]
    for category,meshes in groups.items():
        group=act.spawn_actor_from_class(u.Actor,u.Vector());group.set_actor_label('Benmore_River_Art_'+category);counts[category]=0
        root=group.get_editor_property('root_component')
        if root:root.set_mobility(u.ComponentMobility.STATIC)
        for kind,mesh in enumerate(meshes):
            assert mesh,(category,kind);b=mesh.get_bounds();transforms=[]
            pts=[]
            if category=='rocks':
                desc=mesh.get_static_mesh_description(0);pts=[desc.get_vertex_position(u.VertexID(i)) for i in range(desc.get_vertex_count())]
                pts=[p for p in pts if p.z<=b.origin.z-b.box_extent.z+b.box_extent.z*.30];assert pts
            for row in data['placements'][category]:
                if row['kind']!=(kind+1 if category=='rocks' else kind):continue
                x,y=row['x'],row['y'];angle=math.radians(row['yaw']);cs=math.cos(angle);sn=math.sin(angle)
                s=row['size_m']*100/(2*max(b.box_extent.x,b.box_extent.y) if category=='rocks' else 2*b.box_extent.z)
                zs=s*row['height_ratio'] if category=='rocks' else s
                if category=='rocks':
                    constraints=[]
                    for p in pts:
                        px=x+(p.x*cs-p.y*sn)*s/100;py=y+(p.x*sn+p.y*cs)*s/100
                        constraints.append((ground(px,py)-p.z*zs/100,px,py,p.z*zs/100))
                    limit,px,py,offset=min(constraints);z=limit-.075
                    gaps.extend(z-v[0] for v in constraints);samples.append([px,py,z+offset])
                    # Check the complete transformed XY AABB against wet cells.
                    for px in [b.origin.x-b.box_extent.x,b.origin.x+b.box_extent.x]:
                        for py in [b.origin.y-b.box_extent.y,b.origin.y+b.box_extent.y]:
                            qx=x+(px*cs-py*sn)*s/100;qy=y+(px*sn+py*cs)*s/100
                            footprint_clearances.append(triangle(shore,1331,qx+1570,qy+20))
                else:
                    # Small plant root contact. The trunks have their own hulls;
                    # no canopy or water-volume collision is introduced.
                    base_z=(b.origin.z-b.box_extent.z)*zs/100;z=ground(x,y)-base_z-.07
                    if counts[category]%61==0 or category=='trees':samples.append([x,y,z+base_z])
                transforms.append(u.Transform(u.Vector(x*100,y*100,z*100),u.Rotator(yaw=row['yaw']),u.Vector(s,s,zs)));counts[category]+=1
            if not transforms:continue
            collidable=category in ['rocks','trees'];cast=category!='tussocks'
            c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'BenmoreRiverArt','BlockAll' if collidable else 'NoCollision',cast)
            if category=='rocks':c.set_material(0,rockmat)
            if category=='tussocks':c.set_material(0,u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Painterly/M_Painterly_Tussock'))
            c.set_cull_distances(*({'tussocks':(52000,85000),'shrubs':(100000,170000),'rocks':(160000,220000),'trees':(180000,240000)}[category]))
            props(c,affect_distance_field_lighting=False,visible_in_ray_tracing=False,receives_decals=False)
    assert counts==data['counts'];assert max(gaps)<-.07 and min(footprint_clearances)>.25
    if (OUT/'mouth-assets.json').exists():
        from benmore_river_mouth import apply_mouth
        apply_mouth(world)
    report=dict(ok=True,counts=counts,rock_basal_max_gap_m=max(gaps),minimum_rock_AABB_wet_clearance_m=min(footprint_clearances),support_samples_m=samples,
        bake_sha256=data['bake_sha256'],bed_changed=False,flow_changed=False)
    (OUT/'bank-art-install.json').write_text(json.dumps(report,indent=2));return report

def check_support(world,report):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    ignore=[a for a in actors if not isinstance(a,u.LandscapeProxy) and not a.get_actor_label().startswith('Benmore_River_Bank_')]
    measured=[]
    for x,y,z in report['support_samples_m']:
        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,z*100+500),u.Vector(x*100,y*100,z*100-500),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit is not None
        surface=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z/100;measured.append(z-surface)
    assert max(measured)<-.045,(max(measured),min(measured))
    result={k:v for k,v in report.items() if k!='support_samples_m'}
    result.update(native_support_samples=len(measured),native_max_gap_m=max(measured),native_min_gap_m=min(measured))
    if (OUT/'mouth-assets.json').exists():
        from benmore_river_mouth import check_mouth
        result['mouth']=check_mouth(world)
    (OUT/'bank-art-validation.json').write_text(json.dumps(result,indent=2));return result
