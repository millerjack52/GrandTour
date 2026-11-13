"""Exact material-only variants and timed standalone VP2 comparisons."""
import argparse,csv,hashlib,json,math,shutil,statistics,subprocess,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'Saved/LidarAuthoringQA/VP2Materials'
CAP=ROOT/'Saved/LidarAuthoringQA/RS7'
NAMES=['M_BankSurface','M_BankEarth','M_BankLeaf','M_BankGroundLeaf','PerceivedDetail/M_PD_Fern']
RELS=[Path('Content/GrandTour/ArtTests/LidarStudy/FirstSection')/(n+'.uasset') for n in NAMES]

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def idle(allow_game=False):
    names='UnrealEditor,UnrealEditor-Cmd,GrandTour'+('' if allow_game else ',FarCry6,Skate')
    p=subprocess.run(['powershell','-NoProfile','-Command',f"@(Get-Process {names} -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
    assert p.stdout.strip()=='0','Unreal or a game is active; no assets replaced'

def select(variant):
    idle(allow_game=True);backup=read(QA/'backup.json');folder=Path(backup['backup']) if variant=='baseline' else QA/'Variants'/variant
    for rel in RELS:
        assert (folder/rel).is_file(),str(folder/rel)
        # Refuse to overwrite an unrecorded subsequent material edit.
        known={backup['sha256'][str(rel)]}
        for path in (QA/'Variants').glob('*/'+rel.as_posix()):known.add(sha(path))
        assert sha(ROOT/rel) in known,'Unrecorded material edit: '+str(rel)
    for rel in RELS:shutil.copy2(folder/rel,ROOT/rel)
    (QA/'active.json').write_text(json.dumps(dict(variant=variant,sha256={str(r):sha(ROOT/r) for r in RELS}),indent=2))
    print('Selected',variant)

def telemetry(stop,path):
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['unix','temperature_c','graphics_mhz','power_w','used_mib','utilization_percent'])
        while not stop.is_set():
            p=subprocess.run(['nvidia-smi','--query-gpu=temperature.gpu,clocks.gr,power.draw,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True)
            if p.returncode==0:w.writerow([time.time(),*[v.strip() for v in p.stdout.strip().split(',')]]);f.flush()
            stop.wait(1)

def capture(label,motion=False,visual_only=False):
    idle(allow_game=visual_only);stop=threading.Event();thread=threading.Thread(target=telemetry,args=(stop,QA/(label+'-telemetry.csv')),daemon=True);thread.start()
    completed=False
    try:
        if motion:
            cmd=['powershell','-NoProfile','-File',str(ROOT/'Art/capture_lidar_section_motion.ps1'),'-Label',label,'-SampleCount','72','-Sequence','/Game/GrandTour/ArtTests/LidarStudy/FirstSection/PerceivedDetail/LS_PD_Bank','-OutputDirectory',str(Path('D:/GrandTourReviews/VP2Materials')/label)]
        else:
            cmd=['powershell','-NoProfile','-File',str(ROOT/'Art/capture_lidar_first_section.ps1'),'-Label',label,'-FramesPerView','600','-ViewsPath',str(QA/'cameras.json'),'-ExtraCommands','t.MaxFPS 0']
        subprocess.run(cmd,cwd=ROOT,check=True)
        # A competing game may have started after the initial guard.
        if not visual_only:idle()
        completed=True
    finally:
        stop.set();thread.join(timeout=10)
        (QA/(label+'-validity.json')).write_text(json.dumps(dict(completed=completed,performance_valid=completed and not visual_only and not motion,visual_only=visual_only,motion=motion),indent=2))
    if not motion:print(json.dumps(summarize(label),indent=2))

def summarize(label):
    r=read(CAP/('runtime-'+label+'.json'));assert r['exit_code']==0 and r['render_validation_passed']
    with open(r['csv'],newline='') as f:rows=list(csv.DictReader(f))
    keys=[k for k in rows[0] if k in ['GPUTime','FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GameThreadTime_CriticalPath','RenderThreadTime_CriticalPath','GPUMem/LocalUsedMB','GPUMem/LocalBudgetMB'] or (k.startswith('GPU/') and any(s in k.lower() for s in ['basepass','prepass','shadow','temporal','lumen']))]
    metrics={}
    for i,v in enumerate(r['views']):
        start=200+i*r['frames_per_view']
        # Exclude settling, screenshot at +280, and its following disturbance.
        samples=rows[start+150:start+265]+rows[start+350:start+580]
        metrics[v['view']]={}
        for key in keys:
            vals=sorted(float(x[key]) for x in samples if x.get(key))
            if vals:metrics[v['view']][key]=dict(median=statistics.median(vals),mean=statistics.mean(vals),p95=vals[math.ceil(.95*len(vals))-1],p99=vals[math.ceil(.99*len(vals))-1],max=max(vals),samples=len(vals))
    validity=read(QA/(label+'-validity.json')) if (QA/(label+'-validity.json')).exists() else dict(performance_valid=None,reason='Validity not recorded by this version; inspect run conditions.')
    result=dict(label=label,capture=r,metrics=metrics,screenshot_excluded=True,validity=validity)
    (QA/(label+'-summary.json')).write_text(json.dumps(result,indent=2))
    return {v: {k:round(m[k]['median'],3) for k in ['GPUTime','FrameTime'] if k in m} for v,m in metrics.items()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['select','capture','motion','summary','series']);p.add_argument('name');p.add_argument('--visual-only',action='store_true');a=p.parse_args()
    if a.operation=='select':select(a.name)
    elif a.operation in ('capture','motion'):capture(a.name,a.operation=='motion',a.visual_only)
    elif a.operation=='series':
        # b1 is the separately inspected first combined capture. Alternate
        # pair order thereafter; always leave the candidate installed.
        assert read(QA/'vp2-b1-summary.json')['validity']['performance_valid'] is True,'Capture a clean vp2-b1 run first'
        try:
            for variant,label in [('baseline','vp2-a1'),('baseline','vp2-a2'),('final','vp2-b2'),('final','vp2-b3'),('baseline','vp2-a3')]:
                select(variant);capture(label)
        finally:select('final')
    else:print(json.dumps(summarize(a.name),indent=2))
