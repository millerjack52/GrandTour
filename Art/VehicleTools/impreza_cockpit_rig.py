"""Explicit continuation executed in the Impreza builder's shared interface context."""
from mathutils import Matrix
# A frameless pane still needs a lower channel attached to its moving door.
# Split only the bottom weather rail from each otherwise stationary aperture.
for s in [-1,1]:
 sn='L' if s>0 else 'R'
 for key,lo,hi in [('front',-.753,.25),('rear',.29,1.217)]:
  group=sn+'_'+key+'_door'
  for part in ['window frame','window gasket','inner glass reveal']:
   o=bpy.data.objects[sn+' '+key+' | '+part];fv=[];ff=[];mv=[];mf=[];material=o.data.materials[0];thick=o.modifiers[0].thickness if o.modifiers else .008
   def add(poly,vs,fs):
    if len(poly)>2:k=len(vs);vs.extend(poly);fs.append(tuple(range(k,len(vs))))
   for face in o.data.polygons:
    pp=[tuple(o.data.vertices[i].co) for i in face.vertices]
    if max(v[2] for v in pp)<1.18:
     add(clip(clip(pp,lambda x,y,z:y-lo),lambda x,y,z:hi-y),mv,mf)
     add(clip(pp,lambda x,y,z:lo-y),fv,ff);add(clip(pp,lambda x,y,z:y-hi),fv,ff)
    else:add(pp,fv,ff)
   name=o.name;bpy.data.objects.remove(o,do_unlink=True);mesh(name,fv,ff,material,cab,thick,True)
   # The tall painted concept rail is replaced by the door's narrow weather
   # channel; retaining that whole strip would pinch the frameless pane.
  pane=bpy.data.objects[sn+' '+key+' | window pane'];pv=[tuple(v.co) for v in pane.data.vertices];pf=[tuple(f.vertices) for f in pane.data.polygons];lowidx=sorted([i for i,v in enumerate(pv) if v[2]<1.20],key=lambda i:pv[i][1]);newidx=[]
  for i in lowidx:
   x,y,z=pv[i];y=max(lo+.015,min(hi-.015,(lo+hi)/2+(y-(lo+hi)/2)*.97));z=belt(y)-.035;x=s*(width(y,belt(y))-.031);newidx.append(len(pv));pv.append((x,y,z))
  pf.append((lowidx[0],lowidx[1],newidx[1],newidx[0]));name=pane.name;groups[group].remove(name);bpy.data.objects.remove(pane,do_unlink=True);mesh(name,pv,pf,glass,cab,.004,True,group)
  vv=[];ff=[]
  for i in range(31):
   y=lo+(hi-lo)*i/30;z=belt(y)-.014;xx=width(y,z);vv.extend([(s*xx,y,z),(s*(xx-.079),y,z-.008)])
  for i in range(30):k=i*2;ff.append((k,k+1,k+3,k+2))
  mesh(sn+' '+key+' | closed top channel',vv,ff,black,inside,.012,True,group)
 # Thin fixed threshold backing closes the sightline behind the lower reveal.
 box(sn+' | threshold seal',(s*.811,.008,.413),(.021,1.595,.018),black,lin,.003)
 # Inboard corner seals terminate the A/B/C-pillar reveals; these small fixed
 # patches prevent seeing the studio through the lower aperture corners.
 for yy in [-.78,.21,.33,1.19]:
  poly=[(yy-.055,1.075),(yy+.055,1.075),(yy+.055,1.151),(yy-.055,1.151)]
  mesh(sn+' | lower window corner seal',[(s*(cw(y,z)-.063),y,z) for y,z in poly],[(0,1,2,3)],black,cab,.008)
 vv=[]
 for z in [1.075,1.25,1.44,1.60]:vv.extend([(s*(cw(.27,z)-.007),y,z) for y in [.261,.279]])
 mesh(sn+' | B pillar seam backing',vv,[(i,i+1,i+3,i+2) for i in range(0,6,2)],black,cab,.012)

