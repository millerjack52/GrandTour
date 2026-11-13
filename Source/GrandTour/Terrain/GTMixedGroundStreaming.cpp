#include "Terrain/GTMixedGroundDetails.h"
#include "Core/GTPerfProbe.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "LandscapeProxy.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"

bool AGTMixedGroundDetails::FinishReviewStreaming()
{
#if !UE_BUILD_SHIPPING
    if(!Surface || !bGenerateAroundPlayer)return true;
    const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);if(!Pawn)return false;
    const FVector2D Focus(Pawn->GetActorLocation());const double Deadline=FPlatformTime::Seconds()+5.;
    RefreshGrass(Focus);
    if(bClumpActive)PumpClumpJob(Deadline);
    const auto* Far=IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Grass.Distance"));
    if(DistantGrassMaterial && (!Far || Far->GetInt()!=0)){
        // Complete a previous camera's pending ring, then the new camera's ring.
        do{StreamDistantGrass(Focus,Deadline);}
        while((DistantPhase!=EStreamPhase::Idle || (Focus-DistantCentre).GetAbsMax()>800) && FPlatformTime::Seconds()<Deadline);
    }
    return ClumpPhase==EStreamPhase::Idle && DistantPhase==EStreamPhase::Idle;
#else
    return false;
#endif
}

// PF1 (docs/LIDAR_PLACE_PLAN.md): the streamed grass no longer rebuilds its whole disc on every recentre. Both the near clumps and the distant cards walk only the lattice cells that ENTER the new disc
// (never the interior), free the instances that LEFT it, and do the per-cell landscape queries under a per-tick time budget, so no frame carries a whole refresh. What a cell becomes (hash tests, scale, layer,
// height) is the same code as before; the card fallback (gt.Grass.Clumps 0) keeps its original full refresh.
namespace
{
    float ClumpHash(int32 X,int32 Y,uint32 Seed){uint32 H=uint32(X)*374761393u+uint32(Y)*668265263u+Seed*2246822519u;H=(H^(H>>13))*1274126177u;return float((H^(H>>16))&0xffffffu)/16777215.f;}
    /** Value noise on a Cell cm lattice, smoothstep-interpolated: the low-frequency size drift (2.5 m) that keeps clump size from reading as a per-clump random field. */
    float ClumpNoise(FVector2D P,double Cell,uint32 Seed)
    {
        const double U=P.X/Cell,V=P.Y/Cell;const int32 X=FMath::FloorToInt(U),Y=FMath::FloorToInt(V);
        const float Fx=FMath::SmoothStep(0.f,1.f,float(U-X)),Fy=FMath::SmoothStep(0.f,1.f,float(V-Y));
        return FMath::Lerp(FMath::Lerp(ClumpHash(X,Y,Seed),ClumpHash(X+1,Y,Seed),Fx),FMath::Lerp(ClumpHash(X,Y+1,Seed),ClumpHash(X+1,Y+1,Seed),Fx),Fy);
    }
    FVector2D CellPosition(int32 X,int32 Y,double Step,uint32 SeedX,uint32 SeedY){return FVector2D((X+.15+.7*ClumpHash(X,Y,SeedX))*Step,(Y+.15+.7*ClumpHash(X,Y,SeedY))*Step);}
    /** An accepted clump cell: its world transform (z = ground + surface delta - 2), the undeformed root height (ground - 2) and the pasture component its hash picked (rank clumps are always 0). */
    struct FClump{FTransform T;float RootZ;int32 Layer;};
    struct FAdd{FIntPoint Key;FClump C;};
    double Clock(){return FPlatformTime::Seconds();}
}

void AGTMixedGroundDetails::FRingCursor::Begin(double InStep,uint32 InSeedX,uint32 InSeedY,FVector2D InOld,FVector2D InNew,double InRadius)
{
    Step=InStep;SeedX=InSeedX;SeedY=InSeedY;Old=InOld;New=InNew;Radius=InRadius;bOld=InOld.X<DBL_MAX*.5;
    Rows.Reset();RowIndex=0;bRow=false;
    for(int32 Y=FMath::FloorToInt((New.Y-Radius)/Step)-1;Y<=FMath::CeilToInt((New.Y+Radius)/Step)+1;++Y)Rows.Add(Y);
    Rows.Sort([this](int32 A,int32 B){return FMath::Abs((A+.5)*Step-New.Y)<FMath::Abs((B+.5)*Step-New.Y);});
}

