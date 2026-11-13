"""Painterly colour maps with world-continuous UVs and explicit biome/wet masks."""
import bpy

def build(material,root):
    material.name='M_RF_TerrainBlend'
    nodes=material.node_tree.nodes; links=material.node_tree.links; nodes.clear()
    def node(kind): return nodes.new(kind)
    def mathop(op,a,b=None):
        n=node('ShaderNodeMath'); n.operation=op
        for i,v in enumerate([a,b]):
            if v is None: continue
            if isinstance(v,(int,float)): n.inputs[i].default_value=v
            else: links.new(v,n.inputs[i])
        return n.outputs[0]
    def mix(a,b,factor,blend='MIX'):
        n=node('ShaderNodeMixRGB'); n.blend_type=blend
        for i,v in enumerate([factor,a,b]):
            if isinstance(v,(tuple,list,float,int)): n.inputs[i].default_value=v
            else: links.new(v,n.inputs[i])
        return n.outputs[0]
    def vector(op,a,b=None,scale=None):
        n=node('ShaderNodeVectorMath'); n.operation=op
        links.new(a,n.inputs[0])
        if b is not None: n.inputs[1].default_value=b
        if scale is not None: n.inputs['Scale'].default_value=scale
        return n.outputs[0]
    out=node('ShaderNodeOutputMaterial'); p=node('ShaderNodeBsdfPrincipled')
    p.inputs['Specular IOR Level'].default_value=.15
    links.new(p.outputs[0],out.inputs[0])
    uv=node('ShaderNodeUVMap'); uv.uv_map='UVMap'
    # Gentle coordinate warp breaks ruler-straight repeat lines without more samples.
    xyz=node('ShaderNodeSeparateXYZ'); links.new(uv.outputs[0],xyz.inputs[0])
    offset=node('ShaderNodeCombineXYZ')
    links.new(mathop('MULTIPLY',mathop('SINE',mathop('MULTIPLY',xyz.outputs['Y'],1.71)),.08),offset.inputs['X'])
    links.new(mathop('MULTIPLY',mathop('SINE',mathop('MULTIPLY',xyz.outputs['X'],1.37)),.08),offset.inputs['Y'])
    add=node('ShaderNodeVectorMath'); add.operation='ADD'; links.new(uv.outputs[0],add.inputs[0]); links.new(offset.outputs[0],add.inputs[1])
    # Mirrored coordinates guarantee continuity at generated-image boundaries.
    def repeat(scale):
        return vector('ABSOLUTE',vector('SUBTRACT',vector('SCALE',vector('FRACTION',vector('SCALE',add.outputs[0],scale=scale*.5)),scale=2),(1,1,0)))
    textures=[]
    for filename,scale in [('T_Gravel_Painted_v1.png',2),('T_Meadow_Painted_v1.png',1)]:
        tex=node('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(root/'Art/Textures/GroundPainterly'/filename),check_existing=True)
        tex.interpolation='Linear'; links.new(repeat(scale),tex.inputs['Vector']); textures.append(tex.outputs['Color'])
    gravel,meadow=textures
    meadow=mix(meadow,(.63,.56,.58,1),1,'MULTIPLY')
    masks=node('ShaderNodeUVMap'); masks.uv_map='SurfaceMasks'
    sep=node('ShaderNodeSeparateXYZ'); links.new(masks.outputs[0],sep.inputs[0])
    vc=node('ShaderNodeVertexColor'); vc.layer_name='Color'
    lum=node('ShaderNodeRGBToBW'); links.new(gravel,lum.inputs[0])
    dust=mix((.42,.31,.18,1),(1,1,1,1),0)
    dust=mix(dust,mathop('ADD',.8,mathop('MULTIPLY',lum.outputs[0],.5)),1,'MULTIPLY')
    gravel=mix(gravel,dust,mathop('MULTIPLY',mathop('SUBTRACT',1,vc.outputs['Alpha']),.85))
    base=mix(gravel,meadow,sep.outputs['X'])
    base=mix(base,vc.outputs['Color'],1,'MULTIPLY')
    base=mix(base,(1.25,1.25,1.25,1),1,'MULTIPLY')
    wet=mix((.06,.027,.014,1),mathop('ADD',.55,mathop('MULTIPLY',lum.outputs[0],2)),1,'MULTIPLY')
    base=mix(base,wet,mathop('MULTIPLY',sep.outputs['Y'],.82))
    links.new(base,p.inputs['Base Color'])
    links.new(mathop('SUBTRACT',.9,mathop('MULTIPLY',sep.outputs['Y'],.30)),p.inputs['Roughness'])
    # Existing CC0 normal is only fine surface grain, not a claim of stone-matched relief.
    tex=node('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(root/'Art/Textures/RoadBenchmark/gravel_floor_02_nor_gl_2k.jpg'),check_existing=True)
    tex.image.colorspace_settings.name='Non-Color'; links.new(vector('SCALE',uv.outputs[0],scale=3),tex.inputs['Vector'])
    normal=node('ShaderNodeNormalMap'); normal.uv_map='UVMap'; links.new(tex.outputs['Color'],normal.inputs['Color'])
    links.new(mathop('SUBTRACT',.28,mathop('MULTIPLY',sep.outputs['X'],.12)),normal.inputs['Strength'])
    links.new(normal.outputs[0],p.inputs['Normal'])
    return material
