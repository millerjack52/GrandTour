#include "Terrain/GTMixedGroundDetails.h"
#include "Core/GTPerfProbe.h"
#include "Terrain/GTMudRunnerGrass.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Vehicle/GTTractionComponent.h"
#include "LandscapeProxy.h"
#include "GameFramework/Pawn.h"
// GP2: 1 (default) streams clump meshes, 0 restores the single-card path for A/B. Read every tick; a change swaps mode in place.
static TAutoConsoleVariable<int32> CVarGrassClumps(TEXT("gt.Grass.Clumps"),1,TEXT("1 draws the mixed-ground streamed grass as clump meshes (pasture plus rank band), 0 as single cards at GrassSpacingCm."),ECVF_Default);
static TAutoConsoleVariable<int32> CVarGrassDistance(TEXT("gt.Grass.Distance"),1,TEXT("Enable the inexpensive distant grass layer (0 for GPU-cost comparison)."),ECVF_Default);
// Instance LOD scale that puts a mesh's LOD1 at TargetCm: the GPU LOD selection compares the instance's bounds-box diagonal (MeanScale is the mean instance scale) at the distance with
// the mesh's own LOD1 screen size, and the screen size of a sphere is 2*max(.5*P00,.5*P11)*R/D (a 90 degree, 16:9 view: .889). InstanceLODDistanceScale multiplies that distance.
static float Lod1ScaleFor(const UStaticMesh* Mesh,float TargetCm,float MeanScale=1.1f)
{
    if(!Mesh || Mesh->GetNumLODs()<2)return 1.f;
    const FStaticMeshRenderData* RenderData=Mesh->GetRenderData();if(!RenderData)return 1.f;
    const float Screen1=RenderData->ScreenSize[1].GetValue();if(Screen1<=UE_KINDA_SMALL_NUMBER)return 1.f;
    const float Radius=Mesh->GetBounds().BoxExtent.Size()*MeanScale;
    return FMath::Clamp(TargetCm/FMath::Max(2.f*.889f*Radius/Screen1,1.f),.05f,20.f);
}
// GP4b: with LOD1 pinned at Lod1Cm by the scale above, LOD2 lands at Lod1Cm x (LOD1 screen size / LOD2 screen size) of the mesh. 0 when the mesh has no LOD2.
static float Lod2DistanceFor(const UStaticMesh* Mesh,float Lod1Cm)
{
    if(!Mesh || Mesh->GetNumLODs()<3)return 0.f;
    const FStaticMeshRenderData* RenderData=Mesh->GetRenderData();if(!RenderData)return 0.f;
    const float Screen1=RenderData->ScreenSize[1].GetValue(),Screen2=RenderData->ScreenSize[2].GetValue();
    return Screen2>UE_KINDA_SMALL_NUMBER ? Lod1Cm*Screen1/Screen2 : 0.f;
}
// GP4b: B and C draw the same way as Grass, so they take whatever flags the level gave it.
static void CopyRenderFlags(const UPrimitiveComponent* From,UPrimitiveComponent* To)
{
    To->CastShadow=From->CastShadow;To->bCastDynamicShadow=From->bCastDynamicShadow;
    To->bAffectDistanceFieldLighting=From->bAffectDistanceFieldLighting;To->bAffectDynamicIndirectLighting=From->bAffectDynamicIndirectLighting;
    To->SetVisibleInRayTracing(From->bVisibleInRayTracing);To->ShadowCacheInvalidationBehavior=From->ShadowCacheInvalidationBehavior;To->SetBoundsScale(From->BoundsScale);
}
UInstancedStaticMeshComponent* AGTMixedGroundDetails::LayerComp(int32 L)const{return L==0?Grass.Get():(L==1?GrassB.Get():GrassC.Get());}
UStaticMesh* AGTMixedGroundDetails::PastureMeshFor(int32 L)const{return L==0?PastureClumpMesh.Get():(L==1?PastureClumpMeshB.Get():PastureClumpMeshC.Get());}
int32 AGTMixedGroundDetails::PastureLayerCount()const{return PastureClumpMesh ? (PastureClumpMeshB ? (PastureClumpMeshC ? 3 : 2) : 1) : 0;}
int32 AGTMixedGroundDetails::NearGrassCount()const{int32 N=0;for(int32 L=0;L<MaxLayers;++L)if(const auto* C=LayerComp(L))N+=C->GetInstanceCount();return N;}
bool AGTMixedGroundDetails::WantClumps()const{return bGenerateAroundPlayer && PastureClumpMesh && CVarGrassClumps.GetValueOnGameThread()!=0;}
AGTMixedGroundDetails::AGTMixedGroundDetails()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostPhysics;
    Grass=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("NativeShortGrass"));SetRootComponent(Grass);
    Grass->SetCollisionEnabled(ECollisionEnabled::NoCollision);Grass->NumCustomDataFloats=3;
    Grass->SetCastShadow(false);Grass->SetBoundsScale(1.2f);
    DistantGrass=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("DistantGrassCover"));
    DistantGrass->SetupAttachment(Grass);
    DistantGrass->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    DistantGrass->SetCastShadow(false);DistantGrass->SetVisibleInRayTracing(false);
    DistantGrass->bAffectDistanceFieldLighting=false;
    DistantGrass->SetCullDistances(9500,12000);
    // GP4b: the second and third pasture component (patch variants B and C), configured like Grass. Streamed grass only fills them in clump mode.
    GrassB=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("NativeShortGrassB"));
    GrassC=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("NativeShortGrassC"));
    for(UInstancedStaticMeshComponent* C:{GrassB.Get(),GrassC.Get()})
    {
        C->SetupAttachment(Grass);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->NumCustomDataFloats=3;
        C->SetCastShadow(false);C->SetBoundsScale(1.2f);
    }
    // GP2: the rank band's clumps. No collision, no shadow, no contact indexing; its material and mesh are set when the clump mode is applied.
    RankGrass=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("RankClumpGrass"));
    RankGrass->SetupAttachment(Grass);
    RankGrass->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RankGrass->SetCastShadow(false);RankGrass->SetBoundsScale(1.2f);
    RankGrass->bAffectDistanceFieldLighting=false;
}
void AGTMixedGroundDetails::BeginPlay()
{
    Super::BeginPlay();if(!Surface || !GrassMaterial){SetActorTickEnabled(false);return;}
    // CardMesh is the mesh Grass was placed with: the card mesh, which the cards fallback and the distant layer keep using in clump mode.
    AddTickPrerequisiteActor(Surface);CardMesh=Grass->GetStaticMesh();Dynamic=UMaterialInstanceDynamic::Create(GrassMaterial,this);Grass->SetMaterial(0,Dynamic);
    Surface->RegisterResearchMaterial(Dynamic);Grass->GetCullDistances(CardCullStart,CardCullEnd);
    if(bGenerateAroundPlayer && CardGrassMaterial){CardDynamic=UMaterialInstanceDynamic::Create(CardGrassMaterial,this);Surface->RegisterResearchMaterial(CardDynamic);}
    if(bGenerateAroundPlayer && DistantGrassMaterial)
    {
        DistantGrass->SetStaticMesh(CardMesh);
        DistantGrass->SetMaterial(0,DistantGrassMaterial);
    }
    // LP3e: the streamed grass has a fourth custom float, Straw (the rank band's colour, material PerInstanceCustomData 3). Every other grass actor keeps the three
    // floats its saved instances were authored with. No instances exist yet, so resizing the buffer is free.
    if(bGenerateAroundPlayer)
    {
        Grass->SetNumCustomDataFloats(4);
        for(UInstancedStaticMeshComponent* C:{GrassB.Get(),GrassC.Get()}){C->SetNumCustomDataFloats(4);CopyRenderFlags(Grass,C);}
        ApplyGrassMode(WantClumps());RefreshGrass(FVector2D(Surface->GetActorLocation()),true);return;
    }
    IndexGrass();
}
void AGTMixedGroundDetails::ApplyGrassMode(bool bClumps)
{
    bClumpActive=bClumps;
    for(int32 L=0;L<MaxLayers;++L){LayerComp(L)->ClearInstances();Layers[L].Reset();}
    RankGrass->ClearInstances();DistantGrass->ClearInstances();
    RankKeys.Reset();RememberedGrass.Reset();
    DistantKeys.Reset();DistantPending.Clear();DistantPhase=EStreamPhase::Idle;DistantLeaveCursor=0;DistantSlices=0;bDistantDirty=false;
    ClumpPhase=EStreamPhase::Idle;PasturePending.Clear();RankPending.Clear();LeaveStream=LeaveCursor=CompactStream=CompactCursor=SlicesSinceDirty=0;
    for(auto& F:FreeSlots)F.Reset();
    for(bool& T:bStreamTouched)T=false;
    DistantCentre=FVector2D(DBL_MAX,DBL_MAX);GrassCentre=FVector2D(DBL_MAX,DBL_MAX);
    // GP4b: one component per pasture mesh. In card mode only Grass is used (the card mesh); B and C stay empty. The LOD1 distance is the same for all three (each mesh's own LOD1 screen size sets its scale).
    const float MeanScale=.5f*(FMath::Max(ClumpScaleMin,.1f)+FMath::Max(ClumpScaleMax,ClumpScaleMin));
    const IConsoleVariable* GlobalLod=IConsoleManager::Get().FindConsoleVariable(TEXT("r.StaticMeshLODDistanceScale"));
    const float LodCompensation=bIndependentGrassLodScale && GlobalLod ? FMath::Max(.01f,GlobalLod->GetFloat()) : 1.f;
    LastGrassLodScale=LodCompensation;
    const bool bFarPasture=bClumps && DistantPastureMesh && DistantPastureMaterial;
    DistantGrass->SetStaticMesh(bFarPasture?DistantPastureMesh.Get():CardMesh.Get());
    DistantGrass->SetMaterial(0,bFarPasture?DistantPastureMaterial.Get():DistantGrassMaterial.Get());
    DistantGrass->SetCullDistances(bFarPasture?FMath::RoundToInt(DistantPastureEndCm-2500):9500,bFarPasture?FMath::RoundToInt(DistantPastureEndCm):12000);
    DistantGrass->SetLODDistanceScale(bFarPasture?Lod1ScaleFor(DistantPastureMesh,5500.f*LodCompensation,1.f):1.f);
    for(int32 L=0;L<MaxLayers;++L)
    {
        UInstancedStaticMeshComponent* C=LayerComp(L);
        UStaticMesh* Mesh=bClumps ? (L<PastureLayerCount() ? PastureMeshFor(L) : nullptr) : (L==0 ? CardMesh.Get() : nullptr);
        if(Mesh && C->GetStaticMesh()!=Mesh && !C->SetStaticMesh(Mesh))
            UE_LOG(LogTemp,Warning,TEXT("GTMixedGroundDetails: SetStaticMesh(%s) refused on %s"),*Mesh->GetName(),*C->GetName());
        C->SetMaterial(0,(L>0 || bClumps || !CardDynamic)?Dynamic.Get():CardDynamic.Get());
        C->SetLODDistanceScale(bClumps && Mesh?Lod1ScaleFor(Mesh,ClumpLod1DistanceCm*LodCompensation,MeanScale):1.f);
        // The pasture cull distances (and with them the PerInstanceFadeAmount the materials fade by) apply to the clump components only; the cards go back to the level's.
        if(bClumps && GrassCullEndCm>0.f)C->SetCullDistances(FMath::RoundToInt(GrassCullStartCm),FMath::RoundToInt(GrassCullEndCm));
        else if(L==0)C->SetCullDistances(CardCullStart,CardCullEnd);
    }
    if(bClumps)
    {
        if(RankClumpMesh && RankGrass->GetStaticMesh()!=RankClumpMesh)RankGrass->SetStaticMesh(RankClumpMesh);
        if(RankMaterial)RankGrass->SetMaterial(0,RankMaterial);
        RankGrass->SetLODDistanceScale(Lod1ScaleFor(RankClumpMesh,ClumpLod1DistanceCm));
        if(GrassCullEndCm>0.f)RankGrass->SetCullDistances(FMath::RoundToInt(GrassCullStartCm),FMath::RoundToInt(GrassCullEndCm));
    }
}
void AGTMixedGroundDetails::IndexGrass()
{
    GT_PERF_SCOPE(PerfIndex,"IndexGrass");
    for(int32 L=0;L<MaxLayers;++L){IndexLayer(L);PerfIndex.Work+=LayerComp(L)->GetInstanceCount();}
}
void AGTMixedGroundDetails::IndexLayer(int32 L)
{
    UInstancedStaticMeshComponent* Comp=LayerComp(L);FGrassLayer& Ly=Layers[L];
    Ly.ResetIndex();
    for(int32 I=0;I<Comp->GetInstanceCount();++I)
    {
        FTransform T;Comp->GetInstanceTransform(I,T,true);Ly.Packed.Add(0x20);
        const FVector P=T.GetLocation();Ly.RootHeights.Add(P.Z);Ly.Buckets.FindOrAdd(FIntPoint(FMath::FloorToInt(P.X/128),FMath::FloorToInt(P.Y/128))).Add(I);
        // Keep the undeformed root separately: streaming must not accumulate
        // an already displaced root plus the same soil delta on every refresh.
        if(bGenerateAroundPlayer && Surface && Surface->Landscape)
            if(const auto H=Surface->GroundHeightAt(P);H.IsSet())
                T.SetLocation(FVector(P.X,P.Y,H.GetValue()-2));
        Ly.Originals.Add(T);
        uint8 State=0;
        if(bGenerateAroundPlayer && Ly.Keys.IsValidIndex(I))
        {
            State=RememberedGrass.FindRef(Ly.Keys[I]);
            if(State&1)Ly.Bent.Add(I);
            if(State&2){Ly.Removed.Add(I);Ly.Packed[I]=GTMudRunnerGrass::Remove(Ly.Packed[I]);}
        }
        const float Straw=bGenerateAroundPlayer && Ly.Straw.IsValidIndex(I) ? Ly.Straw[I] : 0.f;
        const float Values[4]={float(P.Z),float((State&1)!=0),float((State&2)!=0),Straw};
        const int32 Stride=Comp->NumCustomDataFloats;
        for(int32 Channel=0;Channel<FMath::Min(Stride,4);++Channel)
            if(!Comp->PerInstanceSMCustomData.IsValidIndex(I*Stride+Channel) || Comp->PerInstanceSMCustomData[I*Stride+Channel]!=Values[Channel])
                Comp->SetCustomDataValue(I,Channel,Values[Channel],false);
    }
    GT_PERF_SCOPE(PerfIndexDirty,"IndexGrass.MarkDirty");
    Comp->MarkRenderInstancesDirty();
}
// PF1: the incremental counterparts of IndexLayer for the streamed pasture components. A slot is one instance (the same index in the component and in every array of its FGrassLayer).
static FIntPoint BucketOf(const FVector& P){return FIntPoint(FMath::FloorToInt(P.X/128),FMath::FloorToInt(P.Y/128));}
void AGTMixedGroundDetails::UnindexPastureSlot(int32 L,int32 I)
{
    FGrassLayer& Ly=Layers[L];
    const FIntPoint K=BucketOf(Ly.Originals[I].GetLocation());
    if(TArray<int32>* B=Ly.Buckets.Find(K)){B->RemoveSingleSwap(I,EAllowShrinking::No);if(B->IsEmpty())Ly.Buckets.Remove(K);}
    Ly.Bent.Remove(I);Ly.Removed.Remove(I);
}
void AGTMixedGroundDetails::WritePastureSlot(int32 L,int32 I,bool bNew,const FIntPoint& Key,const FTransform& T,float RootZ,float Straw)
{
    FGrassLayer& Ly=Layers[L];UInstancedStaticMeshComponent* Comp=LayerComp(L);
    const FVector P=T.GetLocation();
    // Keep the undeformed root separately: streaming must not accumulate an already displaced root plus the same soil delta on every refresh.
    FTransform Original=T;Original.SetLocation(FVector(P.X,P.Y,RootZ));
    if(bNew)
    {
        ensure(I==Ly.Keys.Num());
        Ly.Keys.Add(Key);Ly.Straw.Add(Straw);Ly.Originals.Add(Original);Ly.Packed.Add(0x20);Ly.RootHeights.Add(P.Z);
    }
    else
    {
        UnindexPastureSlot(L,I);
        Comp->UpdateInstanceTransform(I,T,true,false,true);
        Ly.Keys[I]=Key;Ly.Straw[I]=Straw;Ly.Originals[I]=Original;Ly.Packed[I]=0x20;Ly.RootHeights[I]=P.Z;
    }
    Ly.Buckets.FindOrAdd(BucketOf(P)).Add(I);
    const uint8 State=RememberedGrass.FindRef(Key);
    if(State&1)Ly.Bent.Add(I);
    if(State&2){Ly.Removed.Add(I);Ly.Packed[I]=GTMudRunnerGrass::Remove(Ly.Packed[I]);}
    const float Values[4]={float(P.Z),float((State&1)!=0),float((State&2)!=0),Straw};
    Comp->SetCustomData(I,MakeArrayView(Values,FMath::Min(Comp->NumCustomDataFloats,4)),false);
}
void AGTMixedGroundDetails::RemoveLastPastureSlot(int32 L)
{
    FGrassLayer& Ly=Layers[L];const int32 Last=Ly.Keys.Num()-1;
    UnindexPastureSlot(L,Last);
    Ly.Keys.Pop();Ly.Straw.Pop();Ly.Originals.Pop();Ly.Packed.Pop();Ly.RootHeights.Pop();
    LayerComp(L)->RemoveInstance(Last);
}
void AGTMixedGroundDetails::MovePastureSlot(int32 L,int32 From,int32 To)
{
    FGrassLayer& Ly=Layers[L];UInstancedStaticMeshComponent* Comp=LayerComp(L);
    UnindexPastureSlot(L,To);
    // The moved instance keeps its bucket, bent and removed membership under its new index.
    const FIntPoint K=BucketOf(Ly.Originals[From].GetLocation());
    if(TArray<int32>* B=Ly.Buckets.Find(K)){const int32 At=B->Find(From);if(At!=INDEX_NONE)(*B)[At]=To;}
    if(Ly.Bent.Remove(From)>0)Ly.Bent.Add(To);
    if(Ly.Removed.Remove(From)>0)Ly.Removed.Add(To);
    FTransform X;Comp->GetInstanceTransform(From,X,true);
    Comp->UpdateInstanceTransform(To,X,true,false,true);
    const int32 Stride=Comp->NumCustomDataFloats;
    if(Stride>0)Comp->SetCustomData(To,MakeArrayView(&Comp->PerInstanceSMCustomData[From*Stride],Stride),false);
    Ly.Keys[To]=Ly.Keys[From];Ly.Straw[To]=Ly.Straw[From];Ly.Originals[To]=Ly.Originals[From];Ly.Packed[To]=Ly.Packed[From];Ly.RootHeights[To]=Ly.RootHeights[From];
    Ly.Keys.Pop();Ly.Straw.Pop();Ly.Originals.Pop();Ly.Packed.Pop();Ly.RootHeights.Pop();
    Comp->RemoveInstance(From);
}
void AGTMixedGroundDetails::ApplyReviewGrassContact(FVector2D Contact,bool Remove)
{
    const FIntPoint K(FMath::FloorToInt(Contact.X/128),FMath::FloorToInt(Contact.Y/128));
    for(int32 L=0;L<MaxLayers;++L)
    {
        FGrassLayer& Ly=Layers[L];UInstancedStaticMeshComponent* Comp=LayerComp(L);
        for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
            if(const auto* Indices=Ly.Buckets.Find(K+FIntPoint(X,Y)))for(int32 I:*Indices)
            {
                const FVector P=Ly.Originals[I].GetLocation();
                if(!GTMudRunnerGrass::RemovedByContact(FVector2D(P),Contact))continue;
                if(!Ly.Bent.Contains(I)){Ly.Bent.Add(I);Comp->SetCustomDataValue(I,1,1,false);bGrassDirty=true;}
                if(Remove && !Ly.Removed.Contains(I)){Ly.Packed[I]=GTMudRunnerGrass::Remove(Ly.Packed[I]);Ly.Removed.Add(I);Comp->SetCustomDataValue(I,2,1,false);bGrassDirty=true;}
                if(bGenerateAroundPlayer && Ly.Keys.IsValidIndex(I))RememberedGrass.FindOrAdd(Ly.Keys[I])|=Remove?3:1;
            }
    }
}
void AGTMixedGroundDetails::Tick(float Dt)
{
    Super::Tick(Dt);
    DistantGrass->SetVisibility(CVarGrassDistance.GetValueOnGameThread()!=0);
    if(bIndependentGrassLodScale && bClumpActive)
    {
        static const IConsoleVariable* GlobalLod=IConsoleManager::Get().FindConsoleVariable(TEXT("r.StaticMeshLODDistanceScale"));
        const float Scale=GlobalLod?FMath::Max(.01f,GlobalLod->GetFloat()):1.f;
        // Launch presets may run after BeginPlay. Update only component LOD scales,
        // preserving streamed instances and remembered wheel contacts.
        if(!FMath::IsNearlyEqual(Scale,LastGrassLodScale))
        {
            LastGrassLodScale=Scale;
            const float MeanScale=.5f*(FMath::Max(ClumpScaleMin,.1f)+FMath::Max(ClumpScaleMax,ClumpScaleMin));
            for(int32 L=0;L<PastureLayerCount();++L)
                LayerComp(L)->SetLODDistanceScale(Lod1ScaleFor(PastureMeshFor(L),ClumpLod1DistanceCm*Scale,MeanScale));
            if(DistantPastureMesh && DistantPastureMaterial)
                DistantGrass->SetLODDistanceScale(Lod1ScaleFor(DistantPastureMesh,5500.f*Scale,1.f));
        }
    }
    // GP2: gt.Grass.Clumps changed in play. The next 0.1 s tick below refreshes from the dropped state (GrassCentre is reset).
    if(Surface && bGenerateAroundPlayer && WantClumps()!=bClumpActive)ApplyGrassMode(!bClumpActive);
    if(Surface && bGenerateAroundPlayer)
    {
        // PF1: the near clump job and the distant ring share a 1.5 ms budget per tick (the near job first, up to 1.0 ms; the distant ring always gets at least 0.5 ms), so a refresh is spread over frames.
        const double Start=FPlatformTime::Seconds();
        if(bClumpActive && ClumpPhase!=EStreamPhase::Idle)PumpClumpJob(Start+.001);
        if(DistantGrassMaterial)
            if(CVarGrassDistance.GetValueOnGameThread()!=0)
                if(const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))StreamDistantGrass(FVector2D(Pawn->GetActorLocation()),FMath::Max(Start+.0015,FPlatformTime::Seconds()+.0005));
    }
    Carry+=Dt;if(Carry<.1f || !Surface)return;Carry=0;
    if(bGenerateAroundPlayer)
        if(const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        {
            const FVector2D P(Pawn->GetActorLocation());
            // GP4b: the clump streaming recentres once the pawn is 2.5 m from the (4 m snapped) centre (cards: 4 m), which keeps the guaranteed coverage within 3.5 m of the radius at the same refresh rate.
            if(bClumpActive)
            {
                // One job at a time; a jump of several radii (teleport) abandons the one in flight.
                const double Radius=FMath::Clamp(double(ClumpStreamRadiusCm),2000.,8000.);
                if(ClumpPhase==EStreamPhase::Idle ? (P-GrassCentre).GetAbsMax()>250. : (P-GrassCentre).GetAbsMax()>3.*Radius)RefreshGrass(P);
            }
            else if((P-GrassCentre).GetAbsMax()>400.)RefreshGrass(P);
        }
    if(const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        if(const auto* Traction=Pawn->FindComponentByClass<UGTTractionComponent>())for(const auto& W:Traction->Wheels)
            if(W.bInContact)
            {
                const auto S=Surface->SampleSurface(FVector2D(W.ContactPoint));
                // Native removal distance and packed state are exact. This host gate
                // maps exposed turf (>3cm compression) to the source deep-contact queue.
                if(S.bAuthored && S.GrassCover>.1f)ApplyReviewGrassContact(FVector2D(W.ContactPoint),S.CompressionCm>3.f);
            }
    GT_PERF_SCOPE(PerfBent,"GrassTick.Bent");
    for(int32 L=0;L<MaxLayers;++L)
    {
        FGrassLayer& Ly=Layers[L];UInstancedStaticMeshComponent* Comp=LayerComp(L);PerfBent.Work+=Ly.Bent.Num();
        for(int32 I:Ly.Bent)
        {
            FTransform T=Ly.Originals[I];FVector P=T.GetLocation();
            P.Z+=Surface->SampleSurface(FVector2D(P)).SurfaceDeltaCm;
            if(FMath::Abs(P.Z-Ly.RootHeights[I])<.02f)continue;
            Ly.RootHeights[I]=P.Z;T.SetLocation(P);bGrassDirty=true;
            Comp->SetCustomDataValue(I,0,P.Z,false);Comp->UpdateInstanceTransform(I,T,true,false,true);
        }
    }
    if(bGrassDirty){for(int32 L=0;L<MaxLayers;++L)if(LayerComp(L)->GetInstanceCount()>0)LayerComp(L)->MarkRenderInstancesDirty();bGrassDirty=false;}
}
FString AGTMixedGroundDetails::GrassReport()const
{
    int32 StrawCards=0,Instances=0,Bent=0,Removed=0;
    for(const FGrassLayer& Ly:Layers){for(const float V:Ly.Straw)StrawCards+=V>.01f;Instances+=Ly.Originals.Num();Bent+=Ly.Bent.Num();Removed+=Ly.Removed.Num();}
    FString Out=FString::Printf(TEXT("instances=%d bent=%d removed=%d native_radius_cm=64 custom_floats=%d straw=%d mode=%s near=%d rank=%d distant=%d"),Instances,Bent,Removed,Grass->NumCustomDataFloats,StrawCards,
        bClumpActive?TEXT("clumps"):TEXT("cards"),NearGrassCount(),RankGrass->GetInstanceCount(),DistantGrass->GetInstanceCount());
    // GP4b: the pasture components, the streaming radius, the cull distances in force and the LOD distances the first pasture mesh gives (LOD2 from its own screen sizes).
    int32 CullStart=0,CullEnd=0;Grass->GetCullDistances(CullStart,CullEnd);
    Out+=FString::Printf(TEXT(" layers=%d near_a=%d near_b=%d near_c=%d stream_radius_cm=%d cull_start_cm=%d cull_end_cm=%d lod1_cm=%d lod2_cm=%d"),bClumpActive?PastureLayerCount():1,Grass->GetInstanceCount(),GrassB->GetInstanceCount(),GrassC->GetInstanceCount(),
        FMath::RoundToInt(ClumpStreamRadiusCm),CullStart,CullEnd,bClumpActive?FMath::RoundToInt(ClumpLod1DistanceCm):0,bClumpActive?FMath::RoundToInt(Lod2DistanceFor(PastureClumpMesh,ClumpLod1DistanceCm)):0);
    // GP4b: the contact bookkeeping per pasture component (a contact must bend and remove across all three).
    Out+=FString::Printf(TEXT(" bent_a=%d bent_b=%d bent_c=%d removed_a=%d removed_b=%d removed_c=%d"),Layers[0].Bent.Num(),Layers[1].Bent.Num(),Layers[2].Bent.Num(),Layers[0].Removed.Num(),Layers[1].Removed.Num(),Layers[2].Removed.Num());
    return Out;
}
