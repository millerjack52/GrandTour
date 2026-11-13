"""Cheaper rendering for the mean-flow surface. This is NOT live simulation.

Reuse the project's sourced water normal. The previous eight finite-difference
evaluations each called a three-octave procedural field in the pixel shader.
"""
import unreal as u
from benmore_river_life_materials import Graph,props
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale'
SOURCE='/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverLife'
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary

NORMAL='''
float distanceM=length(Camera-P)*.01;
float2 q=P.xy*.01,v=(Flow.rg-.5)*4;
float speed=length(v),depth=Flow.b*2;
float fade=1-smoothstep(30,160,distanceM);
float2 footprint=max(abs(ddx(q)),abs(ddy(q)));
float mip=max(0,log2(max(max(footprint.x,footprint.y)*2048/2.4,1)));
[branch] if(fade<=.001) return normalize(N);
float t0=frac(Time/5),t1=frac(Time/5+.5),w=abs(t0*2-1);
float2 a=q-v*t0*5,b=q-v*t1*5;
float2 n0=lerp(Texture2DSampleLevel(Ripple,RippleSampler,a/2.4,mip).rg,Texture2DSampleLevel(Ripple,RippleSampler,b/2.4,mip).rg,w)*2-1;
float2 n1=lerp(Texture2DSampleLevel(Ripple,RippleSampler,a/6.7,max(0,mip-1.48)).rg,Texture2DSampleLevel(Ripple,RippleSampler,b/6.7,max(0,mip-1.48)).rg,w)*2-1;
float riffle=saturate(speed*.7)*(1-smoothstep(.35,.9,depth));
float2 slope=(n0+.35*n1)*lerp(.045,.13,riffle)*fade;slope.y=-slope.y;
return normalize(N+float3(slope,0));
'''

def make_stream():
    path=DEST+'/M_RS_Stream';m=u.load_asset(path) or eal.duplicate_asset(SOURCE+'/M_RL_Stream',path)
    nodes=list(mel.get_material_expressions(m));node=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')][:5]==['P','Flow','Time','Camera','N'])
    if any(str(i.get_editor_property('input_name'))=='Ripple' for i in node.get_editor_property('inputs')):return m
    node.set_editor_property('code',NORMAL)
    node.set_editor_property('inputs',list(node.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='Ripple')])
    g=Graph(m,'RiverBudget');r=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='RippleTex',texture=u.load_asset('/Game/GrandTour/Textures/Water/T_GT_Water_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);assert r.get_editor_property('texture')
    g.wire(r,node,'Ripple')
    for n in nodes:
        if isinstance(n,u.MaterialExpressionCustom) and [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]==['P','Flow','Time','Camera']:
            code=n.get_editor_property('code');start=code.index('float2 q=')
            # Branch before procedural foam work; this is a work skip, not just a faded result.
            n.set_editor_property('code',code[:start]+'[branch] if(Flow.a<.002 || length(Camera-P)>40000) return 0;\n'+code[start:])
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def make_lake():
    path=DEST+'/M_RS_Lake';m=u.load_asset(path) or eal.duplicate_asset(SOURCE+'/M_RL_Lake',path)
    nodes=list(mel.get_material_expressions(m))
    if any(isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='RippleTex' for n in nodes):return m
    g=Graph(m,'RiverBudget');r=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='RippleTex',texture=u.load_asset('/Game/GrandTour/Textures/Water/T_GT_Water_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    node=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'grad*.045' in n.get_editor_property('code'))
    node.set_editor_property('inputs',list(node.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='Ripple')]);g.wire(r,node,'Ripple')
    node.set_editor_property('code','''
float d=length(Camera-P)*.01;float fade=1-smoothstep(40,250,d);
float2 q=P.xy*.01;float footprint=max(length(ddx(q)),length(ddy(q)));
float mip=max(0,log2(max(footprint*2048/7,1)));
[branch]if(fade<=.001)return float3(0,0,1);
float2 a=Texture2DSampleLevel(Ripple,RippleSampler,(q-Time*float2(.08,.035))/7,mip).rg*2-1;
float2 b=Texture2DSampleLevel(Ripple,RippleSampler,(q.yx+Time*float2(.035,.025))/11,max(0,mip-.65)).rg*2-1;
float2 tilt=(a+.3*b)*.026*fade;tilt.y=-tilt.y;return normalize(float3(tilt,1));
''')
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m