# Quietly layered interior fitted to the pan, rather than free-floating seat boxes.
for s in [-1,1]:
 sn='L' if s>0 else 'R'
 for rear in [False,True]:
  xc=s*(.253 if rear else .407);yc=.72 if rear else -.09;w=.456 if rear else .477;name=sn+(' rear seat' if rear else ' front seat');base=.53
  box(name+' | base',(xc,yc,.508),(w-.035,.40,.06),black,inside,.025)
  for dx in [-w*.30,w*.30]:
   box(name+' | rail',(xc+dx,yc,.463),(.035,.43,.027),silver,inside,.006)
   for dy in [-.16,.16]:box(name+' | floor foot',(xc+dx,yc+dy,.425),(.062,.055,.057),black,inside,.006)
  ob=box(name+' | cushion',(xc,yc,.573),(w,.445,.102),cloth,inside,.045)
  box(name+' | cushion insert',(xc,yc-.015,.621),(w*.62,.35,.018),insert,inside,.025)
  # Sloped backrest connected to cushion, with shaped lateral shoulder bolsters.
  pp=[(yc+.135,.56),(yc+.253,.56),(yc+.352,1.205),(yc+.245,1.218)]
  ob=prism(name+' | backrest',pp,0,xc-w*.48,xc+w*.48,cloth,inside);bevel(ob,.038,3)
  mesh(name+' | back insert',[(xc+dx,yc+.157+(.245-.157)*(z-.64)/(.555),z) for dx,z in [(-w*.29,.65),(w*.29,.65),(w*.27,1.166),(-w*.27,1.166)]],[(0,1,2,3)],insert,inside,.012)
  for dx in [-.068,.068]:rod(name+' | headrest post',(xc+dx,yc+.31,1.15),(xc+dx,yc+.31,1.285),.007,silver,inside,12)
  box(name+' | headrest',(xc,yc+.309,1.294),(.235,.117,.157),cloth,inside,.035)
  box(name+' | belt buckle',(xc-s*w*.57,yc+.06,.615),(.037,.048,.053),black,inside,.008)
  box(name+' | red release',(xc-s*w*.57,yc+.06,.64),(.025,.032,.008),red,inside,.003)
 # Door cards stop above the same rear wheel aperture and move with the skin.
 for key,lo,hi in [('front',-.69,.23),('rear',.35,1.17)]:
  group=sn+'_'+key+'_door'
  panel_grid(sn+' '+key+' | shaped inner card',[lo+(hi-lo)*i/28 for i in range(29)],[.441+i*.03 for i in range(20)],lambda y,z:(s*(width(y,z)-.062),y,z),[lambda y,z:.99-z,lambda y,z:z-max(.446,bottom(y)+.065)],cloth,inside,group,.012)
  yy=(lo+hi)/2;zz=.878;x=s*(width(yy,zz)-.092)
  box(sn+' '+key+' | armrest',(x,yy,zz),(.087,.405,.056),black,inside,.018,group)
  box(sn+' '+key+' | inner release',(x-s*.047,yy-.14,.954),(.008,.106,.043),silver,inside,.008,group)
  box(sn+' '+key+' | window switch',(x-s*.012,yy-.07,.911),(.035,.064,.008),black,inside,.003,group)
 # Full sill return from exterior edge to pan, closing the view below seats.
 mesh(sn+' | sill inner closure',[(s*.804,-.76,.355),(s*.804,.827,.355),(s*.848,.827,.407),(s*.848,-.76,.407)],[(0,1,2,3)],black,lin,.012)

box('Rear cabin | parcel shelf',(0,1.212,1.023),(1.40,.39,.029),cloth,inside,.012)
box('Boot | cargo floor',(0,1.676,.831),(1.015,.615,.026),floor_mat,inside,.009)
box('Boot | seat bulkhead',(0,1.182,.653),(1.012,.025,.49),black,inside,.008)
# Dashboard shell has geometric recesses and keeps clear of the door swing.
dash=prism('Dashboard | moulded shell',[(-.924,1.075),(-.672,1.070),(-.526,1.00),(-.523,.879),(-.710,.831),(-.884,.84)],0,-.717,.717,cloth,inside);bevel(dash,.022,3)
for x in [-.60,-.11,.11,.60]:
 poly=rr(x,.981,.148,.082,.012);cut(dash,poly,1,-.93,-.47)
 prism('Dash vent | recess',poly,1,-.571,-.562,dial,inside)
 for z in [.96,.98,1.0]:box('Dash vent | louvre',(x,-.534,z),(.129,.022,.005),black,inside,.002)
