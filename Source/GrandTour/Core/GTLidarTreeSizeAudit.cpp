#if WITH_EDITOR
#include "GTLidarTreeInstances.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "ConvexVolume.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InstanceDataSceneProxy.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Kismet/GameplayStatics.h"
#include "PrimitiveSceneProxy.h"
#include "RenderingThread.h"
#include "SceneView.h"
#include "StaticMeshResources.h"

namespace
{
    void SetFilmDirectory(const TArray<FString>& Args, UWorld* World)
    {
        if (!World || World->WorldType != EWorldType::Game || Args.Num() != 1 || FPaths::IsRelative(Args[0]) ||
            !IFileManager::Get().DirectoryExists(*Args[0]) ||
            UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy")) return;
        // Shot reads this class default at capture time. It is local to this process.
        GetMutableDefault<UEngine>()->GameScreenshotSaveDirectory.Path = Args[0];
        UE_LOG(LogTemp, Display, TEXT("GT_LIDAR_FILM_DIRECTORY path=%s"), *GetDefault<UEngine>()->GameScreenshotSaveDirectory.Path);
    }
    FAutoConsoleCommandWithWorldAndArgs FilmDirectory(TEXT("gt.Lidar.FilmDirectory"),
        TEXT("Write this driving film to the existing evidence directory."),
        FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(SetFilmDirectory));

    bool GetDrivingProjection(UWorld* World, FSceneViewProjectionData& View, double& Factor)
    {
        if (!World || World->WorldType != EWorldType::Game ||
            UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy")) return false;
        const auto* Controller = World->GetFirstPlayerController();
        const auto* Player = Controller ? Controller->GetLocalPlayer() : nullptr;
        if (!Player || !Player->ViewportClient ||
            !Player->GetProjectionData(Player->ViewportClient->Viewport, View)) return false;
        const float LODScale = IConsoleManager::Get().FindConsoleVariable(TEXT("r.StaticMeshLODDistanceScale"))->GetFloat();
        Factor = FMath::Max(View.ProjectionMatrix.M[0][0], View.ProjectionMatrix.M[1][1]) /
            (LODScale * Controller->LocalPlayerCachedLODDistanceFactor);
        return FMath::IsFinite(Factor) && Factor > 0;
    }

    void AuditTreeSizes(const TArray<FString>& Args, UWorld* World)
    {
        FSceneViewProjectionData View;
        double Factor;
        if (Args.Num() != 1 || !GetDrivingProjection(World, View, Factor)) return;
        FConvexVolume Frustum;
        GetViewFrustumBounds(Frustum, View.ComputeViewProjectionMatrix(), true);
        struct FGroup { FString Name; const FPrimitiveSceneProxy* Proxy; float Lod2, Lod3; };
        TArray<FGroup> Groups;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
            for (const auto* Component : Components)
            {
                if (!Component->IsVisible() || !Component->ComponentHasTag(TEXT("FloraWorldCanopy"))) continue;
                const UStaticMesh* Mesh = Component->GetStaticMesh();
                if (!Mesh || !Mesh->GetName().StartsWith(TEXT("SM_Canopy_")) ||
                    !Component->bOverrideMinLOD || Component->MinLOD != 1) return;
                const auto* Data = Mesh->GetRenderData();
                if (!Component->GetSceneProxy() || !Data || Data->LODResources.Num() != 4) return;
                // Match the 10 fractional bits in the engine's packed draw command.
                const auto Threshold = [Data](int32 LOD)
                {
                    return FMath::FloorToFloat(Data->ScreenSize[LOD].GetValue() * 1024) / 1024;
                };
                Groups.Add({Mesh->GetName(), Component->GetSceneProxy(), Threshold(2), Threshold(3)});
            }
        }
        if (Groups.Num() != 3) return;
        ENQUEUE_RENDER_COMMAND(LidarTreeSizeAudit)(
            [Groups = MoveTemp(Groups), Factor, Origin = View.ViewOrigin, Frustum, Mark = Args[0]](FRHICommandListImmediate&)
            {
                for (const auto& Group : Groups)
                {
                    const auto* Instances = Group.Proxy->GetInstanceSceneDataBuffers();
                    if (!Instances || Instances->GetNumInstances() == 0) return;
                    constexpr int32 Ranges[] = {55, 75, 90, 110, 150};
                    int32 Counts[UE_ARRAY_COUNT(Ranges)][3]{};
                    TArray<double> SwitchDistances;
                    for (int32 Index = 0; Index < Instances->GetNumInstances(); ++Index)
                    {
                        const FMatrix Matrix = Instances->GetInstanceToWorld(Index);
                        const FBox Box = Instances->GetInstanceLocalBounds(Index).ToBox();
                        const FVector Center = Matrix.TransformPosition(Box.GetCenter());
                        const double Distance = FVector::Dist(Center, Origin);
                        if (Distance > 15000.) continue;
                        const double Radius = (Box.GetExtent() * Matrix.GetScaleVector()).Size();
                        if (!Frustum.IntersectSphere(Center, Radius)) continue;
                        const double ScreenSize = Factor * Radius / FMath::Max(1., Distance);
                        const int32 Slot = ScreenSize >= Group.Lod2 ? 0 : ScreenSize >= Group.Lod3 ? 1 : 2;
                        SwitchDistances.Add(Factor * Radius / (Group.Lod2 * 100.));
                        for (int32 Range = 0; Range < UE_ARRAY_COUNT(Ranges); ++Range)
                            if (Distance <= Ranges[Range] * 100.) ++Counts[Range][Slot];
                    }
                    SwitchDistances.Sort();
                    const auto Quantile = [&SwitchDistances](double Fraction)
                    {
                        return SwitchDistances.IsEmpty() ? 0. : SwitchDistances[
                            FMath::RoundToInt((SwitchDistances.Num() - 1) * Fraction)];
                    };
                    for (int32 Range = 0; Range < UE_ARRAY_COUNT(Ranges); ++Range)
                        UE_LOG(LogTemp, Display, TEXT("GT_TREE_SIZE site=%s mesh=%s range=%d lod1=%d lod2=%d billboard=%d factor=%.6f switch_min_m=%.2f switch_median_m=%.2f switch_max_m=%.2f"),
                            *Mark, *Group.Name, Ranges[Range], Counts[Range][0], Counts[Range][1], Counts[Range][2],
                            Factor, Quantile(0), Quantile(.5), Quantile(1));
                }
            });
        FlushRenderingCommands();
    }
    FAutoConsoleCommandWithWorldAndArgs TreeSizes(TEXT("gt.Lidar.AuditTreeScreenSizes"),
        TEXT("Measure original mature tree detail transitions in the driving view, before occlusion."),
        FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(AuditTreeSizes));

    void ApplySizeRanges(const TArray<FString>& Args, UWorld* World)
    {
        FSceneViewProjectionData View;
        double Factor;
        int32 LimitMetres;
        if (Args.Num() != 1 || !LexTryParseString(LimitMetres, *Args[0]) || LimitMetres < 20 || LimitMetres > 250 ||
            !GetDrivingProjection(World, View, Factor))
        {
            UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE invalid range or camera projection"));
            return;
        }
        using FTree = UInstancedStaticMeshComponent;
        struct FPair { FTree* Near = nullptr; FTree* Far = nullptr; };
        TMap<FString, FPair> Pairs;
        int32 Shadows = 0;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            TInlineComponentArray<FTree*> Components(*It);
            for (FTree* C : Components)
            {
                if ((C->ComponentHasTag(TEXT("LidarOriginalCanopyShadow")) || C->ComponentHasTag(TEXT("LidarFullNaniteShadow"))) &&
                    C->IsRegistered() && C->CastShadow) ++Shadows;
                if (!C->IsVisible() || !C->ComponentHasTag(TEXT("FloraWorldCanopy"))) continue;
                const UStaticMesh* Mesh = C->GetStaticMesh();
                if (!Mesh || C->CastShadow || C->NumCustomDataFloats || C->ComponentHasTag(TEXT("LidarSizeRange")))
                {
                    UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE unexpected source %s casts=%d data=%d"),
                        *GetNameSafe(Mesh), C->CastShadow, C->NumCustomDataFloats);
                    return;
                }
                const bool bNear = C->ComponentHasTag(TEXT("TrialNearCanopy"));
                if (!Mesh->GetName().StartsWith(bNear ? TEXT("SM_NaniteRenderLod1_") : TEXT("SM_Canopy_")))
                {
                    UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE unexpected mesh=%s near=%d"), *Mesh->GetName(), bNear);
                    return;
                }
                auto& Pair = Pairs.FindOrAdd(Mesh->GetName().Right(1));
                FTree*& Part = bNear ? Pair.Near : Pair.Far;
                if (Part) { UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE repeated mesh=%s"), *Mesh->GetName()); return; }
                Part = C;
            }
        }
        if (Pairs.Num() != 3 || Shadows != 3)
        {
            UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE unexpected source groups=%d shadow_groups=%d"), Pairs.Num(), Shadows);
            return;
        }
        for (const auto& Item : Pairs)
        {
            const auto& Pair = Item.Value;
            if (!Pair.Near || !Pair.Far || !Pair.Far->GetStaticMesh()->GetRenderData() ||
                Pair.Far->GetStaticMesh()->GetRenderData()->LODResources.Num() != 4 ||
                Pair.Near->GetInstanceCount() != Pair.Far->GetInstanceCount() ||
                !Pair.Far->bOverrideMinLOD || Pair.Far->MinLOD != 1)
            {
                UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE invalid near/far pair=%s"), *Item.Key);
                return;
            }
        }
        int32 Total = 0, Buckets = 0;
        for (const auto& Item : Pairs)
        {
            const auto& Pair = Item.Value;
            const UStaticMesh* Mesh = Pair.Far->GetStaticMesh();
            const double Threshold = FMath::FloorToDouble(Mesh->GetRenderData()->ScreenSize[2].GetValue() * 1024.) / 1024.;
            if (Threshold <= 0) return;
            const FVector Extent = Mesh->GetBounds().BoxExtent;
            const auto Seeds = GTLidarTreeInstances::RandomSeeds(*Pair.Far);
            TMap<int32, TArray<int32>> ByRange;
            for (int32 I = 0; I < Pair.Far->GetInstanceCount(); ++I)
            {
                FTransform Instance;
                Pair.Far->GetInstanceTransform(I, Instance, true);
                // The renderer can enlarge bounds for displacement. Using the unpadded
                // original bounds and rounding down hands the transition to the source LODs.
                const double StopCm = Factor * (Extent * Instance.GetScale3D()).Size() / Threshold;
                const int32 Range = FMath::Min(LimitMetres * 100, FMath::FloorToInt(StopCm / 1000.) * 1000);
                if (Range <= 0) { UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE degenerate instance %d on %s"), I, *Mesh->GetName()); return; }
                ByRange.FindOrAdd(Range).Add(I);
            }
            for (const auto& Bucket : ByRange)
            {
                for (FTree* Source : {Pair.Near, Pair.Far})
                {
                    auto* Owner = Source->GetOwner();
                    auto* New = NewObject<FTree>(Owner, NAME_None, RF_Transient, Source);
                    New->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
                    New->SetRelativeTransform(Source->GetRelativeTransform());
                    GTLidarTreeInstances::CopySubset(*New, *Source, Bucket.Value, Seeds);
                    New->ComponentTags.Add(TEXT("LidarSizeRange"));
                    New->InstanceMinDrawDistance = Source == Pair.Near ? 0 : Bucket.Key;
                    New->SetCullDistances(Source == Pair.Near ? Bucket.Key : 0, Source == Pair.Near ? Bucket.Key : MAX_int32);
                    for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot) New->SetMaterial(Slot, Source->GetMaterial(Slot));
                    Owner->AddInstanceComponent(New);
                    Owner->AddOwnedComponent(New);
                    New->RegisterComponent();
                    if (!New->IsRegistered() || New->GetInstanceCount() != Bucket.Value.Num() || New->CastShadow)
                    {
                        UE_LOG(LogTemp, Error, TEXT("GT_SIZE_RANGE invalid registered group %s count=%d expected=%d casts=%d"),
                            *Mesh->GetName(), New->GetInstanceCount(), Bucket.Value.Num(), New->CastShadow);
                        return;
                    }
                }
                ++Buckets;
                Total += Bucket.Value.Num();
                UE_LOG(LogTemp, Display, TEXT("GT_SIZE_RANGE mesh=%s radius_cm=%d instances=%d"), *Mesh->GetName(), Bucket.Key, Bucket.Value.Num());
            }
            for (FTree* Source : {Pair.Near, Pair.Far})
            {
                Source->SetVisibility(false);
                Source->UnregisterComponent();
            }
        }
        UE_LOG(LogTemp, Display, TEXT("GT_SIZE_RANGE_READY species=3 instances=%d buckets=%d factor=%.6f"), Total, Buckets, Factor);
    }
    FAutoConsoleCommandWithWorldAndArgs SizeRanges(TEXT("gt.Lidar.SizeTreeRanges"),
        TEXT("Use each tree's original projected detail threshold in the current driving view."),
        FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(ApplySizeRanges));

