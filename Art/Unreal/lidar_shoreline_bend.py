"""Fit a drive-up test bend to the visible river and the final collision terrain in LiDAR."""

import hashlib
import json
import math
import random

import unreal as u

from lidar_grounding import GroundSampler
from preview_erosion_bank_meshes import build_tile
from benmore_river_life_materials import Graph


LEVEL = "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy"
PACKAGE = "/Game/GrandTour/ArtTests/LidarStudy/ShorelineTestBend"
SOIL = "/Game/GrandTour/ArtTests/LidarStudy/FirstSection/T_BankSoilColour"
TAG = "GT_ShorelineTestBend"
# Endpoints specify cross-sections through the reach, in metres. The wet/dry
# boundary within each cross-section comes from the current map at bake time.
# Each section has separate wet and landward X brackets, interpolated along Y.
SECTIONS = (
    ("OuterCut", -404.8, -394.8, (-494., -472.), (-490., -473.), False, 27),
    ("LowShoulder", -391.8, -385.8, (-488., -473.), (-486., -471.), False, 43),
    ("GravelShelf", -403.8, -390.8, (-494., -512.), (-490., -508.), True, 61),
)


def lerp(a, b, t):
    return a + (b-a)*t


def taper(t):
    t = min(1., max(0., t))
    return t*t*(3.-2.*t)


class RiverSurface:
    def __init__(self, refs, world):
        self.world = world
        author = next(a for a in refs if isinstance(a, u.GTProceduralGround))
        self.terrain = GroundSampler(author)
        self.digest = author.current_terrain_digest()
        self.water = next(a for a in refs if a.get_actor_label() == "LidarStudy_RiverWater")
        self.sheet = next(a for a in refs if isinstance(a, u.GTWaterSheet) and not a.get_editor_property("mud_initial_domain"))
        # Trace only visible river geometry and walkable topography. Foliage and
        # existing bank pieces must never move the measured shoreline on a rebake.
        self.ignore = [a for a in refs if a != self.water and not isinstance(a, (u.Landscape, u.GTRoadReliefTile))]

    def bed(self, x, y):
        return self.terrain.height(x*100., y*100.) / 100.

    def water_hit(self, x, y):
        z = self.bed(x,y)*100.
        hit = u.SystemLibrary.line_trace_single(
            self.world, u.Vector(x*100.,y*100.,z+1200.), u.Vector(x*100.,y*100.,z-250.),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1, True, self.ignore, u.DrawDebugTrace.NONE, True)
        if hit:
            values = hit.to_tuple()
            if self.water in values:
                return values[4].z/100.
        return None

    def shore(self, wet, dry, y):
        if self.water_hit(wet, y) is None or self.water_hit(dry, y) is not None:
            raise ValueError(f"Unbracketed shoreline at {wet}, {dry}, {y}")
        # Follow the first dry surface encountered from the channel. This also
        # works where the rendered mesh ends at the edge of its water mask.
        side = 1 if dry > wet else -1
        while abs(dry-wet) > .6:
            step = wet + side*.6
            if self.water_hit(step,y) is None:
                dry = step
                break
            wet = step
        for _ in range(8):
            middle = (wet+dry)*.5
            if self.water_hit(middle,y) is None:
                dry = middle
            else:
                wet = middle
        return wet, self.water_hit(wet,y)


