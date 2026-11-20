#include "Core/GTLidarPerformanceSubsystem.h"
#include "GTLidarTreeInstances.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "InstanceDataSceneProxy.h"
#include "PrimitiveSceneProxy.h"
#include "RenderingThread.h"
#include "StaticMeshResources.h"
#include "TimerManager.h"

namespace
{
    using FCrown = UInstancedStaticMeshComponent;
    struct FCrownGroup
    {
        FCrown* Source;
        UStaticMesh* Caster;
        TMap<int32, TArray<int32>> Ranges;
    };

    bool PrepareRanges(FCrownGroup& Group)
    {
        auto& Source = *Group.Source;
        auto* Data = Source.GetStaticMesh()->GetRenderData();
        if (!Data || Data->LODResources.Num() != 4 || !Source.bOverrideMinLOD || Source.MinLOD != 1 ||
            Source.InstanceMinDrawDistance || Source.InstanceEndCullDistance || !Source.CastShadow ||
            Source.NumCustomDataFloats || Source.bVisibleInRayTracing || Source.bAffectDistanceFieldLighting ||
            Source.GetCollisionEnabled() != ECollisionEnabled::NoCollision ||
            Source.GetNumMaterials() != Group.Caster->GetStaticMaterials().Num()) return false;
        for (int32 Lod = 1; Lod <= 3; ++Lod)
        {
            const bool bCasts = Data->LODResources[Lod].Sections.ContainsByPredicate(
                [](const FStaticMeshSection& Section) { return Section.NumTriangles && Section.bCastShadow; });
            if (bCasts != (Lod < 3)) return false;
        }
        const double Threshold = FMath::FloorToDouble(Data->ScreenSize[3].GetValue() * 1024.) / 1024.;
        if (Threshold <= 0.) return false;
        FBox Bounds(ForceInit);
        const auto* Proxy = Source.GetSceneProxy();
        if (!Proxy) return false;
        ENQUEUE_RENDER_COMMAND(ReadLidarCrownBounds)([Proxy, &Bounds](FRHICommandListImmediate&)
        {
            const auto* Buffer = Proxy->GetInstanceSceneDataBuffers();
            if (!Buffer || !Buffer->GetNumInstances()) return;
            const auto First = Buffer->GetInstanceLocalBounds(0).ToBox();
            if (Buffer->GetFlags().bHasPerInstanceLocalBounds)
                for (int32 I = 1; I < Buffer->GetNumInstances(); ++I)
                    if (!Buffer->GetInstanceLocalBounds(I).ToBox().Equals(First, .01)) return;
            Bounds = First;
        });
        FlushRenderingCommands();
        if (!Bounds.IsValid) return false;
        // Preserve the shadow distances approved in the 16:9 chase-camera comparison.
        constexpr double ChaseProjection = 2.383508;
        for (int32 I = 0; I < Source.GetInstanceCount(); ++I)
        {
            FTransform Instance;
            if (!Source.GetInstanceTransform(I, Instance, true)) return false;
            const double Radius = (Bounds.GetExtent() * Instance.GetScale3D()).Size();
            const int32 Stop = FMath::RoundToInt(ChaseProjection * Radius / (Threshold * 500.)) * 500;
            if (Stop <= 0) return false;
            Group.Ranges.FindOrAdd(Stop).Add(I);
        }
        return !Group.Ranges.IsEmpty();
    }
}

