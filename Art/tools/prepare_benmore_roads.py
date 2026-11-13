"""Author first-pass roads on a copy of the surveyed Benmore heightfield.

Local metres: X east, Y north, Z above the terrain package datum. Road layout
is fictional. No changes to the original DEM or shared environment assets.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Art/Export/MackenzieRealTerrain/BenmoreFullSite'
OUT=ROOT/'Art/Export/BenmoreRoads'; OUT.mkdir(exist_ok=True)
N=2017; STEP=2500/(N-1)
original=(np.asarray(Image.open(SOURCE/'H_Benmore_UE_2017.png')).astype(float)-32768)/64

def height(grid,x,y):
    fx=np.clip((np.asarray(x)+1250)/STEP,0,N-1.000001); fy=np.clip((np.asarray(y)+1250)/STEP,0,N-1.000001)
    ix=fx.astype(int);iy=fy.astype(int);a=fx-ix;b=fy-iy
    return (grid[iy,ix]*(1-a)+grid[iy,ix+1]*a)*(1-b)+(grid[iy+1,ix]*(1-a)+grid[iy+1,ix+1]*a)*b

def curve(points,closed):
    p=np.array(points,float); dense=[];n=len(p)
    for i in range(n if closed else n-1):
        a,b,c,d=[p[k%n] if closed else p[max(0,min(n-1,k))] for k in [i-1,i,i+1,i+2]]
        for t in np.linspace(0,1,60,endpoint=False):dense.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    dense=np.array(dense+[p[0] if closed else p[-1]])
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
    s=np.linspace(0,arc[-1],math.ceil(arc[-1]/2)+1)
    return s,np.stack([np.interp(s,arc,dense[:,i]) for i in range(2)],axis=1)

def smooth(z,ds,radius,closed):
    k=math.ceil(radius/ds);weights=np.exp(-.5*(np.arange(-k,k+1)/(k/2.5))**2);weights/=weights.sum()
    if closed:return np.r_[np.convolve(np.pad(z[:-1],k,mode='wrap'),weights,'valid'),0][:-1].tolist()
    return np.convolve(np.pad(z,k,mode='edge'),weights,'valid')

def route(name,points,closed,width,radius):
    s,xy=curve(points,closed); raw=height(original,xy[:,0],xy[:,1]);ds=s[1]
    if closed:
        z=np.array(smooth(raw,ds,radius,True));z=np.r_[z,z[0]]
    else:z=smooth(raw,ds,radius,False)
    return dict(name=name,s=s,xy=xy,z=z,raw=raw,closed=closed,width=width)

main=route('Terrace loop',[(-750,-450),(-850,-180),(-730,-30),(-350,-80),(-150,-200),(100,-350),(80,-540),(-230,-530),(-500,-600)],True,6.4,38)
branch=route('Hillside branch',[(-350,-80),(-220,100),(-150,160),(80,90),(300,-100),(100,-350)],False,4.4,42)
routes=[main,branch]
# Weld branch ends to the main profile and preserve tangent height at junctions.
for end in [0,-1]:
    j=np.argmin(np.linalg.norm(main['xy']-branch['xy'][end],axis=1));delta=main['z'][j]-branch['z'][end]
    dist=branch['s'] if end==0 else branch['s'][-1]-branch['s']
    w=np.clip(1-dist/90,0,1);branch['z']+=delta*w*w*(3-2*w)

# Limit the optional climb to a sustained 22% design grade. Keep junction
# heights fixed and distribute small cuts/fills into the neighbouring profile.
z=branch['z'];ends=z[[0,-1]].copy();limit=.22*(branch['s'][1]-branch['s'][0])
for repeat in range(350):
    for parity in [0,1]:
        ids=np.arange(parity,len(z)-1,2);delta=z[ids+1]-z[ids]
        correction=(delta-np.clip(delta,-limit,limit))*.5
        z[ids]+=correction;z[ids+1]-=correction
    z[[0,-1]]=ends

graded=original.copy(); masks=np.zeros((N,N,3),float)
# Nearest-segment projection within small bounding boxes avoids a huge distance
# matrix. Main road wins in the shared junction footprint.
for r in routes[::-1]:
    best=np.full((N,N),1e9);target=original.copy();hw=r['width']/2;shoulder=10 if r is main else 8
    for i,(a,b) in enumerate(zip(r['xy'][:-1],r['xy'][1:])):
        reach=hw+shoulder
        lo=np.maximum(0,np.floor((np.minimum(a,b)-reach+1250)/STEP).astype(int));hi=np.minimum(N-1,np.ceil((np.maximum(a,b)+reach+1250)/STEP).astype(int))
        sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1))
        X,Y=np.meshgrid(np.arange(lo[0],hi[0]+1)*STEP-1250,np.arange(lo[1],hi[1]+1)*STEP-1250)
        v=b-a; t=np.clip(((X-a[0])*v[0]+(Y-a[1])*v[1])/np.dot(v,v),0,1)
        dist=np.hypot(X-a[0]-t*v[0],Y-a[1]-t*v[1]);take=dist<best[sl]
        crown=-.018*np.minimum(dist,hw)
        target[sl]=np.where(take,r['z'][i]+t*(r['z'][i+1]-r['z'][i])+crown,target[sl]);best[sl]=np.minimum(best[sl],dist)
    w=np.clip((hw+shoulder-best)/shoulder,0,1);w=w*w*(3-2*w)
    graded=graded*(1-w)+target*w
    road=np.clip((hw+.8-best)/1.2,0,1)
    masks[:,:,0]=np.maximum(masks[:,:,0],road)
    masks[:,:,1]=np.maximum(masks[:,:,1],np.clip((hw+3-best)/3,0,1))
    if r is branch:masks[:,:,2]=road

encoded=np.rint(graded*64+32768).astype('uint16');graded=(encoded.astype(float)-32768)/64
Image.fromarray(encoded).save(OUT/'H_Benmore_Roads_2017.png')
encoded.astype('<u2').tofile(OUT/'H_Benmore_Roads_2017.r16')
rg=np.zeros((N,N,4),dtype='uint8');rg[:,:,0]=encoded>>8;rg[:,:,1]=encoded&255;rg[:,:,3]=255
Image.fromarray(rg).save(OUT/'T_Benmore_RoadHeightRG.png')
Image.fromarray(np.uint8(np.clip(masks,0,1)*255)).save(OUT/'T_Benmore_RoadMask.png')
graded.astype('<f4').tofile(OUT/'height_local_south_up.f32')
result={'ok':True,'level':'/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive','datum_m':360.531005859375,'grid_resolution':N,'width_m':2500,'orientation':'X east, Y north; images south-up','routes':[]}
for r in routes:
    z=height(graded,r['xy'][:,0],r['xy'][:,1]);yaw=np.degrees(np.arctan2(np.gradient(r['xy'][:,1]),np.gradient(r['xy'][:,0])))
    rows=[dict(arc_m=float(s),x_m=float(p[0]),y_m=float(p[1]),z_m=float(h),yaw=float(a)) for s,p,h,a in zip(r['s'],r['xy'],z,yaw)]
    grade=np.abs(np.diff(z)/np.diff(r['s']))*100
    result['routes'].append(dict(name=r['name'],closed=r['closed'],width_m=r['width'],length_m=float(r['s'][-1]),max_grade_percent=float(grade.max()),p95_grade_percent=float(np.percentile(grade,95)),max_profile_adjustment_m=float(np.abs(r['z']-r['raw']).max()),points=rows))
result['earthworks']={'max_cut_m':float((original-graded).max()),'max_fill_m':float((graded-original).max()),'area_changed_over_10cm_m2':float(np.sum(np.abs(graded-original)>.1)*STEP**2)}
result['validation_anchors']=[{'pixel':[x,y],'z_m':float(graded[y,x])} for y in [0,211,510,1008,1517,1801,2016] for x in [0,189,501,1008,1437,1803,2016]]
assert result['routes'][0]['max_grade_percent']<15
assert result['routes'][1]['max_grade_percent']<24
assert max(result['earthworks']['max_cut_m'],result['earthworks']['max_fill_m'])<4
# Dense art sample on the first 220 m; lighter roadside groups give the rest
# of the loop scale. Exclude every road, including shared junctions.
rng=np.random.default_rng(106);foliage=[];stones=[];posts=[]
for ri,r in enumerate(result['routes']):
    for i,row in enumerate(r['points']):
        a=math.radians(row['yaw']);side=np.array([-math.sin(a),math.cos(a)])
        p=np.array([row['x_m'],row['y_m']]);dense=ri==0 and row['arc_m']<220
        for j in range(24 if dense else (2 if i%3==0 else 0)):
            side_dist=rng.uniform(r['width_m']/2+1.2,9.5 if dense else 9)*rng.choice([-1,1])
            xy=p+side*side_dist+rng.uniform(-1,1,2)
            if height(masks[:,:,0],*xy)>.03:continue
            foliage.append(dict(kind=int(rng.integers(0,4)),xyz=[*xy.tolist(),float(height(graded,*xy))-.04],yaw=float(rng.uniform(0,360)),scale=float(rng.uniform(.65,1.2))))
        if i%2==0:
            xy=p+side*(r['width_m']/2+rng.uniform(.4,1.8))*rng.choice([-1,1])
            if height(masks[:,:,0],*xy)<.1:stones.append(dict(kind=int(rng.integers(1,5)),xyz=[*xy.tolist(),float(height(graded,*xy))-.015],yaw=float(rng.uniform(0,360)),scale=float(rng.uniform(.07,.22))))
        if i%60==0:
            for sign in [-1,1]:
                xy=p+side*(r['width_m']/2+1.6)*sign
                if height(masks[:,:,0],*xy)<.03:posts.append([*xy.tolist(),float(height(graded,*xy))])
result['dressing_counts']={'tussock':len(foliage),'stones':len(stones),'posts':len(posts)}
(OUT/'dressing.json').write_text(json.dumps(dict(foliage=foliage,stones=stones,posts=posts),separators=(',',':')))
(OUT/'road-manifest.json').write_text(json.dumps(result,indent=2))
print(json.dumps({**result,'routes':[{k:v for k,v in r.items() if k!='points'} for r in result['routes']],'validation_anchors':'49'},indent=2))

# GIS presentation, drawn from surveyed terrain and actual authored polylines.
im=Image.open(SOURCE/'Terrain_Colour_Preview_2048.png').resize((1100,1100))
sheet=Image.new('RGB',(1560,1250),'#172123');sheet.paste(im,(30,100));d=ImageDraw.Draw(sheet)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
d.text((30,24),'BENMORE / FIRST DRIVING ROUTES',font=font(30),fill='#f4efdf')
def pix(p):return(30+(p[0]+1250)/2500*1100,100+(1250-p[1])/2500*1100)
for r,col in zip(routes,['#f8d48a','#e88362']):
    pts=[pix(p) for p in r['xy']];d.line(pts,fill='#222b29',width=8);d.line(pts,fill=col,width=4)
start=main['xy'][20];p=pix(start);d.ellipse((p[0]-7,p[1]-7,p[0]+7,p[1]+7),fill='white');d.text((p[0]+14,p[1]),'START',font=font(19),fill='white')
for j,(r,col) in enumerate(zip(result['routes'],['#f8d48a','#e88362'])):
    y=125+j*210;d.text((1160,y),r['name'].upper(),font=font(25),fill=col)
    for k,t in enumerate([f"{r['length_m']/1000:.2f} km / {r['width_m']:.1f} m wide",f"Peak grade: {r['max_grade_percent']:.1f}%",f"95th percentile: {r['p95_grade_percent']:.1f}%"]):d.text((1160,y+50+k*33),t,font=font(20),fill='#ced8d0')
for k,t in enumerate(['Whole selected site retained.','Road corridors graded locally.','Fictional route, real terrain.','','Dressing concentrated near','the start for scale review.','','Source: LINZ / CC BY 4.0']):d.text((1160,625+k*35),t,font=font(19),fill='#ced8d0')
d.text((30,1210),'Road layout blockout / wider landscape remains available for later route expansion.',font=font(20),fill='#ced8d0')
sheet.save(OUT/'Road_Plan.png')
