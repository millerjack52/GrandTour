"""Repeatable camera-only sequences for bank parallax and tree transitions."""
import unreal as u,json
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();QA=ROOT/'Saved/LidarAuthoringQA/PerceivedDetail'
DEST='/Game/GrandTour/ArtTests/LidarStudy/FirstSection/PerceivedDetail'
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def build(name,label,poses):
 seq=u.load_asset(DEST+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.LevelSequence,u.LevelSequenceFactoryNew())
 for b in seq.get_bindings():b.remove()
 for t in seq.get_tracks():seq.remove_track(t)
 seq.set_display_rate(u.FrameRate(24,1));seq.set_playback_start(0);seq.set_playback_end(288)
 cam=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==label)
 binding=seq.add_possessable(cam);s=binding.add_track(u.MovieScene3DTransformTrack).add_section();s.set_range(0,288)
 channels=s.get_all_channels()
 for frame,pos,target in poses:
  rot=u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target))
  for c,v in zip(channels,[*pos,rot.roll,rot.pitch,rot.yaw,1.,1.,1.]):c.add_key(u.FrameNumber(frame),v,interpolation=u.MovieSceneKeyInterpolation.LINEAR)
 cs=seq.add_track(u.MovieSceneCameraCutTrack).add_section();cs.set_range(0,288)
 bid=u.MovieSceneObjectBindingID();bid.set_editor_property('guid',binding.get_id());cs.set_camera_binding_id(bid)
 assert u.EditorAssetLibrary.save_loaded_asset(seq)
 return dict(sequence=DEST+'/'+name,poses=poses)
def run():
 views=json.loads((QA/'cameras-proof.json').read_text());f=next(v for v in views if v['view']=='T01')
 camera=next(a for a in actors.get_all_level_actors() if a.get_name()==f['actor'])
 target=f['target'];pos=f['position'];near=[pos[k]+(target[k]-pos[k])*.45 for k in range(3)];near[2]=pos[2]
 rows=[build('LS_PD_Bank','PD_D01',[(0,(-46700,-32300,4770),(-46000,-31800,4820)),(24,(-46700,-32300,4770),(-46000,-31800,4820)),(132,(-46000,-32550,4770),(-46000,-31800,4820)),(240,(-46700,-32300,4770),(-46000,-31800,4820)),(287,(-46700,-32300,4770),(-46000,-31800,4820))]),
 build('LS_PD_Forest',camera.get_actor_label(),[(0,pos,target),(24,pos,target),(144,near,target),(260,pos,target),(287,pos,target)])]
 (QA/'motion-sequences.json').write_text(json.dumps(rows,indent=2))
