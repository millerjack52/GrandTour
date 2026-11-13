"""Broader connected forest crowns, derived from the existing FS1 beech designs."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_lidar_forest as F
from mathutils import Vector

OUT=Path(__file__).resolve().parents[1]/'Export/LidarStudy/CanopyDepth'
FACTORS={'Mature':(1.65,1.48),'Pole':(2.0,1.65),'Edge':(1.40,1.32)}
original_bough=F.bough
active_lobe_scale=1.
def broad_bough(g,centre,radii,seed,lod,pole=False):
    # Scale leaf groups and their sprays together, retaining their filled volume.
    start=len(g.v);original_bough(g,centre,radii,seed,lod,pole)
    for i in range(start,len(g.v)):
        p=g.v[i]-centre
        g.v[i]=centre+Vector((p.x*active_lobe_scale,p.y*active_lobe_scale,p.z))
F.bough=broad_bough

def main():
    global active_lobe_scale
    OUT.mkdir(parents=True,exist_ok=True)
    F.bpy.ops.wm.read_factory_settings(use_empty=True)
    F.bpy.context.preferences.filepaths.save_version=0
    mats=F.L.plant_materials();rows=[]
    for kind,(reach,lobe) in FACTORS.items():
        F.SPECS[kind]['radius']*=reach;active_lobe_scale=lobe
        D,n=F.design(kind);s=F.SPECS[kind];name='SM_CD_Beech_'+kind
        g,_=F.B.emit(D,0,s['budget'][0]);scale=s['height']/max(v.z for v in g.v)
        for lod in range(3):
            g,_=F.B.emit(D,lod,s['budget'][lod]);g.v=[v*scale for v in g.v]
            ob,dropped=F.L.to_object(g,name+'_LOD'+str(lod),mats,[0,1])
            assert len(ob.data.loop_triangles)<=s['budget'][lod]
            F.L.export(ob,out=OUT)
            rows.append(F.L.manifest_row(ob,name,'Beech',kind,lod,[0,1],s['seed'],g.counts,0,s['budget'][lod],dict(boughs=n,branch_reach=reach,lobe_width=lobe)))
            ob.hide_set(True);ob.hide_render=True
            print('CANOPY_DEPTH',kind,lod,len(ob.data.loop_triangles),flush=True)
    F.L.write_manifest(rows,out=OUT,extra=dict(stage='CanopyDepth',unreal_destination='/Game/GrandTour/ArtTests/LidarStudy/CanopyDepth'))
    F.bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CanopyDepth.blend'))
    print('CANOPY_DEPTH_BUILD_OK',flush=True)
if __name__=='__main__':main()
