"""Small geometric waves, matched slopes and crest-localized transported foam."""
import re
import unreal as u
import benmore_flow_waves as spectrum
from benmore_river_life_materials import Graph,props
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterDetail'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterSurface'
# 12 m periodic field, 0.62--1.49 m middle bands; shading ripples remain below it.
MIDDLE=[(8,1,.030,2.7,.3),(10,-2,.027,3.2,2.1),(13,3,.025,3.7,4.2),
    (15,-4,.022,4.1,1.4),(19,2,.019,4.5,5.3),(8,10,.018,3.3,2.8),
    (13,-11,.014,4.0,.7),(3,18,.012,4.4,3.5)]
COARSE=[(x,y,a*.8,w*1.35,p) for x,y,a,w,p in spectrum.COARSE]+MIDDLE
BOUND=sum(x[2] for x in COARSE)

def precombine():
    spectrum.DEST=DEST;spectrum.COARSE=COARSE
    spectrum.FINE=[(x,y,a*2.6,w*2.1,p) for x,y,a,w,p in spectrum.FINE]
    spectrum.HEIGHT_RANGE=.48
    m=spectrum.make_precombine()
    n=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
    code=str(n.get_editor_property('code'))
    code=code.replace('smoothstep(.0020,.0055,small+h*.025)','smoothstep(.010,.026,small+h*.05)')
    code=code.replace('smoothstep(.025,.085,length(slope))','smoothstep(.18,.42,length(slope))')
    n.set_editor_property('code',code);assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m

