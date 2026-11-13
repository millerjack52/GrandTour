"""Run the established driving regression on FloraTrail without weakening its gates."""
from pathlib import Path
import hashlib,json,sys
root=Path('C:/GrandTour');sys.path.insert(0,str(root/'Art/Unreal'))
source=root/'Art/Unreal/check_flora_drive.py';text=source.read_text()
replacements={
"OUT=ROOT/'Art/Export/FloraDrive'":"OUT=ROOT/'Art/Export/FloraTrail'",
"LEVEL='/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive'":"LEVEL='/Game/GrandTour/ArtTests/FloraTrail/L_FloraTrail'",
'from flora_trial_evidence import audited_fingerprint':'from flora_trail_evidence import audited_fingerprint',
"(OUT/'LidarMud/reference.json')":"(ROOT/'Art/Export/FloraDrive/LidarMud/reference.json')",
'from flora_rendered_deformation import RenderedDeformation':'import flora_rendered_deformation as rd; rd.O=OUT; RenderedDeformation=rd.RenderedDeformation',
"yield 3\n    u.GTPlayWindowLibrary":"yield 3\n    for cmd in json.loads((ROOT/'Art/flora_trail_settings.json').read_text())['console']:u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),cmd)\n    u.GTPlayWindowLibrary",
}
for old,new in replacements.items():
 assert text.count(old)==1,old;text=text.replace(old,new)
# Give the actual chase camera an unpaused update after the fixed rut camera.
text=text.replace("pc.set_view_target_with_blend(car,0);console('ShowHUD')", "pc.set_view_target_with_blend(car,0);console('ShowHUD');yield .3")
(root/'Art/Export/FloraTrail/check-source.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'substitutions':replacements},indent=2))
exec(compile(text,str(source),'exec'),globals())
