"""Instance-space crown normals; scene lights and source pigment stay fixed."""
import unreal as u,json,hashlib
from pathlib import Path
from benmore_river_life_materials import Graph
from flora_world_art_direction import local_volume
import flora_woodland_materials as wood
import flora_woodland_mud as brown
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/CrownForm')
CFG=json.loads((R/'Art/flora_crown_settings.json').read_text())
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/CrownForm/'+CFG['revision']
MAP=D+'/L_FloraTrail_CrownForm';BASE=brown.MAP
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
PROFILES={'baseline':{'CrownEnabled':0.,'CrownVolume':0.,'CrownCard':0.,'CrownTrim':0.},
          'mesh':{'CrownEnabled':1.,'CrownVolume':0.,'CrownCard':0.,'CrownTrim':0.},
          'volume':{'CrownEnabled':1.,'CrownVolume':.85,'CrownCard':0.,'CrownTrim':0.},
          'card':{'CrownEnabled':1.,'CrownVolume':0.,'CrownCard':1.,'CrownTrim':0.},
          'coverage':{'CrownEnabled':1.,'CrownVolume':.5,'CrownCard':1.,'CrownTrim':.08}}
for profile in PROFILES.values():profile['CrownOcclusion']=0.
PROFILES['occlusion']={**PROFILES['baseline'],'CrownOcclusion':.9}
PROFILES['normals']={'CrownEnabled':1.,'CrownVolume':.5,'CrownCard':1.,'CrownTrim':0.,'CrownOcclusion':0.}
SELECTED={k:CFG[k] for k in ('CrownEnabled','CrownVolume','CrownCard','CrownTrim','CrownOcclusion')}
PROFILES.update(final=SELECTED,reverse=SELECTED)

def clone(source):
    key=hashlib.sha1(source.get_path_name().encode()).hexdigest()[:8]
    path=D+'/M_Crown_'+key;m=u.load_asset(path)
    if not m:
        m=E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
        g=Graph(m,'CrownForm')
        params={k:g.node(u.MaterialExpressionScalarParameter,parameter_name=k,default_value=v) for k,v in SELECTED.items()}
        old=M.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
        oldport=M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL) or ''
        q=local_volume(g)
        radial=g.custom(['Q'],'return normalize(float3((Q.xy-.5)*2.,(Q.z-.62)*1.6)+float3(0,0,.0001));')
        g.wire(q,radial,'Q')
        world=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.wire(radial,world,'')
        card=g.custom(['UV'],'return normalize(float3((UV-.5)*1.8,.8));')
        g.wire(g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0),card,'UV')
        cardworld=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.wire(card,cardworld,'')
        normal=g.custom(['Old','Mesh','Radial','Card','CardStrength','Enabled','Volume'],'''float3 mesh=normalize(lerp(float3(0,0,1),normalize(Mesh),.78));
float3 branch=normalize(lerp(mesh,normalize(Card),saturate(CardStrength)));
float3 crown=normalize(lerp(branch,normalize(Radial),saturate(Volume)));
return normalize(lerp(Old,crown,saturate(Enabled)));''')
        for node,pin,out in [(old,'Old',oldport),(g.node(u.MaterialExpressionVertexNormalWS),'Mesh',''),(world,'Radial',''),(cardworld,'Card',''),(params['CrownCard'],'CardStrength',''),(params['CrownEnabled'],'Enabled',''),(params['CrownVolume'],'Volume','')]:g.wire(node,normal,pin,out)
        g.output(normal,u.MaterialProperty.MP_NORMAL)
        oldao=M.get_material_property_input_node(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        aoport=M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION) or ''
        ao=g.custom(['Q','UV','Original','Strength'],'''float radius=length((Q.xy-.5)*2.);
float exposed=max(smoothstep(.20,.90,radius),smoothstep(.78,.98,Q.z));
float fan=lerp(.65,1.,smoothstep(.10,.85,length((UV-.5)*2.)));
float visibility=lerp(.35,1.,exposed)*fan;
return Original*lerp(1.,visibility,saturate(Strength));''',u.CustomMaterialOutputType.CMOT_FLOAT1)
        g.wire(q,ao,'Q');g.wire(g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0),ao,'UV')
        g.wire(oldao or g.scalar(1.),ao,'Original',aoport);g.wire(params['CrownOcclusion'],ao,'Strength');g.output(ao,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        oldmask=M.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
        port=M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK) or ''
        mask=g.custom(['Mask','Trim'],'''#if SHADOW_DEPTH_SHADER
return Mask;
#else
return Mask-Trim;
#endif''',u.CustomMaterialOutputType.CMOT_FLOAT1)
        g.wire(oldmask,mask,'Mask',port);g.wire(params['CrownTrim'],mask,'Trim');g.output(mask,u.MaterialProperty.MP_OPACITY_MASK)
    for n in M.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name')) in SELECTED:
            n.set_editor_property('default_value',SELECTED[str(n.get_editor_property('parameter_name'))])
    assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
    return m

def geometry(world):
    data=json.dumps(wood.geometry(world))
    for root in (BASE,MAP):data=data.replace(root+'.'+root.rsplit('/',1)[-1],'<ReviewWorld>').replace(root,'<ReviewMap>')
    return json.loads(data)

def configure(mid,profile):
    for key,value in profile.items():mid.set_scalar_parameter_value(key,value)

def audit(mid):
    values={k:mid.get_scalar_parameter_value(k) for k in SELECTED}
    assert max(abs(values[k]-SELECTED[k]) for k in SELECTED)<1e-5,values
    return values
