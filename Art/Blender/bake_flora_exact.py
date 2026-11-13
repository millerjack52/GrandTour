"""Bake source pigment and pre-facing opacity, never illumination or painted shadows."""
import bpy,math,json,numpy as np
from pathlib import Path
from flora_pigment_check import emission_material

def bake_shared_masks(scene,objects,out):
    masks={}
    for ob in objects:
        for source in ob.data.materials:
            if source.name in masks:continue
            m=source.copy();t=m.node_tree;flora=next((n for n in t.nodes if n.type=='GROUP' and n.node_tree and n.node_tree.name.startswith('Flora_Shader')),None)
            if not flora:continue
            for n in list(t.nodes):
                if n.type=='OUTPUT_MATERIAL':t.nodes.remove(n)
            emit=t.nodes.new('ShaderNodeEmission');t.links.new(flora.outputs[1],emit.inputs['Color']);output=t.nodes.new('ShaderNodeOutputMaterial');t.links.new(emit.outputs[0],output.inputs['Surface'])
            bpy.ops.object.select_all(action='DESELECT');bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object;plane.data.materials.append(m)
            image=bpy.data.images.new('SourceMask_'+source.name,width=2048,height=2048,float_buffer=True,alpha=False);image.colorspace_settings.name='Non-Color'
            n=t.nodes.new('ShaderNodeTexImage');n.image=image;t.nodes.active=n
            scene.cycles.samples=4;assert bpy.ops.object.bake(type='EMIT',margin=0)=={'FINISHED'};scene.cycles.samples=1
            scene.view_settings.view_transform='Raw';scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8';scene.render.image_settings.color_mode='RGB'
            path=out/'textures'/('T_SourceMask_'+source.name.replace('.','_')+'.png');image.save_render(str(path),scene=scene);masks[source.name]=str(path)
            bpy.data.objects.remove(plane,do_unlink=True)
    return masks

