"""Non-destructive colour studies of the ford with the approved willow family."""
from pathlib import Path
import bpy, json, sys

ROOT=Path('C:/GrandTour')
OUT=ROOT/'Art/Export/LevelPalette/palette-01'
OUT.mkdir(parents=True,exist_ok=True)
PRESETS={
 'current':{},
 'natural':dict(grass=(.48,.345,.14),ground=(.38,.275,.13),road=(.34,.285,.22),stone=(.245,.25,.235),hill=(.19,.29,.40),water=(.06,.235,.255),sky=(.15,.34,.59)),
 'golden':dict(grass=(.57,.355,.10),ground=(.43,.285,.10),road=(.37,.285,.185),stone=(.27,.255,.22),hill=(.18,.275,.41),water=(.045,.255,.28),sky=(.12,.32,.58)),
 'muted':dict(grass=(.35,.32,.18),ground=(.29,.275,.16),road=(.30,.28,.235),stone=(.23,.255,.265),hill=(.23,.32,.405),water=(.075,.215,.24),sky=(.19,.36,.55)),
}

def shader(mat): return next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def colour(name,c):
    mat=bpy.data.materials.get(name)
    if mat: shader(mat).inputs['Base Color'].default_value=(*c,1)

def tint(mat,c,brightness=1):
    nt=mat.node_tree; p=shader(mat); inp=p.inputs['Base Color']
    bw=nt.nodes.new('ShaderNodeRGBToBW'); bw.label='Retain original surface variation'
    if inp.is_linked: nt.links.new(inp.links[0].from_socket,bw.inputs[0])
    else: bw.inputs[0].default_value=inp.default_value
    gain=nt.nodes.new('ShaderNodeMath'); gain.operation='MULTIPLY_ADD'
    gain.inputs[1].default_value=brightness; gain.inputs[2].default_value=.12
    nt.links.new(bw.outputs[0],gain.inputs[0])
    mix=nt.nodes.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=1
    nt.links.new(gain.outputs[0],mix.inputs[1]); mix.inputs[2].default_value=(*c,1)
    nt.links.new(mix.outputs[0],inp)
    return mix

for key,cfg in PRESETS.items():
    if '--skip-current' in sys.argv and key=='current': continue
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Art/Export/RoadFordStyle/RoadFordStyle.blend'))
    scene=bpy.context.scene
    # Same new trees and placements in every study, including the colour baseline.
    for variant,old in [('broad','Mature'),('young','Young')]:
        with bpy.data.libraries.load(str(ROOT/f'Art/Export/WillowFamily/willow-family-01/{variant}.blend'),link=False) as (src,dst):
            dst.objects=[f'SM_Willow_{variant.title()}']
        tree=dst.objects[0]
        for ob in list(scene.objects):
            if ob.name.startswith('Placed_SM_RF_Willow_'+old): ob.data=tree.data
    if cfg:
        tint(bpy.data.materials['M_RF_GrassCarpet'],cfg['grass'],3.7)
        for i,scale in enumerate([1,1.2,.7]): colour('M_RB_Grass'+str(i),tuple(v*scale for v in cfg['grass']))
        for i,scale in enumerate([1,1.18,.63]): colour('M_RB_Stone'+str(i),tuple(v*scale for v in cfg['stone']))
        colour('M_RF_WetStone',tuple(v*.48 for v in cfg['stone']))
        hill=tint(bpy.data.materials['M_RF_DistantHill'],cfg['hill'],2.0)
        p=shader(bpy.data.materials['M_RF_DistantHill'])
        p.inputs['Emission Color'].default_value=(*cfg['hill'],1)
        p.inputs['Emission Strength'].default_value=.28
        colour('M_RF_WaterPreview',cfg['water'])
        colour('M_RF_WaterStroke',tuple(min(1,v*1.6+.04) for v in cfg['water']))
        mat=bpy.data.materials['M_RF_TerrainBlend']; nt=mat.node_tree
        m=tint(mat,cfg['road'],3.3)
        # Existing UV masks keep the ford wet and banks dry; source texture detail remains.
        uv=nt.nodes.new('ShaderNodeUVMap'); uv.uv_map='SurfaceMasks'
        sep=nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs[0],sep.inputs[0])
        mix=nt.nodes.new('ShaderNodeMixRGB'); mix.inputs[1].default_value=(*cfg['road'],1); mix.inputs[2].default_value=(*cfg['ground'],1)
        nt.links.new(sep.outputs['X'],mix.inputs[0])
        wet=nt.nodes.new('ShaderNodeMixRGB'); wet.inputs[2].default_value=(.27,.145,.085,1)
        nt.links.new(sep.outputs['Y'],wet.inputs[0]); nt.links.new(mix.outputs[0],wet.inputs[1]); nt.links.new(wet.outputs[0],m.inputs[2])
        for node in scene.world.node_tree.nodes:
            if node.type=='BACKGROUND' and abs(node.inputs['Strength'].default_value-.8)<.001:
                node.inputs['Color'].default_value=(*cfg['sky'],1)
    scene.camera=bpy.data.objects['Ford_driver_view']
    scene.render.resolution_x=1100; scene.render.resolution_y=688; scene.render.resolution_percentage=100
    scene.cycles.samples=24; scene.cycles.use_denoising=True
    scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=86
    scene.render.filepath=str(OUT/f'{key}.jpg')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{key}.blend'))
    bpy.ops.render.render(write_still=True)
    print('PALETTE_RENDER_OK '+key,flush=True)
(OUT/'palettes.json').write_text(json.dumps({'presets_linear':PRESETS,'camera':'Ford_driver_view','exposure':0,'view_transform':'AgX','note':'Separate Blender studies, same new willow geometry and lighting in all renders. Not imported to Unreal.'},indent=2))
