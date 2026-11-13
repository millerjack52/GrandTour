"""Render original pigment/coverage without illumination for conversion checks."""
import bpy
from mathutils import Vector

def emission_material(source,uv_name='UVMap'):
    copies={}
    def convert(t):
        for n in list(t.nodes):
            if n.type=='GROUP' and n.node_tree:
                key=n.node_tree.name
                if key not in copies:
                    c=n.node_tree.copy();copies[key]=c;convert(c)
                n.node_tree=copies[key]
            elif n.type=='TEX_COORD':
                uv=t.nodes.new('ShaderNodeUVMap');uv.uv_map=uv_name
                for link in list(n.outputs['UV'].links):t.links.new(uv.outputs[0],link.to_socket)
            elif n.type in ['BSDF_DIFFUSE','BSDF_TRANSLUCENT','BSDF_PRINCIPLED']:
                emit=t.nodes.new('ShaderNodeEmission');inp=n.inputs.get('Color') or n.inputs.get('Base Color');emit.inputs['Color'].default_value=inp.default_value
                if inp.is_linked:t.links.new(inp.links[0].from_socket,emit.inputs['Color'])
                for link in list(n.outputs[0].links):t.links.new(emit.outputs[0],link.to_socket)
                t.nodes.remove(n)
    m=source.copy();convert(m.node_tree);return m

def render_pigment(scene,objects,recipe,render,white=False):
    copies={}
    def tree_copy(tree):
        if tree.name in copies:return copies[tree.name]
        t=tree.copy();copies[tree.name]=t
        for n in list(t.nodes):
            if n.type=='GROUP' and n.node_tree:n.node_tree=tree_copy(n.node_tree)
            elif n.type in ['BSDF_DIFFUSE','BSDF_TRANSLUCENT','BSDF_PRINCIPLED']:
                emit=t.nodes.new('ShaderNodeEmission');inp=n.inputs.get('Color') or n.inputs.get('Base Color');emit.inputs['Color'].default_value=inp.default_value
                if white:emit.inputs['Color'].default_value=(1,1,1,1)
                elif inp.is_linked:t.links.new(inp.links[0].from_socket,emit.inputs['Color'])
                for link in list(n.outputs[0].links):t.links.new(emit.outputs[0],link.to_socket)
                t.nodes.remove(n)
        return t
    for ob in scene.objects:
        if ob not in objects and ob.type=='MESH':ob.hide_render=True
        if ob.type=='LIGHT':ob.data.energy=0
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=0
    pos=Vector(recipe['cases'][0]['camera']);target=Vector(recipe['cases'][0]['target']);scene.camera.location=pos;scene.camera.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler()
    for asset,ob in zip(recipe['assets'],objects):
        original=list(ob.data.materials)
        for i,m in enumerate(original):
            c=m.copy();t=c.node_tree
            for n in list(t.nodes):
                if n.type=='GROUP' and n.node_tree:n.node_tree=tree_copy(n.node_tree)
                elif n.type in ['BSDF_DIFFUSE','BSDF_TRANSLUCENT','BSDF_PRINCIPLED']:
                    emit=t.nodes.new('ShaderNodeEmission');inp=n.inputs.get('Color') or n.inputs.get('Base Color');emit.inputs['Color'].default_value=inp.default_value
                    if white:emit.inputs['Color'].default_value=(1,1,1,1)
                    elif inp.is_linked:t.links.new(inp.links[0].from_socket,emit.inputs['Color'])
                    for link in list(n.outputs[0].links):t.links.new(emit.outputs[0],link.to_socket)
                    t.nodes.remove(n)
            ob.data.materials[i]=c
        ob.hide_render=False;render(asset['key']+('_opacity_face' if white else '_pigment_face'));ob.hide_render=True
        for i,m in enumerate(original):ob.data.materials[i]=m
