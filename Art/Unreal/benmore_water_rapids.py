"""Depth/current-directed riffles, standing crests and advected whitewater."""
import unreal as u
from benmore_river_life_materials import Graph,props
mel=u.MaterialEditingLibrary
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterRapids'
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterMotion'

# Shared between vertices and pixels. Fixed direction bases avoid rotating
# world-space coordinates continuously through a bend. Long crests fit the
# existing 62.5 cm mesh; sub-metre turbulence remains shading only.
RAPIDS='''
struct ShallowRapids {
 float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
 float4 crests(float2 q,float2 v,float clock){
  float2 dir=length(v)>.001?v:float2(1,0);
  float turn=atan2(dir.y,dir.x)/6.28318530718*16;
  float lo=floor(turn),mixDir=smoothstep(0,1,frac(turn));float4 result=0;
  [unroll]for(int j=0;j<2;j++){
   float sn,cs;sincos((lo+j)*6.28318530718/16,sn,cs);
   float2 x=float2(cs,sn),y=float2(-sn,cs);
   float2 p=float2(dot(q,x),dot(q,y));
   // Crests stay around shallow bars while their wrinkles pulse. Froth below
   // moves through them with the current, rather than translating the bar.
   float a=p.x*2.094395+p.y*.32+.65*sin(p.y*1.9)+.25*sin(clock*2.1+p.y*.6);
   float b=p.x*1.208305-p.y*.48+.35*sin(p.y*.85+1.2)+.18*sin(clock*2.7);
   float sa,ca,sb,cb;sincos(a,sa,ca);sincos(b,sb,cb);
   float2 da=float2(2.094395,.32+1.235*cos(p.y*1.9)+.15*cos(clock*2.1+p.y*.6));
   float2 db=float2(1.208305,-.48+.2975*cos(p.y*.85+1.2));
   float2 gradient=.024*ca*da+.014*cb*db;
   float crest=max(smoothstep(.28,.93,sa),smoothstep(.5,.95,sb)*.65);
   result+=float4(x*gradient.x+y*gradient.y,.024*sa+.014*sb,crest)*(j==0?1-mixDir:mixDir);
  }
  return result;
 }
 float froth(float2 p){
  float2 eddy=float2(n(p*.85+4),n(p*.85+19))-.5;
  float broad=n((p+eddy*.38)*2.4);
  float bubbles=n(p*7.3+11);
  return smoothstep(.26,.68,broad*.75+bubbles*.25);
 }
 float transport(float2 q,float2 v,float clock){
  float phase=clock/2.8+n(q*.075)*.7;
  float a=frac(phase),b=frac(phase+.5),blend=abs(a*2-1);
  return lerp(froth(q-v*(a-.5)*2.8),froth(q-v*(b-.5)*2.8+float2(17.3,9.1)),blend);
 }
};ShallowRapids rapids;
float rapidShallow=smoothstep(.025,.10,ambientDepth)*(1-smoothstep(.28,.72,ambientDepth));
float rapidCurrent=smoothstep(.35,1.05,length(ambientVelocity));
float rapidPatches=lerp(.30,1,smoothstep(.25,.72,rapids.n(P.xy*.01*.22)));
float rapidStrength=rapidShallow*rapidCurrent*rapidPatches*inBake*saturate(RapidsGain);
float rapidHeightGain=min(1,ambientDepth*.088/.038);
float4 rapidWave=rapids.crests(P.xy*.01,ambientVelocity,Clock);
'''

def precombine():
    path=DEST+'/M_FW_Precombine'
    m=u.load_asset(path) or u.EditorAssetLibrary.duplicate_asset(SRC+'/M_FW_Precombine',path)
    assert m
    assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m

def surface(kind):
    name='M_GC_Domain'+kind
    source=u.load_asset(SRC+'/'+name);assert source
    m=u.load_asset(DEST+'/'+name) or u.EditorAssetLibrary.duplicate_asset(SRC+'/'+name,DEST+'/'+name)
    g=Graph(m,'WaterRapids')
    for prop in (u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_BASE_COLOR):
        src=mel.get_material_property_input_node(source,prop)
        dst=mel.get_material_property_input_node(m,prop)
        inputs=list(dst.get_editor_property('inputs'))
        if 'RapidsGain' not in {str(i.get_editor_property('input_name')) for i in inputs}:
            inputs.append(props(u.CustomInput(),input_name='RapidsGain'))
            dst.set_editor_property('inputs',inputs)
            g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='RapidsIntensity',default_value=1),dst,'RapidsGain')
        code=str(src.get_editor_property('code'))
        marker='float geometryFade=1-smoothstep(55,180,length(Camera-P)*.01);'
        assert marker in code
        code=code.replace(marker,marker+'\n'+RAPIDS)
        if prop==u.MaterialProperty.MP_WORLD_POSITION_OFFSET:
            old='offset.z+=wave.b*100*strength*shore*geometryFade*WaveGain;'
            assert old in code
            code=code.replace(old,'''// Reserve 40% of the old 22%-of-depth ambient height budget
// for the standing crest. New maximum stays <=22% of local depth.
 offset.z+=(wave.b*strength*(1-.40*rapidStrength)
  +rapidWave.b*rapidHeightGain*rapidStrength)*100*shore*geometryFade*WaveGain;''')
        else:
            old='detail=-wave.rg*normalGain*shore*WaveGain;'
            assert old in code
            code=code.replace(old,'''detail=-wave.rg*normalGain*shore*WaveGain*(1+1.8*rapidStrength);
 detail-=rapidWave.rg*rapidHeightGain*rapidStrength*shore*nearFade*WaveGain;
 detail=clamp(detail,-.60,.60);''')
            old='float foam=(flow.a*bubble*.34+surfaceThreads*.72)*flowing*nearFade;'
            assert old in code
            code=code.replace(old,old+'''
// A broken white crest feeds a turbulent downstream foam train. Shallow and
// fast gates also keep calm pools and the lake free of authored whitewater.
float rapidResolve=1-smoothstep(.09,.32,max(length(ddx(q)),length(ddy(q))));
float rapidFroth=rapids.transport(q,ambientVelocity,Clock);
float breaking=rapidStrength*(.18+.82*rapidWave.a)*rapidFroth;
// Saturated, broken white crests, rather than a translucent grey foam wash.
float whitewater=smoothstep(.06,.34,breaking)*shore*nearFade*rapidResolve;
foam=saturate(foam+whitewater*.95);
''')
            old='return lerp(colour,lerp(float3(.35,.39,.36),float3(.46,.53,.49),saturate(interactionFoam*2)),foam);'
            assert old in code
            code=code.replace(old,'''float3 foamColour=lerp(float3(.35,.39,.36),float3(.46,.53,.49),saturate(interactionFoam*2));
foamColour=lerp(foamColour,float3(.82,.87,.84),saturate(whitewater*3));
return lerp(colour,foamColour,foam);''')
        dst.set_editor_property('code',code)
    assert not mel.recompile_material(m)
    assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m
