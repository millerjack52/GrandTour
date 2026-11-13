"""Non-destructive inspection rig for the RR learning prototype; no physics rig."""
bl_info={'name':'Grand Tour Articulation Workshop','author':'Grand Tour','version':(0,1,0),'blender':(5,1,0),'category':'Animation'}
import bpy,math,json
from mathutils import Vector,Matrix
ROOT='GT | inspection controls'
COLLECTION='GT | articulation rig'
DOORS=['left_front_door','right_front_door','left_rear_door','right_rear_door']
PROPS=DOORS+['steer','roll']

def root():return bpy.data.objects.get(ROOT)
def empty(name,c,loc=(0,0,0),parent=None):
    o=bpy.data.objects.new(name,None);c.objects.link(o);o.location=loc;o.parent=parent;o.empty_display_type='ARROWS';o.empty_display_size=.13;o['gt_rig']=True;return o
def attach(ob,p):
    bpy.context.view_layer.update();ob.parent=p;ob.matrix_parent_inverse=p.matrix_world.inverted()
def driver(ob,index,key,expr):
    fc=ob.driver_add('rotation_euler',index);d=fc.driver;d.type='SCRIPTED';v=d.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=root();v.targets[0].data_path='["'+key+'"]';d.expression=expr
def set_controls(**values):
    r=root()
    for k,v in values.items():
        if k not in PROPS or not math.isfinite(v):raise ValueError('Invalid rig control')
        r[k]=v
    r.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
def neutral():set_controls(**{k:0. for k in PROPS})
def build():
    if root() or bpy.data.collections.get(COLLECTION):raise RuntimeError('Rig exists; keep manual work and use the existing controls')
    comps=[c for c in bpy.data.collections if c.get('gt_owner')]
    if len(comps)!=46:raise RuntimeError('Expected the 46-component cockpit-v04 assembly')
    c=bpy.data.collections.new(COLLECTION);bpy.context.scene.collection.children.link(c);r=empty(ROOT,c);r.empty_display_type='CUBE';r.empty_display_size=.07
    for k in PROPS:
        r[k]=0.;lo,hi=(0.,70. if 'front' in k else 65.) if k in DOORS else ((-30.,30.) if k=='steer' else (-720.,720.))
        r.id_properties_ui(k).update(min=lo,max=hi,soft_min=lo,soft_max=hi,description='Degrees; inspection prototype. See sweep report for contacts.')
    r['shape_status']='User says overall shape is off; improved detail. Learning/import prototype, not approved shape.'
    r['steering_ratio']=15.;groups={};guarded=set()
    def guard(cc):
        if cc.name in guarded:return
        # Extra manifest member deliberately blocks old static builders even when closed.
        g=empty('RIG GUARD | '+cc.name,cc);g.hide_viewport=True;g.hide_render=True;g['gt_rig_guard']=True
        cc['gt_articulated']=True;guarded.add(cc.name)
    for side,label in [(1,'Left'),(-1,'Right')]:
        for pos in ['front','rear']:
            key=label.lower()+'_'+pos+'_door';pivot=empty('Hinge | '+key,c,(side*.930,-.770 if pos=='front' else .230,.90),r)
            driver(pivot,2,key,f'{-side}*min(max(v,0),{70 if pos=="front" else 65})*pi/180')
            names=[f'{label} | {pos} door assembly',f'{label} | {pos} window cassette',f'{label} | {pos} door card']
            if pos=='front':names.append(f'{label} | mirror assembly')
            members=[]
            for name in names:
                cc=bpy.data.collections[name];attach(next(o for o in cc.objects if o.get('mount')),pivot);members.extend(o.name for o in cc.objects if o.type=='MESH');guard(cc)
            groups[key]=members
    for cc in comps:
        if cc.get('kind')!='wheel':continue
        s=json.loads(cc['spec']);side=s['side'];center=s['center'];front=center[1]<0;key=('left' if side==1 else 'right')+('_front_wheel' if front else '_rear_wheel')
        turn=empty('Steer pivot | '+key,c,center,r)
        if front:driver(turn,2,'steer',f'atan(2.63*tan(min(max(v,-30),30)*pi/180)/(2.63-{side}*0.78*tan(min(max(v,-30),30)*pi/180)))')
        spin=empty('Roll pivot | '+key,c,(0,0,0),turn);driver(spin,0,'roll','v*pi/180')
        attach(next(o for o in cc.objects if o.get('mount')),spin);groups[key]=[o.name for o in cc.objects if o.type=='MESH'];guard(cc)
    cc=bpy.data.collections['Cabin | steering and pedals'];p=empty('Steering column axis',c,(-.410,-.154,1.090),r)
    normal=Vector((0,.92,.392)).normalized();p.rotation_euler=Vector((0,0,1)).rotation_difference(normal).to_euler()
    spin=empty('Steering wheel rotation',c,parent=p);driver(spin,2,'steer','min(max(v,-30),30)*15*pi/180')
    members=[]
    for ob in list(cc.objects):
        if any(ob.name.startswith(n) for n in ['Steering | shaped rim','Steering | tapered spoke','Steering | hub','Steering | horn pad']):attach(ob,spin);members.append(ob.name)
    groups['steering_wheel']=members;guard(cc)
    r['groups']=json.dumps(groups);r['guarded_collections']=json.dumps(sorted(guarded));neutral();return groups

class GTA_OT_Pose(bpy.types.Operator):
    bl_idname='gta.pose';bl_label='Inspection pose';bl_options={'REGISTER','UNDO'}
    pose:bpy.props.EnumProperty(items=[('neutral','Neutral',''),('open','Open doors',''),('left','Steer left',''),('right','Steer right','')])
    def execute(self,context):
        if root().animation_data and root().animation_data.action:self.report({'ERROR'},'Use the static inspection file for manual controls');return {'CANCELLED'}
        neutral()
        if self.pose=='open':set_controls(**{k:60. for k in DOORS})
        elif self.pose in ['left','right']:set_controls(steer=25. if self.pose=='left' else -25.)
        return {'FINISHED'}
class GTA_PT_Panel(bpy.types.Panel):
    bl_label='Prototype Movement';bl_idname='GTA_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='GT Parts'
    def draw(self,context):
        l=self.layout;r=root()
        if not r:l.label(text='Open the articulation assembly');return
        l.label(text='Learning prototype; shape unapproved')
        for k in PROPS:l.prop(r,'["'+k+'"]',text=k.replace('_',' ').title())
        for key,label in [('neutral','Reset to neutral'),('open','Open all doors'),('left','Steer left'),('right','Steer right')]:o=l.operator('gta.pose',text=label);o.pose=key
        l.label(text='Check sweep report before export')
CLASSES=[GTA_OT_Pose,GTA_PT_Panel]
def register():
    if hasattr(bpy.types,'GTA_PT_panel'):return
    for cls in CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
if __name__=='__main__':register()
