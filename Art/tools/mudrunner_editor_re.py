"""Read-only helpers for deeper inspection of the captured editor code."""
from pathlib import Path
import bisect, hashlib, json, re, struct, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Art/Tools/editor-re-python'))
import pefile, capstone
SOURCE=Path(r'C:/Program Files (x86)/Steam/steamapps/common/MudRunner - Editor')
OUT=ROOT/'Art/Export/MudRunnerEditorResearch'

class EditorCode:
    def __init__(self):
        baseline=json.loads((OUT/'binary-xrefs.json').read_text())
        assert hashlib.sha256((SOURCE/'MudRunnerEditor64.exe').read_bytes()).hexdigest()==baseline['sha256'],'Executable changed since capture investigation'
        self.pe=pefile.PE(str(SOURCE/'MudRunnerEditor64.exe'))
        self.base=self.pe.OPTIONAL_HEADER.ImageBase
        self.code=(OUT/'editor-loaded-text.bin').read_bytes()
        manifest=json.loads((OUT/'loaded-text.json').read_text())
        assert hashlib.sha256(self.code).hexdigest()==manifest['sha256']
        assert manifest['image_base']==self.base
        self.rva=manifest['rva']
        self.image=bytearray(self.pe.get_memory_mapped_image())
        self.image[self.rva:self.rva+len(self.code)]=self.code
        self.functions=sorted((self.base+e.struct.BeginAddress,self.base+e.struct.EndAddress) for e in self.pe.DIRECTORY_ENTRY_EXCEPTION)
        self.starts=[a for a,b in self.functions]
        self.imports={i.address:d.dll.decode()+':'+(i.name.decode() if i.name else str(i.ordinal)) for d in self.pe.DIRECTORY_ENTRY_IMPORT for i in d.imports}
        self.md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);self.md.skipdata=True
    def data(self,va,count):
        return bytes(self.image[va-self.base:va-self.base+count])
    def describe(self,va):
        if va in self.imports:return self.imports[va]
        if not self.base<=va<self.base+len(self.image):return ''
        data=self.data(va,300)
        s=data.split(b'\0')[0]
        if 2<=len(s)<300 and all(32<=c<127 for c in s):return repr(s.decode())
        return ''
    def bounds(self,va):
        k=bisect.bisect_right(self.starts,va)-1
        if k>=0 and va<self.functions[k][1]:return self.functions[k]
        raise ValueError(hex(va))
    def dump(self,start,end=None):
        if end is None:start,end=self.bounds(start)
        lines=[]
        for addr,size,mn,op in self.md.disasm_lite(self.data(start,end-start),start):
            note='';match=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',op)
            if match:
                dest=addr+size+int(match[2],16)*(1 if match[1]=='+' else -1)
                note=self.describe(dest)
                if mn in ['movss','addss','subss','mulss','divss','comiss','ucomiss'] and self.base+0x865000<=dest<self.base+0xa50000:
                    note='float='+repr(struct.unpack('<f',self.data(dest,4))[0])
            if mn=='call' and op.startswith('0x'):
                target=int(op,16)
                # Import jump thunks expose useful C runtime names.
                if self.data(target,2)==b'\xff\x25':
                    note=self.describe(target+6+struct.unpack('<i',self.data(target+2,4))[0])
            lines.append(f'{addr:016x} {mn:10s} {op}'+(' ; '+note if note else ''))
        out=OUT/'Deep';out.mkdir(exist_ok=True)
        path=out/f'{start:x}-{end:x}.asm';path.write_text('\n'.join(lines))
        return path
    def string_xrefs(self,terms):
        strings={}
        for m in re.finditer(rb'[ -~]{3,}\x00',self.image):
            s=m.group()[:-1].decode()
            if any(t.lower() in s.lower() for t in terms):strings[self.base+m.start()]=s
        refs=[]
        for addr,size,mn,op in self.md.disasm_lite(self.code,self.base+self.rva):
            match=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',op)
            if not match:continue
            dest=addr+size+int(match[2],16)*(1 if match[1]=='+' else -1)
            if dest in strings:
                try:bounds=[hex(a) for a in self.bounds(addr)]
                except ValueError:bounds=None
                refs.append(dict(at=hex(addr),string=strings[dest],function=bounds))
        return refs

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dump',nargs='+');p.add_argument('--strings',nargs='+');a=p.parse_args()
    c=EditorCode()
    if a.dump:print(c.dump(*[int(x,16) for x in a.dump]))
    if a.strings:
        r=c.string_xrefs(a.strings);(OUT/'Deep').mkdir(exist_ok=True)
        (OUT/'Deep/string-xrefs.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
