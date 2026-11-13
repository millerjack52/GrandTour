"""Blender reference matching: locked cameras, editable guides and real surface probes.
This is a diagnostic/editing workbench, not an automatic image-to-3D converter.
"""
bl_info={'name':'Grand Tour Reference Fit','author':'Grand Tour','version':(0,1,0),'blender':(5,1,0),'category':'3D View'}
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

def observations():return json.loads(bpy.data.texts['FIT | observations.json'].as_string())
def choose_view(context,key):
    sc=context.scene;data=observations();spec=data[key];sc.camera=bpy.data.objects['FIT | '+key]
    sc.render.resolution_x=spec['width'];sc.render.resolution_y=spec['height'];sc.render.resolution_percentage=100
    for ob in bpy.data.collections['FIT | Traced targets'].objects:
        ob.hide_set(ob.get('fit_view')!=key)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'

def update_alpha(self,context):
    for ob in bpy.data.objects:
        if ob.type=='CAMERA' and ob.name.startswith('FIT | '):
            for bg in ob.data.background_images:bg.alpha=self.reference_alpha

def outline_samples(objects,ys):
    """Intersect evaluated triangle edges with Y planes and take upper silhouette.
    No artist specification or renderer framing is substituted for actual geometry.
    """
    dg=bpy.context.evaluated_depsgraph_get();segments=[]
    for ob in objects:
        eo=ob.evaluated_get(dg);me=eo.to_mesh();me.calc_loop_triangles()
        pts=[eo.matrix_world@v.co for v in me.vertices]
        for tri in me.loop_triangles:
            p=[pts[i] for i in tri.vertices]
            segments.extend([(p[0],p[1]),(p[1],p[2]),(p[2],p[0])])
        eo.to_mesh_clear()
    result=[]
    for y in ys:
        zz=[]
        for p,q in segments:
            if min(p.y,q.y)-1e-6<=y<=max(p.y,q.y)+1e-6:
                if abs(p.y-q.y)<1e-8:
                    if abs(p.y-y)<1e-6:zz.extend([p.z,q.z])
                else:
                    t=(y-p.y)/(q.y-p.y)
                    if -.000001<=t<=1.000001:zz.append(p.z+t*(q.z-p.z))
        result.append(max(zz) if zz else None)
    return result

def measure():
    obs=observations();s=obs['side'];scale=s['pixels_per_metre'];work=bpy.data.collections['FIT | Editable forms'];report={}
    for trace,prefix in [('roof_crown','Roof | shallow pressed crown'),('bonnet_silhouette','Bonnet |')]:
        guide=bpy.data.objects['TARGET | side | '+trace]
        points=[guide.matrix_world@Vector(p.co[:3]) for p in guide.data.splines[0].points]
        objects=[o for o in work.objects if o.get('fit_source','').startswith(prefix)]
        actual=outline_samples(objects,[p.y for p in points]);rows=[]
        for p,z in zip(points,actual):
            u=s['front_hub_px'][0]+(p.y-s['axle_front_world'])*scale
            target_v=s['front_hub_px'][1]-(p.z-s['axle_z'])*scale
            model_v=None if z is None else s['front_hub_px'][1]-(z-s['axle_z'])*scale
            rows.append(dict(u=u,target_v=target_v,model_v=model_v,error_px=None if z is None else model_v-target_v))
        valid=[r['error_px'] for r in rows if r['error_px'] is not None]
        report[trace]=dict(samples=rows,rms_px=math.sqrt(sum(e*e for e in valid)/len(valid)) if valid else None,
                           max_absolute_px=max(abs(e) for e in valid) if valid else None,
                           missing_samples=len(rows)-len(valid))
    report['scope']='Side upper contours of actual evaluated roof and bonnet meshes. No full silhouette, surface-quality or multi-view approval score.'
    report['annotation_uncertainty_px']=s['uncertainty_px']
    return report

class FITSettings(bpy.types.PropertyGroup):
    reference_alpha:bpy.props.FloatProperty(name='Reference opacity',min=0,max=1,default=.65,update=update_alpha)

class FIT_OT_view(bpy.types.Operator):
    bl_idname='gtfit.view';bl_label='Reference view';key:bpy.props.StringProperty()
    def execute(self,context):choose_view(context,self.key);return {'FINISHED'}

class FIT_OT_report(bpy.types.Operator):
    bl_idname='gtfit.report';bl_label='Measure edited bonnet and roof'
    def execute(self,context):
        report=measure();txt=bpy.data.texts.get('FIT | current-errors.json') or bpy.data.texts.new('FIT | current-errors.json');txt.clear();txt.write(json.dumps(report,indent=2))
        base=Path(bpy.path.abspath('//'));i=1
        while (base/('shape-errors-%03d.json'%i)).exists():i+=1
        file=base/('shape-errors-%03d.json'%i);file.write_text(json.dumps(report,indent=2))
        self.report({'INFO'},'Saved '+file.name+'; negative error means model is higher than target');return {'FINISHED'}

class FIT_PT_panel(bpy.types.Panel):
    bl_label='Reference Fit';bl_idname='FIT_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Shape'
    def draw(self,context):
        col=self.layout.column();col.label(text='Primary: original A perspective')
        for key,label in [('hero','Original A - provisional camera'),('side','Side - hub-registered'),('front','Front - provisional guide')]:
            col.operator('gtfit.view',text=label).key=key
        col.prop(context.scene.gtfit,'reference_alpha');col.separator()
        col.label(text='Edit only FIT | Editable forms.')
        col.label(text='Yellow traces are targets, not drivers.')
        col.operator('gtfit.report');col.label(text='Read errors in Text Editor / output JSON.')
        col.label(text='Camera fixed during shape edits.')

classes=[FITSettings,FIT_OT_view,FIT_OT_report,FIT_PT_panel]
def register():
    for cls in classes:bpy.utils.register_class(cls)
    bpy.types.Scene.gtfit=bpy.props.PointerProperty(type=FITSettings)
def unregister():
    if hasattr(bpy.types.Scene,'gtfit'):del bpy.types.Scene.gtfit
    for cls in reversed(classes):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