    void MatchShadowRanges(const TArray<FString>& Args, UWorld* World)
    {
        FSceneViewProjectionData View;
        double Factor;
        if (!Args.IsEmpty() || !GetDrivingProjection(World, View, Factor)) return;
        using FTree = UInstancedStaticMeshComponent;
        struct FGroup
        {
            FTree* Caster = nullptr;
            FTree* Source = nullptr;
            FBox Bounds = FBox(ForceInit);
            double Threshold = 0.;
        };
        TMap<FString, FGroup> Groups;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            TInlineComponentArray<FTree*> Components(*It);
            for (FTree* C : Components)
            {
                if (!C->IsRegistered() || !C->GetStaticMesh()) continue;
                const FString Mesh = C->GetStaticMesh()->GetName();
                if (C->ComponentHasTag(TEXT("LidarFullNaniteShadow")) && C->CastShadow)
                {
                    auto& Group = Groups.FindOrAdd(Mesh.Right(1));
                    if (Group.Caster || !Mesh.StartsWith(TEXT("SM_NaniteRenderLod1_"))) return;
                    Group.Caster = C;
                }
                else if (C->ComponentHasTag(TEXT("LidarSizeRange")) && Mesh.StartsWith(TEXT("SM_Canopy_")))
                {
                    Groups.FindOrAdd(Mesh.Right(1)).Source = C;
                }
            }
        }
        if (Groups.Num() != 3) return;
        for (auto& Entry : Groups)
        {
            auto& Group = Entry.Value;
            if (!Group.Source || !Group.Caster || !Group.Source->GetSceneProxy() || Group.Caster->NumCustomDataFloats) return;
            const auto* Data = Group.Source->GetStaticMesh()->GetRenderData();
            if (!Data || Data->LODResources.Num() != 4 || Group.Source->MinLOD != 1) return;
            int32 FirstSilent = INDEX_NONE;
            for (int32 LOD = 1; LOD < Data->LODResources.Num(); ++LOD)
            {
                bool bCasts = false;
                for (const auto& Section : Data->LODResources[LOD].Sections)
                {
                    UE_LOG(LogTemp, Display, TEXT("GT_SOURCE_SHADOW_LOD mesh=%s lod=%d slot=%d casts=%d triangles=%u"),
                        *Group.Source->GetStaticMesh()->GetName(), LOD, Section.MaterialIndex, int32(Section.bCastShadow), Section.NumTriangles);
                    bCasts |= Section.NumTriangles > 0 && Section.bCastShadow;
                }
                if (bCasts && FirstSilent != INDEX_NONE) return;
                if (!bCasts && FirstSilent == INDEX_NONE) FirstSilent = LOD;
            }
            if (FirstSilent <= 1) return;
            Group.Threshold = FMath::FloorToDouble(Data->ScreenSize[FirstSilent].GetValue() * 1024.) / 1024.;
            if (Group.Threshold <= 0.) return;
            // Conventional shadow instance culling uses the padded local bounds in GPU Scene.
            const auto* Proxy = Group.Source->GetSceneProxy();
            ENQUEUE_RENDER_COMMAND(LidarReadShadowLodBounds)([Proxy, &Group](FRHICommandListImmediate&)
            {
                const auto* Buffer = Proxy->GetInstanceSceneDataBuffers();
                if (!Buffer || Buffer->GetNumInstances() == 0) return;
                const auto Bounds = Buffer->GetInstanceLocalBounds(0).ToBox();
                if (Buffer->GetFlags().bHasPerInstanceLocalBounds)
                    for (int32 I = 1; I < Buffer->GetNumInstances(); ++I)
                        if (!Buffer->GetInstanceLocalBounds(I).ToBox().Equals(Bounds, .01)) return;
                Group.Bounds = Bounds;
            });
            FlushRenderingCommands();
            if (!Group.Bounds.IsValid || Group.Bounds.GetExtent().IsNearlyZero()) return;
        }
        int32 Total = 0, Count = 0;
        for (auto& Entry : Groups)
        {
            auto& Group = Entry.Value;
            auto* Source = Group.Caster;
            TMap<int32, TArray<int32>> ByDistance;
            for (int32 I = 0; I < Source->GetInstanceCount(); ++I)
            {
                FTransform Instance;
                if (!Source->GetInstanceTransform(I, Instance, true)) return;
                const double Radius = (Group.Bounds.GetExtent() * Instance.GetScale3D()).Size();
                const int32 Stop = FMath::RoundToInt(Factor * Radius / (Group.Threshold * 500.)) * 500;
                if (Stop <= 0) return;
                ByDistance.FindOrAdd(Stop).Add(I);
            }
            const auto Seeds = GTLidarTreeInstances::RandomSeeds(*Source);
            auto* Owner = Source->GetOwner();
            for (const auto& Bucket : ByDistance)
            {
                auto* C = NewObject<FTree>(Owner, NAME_None, RF_Transient, Source);
                C->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
                C->SetRelativeTransform(Source->GetRelativeTransform());
                GTLidarTreeInstances::CopySubset(*C, *Source, Bucket.Value, Seeds);
                C->SetCullDistances(Bucket.Key, Bucket.Key);
                Owner->AddInstanceComponent(C);
                Owner->AddOwnedComponent(C);
                C->RegisterComponent();
                if (!C->IsRegistered() || !C->CastShadow || !C->bCastHiddenShadow || !C->bHiddenInGame ||
                    C->GetInstanceCount() != Bucket.Value.Num() || C->GetStaticMesh() != Source->GetStaticMesh()) return;
                Total += C->GetInstanceCount();
                ++Count;
                UE_LOG(LogTemp, Display, TEXT("GT_CAST_RANGE mesh=%s stop_cm=%d instances=%d"), *Entry.Key, Bucket.Key, C->GetInstanceCount());
            }
            Source->SetCastShadow(false);
            Source->UnregisterComponent();
        }
        UE_LOG(LogTemp, Display, TEXT("GT_MATCHED_SHADOW_RANGE species=%d groups=%d instances=%d factor=%.6f"), Groups.Num(), Count, Total, Factor);
    }
    FAutoConsoleCommandWithWorldAndArgs ShadowRanges(TEXT("gt.Lidar.MatchTreeShadowRanges"),
        TEXT("Match study shadow draw distances to each original tree's final shadow-casting detail level."),
        FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(MatchShadowRanges));
}
#endif
