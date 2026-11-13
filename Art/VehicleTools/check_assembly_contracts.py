import bpy,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root));import assembly_contracts as ac
args=sys.argv[sys.argv.index('--')+1:];required='--require-pass' in args;args=[v for v in args if v!='--require-pass'];folder=Path(args[0]);bpy.ops.wm.open_mainfile(filepath=str(folder/'Crafted_Utility_Detailed.blend'))
report=ac.inspect(json.loads((folder/'shape-spec.json').read_text()))
target=Path(args[1]) if len(args)>1 else folder/'assembly-contracts.json'
target.write_text(json.dumps(report,indent=2));print(json.dumps({k:v.get('passed') for k,v in report.items() if isinstance(v,dict)},indent=2))
if required:assert report['passed'],'See assembly-contracts.json for failed contracts'
