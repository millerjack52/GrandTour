"""Read-only x64 PE string cross-references and bounded function disassembly."""
from pathlib import Path
import sys,re,json,hashlib,bisect,struct
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Art/Tools/editor-re-python'))
import pefile,capstone
SOURCE=Path(r'C:/Program Files (x86)/Steam/steamapps/common/MudRunner - Editor/MudRunnerEditor64.exe')
OUT=ROOT/'Art/Export/MudRunnerEditorResearch';OUT.mkdir(parents=True,exist_ok=True)
blob=SOURCE.read_bytes();pe=pefile.PE(data=blob);base=pe.OPTIONAL_HEADER.ImageBase
terms=['PlantsPerBlock','FlatThreshold','MinMapScale','MaxMapScale','LinkedGrassBrush','UpdatePlants (distributions)','Failed process distribution','Failed process grass distribution','OverlayFlattenHM','OverlayHMOffset','Prebuild/HeightmapOffset','ApplyMaterials','IgnoreOverlays','IgnoreMud','IgnoreWater','ScaleRandom','PlaceOnlyInWater']
strings={}
for m in re.finditer(rb'[ -~]{5,}',blob):
 s=m.group().decode()
 if any(t in s for t in terms):strings[base+pe.get_rva_from_offset(m.start())]=s
functions=sorted((base+f.struct.BeginAddress,base+f.struct.EndAddress) for f in pe.DIRECTORY_ENTRY_EXCEPTION);starts=[a for a,b in functions]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.skipdata=True
refs=[]
for sec in pe.sections:
 if not sec.Characteristics&0x20000000:continue
 # Steam's on-disk code differs from normally loaded executable code. Analyse
 # the read-only .text capture from the legitimate running editor when present.
 code=sec.get_data()
 if sec.Name.startswith(b'.text') and (OUT/'editor-loaded-text.bin').exists():code=(OUT/'editor-loaded-text.bin').read_bytes()
 for addr,size,mn,op in md.disasm_lite(code,base+sec.VirtualAddress):
  match=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',op)
  if not match:continue
  dest=addr+size+int(match[2],16)*(1 if match[1]=='+' else -1)
  if dest not in strings:continue
  k=bisect.bisect_right(starts,addr)-1;fn=functions[k] if k>=0 and addr<functions[k][1] else None
  refs.append(dict(at=hex(addr),instruction=mn+' '+op,target=hex(dest),string=strings[dest],function=[hex(v) for v in fn] if fn else None))
(OUT/'binary-xrefs.json').write_text(json.dumps(dict(source=str(SOURCE),sha256=hashlib.sha256(blob).hexdigest(),image_base=hex(base),strings={hex(a):s for a,s in strings.items()},xrefs=refs),indent=2))
imports={i.address:d.dll.decode()+':'+(i.name.decode() if i.name else str(i.ordinal)) for d in pe.DIRECTORY_ENTRY_IMPORT for i in d.imports}
selected=set(tuple(r['function']) for r in refs if r['function'])
# Resolved direct call targets: candidate pattern builder, plant block worker,
# and the parallel grass wrapper. Preserve these on every rerun too.
for address in [0x140252ad0,0x140253310,0x14021b790]:
 k=bisect.bisect_right(starts,address)-1
 if k>=0 and functions[k][0]==address:selected.add(tuple(hex(v) for v in functions[k]))
constants=[]
for fn in sorted(selected):
 a,b=map(lambda s:int(s,16),fn);offset=pe.get_offset_from_rva(a-base);lines=[];code=blob[offset:offset+b-a]
 if (OUT/'editor-loaded-text.bin').exists():
  textsection=pe.sections[0];capture=(OUT/'editor-loaded-text.bin').read_bytes();offset=a-base-textsection.VirtualAddress
  if 0<=offset<len(capture):code=capture[offset:offset+b-a]
 for addr,size,mn,op in md.disasm_lite(code,a):
  note=next((' ; '+r['string'] for r in refs if int(r['at'],16)==addr),'')
  match=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',op)
  if match:
   dest=addr+size+int(match[2],16)*(1 if match[1]=='+' else -1)
   if dest in imports:note+=' ; '+imports[dest]
   if mn in ['movss','addss','subss','mulss','divss','comiss','ucomiss'] and 0x140865000<=dest<0x140a50000:
    value=struct.unpack('<f',pe.get_data(dest-base,4))[0]
    note+=' ; float='+str(value)
    constants.append(dict(at=hex(addr),target=hex(dest),value=value))
  lines.append(f'{addr:016x} {mn:10s} {op}{note}')
 (OUT/('function_'+hex(a)+'.asm')).write_text('\n'.join(lines))
(OUT/'float-constants.json').write_text(json.dumps(constants,indent=2))
print(json.dumps(dict(xrefs=len(refs),functions=len(selected),float_constants=len(constants))))
