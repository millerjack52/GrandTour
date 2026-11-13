"""Explicit, recorded migration of static-fit interfaces for movement review.

Run only on a verified fresh cockpit-v04 derivative. Does not redefine styling.
"""
import bpy,math
def migrate():
    changed=[]
    for o in bpy.data.objects:
        if o.type!='MESH':continue
        reason=None
        if o.name=='Underbody mass':
            for v in o.data.vertices:v.co.x*=2/3
            reason='Narrow placeholder chassis to 0.8 m for steering tyre clearance'
        elif 'fixed door jamb' in o.name:
            for v in o.data.vertices:v.co.x-=math.copysign(.055,v.co.x)
            reason='Set fixed jamb backing 55 mm inward behind moving door returns'
        elif 'wheelhouse back panel' in o.name or 'wheelhouse liner' in o.name:
            for v in o.data.vertices:
                if abs(v.co.x+.210)<1e-5:v.co.x=-.380
            reason='Move inner front wheelhouse plane from X ±0.57 to ±0.40 m; keep visible arch unchanged'
        elif 'lower drip lip' in o.name and min(v.co.y for v in o.data.vertices)<-.7:
            for v in o.data.vertices:
                if v.co.y<-.7:v.co.y+=.045
            reason='Shorten front drip lip 45 mm at windscreen end'
        elif any(c.get('kind')=='window' and 'rear window cassette' in c.name for c in o.users_collection):
            for v in o.data.vertices:v.co.y=.230+(v.co.y-.230)*(.940-.006)/.940
            reason='Add 6 mm clearance at rear door window trailing edge for its initial opening arc'
        elif any(c.name=='Cabin | dashboard carrier' for c in o.users_collection):
            edited=False
            for v in o.data.vertices:
                if abs(v.co.x)>.620:
                    v.co.x=math.copysign(.620+(abs(v.co.x)-.620)*(.750-.620)/(.813-.620),v.co.x);edited=True
            if edited:reason='Inset dashboard end zones and their vents to X ±0.75 m, clear of moving door trim'
        if reason:
            o.data.update();o['articulation_fit_change']=reason;changed.append(dict(object=o.name,reason=reason,collections=[c.name for c in o.users_collection]))
    bpy.context.view_layer.update();return changed
