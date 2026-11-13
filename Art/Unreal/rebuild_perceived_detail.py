"""Reapply the accepted bounded asset pass after regenerating its source bakes."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
def run():
 import lidar_first_section as section
 import perceived_detail_materials as surface
 import perceived_tree_occlusion as canopy
 from repair_perceived_trial import prepare_materials
 accepted=json.loads((ROOT/'Art/Export/LidarStudy/FirstSection/PerceivedDetail/accepted.json').read_text())
 before=section.snapshot();outside=section.outside_snapshot()
 surface.apply(bool(accepted['parallax']))
 if accepted['tree_mode'] in ('ao-voxel','ao-preserve'):
  prepare_materials();canopy.run()
  if accepted['tree_mode']=='ao-preserve':
   mesh=u.load_asset(canopy.PD+'/SM_PD_Canopy_0');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
   ns=mesh.get_editor_property('nanite_settings');ns.shape_preservation=u.NaniteShapePreservation.PRESERVE_AREA;sm.set_nanite_settings(mesh,ns,True);u.EditorAssetLibrary.save_loaded_asset(mesh,False)
 import perceived_shadow_proxy as shadows
 shadows.run()
 assert section.snapshot()==before and section.outside_snapshot()==outside
 print('ACCEPTED_PERCEIVED_DETAIL_REBUILT')
