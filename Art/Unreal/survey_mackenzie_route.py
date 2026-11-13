"""Check metre-by-metre grades and continuity at the loop seam and shortcut joins."""
import unreal as u, json, math, traceback
from pathlib import Path
out=Path(u.Paths.project_dir()).resolve()/'Art/Export/MackenzieBlockout'
lib=u.GTVehicleSetupLibrary
report={'ok':False}
try:
    spec=u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
    rows=[]
    for name,alt in [('loop',False),('shortcut',True)]:
        length=lib.terrain_alt_route_length_m(spec,0) if alt else lib.terrain_route_length_m(spec)
        def point(arc): return lib.terrain_alt_route_point_cm(spec,0,arc)[0] if alt else lib.terrain_route_point_cm(spec,arc)[0]
        samples=[point(float(i)) for i in range(math.ceil(length))]+[point(length)]
        grades=[]
        for i,(a,b) in enumerate(zip(samples,samples[1:])):
            dist=math.hypot(b.x-a.x,b.y-a.y)
            if dist>.01: grades.append((abs(b.z-a.z)/dist*100,i))
        worst=max(grades)
        rows.append({'route':name,'samples':len(samples),'max_grade_percent':worst[0],'max_grade_arc_m':worst[1]})
        if not alt:
            a=point(length-.5);b=point(.5)
            rows[-1]['seam_height_change_cm_over_1m']=abs(a.z-b.z)
    report['routes']=rows
    assert rows[0]['max_grade_percent']<22,rows[0]
    assert rows[0]['seam_height_change_cm_over_1m']<22,rows[0]
    assert rows[1]['max_grade_percent']<25,rows[1]
    report['ok']=True
except Exception: report['error']=traceback.format_exc()
(out/'route-survey.json').write_text(json.dumps(report,indent=2));u.log('MACKENZIE_SURVEY '+json.dumps(report))
