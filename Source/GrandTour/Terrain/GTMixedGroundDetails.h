#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTMixedGroundDetails.generated.h"
class AGTLandscapeSurface;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UStaticMesh;
class UMaterialInstanceDynamic;
/** Native grass state/deflection bridge for the mixed-surface route only. */
UCLASS()
class GRANDTOUR_API AGTMixedGroundDetails:public AActor
{
    GENERATED_BODY()
public:
    AGTMixedGroundDetails();
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<AGTLandscapeSurface> Surface;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> GrassMaterial;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Grass;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bGenerateAroundPlayer=false;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float GrassSpacingCm=55.f;
    /** LP3e: multiplies the near cards' XY and Z scale (clamped .5 to 1.5). Card positions and jitter depend only on GrassSpacingCm, never on this. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0.5",ClampMax="1.5")) float BladeScale=1.f;
    /** LP3e: near cards where style G is between .3 and .8 (rank grass at the bush edge and verges) grow this much taller (Z scale) and carry Straw in
     * per-instance custom data 3 (0 to 1; the grass material multiplies its diffuse by lerp(1, straw colour, Straw)). Only the streamed (bGenerateAroundPlayer) grass has the fourth float. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="1.0",ClampMax="3.0")) float RankBandScale=1.4f;
    /** Optional inexpensive distance cover. Near grass still owns all contacts. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> DistantGrassMaterial;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> DistantGrass;
    /** GS3 opt-in: inexpensive geometric pasture beyond the interactive layer. Null preserves legacy cards. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UStaticMesh> DistantPastureMesh;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> DistantPastureMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="130",ClampMax="400")) float DistantPastureSpacingCm=200.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="4000",ClampMax="20000")) float DistantPastureEndCm=15000.f;
    /** Keep authored grass LOD distances independent of the tree/prop performance preset. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bIndependentGrassLodScale=false;
    /** GP2 clump mode (streamed grass only, console variable gt.Grass.Clumps, default 1; 0 restores the single-card path at GrassSpacingCm for A/B).
     * `Grass` then draws PastureClumpMesh with GrassMaterial (the clump material) on a ClumpSpacingCm lattice; `RankGrass` draws RankClumpMesh with RankMaterial
     * on a 1.2 x ClumpSpacingCm lattice where the rank band weight (style G .3 to .8, smoothstep .3-.4 in, .7-.8 out) is above .2. Pasture clumps cover G over .8 and the
     * band weight below .2 (with G over .15, at the cover probability). Cards (and the distant layer's mesh) come from the mesh `Grass` was placed with; CardGrassMaterial is
     * the card material used when the variable is 0. Clumps bend and are removed under the wheels exactly as cards; RankGrass is not indexed for contact. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UStaticMesh> PastureClumpMesh;
    /** GP4b: optional second and third pasture mesh (patch variants B and C). Each lattice cell takes one of the set meshes by a per-cell hash, one ISM component per mesh (Grass = PastureClumpMesh,
     * GrassB, GrassC), so the variants mix with no pattern. PastureClumpMeshC is used only when PastureClumpMeshB is set. Leaving both empty is the single-mesh GP2 behaviour. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UStaticMesh> PastureClumpMeshB;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UStaticMesh> PastureClumpMeshC;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="40",ClampMax="120")) float ClumpSpacingCm=65.f;
    /** GP4b: pasture scale per lattice cell = Lerp(ClumpScaleMin, ClumpScaleMax, t), t = .67 x a per-cell hash + .33 x the 2.5 m value noise (both 0 to 1), so size drifts slowly instead of reading as a random field. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0.3",ClampMax="3")) float ClumpScaleMin=.8f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0.3",ClampMax="3")) float ClumpScaleMax=1.4f;
    /** GP4b: radius (cm) around the pawn inside which clumps are streamed (cards keep 33 m). The refresh moves the centre on a 4 m grid once the pawn is 2.5 m from it, so the guaranteed coverage is this minus 3.5 m
     * (diagonal); set it at least 4 m above the cull end so no streaming edge shows inside the fade. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="2000",ClampMax="8000")) float ClumpStreamRadiusCm=3300.f;
    /** GP4b: pasture cull distances (cm, start of the per-instance fade and the end where the instance is gone) applied to Grass, GrassB, GrassC and RankGrass in clump mode; the grass materials fade with
     * PerInstanceFadeAmount, which these distances drive. 0 for the end leaves the level's own cull distances alone. Card mode always restores the distances the level had at BeginPlay. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="20000")) float GrassCullStartCm=0.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="0",ClampMax="20000")) float GrassCullEndCm=0.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UStaticMesh> RankClumpMesh;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> RankMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> CardGrassMaterial;
    /** Distance at which the clump meshes' LOD1 takes over (InstanceLODDistanceScale is derived from the mesh's own LOD1 screen size for a 90 degree, 16:9 view). */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="300",ClampMax="3000")) float ClumpLod1DistanceCm=1200.f;
    /** GP4b: distance at which LOD2 takes over. The GPU LOD selection has one distance scale per component, so LOD2 lands at ClumpLod1DistanceCm x (LOD1 screen size / LOD2 screen size) of the mesh; this value is what the
     * mesh's LOD2 screen size should be authored for (the LiDAR install sets it on the patch meshes) and what GrassReport compares the effective distance against. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,meta=(ClampMin="600",ClampMax="6000")) float ClumpLod2DistanceCm=2200.f;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> RankGrass;
    /** GP4b: the second and third pasture components (patch variants B and C); empty unless the clump mode streams more than one pasture mesh. */
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> GrassB;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> GrassC;
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UFUNCTION(BlueprintCallable) void ApplyReviewGrassContact(FVector2D Contact,bool Remove=false);
    UFUNCTION(BlueprintPure) FString GrassReport() const;
    /** PF1: checks the incrementally maintained streaming state (clump mode, no job in flight): component counts against the per-instance arrays, duplicate keys, instances outside the disc, the contact buckets and the
     * bent and removed sets against the remembered contacts, the rank and distant lists. With bRebuild it also re-evaluates every lattice cell of the disc from scratch (the old full refresh) and appends how many cells the
     * live instances miss or hold extra. "ok" when nothing is wrong; the rebuild counts are appended after it (rebuild_missing=, rebuild_extra=). */
    UFUNCTION(BlueprintPure) FString StreamingConsistency(bool bRebuild) const;
    /** Development capture only: finish the current grass window without changing
     * ordinary gameplay streaming budgets, placement rules or contacts. */
    bool FinishReviewStreaming();
    /** GP4b: pasture instances over Grass, GrassB and GrassC (the rank band and the distant cards are separate). */
    UFUNCTION(BlueprintPure) int32 NearGrassCount() const;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Dynamic;
    /** GP4b: everything that is indexed per ISM component for the contact program, one set per pasture component (0 = Grass, which also carries the authored instances of the other maps and the cards; 1 = GrassB; 2 = GrassC).
     * Keys[I] and Straw[I] describe instance I of that component (streamed grass only); RememberedGrass stays shared because a lattice cell always maps to the same component. */
    struct FGrassLayer
    {
        TArray<FTransform> Originals;
        TArray<uint8> Packed;
        TArray<float> RootHeights;
        TMap<FIntPoint,TArray<int32>> Buckets;
        TSet<int32> Bent,Removed;
        TArray<FIntPoint> Keys;
        TArray<float> Straw;
        void ResetIndex(){Originals.Reset();Packed.Reset();RootHeights.Reset();Buckets.Reset();Bent.Reset();Removed.Reset();}
        void Reset(){ResetIndex();Keys.Reset();Straw.Reset();}
    };
    static constexpr int32 MaxLayers=3;
    FGrassLayer Layers[MaxLayers];
    UInstancedStaticMeshComponent* LayerComp(int32 L) const;
    /** Pasture meshes in use: 1 (PastureClumpMesh) to 3. */
    int32 PastureLayerCount() const;
    UStaticMesh* PastureMeshFor(int32 L) const;
    float Carry=0;
    bool bGrassDirty=false;
    void IndexGrass();
    void IndexLayer(int32 L);
    /** Card mode refreshes the whole disc in one go (bImmediate is ignored); clump mode starts an incremental ring job (see below), and bImmediate runs it to the end at once (BeginPlay). */
    void RefreshGrass(FVector2D Centre,bool bImmediate=false);
    /** PF1: clump streaming is an incremental, time-sliced ring job. A job moves the snapped centre, lists only the lattice cells that enter the new disc (cells inside both discs are never revisited), then runs
     * Leave (instances outside the new disc become free slots), Enter (evaluate the pending cells under a time budget; accepted cells refill free slots, the rest are added in one AddInstances call per component per
     * slice) and Compact (free slots left over are closed by moving the last instance into them). One job runs at a time. Streams 0..MaxLayers-1 are the pasture components (contact-indexed), stream MaxLayers is RankGrass. */
    enum class EStreamPhase:uint8{Idle,Leave,Enter,Compact};
    /** Lazy walk over the lattice cells that enter a disc, rows nearest the centre first: the cells whose jittered position (hash seeds SeedX, SeedY) lies in the disc of Radius around New and not in the disc around Old
     * (Old.X >= DBL_MAX/2 means there is no old disc, so every cell of the new one enters). Nothing is listed up front, so a first fill costs nothing in the frame that starts it. */
    struct FRingCursor
    {
        double Step=1,Radius=1;uint32 SeedX=0,SeedY=1;FVector2D Old=FVector2D::ZeroVector,New=FVector2D::ZeroVector;bool bOld=false;
        TArray<int32> Rows;int32 RowIndex=0,RowY=0,X=0,XEnd=-1,InLo=1,InHi=0;bool bRow=false;
        void Begin(double InStep,uint32 InSeedX,uint32 InSeedY,FVector2D InOld,FVector2D InNew,double InRadius);
        bool Next(FIntPoint& Out);
        bool Done() const{return !bRow && RowIndex>=Rows.Num();}
        void Clear(){Rows.Reset();RowIndex=0;bRow=false;}
    };
    EStreamPhase ClumpPhase=EStreamPhase::Idle;
    FRingCursor PasturePending,RankPending;
    int32 LeaveStream=0,LeaveCursor=0,CompactStream=0,CompactCursor=0,SlicesSinceDirty=0;
    TArray<int32> FreeSlots[MaxLayers+1];
    bool bStreamTouched[MaxLayers+1]={};
    void StartClumpJob(FVector2D Centre);
    /** The test and values of one clump lattice cell, shared by the streaming and StreamingConsistency: false when the cell grows nothing; otherwise its pasture component (0 for rank), world transform and undeformed root height. */
    bool EvalClumpCell(FIntPoint K,double LatticeStep,bool bRank,int32 NumLayers,int32& OutLayer,FTransform& OutT,float& OutRootZ) const;
    /** Runs the current job until Deadline (FPlatformTime::Seconds); always makes progress. */
    void PumpClumpJob(double Deadline);
    bool ScanLeavingClumps(double Deadline);
    bool EnterClumps(double Deadline);
    bool CompactClumps(double Deadline);
    void FinishClumpJob();
    void MarkStreamsDirty();
    /** Per-instance contact bookkeeping of a pasture component, kept incrementally (IndexLayer rebuilds it from scratch for the card path and authored grass). */
    void UnindexPastureSlot(int32 L,int32 I);
    void WritePastureSlot(int32 L,int32 I,bool bNew,const FIntPoint& Key,const FTransform& T,float RootZ,float Straw);
    void RemoveLastPastureSlot(int32 L);
    void MovePastureSlot(int32 L,int32 From,int32 To);
    /** True when this actor streams grass around the player, a pasture clump mesh is set and gt.Grass.Clumps is not 0. */
    bool WantClumps() const;
    /** Swaps mesh, material, LOD scale and lattices between clump and card mode; every streamed instance and remembered contact is dropped. */
    void ApplyGrassMode(bool bClumps);
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CardDynamic;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> CardMesh;
    bool bClumpActive=false;
    float LastGrassLodScale=0.f;
    /** The level's own cull distances of Grass at BeginPlay, restored in card mode. */
    int32 CardCullStart=0,CardCullEnd=0;
    TArray<FIntPoint> RankKeys;
    FVector2D GrassCentre=FVector2D(DBL_MAX,DBL_MAX);
    TMap<FIntPoint,uint8> RememberedGrass;
    /** PF1: the distant card layer streams like the near clumps (ring only, Leave then Enter, time-sliced). Deadline is FPlatformTime::Seconds. */
    void StreamDistantGrass(FVector2D Centre,double Deadline);
    FVector2D DistantCentre=FVector2D(DBL_MAX,DBL_MAX);
    TArray<FIntPoint> DistantKeys;
    FRingCursor DistantPending;
    int32 DistantLeaveCursor=0,DistantSlices=0;
    bool bDistantDirty=false;
    EStreamPhase DistantPhase=EStreamPhase::Idle;
};
