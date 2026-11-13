"""Debug only the owned Unreal smoke process; record second-chance AV stack addresses.
Windows SDK DEBUG_EVENT/AMD64 CONTEXT layouts. No game attachment or process injection.
"""
import ctypes as c,ctypes.wintypes as w,json,sys,struct,os
from pathlib import Path
k=c.WinDLL('kernel32',use_last_error=True);dbg=c.WinDLL('dbghelp',use_last_error=True)
PTR=c.c_void_p;U64=c.c_ulonglong;SIZE=c.c_size_t
class STARTUP(c.Structure):
 _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),('x',w.DWORD),('y',w.DWORD),('xs',w.DWORD),('ys',w.DWORD),('charsx',w.DWORD),('charsy',w.DWORD),('fill',w.DWORD),('flags',w.DWORD),('show',w.WORD),('reserved2size',w.WORD),('reserved2',PTR),('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
class PI(c.Structure):_fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
class EXCEPTION(c.Structure):_fields_=[('code',w.DWORD),('flags',w.DWORD),('record',PTR),('address',PTR),('count',w.DWORD),('information',U64*15)]
class EXINFO(c.Structure):_fields_=[('record',EXCEPTION),('first',w.DWORD)]
class CREATEINFO(c.Structure):_fields_=[('file',w.HANDLE),('process',w.HANDLE),('thread',w.HANDLE),('base',PTR),('debugOffset',w.DWORD),('debugSize',w.DWORD),('tls',PTR),('start',PTR),('name',PTR),('unicode',w.WORD)]
class LOADINFO(c.Structure):_fields_=[('file',w.HANDLE),('base',PTR),('debugOffset',w.DWORD),('debugSize',w.DWORD),('name',PTR),('unicode',w.WORD)]
class UNION(c.Union):_fields_=[('exception',EXINFO),('create',CREATEINFO),('load',LOADINFO),('exitCode',w.DWORD),('pad',c.c_byte*160)]
class EVENT(c.Structure):_fields_=[('code',w.DWORD),('pid',w.DWORD),('tid',w.DWORD),('data',UNION)]
def proto(dll,name,restype,args):
 f=getattr(dll,name);f.restype=restype;f.argtypes=args;return f
create=proto(k,'CreateProcessW',w.BOOL,[w.LPCWSTR,w.LPWSTR,PTR,PTR,w.BOOL,w.DWORD,PTR,w.LPCWSTR,c.POINTER(STARTUP),c.POINTER(PI)])
wait=proto(k,'WaitForDebugEvent',w.BOOL,[c.POINTER(EVENT),w.DWORD]);cont=proto(k,'ContinueDebugEvent',w.BOOL,[w.DWORD,w.DWORD,w.DWORD]);close=proto(k,'CloseHandle',w.BOOL,[w.HANDLE])
path_for=proto(k,'GetFinalPathNameByHandleW',w.DWORD,[w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD])
read=proto(k,'ReadProcessMemory',w.BOOL,[w.HANDLE,PTR,PTR,SIZE,c.POINTER(SIZE)])
open_thread=proto(k,'OpenThread',w.HANDLE,[w.DWORD,w.BOOL,w.DWORD]);context=proto(k,'GetThreadContext',w.BOOL,[w.HANDLE,PTR])
sym_init=proto(dbg,'SymInitializeW',w.BOOL,[w.HANDLE,w.LPCWSTR,w.BOOL]);sym_load=proto(dbg,'SymLoadModuleExW',U64,[w.HANDLE,w.HANDLE,w.LPCWSTR,w.LPCWSTR,U64,w.DWORD,PTR,w.DWORD])
sym_from=proto(dbg,'SymFromAddr',w.BOOL,[w.HANDLE,U64,c.POINTER(U64),PTR])
class SYMBOL(c.Structure):
 _fields_=[('size',w.ULONG),('type',w.ULONG),('reserved',U64*2),('index',w.ULONG),('symbolSize',w.ULONG),('modBase',U64),('flags',w.ULONG),('value',U64),('address',U64),('register',w.ULONG),('scope',w.ULONG),('tag',w.ULONG),('nameLen',w.ULONG),('maxNameLen',w.ULONG),('name',c.c_char*1)]
out=Path('C:/GrandTour/Art/Export/MudRoad/NativeStage4/debug-exit.json');log={'modules':{},'faults':[]};modules={};loaded_symbols=set();pi=PI();startup=STARTUP();startup.cb=c.sizeof(startup);startup.flags=1;startup.show=0
args=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'));command=c.create_unicode_buffer('"'+args['exe']+'" '+args['args'])
# Keep the ordinary process heap behavior while observing exceptions. Debug
# heap allocation/layout can otherwise hide a teardown lifetime race.
os.environ['_NO_DEBUG_HEAP']='1'
assert create(args['exe'],command,None,None,False,0x2|0x08000000,None,'C:/GrandTour',c.byref(startup),c.byref(pi)),c.get_last_error()
sym_init(pi.process,None,False)
def read_bytes(address,n):
 b=c.create_string_buffer(n);done=SIZE();return b.raw[:done.value] if not read(pi.process,PTR(address),b,n,c.byref(done)) else b.raw[:done.value]
def module_at(a):
 for base,(name,size) in modules.items():
  if base<=a<base+size:return base,name
 return None
def describe(a):
 m=module_at(a)
 if not m:return hex(a)
 base,name=m;result=Path(name).name+'+'+hex(a-base)
 if base not in loaded_symbols:
  sym_load(pi.process,None,name,None,base,modules[base][1],None,0);loaded_symbols.add(base)
 buf=c.create_string_buffer(c.sizeof(SYMBOL)+1024);s=SYMBOL.from_buffer(buf);s.size=c.sizeof(SYMBOL);s.maxNameLen=1024;disp=U64()
 if sym_from(pi.process,a,c.byref(disp),buf):result+=' '+c.string_at(c.addressof(buf)+SYMBOL.name.offset,s.nameLen).decode(errors='replace')+'+'+hex(disp.value)
 return result
exitcode=1
while True:
 ev=EVENT()
 if not wait(c.byref(ev),1000):continue
 status=0x10002
 if ev.code in (3,6):
  d=ev.data.create if ev.code==3 else ev.data.load
  if d.file:
   path=c.create_unicode_buffer(32768);path_for(d.file,path,len(path),0);name=path.value
   try:
    header=read_bytes(d.base,4096);pe=struct.unpack_from('<I',header,60)[0];size=struct.unpack_from('<I',header,pe+24+56)[0]
    modules[int(d.base)]=(name,size);log['modules'][hex(d.base)]=name
   except Exception:pass
   close(d.file)
 elif ev.code==1:
  e=ev.data.exception;r=e.record
  if r.code!=0x80000003:status=0x80010001
  if not e.first:
   t=open_thread(0x48,False,ev.tid);storage=c.create_string_buffer(1250);addr=(c.addressof(storage)+15)&~15;c.c_uint32.from_address(addr+48).value=0x10001f
   assert context(t,PTR(addr)),c.get_last_error();raw=c.string_at(addr,1232);rsp=struct.unpack_from('<Q',raw,152)[0];rip=struct.unpack_from('<Q',raw,248)[0]
   stack=read_bytes(rsp,4096);addresses=[struct.unpack_from('<Q',stack,i)[0] for i in range(0,len(stack)-7,8)]
   log['faults'].append(dict(code=hex(r.code),rip=describe(rip),address=hex(r.address),information=list(r.information)[:r.count],stack=[describe(a) for a in addresses if module_at(a)][:60]))
   out.write_text(json.dumps(log,indent=2));close(t)
 elif ev.code==5:
  exitcode=ev.data.exitCode;log['exit_code']=exitcode;out.write_text(json.dumps(log,indent=2));cont(ev.pid,ev.tid,status);break
 cont(ev.pid,ev.tid,status)
close(pi.thread);close(pi.process)
os._exit(c.c_int(exitcode).value)