bool AGTMixedGroundDetails::FRingCursor::Next(FIntPoint& Out)
{
    const double R2=Radius*Radius;
    for(;;)
    {
        if(!bRow)
        {
            if(RowIndex>=Rows.Num())return false;
            RowY=Rows[RowIndex++];
            // A cell of this row has its position y in [(Y+.15) Step, (Y+.85) Step]; the widest chord of the new disc over that span bounds the cells that can be inside it.
            const double YLo=(RowY+.15)*Step,YHi=(RowY+.85)*Step;
            const double DyMin=(New.Y>=YLo && New.Y<=YHi) ? 0. : FMath::Min(FMath::Abs(New.Y-YLo),FMath::Abs(New.Y-YHi));
            if(DyMin>Radius)continue;
            const double Hw=FMath::Sqrt(R2-DyMin*DyMin);
            X=FMath::FloorToInt((New.X-Hw)/Step-.85);XEnd=FMath::CeilToInt((New.X+Hw)/Step-.15);
            // Cells that are inside the OLD disc whatever their jitter (the narrowest chord of the old disc over the span): never entering, skipped without a test.
            InLo=1;InHi=0;
            if(bOld)
            {
                const double DyMax=FMath::Max(FMath::Abs(Old.Y-YLo),FMath::Abs(Old.Y-YHi));
                if(DyMax<Radius){const double HwIn=FMath::Sqrt(R2-DyMax*DyMax);InLo=FMath::CeilToInt((Old.X-HwIn)/Step-.15);InHi=FMath::FloorToInt((Old.X+HwIn)/Step-.85);}
            }
            bRow=true;
        }
        while(X<=XEnd)
        {
            if(X>=InLo && X<=InHi){X=InHi+1;continue;}
            const int32 Cx=X++;
            const FVector2D P=CellPosition(Cx,RowY,Step,SeedX,SeedY);
            if((P-New).SizeSquared()>R2)continue;
            if(bOld && (P-Old).SizeSquared()<=R2)continue;
            Out=FIntPoint(Cx,RowY);return true;
        }
        bRow=false;
    }
}

