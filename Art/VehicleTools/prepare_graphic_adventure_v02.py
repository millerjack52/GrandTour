from pathlib import Path
import re
p=Path('C:/GrandTour/Art/VehicleTools/build_graphic_adventure_v02.py')
s=p.read_text().replace("graphic-adventure-assembly-v01","graphic-adventure-assembly-v02")
# Lower window belt, narrower frames and the measured straight shoulder.
s=re.sub(r'\.308(?!\d)', '.301',s)
s=s.replace("[(.13,.209),(.15,.216),(.18,.2185),(.25,.2185),(.27,.2192),(.286,.2165),(.301,.200),(.424,.1675),(.43,.1675)]", "[(.13,.213),(.139,.2165),(.15,.218),(.18,.2185),(.25,.2181),(.26,.2205),(.27,.2192),(.29,.2152),(.301,.203),(.424,.1684),(.43,.1684)]")
s=s.replace("[(.139,.446),(.15,.4525),(.18,.463),(.25,.4908),(.27,.491),(.29,.4862),(.301,.471),(.424,.407)]", "[(.139,.4393),(.15,.4525),(.18,.463),(.187,.4655),(.190,.4876),(.25,.4910),(.26,.4936),(.29,.4862),(.301,.4787),(.424,.407)]")
s=s.replace("Z=[.139,.15,.18,.22,.25,.27,.286,.29,.301]", "Z=[.139,.15,.18,.187,.190,.22,.25,.26,.27,.286,.29,.301]")
s=s.replace("('Front',-.177,.041,-.102),('Rear',.050,.249,.050)","('Front',-.177,.032,-.089),('Rear',.036,.254,.036)")
s=s.replace("else .210", "else .208")
s=s.replace("inner=[(a+.017,.324),(ytop+.012,.414),(b-.012 if label=='Front' else .198,.414),(b-.013,.324)]", "inner=[(a+.008,.306),(ytop+.008,.417),(b-.006 if label=='Front' else .201,.417),(b-.007,.306)]")
s=s.replace("[.251,.28,.329,.369,.392,.415,.449,.491]", "[.256,.28,.329,.369,.392,.415,.449,.494]")
s=s.replace("[.041,.050]", "[.032,.036]")
s=s.replace("[(.301,.249),(.424,.210)]", "[(.301,.254),(.424,.208)]")
s=s.replace("[(.301,.260),(.424,.221)]", "[(.301,.259),(.424,.214)]")
s=s.replace("[.301,.324,.414,.424]", "[.301,.306,.417,.424]")
s=s.replace("[(.260,.301),(.221,.424),(.386,.424),(.446,.301)],[(.274,.324),(.231,.414),(.377,.414),(.426,.324)]", "[(.259,.301),(.214,.424),(.352,.424),(.416,.301)],[(.267,.307),(.220,.417),(.340,.417),(.401,.307)]")
s=s.replace("[(.301,.446),(.424,.386)]", "[(.301,.416),(.424,.352)]")
s=s.replace("[-.102,.10,.386,tail(z)]", "[-.089,.10,.352,tail(z)]")
s=s.replace("y+.025,z", "y+.035,z")
# Bonnet is independent of the cabin taper: broad near-flat top, curved nose,
# controlled edge roll and vertical skirt meeting a single horizontal wing seam.
a=s.index('# Broad clamshell bonnet');b=s.index('# Single windscreen',a)
s=s[:a]+'''# Source-fitted bonnet and matching wings. No cabin-width function on the hood.
par=pivot('GA | Bonnet',(0,-.181,.306),root)
hood=[]
uvals=[-1,-.98,-.95,-.88,-.64,-.35,0,.35,.64,.88,.95,.98,1]
hood_profile=[(-.450,.264),(-.440,.2755),(-.420,.282),(-.400,.286),(-.350,.2935),(-.300,.299),(-.250,.3045),(-.200,.308),(-.181,.3075)]
for y,cz in hood_profile:
 row=[]
 for u in uvals:
  edge_drop=interp(abs(u),[(0,0),(.64,0),(.88,.004),(.95,.007),(.98,.014),(1,.026)])
  z=max(.261,cz-edge_drop)
  # Front corners recede around the nose; the rear remains at the cowl interface.
  yy=y+max(0,1-(y+.450)/.030)*.010*abs(u)**4
  row.append((u*.220,yy,z))
 hood.append(row)
panel('Bonnet main pressing',hood,(0,0,1),thick=.009,parent=par,smooth=False)
for sign in [-1,1]:
 edge=[r[-1] if sign>0 else r[0] for r in hood]
 panel('Bonnet side return '+str(sign),[edge,[(sign*.220,y,.259) for x,y,z in edge]],(sign,0,0),thick=.008,parent=par)
 panel('Bonnet seating flange '+str(sign),[[(sign*.216,y,.253) for x,y,z in edge],[(sign*.216,y,.262) for x,y,z in edge]],(sign,0,0),group='Underbody',mat='Inner',thick=.008)
 # The wing upper edge uses the exact bonnet skirt y/x station sequence.
 panel('Wing top return '+str(sign),[[(sign*sx(.258),y,.258) for x,y,z in edge],[(sign*.220,y,.258) for x,y,z in edge]],(0,0,1),thick=.008)
grid('Bonnet nose return',[hood[0],[(x,y,.259) for x,y,z in hood[0]]],thick=.008,parent=par)
grid('Bonnet rear return',[hood[-1],[(x,y,.270) for x,y,z in hood[-1]]],thick=.008,parent=par)
panel('Firewall',[[(x,y,z) for x in [-sx(z),-.139,0,.139,sx(z)]] for y,z in [(-.181,.139),(-.181,.265),(-.181,.301)]],(0,-1,0),group='Underbody',mat='Inner',thick=.018)
box('Bonnet scuttle vent',(0,-.209,.312),(.225,.014,.008),mat='Inner',bevel=.004,parent=par)
for x in [-.075,0,.075]:box('Vent divider '+str(x),(x,-.217,.312),(.003,.003,.008),mat='Body',bevel=.001,parent=par)

''' +s[b:]
s=s.replace(".265,sign)",".258,sign)")
s=s.replace("[(.301,-.181),(.424,-.111)]", "[(.301,-.185),(.424,-.107)]")
s=s.replace("[(-.200,.301),(-.1675,.424),(.1675,.424),(.200,.301)],[(-.183,.320),(-.157,.413),(.157,.413),(.183,.320)]", "[(-.203,.301),(-.1684,.424),(.1684,.424),(.203,.301)],[(-.190,.311),(-.158,.417),(.158,.417),(.190,.311)]")
s=s.replace("[(.301,-.177),(.424,-.102)]", "[(.301,-.177),(.424,-.089)]")
# Roof: source has rolled shoulders and rounded plan corners, not a flat tray.
a=s.index('# Crowned roof:');b=s.index('# Rear end:',a)
s=s[:a]+'''# Source-fitted roof crown and rounded plan corners; compact drip rails.
roof=[]
rx=[-1,-.9773,-.9375,-.8523,-.7386,-.4545,0,.4545,.7386,.8523,.9375,.9773,1]
for y,centre in [(-.120,.430),(-.103,.439),(-.070,.4425),(0,.4462),(.15,.4486),(.30,.4465),(.395,.4415),(.412,.427)]:
 row=[]
 for u in rx:
  f=interp(abs(u),[(0,1),(.4545,.91),(.7386,.77),(.8523,.67),(.9375,.49),(.9773,.24),(1,0)])
  yy=y
  if y<-.070:yy+=.028*abs(u)**4*((-.070-y)/.050)
  if y>.395:yy-=.007*abs(u)**4
  row.append((u*.176,yy,.4245+(centre-.4245)*f))
 roof.append(row)
roofpar=pivot('GA | Roof',(0,.15,.4245),root)
panel('Roof crown',roof,(0,0,1),thick=.009,parent=roofpar,smooth=False)
for sign in [-1,1]:
 edge=[r[-1] if sign>0 else r[0] for r in roof]
 grid('Roof gutter '+str(sign),[edge,[(x+sign*.001,y,z-.0015) for x,y,z in edge],[(x+sign*.001,y,z-.003) for x,y,z in edge]],group='Cabin frames',thick=.004,parent=roofpar)
 ys=[-.089,-.07,0,.15,.30,.395,.407]
 # Headliner/flange closes the underside without adding exterior roof width.
 panel('Roof side closure '+str(sign),[[(sign*.1684,y,.4230) for y in ys],[(sign*.176,y,.4245) for y in ys]],(0,0,1),group='Cabin frames',thick=.009,parent=roofpar)

''' +s[b:]
# Rear body follows a near-vertical lamp/tailgate panel then a low tuck under bumper.
a=s.index("panel('Lower tailgate'");b=s.index("upperpar=pivot",a)
s=s[:a]+"panel('Lower tailgate',[[(x,tail(z),z) for x in [-.167,-.1,0,.1,.167]] for z in [.187,.190,.22,.25,.26,.27,.29,.301]],(0,1,0),group='Rear module',thick=.016,parent=rearpar)\n"+s[b:]
a=s.index("for side,s in [('L',1),('R',-1)]:\n panel(side+' rear lamp support'");b=s.index("panel('Rear lower apron'",a)
s=s[:a]+'''for side,sgn in [('L',1),('R',-1)]:
 # One fitted vertical cassette per corner with a surrounding body aperture.
 zlo,zhi=.191,.251;xi,xo=.174,.214
 for name,zs,xs in [('bottom',[.139,.15,.18,.187,zlo],None),('top',[zhi,.26,.27,.29,.301],None),('inner',[zlo,.22,zhi],(.167,xi)),('outer',[zlo,.22,zhi],(xo,None))]:
  rows=[]
  for z in zs:
   lo,hi=(.167,sx(z)) if xs is None else (xs[0],sx(z) if xs[1] is None else xs[1])
   rows.append([(sgn*x,tail(z),z) for x in [lo,hi]])
  panel(side+' rear lamp aperture '+name,rows,(0,1,0),group='Rear module',thick=.012)
 def lampmap(x,z,depth=0):return(sgn*x,tail(z)+depth,z)
 outer=[(xi,zlo),(xo,zlo),(xo,zhi),(xi,zhi)]
 inner=[(xi+.002,zlo+.002),(xo-.002,zlo+.002),(xo-.002,zhi-.002),(xi+.002,zhi-.002)]
 v=[lampmap(x,z,.001) for x,z in outer+inner]
 panel_faces=[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)]
 bezel=make(side+' rear lamp cassette bezel',v,panel_faces,'Rear module','Inner',thick=.010,bevel=.002);orient(bezel,(0,1,0))
 for k,(za,zb) in enumerate([(.194,.208),(.211,.230),(.233,.248)]):
  vv=[lampmap(x,z,.0015) for x,z in [(xi+.003,za),(xo-.003,za),(xo-.003,zb),(xi+.003,zb)]]
  o=make(side+' rear lamp lens '+str(k),vv,[(0,1,2,3)],'Rear module','Light',thick=.008,bevel=.002);orient(o,(0,1,0))
  for j in range(1,8):
   x=xi+.003+(xo-xi-.006)*j/8
   tube(side+' tail lens rib '+str(k)+' '+str(j),lampmap(x,za+.001,.0018),lampmap(x,zb-.001,.0018),.00035,'Rear module','Light')
 # Recess-backed dividers connect the three lenses into a single unit.
 for za,zb in [(zlo+.001,.194),(.208,.211),(.230,.233),(.248,zhi-.001)]:
  o=make(side+' cassette divider '+str(za),[lampmap(x,z,.0005) for x,z in [(xi+.001,za),(xo-.001,za),(xo-.001,zb),(xi+.001,zb)]],[(0,1,2,3)],'Rear module','Inner',thick=.010);orient(o,(0,1,0))
''' +s[b:]
s=s.replace("for z in [.139,.15,.177]", "for z in [.139,.15,.18,.187]")
s=s.replace("for x in [-.170,.170]", "for x in [-.1675,.1675]")
s=s.replace("[.177,.18,.25,.27,.286,.29,.301]", "[.187,.190,.22,.25,.26,.27,.29,.301]")
s=s.replace("(0,tail(.201)+.004,.201)","(0,tail(.208)+.004,.208)")
# Front cap aligns to bonnet lower seam; remove the overhanging straight upper bar.
s=s.replace("(.438,.01,.003)","(.425,.006,.003)")
s=s.replace("[.188,.265]", "[.188,.259]")
s=s.replace("zmin,zmax=.190,.264", "zmin,zmax=.190,.259")
s=s.replace("[.187,.25,.265]", "[.187,.25,.258]")
s=s.replace("render('side',(9,0,1.3),6.3)","render('side',(9,0,1.3),6.3);render('front',(0,-9,1.3),3.5);render('rear',(0,9,1.3),3.5);render('top',(0,0,10),6.3)")
p.write_text(s)
print('Prepared',p)
