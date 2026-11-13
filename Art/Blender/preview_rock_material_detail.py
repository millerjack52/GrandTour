"""Apply a material-only revision to the saved forest study and prove parity."""
import bpy,sys,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rock_detail_material import build
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FirstSection/ForestFloorRevision')


def geometry_state():
    state={}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        me=ob.data;h=hashlib.sha256()
        for v in me.vertices:h.update(struct.pack('<3f',*v.co))
        for p in me.polygons:h.update(struct.pack('<I',len(p.vertices)));h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
        for layer in me.uv_layers:
            for item in layer.data:h.update(struct.pack('<2f',*item.uv))
        for layer in me.color_attributes:
            for item in layer.data:h.update(struct.pack('<4f',*item.color))
        for row in ob.matrix_world:h.update(struct.pack('<4f',*row))
        me.calc_loop_triangles()
        state[ob.name]=dict(sha256=h.hexdigest(),vertices=len(me.vertices),triangles=len(me.loop_triangles))
    return state


bpy.ops.wm.open_mainfile(filepath=str(OUT/'before-material-detail.blend'))
before=geometry_state()
rock=next(o for o in bpy.context.scene.objects if o.name.startswith('SM_ForestStudy_Outcrops'))
rock.data.materials.clear();rock.data.materials.append(build())
after=geometry_state();assert before==after,'Material revision changed geometry, UVs, masks or transforms'
assert after[rock.name]['triangles']==2112
manifest=json.loads((OUT/'manifest.json').read_text())
manifest['rock_material'].update(colour_map='Textures/T_RockWeather_Colour.png',
    moss_colour='Textures/T_RockMoss_Colour.png',moss_data='Textures/T_RockMoss_Data.png',
    texture_samples=5,texture_baker='Art/tools/bake_rock_surface_detail.py',
    shading_only=True,geometry_validation='material-detail-validation.json')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.cycles.device='CPU'
bank=bpy.data.objects['SM_ForestStudy_Bank'];me=bank.data
tree=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[list(p.vertices) for p in me.polygons])
focus=tree.ray_cast(Vector((-5.34,-4.12,100)),Vector((0,0,-1)),200)[0]+Vector((0,0,.32))
views=[('rock-weathering',tuple(focus+Vector((-3.6,3.7,2.1))),tuple(focus),45),
       ('forest-bank',(-12,12,2),(-1,1,1),32)]
(OUT/'material-detail-validation.json').write_text(json.dumps(dict(geometry_unchanged=before==after,
    checks='All scene mesh positions, topology, UVs, colour attributes, world transforms and triangle counts',
    outcrop_triangles=2112,geometry=after,texture_samples=5,displacement=False,
    live_packages_changed=False,performance='Pending at user request',views=views),indent=2))
scene.camera.location=views[0][1]
scene.camera.rotation_euler=(Vector(views[0][2])-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.lens=45
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'forest-floor-study.blend'))
for name,position,target,lens in views:
    scene.camera.location=position;scene.camera.data.lens=lens
    scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('MATERIAL_DETAIL_COMPLETE_GEOMETRY_UNCHANGED',flush=True)