void AGTMixedGroundDetails::StreamDistantGrass(FVector2D Centre,double Deadline)
{
    if(!Surface || !Surface->Landscape)return;
    GT_PERF_SCOPE(PerfStream,"StreamDistantGrass");
    const bool bFarPasture=bClumpActive && DistantPastureMesh && DistantPastureMaterial;
    const double Step=bFarPasture?FMath::Clamp(double(DistantPastureSpacingCm),130.,400.):130.;
    const double Radius=bFarPasture?FMath::Clamp(double(DistantPastureEndCm),4000.,20000.)+3000.:16000.;
    const double R2=Radius*Radius;
    auto Position=[&](FIntPoint K){return CellPosition(K.X,K.Y,Step,10,11);};
    bool Dirty=false;
    // A job starts only when the previous one is complete (so an instance outside the disc never meets a re-entering cell) and the focus is 8 m from the snapped centre.
    if(DistantPhase==EStreamPhase::Idle && (Centre-DistantCentre).GetAbsMax()>800)
    {
        GT_PERF_SCOPE(PerfRecentre,"StreamDistantGrass.Recentre");
        const FVector2D Old=DistantCentre;
        DistantCentre=FVector2D(FMath::GridSnap(Centre.X,800.),FMath::GridSnap(Centre.Y,800.));
        // Keep the interior: the new job lists only the cells that enter, and removes only the instances that left (the 40 m guard band includes the snapped focus offset and the chase camera offset).
        DistantPending.Begin(Step,10,11,Old,DistantCentre,Radius);DistantLeaveCursor=0;DistantPhase=EStreamPhase::Leave;
    }
    if(DistantPhase==EStreamPhase::Leave)
    {
        int32 Scanned=0;
        while(DistantLeaveCursor<DistantKeys.Num())
        {
            if((Scanned++&127)==127 && Clock()>=Deadline)break;
            const int32 I=DistantLeaveCursor;
            if((Position(DistantKeys[I])-DistantCentre).SizeSquared()<=R2){++DistantLeaveCursor;continue;}
            const int32 Last=DistantKeys.Num()-1;
            if(I!=Last)
            {
                FTransform T;DistantGrass->GetInstanceTransform(Last,T,true);
                DistantGrass->UpdateInstanceTransform(I,T,true,false,true);DistantKeys[I]=DistantKeys[Last];
            }
            DistantGrass->RemoveInstance(Last);DistantKeys.Pop();Dirty=true;
        }
        PerfStream.Work+=Scanned;
        if(DistantLeaveCursor>=DistantKeys.Num())DistantPhase=EStreamPhase::Enter;
    }
    if(DistantPhase==EStreamPhase::Enter && Clock()<Deadline)
    {
        // Spread landscape/material queries across frames; never rebuild a full distant field in one tick. No contact indexing, custom data or wind here.
        TArray<FTransform> Adds;TArray<FIntPoint> AddKeys;FIntPoint K;int32 Work=0;
        while(true)
        {
            if(Work>0 && Clock()>=Deadline)break;
            if(!DistantPending.Next(K))break;
            ++Work;
            const FVector2D P=Position(K);
            const auto S=Surface->SampleSurface(P);
            if(S.GrassCover<.15f || ClumpHash(K.X,K.Y,12)>FMath::Min(1.f,S.GrassCover*1.5f) || S.WaterDepthCm>2)continue;
            // GP2: paddock interiors (style G over .8) have no distant cards in clump mode; the ground material's pasture colour carries them. The band and verges keep them.
            if(bClumpActive && !bFarPasture && S.GrassCover>.8f)continue;
            const auto H=Surface->GroundHeightAt(FVector(P,0));if(!H.IsSet())continue;
            const float Scale=bFarPasture ? .92f+.16f*ClumpHash(K.X,K.Y,13) : 2.4f+.8f*ClumpHash(K.X,K.Y,13);
            FQuat Rotation=FRotator(0,ClumpHash(K.X,K.Y,14)*360,0).Quaternion();
            if(bFarPasture)
            {
                // Broad distant patches follow the local slope instead of hovering at their edges.
                const auto Hx=Surface->GroundHeightAt(FVector(P+FVector2D(100,0),0));
                const auto Hy=Surface->GroundHeightAt(FVector(P+FVector2D(0,100),0));
                if(Hx.IsSet() && Hy.IsSet())
                {
                    const FVector Normal=FVector(-(Hx.GetValue()-H.GetValue())/100.,-(Hy.GetValue()-H.GetValue())/100.,1).GetSafeNormal();
                    Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Normal)*Rotation;
                }
            }
            Adds.Add(FTransform(Rotation,FVector(P,H.GetValue()-2+S.SurfaceDeltaCm),FVector(Scale,Scale,bFarPasture?1.f:.85f+.5f*ClumpHash(K.X,K.Y,15))));AddKeys.Add(K);
        }
        PerfStream.Work+=Work;
        if(!Adds.IsEmpty()){DistantGrass->AddInstances(Adds,false,true,false);DistantKeys.Append(AddKeys);Dirty=true;}
        if(DistantPending.Done())
        {
            // Job complete: flush instance changes and bounds without recreating the scene proxy.
            DistantPending.Clear();DistantPhase=EStreamPhase::Idle;
            DistantGrass->MarkRenderInstancesDirty();bDistantDirty=false;DistantSlices=0;Dirty=false;
        }
    }
    // Flush instance changes every fourth changed slice while a long streaming job runs.
    bDistantDirty|=Dirty;
    if(bDistantDirty && ++DistantSlices>=4){DistantGrass->MarkRenderInstancesDirty();bDistantDirty=false;DistantSlices=0;}
}

