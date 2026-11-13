"""Actual PIE views and bounded stationary GPU spot checks for the new section."""
from pathlib import Path
import sys,json,hashlib
root=Path('C:/GrandTour');sys.path.insert(0,str(root/'Art/Unreal'))
source=root/'Art/Unreal/capture_flora_drive.py';text=source.read_text()
replacements={
"OUT=ROOT/'Art/Export/FloraDrive'":"OUT=ROOT/'Art/Export/FloraTrail'",
"LEVEL='/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive'":"LEVEL='/Game/GrandTour/ArtTests/FloraTrail/L_FloraTrail'",
'from flora_trial_evidence import audited_fingerprint':'from flora_trail_evidence import audited_fingerprint',
"(OUT/'road-relief-authoring.json')":"(ROOT/'Art/Export/FloraDrive/road-relief-authoring.json')",
"'/Game/GrandTour/ArtTests/FloraDrive/MPC_ForestGround'":"'/Game/GrandTour/ArtTests/FloraTrail/Controls/MPC_ForestGround'",
"yield 3\n    u.GTPlayWindowLibrary":"yield 3\n    for cmd in json.loads((ROOT/'Art/flora_trail_settings.json').read_text())['console']:u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),cmd)\n    u.GTPlayWindowLibrary",
}
for old,new in replacements.items():
 assert old in text,old;text=text.replace(old,new)
text=text.replace('    u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12', "    yield 10\n    from flora_trail_asset_audit import verify\n    report['asset_audit']=verify(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())\n    u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12")
# Drain render commands on the game thread before releasing PIE resources.
text=text.replace("    u.EditorLevelLibrary.editor_end_play();yield 4", "    console('r.RHIThread.Enable 0');yield 2\n    u.EditorLevelLibrary.editor_end_play();yield 4")
# Keep the meaningful terrain, water and timing checks. The old texture-debug
# sweep is already covered in its own study; this run reviews the new composition.
a=text.index('        if checkpoint==2:');b=text.index('    authored=',a);text=text[:a]+text[b:]
a=text.index('    # Isolate the normal');b=text.index('    pond_bed=',a);text=text[:a]+text[b:]
(root/'Art/Export/FloraTrail/capture-source.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':'Inherited scene cameras, road cross-sections, pond bed and stationary timings. Omitted old texture debug sweep.'},indent=2))
exec(compile(text,str(source),'exec'),globals())
