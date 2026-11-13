"""Actual RS7 bank/placement asset study. CPU preview; no live game mutations.

Habitat masks, material previews and fitted detail exports stay in ForestFloorRevision.
The new fern envelopes require Unreal clearance/contact validation before install.
"""
import bpy,sys,math,json,random,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('C:/GrandTour');HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(ROOT/'Art/Unreal')]
import native_plant_lib as L
import lidar_section_surface as S
BASE=ROOT/'Art/Export/LidarStudy/FirstSection'
OUT=BASE/'ForestFloorRevision';OUT.mkdir(parents=True,exist_ok=True)


def smooth(a,b,v):
    t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)


def material(name,lo,hi,scale,rough=.85,bump=.015):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=rough;p.inputs['Specular IOR Level'].default_value=.23
    coord=n.new('ShaderNodeTexCoord')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=2
    l.new(coord.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(*lo,1)
    ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(*hi,1)
    l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color'])
    micro=n.new('ShaderNodeTexNoise');micro.inputs['Scale'].default_value=scale*9;micro.inputs['Detail'].default_value=1
    l.new(coord.outputs['Object'],micro.inputs['Vector'])
    normal=n.new('ShaderNodeBump');normal.inputs['Strength'].default_value=.28;normal.inputs['Distance'].default_value=bump
    l.new(micro.outputs['Fac'],normal.inputs['Height']);l.new(normal.outputs[0],p.inputs['Normal'])
    return m


def ground_material():
    m=material('M_Study_HabitatGround',(.045,.034,.022),(.10,.071,.038),3,.87,.012)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    soil=next(node for node in n if node.type=='VALTORGB')
    attr=n.new('ShaderNodeVertexColor');attr.layer_name='Habitat'
    split=n.new('ShaderNodeSeparateColor');l.new(attr.outputs['Color'],split.inputs[0])
    def colour_mix(a,b,factor):
        node=n.new('ShaderNodeMixRGB');node.blend_type='MIX'
        if isinstance(a,tuple):node.inputs[1].default_value=(*a,1)
        else:l.new(a,node.inputs[1])
        if isinstance(b,tuple):node.inputs[2].default_value=(*b,1)
        else:l.new(b,node.inputs[2])
        l.new(factor,node.inputs[0]);return node.outputs[0]
    coord=next(node for node in n if node.type=='TEX_COORD')
    soil_tex=n.new('ShaderNodeTexImage')
    soil_tex.image=bpy.data.images.load(str(ROOT/'Art/Export/GroundDetailGR2/T_GD_SoilUnderGrassColor.png'),check_existing=True)
    soil_tex.projection='BOX';soil_tex.projection_blend=.3
    soil_scale=n.new('ShaderNodeVectorMath');soil_scale.operation='SCALE';soil_scale.inputs['Scale'].default_value=.5
    l.new(coord.outputs['Object'],soil_scale.inputs[0]);l.new(soil_scale.outputs[0],soil_tex.inputs['Vector'])
    soil_detail=n.new('ShaderNodeMixRGB');soil_detail.blend_type='MULTIPLY';soil_detail.inputs[0].default_value=.65
    l.new(soil.outputs[0],soil_detail.inputs[1]);l.new(soil_tex.outputs['Color'],soil_detail.inputs[2])
    mineral=n.new('ShaderNodeTexNoise');mineral.inputs['Scale'].default_value=13;mineral.inputs['Detail'].default_value=2
    l.new(coord.outputs['Object'],mineral.inputs['Vector'])
    mineral_ramp=n.new('ShaderNodeValToRGB')
    mineral_ramp.color_ramp.elements[0].color=(.065,.078,.08,1)
    mineral_ramp.color_ramp.elements[1].color=(.19,.215,.205,1)
    l.new(mineral.outputs['Fac'],mineral_ramp.inputs[0])
    rock=colour_mix(soil_detail.outputs[0],mineral_ramp.outputs[0],split.outputs['Red'])
    moss_noise=n.new('ShaderNodeTexNoise');moss_noise.inputs['Scale'].default_value=16;moss_noise.inputs['Detail'].default_value=2
    l.new(coord.outputs['Object'],moss_noise.inputs['Vector'])
    moss_ramp=n.new('ShaderNodeValToRGB');moss_ramp.color_ramp.elements[0].color=(.025,.05,.012,1)
    moss_ramp.color_ramp.elements[1].color=(.10,.145,.037,1);l.new(moss_noise.outputs['Fac'],moss_ramp.inputs[0])
    moss=colour_mix(rock,moss_ramp.outputs[0],split.outputs['Green'])
    wet_pigment=colour_mix((.03,.026,.018),(.035,.048,.049),split.outputs['Red'])
    wet=colour_mix(moss,wet_pigment,split.outputs['Blue'])
    l.new(wet,p.inputs['Base Color'])
    rough=n.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1
    dry_rough=n.new('ShaderNodeMapRange');dry_rough.inputs['To Min'].default_value=.89;dry_rough.inputs['To Max'].default_value=.70
    l.new(split.outputs['Red'],dry_rough.inputs['Value']);l.new(dry_rough.outputs[0],rough.inputs['To Min'])
    rough.inputs['To Max'].default_value=.34
    l.new(split.outputs['Blue'],rough.inputs['Value']);l.new(rough.outputs[0],p.inputs['Roughness'])
    # Relief follows the rock mask; do not put stone fissures into mud or moss.
    # Reuse authored rock relief: a cellular pattern read like paving in review.
    cracks=n.new('ShaderNodeTexImage');cracks.image=bpy.data.images.load(str(BASE/'PerceivedDetail/T_PD_RockNH_Height16.png'),check_existing=True)
    cracks.image.colorspace_settings.name='Non-Color';cracks.projection='BOX';cracks.projection_blend=.3
    scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=.5
    l.new(coord.outputs['Object'],scale.inputs[0]);l.new(scale.outputs[0],cracks.inputs['Vector'])
    amount=n.new('ShaderNodeMath');amount.operation='MULTIPLY';l.new(cracks.outputs['Color'],amount.inputs[0]);l.new(split.outputs['Red'],amount.inputs[1])
    prior_normal=p.inputs['Normal'].links[0].from_socket
    soil_height=n.new('ShaderNodeTexImage')
    soil_height.image=bpy.data.images.load(str(BASE/'PerceivedDetail/T_PD_SoilNH_Height16.png'),check_existing=True)
    soil_height.image.colorspace_settings.name='Non-Color';soil_height.projection='BOX';soil_height.projection_blend=.3
    l.new(soil_scale.outputs[0],soil_height.inputs['Vector'])
    soil_bump=n.new('ShaderNodeBump');soil_bump.inputs['Distance'].default_value=.025;soil_bump.inputs['Strength'].default_value=.4
    l.new(soil_height.outputs['Color'],soil_bump.inputs['Height']);l.new(prior_normal,soil_bump.inputs['Normal'])
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.028;bump.inputs['Strength'].default_value=.35
    l.new(soil_bump.outputs[0],bump.inputs['Normal'])
    l.new(amount.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    return m


def bark_material():
    m=material('M_Study_BeechBark',(.04,.035,.025),(.12,.11,.075),8,.92,.018)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    coord=next(node for node in n if node.type=='TEX_COORD')
    separate=n.new('ShaderNodeSeparateXYZ');l.new(coord.outputs['Object'],separate.inputs[0])
    low=n.new('ShaderNodeMapRange');low.clamp=True;low.inputs['From Min'].default_value=.15;low.inputs['From Max'].default_value=4.5
    low.inputs['To Min'].default_value=.75;low.inputs['To Max'].default_value=.02;l.new(separate.outputs['Z'],low.inputs['Value'])
    noise=next(node for node in n if node.type=='TEX_NOISE')
    blend=n.new('ShaderNodeMath');blend.operation='MULTIPLY';l.new(low.outputs[0],blend.inputs[0]);l.new(noise.outputs['Fac'],blend.inputs[1])
    pigment=next(node for node in n if node.type=='VALTORGB')
    mix=n.new('ShaderNodeMixRGB');l.new(blend.outputs[0],mix.inputs[0]);l.new(pigment.outputs[0],mix.inputs[1]);mix.inputs[2].default_value=(.055,.09,.022,1)
    l.new(mix.outputs[0],p.inputs['Base Color']);return m


def weathered_rock_material():
    from rock_detail_material import build
    return build()


def outcrops(ground):
    """Rounded weathered masses; explicit geometry, no runtime tessellation.

    Connected rings share smooth normals. The UV footprint is two metres per
    tile, so the normal map carries pores/fissures instead of silhouette polygons.
    Colour.R is an irregular moss mask based on height above the actual support.
    """
    g=L.Geo();rng=random.Random(132052);records=[]
    patches=[(-650,180,240,165),(120,-160,340,180),(770,270,180,220)]
    chunks=[]
    for patch,(au,bv,wu,wv) in enumerate(patches):
        chunks.extend([(patch,au-wu*.18,bv-wv*.12,wu*.66,wv*.77),
                       (patch,au+wu*.45,bv+wv*.24,wu*.38,wv*.52)])
    for index,(patch,au,bv,wu,wv) in enumerate(chunks):
        count=32;phase=rng.uniform(0,math.tau);outline=[]
        for j in range(count):
            angle=j*math.tau/count
            radius=.86+.05*math.sin(angle*3+phase)+.035*math.cos(angle*5-phase)
            outline.append((math.cos(angle)*wu*radius,math.sin(angle)*wv*radius))
        vs=[];uvs=[];colours=[]
        # Denser connected shoulders replace the coarse planar bevels. Irregular
        # outline and crown variation keep this from becoming a perfect ellipsoid.
        profile=[(1.08,-.14),(1.02,-.015),(.94,.13),(.80,.32),(.60,.47),(.34,.57)]
        def add_vertex(da,db,offset):
            wx,wy=S.xy(au+da,bv+db);h=ground((wx-S.CX)/100,-(wy-S.CY)/100)
            assert h[0] is not None
            height=offset*(1 if index%2==0 else .82)
            p=h[0]+Vector((0,0,height));vs.append(p)
            uvs.append(((au+da)/200,(bv+db)/200))
            patch=.5+.25*math.sin(p.x*4.1+math.sin(p.y*3.7))+.2*math.cos(p.y*6.3+phase)
            moss=(1-smooth(.12,.40+.06*math.sin(phase+p.x*3),height))*smooth(.20,.60,patch)*.97
            colours.append((moss,0,0))
        for ring,(factor,height) in enumerate(profile):
            for j,(da,db) in enumerate(outline):
                angle=j*math.tau/count
                weather=(.024*math.sin(angle*3+phase)+.012*math.cos(angle*7-phase))*math.sin(ring/(len(profile)-1)*math.pi)
                add_vertex(da*factor,db*factor,height+weather)
        add_vertex(0,0,.62)
        faces=[]
        for ring in range(len(profile)-1):
            for j in range(count):
                k=(j+1)%count;start=ring*count
                faces.append((start+j,start+k,start+count+k,start+count+j))
        for j in range(count):
            k=(j+1)%count
            start=(len(profile)-1)*count;faces.append((start+j,start+k,len(vs)-1))
        faces=[tuple(reversed(f)) if (vs[f[1]]-vs[f[0]]).cross(vs[f[2]]-vs[f[0]]).z<0 else f for f in faces]
        g.add(vs,faces,colours,uvs,0)
        records.append(dict(existing_patch=patch,chunk=index,base_burial_m=.14,max_added_height_m=.62,
                            segments=count,profile_rings=len(profile),moss='Patchy basal mask, upper faces mineral'))
    ob,dropped=L.to_object(g,'SM_ForestStudy_Outcrops',{0:weathered_rock_material()},[0])
    assert dropped==0
    for p in ob.data.polygons:p.use_smooth=True
    ob.data.calc_loop_triangles();triangles=len(ob.data.loop_triangles)
    L.export(ob,out=OUT)
    return records,triangles


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BASE/'bank-surface.blend'))
    bank=next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('SM_RS7_BankSkin'))
    for ob in list(bpy.data.objects):
        if ob!=bank:bpy.data.objects.remove(ob,do_unlink=True)
    bank.hide_render=False;bank.hide_set(False)
    mesh=bank.data
    original=hashlib.sha256(str([list(v.co) for v in mesh.vertices]).encode()).hexdigest()
    tree=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
    def ground(x,y):
        return tree.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)
    # Reuse the existing mesh and physical rock distribution, with explicit masks.
    masks=[];top_count=221*157
    for v in mesh.vertices:
        x,y,z=v.co;a,b=S.uv(S.CX+x*100,S.CY-y*100)
        # Distinct rock meshes carry the mineral faces now. A broad grey tint
        # beneath them made the soil look like a continuation of each boulder.
        rock=.12*smooth(.44,.73,S.rock(a,b))
        organic=.5+.24*math.sin(x*1.1+math.sin(y*1.3))+.17*math.cos(y*2.1-x*.7)
        cavity=0
        if v.index<top_count:
            i,j=divmod(v.index,157)
            if 3<i<217 and 3<j<153:
                cavity=max(0,sum(mesh.vertices[v.index+d].co.z for d in (3,-3,471,-471))/4-z)
        damp=max(1-smooth(-4,-1.4,z),min(.6,cavity*2.7))*(1-rock*.45)
        # Exposed faces stay mineral; moss concentrates at margins and hollows.
        moss=smooth(.39,.74,organic)*(.9*(1-rock)+rock*(.16+min(.25,cavity*3)))*(1-damp*.55)
        # Moss dominates sheltered pockets, while occasional mineral faces remain.
        masks.append((rock,moss,damp,1))
    attr=mesh.color_attributes.new(name='Habitat',type='FLOAT_COLOR',domain='CORNER')
    attr.data.foreach_set('color',[value for loop in mesh.loops for value in masks[loop.vertex_index]])
    mesh.color_attributes.active_color=attr
    (OUT/'habitat-masks.json').write_text(json.dumps(dict(channels='R rock, G moss, B moisture',values=masks)))
    mesh.materials.clear();mesh.materials.append(ground_material())
    for poly in mesh.polygons:poly.material_index=0
    # Export a candidate copy only; never overwrite the source bank or collision.
    bank.name='SM_ForestStudy_Bank'
    export_copy=bank.copy();export_copy.data=mesh.copy();bpy.context.scene.collection.objects.link(export_copy)
    export_copy.name='SM_ForestStudy_Bank_Export';L.export(export_copy,out=OUT)
    bpy.data.objects.remove(export_copy,do_unlink=True)
    assert original==hashlib.sha256(str([list(v.co) for v in mesh.vertices]).encode()).hexdigest()
    # Existing litter/roots are fitted to this exact surface.
    with bpy.data.libraries.load(str(BASE/'FernFloor/fern-floor.blend'),link=False) as (src,dst):
        dst.objects=[name for name in src.objects if name.startswith('SM_FernFloor_Litter')]
    litter=dst.objects[0];bpy.context.scene.collection.objects.link(litter);litter.hide_render=False;litter.hide_set(False)
    wood=material('M_Study_Roots',(.055,.035,.018),(.13,.095,.045),7,.88,.008)
    leaves=L.material('M_Study_LeafLitter',(.15,.10,.04));litter.data.materials.clear()
    litter.data.materials.append(wood);litter.data.materials.append(leaves)
    mossmat=material('M_Study_Moss',(.035,.065,.018),(.11,.16,.04),20,.96,.008)
    rockmat=material('M_Study_Stone',(.075,.09,.095),(.23,.255,.245),8,.72,.007)
    outcrop_records,outcrop_triangles=outcrops(ground)
    rng=random.Random(132051);detail=L.Geo();counts=dict(stones=0,moss_cushions=0,fallen_branches=0)
    # Modest silhouette relief near the review pocket, not an expensive full-bank carpet.
    for k in range(210):
        x=rng.uniform(-8,4);y=rng.uniform(-3,8);hit=ground(x,y)
        if hit[0] is None or hit[1].z<.35:continue
        p,n=hit[:2];a,b=S.uv(S.CX+x*100,S.CY-y*100)
        moss=(k%4!=0);radius=rng.uniform(.045,.15) if moss else rng.uniform(.07,.23)
        if not moss and S.rock(a,b)>.8:continue
        # Low rounded cushions/stones embedded into the actual support.
        verts=[];rings=3;sides=7
        tangent=n.cross(Vector((0,1,0))).normalized();bitangent=n.cross(tangent)
        for ring in range(rings):
            theta=(ring+.35)/(rings+.1)*math.pi*.5
            for j in range(sides):
                angle=j*math.tau/sides
                rr=radius*(.9+.1*math.sin(j*2+k))
                verts.append(p+(tangent*math.cos(angle)+bitangent*math.sin(angle))*rr*math.cos(theta)+n*(radius*(.32 if moss else .65)*math.sin(theta)-.018))
        faces=[]
        for ring in range(rings-1):
            for j in range(sides):
                a0=ring*sides+j;b0=ring*sides+(j+1)%sides
                faces.append((a0,b0,b0+sides,a0+sides))
        faces.append(tuple(range((rings-1)*sides,rings*sides)))
        detail.add(verts,faces,(.09,.13,.03) if moss else (.15,.16,.13),None,0 if moss else 1)
        counts['moss_cushions' if moss else 'stones']+=1
    # A few grounded fallen branches, with taper and small side forks.
    for k in range(9):
        x=rng.uniform(-7,3);y=rng.uniform(-1,7);angle=rng.uniform(0,math.tau);length=rng.uniform(.7,1.8)
        pts=[]
        for j in range(8):
            h=ground(x+math.cos(angle)*length*j/7,y+math.sin(angle)*length*j/7)
            if h[0] is None:break
            pts.append(h[0]+h[1]*.018)
        if len(pts)==8:
            L.tube(detail,pts,[.045*(1-j/10) for j in range(8)],6,(.08,.055,.025),mi=2)
            L.tube(detail,[pts[3],pts[3]+Vector((.12,.1,.035)),pts[3]+Vector((.24,.23,.02))],[.016,.012,.005],4,(.08,.055,.025),mi=2)
            counts['fallen_branches']+=1
    dressing,dropped=L.to_object(detail,'SM_ForestStudy_Detail',{0:mossmat,1:rockmat,2:wood},[0,1,2])
    for p in dressing.data.polygons:p.use_smooth=True
    assert dropped==0;L.export(dressing,out=OUT)
    with bpy.data.libraries.load(str(BASE/'FernRevision/Variation/fern-variation-library.blend'),link=False) as (src,dst):
        dst.objects=[name for name in src.objects if name.startswith('SM_FernVar_') and name.endswith('_LOD0')]
    meshes={o.name:o.data for o in dst.objects}
    placements=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/placement.json').read_text())['placement']
    roots=[]
    for i,p in enumerate(placements):
        form=p['mesh'].split('_')[2];variant=(i*7+int(abs(p['x'])))%4
        ob=bpy.data.objects.new('StudyPlant_'+str(i),meshes[f'SM_FernVar_{form}_{variant}_LOD0']);bpy.context.scene.collection.objects.link(ob)
        x=(p['x']-S.CX)/100;y=-(p['y']-S.CY)/100;h=ground(x,y)
        z=(p['z']-4800)/100 if h[0] is None else h[0].z-.035*p['scale']
        ob.location=(x,y,z);ob.rotation_euler.z=-math.radians(p['yaw']);ob.scale=(p['scale'],)*3
        roots.append(dict(index=i,mesh=ob.data.name,position=[x,y,z],source_z=(p['z']-4800)/100))
    # Bring in the recorded 12 local trees, rather than inventing a new canopy.
    canopy_sources=json.loads((ROOT/'Saved/LidarAuthoringQA/RS7/forest-sources.json').read_text())
    with bpy.data.libraries.load(str(ROOT/'Art/Export/LidarStudy/ForestFS1/ForestShapes.blend'),link=False) as (src,dst):
        dst.objects=[name for name in src.objects if name in ('SM_FS1_Beech_Mature_LOD0','SM_FS1_Beech_Pole_LOD0')]
    tree_meshes={o.name:o.data for o in dst.objects};bark=bark_material()
    for me in tree_meshes.values():me.materials[0]=bark
    for i,row in enumerate(canopy_sources):
        kind='Mature' if 'SM_Canopy_0' in row['mesh'] else 'Pole'
        ob=bpy.data.objects.new('RecordedTree_'+str(i),tree_meshes['SM_FS1_Beech_'+kind+'_LOD0']);bpy.context.scene.collection.objects.link(ob)
        tf=row['transform'];ob.location=((tf[0]-S.CX)/100,-(tf[1]-S.CY)/100,(tf[2]-4800)/100)
        ob.rotation_euler.z=-2*math.atan2(tf[5],tf[6]);ob.scale=tuple(tf[7:10])
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.22,.27,.30,1);bg.inputs[1].default_value=.45
    bpy.ops.object.light_add(type='AREA',location=(-5,2,10));key=bpy.context.object;key.data.energy=1500;key.data.size=8
    bpy.ops.object.light_add(type='AREA',location=(2,-2,7));bpy.context.object.data.energy=800;bpy.context.object.data.size=6
    bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.lens=32
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    review_cameras=[('forest-bank',(-12,12,2),(-1,1,1)),('forest-floor',(-5,5,1.64),(-2,2,-.36))]
    focus=ground(-5.34,-4.12)[0]+Vector((0,0,.32))
    review_cameras.append(('rock-weathering',tuple(focus+Vector((-3.6,3.7,2.1))),tuple(focus)))
    if '--views' in sys.argv:
        requested=sys.argv[sys.argv.index('--views')+1].split(',')
        review_cameras=[item for item in review_cameras if item[0] in requested]
        assert review_cameras,'No valid review view selected'
    cam.location=review_cameras[0][1];cam.rotation_euler=(Vector(review_cameras[0][2])-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'forest-floor-study.blend'))
    dressing.data.calc_loop_triangles()
    (OUT/'manifest.json').write_text(json.dumps(dict(status='CPU study on actual bank mesh; not installed or accepted',
        bank_source_sha256=hashlib.sha256((BASE/'bank-surface.blend').read_bytes()).hexdigest(),
        bank_geometry_sha256=original,unchanged_bank_geometry=True,plant_instances=len(roots),
        plants=roots,recorded_tree_instances=len(canopy_sources),detail_counts=counts,detail_triangles=len(dressing.data.loop_triangles),
        outcrop_geometry=outcrop_records,outcrop_triangles=outcrop_triangles,rendered_views=[item[0] for item in review_cameras],
        rock_material=dict(normal_map='Textures/T_RockWeather_Normal.png',packed_data='Textures/T_RockWeather_RAH.png',
                           colour_map='Textures/T_RockWeather_Colour.png',moss_colour='Textures/T_RockMoss_Colour.png',
                           moss_data='Textures/T_RockMoss_Data.png',texture_samples=5,
                           texture_baker='Art/tools/bake_rock_surface_detail.py',
                           normal_convention='Tangent +Y, non-colour',uv_tile_metres=2,vertex_colour='R basal moss mask',
                           runtime_tessellation=False,material_slots=1),
        habitat_channels='R exposed rock, G moss, B moisture; vertex masks, not physical mud state',
        pending=['Unreal shader translation/baking','Collision parity for raised rock outcrops','Frond and root clearance for new meshes','Contact bake refresh','Whole-scene canopy and understory review','Runtime performance and memory'],
        lighting='CPU studio approximation; not matched game lighting',live_packages_changed=False),indent=2))
    for label,position,target in review_cameras:
        cam.data.lens=45 if label=='rock-weathering' else 32
        cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    print('FOREST_FLOOR_STUDY_COMPLETE',counts,flush=True)


if __name__=='__main__':main()
