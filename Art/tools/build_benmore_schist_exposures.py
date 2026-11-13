"""Terrain-fitted angular schist beds and their downslope fragments."""
from prepare_benmore_composition import OUT, height, gradient, clearance, HFILE
import numpy as np
import json, math, hashlib

data=json.loads((OUT/'placements.json').read_text());manifest=[]
for index,site in enumerate(data['outcrops']):
    rng=np.random.default_rng(site['seed']);origin=np.array([site['x'],site['y'],site['z']])
    yaw=math.radians(site['yaw']);along=np.array([math.cos(yaw),math.sin(yaw)])
    across=np.array([-along[1],along[0]])
    verts=[];faces=[];colors=[];contacts=[]

    def slab(xy,rx,ry,tall,angle,scree=False):
        if clearance(*xy)<max(rx,ry)+10:return
        a=np.array([math.cos(angle),math.sin(angle)]);b=np.array([-a[1],a[0]])
        n=7;theta=np.arange(n)*2*math.pi/n+rng.uniform(-.09,.09,n)
        outline=np.cos(theta)[:,None]*a*rx+np.sin(theta)[:,None]*b*ry
        outline*=rng.uniform(.85,1.06,(n,1));g=gradient(*xy,5)
        basal=height(xy[0]+outline[:,0],xy[1]+outline[:,1])-(.12 if scree else .38)
        top=float(height(*xy))+tall*rng.uniform(.62,1.13,n)+outline@g*.72+outline@along*.065
        top=np.maximum(top,height(xy[0]+outline[:,0],xy[1]+outline[:,1])+.12)
        # Fracture planes retain sharp edges; nested bevels produce thin beds.
        levels=[(0,1.0),(0.12,1.02)] if not scree else [(0,1.0)]
        if not scree:
            for k in range(1,int(rng.integers(3,6))):
                t=.16+k*.145
                levels.extend([(t,1.0-t*.28+rng.uniform(-.04,.05)),(t+.028,.95-t*.28)])
        levels.extend([(.94,.70),(1,.54)])
        start=len(verts);tone=float(rng.uniform(.30,.85))
        for t,radius in levels:
            shift=along*t*rx*.21;ringxy=xy+outline*radius+shift
            z=basal*(1-t)+top*t
            for j in range(n):
                pt=np.array([ringxy[j,0],ringxy[j,1],z[j]])
                if t==0:
                    pt[2]=float(height(*pt[:2]))-(.12 if scree else .38)
                    contacts.append(pt.tolist())
                verts.append((pt-origin).tolist());colors.append([tone,t,0,1])
        faces.append([start+j for j in reversed(range(n))])
        for k in range(len(levels)-1):
            for j in range(n):
                faces.append([start+k*n+j,start+k*n+(j+1)%n,start+(k+1)*n+(j+1)%n,start+(k+1)*n+j])
        # Uneven caps split into visible planes rather than a level parapet.
        cap=start+(len(levels)-1)*n
        centre=np.mean(np.array(verts[cap:cap+n]),axis=0);centre[2]+=tall*.12
        vi=len(verts);verts.append(centre.tolist());colors.append([tone,1,0,1])
        for j in range(n):faces.append([cap+j,cap+(j+1)%n,vi])

    # Broken, asymmetric clusters share a geological strike but have no
    # continuous wall. Short wedges emerge at several depths across the bank.
    slab_count=0
    for _ in range(int(rng.integers(9,17))):
        cursor=float(rng.normal(0,site['length_m']*.23))
        if abs(cursor)>site['length_m']*.45:continue
        rx=float(rng.uniform(1.5,3.9));ry=float(rng.uniform(1.4,3.2))
        xy=origin[:2]+along*cursor+across*rng.normal(0,site['width_m']*.45)
        tall=float(rng.uniform(.65,1.95))*(1.1-abs(cursor)/site['length_m']*.5)
        slab(xy,rx,ry,tall,yaw+rng.uniform(-.40,.40));slab_count+=1
    down=-gradient(*origin[:2],10);down/=max(np.linalg.norm(down),.01)
    for _ in range(110):
        xy=origin[:2]+along*rng.uniform(-site['length_m']*.62,site['length_m']*.62)+down*rng.uniform(3,22)+rng.normal(0,2,2)
        slab(xy,float(rng.uniform(.20,.83)),float(rng.uniform(.16,.54)),float(rng.uniform(.10,.42)),yaw+rng.uniform(-.45,.45),True)
    assert len(verts)>1000
    name='SM_Benmore_SchistExposure_'+str(index).zfill(2)
    payload=dict(vertices=verts,faces=faces,colors=colors)
    (OUT/(name+'.json')).write_text(json.dumps(payload,separators=(',',':')))
    contact_clearance=min(clearance(v[0],v[1]) for v in contacts)
    gap=max(v[2]-float(height(v[0],v[1])) for v in contacts)
    assert contact_clearance>9 and gap<-.1
    manifest.append(dict(name=name,origin_m=origin.tolist(),vertices=len(verts),faces=len(faces),slabs=slab_count,
                         min_road_edge_clearance_m=contact_clearance,max_basal_gap_m=gap,
                         support_samples_m=contacts[::max(1,len(contacts)//24)]))
report=dict(parts=manifest,height_sha256=hashlib.sha256(HFILE.read_bytes()).hexdigest(),height_changed=False,
            min_road_edge_clearance_m=min(p['min_road_edge_clearance_m'] for p in manifest),
            max_basal_gap_m=max(p['max_basal_gap_m'] for p in manifest))
(OUT/'outcrops.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='parts'},indent=2))
print('formations',len(manifest),'faces',sum(p['faces'] for p in manifest))
