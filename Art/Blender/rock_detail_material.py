"""Shared rock material for the forest study; all relief is shading only."""
import bpy
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FirstSection/ForestFloorRevision')


def build():
    m=bpy.data.materials.new('M_Study_WeatheredRock_Detail');m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Specular IOR Level'].default_value=.23
    uv=n.new('ShaderNodeTexCoord')
    def tex(name,data=False):
        node=n.new('ShaderNodeTexImage');node.label=name
        node.image=bpy.data.images.load(str(OUT/'Textures'/name),check_existing=True)
        node.image.reload();node.image.colorspace_settings.name='Non-Color' if data else 'sRGB'
        l.new(uv.outputs['UV'],node.inputs['Vector']);return node.outputs['Color']
    def math(op,a,b):
        node=n.new('ShaderNodeMath');node.operation=op
        for i,value in enumerate((a,b)):
            if isinstance(value,(float,int)):node.inputs[i].default_value=value
            else:l.new(value,node.inputs[i])
        return node.outputs[0]
    def mix(a,b,factor):
        node=n.new('ShaderNodeMixRGB')
        for i,value in enumerate((factor,a,b)):
            if isinstance(value,(float,int)):node.inputs[i].default_value=value
            else:l.new(value,node.inputs[i])
        return node.outputs[0]
    def split(source):
        node=n.new('ShaderNodeSeparateColor');l.new(source,node.inputs[0]);return node.outputs
    rock=tex('T_RockWeather_Colour.png')
    normaltex=tex('T_RockWeather_Normal.png',True)
    data=split(tex('T_RockWeather_RAH.png',True))
    moss=tex('T_RockMoss_Colour.png')
    mossdata=split(tex('T_RockMoss_Data.png',True))
    attr=n.new('ShaderNodeVertexColor');attr.layer_name='Color'
    basal=split(attr.outputs['Color'])['Red']
    # The coarse mask only locates the habitat. Texture coverage breaks its edge;
    # modest cavity influence encourages growth within eroded surface hollows.
    coverage=math('ADD',math('MULTIPLY',basal,1.35),math('MULTIPLY',mossdata['Red'],.8))
    coverage=math('ADD',coverage,math('MULTIPLY',math('SUBTRACT',1.,data['Green']),.4))
    edge=n.new('ShaderNodeMapRange');edge.interpolation_type='SMOOTHSTEP';edge.clamp=True
    edge.inputs['From Min'].default_value=.60;edge.inputs['From Max'].default_value=.99
    l.new(coverage,edge.inputs['Value']);mask=edge.outputs[0]
    l.new(mix(rock,moss,mask),p.inputs['Base Color'])
    l.new(math('ADD',math('MULTIPLY',data['Red'],math('SUBTRACT',1.,mask)),math('MULTIPLY',mossdata['Green'],mask)),p.inputs['Roughness'])
    normal=n.new('ShaderNodeNormalMap');normal.space='TANGENT';normal.uv_map='UVMap'
    l.new(normaltex,normal.inputs['Color'])
    l.new(math('SUBTRACT',1.,math('MULTIPLY',mask,.55)),normal.inputs['Strength'])
    # Derivative bump is applied about the existing structural normal, avoiding
    # colour-style averaging of two encoded tangent-space normal maps.
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.003
    bump.inputs['Strength'].default_value=.8
    l.new(math('MULTIPLY',mossdata['Blue'],mask),bump.inputs['Height'])
    l.new(normal.outputs['Normal'],bump.inputs['Normal']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
