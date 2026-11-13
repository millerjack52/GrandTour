import csv,json,statistics
from pathlib import Path
csv.field_size_limit(10000000)
root=Path(__file__).resolve().parents[1]/'Art/Export/DenseTussock/performance'
runs=json.loads((root/'runs.json').read_text(encoding='utf-8-sig'))
if isinstance(runs,dict): runs=[runs]
excluded=[r for r in runs if not r.get('valid',True)]
runs=[r for r in runs if r.get('valid',True)]
metrics=['FrameTime','GPUTime','GameThreadTime','RenderThreadTime','GPU/Basepass','GPU/ShadowDepths','GPU/TemporalSuperResolution','GPUMem/LocalUsedMB','RHI/DrawCalls']
results=[]
def stats(values):
    v=sorted(values)
    return dict(median=round(statistics.median(v),4),p95=round(v[int(.95*(len(v)-1))],4),mean=round(statistics.mean(v),4))
for run in runs:
    with open(run['csv'],newline='',encoding='utf-8-sig') as f:
        rows=list(csv.reader(f))
    header=rows[0]; meta=rows[-1]
    assert meta[meta.index('[rhiname]')+1]=='D3D12'
    assert meta[meta.index('[systemresolution.resx]')+1]=='1440'
    assert meta[meta.index('[systemresolution.resy]')+1]=='900'
    thermal=any(int(s.split(',')[1].strip(),16)&0x60 for s in run['gpu_during'])
    item=dict(mode=run['mode'],view=run['view'],index=run['index'],thermal=thermal,metrics={})
    keys=metrics+[k for k in header if k.startswith('GPU/') and any(t in k.lower() for t in ['nanite','visbuffer','lumen','material'])]
    for key in dict.fromkeys(keys):
        if key not in header: continue
        col=header.index(key); values=[]
        for row in rows[run['sample_start']+1:run['sample_end']+1]:
            try: values.append(float(row[col]))
            except (IndexError,ValueError): pass
        if values:item['metrics'][key]=stats(values)
    results.append(item)
summary=[]
for view in ['Driver','Overview']:
    for mode in ['LOD','Voxel','Preserve']:
        selected=[r for r in results if r['mode']==mode and r['view']==view]
        if not selected:continue
        vals={key:{stat:round(statistics.mean(r['metrics'][key][stat] for r in selected),4) for stat in ['median','p95','mean']} for key in selected[0]['metrics']}
        summary.append(dict(view=view,mode=mode,runs=len(selected),metrics=vals))
complete=len(results)==12 and all(r['runs']==2 for r in summary) and len(summary)==6
report=dict(complete=complete,thermal_valid=not any(r['thermal'] for r in results),excluded=excluded,runs=results,summary=summary)
(root/'analysis.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(complete=complete,thermal_valid=report['thermal_valid'],summary=[dict(view=r['view'],mode=r['mode'],runs=r['runs'],gpu=r['metrics'].get('GPUTime'),frame=r['metrics'].get('FrameTime')) for r in summary]),indent=2))