box('Dashboard | glovebox',(.43,-.517,.905),(.43,.035,.116),black,inside,.015)
box('Dashboard | glovebox latch',(.43,-.494,.93),(.075,.01,.018),silver,inside,.005)
box('Instruments | pod',(-.407,-.646,1.097),(.374,.22,.175),black,inside,.035)
box('Instruments | face',(-.407,-.528,1.091),(.326,.012,.134),dial,inside,.018)
for x,rad in [(-.493,.057),(-.33,.050)]:
 rod('Gauge | silver bezel',(x,-.532,1.096),(x,-.518,1.096),rad,silver,inside,32)
 rod('Gauge | black face',(x,-.516,1.096),(x,-.512,1.096),rad-.004,dial,inside,32)
 for i in range(13):
  ang=math.radians(220-260*i/12);u,v=math.cos(ang),math.sin(ang)
  rod('Gauge | tick',(x-u*rad*.72,-.509,1.096+v*rad*.72),(x-u*rad*.88,-.509,1.096+v*rad*.88),.001,white,inside,6)
 rod('Gauge | needle',(x,-.506,1.096),(x+.024,-.506,1.112),.0018,red,inside,6)
box('Console | upper stack',(0,-.528,.831),(.275,.065,.155),black,inside,.015)
box('Console | radio display',(0,-.49,.861),(.158,.008,.028),dial,inside,.005)
for x in [-.107,.107]:rod('Console | radio knob',(x,-.502,.859),(x,-.477,.859),.014,silver,inside)
for x in [-.084,0,.084]:rod('Console | climate dial',(x,-.501,.797),(x,-.474,.797),.022,cloth,inside)
box('Console | floor tunnel',(0,-.05,.505),(.228,.78,.178),black,inside,.03)
box('Console | shifter gaiter',(0,-.25,.610),(.095,.115,.06),cloth,inside,.026)
rod('Console | shifter',(0,-.25,.635),(0,-.23,.748),.009,silver,inside)
box('Console | shift knob',(0,-.23,.754),(.045,.04,.046),black,inside,.018)
curve('Console | handbrake',[(.078,-.02,.596),(.079,.14,.646)],.014,black,inside)
for y in [.17,.29]:rod('Console | cup recess',(0,y,.588),(0,y,.60),.040,dial,inside,24)
for x in [-.50,-.40,-.30]:box('Driver | pedal',(x,-.70,.543),(.06,.035,.083),silver,inside,.007)
# Steering rim in its own inclined frame, driven independently of the fixed column.
wc=Vector((-.407,-.308,.963));wn=Vector((0,.92,.392)).normalized();wu=Vector((1,0,0));wv=wn.cross(wu);vv=[];ff=[]
for i in range(48):
 d=wu*math.cos(i*math.tau/48)+wv*math.sin(i*math.tau/48)
 for j in range(10):ang=j*math.tau/10;vv.append(tuple(wc+d*(.151+.013*math.cos(ang))+wn*.013*math.sin(ang)))
for i in range(48):
 for j in range(10):ff.append((i*10+j,((i+1)%48)*10+j,((i+1)%48)*10+(j+1)%10,i*10+(j+1)%10))
mesh('Steering | padded rim',vv,ff,black,inside,smooth=True,group='cabin_steer')
rod('Steering | fixed column',(-.407,-.65,.83),wc-wn*.031,.023,black,inside)
rod('Steering | boss',wc-wn*.027,wc+wn*.020,.052,cloth,inside,24,'cabin_steer')
for ang in [0,math.pi,math.pi*1.5]:
 d=wu*math.cos(ang)+wv*math.sin(ang);rod('Steering | spoke',wc+d*.035,wc+d*.14,.017,silver,inside,12,'cabin_steer')
rod('Steering | indicator stalk',(-.407,-.386,.93),(-.59,-.386,.95),.006,black,inside,12)
box('Cabin | rearview mirror',(0,-.566,1.451),(.216,.051,.072),black,inside,.014)
rod('Cabin | mirror arm',(0,-.531,1.537),(0,-.554,1.477),.009,black,inside)
for s in [-1,1]:box('Cabin | sunvisor',(s*.37,-.411,1.511),(.319,.145,.019),cloth,inside,.016)
# Rounded seat belt webbing and pillars share their actual attachment location.
for s in [-1,1]:
 curve('Cabin | front belt '+str(s),[(s*.72,.254,1.413),(s*.635,.253,.954),(s*.67,.24,.439)],.015,black,inside)
 box('Cabin | belt upper anchor',(s*.722,.254,1.408),(.051,.044,.061),black,inside,.012)

