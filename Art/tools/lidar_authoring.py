"""LiDAR design inputs. Importable in Unreal without NumPy; geometry uses NumPy lazily.

Original reference vectors/DEM are never written. Bed edits leave the water surface
and course fixed and blend only within the existing wet channel.
"""
from pathlib import Path
import copy
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Art/LidarAuthoring/edits.json'
COORDINATES = 'Unreal world centimetres; X east, Y south; NZVD2016 Z'


def validate(data):
    if data.get('version') != 1 or data.get('coordinate_system') != COORDINATES:
        raise ValueError('Unsupported design version or coordinate system')
    if not isinstance(data.get('paths'), list):
        raise ValueError('paths must be a list')
    ids, names = set(), set()
    for p in data['paths']:
        def number(key, lo, hi):
            v = p.get(key)
            if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not lo <= v <= hi:
                raise ValueError(f'{p.get("name", "Path")}: {key} must be {lo}..{hi}')
        if not isinstance(p.get('id'), str) or not p['id'] or p['id'] in ids:
            raise ValueError('Every path needs a unique id; export assigns one')
        if not isinstance(p.get('name'), str) or not p['name'].strip() or p['name'] in names:
            raise ValueError('Every path needs a unique nonempty name')
        if p['name'] in ('Riverside access', 'Pond field spur', 'Waimeamea Road', 'Waterhouse Road'):
            raise ValueError('Design name conflicts with an existing road')
        ids.add(p['id']); names.add(p['name'])
        if p.get('kind') not in ('mud_track', 'river_bed') or type(p.get('enabled')) is not bool:
            raise ValueError('Invalid kind or enabled flag')
        pts = p.get('points_cm')
        if not isinstance(pts, list) or not 2 <= len(pts) <= 512:
            raise ValueError('A path needs 2..512 control points')
        for q in pts:
            if len(q) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in q):
                raise ValueError('Control points must be finite XYZ centimetres')
            if max(abs(q[0]), abs(q[1])) > 180000 or not 0 <= q[2] <= 32768:
                raise ValueError('Control point outside the LiDAR authoring bounds')
        distances = [math.hypot(b[0]-a[0], b[1]-a[1])/100 for a,b in zip(pts, pts[1:])]
        if min(distances) < .25 or max(distances) > 150 or sum(distances) > 2000:
            raise ValueError('Use points 0.25..150 m apart and paths up to 2 km; split longer designs')
        number('width_m', 2, 20)
        if 'widths_m' in p:
            widths=p['widths_m']
            if not isinstance(widths,list) or len(widths)!=len(pts) or any(type(v) not in (int,float) or not math.isfinite(v) or not 2<=v<=20 for v in widths):
                raise ValueError('widths_m must contain one finite 2..20 m width per control point')
        number('max_cut_fill_m', .1, 3)
        if p['kind'] == 'river_bed':
            number('bank_blend_m', 1, 20)
            number('target_depth_m', .1, 1.5)
        else:
            number('mud_depth_cm', 1, 40); number('rut_depth_cm', 0, 20)
            number('firmness', 0, 1); number('wetness', 0, 1)
            number('relief_strength', 0, 2)
            for c in p.get('conditions', []):
                knot_length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))/100
                limits={'start_metres':(0,knot_length), 'end_metres':(0,knot_length), 'blend_metres':(1,100),
                        'mud_depth_cm':(0,100),'rut_depth_cm':(0,70),'wetness':(0,1),'firmness':(0,1),'grass_cover':(0,1),
                        'water_fill_cm':(0,40),'track_spread_cm':(0,300),'churn':(0,1),'crossing_tracks':(0,1),'breakup_cm':(0,20)}
                if 'basin_depth_cm' in c:limits['basin_depth_cm']=(0,100)
                if not isinstance(c.get('name'),str):raise ValueError('Condition needs a name')
                for key,(lo,hi) in limits.items():
                    v=c.get(key)
                    if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(f'Condition {key} must be {lo}..{hi}')
                if c['end_metres']<=c['start_metres']:raise ValueError('Condition end must follow start')
    return data


def load(path=DEFAULT):
    return validate(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def enabled(data, kind):
    return [p for p in data['paths'] if p['enabled'] and p['kind'] == kind]


def road_records(data):
    result = []
    for p in enabled(data, 'mud_track'):
        points = p['points_cm']
        # Linear resampling preserves the owner's polygon; no automatic bench relocation.
        xyz = []; widths=[]; control_widths=p.get('widths_m',[p['width_m']]*len(points))
        for j,(a,b) in enumerate(zip(points, points[1:])):
            count = max(1, math.ceil(math.dist(a[:2], b[:2])/500))
            xyz.extend([[a[k]+(b[k]-a[k])*i/count for k in range(3)] for i in range(count)])
            widths.extend([(control_widths[j]+(control_widths[j+1]-control_widths[j])*i/count)*100 for i in range(count)])
        xyz.append(points[-1][:])
        widths.append(control_widths[-1]*100)
        result.append(dict(name=p['name'], points=[q[:2] for q in xyz], elevations_cm=[q[2] for q in xyz],
                           widths_cm=widths,
                           length_m=sum(math.dist(a,b) for a,b in zip(points,points[1:]))/100,
                           authoring=copy.deepcopy(p), surface='mud'))
    return result


def nearest_profile(path, x, y):
    """Exact segment projection: no k-d tree vertex artefacts on ford edges."""
    import numpy as np
    x,y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    distance = np.full(x.shape, np.inf); elevation = np.zeros(x.shape); station = np.zeros(x.shape)
    total = 0.
    for a,b in zip(path['points_cm'], path['points_cm'][1:]):
        a=np.asarray(a)/100; b=np.asarray(b)/100; d=b-a; length=float(np.hypot(*d[:2]))
        t=np.clip(((x-a[0])*d[0]+(y-a[1])*d[1])/(length*length),0,1)
        dd=np.hypot(x-a[0]-t*d[0], y-a[1]-t*d[1]); choose=dd<distance
        elevation=np.where(choose,a[2]+t*d[2],elevation)
        station=np.where(choose,total+t*length,station); distance=np.minimum(distance,dd); total+=length
    return distance,elevation,station,total


def smooth(lo, hi, x):
    import numpy as np
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)


