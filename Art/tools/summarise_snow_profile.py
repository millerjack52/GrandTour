"""Living mud LM4e: prints Art/Unreal/profile_live_snow.py's report (Art/profile_live_snow.ps1 calls it), and for a run other
than the before one, the pictures' mean absolute pixel difference against Art/Export/LiveSnowDrive/BeforeLM4e (0-255 per
channel, averaged over the picture's pixels and channels) with the share of pixels whose largest channel difference is over 8
and over 32, and a difference image (x4, *_diff.png) beside each after picture."""
import json,sys
from pathlib import Path
rep=json.loads(Path(sys.argv[1]).read_text())
tag=rep['tag']
print('LM4e profile [%s]: sections %s; viewport %s; play %s'%(tag,','.join(rep['sections']),rep.get('viewport_size'),rep.get('play_mode')))
if rep.get('error'):print('ERROR:',rep['error'][:2000])
if rep.get('profile_error'):print('PROFILE ERROR:',rep['profile_error'][:2000])
if rep.get('warm'):print('warm: shader workers idle after %s s (CPU %s -> %s s)'%(rep['warm'].get('waited_s'),rep['warm'].get('scw_cpu_start'),rep['warm'].get('scw_cpu_end')))
seen=[o for o in rep.get('others_seen',[]) if o[2]]
print('other processes during the run: %s'%('none seen at %d checks'%len(rep.get('others_seen',[])) if not seen else '; '.join('%s at %s s: %s'%(o[0],o[1],','.join(o[2])) for o in seen)))
p=rep.get('patch',{});print('patch: cell %s cm, %s cells, %s vertices, %s triangles, %s'%(p.get('cell_cm'),p.get('cells'),p.get('mesh_vertices'),p.get('mesh_triangles'),p.get('material')))
def f(v,n=2):
    return '-' if v is None else ('%.*f'%(n,v) if isinstance(v,(int,float)) else str(v))
def unit(c):
    if not c:return 'no csv'
    return 'frame %s game %s draw %s (busy %s) rhit %s gpu %s | base %s shadows %s lights %s lumen %s transl %s post %s vel %s | UI %s'%(
        f(c.get('FrameTime')),f(c.get('GameThreadTime')),f(c.get('RenderThreadTime')),f(c.get('render_busy_ms')),f(c.get('RHIThreadTime')),f(c.get('GPUTime')),
        f(c.get('base')),f(c.get('shadows')),f(c.get('lights')),f(c.get('lumen')),f(c.get('translucency')),f(c.get('post')),f(c.get('velocity')),f(c.get('Exclusive/GameThread/UI')))
def gt(x):
    return 'settle %s/%s/%s ms (frames %s, awake peak %s, swept %s a frame) upload %s/%s/%s ms (%s cells a frame) stamp %s/%s/%s ms clods %s/%s/%s ms'%(
        f(x.get('settle_mean_ms'),3),f(x.get('settle_p99_ms'),3),f(x.get('settle_max_ms'),2),x.get('settle_frames'),x.get('awake_peak'),f(x.get('swept_tiles_mean'),1),
        f(x.get('upload_mean_ms'),3),f(x.get('upload_p99_ms'),3),f(x.get('upload_max_ms'),2),f(x.get('upload_cells_mean'),0),
        f(x.get('stamp_mean_ms'),3),f(x.get('stamp_p99_ms'),3),f(x.get('stamp_max_ms'),2),f(x.get('clod_mean_ms'),3),f(x.get('clod_p99_ms'),3),f(x.get('clod_max_ms'),2))