# Close lower surfaces, suspension representations and brake mounts.
box('Front subframe | crossmember',(0,-1.985,.315),(.89,.10,.075),black,lin,.01)
for s in [-1,1]:box('Front subframe | longitudinal mount '+str(s),(s*.385,-1.43,.328),(.068,1.12,.069),black,lin,.009)
for cy in S['axles']:
 rod('Chassis | axle '+str(cy),(-.67,cy,.344),(.67,cy,.344),.027,black,lin,20)
 box('Chassis | differential '+str(cy),(0,cy,.346),(.17,.17,.125),black,lin,.035)
 for s in [-1,1]:
  rod('Chassis | spring strut',(s*.43,cy,.378),(s*.43,cy,.720),.025,silver,lin,20)
  curve('Chassis | spring',[(s*.43+.050*math.cos(t*math.tau/12),cy+.050*math.sin(t*math.tau/12),.48+t*.004) for t in range(49)],.008,black,lin)
  sn='L' if s>0 else 'R';ax='front' if cy<0 else 'rear';g=sn+'_'+ax+'_wheel'
  box(g+' | caliper',(s*.825,cy+.142,.362),(.05,.056,.118),red,wheelcol,.014,g+'_caliper')

# Match normals at the shaped cap after Boolean openings. The outer skin uses
# parametric normals; depth returns retain their own geometric normals.
for rear,o in caps.items():
 # Inset housings already provide aperture walls. Avoid creating tiny return
 # walls at grid T-junctions, which can produce bright shading artifacts.
 for mod in o.modifiers:
  if mod.type=='SOLIDIFY':mod.use_rim=False
 apply(o);me=o.data;normals=[None]*len(me.loops)
 for face in me.polygons:
  for li in face.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;x,y,z=v
   if abs(y-cap_y(x,z,rear))<.003:
    h=.0003;dx=(cap_y(x+h,z,rear)-cap_y(x-h,z,rear))/(2*h);dz=(cap_y(x,z+h,rear)-cap_y(x,z-h,rear))/(2*h);n=Vector((dx,-1,dz));n*=(-1 if rear else 1);normals[li]=tuple(n.normalized())
   else:normals[li]=tuple(face.normal)
 me.normals_split_custom_set(normals)

# Distinct bonnet/boot/bumper boundaries, with no arbitrary duplicated broad skins.
for rear,z in [(False,.735),(True,.746)]:
 base=2.04 if rear else -2.055;sg=1 if rear else -1
 curve(('Rear' if rear else 'Front')+' | bumper reveal',[(f*width(base,z),cap_y(f*width(base,z),z,rear)+sg*.002,z) for f in fracs],.002,black)
for s in [-1,1]:
 curve('Boot | side reveal '+str(s),[(s*.72,y,interp(y,S['trunk'])-.015) for y in [1.43,1.6,1.84,2.0]],.002,black)
pp=rr(0,.791,.375,.112,.008)
mesh('Rear plate | inset panel',[(x,cap_y(x,z,True)-.027,z) for x,z in pp],[tuple(range(len(pp)))],cream,trim,.004)
cu=bpy.data.curves.new('Rear plate | lettering','FONT');cu.body='GT / 03';cu.align_x='CENTER';cu.align_y='CENTER';cu.size=.055;cu.extrude=.0001;o=bpy.data.objects.new('Rear plate | lettering',cu);trim.objects.link(o);cu.materials.append(black);o.location=(0,0,.791);o.rotation_euler=(math.pi/2,0,math.pi)
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for v in o.data.vertices:v.co.y=cap_y(v.co.x,v.co.z,True)-.017+v.co.y

# Shared rear arch paint needs to travel with the rear door, while its tub stays.
for s in [-1,1]:
 sn='L' if s>0 else 'R';o=bpy.data.objects[sn+' | arch lip and tub 1.27'];vv=[];ff=[];fixedv=[];fixedf=[];mats=[]
 for face in o.data.polygons:
  pts=[tuple(o.data.vertices[i].co) for i in face.vertices]
  if face.material_index==0:
   mov=clip(clip(clip(pts,lambda x,y,z:y-.275),lambda x,y,z:1.224-y),lambda x,y,z:z-.430)
   stay=clip(pts,lambda x,y,z:y-1.236)
   low=clip(clip(pts,lambda x,y,z:1.236-y),lambda x,y,z:.422-z)
   for pp,vlist,flist in [(mov,vv,ff),(stay,fixedv,fixedf)]:
    if len(pp)>2:k=len(vlist);vlist.extend(pp);flist.append(tuple(range(k,len(vlist))))
   if len(stay)>2:mats.append(0)
   if len(low)>2:k=len(fixedv);fixedv.extend(low);fixedf.append(tuple(range(k,len(fixedv))));mats.append(0)
  else:
   adjusted=[]
   for x,y,z in pts:
    d=Vector((y-1.27,z-.362)).normalized();adjusted.append((s*min(abs(x),.85),y-d.x*.015,z-d.y*.015))
   k=len(fixedv);fixedv.extend(adjusted);fixedf.append(tuple(range(k,len(fixedv))));mats.append(1)
 new=mesh(sn+' | rear fixed arch and liner',fixedv,fixedf,paint,lin,.008,True);new.data.materials.append(black)
 for f,mi in zip(new.data.polygons,mats):f.material_index=mi
 mesh(sn+' | rear door arch return',vv,ff,paint,body,.009,True,sn+'_rear_door');bpy.data.objects.remove(o,do_unlink=True)

