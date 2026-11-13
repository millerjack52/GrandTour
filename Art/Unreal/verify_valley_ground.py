"""Verify reload and preserve the valley treatment through floor rebuilds."""
import unreal as u,sys,json,traceback,hashlib
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
import valley_ground as vg,forest_ground
from forest_shaders import connected_nodes
mel=u.MaterialEditingLibrary
def signature(m):
    nodes=connected_nodes(m)
    return {n.get_name():dict(type=n.get_class().get_name(),desc=str(n.get_editor_property('desc')),
        code=n.get_editor_property('code') if isinstance(n,u.MaterialExpressionCustom) else None,
        inputs=[v.get_name() if v else None for v in mel.get_inputs_for_material_expression(m,n)]) for n in nodes}
try:
    assert vg.enabled();rows=[]
    texture=u.load_asset(vg.DEST+'/T_VG_Floor')
    assert texture.get_editor_property('mip_gen_settings')==u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE
    assert texture.get_editor_property('max_texture_size')==4096
    for name in ['M_Terrain','M_Detail']:
        m=u.load_asset(vg.BASE+'/'+name);before=signature(m)
        surfaces=[n for n in connected_nodes(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='FGSurface']
        assert len(surfaces)==1 and vg.FAR in surfaces[0].get_editor_property('code')
        assert sum(str(i.get_editor_property('input_name'))=='Valley' for i in surfaces[0].get_editor_property('inputs'))==1
        forest_ground.wrap(name)
        assert signature(m)==before,'Floor rebuild changed the saved shader graph'
        rows.append(dict(material=name,connected_nodes=len(before),shader_graph_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()))
    protected=json.loads((vg.QA/'prepared.json').read_text())['protected']
    for rel,digest in protected.items():
        if rel.endswith(('M_Terrain.uasset','M_Detail.uasset')):continue
        assert vg.sha(root/rel)==digest,rel
    result=dict(ok=True,reloaded=True,floor_rebuild_preserves_shader=True,materials=rows)
except Exception:
    result=dict(ok=False,error=traceback.format_exc());u.log_error(result['error'])
(vg.QA/'verified.json').write_text(json.dumps(result,indent=2));u.SystemLibrary.quit_editor()
