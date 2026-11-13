"""Independent GPU arithmetic fixture and fixed-camera temporal wave review."""
import unreal as u
import json,math
from pathlib import Path

def review(world,pc,report,capture,settle):
 root=Path(u.Paths.project_dir()).resolve()/'Art/Export/SiberianShowcase/WaveResearch'
 oracle=json.loads((root/'sampling-oracle.json').read_text())
 rt=u.RenderingLibrary.create_render_target2d(world,8,8,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
 m=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/Waves/M_SamplingOracle');assert m
 u.RenderingLibrary.draw_material_to_render_target(world,rt,m);yield from settle(2)
 actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
 error=max(abs(v-e) for c,p in zip(actual,oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p))
 report['wave_sampling_gpu_error']=error
 assert error<.005,('Native pixel wave oracle',error)
 rt=None;m=None;actual=[]
 report['optical_animation']={}
 for sheet in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet):
  mat=sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0)
  assert isinstance(mat,u.MaterialInstanceDynamic),sheet.get_actor_label()
  assert mat.get_scalar_parameter_value('AmbientReady')==1
  tex=mat.get_texture_parameter_value('AmbientTex');assert isinstance(tex,u.TextureRenderTarget2D)
  first=mat.get_scalar_parameter_value('AmbientClock')
  a=[u.RenderingLibrary.read_render_target_raw_pixel(world,tex,x,y,False) for x,y in [(100,150),(200,300),(350,400)]]
  yield from settle(.7)
  last=mat.get_scalar_parameter_value('AmbientClock')
  b=[u.RenderingLibrary.read_render_target_raw_pixel(world,tex,x,y,False) for x,y in [(100,150),(200,300),(350,400)]]
  diff=max(abs(v-w) for c,d in zip(a,b) for v,w in zip([c.r,c.g,c.b],[d.r,d.g,d.b]))
  assert last>first and math.isfinite(diff) and diff>1.e-4,(sheet.get_actor_label(),diff)
  report['optical_animation'][sheet.get_actor_label()]={'first_clock':first,'last_clock':last,'sample_change':diff}
  tex=None;mat=None
 sheet=None
 # Fixed cameras at calm ponds and flowing river. No vehicle movement is commanded.
 for name,pos,target in [('still',(-2850,-1800,180),(-2500,-900,30)),('river',(-1300,250,220),(-900,940,0)),('upper',(3200,3200,650),(3900,4400,150))]:
  for i in range(3):yield from capture('wave_'+name+'_'+str(i),pos,target)
