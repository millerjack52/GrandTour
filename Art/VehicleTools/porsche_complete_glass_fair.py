"""Fair rear pane depth and its shared seal interface, preserving X/Z outlines."""
pane=bpy.data.objects['Rear glass'];rim=bpy.data.objects['Rear glass fitted surround'];N=238
ps=np.array([list(v.co) for v in pane.data.vertices]);x,y,z=ps.T
A=np.column_stack([np.ones(len(x)),x,z,x*x,x*z,z*z]);co=np.linalg.lstsq(A,y,rcond=None)[0]
def rear_y(p):
 x,z=p.x,p.z;return float(np.dot(co,[1,x,z,x*x,x*z,z*z]))
oldrim=[rim.data.vertices[i].co.copy() for i in range(N)]
delta=[rear_y(p)+.002-p.y for p in oldrim]
kd=KDTree(N)
for i,p in enumerate(oldrim):kd.insert(p,i)
kd.balance();moved=[]
for v in body.data.vertices:
 p=v.co
 if p.y<.98 or not 1.09<p.z<1.51:continue
 h=kd.find(p);dist=h[2]
 if dist<.065:
  hits=kd.find_n(p,5);w=[math.exp(-(d/.021)**2) for q,i,d in hits]
  dy=sum(a*delta[i] for a,(q,i,d) in zip(w,hits))/max(sum(w),1e-12)
  fall=min(1.,max(0.,(.065-dist)/.040));change=dy*fall;p.y+=change;moved.append(abs(change))
half=len(pane.data.vertices)//2
for i,v in enumerate(pane.data.vertices):v.co.y=rear_y(v.co)+(.001 if i<half else -.001)
rh=len(rim.data.vertices)//2
for i,v in enumerate(rim.data.vertices):
 row=(i%rh)//N;offset=[.002,.007,.007,.002][min(row,3)]-(.004 if i>=rh else 0)
 v.co.y=rear_y(v.co)+offset
for ob in [body,pane,rim]:ob.data.update();finish(ob,1.4)
report['repairs'].append({'part':'Rear glass and shared mounting return','operation':'Continuous quadratic optical depth, original pane outline retained','maximum_local_body_depth_adjustment_m':max(moved,default=0)})
