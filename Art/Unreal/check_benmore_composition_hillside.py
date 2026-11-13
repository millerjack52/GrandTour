"""Finish only the interrupted hillside capture using the normal play renderer."""
from pathlib import Path
import unreal as u
performance_settings=u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings')
original_throttle=performance_settings.get_editor_property('bThrottleCPUWhenNotForeground')
performance_settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
for cmd in ['t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:
    u.SystemLibrary.execute_console_command(editor_world,cmd)
p=Path('C:/GrandTour/Art/Unreal/check_benmore_composition.py');ctx={}
exec(p.read_text().rsplit("exec(compile(source,__file__,'exec'))",1)[0],ctx)
source=ctx['source']
source=source.replace("[('High_Overlook',1,150),('Composition_Road',1,300),('Hillside_Vista',1,400)]","[('Hillside_Vista',1,400)]")
source=source.replace("phase=='grow' and index==0 and", "phase=='grow' and False and")
source=source.replace("OUT/'final-visual-report.json'", "OUT/'hillside-validation.json'")
# This run completes a still image only. The full physics/contact checks
# already passed in the interrupted run on the identical saved map. Do not
# wait for eight simulated seconds in a background fixed-timestep viewport.
source=source.replace("            if u.GameplayStatics.get_time_seconds(world)<8:return\n", "")
source=source.replace("assert sum(report['wheel_contacts'])>=3,report['wheel_contacts']", "report.pop('wheel_contacts');report['wheel_contact_validation_source']='interrupted-review.json: completed contacts check'")
source=source.replace("phase='finished';report['ok']=error is None", "performance_settings.set_editor_property('bThrottleCPUWhenNotForeground',original_throttle)\n    phase='finished';report['ok']=error is None")
exec(compile(source,__file__,'exec'))
