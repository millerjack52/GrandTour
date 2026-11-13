"""Deterministic, batched spray seeds on the accepted shallow river bake."""
import bpy, numpy as np, json
from pathlib import Path
root=Path('C:/GrandTour');out=root/'Art/Export/BenmoreGaea/WaterDetail_20261011'
out.mkdir(exist_ok=True)
d=np.load(root/'Art/Export/BenmoreGaea/Morphology/flow-bake.npz')
rng=np.random.default_rng(10411)
depth=d['depth'];speed=np.hypot(d['vx'],d['vy'])
eligible=(depth>.08)&(depth<.42)&(speed>.65)&d['wet'].astype(bool)
# Require wet neighbours: launch points and their short arcs stay off the bank.
for axis in [0,1]:
 for offset in [-1,1]:eligible &= np.roll(d['wet'].astype(bool),offset,axis)
jj,ii=np.where(eligible)
keep=(ii%2==0)&(jj%2==0);jj,ii=jj[keep],ii[keep]
if len(ii)>1400:
 pick=rng.choice(len(ii),1400,replace=False);jj,ii=jj[pick],ii[pick]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
verts=[];faces=[];uvs=[];seeds=[]
for j,i in zip(jj,ii):
 x=float(d['x'][i]);y=float(d['y'][j]);z=float(d['surface'][j,i])+.015
 for k in range(8):
  cx=x+rng.uniform(-.28,.28);cy=y+rng.uniform(-.28,.28);s=rng.random()
  start=len(verts)
  for u,v in [(0,0),(1,0),(1,1),(0,1)]:
   # Unreal's FBX conversion mirrors Y and flips the texture V coordinate.
   verts.append((cx+(u-.5)*.04,-(cy+(v-.5)*.04),z));uvs.append((u,1-v));seeds.append((s,0))
  faces.append(tuple(start+n for n in range(4)))
mesh=bpy.data.meshes.new('RiffleSpray');mesh.from_pydata(verts,[],faces);mesh.update()
for name,values in [('UVMap',uvs),('Seed',seeds)]:
 layer=mesh.uv_layers.new(name=name)
 for polygon in mesh.polygons:
  for li in polygon.loop_indices:layer.data[li].uv=values[mesh.loops[li].vertex_index]
obj=bpy.data.objects.new('SM_RiffleSpray',mesh);bpy.context.collection.objects.link(obj)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
bpy.ops.export_scene.fbx(filepath=str(out/'SM_RiffleSpray.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
(out/'spray-seeds.json').write_text(json.dumps({'sites':len(ii),'droplets':len(faces),'triangles':len(faces)*2,'depth_m':[.08,.42],'min_speed_mps':.65,'collision':False},indent=2))
