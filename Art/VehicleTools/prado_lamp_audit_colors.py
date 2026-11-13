exec(compile(open('C:/GrandTour/Art/VehicleTools/prado_lamp_audit_inspect.py').read().split("render('rear-v08'")[0],'<audit_setup>','exec'))
body=bpy.data.objects['Prado | fixed shell and underbody']
sh.color_type='MATERIAL'
matids={}
for name,col in [('amber',(.83,.24,.016,1)),('red',(.50,.025,.012,1)),('reverse',(.73,.79,.76,1)),('rim',(.04,.047,.045,1))]:
 m=bpy.data.materials.new('audit '+name);m.diffuse_color=col;matids[name]=len(body.data.materials);body.data.materials.append(m)
faces={'L':[],'R':[]};bands={}
for p in body.data.polygons:
 vs=[(body.matrix_world@body.data.vertices[i].co)/5 for i in p.vertices];c=sum(vs,Vector())/len(vs)
 if .1535<abs(c.x)<.190 and .4235<c.y<.437 and .211<c.z<.285 and p.normal.y>.20 and min(v.z for v in vs)>.2109 and max(v.z for v in vs)<.2867:
  name='reverse' if c.z<.2338867 else ('red' if c.z<.258301 else 'amber')
  p.material_index=matids[name];faces['L' if c.x>0 else 'R'].append(p.index);bands[str(p.index)]=name
for o in sc.objects:
 if o.type=='MESH' and any(c.name in ['04 Spare wheel','06 Roof rack and cargo','07 Side equipment','09 Small fittings'] for c in o.users_collection):o.hide_render=True
render('candidate-rear-2',(0,.43,.27),(0,3,0),.49)
render('candidate-corner-2',(.17,.43,.255),(1.7,3,.4),.20)
(OUT/'candidate-lamp-faces.json').write_text(json.dumps({'faces':faces,'bands':bands},indent=2))
print('CANDIDATES',faces)
