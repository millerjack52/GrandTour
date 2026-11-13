"""Blender gravel study: matched normal/detail scales, existing meadow/wet masks."""
import bpy

def build(original, root):
    mat=original.copy(); mat.name='M_GR_GravelRoad'
    ns=mat.node_tree.nodes; ls=mat.node_tree.links
    p=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    old_color=p.inputs['Base Color'].links[0].from_socket
    old_normal=p.inputs['Normal'].links[0].from_socket
    def node(kind,label):
        n=ns.new(kind); n.label=label; return n
    def wire(value,socket):
        if isinstance(value,(int,float,tuple,list)):socket.default_value=value
        else:ls.new(value,socket)
    def math(op,a,b=0):
        n=node('ShaderNodeMath',op); n.operation=op
        wire(a,n.inputs[0]); wire(b,n.inputs[1]); return n.outputs[0]
    def mix(a,b,f):
        n=node('ShaderNodeMixRGB','Mix'); wire(f,n.inputs[0]);wire(a,n.inputs[1]);wire(b,n.inputs[2]);return n.outputs[0]
    def scale(v,s):
        n=node('ShaderNodeVectorMath','Metre scale');n.operation='SCALE';wire(v,n.inputs[0]);n.inputs['Scale'].default_value=s;return n.outputs[0]
    uv=node('ShaderNodeUVMap','Road continuous metre coordinates');uv.uv_map='UVMap'
    masks=node('ShaderNodeUVMap','Meadow / moisture');masks.uv_map='SurfaceMasks'
    sep=node('ShaderNodeSeparateXYZ','Masks');ls.new(masks.outputs[0],sep.inputs[0])
    vc=node('ShaderNodeVertexColor','Existing wheel wear');vc.layer_name='Color'
    noise=node('ShaderNodeTexNoise','Patch-scale gravel redistribution')
    ls.new(scale(uv.outputs[0],3),noise.inputs['Vector']);noise.inputs['Scale'].default_value=.65;noise.inputs['Detail'].default_value=2
    # Worn tracks retain aggregate; broken patch modulation avoids painted stripes.
    wear=math('MULTIPLY',math('SUBTRACT',1,vc.outputs['Alpha']),math('ADD',.48,math('MULTIPLY',noise.outputs['Fac'],.65)))
    loose=math('SUBTRACT',.94,math('MULTIPLY',wear,1.05))
    def texture(file,coords,normal=False):
        n=node('ShaderNodeTexImage',file);n.image=bpy.data.images.load(str(root/'Art/Textures/RoadBenchmark'/file),check_existing=True)
        if normal:n.image.colorspace_settings.name='Non-Color'
        ls.new(coords,n.inputs['Vector']);return n.outputs['Color']
    coarse_uv=scale(uv.outputs[0],3/5.4);fine_uv=scale(uv.outputs[0],3/2.4)
    def colour(file,coords):
        rgb=texture(file,coords);bw=node('ShaderNodeRGBToBW','Restrained grey aggregate');ls.new(rgb,bw.inputs[0])
        remap=node('ShaderNodeMapRange','Detail contrast')
        wire(bw.outputs[0],remap.inputs['Value']);remap.inputs['From Min'].default_value=.10;remap.inputs['From Max'].default_value=.52
        ramp=node('ShaderNodeValToRGB','Warm slate / limestone palette')
        ramp.color_ramp.elements[0].color=(.070,.077,.072,1)
        ramp.color_ramp.elements[1].color=(.46,.445,.39,1)
        ls.new(remap.outputs[0],ramp.inputs[0]);return ramp.outputs[0]
    fine=colour('gravel_floor_04_diff_2k.jpg',fine_uv)
    coarse=colour('gravel_floor_02_diff_2k.jpg',coarse_uv)
    road=mix(fine,coarse,loose)
    # Small broad variation, not random high-frequency colour speckle.
    mult=node('ShaderNodeMixRGB','Broad tonal drift');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1
    wire(road,mult.inputs[1]);wire(math('ADD',.87,math('MULTIPLY',noise.outputs['Fac'],.26)),mult.inputs[2]);road=mult.outputs[0]
    wet=mix(road,(.06,.05,.036,1),math('MULTIPLY',sep.outputs['Y'],.82))
    wire(mix(wet,old_color,sep.outputs['X']),p.inputs['Base Color'])
    normals=[]
    for file,coords,strength in [('gravel_floor_04_nor_gl_2k.jpg',fine_uv,.45),('gravel_floor_02_nor_gl_2k.jpg',coarse_uv,1.1)]:
        nm=node('ShaderNodeNormalMap','Matched aggregate relief');nm.uv_map='UVMap';nm.inputs['Strength'].default_value=strength
        wire(texture(file,coords,True),nm.inputs['Color']);normals.append(nm.outputs[0])
    wire(mix(mix(normals[0],normals[1],loose),old_normal,sep.outputs['X']),p.inputs['Normal'])
    # No displacement: existing smooth road shape and tyre collision stay intact.
    return mat
