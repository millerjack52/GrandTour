"""Stylized gravel: broad procedural stone faces, limited palette, softened bevels."""
import bpy

def build(original, root):
    mat=original.copy();mat.name='M_GR_PaintedGravel'
    ns=mat.node_tree.nodes;ls=mat.node_tree.links
    p=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    old_color=p.inputs['Base Color'].links[0].from_socket
    old_normal=p.inputs['Normal'].links[0].from_socket
    def node(kind,label):
        n=ns.new(kind);n.label=label;return n
    def wire(value,socket):
        if isinstance(value,(int,float,tuple,list)):socket.default_value=value
        else:ls.new(value,socket)
    def math(op,a,b=0):
        n=node('ShaderNodeMath',op);n.operation=op;wire(a,n.inputs[0]);wire(b,n.inputs[1]);return n.outputs[0]
    def mix(a,b,f):
        n=node('ShaderNodeMixRGB','Paint blend');wire(f,n.inputs[0]);wire(a,n.inputs[1]);wire(b,n.inputs[2]);return n.outputs[0]
    def vector(op,a,b):
        n=node('ShaderNodeVectorMath',op);n.operation=op;wire(a,n.inputs[0]);wire(b,n.inputs['Scale'] if op=='SCALE' else n.inputs[1]);return n.outputs[0]
    def ramp(value,entries,interpolation='LINEAR'):
        n=node('ShaderNodeValToRGB','Restricted painted palette');n.color_ramp.interpolation=interpolation
        for i,(pos,col) in enumerate(entries):
            e=n.color_ramp.elements[i] if i<2 else n.color_ramp.elements.new(pos)
            e.position=pos;e.color=(*col,1)
        wire(value,n.inputs[0]);return n.outputs[0]
    uv=node('ShaderNodeUVMap','Continuous road coordinates');uv.uv_map='UVMap'
    metres=vector('SCALE',uv.outputs[0],3)
    masks=node('ShaderNodeUVMap','Meadow / wetness');masks.uv_map='SurfaceMasks'
    sep=node('ShaderNodeSeparateXYZ','Surface masks');wire(masks.outputs[0],sep.inputs[0])
    vc=node('ShaderNodeVertexColor','Wheel wear');vc.layer_name='Color'
    patch=node('ShaderNodeTexNoise','Broad brush wash');wire(metres,patch.inputs['Vector']);patch.inputs['Scale'].default_value=1.15;patch.inputs['Detail'].default_value=1
    wear=math('MULTIPLY',math('SUBTRACT',1,vc.outputs['Alpha']),math('ADD',.55,math('MULTIPLY',patch.outputs['Fac'],.6)))
    loose=math('SUBTRACT',1,math('MULTIPLY',wear,1.1))
    distort=node('ShaderNodeTexNoise','Chipped outlines');wire(metres,distort.inputs['Vector']);distort.inputs['Scale'].default_value=16;distort.inputs['Detail'].default_value=0
    warped=vector('ADD',metres,vector('SCALE',vector('SUBTRACT',distort.outputs['Color'],(.5,.5,.5)),.026))
    stones=node('ShaderNodeTexVoronoi','Broad gravel faces');stones.voronoi_dimensions='2D';stones.feature='F1';stones.distance='EUCLIDEAN';stones.inputs['Scale'].default_value=13
    wire(warped,stones.inputs['Vector'])
    random=node('ShaderNodeSeparateColor','One colour per stone');wire(stones.outputs['Color'],random.inputs[0])
    stone_color=ramp(random.outputs[0],[(0,(.20,.235,.25)),(.24,(.29,.315,.31)),(.49,(.38,.375,.335)),(.75,(.26,.275,.265)),(.91,(.43,.415,.355))],'CONSTANT')
    # Broad flat centre and a short rounded bevel, without photographic micro-normal noise.
    bevel=node('ShaderNodeMapRange','Broad stone crown');bevel.interpolation_type='SMOOTHERSTEP';bevel.clamp=True
    wire(stones.outputs['Distance'],bevel.inputs['Value']);bevel.inputs['From Min'].default_value=.18;bevel.inputs['From Max'].default_value=.52;bevel.inputs['To Min'].default_value=1;bevel.inputs['To Max'].default_value=0
    coverage=math('MULTIPLY',bevel.outputs[0],math('ADD',.55,math('MULTIPLY',loose,.45)))
    base=ramp(patch.outputs['Fac'],[(.23,(.19,.205,.195)),(.75,(.285,.29,.26))])
    road=mix(base,stone_color,coverage)
    brush=node('ShaderNodeTexNoise','Long restrained paint dabs');brush.inputs['Scale'].default_value=1;brush.inputs['Detail'].default_value=0
    wire(vector('MULTIPLY',metres,(8,48,1)),brush.inputs['Vector'])
    wash=ramp(brush.outputs['Fac'],[(.30,(.89,.91,.93)),(.70,(1.02,1.01,.98))])
    multiply=node('ShaderNodeMixRGB','Subtle surface brushwork');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=.4;wire(road,multiply.inputs[1]);wire(wash,multiply.inputs[2]);road=multiply.outputs[0]
    wet=mix(road,(.06,.05,.036,1),math('MULTIPLY',sep.outputs['Y'],.82))
    wire(mix(wet,old_color,sep.outputs['X']),p.inputs['Base Color'])
    bump=node('ShaderNodeBump','Stone bevel relief');bump.inputs['Distance'].default_value=.014;bump.inputs['Strength'].default_value=.65
    wire(math('MULTIPLY',bevel.outputs[0],math('ADD',.35,math('MULTIPLY',loose,.65))),bump.inputs['Height'])
    wire(mix(bump.outputs['Normal'],old_normal,sep.outputs['X']),p.inputs['Normal'])
    p.inputs['Specular IOR Level'].default_value=.12
    return mat
