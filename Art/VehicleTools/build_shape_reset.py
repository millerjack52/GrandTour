"""Independent primary-form studies; preserve the detailed learning prototype.

Metres, +X left, -Y front. One section definition drives body, bonnet and glazing.
These are design proposals, not factory dimensions or approved component fits.
"""
import bpy,bmesh,math,sys,json,argparse,shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));import wheel_fender_workshop as wf;import door_window_workshop as dw
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists() and any(out.iterdir()):raise RuntimeError('Use an empty study folder')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='C:/GrandTour/Art/Export/VehicleTools/cockpit-workshop-v04/RangeRover_Cockpit_Workshop.blend')
sc=bpy.context.scene;cam=sc.camera;original=[o for o in sc.objects if o.type in ['MESH','CURVE','FONT','EMPTY'] and o.name!='Ground'];original_hidden={o:o.hide_render for o in original}
wheel_sources=[c for c in bpy.data.collections if c.get('kind')=='wheel']
specs=[dict(name='A | compact four-door',key='A',nose=-1.98,tail=2.03,front=-1.27,rear=1.20,radius=.45,track=1.76,scuttle=-.69,roof_front=-.43,roof_rear=1.78,belt=1.37,roof=1.98,sill=.62),
       dict(name='B | short expedition',key='B',nose=-1.86,tail=1.84,front=-1.10,rear=1.08,radius=.47,track=1.78,scuttle=-.54,roof_front=-.33,roof_rear=1.63,belt=1.41,roof=2.02,sill=.66)]
m=dict(paint=wf.material('Shape study | olive',(.23,.265,.12),.65),trim=wf.material('Shape study | graphite',(.034,.043,.040),.67),glass=wf.material('Shape study | dark glazing',(.070,.115,.120),.23,.25),
       lamp=wf.material('Shape study | ivory lamps',(.68,.70,.58),.39),amber=wf.material('Shape study | amber',(.80,.23,.017),.5),clay=wf.material('Shape study | neutral clay',(.36,.38,.37),.78),steel=wf.material('Shape study | satin rims',(.24,.25,.20),.55,.2))
def mesh(name,verts,faces,mat,c,bevel=0):
    o=wf.mesh(name,verts,faces,mat,c,None,bevel);o['shape_study']=True;return o
def box(name,loc,size,mat,c,bevel=0):
    o=dw.box(name,loc,size,mat,c,None,bevel);o['shape_study']=True;return o
def solid(name,poly,delta,mat,c):
    o=dw.solid(name,poly,delta,mat,c,None);o['shape_study']=True;return o
def mix(v,rows):
    if v<=rows[0][0]:return rows[0][1]
    for (a,x),(b,y) in zip(rows,rows[1:]):
        if v<=b:return x+(y-x)*(v-a)/(b-a)
    return rows[-1][1]
def section_x(s,y,z):
    width=mix(y,[(s['nose'],.910),(s['nose']+.20,1.005),(s['tail']-.16,1.005),(s['tail'],.949)])
    # Deep lower tuck, broad door plane, a crisp projecting shoulder, tapered belt.
    return width+mix(z,[(s['sill'],-.070),(s['sill']+.10,-.038),(s['belt']-.22,-.040),(s['belt']-.11,0),(s['belt']-.045,0),(s['belt'],-.055)])
def bonnet_z(s,y):return mix(y,[(s['nose'],s['belt']-.110),(s['nose']+.16,s['belt']-.025),(s['scuttle'],s['belt'])])
def cab_x(s,z):return mix(z,[(s['belt'],.949),(s['roof']-.075,.822),(s['roof'],.795)])
def ring(name,outer,width,delta,mat,c):
    inner=dw.inset(outer,width);o=dw.ring(name,outer,inner,delta,mat,c,None);o['shape_study']=True;return inner
def glazing(name,poly,delta,c):
    inner=ring(name+' | structural frame',poly,.038,delta,m['paint'],c)
    edge=ring(name+' | dark reveal',inner,.016,delta,m['trim'],c)
    solid(name+' | inset pane',[tuple(Vector(v)+Vector(delta)*.36) for v in edge],tuple(Vector(delta)*.12),m['glass'],c)