def track_mask(data,x,y,base_mask):
    """Width-aware clearing for narrow tracks, without the old gravel-road raster blur."""
    import numpy as np
    result=np.array(base_mask,copy=True)
    for p in enabled(data,'mud_track'):
        pts=np.array(p['points_cm'])[:,:2]/100
        widths=np.array(p.get('widths_m',[p['width_m']]*len(pts)));radius=widths.max()/2+.6
        use=(x>=pts[:,0].min()-radius)&(x<=pts[:,0].max()+radius)&(y>=pts[:,1].min()-radius)&(y<=pts[:,1].max()+radius)
        if not use.any():continue
        d,_,station,_=nearest_profile(p,x[use],y[use])
        knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
        half=np.interp(station,knots,widths)/2;radius=half+.6
        result[use]=np.maximum(result[use],1-smooth(half,radius,d))
    return result


def sculpt_beds(data, x, y, base, water_surface, original_bed):
    """Metres in/out. water_surface is NaN outside the original channel corridor.

    End and shore fades protect joins. Overlapping bed footprints are rejected,
    so changing the order of edits cannot change the result.
    """
    import numpy as np
    x,y,base,water_surface,original_bed=np.broadcast_arrays(x,y,base,water_surface,original_bed)
    result=np.array(base,dtype=float,copy=True); used=np.zeros(base.shape,bool)
    for p in enabled(data,'river_bed'):
        pts=np.array(p['points_cm'])[:,:2]/100; radius=p['width_m']/2+p['bank_blend_m']
        candidates=(x>=pts[:,0].min()-radius)&(x<=pts[:,0].max()+radius)&(y>=pts[:,1].min()-radius)&(y<=pts[:,1].max()+radius)
        if not candidates.any(): continue
        d,z,s,length=nearest_profile(p,x[candidates],y[candidates]); half=p['width_m']/2
        weight=(1-smooth(half,radius,d))*smooth(0,min(5,length/3),s)*smooth(0,min(5,length/3),length-s)
        surf=water_surface[candidates]; original=original_bed[candidates]
        weight*=np.where(np.isfinite(surf),smooth(.015,.30,surf-original),0)
        active=weight>1e-8
        if not active.any():raise ValueError(f'{p["name"]}: no wet river bed in the edit footprint')
        if np.any(used[candidates]&active): raise ValueError('River bed edits overlap: combine them into one path')
        depth=surf-z
        core=weight>.9
        if np.any(core&((depth<.10)|(depth>1.5))):
            raise ValueError(f'{p["name"]}: bed must stay 0.10..1.50 m below the unchanged water surface')
        delta=(z-base[candidates])*weight
        if np.any(np.abs(delta)>p['max_cut_fill_m']+.01):
            raise ValueError(f'{p["name"]}: bed exceeds Maximum Cut Fill; inspect the profile')
        result[candidates]+=np.where(active,delta,0)
        used[candidates]|=active
    return result,used


def input_files(folder):
    """Everything Install consumes, including river-only changes and terrain edits."""
    folder=Path(folder)
    names=['roads.json','sites.json','trees.json','understory.json','hardware.json','paint.png','style.png','clay.png','macro.png','rest.png','prepare.json']
    names+=['authoring-height.r16','authoring-report.json','logging_trial.json']
    names+=['river-repair.json','river-detail.png']
    for name in ('River','AccessPond','MappedPond'):
        names += [name+suffix for suffix in ('.obj','-domain.bin','-flow.png','-shore.png')]
    return [folder/n for n in names if (folder/n).exists()]


def inputs_digest(folder):
    h=hashlib.sha256()
    for p in input_files(folder):
        h.update(p.name.encode()+b'\0'); h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Validate saved LiDAR track/bed designs without opening Unreal')
    parser.add_argument('--edits', type=Path, default=DEFAULT)
    args=parser.parse_args(); design=load(args.edits)
    print(json.dumps(dict(ok=True,digest=digest(design),paths=len(design['paths']),
                          mud_tracks=len(enabled(design,'mud_track')),river_beds=len(enabled(design,'river_bed'))),indent=2))