def stone(part, bed, rng, x, y, radius, water):
    """A low, partly buried cobble with a tilted crown. Shares the bank batch."""
    ox, oy, oz = part["origin"]
    z = bed(x,y)
    h = radius*rng.uniform(.34,.66)
    angle = rng.uniform(-math.pi, math.pi)
    count = 8
    radial = [rng.uniform(.84,1.13) for _ in range(count)]
    width = rng.uniform(.53,.85)
    pigment = rng.choice(((.040,.043,.038),(.054,.052,.041),(.038,.041,.043),(.061,.055,.042)))
    tint = rng.uniform(.82,1.12) * (.74 if z < water+.09 else 1.)
    lean = rng.uniform(-.28,.28)
    rings = []
    for scale, fraction in ((.90,-.55),(1.,.21),(.61,.78)):
        ring = []
        for j in range(count):
            a = 2*math.pi*j/count
            dx,dy = radius*radial[j]*math.cos(a), radius*width*radial[j]*math.sin(a)
            px=x+scale*(dx*math.cos(angle)-dy*math.sin(angle))
            py=y+scale*(dx*math.sin(angle)+dy*math.cos(angle))
            local = bed(px,py)
            pz = min(z,local)-.12 if fraction<0 else .55*z+.45*local+h*(fraction+lean*math.cos(a))
            ring.append(len(part["v"]))
            part["v"].append([px-ox,py-oy,pz-oz])
            part["c"].append([v*tint*(.85+.18*fraction) for v in pigment])
            part["uv"].append([(px-ox)/.72,(py-oy)/.72])
        rings.append(ring)
    top=len(part["v"])
    part["v"].append([x-ox,y-oy,z+h-oz])
    part["uv"].append([(x-ox)/.72,(y-oy)/.72])
    part["c"].append([v*tint*1.03 for v in pigment])
    for k in range(count):
        n=(k+1)%count
        for lower, upper in zip(rings,rings[1:]):
            part["t"].extend(((lower[k],upper[k],lower[n]),(lower[n],upper[k],upper[n])))
        part["t"].append((rings[-1][n],rings[-1][k],top))


# Lateral offsets in metres from the measured waterline. Positive points uphill.
# The sole straddles the wet margin, the rear skirt and both ends enter the soil.
CUT = ((-1.05,-.16),(-.56,.02),(-.31,.16),(-.12,.39),(-.09,.64),
       (-.19,.83),(-.22,.96),(.01,1.),(.55,.85),(1.16,.60),(1.88,.24),(2.36,-.22))
SHELF = ((-1.25,-.2),(-.9,.02),(-.65,.16),(-.38,.43),(-.14,.70),
         (.12,.86),(.43,1.),(.82,.89),(1.25,.68),(1.69,.41),(2.10,.17),(2.5,-.22))


