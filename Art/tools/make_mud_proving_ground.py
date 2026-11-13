"""Deterministic, non-tiled world-space soil authoring data. No Unreal dependency.

Produces numeric textures, not an aesthetic acceptance render. The rest map is
shared by CPU contact and the material; RG encodes -50..15 cm at 16-bit precision.
"""
import json, math, random, struct, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/MudProvingGround'
N=512; SIZE=3150.; ORIGIN=-1575.; WATER=-4.5

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a))); return t*t*(3-2*t)

def noise(x,y,seed=0):
    def h(a,b):
        q=(a*374761393+b*668265263+seed*2246822519)&0xffffffff
        q=((q^(q>>13))*1274126177)&0xffffffff
        return ((q^(q>>16))&0xffffff)/16777215.
    a=math.floor(x);b=math.floor(y);u=smooth(0,1,x-a);v=smooth(0,1,y-b)
    return (h(a,b)*(1-u)+h(a+1,b)*u)*(1-v)+(h(a,b+1)*(1-u)+h(a+1,b+1)*u)*v

def png(path,pixels):
    def chunk(k,b):return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b)&0xffffffff)
    rows=b''.join(b'\0'+pixels[j*N*4:(j+1)*N*4] for j in range(N))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',N,N,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    heights=[0.]*(N*N);mask=[0.]*(N*N);soft=[0.]*(N*N)
    for j in range(N):
        y=ORIGIN+(j+.5)*SIZE/N
        for i in range(N):
            x=ORIGIN+(i+.5)*SIZE/N;k=j*N+i
            centre=(noise(x/380,3,4)-.5)*180
            cover=(1-smooth(1220,1450,abs(x)))*(1-smooth(390,610,abs(y-centre)))
            mask[k]=cover;soft[k]=(.78+.18*noise(x/280,y/310,28))*cover
            # Broad undulations and intermittent old wheel paths, with independently wandering banks.
            h=-1+7*(noise(x/390,y/260,10)-.5)+3*(noise(x/125,y/165,14)-.5)
            h+=1.5*(noise(x/17,y/24,16)-.5)
            for side in (-1,1):
                line=centre+side*(82+28*noise(x/210,side*5,30))+(noise(x/180,side*7,31)-.5)*36
                d=abs(y-line);width=23+19*noise(x/130,side*3,32)
                continuity=smooth(.12,.7,noise(x/240,side*8,33))*(1-smooth(1100,1320,abs(x)))
                h-=(5+7*noise(x/190,side*3,34))*(1-smooth(width*.4,width*1.6,d))*continuity
                h+=2*(1-smooth(width*.5,width*1.7,abs(d-width*2)))*continuity*noise(x/80,y/90,35)
            # Connected lobes carve a basin; warped coordinates and intact islands define its shoreline.
            wx=x+(noise(x/180,y/190,40)-.5)*95
            wy=y+(noise(x/190,y/170,41)-.5)*80
            bowls=[(540,140,300,195,22),(780,-45,210,130,18),(315,-80,200,145,16)]
            basin=max(a*math.exp(-(((wx-cx)/rx)**2+((wy-cy)/ry)**2)*1.6) for cx,cy,rx,ry,a in bowls)
            island=11*math.exp(-(((x-565)/75)**2+((y-95)/60)**2)*1.8)
            heights[k]=(h-basin+island)*cover
    # Spatially scattered sheared lobes, folds and blunt clods. Local rasterisation avoids O(N^2*clods).
    rng=random.Random(7139)
    for index in range(650):
        cx=rng.uniform(-1370,1370);cy=rng.uniform(-470,470)
        # A few large torn slabs amongst many small fragments, with independent orientation.
        large=index%4==0
        length=rng.uniform(35,105) if large else rng.uniform(15,43)
        width=rng.uniform(25,62) if large else rng.uniform(12,32)
        angle=rng.uniform(-math.pi,math.pi)
        c=math.cos(angle);s=math.sin(angle);amp=rng.uniform(9,19) if large else rng.uniform(3,9);form=rng.randrange(3)
        radius=length+width
        lo=lambda v:max(0,math.floor((v-ORIGIN)/SIZE*N))
        hi=lambda v:min(N,math.ceil((v-ORIGIN)/SIZE*N))
        for j in range(lo(cy-radius),hi(cy+radius)):
            for i in range(lo(cx-radius),hi(cx+radius)):
                x=ORIGIN+(i+.5)*SIZE/N-cx;y=ORIGIN+(j+.5)*SIZE/N-cy
                u=(x*c+y*s)/length;v=(-x*s+y*c)/width
                edge=max(abs(u+.22*v),abs(v)+.18*max(0,u))
                if edge>=1:continue
                crown=max(.1,.65-.3*v+.12*u)
                if form==1:crown*=.5+.5*(1-smooth(.1,.5,abs(v+.2)))
                if form==2:crown*=smooth(.05,.35,abs(u+.25*v+.15))
                k=j*N+i
                fragment=amp*(1-smooth(.78,1,edge))*crown
                fracture=1.2*(noise((x+cx)/12,(y+cy)/18,61)-.5)
                heights[k]+=(fragment+fracture)*mask[k]
    rest=bytearray();paint=bytearray();wet=0;area=0;low=100;high=-100
    for k,h in enumerate(heights):
        h=max(-27,min(12,h));heights[k]=h
        q=round((h+50)/65*65535);rest.extend((q>>8,q&255,0,255))
        paint.extend((round((33+6*soft[k])*mask[k]/50*255),round(-WATER/50*255),0,round(soft[k]*255)))
        if mask[k]>.5:
            area+=1;wet+=h<WATER;low=min(low,h);high=max(high,h)
    png(OUT/'world-rest.png',rest);png(OUT/'soil-paint.png',paint)
    # Lag RMS measures whether the previous 2.6 m height repetition survives. This is a numeric guard only.
    lag=round(260/SIZE*N);differences=[]
    for j in range(195,317):
        for i in range(80,430-lag):differences.append((heights[j*N+i]-heights[j*N+i+lag])**2)
    report=dict(resolution=N,size_cm=SIZE,origin_cm=[ORIGIN,ORIGIN],water_level_cm=WATER,
        height_range_cm=[low,high],wet_area_m2=wet*(SIZE/N)**2/10000,
        repeat_260cm_rms=math.sqrt(sum(differences)/len(differences)),
        status='authoring data only; visual and driving acceptance pending',seed=7139)
    assert low>-33 and high<=12 and report['repeat_260cm_rms']>2 and 5<report['wet_area_m2']<70,report
    (OUT/'authoring-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':build()
