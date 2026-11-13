"""Create a review-only camera sequence; nothing auto-plays in normal gameplay."""
import unreal as u,json
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();QA=ROOT/'Saved/LidarAuthoringQA/RS7'
DEST='/Game/GrandTour/ArtTests/LidarStudy/FirstSection'
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
seq=u.load_asset(DEST+'/LS_BankReview') or u.AssetToolsHelpers.get_asset_tools().create_asset('LS_BankReview',DEST,u.LevelSequence,u.LevelSequenceFactoryNew())
for b in seq.get_bindings():b.remove()
for t in seq.get_tracks():seq.remove_track(t)
seq.set_display_rate(u.FrameRate(24,1));seq.set_playback_start(0);seq.set_playback_end(288)
cam=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='RS7_MotionCamera'),None)
if not cam:cam=actors.spawn_actor_from_class(u.CameraActor,u.Vector());cam.set_actor_label('RS7_MotionCamera')
cc=cam.get_editor_property('camera_component');cc.set_field_of_view(68);cc.set_editor_property('constrain_aspect_ratio',False)
binding=seq.add_possessable(cam);track=binding.add_track(u.MovieScene3DTransformTrack);s=track.add_section();s.set_range(0,288)
channels=s.get_all_channels()
poses=[(0,(-47200,-32800,4650),(-45700,-31500,4920)),(36,(-47200,-32800,4650),(-45700,-31500,4920)),(120,(-46650,-32300,4660),(-45800,-31550,4910)),(168,(-46650,-32300,4660),(-45600,-31800,4890)),(252,(-47200,-32800,4650),(-45700,-31500,4920)),(287,(-47200,-32800,4650),(-45700,-31500,4920))]
for frame,pos,target in poses:
 rot=u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target))
 values=[*pos,rot.roll,rot.pitch,rot.yaw,1.,1.,1.]
 for c,v in zip(channels,values):c.add_key(u.FrameNumber(frame),v,interpolation=u.MovieSceneKeyInterpolation.LINEAR)
cut=seq.add_track(u.MovieSceneCameraCutTrack);cs=cut.add_section();cs.set_range(0,288)
bid=u.MovieSceneObjectBindingID();bid.set_editor_property('guid',binding.get_id());cs.set_camera_binding_id(bid)
assert u.EditorAssetLibrary.save_loaded_asset(seq)
(QA/'motion-sequence.json').write_text(json.dumps(dict(asset=DEST+'/LS_BankReview',fps=24,frames=288,poses=poses,auto_play=False),indent=2))