def build_section(spec, ground):
    name, y0,y1,first,last,gravel,seed = spec
    rng=random.Random(seed)
    side=1 if first[1]>first[0] else -1
    n=math.ceil((y1-y0)/.30)
    shore=[]
    for i in range(n+1):
        t=i/n
        y=lerp(y0,y1,t)
        x,level=ground.shore(lerp(first[0],last[0],t),lerp(first[1],last[1],t),y)
        shore.append([x,y,level])
    ox,oy,oz=shore[n//2]
    part=dict(origin=[ox,oy,oz],v=[],c=[],t=[],uv=[])
    profile=SHELF if gravel else CUT
    count=len(profile)
    for i,(x,y,level) in enumerate(shore):
        t=i/n
        end=taper(min(t,1-t)/.13)
        wave=.5+.5*math.sin((y-y0)*1.18+seed)
        height=(.21+.24*wave if gravel else .53+.42*wave)+.09*math.sin(2.4*y+seed)
        near_wet=ground.sheet.covers(u.Vector2D((x-side*.23)*100,y*100))
        if not near_wet:
            raise ValueError(f"Physical river and rendered mesh disagree at {x}, {y}")
        for j,(off,amount) in enumerate(profile):
            off=off*(.79+.21*math.sin(y*.81+seed))+.13*math.sin(y*1.36+seed)*end
            px=x+side*off
            base=ground.bed(px,y)
            rise=height*max(0.,amount)*end
            z=base+rise-.13*(1.-end)
            if j==0 or j==count-1:
                z=base-.16
            if gravel:
                # Limit the bar to the water elevation. Following the original
                # steep slope here spreads a grey skin up the opposite bluff.
                top = level + lerp(-.28, .19+.13*wave, max(amount,0.))
                z = lerp(min(base-.12, level-.12), top, end)
                if j in (0,count-1):
                    z = min(base-.16, level-.16)
            wet=taper((z-level+.035)/.42)
            cap=taper((off-.03)/.60)
            tint=.84+.14*math.sin(y*1.6+seed+off*.8)+rng.uniform(0,.07)
            pigment=[lerp(a,b,wet) for a,b in zip((.030,.028,.021),(.070,.049,.032))]
            if gravel:
                pigment=[lerp(a,b,.52) for a,b in zip(pigment,(.068,.062,.049))]
            else:
                pigment=[lerp(a,b,cap) for a,b in zip(pigment,(.052,.057,.030))]
            part["v"].append([px-ox,y-oy,z-oz])
            part["c"].append([v*tint for v in pigment])
            part["uv"].append([(y-y0)/1.25,(off+rise)/1.25])
            if i and j:
                a=(i-1)*count+j-1
                b=a+count
                faces=((a,b,a+1),(b,b+1,a+1))
                part["t"].extend(f if side>0 else f[::-1] for f in faces)
    def gravel_surface(x, y):
        # The cross-sections are straight in Y. Interpolate their corresponding
        # edge vertices to seat each cobble on the triangle surface or bare bed.
        index=max(0.,min(n-1.e-6,(y-y0)/(y1-y0)*n))
        row=math.floor(index)
        f=index-row
        base=ground.bed(x,y)
        for j in range(count-1):
            a,b=part["v"][row*count+j:row*count+j+2]
            c,d=part["v"][(row+1)*count+j:(row+1)*count+j+2]
            edge=lerp(a[0],c[0],f)
            split=lerp(b[0],c[0],f)
            far=lerp(b[0],d[0],f)
            local=x-ox
            if side*(local-edge)<0 or side*(far-local)<0:
                continue
            e_z,m_z,f_z=lerp(a[2],c[2],f),lerp(b[2],c[2],f),lerp(b[2],d[2],f)
            if side*(local-split)<=0:
                xa,xb,za,zb=edge,split,e_z,m_z
            else:
                xa,xb,za,zb=split,far,m_z,f_z
            blend=(local-xa)/(xb-xa) if abs(xb-xa)>1.e-8 else 0.
            return max(base,oz+lerp(za,zb,blend))
        return base

    for _ in range(round((y1-y0)*(3.1 if gravel else .85))):
        i=rng.randrange(2,n-1)
        x,y,level=shore[i]
        offset=rng.uniform(-.95,.18)
        radius=rng.uniform(.09,.34) if gravel else rng.uniform(.13,.37)
        stone(part,gravel_surface if gravel else ground.bed,rng,x+side*offset,y+rng.uniform(-.1,.1),radius,level)
    return name,part,shore


def earth_material(material=None):
    """Use the existing LiDAR soil colour and packed height on caps and steep faces."""
    colour = u.load_asset(SOIL)
    data = u.load_asset(SOIL.replace("SoilColour", "SoilORH"))
    if not colour or not data:
        raise ValueError("Missing the LiDAR bank soil textures")
    if material is None:
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_BankEarth", PACKAGE, u.Material, u.MaterialFactoryNew())
    if material.get_path_name() != PACKAGE+"/M_BankEarth.M_BankEarth":
        raise ValueError("Expected the dedicated shoreline test material")
    u.MaterialEditingLibrary.delete_all_material_expressions(material)
    graph = Graph(material, "Shoreline soil")
    position = graph.node(u.MaterialExpressionWorldPosition)
    normal = graph.node(u.MaterialExpressionVertexNormalWS)
    graph.m.set_editor_property("tangent_space_normal", False)
    soil = graph.node(u.MaterialExpressionTextureObject, texture=colour)
    packed = graph.node(u.MaterialExpressionTextureObject, texture=data,
                        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    # Two projections prevent a near-vertical face from smearing the forest floor.
    shade = graph.custom(["P","N","Pigment","Soil","Packed"], """
float w=smoothstep(.28,.83,abs(N.z));
float2 face=float2(P.y+.19*P.x,P.z)/145., top=P.xy/165.;
float3 soil=lerp(Texture2DSample(Soil,SoilSampler,face).rgb,Texture2DSample(Soil,SoilSampler,top).rgb,w);
float3 field=lerp(Texture2DSample(Packed,PackedSampler,face).rgb,Texture2DSample(Packed,PackedSampler,top).rgb,w);
float grain=smoothstep(.016,.14,dot(soil,float3(.28,.57,.15)));
Height=field.b*3.2;
float3 base=lerp(float3(.066,.054,.041),float3(.23,.184,.126),grain);
return base*clamp(Pigment/float3(.052,.048,.036),.65,1.45)*lerp(.87,1.10,field.r);
""", outputs=[("Height",u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for name,node in (("P",position),("N",normal),("Pigment",graph.node(u.MaterialExpressionVertexColor)),
                      ("Soil",soil),("Packed",packed)):
        graph.wire(node,shade,name)
    from lidar_bank_material_polish import BUMP
    bump = graph.custom(["H","P","N","Camera"],BUMP)
    graph.wire(shade,bump,"H","Height")
    graph.wire(position,bump,"P")
    graph.wire(normal,bump,"N")
    graph.wire(graph.node(u.MaterialExpressionCameraPositionWS),bump,"Camera")
    graph.output(bump,u.MaterialProperty.MP_NORMAL)
    graph.output(shade,u.MaterialProperty.MP_BASE_COLOR)
    graph.output(graph.scalar(.88),u.MaterialProperty.MP_ROUGHNESS)
    graph.output(graph.scalar(.15),u.MaterialProperty.MP_SPECULAR)
    if u.MaterialEditingLibrary.recompile_material(material):
        raise RuntimeError("Shoreline soil failed to compile")
    return material


def stage():
    ed=u.get_editor_subsystem(u.EditorActorSubsystem)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0]!=LEVEL or u.EditorLevelLibrary.get_game_world():
        raise RuntimeError("Load L_LidarStudy and end Play before placing the bend")
    u.SystemLibrary.execute_console_command(world, "Editor.AsyncAssetCompilationFinishAll")
    refs=ed.get_all_level_actors()
    ground=RiverSurface(refs,world)
    built=[build_section(spec,ground) for spec in SECTIONS]
    assets=u.EditorAssetLibrary
    material_path=PACKAGE+"/M_BankEarth"
    mat=u.load_asset(material_path) if assets.does_asset_exist(material_path) else earth_material()
    rows=[]
    for name,part,shore in built:
        rev=hashlib.sha256(json.dumps(part,separators=(",",":")).encode()).hexdigest()[:10]
        path=PACKAGE+"/SM_"+name+"_"+rev
        if assets.does_asset_exist(path):
            mesh=u.load_asset(path)
            loc=u.Vector(*[100*v for v in part["origin"]])
        else:
            mesh,loc=build_tile([part],path,mat)
        rows.append((name,mesh,loc,part,shore))
    # Build every section before touching the level. Only manage tagged actors.
    existing={a.get_actor_label():a for a in refs if TAG in map(str,a.tags)}
    labels=["Shoreline Test Bend - "+r[0] for r in rows]
    if set(existing)-set(labels):
        raise RuntimeError("Review unexpected previously tagged pieces before replacing them")
    report={"terrain":ground.digest,"sections":[]}
    for label,(name,mesh,loc,part,shore) in zip(labels,rows):
        actor=existing.get(label) or ed.spawn_actor_from_object(mesh,loc)
        actor.set_actor_label(label)
        actor.set_folder_path("LiDAR/River/Shoreline Test Bend")
        if TAG not in map(str, actor.tags):
            actor.set_editor_property("tags", [*actor.tags, u.Name(TAG)])
        comp=actor.static_mesh_component
        comp.set_mobility(u.ComponentMobility.STATIC)
        comp.set_static_mesh(mesh)
        actor.set_actor_transform(u.Transform(location=loc),False,True)
        comp.set_collision_profile_name("BlockAll")
        comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        report["sections"].append(dict(label=label,asset=mesh.get_path_name().split(".")[0],origin_m=part["origin"],shore_m=shore,triangles=len(part["t"])))
    return report


def save(report):
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != LEVEL or u.EditorLevelLibrary.get_game_world():
        raise RuntimeError("Save the staged bend from the LiDAR editor world")
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    expected = {s["asset"] for s in report["sections"]}
    tagged = [a for a in actors if TAG in map(str, a.tags)]
    assigned = {a.static_mesh_component.static_mesh.get_path_name().split(".")[0] for a in tagged}
    if len(tagged) != len(SECTIONS) or assigned != expected:
        raise RuntimeError("The staged actors and the supplied bank report differ")
    for path in [PACKAGE+"/M_BankEarth"]+[s["asset"] for s in report["sections"]]:
        if not u.EditorAssetLibrary.save_loaded_asset(u.load_asset(path),False):
            raise RuntimeError("Could not save "+path)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():
        raise RuntimeError("Could not save LiDAR study level")