static void InstallCrownShadows(const TMap<FString, FCrown*>& Trees)
{
    TArray<FCrownGroup> Groups;
    for (int32 Species = 0; Species < 3; ++Species)
    {
        auto* Source = Trees.FindRef(FString::Printf(TEXT("SM_Canopy_%d"), Species));
        const FString Path = FString::Printf(TEXT("/Game/GrandTour/ArtTests/LidarStudy/FloraWorld/CrownShadows/SM_FastCrownShadow_%d"), Species);
        auto* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
        if (!Source || !Mesh) return;
        auto& Group = Groups.Add_GetRef({Source, Mesh, {}});
        if (!PrepareRanges(Group))
        {
            UE_LOG(LogTemp, Warning, TEXT("LiDAR Fast shadows unavailable for %s. Retaining original shadows."), *Path);
            return;
        }
    }
    TArray<FCrown*> Created;
    int32 Instances = 0;
    for (auto& Group : Groups)
    {
        auto* Source = Group.Source;
        auto* Owner = Source->GetOwner();
        const auto Far = Source->GetStaticMesh()->GetBounds();
        const auto Built = Group.Caster->GetBounds();
        const FVector Extent = Far.BoxExtent.ComponentMax(Built.BoxExtent + (Built.Origin - Far.Origin).GetAbs());
        Group.Caster->SetExtendedBounds(FBoxSphereBounds(Far.Origin, Extent, Extent.Size()));
        const auto Seeds = GTLidarTreeInstances::RandomSeeds(*Source);
        auto* Prototype = NewObject<FCrown>(Owner, NAME_None, RF_Transient, Source);
        Prototype->ClearInstances();
        Prototype->SetStaticMesh(Group.Caster);
        Prototype->SetEvaluateWorldPositionOffset(false);
        for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot)
            Prototype->SetMaterial(Slot, Group.Caster->GetMaterial(Slot));
        Prototype->ComponentTags.Reset();
        Prototype->ComponentTags.Add(TEXT("LidarFastCrownShadow"));
        Prototype->SetCastHiddenShadow(true);
        Prototype->SetHiddenInGame(true);
        Prototype->SetRenderInMainPass(false);
        Prototype->SetRenderInDepthPass(false);
        for (const auto& Range : Group.Ranges)
        {
            auto* C = NewObject<FCrown>(Owner, NAME_None, RF_Transient, Prototype);
            C->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
            C->SetRelativeTransform(Source->GetRelativeTransform());
            GTLidarTreeInstances::CopySubset(*C, *Source, Range.Value, Seeds);
            C->SetCullDistances(Range.Key, Range.Key);
            Owner->AddOwnedComponent(C);
            Owner->AddInstanceComponent(C);
            C->RegisterComponent();
            Created.Add(C);
            if (!C->IsRegistered() || !C->GetSceneProxy() || !C->GetSceneProxy()->IsNaniteMesh() ||
                !C->CastShadow || !C->bCastHiddenShadow || !C->bHiddenInGame || C->bRenderInMainPass ||
                C->bRenderInDepthPass || C->GetInstanceCount() != Range.Value.Num())
            {
                for (auto* Partial : Created) Partial->DestroyComponent();
                Prototype->DestroyComponent();
                UE_LOG(LogTemp, Warning, TEXT("LiDAR Fast shadow proxy unavailable. Retaining original shadows."));
                return;
            }
            UE_LOG(LogTemp, Verbose, TEXT("GT_FAST_CROWN_RANGE mesh=%s stop_cm=%d instances=%d"),
                *Source->GetStaticMesh()->GetName(), Range.Key, C->GetInstanceCount());
            Instances += C->GetInstanceCount();
        }
        Prototype->DestroyComponent();
    }
    for (const auto& Group : Groups) Group.Source->SetCastShadow(false);
    UE_LOG(LogTemp, Display, TEXT("GT_FAST_CROWN_READY species=%d groups=%d instances=%d"), Groups.Num(), Created.Num(), Instances);
}

void UGTLidarPerformanceSubsystem::ApplyTreeSettings()
{
    auto* World = GetWorld();
    if (!World || World->bIsTearingDown) return;
    TMap<FString, FCrown*> Mature;
    TArray<FCrown*> VisibleTrees;
    int32 MatureGroups = 0, SaplingGroups = 0;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        TInlineComponentArray<FCrown*> Components(*It);
        for (auto* Tree : Components)
        {
            const bool bMature = Tree->ComponentHasTag(TEXT("FloraWorldCanopy"));
            if (!(bMature || Tree->ComponentHasTag(TEXT("FloraWorldSaplings"))) ||
                !Tree->IsVisible() || !Tree->GetStaticMesh() || !Tree->GetSceneProxy()) continue;
            VisibleTrees.Add(Tree);
            if (bMature)
            {
                ++MatureGroups;
                Mature.Add(Tree->GetStaticMesh()->GetName(), Tree);
            }
            else ++SaplingGroups;
        }
    }
    const bool bCastersReady = MatureGroups == 3 && Mature.Num() == 3;
    if ((!bCastersReady || (bStaticTreeLeaves && SaplingGroups < 3)) && ++CrownAttempts < 20)
    {
        World->GetTimerManager().SetTimer(CrownTimer, this, &UGTLidarPerformanceSubsystem::ApplyTreeSettings, .25f);
        return;
    }
    // Build the approved caster ranges using the original padded foliage bounds.
    if (bFastCrownShadows)
    {
        if (bCastersReady) InstallCrownShadows(Mature);
        else UE_LOG(LogTemp, Warning, TEXT("LiDAR Fast shadows unavailable: original tree groups did not register."));
    }
    if (bStaticTreeLeaves)
    {
        int32 Instances = 0;
        for (auto* Tree : VisibleTrees)
        {
            Tree->SetEvaluateWorldPositionOffset(false);
            Instances += Tree->GetInstanceCount();
        }
        UE_LOG(LogTemp, Display, TEXT("GT_LIDAR_STATIC_LEAVES mature=%d saplings=%d instances=%d"),
            MatureGroups, SaplingGroups, Instances);
    }
}
