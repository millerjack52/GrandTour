"""Use the licensed fern's painted values as pigment, retaining source coverage."""
import unreal as u,hashlib,json
from pathlib import Path
from benmore_river_life_materials import Graph,props
D='/Game/GrandTour/ArtTests/FloraTrail/FernSurface'
SOURCE='/Game/GrandTour/ArtTests/FloraTrail/UnderstoryTrial/Materials/M_Exact_fern_Fern_1_26834fc_combined'
ART=Path('D:/GrandTourAssets/FlippedNormals/Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/textures/Fern_0_1.png')
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
def build():
 path=D+'/T_FernPaint';t=u.load_asset(path)
 if not t:
  task=props(u.AssetImportTask(),filename=str(ART),destination_path=D,destination_name='T_FernPaint',automated=True,save=True)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=u.load_asset(path)
 assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE,max_texture_size=2048,lod_bias=0)
 E.set_metadata_tag(t,'SourceSHA256',hashlib.sha256(ART.read_bytes()).hexdigest());assert E.save_loaded_asset(t,False)
 path=D+'/M_FernSurface';m=u.load_asset(path) or E.duplicate_asset(SOURCE,path)
 for n in list(M.get_material_expressions(m)):
  if str(n.get_editor_property('desc'))=='FernPaint':M.delete_material_expression(m,n)
 g=Graph(m,'FernPaint');pigment=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SourcePigment')
 uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
 paint=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='FernPaint',texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE);g.wire(uv,paint,'UVs')
 detail=g.node(u.MaterialExpressionScalarParameter,parameter_name='FernDetailStrength',default_value=1.)
 gradient=g.node(u.MaterialExpressionScalarParameter,parameter_name='FernGradientStrength',default_value=1.)
 c=g.custom(['C','Paint','UV','Detail','Gradient'],'''// Source art is almost white inside the frond. Expand its painted values,
// while retaining the existing separate source opacity mask and cutoff.
float pigment=lerp(.50,1.18,saturate((Paint-.82)/.17));
// This frozen fern uses the third/fourth upper-row fronds in UV0.
// FBX V conversion puts their bases at V=.346 and tips near V=.05 in UE.
float tip=smoothstep(0.,1.,saturate((.346-UV.y)/.30));
float3 growth=lerp(.60,1.30,tip)*lerp(float3(.80,.95,1.12),float3(1.18,1.07,.92),tip);
return C*lerp(1.,pigment,Detail)*lerp(float3(1,1,1),growth,Gradient);''')
 for n,pin,out in [(pigment,'C','RGB'),(paint,'Paint','R'),(uv,'UV',''),(detail,'Detail',''),(gradient,'Gradient','')]:g.wire(n,c,pin,out)
 for prop,gain in [(u.MaterialProperty.MP_BASE_COLOR,.45),(u.MaterialProperty.MP_SUBSURFACE_COLOR,.15)]:
  scaled=g.custom(['C'],'return C*'+str(gain)+';');g.wire(c,scaled,'C');g.output(scaled,prop)
 assert not M.recompile_material(m);assert E.save_loaded_asset(m,False);return m
def component(world):
 owner=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='FloraTrail_SourceFoliage')
 return next(c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh.get_name()=='SM_Exact_fern')
def scene_signature(world):
 def canonical(path):
  # Save-as relocates embedded landscape objects without changing their content.
  for root in ('/Game/GrandTour/ArtTests/FloraTrail/UnderstoryTrial/L_FloraTrail_Understory',D+'/L_FloraTrail_Fern'):
   path=path.replace(root+'.'+root.rsplit('/',1)[-1],'<ReviewWorld>').replace(root,'<ReviewMap>')
  return path
 rows=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh:continue
   t=c.get_world_transform()
   row={'actor':a.get_actor_label(),'component':c.get_name(),'mesh':canonical(c.static_mesh.get_path_name()),'transform':[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()],'materials':[canonical(m.get_path_name()) if m else None for m in c.get_materials()]}
   if c.static_mesh.get_name()=='SM_Exact_fern':row['materials']=['FERN_REVIEW_SLOT']
   if isinstance(c,u.InstancedStaticMeshComponent):
    row['instances']=c.get_instance_count()
    row['transforms_sha256']=hashlib.sha256(json.dumps([[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()] for t in (c.get_instance_transform(i,True) for i in range(c.get_instance_count()))]).encode()).hexdigest()
   rows.append(row)
 return sorted(rows,key=lambda r:(r['actor'],r['component']))
