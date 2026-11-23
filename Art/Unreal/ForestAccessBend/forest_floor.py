"""Bake the two forest shoulders as opaque soil relief, folded fern blades and fallen leaves."""
import hashlib
import json
import math
import random

import unreal as u
from benmore_river_life_materials import Graph
from preview_erosion_bank_meshes import build_tile


def clamp(x):
    return max(0.,min(1.,x))


def mix(a,b,t):
    return tuple(x+(y-x)*clamp(t) for x,y in zip(a,b))


def material(folder, plants):
    name='M_BendBrushFoliage' if plants else 'M_BendPeatAndMoss'
    path=folder+'/'+name
    assets=u.EditorAssetLibrary
    if assets.does_asset_exist(path):
        mat=u.load_asset(path)
        tag,version=('BendFoliageSurface','2') if plants else ('BendMossSurface','2')
        if assets.get_metadata_tag(mat,tag)==version:return mat
        u.MaterialEditingLibrary.delete_all_material_expressions(mat)
    else:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('two_sided',plants)
    g=Graph(mat,'BendForestFloor')
    col=g.node(u.MaterialExpressionVertexColor)
    if plants:
        # Geometry carries both the frond outline and its pale midrib.
        uv=g.node(u.MaterialExpressionTextureCoordinate)
        pigment=g.custom(['C','UV','P','Centre'],'''
float2 q=(P.xy-Centre.xy)*.01;
float beds=.61*sin(q.x*.55+q.y*.72)+.39*sin(q.y*.94-q.x*.21);
float fern=smoothstep(.008,.039,C.g-C.r)*smoothstep(.018,.075,C.g-C.b);
float3 bronze=lerp(float3(.095,.042,.022),float3(.307,.158,.059),smoothstep(.032,.185,C.g));
float3 pigment=lerp(C,bronze,.88*smoothstep(.23,.56,beds)*fern);
float midrib=(1.-smoothstep(.014,.105,abs(UV.x-.5)))*smoothstep(.02,.16,UV.y)*(1.-smoothstep(.80,1.,UV.y));
float vane=abs(frac(UV.y*11.+abs(UV.x-.5)*.95)-.5);
return pigment*(1.+.24*midrib-.075*(1.-smoothstep(.05,.22,vane)));
''')
        g.wire(col,pigment,'C');g.wire(uv,pigment,'UV')
        g.wire(g.node(u.MaterialExpressionWorldPosition),pigment,'P')
        g.wire(g.node(u.MaterialExpressionObjectPositionWS),pigment,'Centre')
        g.output(pigment,u.MaterialProperty.MP_BASE_COLOR)
    else:
        base='/Game/GrandTour/ArtTests/LidarStudy/FirstSection/'
        peat=u.load_asset(base+'PeatMoss/T_PM_PeatColour')
        packed=u.load_asset(base+'PeatMoss/T_PM_PeatData')
        field_path=folder+'/T_BendMossLitterFields'
        if not assets.does_asset_exist(field_path):
            from pathlib import Path
            task=u.AssetImportTask()
            task.filename=str(Path(u.Paths.project_dir()).resolve()/'Saved/ForestAccessBend/T_BendMossLitterFields.tga')
            task.destination_path=folder;task.automated=True;task.save=True
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        field=u.load_asset(field_path)
        assert field,field_path
        field.set_editor_property('srgb',False)
        field.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        assert assets.save_loaded_asset(field,False)
        p=g.node(u.MaterialExpressionWorldPosition)
        normal=g.node(u.MaterialExpressionVertexNormalWS)
        surf=g.custom(['Paint','P','Peat','Packed','Fields'],'''
float2 uv=(P.xy-float2(-53000,-32000))/148.;
float4 peat=Texture2DSample(Peat,View.MaterialTextureBilinearWrapedSampler,uv);
float4 data=Texture2DSample(Packed,View.MaterialTextureBilinearWrapedSampler,uv);
float3 field=Texture2DSample(Fields,View.MaterialTextureBilinearWrapedSampler,float2(uv.y+.21*uv.x,-uv.x)*.37).rgb;
float patch=smoothstep(.38,.68,.75*field.r+.39*Paint.g+.10*field.g);
float3 moss=lerp(float3(.046,.061,.025),float3(.144,.157,.064),smoothstep(.19,.81,field.g));
float3 soil=lerp(float3(.085,.061,.039),peat.rgb*float3(1.12,1.00,.85),.77);
float litter=field.b*(1.-.76*patch);
Height=lerp(data.r*1.90,field.g*.75+peat.a*.26+data.r*.34,patch)+.14*litter;
float3 surface=lerp(soil,moss*(.89+.18*peat.a),patch);
return lerp(surface,float3(.183,.102,.043)*(.75+.5*field.g),litter*.68)*lerp(.86,1.05,data.b);
''',outputs=[('Height',u.CustomMaterialOutputType.CMOT_FLOAT1)])
        g.wire(col,surf,'Paint');g.wire(p,surf,'P')
        g.wire(g.node(u.MaterialExpressionTextureObject,texture=field,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS),surf,'Fields')
        for pin,t in [('Peat',peat),('Packed',packed)]:
            assert t,pin
            sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if t.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
            g.wire(g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=sampler),surf,pin)
        from lidar_bank_material_polish import BUMP
        bump=g.custom(['H','P','N','Camera'],BUMP)
        g.wire(surf,bump,'H','Height');g.wire(p,bump,'P');g.wire(normal,bump,'N')
        g.wire(g.node(u.MaterialExpressionCameraPositionWS),bump,'Camera')
        mat.set_editor_property('tangent_space_normal',False)
        g.output(bump,u.MaterialProperty.MP_NORMAL);g.output(surf,u.MaterialProperty.MP_BASE_COLOR)
    g.output(g.scalar(.88),u.MaterialProperty.MP_ROUGHNESS)
    g.output(g.scalar(.14),u.MaterialProperty.MP_SPECULAR)
    assert not u.MaterialEditingLibrary.recompile_material(mat)
    assets.set_metadata_tag(mat,'BendFoliageSurface' if plants else 'BendMossSurface','2')
    assert u.EditorAssetLibrary.save_loaded_asset(mat,False)
    return mat


