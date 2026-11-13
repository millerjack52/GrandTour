"""Bake selected purchased Rock Master models for a bounded Unreal bank trial."""
import bpy,json,math,re,sys
from pathlib import Path
from mathutils import Vector
O=Path('C:/GrandTour/Art/Export/FloraDrive/RockMaster');O.mkdir(parents=True,exist_ok=True)
S='D:/GrandTourAssets/FlippedNormals/Rock Master Tools/DATA.blend'
names=['Asset_Large_Rock_005','Asset_Large_Rock_053','Asset_Large_Rock_077','Asset_Medium_Rock_013','Asset_Medium_Rock_085']
with bpy.data.libraries.load(S,link=False) as (src,dst):dst.objects=names
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.render.image_settings.file_format='PNG'
scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
scene.render.bake.margin=12;scene.render.bake.target='IMAGE_TEXTURES'
rows=[]
for source in dst.objects:
    assert source;scene.collection.objects.link(source);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();mesh=bpy.data.meshes.new_from_object(source.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
    o=bpy.data.objects.new('SM_RM_'+source.name,mesh);scene.collection.objects.link(o);o.matrix_world=source.matrix_world.copy()
    source.hide_render=True;source.hide_set(True)
    for a in bpy.context.selected_objects:a.select_set(False)
    o.select_set(True);bpy.context.view_layer.objects.active=o
    mesh.calc_loop_triangles();original=len(mesh.loop_triangles);budget=18000 if 'Large' in source.name else 6500
    if original>budget:
        dec=o.modifiers.new('Game budget','DECIMATE');dec.ratio=budget/original;bpy.ops.object.modifier_apply(modifier=dec.name)
    mesh=o.data;mesh.calc_loop_triangles()
    mats=[]
    for i,m in enumerate(mesh.materials):
        assert m and m.use_nodes,(source.name,m)
        cp=m.copy();mesh.materials[i]=cp;mats.append(cp)
    # Keep original mapping for any source texture nodes; bake to a separate UV.
    uv=mesh.uv_layers.new(name='GameBake');mesh.uv_layers.active=uv;uv.active_render=True
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
    textures={}
    for channel,kind in [('Colour','DIFFUSE'),('Normal','NORMAL'),('Roughness','ROUGHNESS')]:
        im=bpy.data.images.new(o.name+'_'+channel,width=1024,height=1024,alpha=False)
        im.colorspace_settings.name='sRGB' if channel=='Colour' else 'Non-Color'
        for m in mats:
            node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;m.node_tree.nodes.active=node;node.select=True
        assert bpy.ops.object.bake(type=kind,uv_layer='GameBake')=={'FINISHED'}
        filename=o.name+'_'+channel+'.png';im.filepath_raw=str(O/filename);im.file_format='PNG';im.save();textures[channel]=filename
    # Export a single UV channel, centred at the bottom for reliable embedding.
    baked=[tuple(x.uv) for x in mesh.uv_layers['GameBake'].data]
    for uv in list(mesh.uv_layers):mesh.uv_layers.remove(uv)
    uv=mesh.uv_layers.new(name='UVMap')
    for el,value in zip(uv.data,baked):el.uv=value
    # Materials were baked in original coordinates. Transform geometry only afterwards.
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    lo=Vector([min(v.co[k] for v in mesh.vertices) for k in range(3)]);hi=Vector([max(v.co[k] for v in mesh.vertices) for k in range(3)])
    pivot=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for v in mesh.vertices:v.co-=pivot
    o.location=(0,0,0);mesh.materials.clear();placeholder=bpy.data.materials.new(o.name+'_Baked');mesh.materials.append(placeholder)
    for p in mesh.polygons:p.material_index=0
    bpy.ops.export_scene.fbx(filepath=str(O/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='FACE',bake_anim=False,path_mode='STRIP')
    mesh.calc_loop_triangles();row={'source':source.name,'mesh':o.name,'source_triangles':original,'triangles':len(mesh.loop_triangles),'dimensions_m':list(hi-lo),'textures':textures,'texture_size':1024};rows.append(row)
    (O/'export-report.json').write_text(json.dumps({'ok':False,'source':S,'meshes':rows},indent=2));print('ROCK_EXPORTED',row,flush=True)
    bpy.data.objects.remove(o,do_unlink=True);bpy.data.objects.remove(source,do_unlink=True)
(O/'export-report.json').write_text(json.dumps({'ok':True,'source':S,'creator':'MeiU / Rock Master Tools','meshes':rows},indent=2))