def surface(kind):
    name='M_GC_Domain'+kind;src=u.load_asset(SRC+'/'+name);assert src
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(SRC+'/'+name,DEST+'/'+name)
    # Rebuild from accepted source text on each invocation, preserving its newer
    # advection/refraction fixes rather than regenerating an older material chain.
    g=Graph(m,'SurfaceDetail')
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='SurfaceDetail':mel.delete_material_expression(m,n)
    for prop in [u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_BASE_COLOR]:
        n=mel.get_material_property_input_node(m,prop)
        code=str(mel.get_material_property_input_node(src,prop).get_editor_property('code'))
        assert '(f.b-.5)*.27' in code
        code=code.replace('(f.b-.5)*.27','(f.b-.5)*.48')
        code=re.sub(r'float strength=min\(1.35,.22\*ambientDepth/[0-9.]+\)\*currentShape;',
            'float strength=min(1.65,.60*ambientDepth/%.8f)*currentShape;'%BOUND,code)
        # Height and slope use one depth envelope. Damp broad standing humps;
        # small travelling waves now supply most of the surface structure.
        code=code.replace('float rapidHeightGain=min(1,ambientDepth*.088/.038);','float rapidHeightGain=min(.55,ambientDepth*.045/.038);')
        code=code.replace('*(1-.40*rapidStrength)','*(1-.20*rapidStrength)')
        if prop==u.MaterialProperty.MP_BASE_COLOR:
            code=code.replace('float normalGain=max(.32*(1-currentShape),max(strength,.85*currentShape))*nearFade;',
                'float normalGain=max(.15*(1-currentShape),strength)*nearFade;')
            code=code.replace('*(1+1.8*rapidStrength)','*(1-.20*rapidStrength)')
            # Smooth gradient noise replaces the axis-aligned value-noise cells.
            # A continuous aerated skin has sparse torn holes and wispy edges,
            # rather than equally spaced grey/white islands throughout the cap.
            aeration='''struct WakeAeration {
 float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float2 grad(float2 p){float s,c;sincos(hash(p)*6.2831853,s,c);return float2(c,s);}
 float n(float2 p){
  float2 i=floor(p),f=frac(p),w=f*f*f*(f*(f*6-15)+10);
  float a=dot(grad(i),f),b=dot(grad(i+float2(1,0)),f-float2(1,0));
  float c=dot(grad(i+float2(0,1)),f-float2(0,1)),d=dot(grad(i+1),f-1);
  return saturate(.5+.7*lerp(lerp(a,b,w.x),lerp(c,d,w.x),w.y));
 }
 float3 froth(float2 p){
  float2 warp=float2(n(p*1.7+13),n(p*1.3+41))-.5;p+=warp*.48;
  float2 r=float2(p.x*.8+p.y*.6,-p.x*.6+p.y*.8);
  float broad=n(p*2.4),grain=n(r*39.7+17);
  float holes=smoothstep(.62,.79,n(p*6.7+warp*2)*.65+n(r*14.3)*.35);
  float threads=smoothstep(.40,.66,n(float2(r.x*1.4,r.y*9.5)+warp*5));
  return float3(.96-holes*.78,threads*smoothstep(.28,.65,broad),grain);
 }
};WakeAeration aeration;'''
            code,count=re.subn(r'struct WakeAeration \{.*?\};WakeAeration aeration;',lambda _:aeration,code,flags=re.S)
            assert count==1
            # Alpha now carries fresh pressure-front aeration from the runtime;
            # the transported red field remains a much quieter fading trail.
            code=code.replace('float2 trail=0;', 'float2 trail=0;float contactSignal=0;')
            code=code.replace('trail=Texture2DSampleLevel(Detail,DetailSampler,uv,0).rg*windowBlend;',
                '{float4 detailSample=Texture2DSampleLevel(Detail,DetailSampler,uv,0);trail=detailSample.rg*windowBlend;contactSignal=detailSample.a*windowBlend*saturate(WakeReady);}')
            # The transported concentration supplies placement/lifetime; moving
            # lace supplies holes. Contact foam must remain readable in shade.
            code=code.replace('float concentration=smoothstep(.08,.72,trail.x*FoamGain);',
                'float concentration=smoothstep(.055,.55,trail.x*FoamGain);')
            code=code.replace('float interactionFoam=concentration*flecks*.62*nearFade;',
                '''// A wet, moving shoreline generates intermittent aeration rather
// than a constant outline. The signed bank field is shared by both meshes.
float edgeBand=smoothstep(.06,.25,bankDistance)*(1-smoothstep(.55,1.35,bankDistance));
float edgeActivity=edgeBand*smoothstep(.025,.10,ambientDepth)*(1-smoothstep(.45,.90,ambientDepth))
    *smoothstep(.10,.55,length(ambientVelocity))*inBake;
float3 skin=float3(.9,.08,.5);
[branch]if(max(max(concentration,edgeActivity),contactSignal)>.005 && nearFade>.001)
 skin=lerp(aeration.froth(fpa/5.5),aeration.froth(fpb/5.5),fw);
float wakeCrest=smoothstep(.07,.28,length(slope));
float contactBreakup=lerp(.08,skin.y,rapidResolve);
// Connected white caps ride the bow/shoulder band. Small holes and a ragged
// boundary prevent a smooth painted stripe without destroying its main shape.
float contactGrain=lerp(na,nb,fw);
float focusedContact=smoothstep(.14,.65,contactSignal+(contactGrain-.5)*.10);
float crestCoverage=lerp(.88,skin.x,detailResolve);
float crestHoles=lerp(.95,lerp(.90,1,skin.z),detailResolve);
float frontFoam=focusedContact*crestCoverage*crestHoles;
float fringeFoam=smoothstep(.025,.22,contactSignal)*contactBreakup*.32;
float oldTrail=concentration*contactBreakup*.055;
float interactionFoam=saturate(frontFoam+fringeFoam+oldTrail)*nearFade;
Normal=normalize(Normal+float3(skin.z-.5,contactGrain-.5,0)*.07*focusedContact*detailResolve);
float edgeFoam=edgeActivity*contactBreakup*lerp(.38,.85,wakeCrest)*nearFade*rapidResolve;''')
            assert 'aeration.froth' in code
            assert 'contactSignal=detailSample.a' in code
            code=code.replace('foam=saturate(foam+interactionFoam);',
                'foam=saturate(foam+interactionFoam+edgeFoam)*FoamVisibility;')
            code=code.replace('Rough=clamp(lerp(.19,.28,riffle)+foam*.34,.17,.65);',
                'Rough=clamp(lerp(.105,.17,riffle)+foam*.48,.10,.65);')
            code=code.replace('float3 foamColour=lerp(float3(.43,.51,.47),float3(.78,.84,.79),saturate(whitewater*3));',
                'float3 foamColour=lerp(float3(.72,.78,.76),float3(.93,.96,.94),saturate(whitewater*3+interactionFoam*2+edgeFoam*2));')
            assert 'edgeFoam*2' in code
            inputs=list(n.get_editor_property('inputs'))
            if 'FoamVisibility' not in {str(i.get_editor_property('input_name')) for i in inputs}:
                n.set_editor_property('inputs',inputs+[props(u.CustomInput(),input_name='FoamVisibility')])
            g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='FoamVisibility',default_value=1),n,'FoamVisibility')
        n.set_editor_property('code',code)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m
