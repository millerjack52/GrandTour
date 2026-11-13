"""Original numeric authoring maps for the playable lab (centimetres)."""
import json
from pathlib import Path
from make_mud_proving_ground import N, SIZE, ORIGIN, noise, smooth, png

OUT=Path(__file__).resolve().parents[2]/'Art/Export/MudLab'

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    rest=bytearray();paint=bytearray()
    for j in range(N):
        y=ORIGIN+(j+.5)*SIZE/N
        for i in range(N):
            x=ORIGIN+(i+.5)*SIZE/N
            lane=min(range(3),key=lambda k:abs(y-(k-1)*850))
            across=abs(y-(lane-1)*850)
            cover=smooth(-850,-620,x)*(1-smooth(1000,1275,x))*(1-smooth(235,340,across))
            depth=(12,38,36)[lane]*cover
            softness=(.28,.90,.72)[lane]*cover
            rough=(noise(x/85,y/70,91)-.5)*3+(noise(x/17,y/21,93)-.5)*1.3
            height=(1.5+rough)*cover
            if lane==1:
                height=(1+rough*1.6)*cover
            if lane==2:
                bowl=smooth(-650,-250,x)*(1-smooth(750,1080,x))*(1-smooth(180,310,across))
                height=(rough-21*bowl)*cover
            height=max(-depth,min(12,height))
            q=round((height+50)/65*65535)
            rest.extend((q>>8,q&255,0,255))
            paint.extend((round(depth/50*255),26,0,round(softness*255)))
    png(OUT/'world-rest.png',rest);png(OUT/'soil-paint.png',paint)
    (OUT/'authoring.json').write_text(json.dumps(dict(size_cm=SIZE,origin_cm=ORIGIN,
        lanes=[dict(name=n,y_cm=y,layer_cm=d,softness=s) for n,y,d,s in
        [('Firm soil',-850,12,.28),('Soft mud',0,38,.9),('Standing water',850,36,.72)]],
        water_level_cm=-26*50/255,water_bed_cm=-21),indent=2))
    print('MudLab numeric maps generated')

if __name__=='__main__':build()