void AGTMixedGroundDetails::StartClumpJob(FVector2D Centre)
{
    GT_PERF_SCOPE(PerfStart,"GrassStream.Start");
    const double Step=FMath::Clamp(double(ClumpSpacingCm),40.,120.),RankStep=Step*1.2,Radius=FMath::Clamp(double(ClumpStreamRadiusCm),2000.,8000.);
    FVector2D Old=GrassCentre;
    GrassCentre=FVector2D(FMath::GridSnap(Centre.X,400.),FMath::GridSnap(Centre.Y,400.));
    if(ClumpPhase!=EStreamPhase::Idle)
    {
        // Only called with a job in flight for a jump of several radii (teleport): nothing it had not finished is inside the new disc, so it is dropped, every instance is re-scanned and the new disc is filled whole.
        for(auto& F:FreeSlots)F.Reset();
        Old=FVector2D(DBL_MAX,DBL_MAX);
    }
    // GP2 clump lattices: pasture at ClumpSpacingCm (40 to 120), rank at 1.2 x that, the same 4 m refresh as the cards, GP4b: out to ClumpStreamRadiusCm (the cards keep 33 m). Each clump keeps the cards' hash test
    // (cover probability min(1, 1.5 G), no water) so verges thin out the same way. Rank band weight as the cards' Band: smoothstep(.3,.4,G) * (1 - smoothstep(.7,.8,G)); rank where it
    // is above .2, pasture elsewhere (G over .8, or the band weight below .2 with G over .15).
    PasturePending.Begin(Step,0,1,Old,GrassCentre,Radius);RankPending.Begin(RankStep,0,1,Old,GrassCentre,Radius);
    LeaveStream=LeaveCursor=CompactStream=CompactCursor=SlicesSinceDirty=0;ClumpPhase=EStreamPhase::Leave;
}

void AGTMixedGroundDetails::PumpClumpJob(double Deadline)
{
    GT_PERF_SCOPE(PerfSlice,"GrassStream.Slice");
    while(ClumpPhase!=EStreamPhase::Idle)
    {
        switch(ClumpPhase)
        {
        case EStreamPhase::Leave:   if(ScanLeavingClumps(Deadline))ClumpPhase=EStreamPhase::Enter;break;
        case EStreamPhase::Enter:   if(EnterClumps(Deadline))ClumpPhase=EStreamPhase::Compact;break;
        case EStreamPhase::Compact: if(CompactClumps(Deadline))FinishClumpJob();break;
        default:break;
        }
        if(Clock()>=Deadline)break;
    }
}

bool AGTMixedGroundDetails::ScanLeavingClumps(double Deadline)
{
    GT_PERF_SCOPE(PerfLeave,"GrassStream.Leave");
    const double Step=FMath::Clamp(double(ClumpSpacingCm),40.,120.),RankStep=Step*1.2,Radius=FMath::Clamp(double(ClumpStreamRadiusCm),2000.,8000.),R2=Radius*Radius;
    for(;LeaveStream<=MaxLayers;++LeaveStream,LeaveCursor=0)
    {
        const bool bRank=LeaveStream==MaxLayers;const double LatticeStep=bRank ? RankStep : Step;
        const TArray<FIntPoint>& Keys=bRank ? RankKeys : Layers[LeaveStream].Keys;
        for(;LeaveCursor<Keys.Num();++LeaveCursor,++PerfLeave.Work)
        {
            if((LeaveCursor&255)==255 && Clock()>=Deadline)return false;
            const FIntPoint K=Keys[LeaveCursor];
            if((CellPosition(K.X,K.Y,LatticeStep,0,1)-GrassCentre).SizeSquared()>R2)FreeSlots[LeaveStream].Add(LeaveCursor);
        }
    }
    return true;
}

bool AGTMixedGroundDetails::EvalClumpCell(FIntPoint K,double LatticeStep,bool bRank,int32 NumLayers,int32& OutLayer,FTransform& OutT,float& OutRootZ) const
{
    // GP4b scale: pasture = Lerp(ClumpScaleMin, ClumpScaleMax, .67 x per-cell hash + .33 x 2.5 m value noise); rank keeps the GP2 formula (.8 to 1.4 from the hash plus +-.15 from the noise). Pasture cells pick one of the
    // PastureLayerCount() meshes by hash seed 8, so the variants mix per cell and each lives in its own ISM component.
    const float ScaleMin=ClumpScaleMin,ScaleMax=FMath::Max(ClumpScaleMax,ClumpScaleMin);
    const int32 X=K.X,Y=K.Y;const FVector2D P=CellPosition(X,Y,LatticeStep,0,1);
    const auto S=Surface->SampleSurface(P);const float G=S.GrassCover;
    if(G<.15f || ClumpHash(X,Y,2)>FMath::Min(1.f,G*1.5f) || S.WaterDepthCm>2)return false;
    const float Band=FMath::SmoothStep(.3f,.4f,G)*(1.f-FMath::SmoothStep(.7f,.8f,G));
    if((Band>.2f)!=bRank)return false;
    const auto H=Surface->GroundHeightAt(FVector(P,0));if(!H.IsSet())return false;
    const float Scale=bRank ? .8f+.6f*ClumpHash(X,Y,3)+.15f*(2.f*ClumpNoise(P,250.,7)-1.f)
                            : FMath::Lerp(ScaleMin,ScaleMax,FMath::Clamp(.67f*ClumpHash(X,Y,3)+.33f*ClumpNoise(P,250.,7),0.f,1.f));
    OutLayer=(bRank || NumLayers==1) ? 0 : FMath::Min(NumLayers-1,FMath::FloorToInt(ClumpHash(X,Y,8)*NumLayers));
    OutT=FTransform(FRotator(0,ClumpHash(X,Y,4)*360,0),FVector(P,H.GetValue()-2+S.SurfaceDeltaCm),FVector(Scale));OutRootZ=float(H.GetValue()-2);
    return true;
}