def empty(n,loc):
 o=bpy.data.objects.new(n,None);rigcol.objects.link(o);o.location=loc;o.empty_display_size=.1;o.empty_display_type='PLAIN_AXES';return o
def parent_keep(o,par):
 bpy.context.view_layer.update();m=o.matrix_world.copy();o.parent=par;o.matrix_world=m
root=empty('GT | Impreza controls',(0,0,0));root.empty_display_size=.32
def prop(k,value,lo,hi,desc):
 root[k]=float(value);root.id_properties_ui(k).update(min=lo,max=hi,description=desc)
def driver(o,path,index,prop,expr):
 f=o.driver_add(path,index);d=f.driver;d.type='SCRIPTED';v=d.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=root;v.targets[0].data_path='["'+prop+'"]';d.expression=expr
for s in [-1,1]:
 sn='L' if s>0 else 'R'
 for ax,y in [('front',-.774),('rear',.268)]:
  key=sn+'_'+ax+'_door';prop(key,0,0,55,'Door opening degrees; inspection rig');hinge=empty('Hinge | '+key,(s*.913,y,.69))
  for n in groups[key]:parent_keep(bpy.data.objects[n],hinge)
  driver(hinge,'rotation_euler',2,key,f'{-s}*min(55,max(0,v))*pi/180')
  # Hidden inspection hinges still represent an actual body-to-door mount path.
  for z in [.52,.87]:
   backing=box('Hinge backing | '+key,(s*.797,y+.022,z),(.080,.062,.055),silver,lin,.003)
   leaf=box('Hinge leaf | '+key,(s*.849,y+.03,z),(.115,.050,.04),silver,lin,.002,key);parent_keep(leaf,hinge)
   for ob in [backing,leaf]:ob.hide_render=True;ob.hide_set(True);ob['inspection_fixture']=True
prop('steer',0,-25,25,'Centre road-wheel steering angle');prop('roll',0,-720,720,'Wheel rotation degrees')
for cy in S['axles']:
 for s in [-1,1]:
  sn='L' if s>0 else 'R';ax='front' if cy<0 else 'rear';key=sn+'_'+ax+'_wheel';loc=(s*S['track']/2,cy,S['axle_z']);steer=empty('Steer | '+key,loc);roll=empty('Roll | '+key,loc);parent_keep(roll,steer)
  if cy<0:driver(steer,'rotation_euler',2,'steer',f'atan(2.52*tan(min(25,max(-25,v))*pi/180)/(2.52-{s}*.79*tan(min(25,max(-25,v))*pi/180)))')
  driver(roll,'rotation_euler',0,'roll','v*pi/180')
  for n in groups[key]:parent_keep(bpy.data.objects[n],roll)
  for n in groups[key+'_caliper']:parent_keep(bpy.data.objects[n],steer)
frame=empty('Steering | inclined frame',wc);frame.rotation_euler=wn.to_track_quat('Z','Y').to_euler();bpy.context.view_layer.update()
steer=empty('Steering | cabin spin',wc);steer.parent=frame;steer.matrix_parent_inverse=Matrix.Identity(4);steer.location=(0,0,0)
for n in groups['cabin_steer']:parent_keep(bpy.data.objects[n],steer)
driver(steer,'rotation_euler',2,'steer','min(25,max(-25,v))*pi/180*15')
sc.frame_set(1);bpy.context.view_layer.update()
textblock=bpy.data.texts.new('START HERE - Impreza.txt');textblock.write('Approved Gravel Club style. Model is an artistic interpretation, not a factory blueprint.\nSelect GT | Impreza controls: four door properties, steer, roll. Doors are frameless; body pillars stay fixed.\nStandard Blender drivers, no addon required. Manual scene has no keyed action.\nBody, glass, wheel assemblies, lamps, rally kit, interior and floor are independently editable collections.\nPreserve manual edits by Save As to a new revision. Builder refuses nonempty destinations.\nInspection rig only: no suspension travel, physics, LOD, UV atlas or engine-export certification.\n')
