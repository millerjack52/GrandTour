"""Read-only comparison: installed reference recipe, brush budgets and mask channels."""
from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
from mudrunner_editor_re import EditorCode
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/MudRunnerEditorResearch/DistributionLayers';OUT.mkdir(exist_ok=True)
SOURCE=Path('C:/Program Files (x86)/Steam/steamapps/common/MudRunner - Editor/Media/prebuild')
recipe=SOURCE/'ref_road_muddy.xml';tree=ET.parse(recipe).getroot()
catalog=json.loads((OUT.parent/'Authoring/authoring-catalog.json').read_text())
brushes={b['tag']:b for group in catalog['brush_source']['tree']['children'] for b in group['children']}
assert hashlib.sha256(Path(catalog['brush_source']['path']).read_bytes()).hexdigest()==catalog['brush_source']['sha256']
report=dict(source=str(recipe),sha256=hashlib.sha256(recipe.read_bytes()).hexdigest(),area_m2=int(tree.attrib['NumBlocksX'])*int(tree.attrib['NumBlocksZ'])*256,layers=[])
for d in tree.find('Distributions'):
    p=SOURCE/'ref_road_muddy'/('dstr_'+d.attrib['Map']+'.tga');a=np.asarray(Image.open(p).convert('RGB'))/255.
    report['layers'].append(dict(settings=d.attrib,source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=list(a.shape[:2]),red_density=dict(mean=float(a[:,:,0].mean()),coverage_above_minimum=float((a[:,:,0]>.01).mean())),green_scale=dict(min=float(a[:,:,1].min()),max=float(a[:,:,1].max()),mean=float(a[:,:,1].mean())),brushes=[brushes[n] for n in d.attrib['Brushes'].split(',')]))
report['export_counts']={k:len(json.loads((ROOT/'Art/Export/NativeRoad'/(k+'.json')).read_text())) for k in ['trees','understory','debris','grass']}
report['export_counts_per_hectare']={k:v*10000/report['area_m2'] for k,v in report['export_counts'].items()}
c=EditorCode();report['native_variant_disassembly']=str(c.dump(0x140254010,0x14025426f))
# Execute the original inclusive comparison branches and final list selection.
# Water/footprint acceptance between them is deliberately outside this oracle.
from verify_mudrunner_editor_kernels import Harness,Random
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSI,UC_X86_REG_XMM14,UC_X86_REG_RIP,UC_X86_REG_R14,UC_X86_REG_EBX
import struct
h=Harness();uc=h.uc;cases=[];selection=[]
def stop_gate(uc,address,size,data):
    if address in [0x14025403d,0x140254215]:uc.emu_stop()
hook=uc.hook_add(UC_HOOK_CODE,stop_gate)
for lo,hi in [(0,.4),(.2,1),(.4,1),(.5,.5)]:
    for green in [-.001,0,.19999,.2,.39999,.4,.5,.50001,1,1.001]:
        h.reset_stack();uc.reg_write(UC_X86_REG_RSI,h.heap);h.f(h.heap+0x20,lo);h.f(h.heap+0x24,hi);h.xmm(UC_X86_REG_XMM14,green)
        uc.emu_start(0x140254023,h.stop,count=20)
        accepted=uc.reg_read(UC_X86_REG_RIP)==0x14025403d
        assert accepted==(np.float32(lo)<=np.float32(green)<=np.float32(hi))
        cases.append(dict(green=green,min=lo,max=hi,accepted=accepted))
uc.hook_del(hook)
for values in [[2],[1,4],[0,3,5,9]]:
    for seed in [0,1,962,123456]:
        h.reset_stack();h.rng=Random(seed);expected=Random(seed);uc.reg_write(UC_X86_REG_R14,h.heap);uc.reg_write(UC_X86_REG_EBX,len(values));uc.mem_write(h.heap,struct.pack('<'+'i'*len(values),*values))
        uc.emu_start(0x14025424a,0x14025425a,count=30)
        selected=uc.reg_read(UC_X86_REG_EBX);assert selected==values[(expected.rand()*len(values))>>15] and h.rng.calls==1
        selection.append(dict(values=values,seed=seed,selected=selected))
report['executed_native_range_cases']=cases;report['executed_native_selection_cases']=selection
report['boundary']='Independent density and scale maps and brush presets are source evidence. Generated noise, habitat masks, seed addressing, mesh substitutes, ground alignment and culling are Unreal adaptations. No source placements or density maps are imported.'
(OUT/'comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['layers','executed_native_range_cases','executed_native_selection_cases']},indent=2));print('Native range cases:',len(cases),'selection cases:',len(selection))