def build(s):
    c=bpy.data.collections.new(s['name']);sc.collection.children.link(c);c['shape_spec']=json.dumps(s);c['status']='PROPOSED PRIMARY SHAPE; details and rig not fitted'
    # Closed connected lower shell. Longitudinal stations preserve deliberate folds.
    ys=sorted(set([s['nose'],s['nose']+.16,s['front'],s['scuttle'],.28,s['rear'],s['tail']-.16,s['tail']]))
    zs=[s['sill'],s['sill']+.10,s['belt']-.22,s['belt']-.11,s['belt']-.045,s['belt']]
    verts=[]
    for y in ys:
        # Cross section runs up left side, across formed bonnet/shoulder, down right.
        zz=[min(z,bonnet_z(s,y)) for z in zs]
        zz=[s['sill']+(bonnet_z(s,y)-s['sill'])*(z-s['sill'])/(s['belt']-s['sill']) for z in zs]
        left=[(section_x(s,y,z),y,z) for z in zz]
        top=zz[-1];verts+=left+[(.74,y,top+.035),(.66,y,top+.045),(-.66,y,top+.045),(-.74,y,top+.035)]+[(-x,y,z) for x,y,z in reversed(left)]
    n=16;faces=[tuple(range(n-1,-1,-1)),tuple(range((len(ys)-1)*n,len(ys)*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(ys)-1) for i in range(n)]
    body=mesh('Study | continuous folded lower body',verts,faces,m['paint'],c)
    # Hollow the cabin before evaluating silhouette. Four walls/bonnet remain connected.
    dw.cut(body,box('Temporary cabin cavity',(0,(s['scuttle']+s['tail']-.06)/2,1.65),(1.77,s['tail']-.06-s['scuttle'],1.92),None,c))
    for axle in [s['front'],s['rear']]:
        rr=s['radius']+.060
        arch=[(-1.30,axle+rr*math.cos(math.pi-i*math.pi/12),max(s['sill'],s['radius']+rr*math.sin(math.pi-i*math.pi/12))) for i in range(13)]
        poly=arch+[(-1.30,axle+rr,-.2),(-1.30,axle-rr,-.2)]
        dw.cut(body,solid('Temporary arch aperture',poly,(2.60,0,0),None,c))
        for side in [-1,1]:
            vv=[]
            for layer in range(4):
                rad=rr if layer in [1,2] else rr+.095
                for i in range(13):
                    y=axle+rad*math.cos(math.pi-i*math.pi/12);z=max(s['sill'],s['radius']+rad*math.sin(math.pi-i*math.pi/12))
                    x=section_x(s,y,z)+.004 if layer==0 else 1.070 if layer==1 else .915 if layer==2 else section_x(s,y,z)-.012
                    vv.append((side*x,y,z))
            ff=[(j*13+i,j*13+i+1,((j+1)%4)*13+i+1,((j+1)%4)*13+i) for j in range(4) for i in range(12)]+[(0,13,26,39),(12,51,38,25)]
            mesh('Study | substantial arch shoulder',vv,ff,m['paint'],c)
    # Close small triangular Boolean slivers at the compound rear shoulder.
    # Arch and cabin apertures have proper cut walls; no large opening is capped.
    bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=3)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),'Lower body Boolean requires repair';bm.to_mesh(body.data);bm.free()
    # Bonnet plateau and shoulders are part of the connected shell above.
    # Cabin built around the same belt/roof landmarks, with real recessed panes.
    z0=s['belt']+.003;zt=s['roof']-.082;front0=s['scuttle']+.008;front1=s['roof_front'];rear0=s['tail']-.035;rear1=s['roof_rear']
    glazing('Study | windscreen',[(-cab_x(s,z0),front0,z0),(cab_x(s,z0),front0,z0),(cab_x(s,zt),front1,zt),(-cab_x(s,zt),front1,zt)],(0,.023,0),c)
    glazing('Study | rear screen',[(cab_x(s,z0),rear0,z0),(-cab_x(s,z0),rear0,z0),(-cab_x(s,zt),rear1,zt),(cab_x(s,zt),rear1,zt)],(0,-.023,0),c)
    cuts=[(front0,front1),(.20,.20),(1.04,1.01),(rear0,rear1)] if s['key']=='A' else [(front0,front1),(.60,.60),(rear0,rear1)]
    for side in [-1,1]:
        for j,((b0,t0),(b1,t1)) in enumerate(zip(cuts,cuts[1:])):
            poly=[(side*cab_x(s,z0),b0+.004,z0),(side*cab_x(s,z0),b1-.004,z0),(side*cab_x(s,zt),t1-.004,zt),(side*cab_x(s,zt),t0+.004,zt)]
            glazing('Study | side window '+str(j),poly,(-side*.022,0,0),c)
        # Broad rocker tuck makes the body sit above the wheels rather than between them.
        box('Study | recessed rocker',(side*.952,(s['front']+s['rear'])/2,s['sill']+.034),(.057,s['rear']-s['front']-1.0,.064),m['trim'],c,.012)
        # Minimal handles locate the doors; no accessory/detail pass in this study.
        for end in ([.20,1.04] if s['key']=='A' else [.60]):
            z=s['belt']-.16;box('Study | door handle',(side*(section_x(s,end-.10,z)+.016),end-.10,z),(.033,.100,.034),m['trim'],c,.006)
        box('Study | mirror',(side*1.047,s['scuttle']+.085,s['belt']+.15),(.160,.10,.128),m['trim'],c,.015)
    # Roof has a shallow crown and turned rim, rather than a flat slab.
    roofsections=[(front1-.060,s['roof']-.027),(front1+.030,s['roof']),(rear1-.055,s['roof']),(rear1+.045,s['roof']-.025)]
    vv=[]
    for y,z in roofsections:
        vv += [(x,y,z+dz) for x,dz in [(-.850,-.038),(-.780,0),(0,.017),(.780,0),(.850,-.038)]]
    ro=mesh('Study | crowned roof and folded lip',vv,[(j*5+i,j*5+i+1,(j+1)*5+i+1,(j+1)*5+i) for j in range(3) for i in range(4)],m['paint'],c)
    mod=ro.modifiers.new('Roof rim depth','SOLIDIFY');mod.thickness=.040;mod.offset=-1
    # Front mask, high square bumper and a simple lamp layout establish identity.
    fy=s['nose']-.008;hz=s['belt']-.29
    box('Study | front fascia',(0,fy,hz),(1.81,.045,.337),m['trim'],c,.013)
    box('Study | grille recess',(0,fy-.03,hz),(.98,.040,.270),m['trim'],c)
    for z in [hz-.11,hz-.055,hz,hz+.055,hz+.11]:box('Study | grille blade',(0,fy-.056,z),(.970,.030,.012),m['steel'],c,.003)
    for side in [-1,1]:
        x=side*.675;rad=.133;outer=[(x+rad*math.cos(i*math.tau/32),fy-.041,hz+rad*math.sin(i*math.tau/32)) for i in range(32)]
        edge=ring('Study | headlamp ring',outer,.014,(0,.027,0),m['steel'],c);solid('Study | headlamp',edge,(0,.012,0),m['lamp'],c)
        box('Study | upright indicator',(side*.860,fy-.035,hz),(.066,.030,.225),m['amber'],c,.003)
    bumperz=s['sill']+.075
    poly=[(-.98,fy-.18),(.98,fy-.18),(1.035,fy-.12),(1.035,fy+.07),(.935,fy+.12),(-.935,fy+.12),(-1.035,fy+.07),(-1.035,fy-.12)]
    solid('Study | chamfered front bumper',[(x,y,bumperz-.09) for x,y in poly],(0,0,.18),m['trim'],c)
    box('Study | rear bumper',(0,s['tail']+.04,bumperz),(2.015,.22,.18),m['trim'],c,.035)
    box('Study | chassis mass',(0,0,s['sill']-.080),(.70,s['rear']-s['front']+.15,.11),m['trim'],c,.010)
    # Reuse the wheel's demonstrated shape, uniformly scaled, never squash circles.
    for src in wheel_sources:
        old=json.loads(src['spec']);front=old['center'][1]<0;side=old['side'];center=Vector((side*s['track']/2,s['front'] if front else s['rear'],s['radius']));scale=s['radius']/.38
        for ob in src.objects:
            if ob.type!='MESH':continue
            eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());data=bpy.data.meshes.new_from_object(eo,depsgraph=bpy.context.evaluated_depsgraph_get());copy=bpy.data.objects.new('Study wheel | '+ob.name,data);c.objects.link(copy)
            for v in data.vertices:v.co=center+(ob.matrix_world@v.co-Vector(old['center']))*scale
            copy['shape_study']=True
    return c
