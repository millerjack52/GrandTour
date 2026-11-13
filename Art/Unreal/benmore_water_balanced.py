"""Bounded flow advection and restrained aeration over the accepted river surface.

Layered short advection follows Valve's Water Flow in Portal 2 / L4D2 method
(Vlachos, SIGGRAPH 2010). Here velocity comes from the existing hydraulic bake.
No terrain, bathymetry, displacement amplitude or spray material edits.
"""
import unreal as u
import benmore_water_interaction as interaction
from benmore_flow_waves import SAMPLE
mel=u.MaterialEditingLibrary
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterBalanced'

# Four texture reads, as before: two fixed orientation bases, two short flow
# phases. Continuous velocity replaces the old interpolation between speed bins.
FLOW_SAMPLE='''
struct CurrentWaves {
 float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
 float4 evaluate(Texture2D tex,SamplerState ss,float2 q,float2 v,float clock,float mip) {
  float speed=length(v);
  float2 direction=speed>.001?v/speed:float2(1,0);
  float turn=atan2(direction.y,direction.x)/6.28318530718*16;
  float lo=floor(turn),d=smoothstep(0,1,frac(turn));
  float phase=clock/3.6+noise(q*.075)*.7;
  float a0=frac(phase),a1=frac(phase+.5);
  float blend=abs(a0*2-1);
  float4 result=0;
  [unroll]for(int j=0;j<2;j++) {
   float a=(lo+j)*6.28318530718/16;
   float sn,cs;sincos(a,sn,cs);float2 x=float2(cs,sn),y=float2(-sn,cs);
   float2 p=float2(dot(q,x),dot(q,y));
   float2 adv=float2(dot(v,x),dot(v,y))*3.6;
   float4 f0=Texture2DSampleLevel(tex,ss,(p-adv*(a0-.5))/12,mip);
   float4 f1=Texture2DSampleLevel(tex,ss,(p-adv*(a1-.5))/12+float2(.37,.61),mip);
   float4 f=lerp(f0,f1,blend);float2 grad=(f.rg-.5)*2;
   f=float4(x*grad.x+y*grad.y,(f.b-.5)*.18,1-f.a);
   result+=f*(j==0?1-d:d);
  }
  return result;
 }
};CurrentWaves waves;
'''

def make_balanced(kind):
    interaction.DEST=DEST
    m=interaction.make(kind)
    wpo=mel.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    pixel=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
    for node in (wpo,pixel):
        code=str(node.get_editor_property('code'))
        assert SAMPLE in code,'Expected stage-94 flow sampler'
        node.set_editor_property('code',code.replace(SAMPLE,FLOW_SAMPLE))
    code=str(pixel.get_editor_property('code'))
    start=code.index('float2 foamUV=')
    end=code.index('foam=saturate(foam+interactionFoam);',start)
    code=code[:start]+'''
// Concentration is already transported by the live field. Fine breakup follows
// that current too, with hidden phase resets so bends cannot stretch forever.
float foamPhase=Time/2.8+aeration.n(q*.12)*.65;
float fa=frac(foamPhase),fb=frac(foamPhase+.5),fw=abs(fa*2-1);
float2 foamVelocity=lerp(velocity,live.ba*.01,physicalWeight);
float2 fpa=(q-foamVelocity*(fa-.5)*2.8)*5.5;
float2 fpb=(q-foamVelocity*(fb-.5)*2.8)*5.5+float2(17.3,9.1);
float na=aeration.n(fpa)*.7+aeration.n(fpa*2.3+13)*.3;
float nb=aeration.n(fpb)*.7+aeration.n(fpb*2.3+13)*.3;
float flecks=lerp(smoothstep(.44,.72,na),smoothstep(.44,.72,nb),fw);
float fleckResolve=1-smoothstep(.035,.14,max(length(ddx(q)),length(ddy(q))));
flecks=lerp(.12,flecks,fleckResolve);
float concentration=smoothstep(.08,.72,trail.x*FoamGain);
float interactionFoam=concentration*flecks*.62*nearFade;
'''+code[end:]
    # Keep visible water between aerated flecks. The former bright .69 peak and
    # nearly opaque metre-wide patches obscured the pressure ridge and tyres.
    code=code.replace('float3(.62,.69,.65)','float3(.46,.53,.49)')
    pixel.set_editor_property('code',code)
    assert not mel.recompile_material(m)
    assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m
