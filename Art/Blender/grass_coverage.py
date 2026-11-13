"""Four dry meadow forms, shared slope variants and clustered opaque coverage."""
import bpy, math, random

def build(mesh, simple, center, channel, edge, height, noise, scene):
    material=simple('M_RF_GrassCarpet',(1,1,1),vertex=True)
    slopes=[0,.15,.30,.50,.80]
    # name, fine blades, folded blades, height, lateral lean, root spread, tip colour
    forms=[('Mat',44,0,(.12,.27),(.10,.25),.43,(.31,.225,.105)),
           ('Tuft',30,6,(.22,.46),(.06,.22),.31,(.36,.265,.12)),
           ('Swept',40,4,(.16,.34),(.22,.44),.39,(.29,.195,.085)),
           ('Seed',28,6,(.34,.65),(.035,.15),.25,(.40,.31,.16))]
    prototypes=[]
    for kind,(name,nfine,nfold,hrange,lrange,spread,tip_colour) in enumerate(forms):
        r=random.Random(94021+kind*173)
        blades=[]
        for b in range(nfine+nfold):
            folded=b>=nfine
            angle=r.uniform(-math.pi,math.pi)
            radius=spread*math.sqrt(r.random())
            x,y=radius*math.cos(angle),radius*math.sin(angle)
            if name=='Tuft':
                x=x*.45+(-.16 if b%2 else .17); y*=.65
            heading=r.uniform(-math.pi,math.pi) if name!='Swept' else r.uniform(-.5,.7)
            length=r.uniform(*hrange)*(1.05 if folded else 1)
            width=r.uniform(.026,.042) if folded else r.uniform(.012,.026)
            blades.append((x,y,heading,length,width,r.uniform(*lrange),r.random(),folded))
        for i,slope in enumerate(slopes):
            verts=[]; faces=[]; colors=[]
            def add(points,x,y,a,base,tip,length,triangles):
                dx,dy=math.cos(a),math.sin(a); sx,sy=-dy,dx
                n=len(verts)
                for across,forward,z in points:
                    px=x+sx*across+dx*forward; py=y+sy*across+dy*forward
                    verts.append((px,py,z+slope*px-.045))
                    f=min(1,z/length*1.4)
                    colors.append(tuple(base[k]*(1-f)+tip[k]*f for k in range(3))+(z,))
                faces.extend(tuple(n+v for v in face) for face in triangles)
            for b,(x,y,a,length,width,lean,tint,folded) in enumerate(blades):
                base=(.085+.045*tint,.048+.03*tint,.024+.012*tint)
                shade=.78+.35*tint
                tip=tuple(c*shade for c in tip_colour)
                if folded:
                    points=[(-width*.8,0,0),(width*.8,0,0),
                            (-width*.65,lean*.36,length*.53),(0,lean*.30,length*.64),
                            (width*.65,lean*.36,length*.53),(0,lean,length)]
                    triangles=[(0,1,3),(0,3,2),(1,4,3),(2,3,5),(3,4,5)]
                else:
                    points=[(0,0,0),(-width,lean*.3,length*.42),(0,lean,length),(width,lean*.3,length*.42)]
                    triangles=[(0,1,2),(0,2,3)]
                add(points,x,y,a,base,tip,length,triangles)
                if name=='Seed' and b<6:
                    # Small dry seed ears on six of the existing stems.
                    w=.016; low=length*.82; mid=length*.93
                    points=[(0,lean*.80,low),(-w,lean*.92,mid),(0,lean,length),(w,lean*.92,mid)]
                    add(points,x,y,a,(.17,.105,.048),(.26,.175,.085),length,[(0,1,2),(0,2,3)])
            ob=mesh('SM_RF_GrassCarpet_'+name+'_Slope'+str(i),verts,faces,material,colors,smooth=False)
            prototypes.append(ob)

    rng=random.Random(7319)
    placements=[]; step=.56
    for ix in range(int(94/step)):
        for iy in range(int(62/step)):
            s=.5+(ix+rng.uniform(-.46,.46))*step
            t=-31+(iy+rng.uniform(-.46,.46))*step
            shoulder=abs(t)-edge(s,t)-.15-.25*noise(s,t,1.2)
            shore=abs(s-channel(t))-3.9-.30*noise(s,t,1.4)
            if shoulder<0 or shore<0: continue
            feather=min(1,shoulder/1.15,shore/.9)
            if rng.random()>.35+.65*feather: continue
            if s>72 and abs(t)<3: continue
            # Low grass is continuous; taller forms occur in loose coherent patches.
            patch=.5+.5*noise(s+19,t-12,3.8)
            choice=rng.random()
            if feather<.5 or choice<.32: kind=0
            elif choice<.62: kind=1 if patch>.48 else 2
            elif choice<.90: kind=2 if patch>.48 else 0
            else: kind=3 if patch>.38 else 1
            eps=.1
            gx=(height(s+eps,t)-height(s-eps,t))/(2*eps)
            gy=(height(s,t+eps)-height(s,t-eps))/(2*eps)
            gx-=gy*(center(s+eps)-center(s-eps))/(2*eps)
            slope=math.hypot(gx,gy)
            index=min(range(len(slopes)),key=lambda i:abs(slopes[i]-slope))
            yaw=math.atan2(gy,gx) if slope>.06 else rng.uniform(-math.pi,math.pi)
            proto=prototypes[kind*len(slopes)+index]
            ob=bpy.data.objects.new('Coverage_'+str(len(placements)),proto.data)
            scene.collection.objects.link(ob); ob.visible_shadow=False
            ob.location=(s,center(s)+t,height(s,t)); ob.rotation_euler.z=yaw
            mass=.94+.12*noise(s,t,2.7)
            scale=rng.uniform(.83,1.10)*(.70+.30*feather)*mass; ob.scale=(scale,)*3
            placements.append(dict(mesh=proto.name,location_m=list(ob.location),yaw_deg=math.degrees(yaw),scale=scale,collision=False))
    return prototypes,placements
