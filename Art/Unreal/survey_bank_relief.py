import unreal as u,json,shutil,time,sys
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import lidar_first_section as section
qa=root/'Saved/LidarAuthoringQA/RS7Relief';qa.mkdir(exist_ok=True)
backup=root/'Saved/LidarAuthoringBackups'/('RS7Relief-'+str(time.time_ns()));backup.mkdir()
for rel in ['Content/GrandTour/ArtTests/LidarStudy/FirstSection/SM_RS7_BankSkin.uasset','Art/Unreal/lidar_section_surface.py','Art/Blender/build_lidar_bank_surface.py','Art/Export/LidarStudy/FirstSection/SM_RS7_BankSkin_LOD0.fbx','Art/Export/LidarStudy/FirstSection/bank-surface.blend']:
 source=root/rel
 if source.exists():shutil.copy2(source,backup/source.name)
anchors=[]
for a in section.actors.get_all_level_actors():
 if not a.get_actor_label().startswith(section.PREFIX):continue
 for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,True);p=t.translation
   radius=45 if 'Trees_' in a.get_actor_label() else 23 if 'Floor_' in a.get_actor_label() else 30
   anchors.append(dict(x=p.x,y=p.y,z=p.z,radius=radius,label=a.get_actor_label()))
report=dict(backup=str(backup),snapshot=section.snapshot(),outside=section.outside_snapshot(),anchors=anchors)
(qa/'survey.json').write_text(json.dumps(report,indent=2))
print('BANK_RELIEF_SURVEY',len(anchors))
