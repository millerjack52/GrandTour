"""Continuous fitted rubber bumper insert with a real recessed mounting flange."""
source_tree=tree(body);angles=np.linspace(-1.18,1.18,101);origin=Vector((0,-1.25,0));samples=[]
for theta in angles:
 direction=Vector((sin(theta),-cos(theta),0));row=[]
 for z in [.600,.680]:
  ray=origin+direction*1.8;ray.z=z;h=source_tree.ray_cast(ray,-direction,1.4)
  if h[0] is not None:row.append((h[0]-Vector((0,-1.25,z))).dot(direction))
 if row:samples.append((theta,sum(row)/len(row)))
coef=np.polynomial.polynomial.polyfit([a for a,r in samples],[r for a,r in samples],8)
vs=[];N=len(angles)
for z,offset in [(.602,-.018),(.602,.014),(.675,.014),(.675,-.018)]:
 for theta in angles:
  direction=Vector((sin(theta),-cos(theta),0));radius=float(np.polynomial.polynomial.polyval(theta,coef));p=origin+direction*(radius+offset);p.z=z;vs.append(p)
faces=[(j*N+i,j*N+i+1,((j+1)%4)*N+i+1,((j+1)%4)*N+i) for j in range(4) for i in range(N-1)];faces.extend([(0,N,2*N,3*N),(N-1,2*N-1,3*N-1,4*N-1)])
band=mesh('Front bumper | continuous rubber insert',vs,faces,rubber);bevel(band,.004,3)
# Set the trapped folded lip behind the insert's interior mounting face.
recess=[]
for v in body.data.vertices:
 p=v.co
 if not (.603<p.z<.674 and p.y<-1.48):continue
 d=p-Vector((0,-1.25,p.z));theta=math.atan2(d.x,-d.y)
 if abs(theta)>1.175:continue
 radius=float(np.polynomial.polynomial.polyval(theta,coef));excess=d.length-(radius-.020)
 if 0<excess<.045:
  v.co-=d.normalized()*excess;recess.append(excess)
body.data.update();report['repairs'].append({'part':'Front bumper mounting seam','method':'Continuous closed rubber insert fitted to original bumper cross-sections; folded mounting lip recessed behind it','max_lip_recess_m':max(recess,default=0),'vertices':len(recess)})
