"""Branch-aligned bark material and shallow longitudinal relief for willow studies."""
import bpy
import math
import numpy as np
from mathutils import Vector
from pathlib import Path


def apply_bark(ob, axes):
    mesh=ob.data
    # Work in physical metres. Each chart follows an authored curved limb.
    starts=[]; ends=[]; lengths=[]; radii=[]; frames=[]; distances=[]; ids=[]
    for chart,(points,rr) in enumerate(axes):
        distance=0
        for i in range(len(points)-1):
            a=Vector(points[i]); b=Vector(points[i+1]); delta=b-a
            length=delta.length; tangent=delta.normalized()
            u=tangent.cross(Vector((0,1,0))).normalized()
            if u.length<.1: u=tangent.cross(Vector((1,0,0))).normalized()
            starts.append(tuple(a)); ends.append(tuple(b)); lengths.append(length)
            radii.append((rr[i],rr[i+1])); frames.append((tuple(u),tuple(tangent.cross(u))))
            distances.append(distance); ids.append(chart); distance+=length
    a=np.asarray(starts); delta=np.asarray(ends)-a; ll=np.asarray(lengths)
    rr=np.asarray(radii); frames=np.asarray(frames); distances=np.asarray(distances)
    xyz=np.asarray([tuple(v.co) for v in mesh.vertices])
    coords=np.zeros((len(xyz),3)); radial=np.zeros_like(coords)
    chosen_chart=np.zeros(len(xyz),dtype=int); ids=np.asarray(ids)
    wood_vertices=sorted({i for p in mesh.polygons if p.material_index==0 for i in p.vertices})
    for lo in range(0,len(wood_vertices),2048):
        vi=wood_vertices[lo:lo+2048]; q=xyz[vi]
        rel=q[:,None,:]-a[None,:,:]
        t=np.clip(np.sum(rel*delta[None,:,:],axis=2)/(ll[None,:]**2),0,1)
        off=rel-t[:,:,None]*delta[None,:,:]
        rad=np.sqrt(np.sum(off*off,axis=2))
        radius=rr[None,:,0]*(1-t)+rr[None,:,1]*t
        # Prefer the limb whose cylindrical surface actually contains the vertex.
        score=np.abs(rad-radius)+.08*rad
        which=np.argmin(score,axis=1); row=np.arange(len(vi))
        chosen_chart[vi]=ids[which]
        radial_vector=off[row,which]; radius_here=radius[row,which]
        angle=np.arctan2(np.sum(radial_vector*frames[which,1],axis=1),np.sum(radial_vector*frames[which,0],axis=1))
        along=distances[which]+t[row,which]*ll[which]
        # Angle is the chart U. Material scales it by local circumference radius.
        coords[vi,0]=angle
        coords[vi,1]=along
        coords[vi,2]=radius_here
        radial[vi]=radial_vector/np.maximum(np.linalg.norm(radial_vector,axis=1)[:,None],.001)
    uv=mesh.uv_layers.new(name='BarkFlow')
    radius_attribute=mesh.attributes.new(name='BarkRadius',type='FLOAT',domain='POINT')
    for i in wood_vertices: radius_attribute.data[i].value=float(coords[i,2])
    for p in mesh.polygons:
        if p.material_index!=0: continue
        vi=list(p.vertices)
        face_coords=coords[vi].copy()
        if len(set(chosen_chart[vi]))>1:
            # Never interpolate coordinates belonging to two unrelated limbs.
            chart=int(chosen_chart[vi[np.argmax(coords[vi,2])]])
            segments=np.flatnonzero(ids==chart)
            rel=xyz[vi,None,:]-a[None,segments,:]
            t=np.clip(np.sum(rel*delta[None,segments,:],axis=2)/(ll[None,segments]**2),0,1)
            off=rel-t[:,:,None]*delta[None,segments,:]
            dist=np.sqrt(np.sum(off*off,axis=2))
            radius=rr[None,segments,0]*(1-t)+rr[None,segments,1]*t
            which=np.argmin(np.abs(dist-radius)+.08*dist,axis=1); row=np.arange(len(vi))
            seg=segments[which]; radial_vector=off[row,which]
            face_coords[:,0]=np.arctan2(np.sum(radial_vector*frames[seg,1],axis=1),np.sum(radial_vector*frames[seg,0],axis=1))
            face_coords[:,1]=distances[seg]+t[row,which]*ll[seg]
            face_coords[:,2]=radius[row,which]
        angles=face_coords[:,0]
        unwrap=max(angles)-min(angles)>math.pi
        for j,li in enumerate(p.loop_indices):
            angle,along,radius=face_coords[j]
            if unwrap and angle<0: angle+=math.tau
            uv.data[li].uv=(angle*radius,along)
        # Lighting should describe bark relief, not arbitrary remesh triangles.
        p.use_smooth=True
    for i in wood_vertices:
        angle,along,radius=coords[i]
        if radius<.075: continue
        # Uneven, broken ridges follow the branch; these remain subtle at distance.
        wave=math.sin(angle*11+.65*math.sin(along*2.3))+ .38*math.sin(angle*19-along*.7)
        amount=min(.009,radius*.025)*wave
        mesh.vertices[i].co += Vector(tuple(radial[i]))*amount

    # Blend two separate texture samples at forks, rather than interpolating
    # unrelated coordinates and producing a stretched ring around the joint.
    charts=sorted(set(ids)); vc=len(wood_vertices)
    chart_coord=np.empty((vc,len(charts),3),dtype=np.float32)
    chart_score=np.empty((vc,len(charts)),dtype=np.float32)
    vertex_lookup={v:i for i,v in enumerate(wood_vertices)}
    wraps=[]
    for ci,chart in enumerate(charts):
        segments=np.flatnonzero(ids==chart)
        wraps.append(max(1,round(math.tau*rr[segments[0],0])))
        for lo in range(0,vc,2048):
            vs=wood_vertices[lo:lo+2048]; rel=xyz[vs,None,:]-a[None,segments,:]
            t=np.clip(np.sum(rel*delta[None,segments,:],axis=2)/(ll[None,segments]**2),0,1)
            off=rel-t[:,:,None]*delta[None,segments,:]
            dist=np.sqrt(np.sum(off*off,axis=2)); radius=rr[None,segments,0]*(1-t)+rr[None,segments,1]*t
            scores=np.abs(dist-radius)+.08*dist
            which=np.argmin(scores,axis=1); row=np.arange(len(vs)); seg=segments[which]
            rv=off[row,which]
            chart_coord[lo:lo+len(vs),ci,0]=np.arctan2(np.sum(rv*frames[seg,1],axis=1),np.sum(rv*frames[seg,0],axis=1))
            chart_coord[lo:lo+len(vs),ci,1]=distances[seg]+t[row,which]*ll[seg]
            chart_coord[lo:lo+len(vs),ci,2]=radius[row,which]
            chart_score[lo:lo+len(vs),ci]=scores[row,which]
    uv2=mesh.uv_layers.new(name='BarkFlowSecondary')
    blend_attr=mesh.color_attributes.new(name='BarkBlend',type='FLOAT_COLOR',domain='CORNER')
    for p in mesh.polygons:
        if p.material_index!=0: continue
        vi=[vertex_lookup[i] for i in p.vertices]
        pair=sorted(np.argsort(np.mean(chart_score[vi,:],axis=0))[:2])
        for channel,layer in enumerate((uv,uv2)):
            ci=pair[channel]; fc=chart_coord[vi,ci,:].copy()
            if np.max(fc[:,0])-np.min(fc[:,0])>math.pi: fc[fc[:,0]<0,0]+=math.tau
            for j,li in enumerate(p.loop_indices): layer.data[li].uv=(fc[j,0]/math.tau*wraps[ci],fc[j,1])
        for j,li in enumerate(p.loop_indices):
            first,second=chart_score[vi[j],pair]
            weight=1/(1+math.exp(max(-40,min(40,float((second-first)/.075)))))
            blend_attr.data[li].color=(weight,weight,weight,1)

    mat=bpy.data.materials.new('M_RF_Willow_BarkPainted'); mat.use_nodes=True
    nt=mat.node_tree; nt.nodes.clear(); nodes=nt.nodes; links=nt.links
    def node(kind,label):
        n=nodes.new(kind); n.label=label; n.name=label; return n
    def mathnode(op,left,right=None):
        n=node('ShaderNodeMath',op); n.operation=op
        if isinstance(left,(int,float)): n.inputs[0].default_value=left
        else: links.new(left,n.inputs[0])
        if right is not None:
            if isinstance(right,(int,float)): n.inputs[1].default_value=right
            else: links.new(right,n.inputs[1])
        return n.outputs[0]
    def scale(socket,values,label):
        n=node('ShaderNodeVectorMath',label); n.operation='MULTIPLY'
        links.new(socket,n.inputs[0]); n.inputs[1].default_value=values
        return n.outputs['Vector']
    def noise(socket,detail,label):
        n=node('ShaderNodeTexNoise',label); n.inputs['Scale'].default_value=1
        n.inputs['Detail'].default_value=detail; n.inputs['Roughness'].default_value=.65
        links.new(socket,n.inputs['Vector']); return n.outputs['Fac']
    def ramp(socket,stops,label):
        n=node('ShaderNodeValToRGB',label); cr=n.color_ramp
        cr.elements.remove(cr.elements[1]); cr.elements[0].position=stops[0][0]; cr.elements[0].color=(*stops[0][1],1)
        for pos,color in stops[1:]: cr.elements.new(pos).color=(*color,1)
        links.new(socket,n.inputs[0]); return n.outputs['Color']

    uvnode=node('ShaderNodeUVMap','Grain follows the branch'); uvnode.uv_map='BarkFlow'
    sep=node('ShaderNodeSeparateXYZ','Branch coordinates'); links.new(uvnode.outputs[0],sep.inputs[0])
    radius=node('ShaderNodeAttribute','Local limb radius'); radius.attribute_name='BarkRadius'
    combine=node('ShaderNodeCombineXYZ','Physical bark coordinates')
    links.new(sep.outputs['X'],combine.inputs['X'])
    links.new(sep.outputs['Y'],combine.inputs['Y'])
    physical=combine.outputs[0]
    warp=noise(scale(physical,(8,2,1),'Bending grain'),3,'Irregular growth')
    warped=node('ShaderNodeCombineXYZ','Meandering furrows')
    links.new(mathnode('ADD',combine.inputs['X'].links[0].from_socket,mathnode('MULTIPLY',mathnode('SUBTRACT',warp,.5),.038)),warped.inputs['X'])
    links.new(sep.outputs['Y'],warped.inputs['Y'])
    grain=warped.outputs[0]
    plates=node('ShaderNodeTexVoronoi','Unequal elongated bark plates'); plates.voronoi_dimensions='2D'; plates.feature='DISTANCE_TO_EDGE'
    plates.inputs['Scale'].default_value=1
    links.new(scale(grain,(12,2.5,1),'Bark strips'),plates.inputs['Vector'])
    broad=noise(scale(grain,(12,3,1),'Broken lengthwise brush strokes'),1,'Weathered bark colour')
    fine=noise(scale(grain,(95,11,1),'Fine fibres'),2,'Fine surface grain')
    base=ramp(broad,[(.28,(.055,.048,.038)),(.40,(.105,.084,.057)),(.48,(.18,.144,.093)),(.55,(.13,.135,.115)),(.62,(.28,.235,.16)),(.73,(.21,.167,.10))],'Weathered grey and warm wood')
    nodes['Weathered grey and warm wood'].color_ramp.interpolation='CONSTANT'
    groove=ramp(plates.outputs['Distance'],[(0,(.76,.76,.76)),(.016,(.82,.82,.82)),(.05,(1,1,1))],'Narrow fissures only')
    color=node('ShaderNodeMixRGB','Grain in the surface'); color.blend_type='MULTIPLY'; color.inputs[0].default_value=1
    links.new(base,color.inputs[1]); links.new(groove,color.inputs[2])
    bump=node('ShaderNodeBump','Shallow bark relief'); bump.inputs['Strength'].default_value=.3; bump.inputs['Distance'].default_value=.006
    links.new(mathnode('ADD',mathnode('MULTIPLY',plates.outputs['Distance'],.3),mathnode('MULTIPLY',fine,.25)),bump.inputs['Height'])
    p=node('ShaderNodeBsdfPrincipled','Matte bark'); p.inputs['Roughness'].default_value=.92; p.inputs['Specular IOR Level'].default_value=.18
    links.new(color.outputs[0],p.inputs['Base Color']); links.new(bump.outputs[0],p.inputs['Normal'])
    out=node('ShaderNodeOutputMaterial','Bark output'); links.new(p.outputs[0],out.inputs['Surface'])
    # Use an actual painted surface instead of noise contours for visible colour.
    texture_path=Path(__file__).resolve().parents[1]/'Textures/WillowBark/willow_bark_painted_v1.png'
    image=bpy.data.images.load(str(texture_path),check_existing=True); image.pack()
    tex=node('ShaderNodeTexImage','Painted willow bark'); tex.image=image; tex.extension='REPEAT'
    links.new(scale(uvnode.outputs[0],(1,.5,1),'One metre around, two metres along'),tex.inputs['Vector'])
    uvnode2=node('ShaderNodeUVMap','Second limb at fork'); uvnode2.uv_map='BarkFlowSecondary'
    tex2=node('ShaderNodeTexImage','Bark across the fork'); tex2.image=image; tex2.extension='REPEAT'
    links.new(scale(uvnode2.outputs[0],(1,.5,1),'Second limb texture scale'),tex2.inputs['Vector'])
    mix=node('ShaderNodeMixRGB','Soft transition through the fork')
    blendnode=node('ShaderNodeVertexColor','Fork blend weight'); blendnode.layer_name='BarkBlend'
    links.new(blendnode.outputs['Color'],mix.inputs[0]); links.new(tex.outputs['Color'],mix.inputs[1]); links.new(tex2.outputs['Color'],mix.inputs[2])
    links.new(mix.outputs[0],p.inputs['Base Color'])
    bump.inputs['Strength'].default_value=.23; bump.inputs['Distance'].default_value=.014
    links.new(mix.outputs[0],bump.inputs['Height'])
    # Remove disconnected prototype nodes so the saved material is understandable.
    used=set()
    def visit(n):
        if n in used: return
        used.add(n)
        for socket in n.inputs:
            for link in socket.links: visit(link.from_node)
    visit(out)
    for n in list(nodes):
        if n not in used: nodes.remove(n)
    # Arrange editable shader nodes in rough functional columns.
    for i,n in enumerate(nodes): n.location=((i//7)*230,-(i%7)*160)
    mesh.materials[0]=mat
    mesh.update()
