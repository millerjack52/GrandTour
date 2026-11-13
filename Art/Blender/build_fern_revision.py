"""Isolated fern form/shading study. CPU preview; never imports into the live map.

Run Blender --background --threads 4 --python this_file.py.
Owner Waimeamea photos 04 and 08 guide the hanging and upright growth forms.
The review renderer is a material approximation, not Unreal acceptance evidence.
"""
import ast
import bpy
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'Art/Export/LidarStudy/FirstSection/FernRevision'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))
import native_plant_lib as L


def old_definitions():
    path = HERE / 'build_lidar_bank_section.py'
    tree = ast.parse(path.read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    namespace = dict(L=L, Vector=Vector, math=math, random=random)
    exec(compile(tree, str(path), 'exec'), namespace)
    return namespace


def design(variant):
    rng = random.Random(85031 + variant * 101)
    fronds = []
    for i in range(11):
        young = i >= 8
        # An outward fan with a raised centre, not an evenly spaced radial disc.
        az = rng.uniform(-1.35, 1.35) if not young else rng.uniform(-1.8, 1.8)
        length = rng.uniform(1.28, 2.02) if not young else rng.uniform(.63, 1.06)
        el = rng.uniform(.84, 1.15) if not young else rng.uniform(1.22, 1.48)
        droop = rng.uniform(2.02, 2.7) if not young else rng.uniform(.48, .95)
        pigment = (.075, .185, .085) if not young else (.145, .245, .082)
        if i == 1 and variant == 1:
            pigment = (.15, .105, .043)
        colour = tuple(c * rng.uniform(.92, 1.08) for c in pigment)
        fronds.append(dict(az=az, length=length, el=el, droop=droop,
                           width=rng.uniform(.18, .24), curl=rng.uniform(-.18, .18),
                           roll=rng.uniform(-.65, .65), colour=colour,
                           phase=rng.uniform(0, math.tau), seed=rng.randrange(100000), young=young))
    return fronds


def pinna(g, a, direction, side, up, length, halfwidth, colour, phase, lod):
    """Curved lanceolate blade, open silhouette, gently cupped cross-section."""
    stations = (.28, .65) if lod == 0 else (.44,)
    verts = [a]
    uvs = [(0, .5)]
    colours = [tuple(c * .83 for c in colour)]
    for u in stations:
        centre = a + direction * length * u + side * length * .12 * u*u
        centre += up * length * (.09 * math.sin(math.pi*u) - .14*u*u)
        width = halfwidth * math.sin(math.pi * u)**.65
        for cross in (-1, 0, 1):
            p = centre + side * width * cross
            p += up * (width * .14 * (1-abs(cross)) + cross * width * .12 * math.sin(phase+u*3))
            verts.append(p)
            uvs.append((u, (cross+1)*.5))
            # Quiet pigment variation follows the blade; no random colour per face.
            tint = 1 + .07*math.sin(u*math.pi) + (.035 if cross == 0 else 0)
            colours.append(tuple(c*tint for c in colour))
    verts.append(a + direction*length + side*length*.12 - up*length*.14)
    uvs.append((1, .5)); colours.append(tuple(c*.94 for c in colour))
    faces = [(0,1,2), (0,2,3)]
    if len(stations) == 2:
        faces += [(1,4,2),(2,4,5),(2,5,3),(3,5,6)]
    last = 1 + (len(stations)-1)*3
    tip = len(verts)-1
    faces += [(last,tip,last+1), (last+1,tip,last+2)]
    # Keep normals consistent on both sides of the rachis.
    if (verts[faces[0][1]]-verts[0]).cross(verts[faces[0][2]]-verts[0]).dot(up) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, colours, uvs, 1)


def build(fronds, lod):
    g = L.Geo()
    L.tube(g, [(0,0,-.16),(.015,0,-.02),(.035,0,.07)], [.08,.065,.03], 7,
           (.085,.065,.028), mi=0, caps=(True, True))
    skeleton = []
    for f in fronds:
        direction = Vector((math.cos(f['az'])*math.cos(f['el']), math.sin(f['az'])*math.cos(f['el']), math.sin(f['el'])))
        pts, tans, sides, ups = L.frond_path(Vector((.025,0,.065)), direction, f['length'], f['droop'], 16, 1.25, f['curl'], f['roll'])
        skeleton.append([list(p) for p in pts])
        L.tube(g, pts[::2], [.005*(1-j/11) for j in range(9)], 3, (.105,.135,.047), mi=1)
        rng = random.Random(f['seed'])
        for j in range(24):
            jitter = rng.uniform(-.18,.18)
            scale = rng.uniform(.89,1.08)
            for sign in (-1, 1):
                asymmetry = rng.uniform(.88,1.08)
                twist = rng.uniform(-.14,.14)
                # Draw the same random design at all LODs, then reduce coverage detail.
                if lod == 1 and j % 4 == 1: continue
                if lod == 2 and j % 2: continue
                t = .13 + .84*(j+.5+jitter+(.27 if sign<0 else 0))/24
                seg = min(15,int(t*16)); v=t*16-seg
                a=pts[seg].lerp(pts[seg+1],v)
                T=tans[seg].lerp(tans[seg+1],v).normalized()
                S=sides[seg]; U=ups[seg]
                envelope=math.sin(math.pi*(t-.05)/.95)**.85
                ln=f['width']*envelope*scale*asymmetry
                d=(S*sign + T*(.24 + .19*t) + U*twist).normalized()
                cross=(T-d*T.dot(d)).normalized()
                width=f['length']*.84/24*.62*(1-.35*t)
                width=min(width, ln*.18)
                if lod: width *= (1.18 if lod==1 else 1.6)
                colour=tuple(c*(.94+.08*math.sin(t*4+f['phase'])) for c in f['colour'])
                pinna(g,a,d,cross,U,ln,width,colour,f['phase'],lod)
    g.a = [max(0.,min(1.,(math.hypot(v.x,v.y)-.12)/1.2)) for v in g.v]
    return g, skeleton