bool AGTMixedGroundDetails::EnterClumps(double Deadline)
{
    GT_PERF_SCOPE(PerfEnter,"GrassStream.Enter");
    const double Step=FMath::Clamp(double(ClumpSpacingCm),40.,120.),RankStep=Step*1.2;
    const int32 NumLayers=FMath::Clamp(PastureLayerCount(),1,MaxLayers);
    TArray<FAdd> Adds[MaxLayers+1];
    int32 Count=0;
    auto Run=[&](FRingCursor& Cursor,double LatticeStep,bool bRank)->bool
    {
        FIntPoint K;
        while(true)
        {
            if(Count>=16 && Clock()>=Deadline)return false;
            if(!Cursor.Next(K))return true;
            ++Count;FClump C;
            if(EvalClumpCell(K,LatticeStep,bRank,NumLayers,C.Layer,C.T,C.RootZ))Adds[bRank ? MaxLayers : C.Layer].Add({K,C});
        }
    };
    const bool bDone=Run(PasturePending,Step,false) && Run(RankPending,RankStep,true);
    PerfEnter.Work=Count;
    {
        // Accepted cells refill the slots the Leave pass freed; the rest are added with one AddInstances call per component for this slice.
        GT_PERF_SCOPE(PerfApply,"GrassStream.Apply");
        for(int32 S=0;S<=MaxLayers;++S)
        {
            const TArray<FAdd>& A=Adds[S];if(A.IsEmpty())continue;
            const bool bRank=S==MaxLayers;UInstancedStaticMeshComponent* Comp=bRank ? RankGrass.Get() : LayerComp(S);
            int32 Next=0;
            for(;Next<A.Num() && !FreeSlots[S].IsEmpty();++Next)
            {
                const int32 I=FreeSlots[S].Pop();
                if(bRank){Comp->UpdateInstanceTransform(I,A[Next].C.T,true,false,true);RankKeys[I]=A[Next].Key;}
                else WritePastureSlot(S,I,false,A[Next].Key,A[Next].C.T,A[Next].C.RootZ,0.f);
            }
            if(Next<A.Num())
            {
                TArray<FTransform> Ts;Ts.Reserve(A.Num()-Next);
                for(int32 J=Next;J<A.Num();++J)Ts.Add(A[J].C.T);
                const TArray<int32> Indices=Comp->AddInstances(Ts,true,true,false);
                for(int32 J=Next;J<A.Num();++J)
                {
                    if(bRank)RankKeys.Add(A[J].Key);
                    else WritePastureSlot(S,Indices[J-Next],true,A[J].Key,A[J].C.T,A[J].C.RootZ,0.f);
                }
            }
            bStreamTouched[S]=true;
            PerfApply.Work+=A.Num();
        }
    }
    if(++SlicesSinceDirty>=6){MarkStreamsDirty();SlicesSinceDirty=0;}
    return bDone;
}