for x in rep.get('passes',[]):
    s=x['seg'];k=lambda n:f((s.get(n) or {}).get('kmh'),1)
    print('%s: %s, end %s m in %s s; A %s B %s 35cm %s drift %s km/h; longest stop %s s; cell %s, %s tris, collapses %s, clods %s'%(x['label'],x['ended'],x['end_x_m'],x['elapsed_s'],k('A'),k('B'),k('35cm'),k('drift'),x['longest_stop_s'],x['cell_cm'],x['mesh_triangles'],x['collapses_fired'],x['clods_live']))
    print('   GT: '+gt(x))
    print('   CSV: '+unit(x.get('csv')))
    if x.get('csv_p99'):print('   CSV p99: '+', '.join('%s %s'%(a.split('/')[-1],f(b)) for a,b in x['csv_p99'].items()))
if rep.get('feel'):print('feel: '+', '.join('%s %s'%(a,b) for a,b in rep['feel'].items()))
if rep.get('record_events'):print('record: pass 1 %s events, pass 1+2 %s events, end CRC %s'%(rep.get('record_pass1_events'),rep['record_events'],rep.get('record_end_crc')))
r=rep.get('replay')
if r:
    print('replay %s (%s events, %s s; CRC %s): %s'%(r.get('record'),r.get('events'),r.get('seconds'),r.get('crc'),gt(r)))
    print('   CSV: '+unit(r.get('csv')))
    if r.get('csv_p99'):print('   CSV p99: '+', '.join('%s %s'%(a.split('/')[-1],f(b)) for a,b in r['csv_p99'].items()))
pc=rep.get('pics')
if pc:print('pictures: %s (%s events) replayed in %s s, CRC %s against the record end %s (match %s), settled %s; collapses %s, clods %s'%(pc.get('record'),pc.get('events'),pc.get('replay_s'),pc.get('crc_after_replay'),pc.get('record_end_crc'),pc.get('crc_match'),pc.get('crc_settled'),pc.get('collapses_fired'),pc.get('clods_live')))
COLS=['FrameTime','GameThreadTime','render_busy_ms','GPUTime','base','shadows','lights','lumen','translucency','post','velocity','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/Stamp','Exclusive/GameThread/UI']
SHORT={'FrameTime':'frame','GameThreadTime':'game','render_busy_ms':'draw','GPUTime':'gpu','GTMud/GameThread/Settle':'settle','GTMud/GameThread/Upload':'upload','GTMud/Stamp':'stamp','Exclusive/GameThread/UI':'UI'}
for x in rep.get('replays',[]):
    print('%s (%s s, CRC %s): %s'%(x['label'],x.get('seconds'),x.get('crc'),gt(x)))
for grp in ('stand_summary','toggles_summary','replay_ab_summary'):
    rows=rep.get(grp) or []
    if not rows:continue
    print('%s (B - A, ms; A = base, B = the feature toggled; runs A/B):'%grp)
    print('  %-8s %-26s'%('view','feature')+''.join('%9s'%SHORT.get(c,c)[:8] for c in COLS))
    for x in rows:
        d=x['B_minus_A'];print('  %-8s %-26s'%(x['view'],x['feature'])+''.join('%9s'%f(d.get(c),3) for c in COLS)+'  (%d/%d)'%tuple(x['runs']))
        if x.get('gt_A') and x.get('gt_B'):
            print('  %-35s GT A: %s'%('',', '.join('%s %s'%(k.replace('_ms',''),f(v,3)) for k,v in x['gt_A'].items())))
            print('  %-35s GT B: %s'%('',', '.join('%s %s'%(k.replace('_ms',''),f(v,3)) for k,v in x['gt_B'].items())))
    a=rows[0]['A'];print('  %-8s %-26s'%('','(A of the first row)')+''.join('%9s'%f(a.get(c),3) for c in COLS))
