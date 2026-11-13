"""Keep painted mask gradients through temporal coverage, with stable shadows."""
import unreal as u,json,traceback
from pathlib import Path
O=Path(u.Paths.project_dir()).resolve()/'Art/Export/LidarStudy/FloraPath';mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
report={'ok':False,'materials':[]}
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def node(m,c,**kw):return props(mel.create_material_expression(m,c),**kw)
def wire(a,b,p,out=''):assert mel.connect_material_expressions(a,out,b,p)
try:
 rows=json.loads((O/'build-report.json').read_text())['materials'];seen=set()
 for row in rows:
  if not row['foliage'] or row['path'] in seen:continue
  seen.add(row['path']);m=u.load_asset(row['path']);assert m
  es=[];pending=[mel.get_material_property_input_node(m,getattr(u.MaterialProperty,k)) for k in ['MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_SPECULAR','MP_OPACITY_MASK','MP_OPACITY','MP_SUBSURFACE_COLOR','MP_EMISSIVE_COLOR']];visited=set()
  while pending:
   x=pending.pop()
   if not x or x.get_path_name() in visited:continue
   visited.add(x.get_path_name());es.append(x);pending.extend(y for y in mel.get_inputs_for_material_expression(m,x) if y)
  alpha=next(x for x in es if isinstance(x,u.MaterialExpressionCustom) and 'float x=Mask' in x.get_editor_property('code'))
  # Re-runs reconnect a single named coverage network, preserving source masks.
  for x in list(es):
   if isinstance(x,u.MaterialExpression) and x.get_editor_property('desc')=='PathPainterlyCoverage':mel.delete_material_expression(m,x)
  inputs=[props(u.CustomInput(),input_name=n) for n in ['Coverage','Seed','Softness']]
  coverage=node(m,u.MaterialExpressionCustom,desc='PathPainterlyCoverage',inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,code='float c=smoothstep(0.015,max(0.05,Softness),saturate(Coverage));uint leaf=(uint)(Seed*255.);uint2 p=(uint2)Parameters.SvPosition.xy+uint2(leaf*37u,leaf*91u);return step(ViewScalarBlueNoise(p,View.StateFrameIndex),c);')
  seed=node(m,u.MaterialExpressionVertexColor,desc='PathPainterlyCoverage');soft=node(m,u.MaterialExpressionScalarParameter,desc='PathPainterlyCoverage',parameter_name='PaintedEdgeSoftness',default_value=.75)
  wire(alpha,coverage,'Coverage');wire(seed,coverage,'Seed','A');wire(soft,coverage,'Softness')
  shadow=node(m,u.MaterialExpressionMultiply,desc='PathPainterlyCoverage',const_b=1.7);wire(alpha,shadow,'A')
  switch=node(m,u.MaterialExpressionShadowReplace,desc='PathPainterlyCoverage');wire(coverage,switch,'Default');wire(shadow,switch,'Shadow');assert mel.connect_material_property(switch,'',u.MaterialProperty.MP_OPACITY_MASK)
  props(m,dither_opacity_mask=True,opacity_mask_clip_value=.5,has_pixel_animation=False)
  for x in es:
   if isinstance(x,u.MaterialExpressionScalarParameter) and str(x.get_editor_property('parameter_name'))=='NormalUpBlend':props(x,default_value=.95 if 'Leaf_0' in row['path'] else .6)
  mel.recompile_material(m);eal.save_loaded_asset(m);stats=mel.get_statistics(m);report['materials'].append({'path':row['path'],'pixel_instructions':stats.num_pixel_shader_instructions})
 report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(O/'soften-report.json').write_text(json.dumps(report,indent=2))
def quit(dt):u.unregister_slate_post_tick_callback(h);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);h=u.register_slate_post_tick_callback(quit)
