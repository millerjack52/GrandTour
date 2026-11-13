import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01');O=P.parent/'prado-glazing-audit';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'prado-cabin-v08/Prado_Interior.blend'));sc=bpy.context.scene
A=json.loads((P/'islands.json').read_text())[0];G=json.loads((P/'glass-selections.json').read_text());v=[Vector(p) for p in A['verts']]
tree=BVHTree.FromPolygons(v,A['polys'])
rep={'objects':{},'rear_rays':{},'front_rays':{}}
for o in sc.objects:
 if o.name.startswith('Glass'):
  rep['objects'][o.name]={'bounds':[[min((o.matrix_world@w.co)[i]/5 for w in o.data.vertices) for i in range(3)],[max((o.matrix_world@w.co)[i]/5 for w in o.data.vertices) for i in range(3)]],'verts':len(o.data.vertices)}
for z in [.31,.32,.34,.36,.38,.40,.415,.42]:
 rep['rear_rays'][str(z)]={}
 for x in [-.15,-.12,-.08,-.04,0,.04,.08,.12,.15]:
  p,n,idx,d=tree.ray_cast(Vector((x,.55,z)),Vector((0,-1,0)),.25)
  rep['rear_rays'][str(z)][str(x)]={'hit':list(p) if p else None,'normal':list(n) if n else None,'face':idx}
for z in [.300,.305,.31,.315,.32,.34,.36,.38,.40,.41]:
 rep['front_rays'][str(z)]={}
 for x in [-.15,-.12,-.08,-.04,0,.04,.08,.12,.15]:
  p,n,idx,d=tree.ray_cast(Vector((x,-.3,z)),Vector((0,1,0)),.25)
  rep['front_rays'][str(z)][str(x)]={'hit':list(p) if p else None,'normal':list(n) if n else None,'face':idx,'selected':idx in G['Windscreen']['faces'] if idx is not None else False}
(O/'rays.json').write_text(json.dumps(rep,indent=2))
for o in sc.objects:o.hide_render=True
me=bpy.data.meshes.new('Original body audit');me.from_pydata([p*5 for p in v],[],A['polys']);me.update();ob=bpy.data.objects.new('Original body audit',me);sc.collection.objects.link(ob)
def mat(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);return m
for n,c in [('body',(.45,.46,.39)),('selected rear',(.02,.2,.7)),('selected front',(.03,.5,.7))]:me.materials.append(mat(n,c))
for f in me.polygons:
 f.material_index=1 if f.index in G['RearWindow']['faces'] else 2 if f.index in G['Windscreen']['faces'] else 0
 f.use_smooth=False
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=False;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.show_object_outline=True
sc.render.resolution_x=1300;sc.render.resolution_y=900;sc.render.resolution_percentage=100
cam=sc.camera;cam.hide_render=False;cam.data.type='ORTHO'
for name,c,d,sz in [('source-rear',(0,.36,.36),(0,3,0),.45),('source-rear-quarter',(0,.35,.36),(-2,3,.5),.50),('source-front',(0,-.13,.355),(0,-3,0),.45),('source-front-quarter',(0,-.13,.355),(-2,-3,.5),.5)]:
 center=Vector(c)*5;cam.location=center+Vector(d)*5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=sz*5;sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('AUDIT DONE',O)
