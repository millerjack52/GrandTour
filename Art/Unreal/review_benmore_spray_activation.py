"""Run existing rendered spray scenarios in a fresh, private output directory.

This verifies lazy Niagara activation with real GPU particles. It is a visual /
functional check using the original fixed-step harness, never an FPS benchmark.
The original scenario code is snapshotted and left unchanged.
"""
import unreal as u
import os,sys,types,json,hashlib
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_VISUAL_OUT']).resolve()
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
source_path=ROOT/'Art/Unreal/check_wheel_spray.py'
source=source_path.read_bytes()
(OUT/'scenario-source.py').write_bytes(source)
sys.path.insert(0,str(ROOT/'Art/Unreal'))
check=types.ModuleType('benmore_spray_activation_scenarios')
check.__file__=str(source_path)
exec(compile(source,str(source_path),'exec'),check.__dict__)
check.OUT=OUT
selected={'Spray_Mud_Spin','Spray_Mud_Spin_Greybox','Spray_Mud_Drive',
          'KillCheck','Spray_Gravel_Launch','Spray_Gravel_Wet'}
check.SCENARIOS=[sc for sc in check.SCENARIOS if sc[1] in selected]
assert {sc[1] for sc in check.SCENARIOS}==selected
check.report.update(timings_collected=False,source_sha256=hashlib.sha256(source).hexdigest(),
                    scope='Rendered lazy fine-spray activation / reactivation regression')
original_finish=check.finish


def finish(error=None):
    if error is None:
        try:
            assert u.SystemLibrary.get_console_variable_int_value('gt.Spray.LazyFineActivation')==1
            pics={p['name']:p['at_capture'] for p in check.report['pictures']}
            assert pics['Spray_Mud_Spin']['niagara_live']['MudDroplets']>0,'Mud did not activate'
            assert not any(pics['Spray_Mud_Spin_Greybox']['niagara_live'].values()),'Disabled art retained fine particles'
            assert pics['Spray_Mud_Drive']['niagara_live']['MudDroplets']>0,'Mud did not reactivate'
            assert pics['Spray_Gravel_Launch']['niagara_live']['GravelGrit']>0,'Gravel did not activate'
            assert pics['Spray_Gravel_Wet']['niagara_live']['GravelDust']==0,'Wet gravel emitted dust'
            check.report['activation_gate_passed']=True
        except Exception as e:
            error=str(e)
            check.report.update(ok=False,activation_gate_passed=False)
    original_finish(error)


check.finish=finish