studies=[build(s) for s in specs]
def show(c=None):
    for o in original:o.hide_render=original_hidden[o] if c is None else True;o.hide_set(c is not None)
    for cc in studies:
        for o in cc.objects:o.hide_render=cc!=c;o.hide_set(cc!=c)
    bpy.context.view_layer.update()
sc.cycles.samples=32;sc.render.threads_mode='FIXED';sc.render.threads=10;sc.render.resolution_x=1200;sc.render.resolution_y=900
views={'quarter':((4.7,-7,2.9),(0,.02,1.02),5.65),'side':((7,.05,1.03),(0,.05,1.03),5.10),'front':((0,-8,1.04),(0,0,1.04),3.35)}
def render(name,view,clay):
    loc,target,size=views[view];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size
    sc.view_layers[0].material_override=m['clay'] if clay else None;sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True);sc.view_layers[0].material_override=None
show()
for v in views:render('OLD-'+v+'-clay',v,True)
for s,c in zip(specs,studies):
    show(c)
    for v in views:render(s['key']+'-'+v+'-clay',v,True)
    render(s['key']+'-quarter-colour','quarter',False)
    sc['shape_review_status']='Unapproved primary-form study. No fitted cockpit or functioning rig. Original prototype preserved.'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/('Shape_Study_'+s['key']+'.blend')))
(out/'shape-specs.json').write_text(json.dumps(specs,indent=2));shutil.copy2(__file__,out/Path(__file__).name)
print('SHAPE_STUDIES_SAVED',flush=True)
