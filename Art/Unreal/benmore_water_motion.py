"""Readable ambient river motion at driving distance; material-only art pass."""
import unreal as u
import benmore_flow_waves as spectrum
from benmore_river_life_materials import Graph
mel=u.MaterialEditingLibrary
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterMotion'
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterBalanced'
HEIGHT_RANGE=.27
COARSE=[(x,y,a*1.5,w*1.35,p) for x,y,a,w,p in spectrum.COARSE]
FINE=[(x,y,a*3.3,w*1.8,p) for x,y,a,w,p in spectrum.FINE]

def precombine():
    spectrum.DEST=DEST
    spectrum.COARSE=COARSE;spectrum.FINE=FINE;spectrum.HEIGHT_RANGE=HEIGHT_RANGE
    m=spectrum.make_precombine()
    node=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
    code=str(node.get_editor_property('code'))
    # Keep crest coverage sparse as fine-wave amplitude increases.
    code=code.replace('smoothstep(.0020,.0055,small+h*.025)',
                      'smoothstep(.0066,.01815,small+h*.055)')
    code=code.replace('smoothstep(.025,.085,length(slope))',
                      'smoothstep(.07,.22,length(slope))')
    node.set_editor_property('code',code)
    assert not mel.recompile_material(m)
    assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m

TRACERS='''
// Sparse elongated surface foam is present without a car. Use fixed direction
// bases and short overlapping phases, so changing flow never winds up a UV warp.
struct RiverThreads {
 float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
 float mask(float2 p){
  float strand=n(p*float2(.85,5.8));
  float breakup=n(p*3.7+23);
  return smoothstep(.59,.78,strand)*smoothstep(.30,.65,breakup);
 }
 float value(float2 q,float2 v,float clock){
  float speed=length(v);float2 dir=speed>.001?v/speed:float2(1,0);
  float turn=atan2(dir.y,dir.x)/6.28318530718*16;
  float lo=floor(turn),mixDir=smoothstep(0,1,frac(turn));
  float phase=clock/3.6+n(q*.075)*.7;
  float a=frac(phase),b=frac(phase+.5),blend=abs(a*2-1),outFoam=0;
  [unroll]for(int j=0;j<2;j++){
   float sn,cs;sincos((lo+j)*6.28318530718/16,sn,cs);
   float2 x=float2(cs,sn),y=float2(-sn,cs);
   float2 p=float2(dot(q,x),dot(q,y)),adv=float2(dot(v,x),dot(v,y))*3.6;
   float trace=lerp(mask(p-adv*(a-.5)),mask(p-adv*(b-.5)+float2(13.7,8.1)),blend);
   outFoam+=trace*(j==0?1-mixDir:mixDir);
  }
  return outFoam;
 }
};RiverThreads threads;
float traceResolve=1-smoothstep(.055,.20,max(length(ddx(q)),length(ddy(q))));
float flowing=smoothstep(.12,.65,length(ambientVelocity))*inBake;
float surfaceThreads=threads.value(q,ambientVelocity,Clock)*flowing*shore*nearFade*traceResolve;
float foam=(flow.a*bubble*.34+surfaceThreads*.72)*flowing*nearFade;
'''

def surface(kind):
    name='M_GC_Domain'+kind
    source=u.load_asset(SRC+'/'+name);assert source
    m=u.load_asset(DEST+'/'+name) or u.EditorAssetLibrary.duplicate_asset(SRC+'/'+name,DEST+'/'+name)
    # Reset code from the accepted pass so rebuilding cannot stack gains.
    for prop in (u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_BASE_COLOR):
        src=mel.get_material_property_input_node(source,prop)
        dst=mel.get_material_property_input_node(m,prop)
        code=str(src.get_editor_property('code'))
        assert '(f.b-.5)*.18' in code
        code=code.replace('(f.b-.5)*.18','(f.b-.5)*.27')
        # Retain the 22%-of-depth geometric cap despite the taller coarse bands.
        assert '.22*ambientDepth/0.06100000' in code
        code=code.replace('.22*ambientDepth/0.06100000','.22*ambientDepth/0.09150000')
        if prop==u.MaterialProperty.MP_BASE_COLOR:
            old='float normalGain=max(.15*(1-currentShape),strength)*nearFade;'
            assert old in code
            code=code.replace(old,'float normalGain=max(.32*(1-currentShape),max(strength,.85*currentShape))*nearFade;')
            code=code.replace('bubble=saturate(wave.a);','bubble=saturate(wave.a);\n rippleShade=clamp(dot(wave.rg,float2(.8,.6))*1.1,-.22,.22)*shore*nearFade;')
            old='float foam=flow.a*smoothstep(.18,.95,speed)*bubble*.28*nearFade;'
            assert old in code
            code=code.replace(old,TRACERS)
            old='Rough=clamp(lerp(.23,.36,riffle)+foam*.34,.18,.65);'
            assert old in code
            code=code.replace(old,'Rough=clamp(lerp(.19,.28,riffle)+foam*.34,.17,.65);')
        dst.set_editor_property('code',code)
    # Restore a readable reflection response to the moving normals.
    g=Graph(m,'WaterMotion')
    spec=g.custom(['P','Camera'],'return lerp(.32,.20,smoothstep(35,160,length(Camera-P)*.01));',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(g.node(u.MaterialExpressionWorldPosition),spec,'P')
    g.wire(g.node(u.MaterialExpressionCameraPositionWS),spec,'Camera')
    g.output(spec,u.MaterialProperty.MP_SPECULAR)
    assert not mel.recompile_material(m)
    assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m
