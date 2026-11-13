"""Recess only hidden front wheelhouse vertices out of the sampled tyre envelope."""
rep=[]
for tag in ['FL','FR']:
 obs=[o for o in GEAR.objects if o.name.startswith('Wheel_'+tag) and ('Tyre' in o.name or 'Tread' in o.name)];pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 centre=Vector([(min(p[k] for p in pts)+max(p[k] for p in pts))/2 for k in range(3)]);radius=max(math.hypot(p.y-centre.y,p.z-centre.z) for p in pts);width=max(abs(p.x-centre.x) for p in pts);moved=[]
 for vert in body.data.vertices:
  p=vert.co.copy()
  if abs(p.x)>.996 or abs(p.x)<.46 or p.z<centre.z-.02 or abs(p.y-centre.y)>radius+.12 or p.z>centre.z+radius+.12:continue
  for _ in range(4):
   for deg in [-22,-15,-8,0,8,15,22]:
    a=math.radians(deg);u=Vector((cos(a),sin(a),0));v=Vector((-sin(a),cos(a),0));c=centre+Vector((0,0,.025));delta=p-c;ax=delta.dot(u);t=delta.dot(v);z=delta.z;r=math.hypot(t,z)
    if abs(ax)<width+.003 and .10<r<radius+.007:
     change=radius+.007-r;direction=(v*t+Vector((0,0,z))).normalized();p+=direction*change
  delta=p-vert.co
  if .00001<delta.length<.075:vert.co=p;moved.append(delta.length)
 rep.append({'wheel':tag,'vertices':len(moved),'maximum_recess_m':max(moved,default=0),'scope':'Wheelhouse and inner arch return, |X| < 0.996 m; outermost arch edge retained'})
body.data.update();report['wheelhouse_clearance_repairs']=rep
