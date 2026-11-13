import bpy,json,sys
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools');import assembly_contracts as ac
folder=Path('C:/GrandTour/Art/Export/VehicleTools/crafted-character-detailed-v06')
bpy.ops.wm.open_mainfile(filepath=str(folder/'Crafted_Utility_Detailed.blend'));sc=bpy.context.scene
S=json.loads((folder/'shape-spec.json').read_text());R=S['registration'];P=R['pixels_per_metre']
o=bpy.data.objects['Floor pan | continuous cabin and cargo']
for v in o.data.vertices:
    if v.co.z<.56 and abs(v.co.x)>.61:
        u=R['front_hub_px'][0]+(v.co.y-R['axle_front_world'])*P
        pv=R['front_hub_px'][1]-(v.co.z-R['axle_z'])*P
        v.co.x=(1 if v.co.x>0 else -1)*(ac.interp(pv,S['side_section_v_width'])*ac.interp(u,S['longitudinal_width'])-.003)
for key,name in [('underside','QA | floor straight underside'),('underside-quarter','QA | floor oblique'),('quarter','Front quarter | volume review'),('side','Side | fixed reference registration')]:
    sc.camera=bpy.data.objects[name];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
    bpy.data.objects['Ground'].hide_render=key.startswith('underside');sc.render.filepath=str(folder/(key+'.png'));bpy.ops.render.render(write_still=True)
bpy.data.objects['Ground'].hide_render=False
sc.camera=bpy.data.objects['Front quarter | volume review'];sc.render.resolution_x,sc.render.resolution_y=sc.camera['resolution']
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Crafted_Utility_Detailed.blend'))
