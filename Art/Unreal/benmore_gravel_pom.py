"""Close-range blended-height parallax for world-XY gravel textures.

No PDO: leaves depth/shadow/collision geometry unchanged. Height samples use
explicit pre-parallax derivatives for stable mips inside the dynamic loop.
The same displaced coordinates drive colour and normal samples.
"""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface'
COLLECTION=DEST+'/MPC_Benmore_GravelPOM'

def attach(m,base_uv,p,n,mask,coords,expr,wire,custom,tracks):
    if not u.EditorAssetLibrary.does_asset_exist(DEST+'/T_Benmore_LooseGravelH'):
        return base_uv,{'gravel_pom':False}
    collection=u.load_asset(COLLECTION);assert collection
    view=expr(u.MaterialExpressionCameraVectorWS)
    camera=expr(u.MaterialExpressionCameraPositionWS)
    enable=expr(u.MaterialExpressionCollectionParameter,collection=collection,parameter_name='Enabled')
    textures=[]
    for name in ['T_Benmore_FineGravelH','T_Benmore_LooseGravelH']:
        textures.append(expr(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/'+name),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE))
    names=['UV','P','N','V','Camera','Mask','Coords','Enabled','FineH','CoarseH']
    code=tracks+'''
float2 dx=ddx(UV),dy=ddy(UV);
float distanceFade=1-smoothstep(1500,3000,length(Camera-P));
float facing=dot(normalize(N),normalize(V));
float angleFade=smoothstep(.08,.20,facing);
float strength=saturate(Enabled)*distanceFade*angleFade*smoothstep(.05,.65,Mask.r);
// This branch avoids height-map work outside the close road corridor.
[branch] if(strength<.001 || P.z<48) return UV;
float fineDepth=.8*(1-loose),coarseDepth=5.5*loose;
float totalDepth=fineDepth+coarseDepth;
float2 ray=-normalize(V).xy*(totalDepth*strength*max(N.z,.1)/max(facing,.08))/400;
int steps=(int)lerp(28.0,12.0,saturate(facing));
float stepDepth=1.0/steps;
float t=0,previousT=0,previousDiff=0;
float2 result=UV;
[loop] for(int i=0;i<=28;i++) {
    float2 at=UV+ray*t;
    float f=Texture2DSampleGrad(FineH,FineHSampler,at,dx,dy).r;
    float c=Texture2DSampleGrad(CoarseH,CoarseHSampler,at*.32,dx*.32,dy*.32).r;
    float depth=((1-f)*fineDepth+(1-c)*coarseDepth)/totalDepth;
    float diff=t-depth;
    if(diff>=0 || i==steps) {
        float blend=saturate(-previousDiff/max(diff-previousDiff,.00001));
        result=UV+ray*lerp(previousT,t,blend);
        break;
    }
    previousT=t;previousDiff=diff;t+=stepDepth;
}
return result;'''
    pom=custom(names,code,u.CustomMaterialOutputType.CMOT_FLOAT2)
    sources=[(base_uv,''),(p,''),(n,''),(view,''),(camera,''),(mask,'RGB'),(coords,'RGB'),(enable,''),(textures[0],''),(textures[1],'')]
    for name,(node,out) in zip(names,sources):wire(node,pom,name,out)
    return pom,{'gravel_pom':True,'pom_depth_cm':{'fine':.8,'loose':5.5},'pom_fade_m':[15,30],'pom_steps':[12,28],'pom_pixel_depth_offset':False}