bool AGTMixedGroundDetails::CompactClumps(double Deadline)
{
    GT_PERF_SCOPE(PerfCompact,"GrassStream.Compact");
    for(;CompactStream<=MaxLayers;++CompactStream,CompactCursor=0)
    {
        TArray<int32>& F=FreeSlots[CompactStream];
        if(CompactCursor==0)F.Sort(TGreater<int32>());   // highest first: the last instance is then always a live one (or the slot itself)
        const bool bRank=CompactStream==MaxLayers;
        for(;CompactCursor<F.Num();++CompactCursor,++PerfCompact.Work)
        {
            if((CompactCursor&63)==63 && Clock()>=Deadline)return false;
            const int32 I=F[CompactCursor];
            if(bRank)
            {
                const int32 Last=RankKeys.Num()-1;
                if(I!=Last)
                {
                    FTransform T;RankGrass->GetInstanceTransform(Last,T,true);
                    RankGrass->UpdateInstanceTransform(I,T,true,false,true);RankKeys[I]=RankKeys[Last];
                }
                RankGrass->RemoveInstance(Last);RankKeys.Pop();
            }
            else
            {
                const int32 Last=Layers[CompactStream].Keys.Num()-1;
                if(I==Last)RemoveLastPastureSlot(CompactStream);else MovePastureSlot(CompactStream,Last,I);
            }
            bStreamTouched[CompactStream]=true;
        }
        F.Reset();
    }
    return true;
}

void AGTMixedGroundDetails::MarkStreamsDirty()
{
    for(int32 S=0;S<=MaxLayers;++S)
        if(bStreamTouched[S])
        {
            UInstancedStaticMeshComponent* Comp=S==MaxLayers ? RankGrass.Get() : LayerComp(S);
            Comp->MarkRenderInstancesDirty();bStreamTouched[S]=false;
        }
}

void AGTMixedGroundDetails::FinishClumpJob()
{
    MarkStreamsDirty();
    PasturePending.Clear();RankPending.Clear();
    for(auto& F:FreeSlots)F.Reset();
    ClumpPhase=EStreamPhase::Idle;
}