# The pictures against the before ones.
pics=[Path(q) for q in rep.get('images',[]) if not Path(q).stem.endswith('_Hidden') and not Path(q).stem.startswith('Snow_Seams')]
if tag!='before' and pics:
    try:
        import numpy as np
        from PIL import Image
        before=Path(sys.argv[1]).parent.parent/'BeforeLM4e'
        for q in pics:
            b=before/q.name
            if not q.exists() or not b.exists():print('picture %s: missing (%s, %s)'%(q.name,q.exists(),b.exists()));continue
            A=np.asarray(Image.open(b).convert('RGB')).astype(np.int16);B=np.asarray(Image.open(q).convert('RGB')).astype(np.int16)
            if A.shape!=B.shape:print('picture %s: sizes differ %s %s'%(q.name,A.shape,B.shape));continue
            D=np.abs(A-B);m=D.max(axis=2)
            line='picture %-22s whole frame: mean abs diff %.3f (0-255), pixels over 8 %.3f %%, over 32 %.3f %%, max %d'%(q.name,D.mean(),100.*(m>8).mean(),100.*(m>32).mean(),int(m.max()))
            # The patch's pixels: where the frame differs from its patch-hidden twin by over 24 in a channel (the sky's
            # drifting clouds and the HUD are outside it).
            hid=q.with_name(q.stem+'_Hidden.png')
            if hid.exists():
                Hd=np.asarray(Image.open(hid).convert('RGB')).astype(np.int16);mask=np.abs(B-Hd).max(axis=2)>24
                if mask.any():
                    Dm=D[mask];mm=m[mask]
                    line+='; the patch (%.1f %% of the frame): mean abs diff %.3f, pixels over 8 %.3f %%, over 32 %.3f %%, max %d'%(100.*mask.mean(),Dm.mean(),100.*(mm>8).mean(),100.*(mm>32).mean(),int(mm.max()))
            print(line)
            Image.fromarray(np.clip(D*4,0,255).astype(np.uint8)).save(q.with_name(q.stem+'_diff.png'))
    except Exception as e:print('picture compare failed:',e)
# LM4e cut 4, the seams: dark (brightest channel under 40) and sky-coloured (blue the brightest, 15 or more over red) pixels
# within 2 px of every chunk border in view, in Snow_Seams (the LODs by distance) and Snow_Seams_L0 (every chunk at LOD 0),
# and the two pictures' mean difference along the borders.
sm=(rep.get('pics') or {}).get('seams')
if sm:
    try:
        import numpy as np
        from PIL import Image
        folder=Path(rep['images'][0]).parent
        S=np.asarray(Image.open(folder/'Snow_Seams.png').convert('RGB')).astype(np.int16);S0=np.asarray(Image.open(folder/'Snow_Seams_L0.png').convert('RGB')).astype(np.int16)
        Hh,Ww=S.shape[:2];near=np.zeros((Hh,Ww),bool)
        for ln in sm['lines']:
            pts=ln['points']
            for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
                n=int(max(abs(x1-x0),abs(y1-y0)))+1
                for t in np.linspace(0.,1.,n):
                    x=int(round(x0+(x1-x0)*t));y=int(round(y0+(y1-y0)*t)+16)   # the PIE view is 1440x868 in the 1440x900 picture: 16 px down
                    if 0<=x<Ww and 0<=y<Hh:near[max(0,y-2):y+3,max(0,x-2):x+3]=True
        def count(I):
            mx=I.max(axis=2);dark=(mx<40)&near;sky=(I[...,2]>=I[...,0]+15)&(I[...,2]==mx)&near
            return int(dark.sum()),int(sky.sum())
        d1,s1=count(S);d0,s0=count(S0);diff=np.abs(S-S0).max(axis=2)[near]
        print('seams: %d chunks (LODs by distance %s, forced %s); %d pixels within 2 px of a chunk border: dark %d / sky %d with the LODs, dark %d / sky %d all at LOD 0; along the borders the two differ by %.2f on average, %.2f %% over 8, max %d'%(
            sm['chunks'],sm.get('lods_natural'),sm.get('lods_forced'),int(near.sum()),d1,s1,d0,s0,float(diff.mean()) if diff.size else 0.,100.*float((diff>8).mean()) if diff.size else 0.,int(diff.max()) if diff.size else 0))
    except Exception as e:print('seam check failed:',e)