def bake_assets(scene,objects,recipe,out):
    (out/'textures').mkdir(exist_ok=True);(out/'meshes').mkdir(exist_ok=True)
    result=[]
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
    scene.render.bake.target='IMAGE_TEXTURES';scene.render.bake.use_clear=True
    shared_masks=bake_shared_masks(scene,objects,out)
    for asset,ob in zip(recipe['assets'],objects):
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;ob.hide_render=False
        mesh=ob.data;originals=list(mesh.materials);indices=[p.material_index for p in mesh.polygons]
        # Author a new unique UV channel only where the original export lacks one.
        if len(mesh.uv_layers)<2:
            uv=mesh.uv_layers.new(name='ExactAtlas');mesh.uv_layers.active=uv
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
        mesh.uv_layers.active=mesh.uv_layers[1]
        mats=[];slots=[]
        for source in originals:
            m=source.copy();t=m.node_tree
            flora=next((n for n in t.nodes if n.type=='GROUP' and n.node_tree and n.node_tree.name.startswith('Flora_Shader')),None)
            # Freeze the source's unconnected/default UVs to its mask UV channel.
            for n in list(t.nodes):
                if n.type=='TEX_COORD':
                    uv=t.nodes.new('ShaderNodeUVMap');uv.uv_map=mesh.uv_layers[0].name
                    for link in list(n.outputs['UV'].links):t.links.new(uv.outputs[0],link.to_socket)
            if flora:
                slots.append(dict(name=source.name,foliage=True,soft=flora.inputs[14].default_value,diffuse_weight=flora.inputs[15].default_value,emission_strength=flora.inputs[8].default_value,shared_mask=shared_masks[source.name]))
                colour=flora.outputs[2];alpha=flora.outputs[1]
            else:
                # Preserve the ACTIVE wood+moss output, not a dormant diffuse node.
                m=emission_material(source,mesh.uv_layers[0].name)
                slots.append(dict(name=source.name,foliage=False))
                mats.append((m,None,None,None));continue
            for n in list(t.nodes):
                if n.type=='OUTPUT_MATERIAL':t.nodes.remove(n)
            emit=t.nodes.new('ShaderNodeEmission');output=t.nodes.new('ShaderNodeOutputMaterial');t.links.new(emit.outputs[0],output.inputs['Surface'])
            if colour:t.links.new(colour,emit.inputs['Color'])
            else:emit.inputs['Color'].default_value=inp.default_value
            mats.append((m,emit,colour,alpha))
        for i,(m,*_) in enumerate(mats):mesh.materials[i]=m
        images={}
        for channel in ['Colour','Coverage']:
            image=bpy.data.images.new('Exact_'+asset['key']+'_'+channel,width=2048,height=2048,float_buffer=True,alpha=False)
            image.colorspace_settings.name='Linear Rec.709' if channel=='Colour' else 'Non-Color'
            for i,(m,emit,colour,alpha) in enumerate(mats):
                t=m.node_tree
                if emit is None:
                    if channel=='Coverage':
                        m=m.copy();t=m.node_tree
                        for n in list(t.nodes):
                            if n.type=='OUTPUT_MATERIAL':t.nodes.remove(n)
                        white=t.nodes.new('ShaderNodeEmission');white.inputs['Color'].default_value=(1,1,1,1);o=t.nodes.new('ShaderNodeOutputMaterial');t.links.new(white.outputs[0],o.inputs['Surface'])
                    mesh.materials[i]=m;n=t.nodes.new('ShaderNodeTexImage');n.image=image;t.nodes.active=n;continue
                for l in list(emit.inputs['Color'].links):t.links.remove(l)
                source=colour if channel=='Colour' else alpha
                if source:t.links.new(source,emit.inputs['Color'])
                else:emit.inputs['Color'].default_value=tuple(slots[i].get('colour_default',[1,1,1,1])) if channel=='Colour' else (1,1,1,1)
                n=t.nodes.new('ShaderNodeTexImage');n.image=image;t.nodes.active=n
            assert bpy.ops.object.bake(type='EMIT',margin=16,uv_layer=mesh.uv_layers[1].name)=={'FINISHED'}
            scene.view_settings.view_transform='Standard' if channel=='Colour' else 'Raw'
            # Use an explicit 8-bit sRGB colour file. UE interprets 16-bit PNG
            # source data through a different build path; do not double-encode it.
            scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8';scene.render.image_settings.color_mode='RGB'
            path=out/'textures'/('T_Exact_'+asset['key']+'_'+channel+'.png');image.save_render(str(path),scene=scene)
            images[channel]=str(path)
        # Restore EXACT source materials for the Blender reference beauty render.
        for i,m in enumerate(originals):mesh.materials[i]=m
        for p,i in zip(mesh.polygons,indices):p.material_index=i
        mesh.uv_layers.active=mesh.uv_layers[0]
        oldloc=ob.location.copy();oldscale=ob.scale.copy();ob.location=(0,0,0);ob.scale=(1,1,1)
        path=out/'meshes'/('SM_Exact_'+asset['key']+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',colors_type='SRGB',bake_anim=False,path_mode='STRIP')
        ob.location=oldloc;ob.scale=oldscale;ob.hide_render=True
        asset.update(exact_mesh='SM_Exact_'+asset['key'],exact_slots=slots,textures=images)
        result.append(dict(key=asset['key'],slots=slots,files=images,mesh=str(path),uv_channels=len(mesh.uv_layers)))
        print('EXACT_ASSET_BAKED',asset['key'],flush=True)
    scene.render.engine='BLENDER_EEVEE';scene.view_settings.view_transform='Standard';scene.render.image_settings.color_depth='8'
    (out/'source-export.json').write_text(json.dumps({'ok':True,'assets':result,'illumination_baked':False,'source_mask_blur_baked':True,'source_materials_restored':True},indent=2))