FString AGTMixedGroundDetails::StreamingConsistency(bool bRebuild) const
{
    if(!bClumpActive)return TEXT("cards");
    if(ClumpPhase!=EStreamPhase::Idle || DistantPhase!=EStreamPhase::Idle)return TEXT("busy");
    FString Err;int32 Faults=0;
    auto Fail=[&](const TCHAR* What,int32 N){if(N>0){++Faults;Err+=FString::Printf(TEXT("%s=%d; "),What,N);}};
    const double Step=FMath::Clamp(double(ClumpSpacingCm),40.,120.),RankStep=Step*1.2,Radius=FMath::Clamp(double(ClumpStreamRadiusCm),2000.,8000.),R2=Radius*Radius;
    const int32 NumLayers=FMath::Clamp(PastureLayerCount(),1,MaxLayers);
    auto BucketOf=[](const FVector& P){return FIntPoint(FMath::FloorToInt(P.X/128),FMath::FloorToInt(P.Y/128));};
    for(int32 L=0;L<MaxLayers;++L)
    {
        const FGrassLayer& Ly=Layers[L];const UInstancedStaticMeshComponent* Comp=LayerComp(L);const int32 N=Ly.Keys.Num();
        const FString Tag=FString::Printf(TEXT("L%d."),L);
        Fail(*(Tag+TEXT("component_count")),Comp->GetInstanceCount()!=N);
        Fail(*(Tag+TEXT("array_sizes")),(Ly.Originals.Num()!=N)+(Ly.Packed.Num()!=N)+(Ly.RootHeights.Num()!=N)+(Ly.Straw.Num()!=N));
        if(Ly.Originals.Num()!=N || Ly.Packed.Num()!=N || Ly.RootHeights.Num()!=N)continue;
        TSet<FIntPoint> Seen;int32 Dup=0,Outside=0;
        for(const FIntPoint& K:Ly.Keys)
        {
            if(Seen.Contains(K))++Dup;Seen.Add(K);
            if((CellPosition(K.X,K.Y,Step,0,1)-GrassCentre).SizeSquared()>R2)++Outside;
        }
        Fail(*(Tag+TEXT("duplicate_keys")),Dup);Fail(*(Tag+TEXT("outside_disc")),Outside);
        int32 Bucketed=0,BadBucket=0;
        for(const auto& Pair:Ly.Buckets)for(const int32 I:Pair.Value){++Bucketed;if(!Ly.Originals.IsValidIndex(I) || BucketOf(Ly.Originals[I].GetLocation())!=Pair.Key)++BadBucket;}
        Fail(*(Tag+TEXT("bucket_entries")),Bucketed!=N);Fail(*(Tag+TEXT("bad_bucket")),BadBucket);
        int32 BadSet=0;
        for(const int32 I:Ly.Bent)if(I<0||I>=N)++BadSet;
        for(const int32 I:Ly.Removed)if(I<0||I>=N)++BadSet;
        for(int32 I=0;I<N;++I)
        {
            const uint8 State=RememberedGrass.FindRef(Ly.Keys[I]);
            if(((State&1)!=0 && !Ly.Bent.Contains(I)) || ((State&2)!=0 && !Ly.Removed.Contains(I)))++BadSet;
        }
        Fail(*(Tag+TEXT("bent_removed")),BadSet);
        if(bRebuild)
        {
            // The old full refresh, for this layer: every lattice cell of the disc through the same test.
            FRingCursor Cursor;Cursor.Begin(Step,0,1,FVector2D(DBL_MAX,DBL_MAX),GrassCentre,Radius);
            FIntPoint K;int32 Missing=0,Expected=0;int32 Layer=0;FTransform T;float Root=0;
            while(Cursor.Next(K))if(EvalClumpCell(K,Step,false,NumLayers,Layer,T,Root) && Layer==L){++Expected;if(!Seen.Contains(K))++Missing;}
            Err+=FString::Printf(TEXT("%srebuild_expected=%d %srebuild_missing=%d %srebuild_extra=%d; "),*Tag,Expected,*Tag,Missing,*Tag,N-(Expected-Missing));
        }
    }
    {
        const int32 N=RankKeys.Num();TSet<FIntPoint> Seen;int32 Dup=0,Outside=0;
        Fail(TEXT("rank.component_count"),RankGrass->GetInstanceCount()!=N);
        for(const FIntPoint& K:RankKeys){if(Seen.Contains(K))++Dup;Seen.Add(K);if((CellPosition(K.X,K.Y,RankStep,0,1)-GrassCentre).SizeSquared()>R2)++Outside;}
        Fail(TEXT("rank.duplicate_keys"),Dup);Fail(TEXT("rank.outside_disc"),Outside);
        if(bRebuild)
        {
            FRingCursor Cursor;Cursor.Begin(RankStep,0,1,FVector2D(DBL_MAX,DBL_MAX),GrassCentre,Radius);
            FIntPoint K;int32 Missing=0,Expected=0,Layer=0;FTransform T;float Root=0;
            while(Cursor.Next(K))if(EvalClumpCell(K,RankStep,true,NumLayers,Layer,T,Root)){++Expected;if(!Seen.Contains(K))++Missing;}
            Err+=FString::Printf(TEXT("rank.rebuild_expected=%d rank.rebuild_missing=%d rank.rebuild_extra=%d; "),Expected,Missing,N-(Expected-Missing));
        }
    }
    {
        const int32 N=DistantKeys.Num();TSet<FIntPoint> Seen;int32 Dup=0,Outside=0;
        Fail(TEXT("distant.component_count"),DistantGrass->GetInstanceCount()!=N);
        const bool bFarPasture=bClumpActive && DistantPastureMesh && DistantPastureMaterial;
        const double FarStep=bFarPasture?FMath::Clamp(double(DistantPastureSpacingCm),130.,400.):130.;
        const double FarRadius=bFarPasture?FMath::Clamp(double(DistantPastureEndCm),4000.,20000.)+3000.:16000.;
        for(const FIntPoint& K:DistantKeys){if(Seen.Contains(K))++Dup;Seen.Add(K);if((CellPosition(K.X,K.Y,FarStep,10,11)-DistantCentre).SizeSquared()>FarRadius*FarRadius)++Outside;}
        Fail(TEXT("distant.duplicate_keys"),Dup);Fail(TEXT("distant.outside_disc"),Outside);
    }
    return Faults==0 ? FString(TEXT("ok ")+Err) : Err;
}

