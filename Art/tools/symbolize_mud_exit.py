"""Resolve captured addresses offline; names are nearest exports when PDBs are absent.
Large symbol displacements are not proof of the containing function. The probe
labels raw stack candidates separately from its unwind, as they can be non-code.
"""
from pathlib import Path
import re
scope={}
source=Path(__file__).with_name('debug_mud_exit.py').read_text()
exec(source.split("out=Path(")[0],scope)
c=scope['c'];k=scope['k'];proto=scope['proto'];w=scope['w'];U64=scope['U64'];SYMBOL=scope['SYMBOL']
process=proto(k,'GetCurrentProcess',w.HANDLE,[])();scope['sym_init'](process,None,False)
loaded=set();text=Path('C:/GrandTour/Art/Export/MudRoad/NativeStage4/exit-probe.txt').read_text();out=[]
if 'AV thread=' not in text:
 print('No access violation recorded.');raise SystemExit(0)
for line in text.split('AV thread=',1)[1].splitlines():
 m=re.match(r'([0-9A-F]+) ([0-9A-F]+) \+([0-9a-f]+) (.*)',line)
 if not m:continue
 address,base=int(m[1],16),int(m[2],16);path=m[4]
 if base not in loaded:
  scope['sym_load'](process,None,path,None,base,0,None,0);loaded.add(base)
 buf=c.create_string_buffer(c.sizeof(SYMBOL)+1024);s=SYMBOL.from_buffer(buf);s.size=c.sizeof(SYMBOL);s.maxNameLen=1024;disp=U64()
 symbol=''
 if scope['sym_from'](process,address,c.byref(disp),buf):symbol=c.string_at(c.addressof(buf)+SYMBOL.name.offset,s.nameLen).decode(errors='replace')+'+'+hex(disp.value)
 out.append(Path(path).name+'+'+m[3]+' '+symbol)
Path('C:/GrandTour/Art/Export/MudRoad/NativeStage4/exit-probe-symbols.txt').write_text('\n'.join(out))
print('\n'.join(out))