def material():
    m=L.material('M_FernRevision_Preview',(.075,.185,.085))
    nodes=m.node_tree.nodes; links=m.node_tree.links
    p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Roughness'].default_value=.7
    p.inputs['Specular IOR Level'].default_value=.25
    # Thin leaf diffuse transmission approximation, not a claimed Unreal match.
    output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    translucent=nodes.new('ShaderNodeBsdfTranslucent')
    colour=next(n for n in nodes if n.type=='VERTEX_COLOR')
    links.new(colour.outputs['Color'],translucent.inputs['Color'])
    mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.16
    links.new(p.outputs['BSDF'],mix.inputs[1]);links.new(translucent.outputs[0],mix.inputs[2])
    links.new(mix.outputs[0],output.inputs['Surface'])
    return m


def main():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mats=L.plant_materials();candidate_mats={0:mats[0],1:material()}
    old=old_definitions();records=[];display=[]
    for variant in range(3):
        fs=design(variant); hashes=[]; counts=[]
        for lod in range(3):
            g,skeleton=build(fs,lod)
            ob,dropped=L.to_object(g,f'SM_FernRevision_Cascade_{variant}_LOD{lod}',candidate_mats,[0,1])
            # Shared pinna vertices interpolate normal direction across their curvature.
            for p in ob.data.polygons:p.use_smooth=True
            hashes.append(hashlib.sha256(json.dumps(skeleton).encode()).hexdigest())
            ob.data.calc_loop_triangles();counts.append(len(ob.data.loop_triangles))
            assert dropped==0,(ob.name,dropped)
            L.export(ob,out=OUT)
            ob.hide_render=True
            if lod==0:display.append(ob)
        oldg,_=old['build'](old['design'](0,variant),0,0)
        oldob,_=L.to_object(oldg,f'Original_Cascade_{variant}',mats,[0,1])
        oldob.hide_render=True
        oldob.data.calc_loop_triangles();original=len(oldob.data.loop_triangles)
        assert len(set(hashes))==1, 'LOD changed frond skeleton'
        assert counts[0]<=original, (counts,original)
        assert counts[0]>counts[1]>counts[2]
        records.append(dict(variant=variant,triangles=counts,original_lod0_triangles=original,
                            skeleton_sha256=hashes[0],dropped_faces=0))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.2,.25,.3,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
    bpy.ops.object.light_add(type='AREA',location=(0,-3,5));bpy.context.object.data.energy=500;bpy.context.object.data.size=4
    bpy.ops.object.light_add(type='AREA',location=(2,3,2));bpy.context.object.data.energy=320;bpy.context.object.data.size=3
    bpy.ops.object.camera_add(location=(4,-5,2.8));cam=bpy.context.object
    cam.rotation_euler=(Vector((.65,0,.15))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=3.9;scene.camera=cam
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    manifest=dict(status='CANDIDATE: CPU asset preview, not installed or accepted',
                  owner_feedback='Both fern shape and shading unsatisfactory',
                  references=['Waimeamea/04_river_riffle_wading_ferns.jpg','Waimeamea/08_bush_interior_crown_fern_pole_beech_mud.jpg'],
                  variants=records,performance='PENDING; triangle counts are not GPU timings',
                  constraints='No live map, package, shared generator or planting changes; opaque mesh leaves, no new alpha overdraw',
                  pending=['Unreal material translation and visual comparison','Placement and uphill clearance recheck','Wind and LOD motion review','Clean GPU comparison'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fern-revision.blend'))
    for name,ob in [('before',bpy.data.objects['Original_Cascade_0']),('candidate',display[0])]:
        ob.hide_render=False;scene.render.filepath=str(OUT/(name+'.png'))
        bpy.ops.render.render(write_still=True);ob.hide_render=True
    print('FERN_REVISION_COMPLETE',json.dumps(records),flush=True)


if __name__=='__main__':main()
