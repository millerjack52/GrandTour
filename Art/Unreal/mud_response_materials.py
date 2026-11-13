"""Private response-study materials: same scanned soil, torn shallow sod, caked tyre detail."""
import unreal as u
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/MudResponse'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

def ground():
    path=BASE+'/M_ResponseGround'
    m=assets.load_asset(path) or assets.duplicate_asset('/Game/GrandTour/ArtTests/LandscapeMudScene/M_MudScene',path)
    nodes=list(mel.get_material_expressions(m));g=Graph(m,'MudResponse')
    for e in nodes:
        if not isinstance(e,u.MaterialExpressionCustom):continue
        code=str(e.get_editor_property('code'))
        if 'float4 water=' in code and 'float turf=' not in code:
            at=code.index('float thickness=')
            code=code[:at]+'float turf=saturate(-water.a);water.a=max(0,water.a);\n'+code[at:]
        if 'float3 fine=' in code and '// RESPONSE_SOD' not in code:
            key='float3 slurry='
            at=code.index(key)
            code=code[:at]+'''// RESPONSE_SOD: intact cover gives way inside the tyre, leaving broken islands at its edge.
float intact=turf*(1-smoothstep(.18,.85,field.a+grain.noise(P.xy/14)*.22));
float3 sod=Texture2DSample(Grass,GrassSampler,P.xy/135.).rgb;
float lum=dot(sod,float3(.2126,.7152,.0722));
sod=lerp(sod,lum*float3(.78,.83,.48),.65)*lerp(.8,.5,wet);
colour=lerp(colour,sod,intact);
'''+code[at:]
            tex=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/Textures/Stylised/T_GT_Grass_D'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            e.set_editor_property('inputs',list(e.get_editor_property('inputs'))+[props(u.CustomInput(),input_name='Grass')]);g.wire(tex,e,'Grass')
        if '// RESPONSE_TYRE_BED' not in code:
            # Existing outward soil flow gives the local tyre axis. Fine impressions
            # belong in shading: the 6.25 cm physics grid must not become tread blocks.
            tread='''// RESPONSE_TYRE_BED
float flowLength=length(field.gb);
float2 tyreAxis=float2(-field.b,field.g)/max(flowLength,.001);
float bed=smoothstep(.78,.98,field.a)*(1-pool)*mud;
float treadMask=bed*smoothstep(.15,.65,flowLength);
float treadPhase=6.283185*(dot(P.xy,tyreAxis)/21.+(1-field.a)*.8+grain.noise(P.xy/37.)*.12);
float treadFade=1-smoothstep(.6,2.2,fwidth(treadPhase));
float lug=pow(saturate(.5+.5*cos(treadPhase)),4)*treadMask*treadFade;
'''
            if 'float3 fine=' in code:
                code=code.replace('// RESPONSE_SOD',tread+'''// Compress fine aggregate contrast in the worked clay, preserving broad colour.
float workedLight=dot(colour,float3(.2126,.7152,.0722));
float3 pressed=lerp(colour,workedLight*float3(1.02,1.,.94),.4)*(.96-lug*.06);
colour=lerp(colour,pressed,bed*.8);
// RESPONSE_SOD''')
            elif 'float2 slope=' in code:
                code=code.replace('float2 tilt=',tread+'float2 tilt=')
                code=code.replace('return normalize(float3(BaseN.xy-',
                    'tilt+=tyreAxis*(-sin(treadPhase))*.10*lug;\nreturn normalize(float3(BaseN.xy-')
            # Flatten the scan's original chip relief where the tyre has pressed it.
            code=code.replace('(1-field.a*.75)','(1-field.a*.92)')
        e.set_editor_property('code',code)
    improve_rut_water(m)
    assert not mel.recompile_material(m)
    assets.save_loaded_asset(m);return m

