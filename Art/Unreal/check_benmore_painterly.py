"""Review the saved material treatment using the same two vistas and rain view."""
from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/check_benmore_daylight.py');ctx={}
exec(p.read_text().rsplit("exec(compile(source,__file__,'exec'))",1)[0],ctx)
source=ctx['source'].replace('Art/Export/BenmoreDaylight','Art/Export/BenmorePainterly').replace('13.6','13.3')
source=source.replace("=='M_Benmore_VistaLake'","=='M_Painterly_Lake'")
# An unattended editor can run only a few frames per second while compiling.
# Increase review-only creation throughput so the first camera isn't captured
# with just the distant grass clusters populated. Gameplay settings stay saved
# at their original values.
source=source.replace("'t.MaxFPS 30']:console(cmd)","'t.MaxFPS 30','grass.MaxCreatePerFrame 8','grass.MaxAsyncTasks 16']:console(cmd)")
extra='''            landscape=next(a for a in actors if isinstance(a,u.Landscape))
            surface=landscape.get_editor_property('landscape_material');assert surface.get_name()=='M_Painterly_Terrain'
            gout=next(n for n in u.MaterialEditingLibrary.get_material_expressions(surface) if isinstance(n,u.MaterialExpressionLandscapeGrassOutput))
            linked=u.MaterialEditingLibrary.get_inputs_for_material_expression(surface,gout)
            assert len(linked)==5 and all(n and isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture').get_name()=='T_Benmore_VegetationMask' for n in linked), 'Grass outputs must retain all five original mask connections'
            for entry in gout.get_editor_property('grass_types'):
                gt=entry.get_editor_property('grass_type');assert '/Painterly/' in gt.get_path_name()
                for v in gt.get_editor_property('grass_varieties'):
                    assert v.get_editor_property('grass_mesh').get_name() in ['SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine']
                    assert v.get_editor_property('override_materials')[0].get_name()=='M_Painterly_Tussock'
            for hill in hills:assert hill.static_mesh_component.get_material(0).get_name()=='M_Painterly_Hills'
            report['painterly']={'world_space_surface':True,'original_tussock_meshes':True,'map_owned_overrides':True,'screen_filter':False}
'''
needle="            phase='begin';last=now";assert source.count(needle)==1;source=source.replace(needle,extra+needle)
exec(compile(source,__file__,'exec'))
