import bpy,json,collections
from pathlib import Path
S=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend')
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath');O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S),load_ui=False,use_scripts=False)
s=bpy.context.scene
rows=[]
for o in s.objects:
 rows.append(dict(name=o.name,type=o.type,hide=o.hide_render,location=list(o.location),dimensions=list(o.dimensions),vertices=len(o.data.vertices) if o.type=='MESH' else 0,materials=[m.name if m else '' for m in o.data.materials] if o.type=='MESH' else [],modifiers=[dict(name=m.name,type=m.type,group=m.node_group.name if m.type=='NODES' and m.node_group else '') for m in o.modifiers],particles=[dict(name=p.name,count=p.settings.count,instance=p.settings.instance_object.name if p.settings.instance_object else '',collection=p.settings.instance_collection.name if p.settings.instance_collection else '') for p in o.particle_systems]))
dg=bpy.context.evaluated_depsgraph_get();instances=collections.Counter();base={}
for i in dg.object_instances:
 if i.object.type=='MESH':
  key=i.object.original.name;instances[key]+=1;base[key]={'verts':len(i.object.data.vertices),'hide':i.object.hide_render}
lights=[dict(name=o.name,type=o.data.type,energy=o.data.energy,color=list(o.data.color),matrix=[list(r) for r in o.matrix_world]) for o in s.objects if o.type=='LIGHT']
cam=s.camera;fwd=cam.matrix_world.to_quaternion() @ __import__('mathutils').Vector((0,0,-1))
out=dict(source=str(S),objects=rows,instances=dict(instances),instance_bases=base,lights=lights,camera=dict(name=cam.name,matrix=[list(r) for r in cam.matrix_world],position=list(cam.matrix_world.translation),forward=list(fwd),angle=cam.data.angle,lens=cam.data.lens,sensor=cam.data.sensor_width),render=dict(engine=s.render.engine,resolution=[s.render.resolution_x,s.render.resolution_y],transform=s.view_settings.view_transform,look=s.view_settings.look,exposure=s.view_settings.exposure),materials=[dict(name=m.name,nodes=[dict(name=n.name,type=n.type,group=n.node_tree.name if n.type=='GROUP' and n.node_tree else '',image=n.image.name if n.type=='TEX_IMAGE' and n.image else '') for n in m.node_tree.nodes]) for m in bpy.data.materials if m.node_tree])
(O/'source-audit.json').write_text(json.dumps(out,indent=2))
print('PATH_AUDIT',len(rows),sum(instances.values()),len(instances),out['camera'],flush=True)
