"""Fitted closed wheelwell interiors; original visible arch lips stay in place."""
well_rep=[]
bm=bmesh.new();bm.from_mesh(body.data)
local_edges=[]
for e in bm.edges:
 p=(e.verts[0].co+e.verts[1].co)/2
 if e.calc_length()>.040 and .54<abs(p.x)<.985 and p.z>.375 and any(math.hypot(p.y-y,p.z-.383423)<.56 for y in [-1.31067,1.20411]):local_edges.append(e)
if local_edges:bmesh.ops.subdivide_edges(bm,edges=local_edges,cuts=3,use_grid_fill=True)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
for y0,r,xinner,label in [(-1.31067,.446,.570,'Front'),(1.20411,.458,.645,'Rear')]:
 for side in [-1,1]:
  # Remove the folded donor returns behind the new closed tub rather than
  # leave chords intersecting its surface. The exterior lip is retained.
  bm=bmesh.new();bm.from_mesh(body.data);cut=[]
  for f in bm.faces:
   p=f.calc_center_median();x=abs(p.x);rr=math.hypot(p.y-y0,p.z-.383423)
   localr=r+((.430 if label=='Front' else .435)-r)*max(0.,min(1.,(x-xinner)/(.982-xinner)))
   if p.x*side>0 and xinner-.006<x<.978 and p.z>.378 and rr<localr+.012:cut.append(f)
  moved=len(cut)
  bmesh.ops.delete(bm,geom=cut,context='FACES');bm.to_mesh(body.data);bm.free()
  # Slightly crowned barrel, bounded by the actual arch width and cabin wall.
  n=65;vs=[]
  for x in np.linspace(xinner,.982,9):
   t=(x-xinner)/(.982-xinner);rad=r+((.430 if label=='Front' else .435)-r)*t
   for j in range(n):
    a=pi*j/(n-1);vs.append((side*float(x),y0+rad*cos(a),.383423+rad*sin(a)))
  fs=[(k*n+j,k*n+j+1,(k+1)*n+j+1,(k+1)*n+j) for k in range(8) for j in range(n-1)]
  liner=mesh(label+' wheelhouse | fitted barrel '+str(side),vs,fs,rubber,GEAR);thick(liner,.005)
  arc=[(side*xinner,y0+r*cos(pi*j/(n-1)),.383423+r*sin(pi*j/(n-1))) for j in range(n)]
  wall=mesh(label+' wheelhouse | inner closure '+str(side),arc,[tuple(range(n))],rubber,GEAR);thick(wall,.005)
  well_rep.append({'part':label+str(side),'radius_m':r,'inner_x_m':xinner,'folded_source_return_faces_removed':moved})
body.data.update()
box('Underbody | central floor shield',(0,-.03,.431),(1.27,1.74,.026),steel,GEAR,.010)
box('Underbody | front compartment closure',(0,-1.34,.416),(1.07,.91,.020),steel,GEAR,.009)
report['fitted_wheelwell_liners']=well_rep
