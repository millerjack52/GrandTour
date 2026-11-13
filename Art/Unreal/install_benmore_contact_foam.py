"""Material-only contact foam pass, preserving saved geometry and simulation."""
import unreal as u
import sys,time,json,hashlib,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_surface as h
from benmore_water_surface import surface,DEST
OUT=Path(os.environ.get('GT_CONTACT_FOAM_OUT',str(ROOT/'Art/Export/BenmoreGaea/WaterSurface_Foam_20261011')))
OUT.mkdir(parents=True,exist_ok=True)
VERIFY='-GTFoamVerify' in u.SystemLibrary.get_command_line()
h.OUT=OUT;h.report={'ok':False,'mode':'verify' if VERIFY else 'install','images':[],'material_only':True}

def protected():
    folder=ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea'
    files=list((folder/'WaterSurface').glob('SM_*.uasset'))+list((folder/'WaterSurface').glob('*Precombine*.uasset'))
    files+=list(folder.glob('*.umap'))
    return {str(p.relative_to(ROOT)):h.digest(p) for p in files}

def vertex(kind):
    m=u.load_asset(DEST+'/M_GC_Domain'+kind)
    return str(u.MaterialEditingLibrary.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET).get_editor_property('code'))

def run():
    h.load();before=h.snapshot();files=protected();vertices={k:vertex(k) for k in ['River','Lake']}
    h.report['before']=before;h.report['protected_files']=files
    if not VERIFY:
        backup=DEST+('/BeforeMotionFoam' if 'Motion_' in OUT.name else '/BeforeFocusedFoam' if 'Focused_' in OUT.name else '/BeforeContactFoam')
        for k in vertices:
            path=backup+'/M_GC_Domain'+k
            if not h.s.eal.does_asset_exist(path):assert h.s.eal.duplicate_asset(DEST+'/M_GC_Domain'+k,path)
        if not (OUT/'Before_00.png').exists():yield from h.capture('Before',1)
        for k in vertices:surface(k)
        assert all(vertex(k)==v for k,v in vertices.items()),'Wave displacement changed'
        h.load()
    h.s.DEST=DEST;h.s.verify_saved_water()
    for k in vertices:
        m=u.load_asset(DEST+'/M_GC_Domain'+k)
        assert not u.MaterialEditingLibrary.recompile_material(m)
        code=str(u.MaterialEditingLibrary.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR).get_editor_property('code'))
        assert 'edgeFoam*2' in code and 'contactBreakup' in code
        assert 'contactSignal=detailSample.a' in code and 'frontFoam' in code
        (OUT/(k+'-pixel.hlsl')).write_text(code)
        assert m.get_editor_property('refraction_method')==u.RefractionMode.RM_2D_OFFSET
    yield from h.capture('Verified' if VERIFY else 'After',8)
    h.load();h.s.verify_saved_water()
    h.report['after']=h.snapshot()
    assert h.report['after']==before
    assert protected()==files,'Geometry, precombined waves or map changed'
    assert all(vertex(k)==v for k,v in vertices.items())
    h.report['wave_displacement_unchanged']=True;h.report['protected_files_unchanged']=True
    h.report['ok']=True

h.started=time.monotonic();h.next_at=h.started;h.gen=run()
h.handle=u.register_slate_post_tick_callback(h.tick)