def build(road, ground, roads, water, folder, spawn, prefix, stone):
    rng=random.Random(348105)
    x0,y0,_=road.at(48)
    z0=ground.height(x0,y0)
    origin=(x0/100,y0/100,z0/100)
    def part():return dict(origin=origin,v=[],t=[],c=[],uv=[])
    earth,foliage=part(),part()
    def vert(p,x,y,z,c,uv):
        p['v'].append(((x-x0)/100,(y-y0)/100,(z-z0)/100))
        p['c'].append(c);p['uv'].append(uv)
        return len(p['v'])-1
    def face(p,a,b,c):
        v,w,t=[p['v'][i] for i in (a,b,c)]
        area=(w[0]-v[0])*(t[1]-v[1])-(w[1]-v[1])*(t[0]-v[0])
        p['t'].append((a,c,b) if area>0 else (a,b,c))
    # Uneven hummocks sweep obliquely away from the road. Low gaps divide the beds.
    lobes=[(33,6,5.2,2.2,44),(42,9.0,7.3,3.6,61),(51,5.9,6.1,2.2,45),
           (56,11,7.8,4.2,49),(65,6.5,5.1,2.4,47),(35,-5.9,5.8,2.4,46),
           (44,-7.5,6.2,2.9,54),(53,-5.8,5.3,2.3,40),(63,-6.4,6.1,2.6,37)]
    def field(s,d):
        h=0.; moss=0.
        for i,(cs,cd,rs,rd,amp) in enumerate(lobes):
            a=(s-cs)/rs
            b=(d-cd-.22*(s-cs)*math.sin(.4+i*1.7))/rd
            k=clamp(1-a*a-b*b)
            h=max(h,amp*k**1.18)
            moss=max(moss,k)
        phase=math.sin(s*1.09+d*1.45)*.52+math.sin(d*2.7-s*.51)*.3
        channel=clamp((.57-abs(math.sin(.46*s+1.14*d+.77*math.sin(.29*s))))/.57)
        h*=1-.55*channel
        rim=clamp((abs(d)-3.55)/1.0)*clamp((s-27)/1.4)*clamp((69-s)/1.4)
        return (h*(.91+.20*phase)-11)*rim-4,clamp(moss*.91+.25*phase-.51*channel)
    segments=[]
    for r in roads:
        for a,b in zip(r.points,r.points[1:]):
            if max(a[0],b[0])<x0-5500 or min(a[0],b[0])>x0+5500:continue
            if max(a[1],b[1])<y0-5500 or min(a[1],b[1])>y0+5500:continue
            dx,dy=b[0]-a[0],b[1]-a[1]
            if dx*dx+dy*dy:segments.append((a[0],a[1],dx,dy,dx*dx+dy*dy))
    def safe(x,y):
        if water.covers(u.Vector2D(x,y)):return False
        for ax,ay,dx,dy,n in segments:
            t=clamp(((x-ax)*dx+(y-ay)*dy)/n)
            if (x-ax-t*dx)**2+(y-ay-t*dy)**2<355**2:return False
        return True
    # A single XY lattice cannot fold over itself on the inside of a tight bend.
    # Sink every cut edge, including the banks clipped by water and other roads.
    from bend_layout import Road
    nearby=[i for i,s in enumerate(road.stations) if 18<=s<=82]
    lo,hi=nearby[0]-1,nearby[-1]+2
    local=Road(road.points[lo:hi],road.stations[lo:hi])
    step=38.
    grid={}
    for i in range(-90,91):
        for j in range(-90,91):
            x,y=x0+i*step,y0+j*step
            _,s,d=local.nearest(x,y)
            if not (26<s<70 and 3.55<=abs(d)<15):continue
            h,m=field(s,d)
            if h<-10 or not safe(x,y):continue
            grid[i,j]=(x,y,h,m)
    indices={};heights={}
    for (i,j),(x,y,h,m) in grid.items():
        r=next((r for r in (1,2,3) if any((i+a*r,j+b*r) not in grid for a,b in
                  ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)))),4)
        h=-16+(h+16)*clamp((r-1)/2)
        heights[i,j]=h
        indices[i,j]=vert(earth,x,y,ground.height(x,y)+h,(.20,.04+.90*m,.12),(x/148,y/148))
    for i,j in grid:
        for keys in (((i,j),(i+1,j),(i,j+1)),((i+1,j),(i+1,j+1),(i,j+1))):
            if all(k in indices for k in keys) and max(heights[k] for k in keys)>-8:
                face(earth,*[indices[k] for k in keys])
    def surface(s,d):
        x,y,_=road.at(s,d)
        ix,iy=(x-x0)/step,(y-y0)/step
        i,j=math.floor(ix),math.floor(iy);a,b=ix-i,iy-j
        if a+b<=1: weights=[((i,j),1-a-b),((i+1,j),a),((i,j+1),b)]
        else: weights=[((i+1,j+1),a+b-1),((i+1,j),1-b),((i,j+1),1-a)]
        z=ground.height(x,y)
        if all(k in indices for k,_ in weights):
            z=max(z,sum((earth['v'][indices[k]][2]*100+z0)*w for k,w in weights))
        return x,y,z,field(s,d)[1]
    fern_count=leaf_count=0
    for i,(cs,cd,rs,rd,_) in enumerate(lobes):
        # Each colony shares a pigment family. Bronze is restricted to two colonies.
        tip=[(.162,.22,.054),(.20,.26,.067),(.185,.228,.052),(.237,.236,.066)][i%4]
        for j in range(14):
            s=cs+rng.uniform(-rs*.80,rs*.80);d=cd+rng.uniform(-rd*.80,rd*.80)
            x,y,z,m=surface(s,d)
            span=rng.uniform(65,126)
            if not (28<s<68 and abs(d)>3.55+span/100 and safe(x,y) and m>.18):continue
            if math.hypot(x-stone[0],y-stone[1])<155:continue
            angle=rng.uniform(-math.pi,math.pi)
            fern_count+=1
            for k in range(8):
                yaw=angle+k*2.40+rng.uniform(-.21,.21)
                dx,dy=math.cos(yaw),math.sin(yaw)
                reach=span*rng.uniform(.56,1.04)
                lift=span*rng.uniform(.54,.88)*(1.22 if k<3 else .85)
                width=reach*rng.uniform(.12,.19)
                foot=mix((.027,.050,.024),(.052,.080,.027),rng.random())
                hue=tip if k!=6 or i not in (3,7) else (.229,.121,.046)
                last=None
                broad_leaf=fern_count%6==2
                for n in range(11):
                    f=n/10
                    along=reach*f**1.19
                    bend=reach*.13*math.sin(f*2.5)*(1 if k%2 else -1)
                    xx=x+dx*along-dy*bend;yy=y+dy*along+dx*bend
                    zz=z-3+lift*(1.40*math.sin(f*1.66)-.70*f*f)
                    fan=width*max(.025,math.sin(math.pi*f)**.68)
                    w=(fan*(.83 if n%2 else 1.)) if broad_leaf else .25+1.65*(1-f)
                    c=mix(foot,hue,f**.86)
                    row=[vert(foliage,xx-dy*w,yy+dx*w,zz-w*.26,tuple(v*.83 for v in c),(0,f)),
                         vert(foliage,xx,yy,zz,c,(.5,f)),
                         vert(foliage,xx+dy*w,yy-dx*w,zz-w*.34,tuple(v*.91 for v in c),(1,f))]
                    if last:
                        for b in (0,1):
                            face(foliage,last[b],row[b],last[b+1]);face(foliage,last[b+1],row[b],row[b+1])
                    last=row
                    if broad_leaf or n==0 or n==10:continue
                    for hand in (-1,1):
                        # Fold each pinna along a ridge and sweep its tip forward.
                        # The narrow slots between pinnae keep the frond legible in profile.
                        lateral=hand*fan*(1+.10*math.sin(k+2*n+hand))
                        ox,oy=xx-dy*hand*w*.55,yy+dx*hand*w*.55
                        forward=reach*(.065+.045*f)
                        tx,ty=ox-dy*lateral+dx*forward,oy+dx*lateral+dy*forward
                        mx,my=ox+(tx-ox)*.48,oy+(ty-oy)*.48
                        half=reach*(.026+.018*(1-f))
                        tint=mix(c,hue,.18 if hand>0 else .06)
                        drop=abs(lateral)*(.12+.22*f)
                        ids=[vert(foliage,ox,oy,zz,c,(.5,0)),
                             vert(foliage,mx-dx*half,my-dy*half,zz-drop*.42,tuple(v*.78 for v in tint),(0,.5)),
                             vert(foliage,mx,my,zz-drop*.38+1.1,tint,(.5,.5)),
                             vert(foliage,mx+dx*half,my+dy*half,zz-drop*.50,tuple(v*.92 for v in tint),(1,.5)),
                             vert(foliage,tx,ty,zz-drop,mix(tint,hue,.30),(.5,1))]
                        for a,b,cidx in ((0,1,2),(0,2,3),(1,4,2),(2,4,3)):
                            face(foliage,ids[a],ids[b],ids[cidx])
        # Dry litter follows the sheltered flanks. Fold and vary individual blades.
        for j in range(190):
            s=cs+rng.uniform(-rs,rs);d=cd+rng.uniform(-rd,rd)
            x,y,z,m=surface(s,d)
            if not (27.5<s<68.5 and abs(d)>3.72 and safe(x,y) and .05<m<.78):continue
            a=rng.uniform(-math.pi,math.pi);dx,dy=math.cos(a),math.sin(a)
            l=rng.uniform(4,11);w=l*rng.uniform(.22,.48);z+=rng.uniform(1.4,3.1)
            c=rng.choice(((.20,.096,.042),(.229,.133,.056),(.148,.102,.049),(.162,.119,.058),(.11,.079,.039)))
            points=[(-l,0,0),(0,-w,.2),(0,0,1.5),(l,0,1.1),(0,w,-.4)]
            ids=[vert(foliage,x+dx*a-dy*b,y+dy*a+dx*b,z+h,c,((b/w+1)*.5,(a/l+1)*.5)) for a,b,h in points]
            for a,b,c in ((0,1,2),(0,2,4),(1,3,2),(2,3,4)):face(foliage,ids[a],ids[b],ids[c])
            leaf_count+=1
    audit=dict(ferns=fern_count,leaves=leaf_count,meshes={})
    for name,p,plants in [('ShoulderRelief',earth,False),('WoodlandFronds',foliage,True)]:
        sig=hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()[:10]
        path=folder+'/SM_'+name+'_'+sig
        mat=material(folder,plants)
        if u.EditorAssetLibrary.does_asset_exist(path):
            mesh=u.load_asset(path);pos=u.Vector(x0,y0,z0)
        else:mesh,pos=build_tile([p],path,mat)
        assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
        label=prefix+'_'+name
        existing=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
                  if a.get_actor_label()==label and prefix in map(str,a.tags)]
        if len(existing)>1:raise ValueError('Duplicate forest shoulder '+label)
        a=existing[0] if existing else spawn(u.StaticMeshActor,label,pos)
        a.modify()
        c=a.static_mesh_component
        c.modify()
        c.set_static_mesh(mesh);c.set_collision_profile_name('NoCollision')
        c.set_editor_property('receives_decals',False)
        c.set_editor_property('cast_shadow',True)
        c.set_editor_property('visible_in_ray_tracing',False)
        c.set_editor_property('ld_max_draw_distance',7500 if plants else 12500)
        audit['meshes'][a.get_actor_label()]=[path,len(p['t'])]
    return audit
