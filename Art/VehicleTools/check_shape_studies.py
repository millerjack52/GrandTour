import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]);report={}
for key in ['A','B']:
 bpy.ops.wm.open_mainfile(filepath=str(out/('Shape_Study_'+key+'.blend')))
 c=next(c for c in bpy.data.collections if c.get('shape_spec') and json.loads(c['shape_spec'])['key']==key)
 body=next(o for o in c.objects if o.name.startswith('Study | continuous folded lower body'))
 bm=bmesh.new();bm.from_mesh(body.data);closed=all(e.is_manifold for e in bm.edges)
 if not closed:print('OPEN_EDGES',[(len(e.link_faces),[tuple(v.co) for v in e.verts]) for e in bm.edges if not e.is_manifold],flush=True)
 bm.free()
 finite=all(math.isfinite(v) for o in c.objects if o.type=='MESH' for p in o.data.vertices for v in p.co)
 visible=all(not o.hide_render for o in c.objects)
 for o in bpy.context.scene.objects:
  if o.type=='EMPTY' and any(cc.get('gt_owner') for cc in o.users_collection):o.hide_set(True)
 report[key]=dict(lower_shell_closed=closed,finite_mesh_coordinates=finite,correct_study_visible_on_reopen=visible,spec=json.loads(c['shape_spec']),scope='Primary shape review only. No component fit, rig or export clearance claims.')
 assert closed and finite and visible,report[key]
 sc=bpy.context.scene;cam=sc.camera;matrix=cam.matrix_world.copy();scale=cam.data.ortho_scale
 cam.location=(0,.06,7);cam.rotation_euler=(Vector((0,.06,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=6.6
 clay=bpy.data.materials.get('Shape study | neutral clay')
 if not clay:
  clay=bpy.data.materials.new('Shape study | neutral clay');clay.use_nodes=True;bs=clay.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.36,.38,.37,1);bs.inputs['Roughness'].default_value=.78
 sc.view_layers[0].material_override=clay;sc.render.filepath=str(out/(key+'-top-clay.png'));bpy.ops.render.render(write_still=True)
 cam.matrix_world=matrix;cam.data.ortho_scale=scale;sc.view_layers[0].material_override=None
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(out/('Shape_Study_'+key+'.blend')))
(out/'geometry-check.json').write_text(json.dumps(report,indent=2));print('SHAPE_CHECKS '+json.dumps(report),flush=True)
