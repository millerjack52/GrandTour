"""Read-only source binding and LOD audit in the rendered FloraTrail world."""
import unreal as u

def verify(world):
 M=u.MaterialEditingLibrary;S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 rows=[];total=0;seen=set();textures={}
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh;count=c.get_instance_count()
   if not count or not mesh or '/FloraTrail/Meshes/' not in mesh.get_path_name():continue
   source=u.load_asset('/Game/GrandTour/ArtTests/FloraGroup/Assets/'+mesh.get_name());assert source
   lods=S.get_lod_count(mesh);assert lods==3,(mesh.get_name(),lods)
   triangles=mesh.get_static_mesh_description(0).get_triangle_count();assert triangles==source.get_static_mesh_description(0).get_triangle_count(),'LOD0 geometry changed'
   total+=triangles*count
   def bound(mat):
    result={}
    for n in M.get_material_expressions(mat):
     if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):
      tex=n.get_editor_property('texture');assert tex
      result[str(n.get_editor_property('parameter_name'))]=tex
    return result
   for i,entry in enumerate(source.static_materials):
    mat=c.get_material(i);assert mat and mat.get_path_name().startswith('/Game/GrandTour/ArtTests/FloraTrail/Materials/')
    expected=bound(entry.material_interface);actual=bound(mat)
    assert {k:t.get_path_name() for k,t in expected.items()}=={k:t.get_path_name() for k,t in actual.items()},(mesh.get_name(),i)
    for key,t in actual.items():
     if key=='SourceCoverage':assert not t.get_editor_property('srgb')
     if key=='SourceBarkColour':
      assert t.get_editor_property('srgb') and t.get_editor_property('max_texture_size')==4096
      assert [t.blueprint_get_size_x(),t.blueprint_get_size_y()]==[4096,4096],(t.get_path_name(),t.blueprint_get_size_x(),t.blueprint_get_size_y())
     textures[t.get_path_name()]={'dimensions':[t.blueprint_get_size_x(),t.blueprint_get_size_y()],'srgb':bool(t.get_editor_property('srgb'))}
   rows.append({'mesh':mesh.get_name(),'instances':count,'lods':lods,'lod0_triangles':triangles,'cast_shadow':bool(c.get_editor_property('cast_shadow')),'contact_shadow':bool(c.get_editor_property('cast_contact_shadow'))})
 assert len(rows)==8,rows
 return {'ok':True,'components':rows,'textures':textures,'lod0_triangle_upper_bound':total,'scope':'Every populated new foliage component uses the approved source texture bindings; LOD0 triangles preserved, 3 LODs, bark loaded at 4K.'}
