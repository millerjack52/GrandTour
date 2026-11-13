"""Restore Mud_001 visual relief with an explicit fixed-grid sampling adapter.

Source: SpinTires_Mud_001, c35.z=.24 cycles/metre, c35.w=.22 metre.
Noise is centred at .5 and multiplied by mud presence (r6.x). The physical
height field is deliberately separate, just as in the original shader. Four
filter taps and the 2.5 cm XY limit adapt it to our grid; they are not recovered
native constants. The source game's adaptive mesh topology is not ported here.
"""
import unreal as u
import benmore_woodland_materials as mat
from benmore_river_life_materials import Graph, props

GRID_NOISE = '''
// WoodlandGridNoise: bandwidth/XY guard for the host's fixed 12.5 cm lattice.
// The source noise has 3.26 cm texels; point-vertex sampling aliases that detail.
struct WoodlandGridNoise {
 float3 offset(Texture2D T,SamplerState S,float2 xy,float presence) {
  float2 q=xy*.0024,e=float2(6.25*.0024,0);
  float3 n=(Texture2DSampleLevel(T,S,q+e+e.yx,0).rbg+
            Texture2DSampleLevel(T,S,q+e-e.yx,0).rbg+
            Texture2DSampleLevel(T,S,q-e+e.yx,0).rbg+
            Texture2DSampleLevel(T,S,q-e-e.yx,0).rbg)*.25-.5;
  float3 d=n*22*presence;
  // Keep adjacent grid vertices ordered in XY, including at full mud presence.
  d.xy=clamp(d.xy,-2.5,2.5);
  return d;
 }
}; WoodlandGridNoise woodlandNoise;
'''

LIGHTING = '''
// WoodlandClodLighting: UE lighting adapter, NOT original Mud_001 arithmetic.
// Evaluate at visual vertices and interpolate, avoiding per-pixel noise shimmer.
// Source colour still uses its unmodified physical mud normal.
float3 cl=woodlandNoise.offset(Noise,NoiseSampler,P.xy-float2(12.5,0),presence);
float3 cr=woodlandNoise.offset(Noise,NoiseSampler,P.xy+float2(12.5,0),presence);
float3 cd=woodlandNoise.offset(Noise,NoiseSampler,P.xy-float2(0,12.5),presence);
float3 cu=woodlandNoise.offset(Noise,NoiseSampler,P.xy+float2(0,12.5),presence);
float2 baseSlope=-mrNormal.xy/max(mrNormal.z,.05);
float3 tx=float3(25,0,baseSlope.x*25)+(cr-cl)*VisualGrid;
float3 ty=float3(0,25,baseSlope.y*25)+(cu-cd)*VisualGrid;
return normalize(cross(tx,ty));
'''


