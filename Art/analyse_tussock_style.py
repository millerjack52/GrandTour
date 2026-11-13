import csv,json,statistics
from pathlib import Path
csv.field_size_limit(10000000)
root=Path(__file__).resolve().parents[1]/'Art/Export/TussockStyle/performance'
runs=json.loads((root/'runs.json').read_text(encoding='utf-8-sig'));results=[]
for run in runs:
    with open(run['csv'],newline='',encoding='utf-8-sig') as f:rows=list(csv.reader(f))
    header=rows[0];meta=rows[-1]
    assert meta[meta.index('[rhiname]')+1]=='D3D12'
    assert meta[meta.index('[systemresolution.resx]')+1]=='1440'
    assert meta[meta.index('[systemresolution.resy]')+1]=='900'
    item=dict(view=run['view'],thermal=any(int(v.split(',')[1].strip(),16)&0x60 for v in run['gpu_during']),metrics={})
    for key in ['GPUTime','FrameTime','GameThreadTime','RenderThreadTime','GPUMem/LocalUsedMB','RHI/DrawCalls']:
        if key not in header:continue
        idx=header.index(key);v=sorted(float(r[idx]) for r in rows[301:851])
        assert len(v)==550
        item['metrics'][key]=dict(median=statistics.median(v),p95=v[int(.95*(len(v)-1))])
    results.append(item)
report=dict(complete=len(results)==2,scope='Single stationary run per view; not a driving or incremental grass cost benchmark',runs=results)
(root/'analysis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