void AGTMixedGroundDetails::RefreshGrass(FVector2D Centre,bool bImmediate)
{
    if(!Surface || !Surface->Landscape)return;
    if(bClumpActive){StartClumpJob(Centre);if(bImmediate)PumpClumpJob(DBL_MAX);return;}
    GT_PERF_SCOPE(PerfRefresh,"RefreshGrass");
    GrassCentre=FVector2D(FMath::GridSnap(Centre.X,400.),FMath::GridSnap(Centre.Y,400.));
    // 33m radius minus the largest allowed diagonal focus offset still exceeds
    // the 27m final fade distance, so streamed edges remain invisible.
    // LP3e: the spacing floor is 30 cm (was 45). BladeScale only scales the cards; the lattice and its jitter depend on the spacing alone.
    const double Step=FMath::Clamp(double(GrassSpacingCm),30.,100.),Radius=3300.;
    const float Blade=FMath::Clamp(BladeScale,.5f,1.5f),RankZ=FMath::Clamp(RankBandScale,.5f,3.f);
    struct FNearCard{FTransform T;float Straw;};
    TMap<FIntPoint,FNearCard> Desired;
    auto Hash=[](int32 X,int32 Y,uint32 Seed){uint32 H=uint32(X)*374761393u+uint32(Y)*668265263u+Seed*2246822519u;H=(H^(H>>13))*1274126177u;return float((H^(H>>16))&0xffffffu)/16777215.f;};
    for(int32 Y=FMath::FloorToInt((GrassCentre.Y-Radius)/Step);Y<=FMath::CeilToInt((GrassCentre.Y+Radius)/Step);++Y)
    for(int32 X=FMath::FloorToInt((GrassCentre.X-Radius)/Step);X<=FMath::CeilToInt((GrassCentre.X+Radius)/Step);++X)
    {
        const FVector2D P((X+.15+.7*Hash(X,Y,0))*Step,(Y+.15+.7*Hash(X,Y,1))*Step);
        if((P-GrassCentre).SizeSquared()>Radius*Radius)continue;
        const auto S=Surface->SampleSurface(P);
        if(S.GrassCover<.15f || Hash(X,Y,2)>FMath::Min(1.f,S.GrassCover*1.5f) || S.WaterDepthCm>2)continue;
        const auto H=Surface->GroundHeightAt(FVector(P,0));if(!H.IsSet())continue;
        // Rank band: style G .3 to .8 (the bush edge and verges). Soft window .3 to .4 in, .7 to .8 out so no hard line shows; every card in the band is
        // RankZ taller, and its straw colour varies per card (hash seed 6) so the band mottles instead of reading as one flat strip.
        const float G=S.GrassCover;
        const float Band=FMath::SmoothStep(.3f,.4f,G)*(1.f-FMath::SmoothStep(.7f,.8f,G));
        const float Straw=Band*(.65f+.35f*Hash(X,Y,6));
        const float Scale=(.95f+.65f*Hash(X,Y,3))*Blade;
        const float ZScale=(.7f+.5f*Hash(X,Y,5))*Blade*FMath::Lerp(1.f,RankZ,Band);
        Desired.Add(FIntPoint(X,Y),FNearCard{FTransform(FRotator(0,Hash(X,Y,4)*360,0),FVector(P,H.GetValue()-2+S.SurfaceDeltaCm),FVector(Scale,Scale,ZScale)),Straw});
    }
    // Retain interior instances. Only recycled edge slots upload new transforms;
    // removal always uses the final slot, independent of the ISM removal policy.
    TArray<int32> Free;
    for(int32 I=0;I<Layers[0].Keys.Num();++I)
        if(Desired.Remove(Layers[0].Keys[I])==0)Free.Add(I);
    for(const auto& Pair:Desired)
    {
        if(Free.Num())
        {
            const int32 I=Free.Pop();Layers[0].Keys[I]=Pair.Key;Layers[0].Straw[I]=Pair.Value.Straw;
            Grass->UpdateInstanceTransform(I,Pair.Value.T,true,false,true);
        }
        else {Grass->AddInstance(Pair.Value.T,true);Layers[0].Keys.Add(Pair.Key);Layers[0].Straw.Add(Pair.Value.Straw);}
    }
    Free.Sort(TGreater<int32>());
    for(int32 I:Free)
    {
        const int32 Last=Layers[0].Keys.Num()-1;
        if(I!=Last)
        {
            FTransform T;Grass->GetInstanceTransform(Last,T,true);
            Grass->UpdateInstanceTransform(I,T,true,false,true);Layers[0].Keys[I]=Layers[0].Keys[Last];Layers[0].Straw[I]=Layers[0].Straw[Last];
        }
        Grass->RemoveInstance(Last);Layers[0].Keys.Pop();Layers[0].Straw.Pop();
    }
    IndexGrass();bGrassDirty=true;
}
