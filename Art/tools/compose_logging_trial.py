"""Compose LT3 on the owner's saved 714 m route; never relocate its control points."""
import bisect
import json
import math
from pathlib import Path
import random
import shutil
import time
import lidar_authoring as la


def compose(data):
    p=next(p for p in data['paths'] if p['id']=='fce56694-1591-406d-8ac5-75b330a90436')
    pts=p['points_cm'];knots=[0.]
    for a,b in zip(pts,pts[1:]):knots.append(knots[-1]+math.dist(a,b)/100)
    length=knots[-1]
    if not 700<length<730:raise ValueError('LT3 stations require the owner\'s saved 714 m route; review layout before composing another route')
    def width(s):
        keys=[(0,2.5),(55,2.6),(85,3.0),(115,2.8),(152,3.),(175,2.4),(192,2.3),
              (210,4.1),(225,3.0),(248,2.25),(268,2.5),(292,3.45),(314,2.6),
              (347,2.2),(375,2.6),(405,3.3),(434,3.5),(466,2.45),(499,2.7),
              (525,2.3),(550,3.75),(571,2.6),(598,2.3),(624,2.7),(642,3.1),
              (663,4.5),(680,3.8),(697,2.65),(length,2.8)]
        i=max(1,min(len(keys)-1,bisect.bisect_right([k[0] for k in keys],s)))
        a,b=keys[i-1:i+1];t=(s-a[0])/(b[0]-a[0]);return round(a[1]+(b[1]-a[1])*t,4)
    p.update(width_m=2.6,widths_m=[width(s) for s in knots],mud_depth_cm=5.,rut_depth_cm=0.,firmness=.9,wetness=.25,relief_strength=0.)
    conditions=[]
    def section(name,a,b,soil,firm,wet,rut=0,basin=0,fill=0,spread=0,churn=0,breakup=0,grass=.03,blend=5):
        conditions.append(dict(name=name,start_metres=float(a),end_metres=float(b),blend_metres=float(blend),mud_depth_cm=float(soil),firmness=float(firm),wetness=float(wet),rut_depth_cm=float(rut),basin_depth_cm=float(basin),water_fill_cm=float(fill),track_spread_cm=float(spread),churn=float(churn),crossing_tracks=0.,breakup_cm=float(breakup),grass_cover=float(grass)))
    section('Firm dirt through both crossings',0,164,5,.9,.25,breakup=1,blend=4)
    section('Solid mud on the climb',156,186,16,.7,.5,rut=2,breakup=2,blend=7)
    section('Mixed bush mud',178,length,26,.52,.68,rut=3,spread=12,churn=.12,breakup=3,blend=8)
    section('Firm narrow climb',228,270,13,.76,.42,rut=5,breakup=4,grass=.08,blend=7)
    section('Worn climbing grooves',319,368,24,.6,.58,rut=10,spread=18,churn=.22,breakup=5,blend=8)
    section('Dry crest and passing place',392,475,9,.85,.32,rut=1,breakup=2,grass=.14,blend=12)
    section('Uneven descent',480,530,30,.48,.75,rut=7,spread=35,churn=.3,breakup=7,blend=9)
    section('Broken rutted approach',590,642,34,.4,.8,rut=12,spread=22,churn=.35,breakup=6,blend=8)
    # Four surveyed route hollows, each with a different length, width and shape.
    section('First hollow - broad shallow churn',199,225,48,.27,.94,rut=5,basin=42,fill=20,spread=55,churn=.55,breakup=4,blend=5)
    section('Saddle hollow - flooded wheel channels',277,310,55,.24,.97,rut=17,basin=24,fill=16,spread=12,churn=.25,breakup=6,blend=7)
    section('Shelf hollow - broken wet pockets',537,568,43,.3,.92,rut=9,basin=28,fill=13,spread=42,churn=.6,breakup=9,blend=6)
    section('Deep gully - long yielding bog',646,686,70,.16,1,rut=22,basin=45,fill=32,spread=35,churn=.65,breakup=5,blend=8)
    p['conditions']=conditions
    logs=[]
    for i,(s,off,size,angle,mass) in enumerate([(239,.15,190,65,38),(335,-.5,260,-35,70),(485,.65,150,80,24),(579,-.25,220,42,52),(621,1.1,170,-65,32),(700,.2,240,70,60)]):
        logs.append(dict(kind='log',station_m=s,across_m=off,size_cm=size,yaw_offset=angle,mass_kg=mass,variant=i%2))
    rng=random.Random(191026);clumps=[]
    for center in (205,217,284,301,503,544,560,612,656,676):
        for j in range(rng.randint(2,4)):
            size=rng.uniform(26,44)
            station=round(center+rng.uniform(-2.5,2.5),2)
            # Loose crust sits on firm shoulders, above the yielding mineral floor.
            side=-1 if len(clumps)%2 else 1
            across=side*(width(station)*.5+rng.uniform(1.4,1.8))
            clumps.append(dict(kind='mud_clump',station_m=station,across_m=round(across,2),size_cm=round(size,1),yaw_offset=rng.randrange(360),mass_kg=round(3+(size/30)**3*7,1),variant=rng.randrange(6)%5))
    # A loose crest clod sits in the wheel corridor. The small saddle-shoulder
    # placement proved unstable after reload, so keep it on this firm surface.
    clumps[12].update(station_m=434.,across_m=.7,size_cm=38.,mass_kg=17.2,variant=0)
    manifest=dict(version='LT3',design_id=p['id'],length_m=length,control_points=len(pts),width_range_m=[min(p['widths_m']),max(p['widths_m'])],
                  natural_hollows_m=[214.,290.,552.,667.],obstacles=logs+clumps,
                  captures=[['Logging_dirt',35],['Logging_crossings',126],['Logging_first_hollow',213],['Logging_rutted_hollow',291],['Logging_dry_crest',430],['Logging_wet_pockets',551],['Logging_deep_gully',665],['Logging_log',239]])
    la.validate(data)
    return data,manifest


if __name__=='__main__':
    data,manifest=compose(la.load());backup=la.ROOT/'Saved/LidarAuthoringBackups'/('LT3-'+str(time.time_ns()))
    backup.mkdir(parents=True);shutil.copy2(la.DEFAULT,backup/'edits.json')
    for destination,value in [(la.DEFAULT,data),(la.DEFAULT.with_name('logging_trial.json'),manifest)]:
        tmp=destination.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');tmp.replace(destination)
    print(json.dumps({k:v for k,v in manifest.items() if k!='obstacles'},indent=2))
    print('Movable obstacles:',len(manifest['obstacles']))
