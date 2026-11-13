"""Summarize warm steady-state samples without merging duplicate CSV columns."""
import csv,json,statistics
csv.field_size_limit(10000000)
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'Art/Export/RoadFordStyle'
runs=json.loads((out/'grass-profile-runs.json').read_text(encoding='utf-8-sig'))
if isinstance(runs,dict): runs=[runs]
results=[]
keys=['FrameTime','GPUTime','GameThreadTime','RenderThreadTime','GPU/Basepass','GPU/Prepass','GPU/ShadowDepths','GPU/TemporalSuperResolution','RHI/PrimitivesDrawn','RHI/DrawCalls','GPUMem/LocalUsedMB','GPUSceneInstanceCount']
def summary(values):
    values=sorted(values)
    return dict(median=round(statistics.median(values),4),p95=round(values[int(.95*(len(values)-1))],4),mean=round(statistics.mean(values),4))
for run in runs:
    with open(run['csv'],newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f); header=next(reader); rows=list(reader)
    # Boot load, PSO compilation, first-frame cache updates and warm-up excluded.
    samples=rows[run.get('sample_start',1000):run.get('sample_end',2100)]
    metadata=rows[-1]
    def meta(key):
        tag='['+key+']'
        return metadata[metadata.index(tag)+1] if tag in metadata else None
    assert meta('systemresolution.resx')=='1440' and meta('systemresolution.resy')=='900'
    assert meta('rhiname')=='D3D12'
    telemetry=run.get('gpu_during',[])
    # NVIDIA bit 0x20 is software thermal slowdown; 0x40 hardware thermal.
    thermal=any(int(sample.split(',')[1].strip(),16)&0x60 for sample in telemetry)
    record=dict(mode=run['mode'],index=run['index'],sample_count=len(samples),metrics={},gpu_during=telemetry,thermal_slowdown_observed=thermal,resolution=[1440,900])
    for key in keys:
        if key not in header: continue
        col=header.index(key)
        values=[]
        for row in samples:
            try: values.append(float(row[col]))
            except (ValueError,IndexError): pass
        if values: record['metrics'][key]=summary(values)
    results.append(record)
delta={}
for key in keys:
    on=[r['metrics'][key]['median'] for r in results if r['mode']=='On' and key in r['metrics']]
    off=[r['metrics'][key]['median'] for r in results if r['mode']=='Off' and key in r['metrics']]
    if on and off:
        on_mean=[r['metrics'][key]['mean'] for r in results if r['mode']=='On' and key in r['metrics']]
        off_mean=[r['metrics'][key]['mean'] for r in results if r['mode']=='Off' and key in r['metrics']]
        delta[key]=dict(off_median=round(statistics.mean(off),4),on_median=round(statistics.mean(on),4),delta=round(statistics.mean(on)-statistics.mean(off),4),off_mean=round(statistics.mean(off_mean),4),on_mean=round(statistics.mean(on_mean),4))
report=dict(method='ABBA, 1440x900 verified in CSV metadata, 100% screen percentage, standalone offscreen DX12; stationary driver-height view; Kuwahara disabled in both; sample bounds in grass-profile-runs.json',thermal_valid=not any(r['thermal_slowdown_observed'] for r in results),runs=results,comparison=delta)
(out/'grass-performance.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(runs=len(results),comparison=delta),indent=2))
