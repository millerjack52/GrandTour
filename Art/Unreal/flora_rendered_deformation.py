"""Measure actual rendered ground depth, excluding vehicle, water and tread overlays."""
import unreal as u,json,math
from pathlib import Path
from make_mud_road import centre
O=Path('C:/GrandTour/Art/Export/FloraDrive')

class RenderedDeformation:
    def __init__(self,world):
        self.world=world;self.frames={};self.n=128
        visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
        self.mesh=next(c for c in visual.get_components_by_class(u.ProceduralMeshComponent) if c.get_name()=='NativeVisualGrid')
        self.material=self.mesh.get_material(0)
        self.actor=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.SceneCapture2D,u.Transform(location=u.Vector(0,centre(0),1000)),'FloraDrive_DepthCheck')
        self.actor.set_actor_rotation(u.Rotator(pitch=-90),False)
        self.cc=self.actor.capture_component2d
        self.rt=u.RenderingLibrary.create_render_target2d(world,self.n,self.n,u.TextureRenderTargetFormat.RTF_RGBA32F)
        for k,v in dict(texture_target=self.rt,capture_every_frame=False,capture_on_movement=False,projection_type=u.CameraProjectionMode.ORTHOGRAPHIC,ortho_width=1200.,capture_source=u.SceneCaptureSource.SCS_SCENE_DEPTH,primitive_render_mode=u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST).items():self.cc.set_editor_property(k,v)
        self.cc.show_only_component(self.mesh)

    def measure(self,label):
        self.cc.capture_scene();yield .5
        pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(self.world,self.rt,0,0,self.n,self.n,False)
        values=[p.r for p in pixels];assert len(values)==self.n*self.n
        assert all(math.isfinite(v) and 500<v<1500 for v in values),'Depth capture did not see the ground grid'
        self.frames[label]=values
        (O/'rendered-ground-depth.json').write_text(json.dumps(dict(resolution=self.n,width_cm=1200,centre=[0,centre(0)],frames=self.frames)))

    def baseline(self):
        window=self.material.get_vector_parameter_value('MR_VisualWindow')
        try:
            self.material.set_vector_parameter_value('MR_VisualWindow',u.LinearColor(-76000,-43200,2400,600))
            yield .3;yield from self.measure('old_remote_window')
        finally:self.material.set_vector_parameter_value('MR_VisualWindow',window)
        yield .3;yield from self.measure('before_drive')
        delta=max(abs(a-b) for a,b in zip(self.frames['old_remote_window'],self.frames['before_drive']))
        assert delta>5,'Local visual-window fix did not move rendered vertices'
        return delta

    def result(self):
        before=self.frames['before_drive'];after=self.frames['after_drive']
        changes=[b-a for a,b in zip(before,after)]
        result=dict(max_rendered_depression_cm=max(changes),max_rendered_raise_cm=-min(changes),pixels_changed_over_1cm=sum(abs(x)>1 for x in changes),old_window_suppressed_displacement_cm=max(abs(a-b) for a,b in zip(self.frames['old_remote_window'],before)),scope='Actual SceneDepth of NativeVisualGrid only; car, foliage, water and tread ribbons excluded',resolution=[self.n,self.n])
        assert result['max_rendered_depression_cm']>1 and result['pixels_changed_over_1cm']>25,'Driving did not visibly deform the rendered ground grid'
        return result