def improve_rut_water(m):
    """A level pooled surface, wet meniscus, depth colour and quieter shallow ripples."""
    for e in mel.get_material_expressions(m):
        if not isinstance(e,u.MaterialExpressionCustom):continue
        code=str(e.get_editor_property('code'))
        if '// RESPONSE_POOL_V2' in code:continue
        code=code.replace('min(water.r,6)','min(water.r,32)')
        code=code.replace('float pool=smoothstep(.05,.6,depth);',
            '// RESPONSE_POOL_V2\nfloat pool=smoothstep(.08,1.25,depth);\nfloat wetRim=smoothstep(-2.5,.2,-paint.g*50-delta)*mud;')
        code=code.replace('float3 slurry=lerp(float3(.045,.052,.042),float3(.105,.092,.064),saturate(water.a*.65+.15));',
            'colour*=lerp(1.,.72,wetRim*(1-pool));\nfloat3 slurry=lerp(colour*.58,float3(.07,.067,.048),1-exp(-depth*.22));\nslurry=lerp(slurry,float3(.145,.12,.08),saturate(water.a)*.42);')
        # The soil scan and field tilt must not continue across the pool as a stony normal.
        code=code.replace('return normalize(float3(BaseN.xy-lerp(tilt,slope,ClayReview),BaseN.z));',
            'tilt=lerp(tilt,slope+waveN*(1.1+water.b*4.),pool);\nreturn normalize(float3(BaseN.xy-lerp(tilt,slope,ClayReview),BaseN.z));')
        code=code.replace('),.38,pool);', '),lerp(.09,.19,saturate(water.b)),pool);')
        code=code.replace('return lerp(.16,.055,pool);','return lerp(.16,.25,pool);')
        code=code.replace('float amp=.045/(1+i*.45);','float amp=.022*(1+water.b*3)/(1+i*.45);')
        e.set_editor_property('code',code)

def clod():
    path=BASE+'/M_ResponseClod'
    m=assets.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_ResponseClod',BASE,u.Material,u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,e)
    g=Graph(m);uv=g.node(u.MaterialExpressionTextureCoordinate)
    for kind,prop,normal in [('Diffuse',u.MaterialProperty.MP_BASE_COLOR,False),('nor_dx',u.MaterialProperty.MP_NORMAL,True)]:
        tex=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_'+kind)
        t=g.node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR);g.wire(uv,t,'UVs')
        if not normal:
            n=g.custom(['C'],'float l=dot(C,float3(.2126,.7152,.0722));return lerp(C,l.xxx,.6)*1.35;');g.wire(t,n,'C','RGB');t=n
        g.output(t,prop)
    g.output(g.scalar(.53),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.15),u.MaterialProperty.MP_SPECULAR)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not mel.recompile_material(m);assets.save_loaded_asset(m);return m

def tyre():
    # A study override only. Packed-mud normal detail follows native wheel UVs;
    # the stock skin/tread geometry remains intact.
    path=BASE+'/M_ResponseTyre'
    m=assets.load_asset(path) or assets.duplicate_asset('/Game/GrandTour/Materials/M_GT_Tyre',path)
    nodes=list(mel.get_material_expressions(m));g=Graph(m,'ResponseTyre')
    for e in nodes:
        if str(e.get_editor_property('desc'))=='ResponseTyre':mel.delete_material_expression(m,e)
    # Native wheel UVs rotate with the skin; use a tangent normal for packed mud grain.
    uv=g.node(u.MaterialExpressionTextureCoordinate)
    tex=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_nor_dx'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    g.wire(uv,tex,'UVs')
    coat=next(e for e in nodes if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='TyreCoat')
    n=g.custom(['N','Coat'],'float amount=dot(Coat,float4(.25,.25,.25,.25));return normalize(lerp(float3(0,0,1),N,amount*.65));')
    g.wire(tex,n,'N');g.wire(coat,n,'Coat');g.output(n,u.MaterialProperty.MP_NORMAL)
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assets.save_loaded_asset(m);return m