def lighting(m):
    if m.get_name() == 'M_Tread': return
    mel = u.MaterialEditingLibrary
    nodes = list(mel.get_material_expressions(m))
    marker = next((n for n in nodes if str(n.get_editor_property('desc')) ==
                   'WoodlandSoilDetailSource:Normal'), None)
    # Recover the original world normal node under the saved passthrough.
    normal = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                  and ('return mrNormal;' in str(n.get_editor_property('code')) or
                       'WoodlandClodLighting:' in str(n.get_editor_property('code')))
                  and str(n.get_editor_property('desc')) == 'BenmoreWoodlandBridge')
    code = str(normal.get_editor_property('code'))
    if 'WoodlandClodLighting:' in code:
        code = code[:code.index('// WoodlandClodLighting:')] + LIGHTING
    else:
        assert code.rstrip().endswith('return mrNormal;')
        code = code.replace('return mrNormal;', LIGHTING)
    if 'struct WoodlandGridNoise' not in code: code = GRID_NOISE + code
    normal.set_editor_property('code', code)
    for n in nodes:
        if str(n.get_editor_property('desc')) == 'WoodlandClodLightingBridge':
            mel.delete_material_expression(m, n)
    g = Graph(m, 'WoodlandClodLightingBridge')
    # Landscape's distant material path was producing invalid GBuffer normals
    # through this custom vertex interpolator (the procedural near grid did not).
    # Evaluate the terrain normal in the pixel stage; keep vertex interpolation
    # for clod normals on the fixed 12.5cm procedural mesh.
    if m.get_name() == 'M_Terrain':
        # Repeating the full physical-field program per distant landscape pixel
        # fixed the normals but was prohibitively expensive. Landscape already
        # supplies its geometric slope. Add only filtered authored rest relief;
        # the moving procedural grid owns live physical normals and native clods.
        source_texture=u.load_asset(mat.BASE+'/T_relief')
        relief=u.load_asset(mat.BASE+'/T_ReliefLighting') or u.EditorAssetLibrary.duplicate_asset(source_texture.get_path_name().split('.')[0],mat.BASE+'/T_ReliefLighting')
        props(relief,srgb=False,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,filter=u.TextureFilter.TF_TRILINEAR,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP)
        assert u.EditorAssetLibrary.save_loaded_asset(relief)
        style=next(e.texture for e in nodes if isinstance(e,u.MaterialExpressionTextureObject) and e.texture and e.texture.get_name() in ['T_style','T_style_groundstudy'])
        paint=next(e for e in nodes if isinstance(e,u.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_Paint')
        depth=next(e for e in nodes if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_DepthScale')
        interp=g.custom(['P','BaseN','Relief','Style','Paint','DepthScale','Camera'],'''// WoodlandLandscapeNormal: geometric slope + mip-filtered rest detail.
float2 q=saturate((P.xy+125000)/250000);
float4 style=Texture2DSample(Style,StyleSampler,q);
float thickness=Texture2DSampleLevel(Paint,PaintSampler,q,0).r*50*DepthScale;
float weight=(1-style.r)*(1-style.a)*smoothstep(4,30,thickness);
float2 uv=P.xy/12800.,e=float2(12.5/12800.,0);
float2 dx=Texture2DSample(Relief,ReliefSampler,uv+e).rg-Texture2DSample(Relief,ReliefSampler,uv-e).rg;
float2 dy=Texture2DSample(Relief,ReliefSampler,uv+e.yx).rg-Texture2DSample(Relief,ReliefSampler,uv-e.yx).rg;
float2 slope=float2(dot(dx,float2(65280,255)),dot(dy,float2(65280,255)))*(65./65535./25.);
slope*=weight*(1-smoothstep(5000,12000,length(Camera-P)));
return normalize(float3(BaseN.xy-slope*BaseN.z,BaseN.z));''')
        inputs={'P':g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),'BaseN':g.node(u.MaterialExpressionVertexNormalWS),'Camera':g.node(u.MaterialExpressionCameraPositionWS),'Relief':g.node(u.MaterialExpressionTextureObject,texture=relief,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),'Style':g.node(u.MaterialExpressionTextureObject,texture=style,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),'Paint':paint,'DepthScale':depth}
        for pin,node in inputs.items():g.wire(node,interp,pin)
    else:
        interp = g.node(u.MaterialExpressionVertexInterpolator)
        g.wire(normal, interp, '')
    signed = g.node(u.MaterialExpressionMultiply)
    g.wire(interp, signed, 'A')
    g.wire(g.node(u.MaterialExpressionTwoSidedSign), signed, 'B')
    if marker: g.wire(signed, marker, 'Value')
    else: g.output(signed, u.MaterialProperty.MP_NORMAL)


def patch(m):
    changed = 0
    offsets = 0
    for node in u.MaterialEditingLibrary.get_material_expressions(m):
        if not isinstance(node, u.MaterialExpressionCustom):
            continue
        old = str(node.get_editor_property('code'))
        code = old
        # Restrict recovery to known WPO expressions; other zero vectors have
        # unrelated meanings. Soil and interpolated tread must agree exactly.
        code = code.replace('float3(0,0,noise.g*22*presence)', 'noise.rbg*22*presence')
        code = code.replace('float3(0,0,n.g*22*pr)', 'n.rbg*22*pr')
        code = code.replace('(float3(0,0,height-.1)+float3(0,0,0))*VisualGrid',
                            '(float3(0,0,height-.1)+noise.rbg*22*presence)*VisualGrid')
        code = code.replace('(float3(0,0,h-.1)+float3(0,0,0))',
                            '(float3(0,0,h-.1)+n.rbg*22*pr)')
        code = code.replace('noise.rbg*22*presence', 'woodlandNoise.offset(Noise,NoiseSampler,P.xy,presence)')
        code = code.replace('n.rbg*22*pr', 'woodlandNoise.offset(Noise,NoiseSampler,xy,pr)')
        if 'woodlandNoise.offset' in code and 'struct WoodlandGridNoise' not in code:
            code = GRID_NOISE + code
        offsets += int('woodlandNoise.offset' in code)
        if code != old:
            node.set_editor_property('code', code)
            changed += 1
    assert offsets >= 1, (m.get_name(), 'Missing recovered geometry path')
    # Materials can retain unused custom nodes from previous bridge versions.
    # Verify the active WPO dependency rather than counting all editor nodes.
    mel = u.MaterialEditingLibrary
    pending = [mel.get_material_property_input_node(m, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)]
    seen = set(); active_offset = False
    while pending:
        node = pending.pop()
        if not node or node.get_path_name() in seen: continue
        seen.add(node.get_path_name())
        if isinstance(node, u.MaterialExpressionCustom):
            code = str(node.get_editor_property('code'))
            active_offset |= 'woodlandNoise.offset' in code
        pending.extend(mel.get_inputs_for_material_expression(m, node))
    assert active_offset, (m.get_name(), 'Native displacement is disconnected')
    lighting(m)
    mat.save(m)
    return dict(material=m.get_path_name(), changed_programs=changed,
                native_xyz_displacement=True, scale_cm=22, uv_cycles_per_cm=.0024,
                host_grid_filter_taps=4, host_lateral_limit_cm=2.5)


def install():
    return [patch(u.load_asset(mat.BASE + '/M_' + name))
            for name in ['Terrain', 'Detail', 'Tread']]
