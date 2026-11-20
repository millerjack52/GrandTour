#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/Material.h"
#include "Materials/MaterialRenderProxy.h"
#include "MaterialShared.h"
#include "NaniteSceneProxy.h"
#include "ShaderCompilerCore.h"
#include "PrimitiveSceneProxy.h"
#include "RenderingThread.h"
#include "StaticMeshResources.h"

#if WITH_EDITOR
#include "AssetCompilingManager.h"
namespace
{
	void AuditRenderPass(const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::Game ||
			UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy")) return;
		auto& Compilers = FAssetCompilingManager::Get();
		if (Args.Contains(TEXT("warm")))
		{
			Compilers.FinishAllCompilation();
			FlushRenderingCommands();
		}
		const auto* Velocity = IConsoleManager::Get().FindConsoleVariable(TEXT("r.VelocityOutputPass"));
		const auto* Mask = IConsoleManager::Get().FindConsoleVariable(TEXT("r.EarlyZPassOnlyMaterialMasking"));
		UE_LOG(LogTemp, Display, TEXT("GT_LIDAR_PASS velocity=%d pending_assets=%d early_mask=%d"),
			Velocity->GetInt(), Compilers.GetNumRemainingAssets(), Mask->GetInt());
	}
	FAutoConsoleCommandWithWorldAndArgs AuditPass(TEXT("gt.Lidar.AuditRenderPass"),
		TEXT("Read active rendering configuration and pending compilation during a LiDAR trial."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(AuditRenderPass));

	void AuditTreeRendering(const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::Game ||
			UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy")) return;
		struct FGroup
		{
			FString Mesh;
			UInstancedStaticMeshComponent* Component;
			FPrimitiveSceneProxy* SceneProxy;
			TArray<const FMaterialRenderProxy*> Materials;
			bool bValidNaniteData;
		};
		TArray<FGroup> Groups;
		TArray<FMaterial*> Resources;
		const bool bShadowAudit = Args.Contains(TEXT("shadow"));
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
			for (auto* Component : Components)
			{
				if (bShadowAudit)
				{
					if (!Component->IsRegistered() || !Component->CastShadow ||
						!(Component->ComponentHasTag(TEXT("LidarFullNaniteShadow")) ||
						  Component->ComponentHasTag(TEXT("LidarFastCrownShadow")))) continue;
				}
				else if (!Component->IsVisible() || (!Component->ComponentHasTag(TEXT("FloraWorldCanopy")) &&
					!Component->ComponentHasTag(TEXT("FloraWorldSaplings")))) continue;
				UStaticMesh* Mesh = Component->GetStaticMesh();
				if (!Mesh) continue;
				FGroup Group{Mesh->GetName(), Component, nullptr, {}, Mesh->HasValidNaniteData()};
				for (int32 Slot = 0; Slot < Component->GetNumMaterials(); ++Slot)
				{
					auto* Material = Component->GetMaterial(Slot);
					Group.Materials.Add(Material ? Material->GetRenderProxy() : nullptr);
					if (Material && Args.Contains(TEXT("warm")))
					{
						if (auto* Resource = Material->GetMaterialResource(GShaderPlatformForFeatureLevel[World->GetFeatureLevel()]))
						{
							Resource->SubmitCompileJobs_GameThread(EShaderCompileJobPriority::High);
							Resources.AddUnique(Resource);
						}
					}
				}
				Groups.Add(MoveTemp(Group));
			}
		}
		if (!Resources.IsEmpty())
		{
			FMaterial::FinishCompilation(TEXT("LiDAR painted canopies"), Resources);
			FlushRenderingCommands();
		}
		const auto Level = World->GetFeatureLevel();
		for (auto& Group : Groups)
		{
			Group.SceneProxy = Group.Component->GetSceneProxy();
		}
		ENQUEUE_RENDER_COMMAND(AuditLidarTreeRendering)(
			[Groups = MoveTemp(Groups), Level, bShadowAudit](FRHICommandListImmediate&)
			{
				int32 Nanite = 0, Fallbacks = 0, Proxies = 0;
				for (const auto& Group : Groups)
				{
					const bool bNanite = Group.SceneProxy && Group.SceneProxy->IsNaniteMesh();
					Nanite += bNanite;
					Proxies += Group.SceneProxy != nullptr;
					int32 GroupFallbacks = 0;
					int32 WindSlots = 0;
					for (const auto* Material : Group.Materials)
					{
						const FMaterialRenderProxy* Fallback = nullptr;
						if (Material)
						{
							WindSlots += Material->GetMaterialWithFallback(Level, Fallback).MaterialUsesWorldPositionOffset_RenderThread();
						}
						GroupFallbacks += !Material || Fallback != nullptr;
					}
					FVector2f Range;
					if (Group.SceneProxy && Group.SceneProxy->GetInstanceDrawDistanceMinMax(Range))
					{
						UE_LOG(LogTemp, Display, TEXT("GT_TREE_DRAW_RANGE mesh=%s min_cm=%.0f max_cm=%.0f wpo_slots=%d"),
							*Group.Mesh, Range.X, Range.Y, WindSlots);
					}
					Fallbacks += GroupFallbacks;
					if (bNanite)
					{
						const auto* Proxy = static_cast<const Nanite::FSceneProxyBase*>(Group.SceneProxy);
						for (const auto& Section : Proxy->GetMaterialSections())
						{
							const bool bMatches = Group.Materials.IsValidIndex(Section.MaterialIndex) &&
								Section.ShadingMaterialProxy == Group.Materials[Section.MaterialIndex];
							Fallbacks += !bMatches;
							UE_LOG(LogTemp, Display, TEXT("GT_TREE_RENDER_SECTION mesh=%s slot=%d bound_paint=%d"),
								*Group.Mesh, Section.MaterialIndex, bMatches);
						}
					}
					UE_LOG(LogTemp, Display, TEXT("GT_TREE_RENDER mesh=%s nanite_data=%d nanite_proxy=%d slots=%d material_fallbacks=%d"),
						*Group.Mesh, Group.bValidNaniteData, bNanite, Group.Materials.Num(), GroupFallbacks);
				}
				UE_LOG(LogTemp, Display, TEXT("%s groups=%d proxies=%d nanite=%d material_fallbacks=%d"),
					bShadowAudit ? TEXT("GT_TREE_SHADOW_SUMMARY") : TEXT("GT_TREE_RENDER_SUMMARY"), Groups.Num(), Proxies, Nanite, Fallbacks);
			});
		FlushRenderingCommands();
	}
	FAutoConsoleCommandWithWorldAndArgs AuditCanopyRendering(TEXT("gt.Lidar.AuditTreeRendering"),
		TEXT("Report the actual LiDAR tree scene proxies and any material shader fallbacks."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&AuditTreeRendering));

	void MatchStudyTreeBounds(UStaticMesh* Mesh, const UStaticMesh* Original)
	{
		// Near and far distance tests must use the same instance centre.
		const auto Far = Original->GetBounds();
		const auto Built = Mesh->GetBounds();
		const FVector Extent = Far.BoxExtent.ComponentMax(Built.BoxExtent + (Built.Origin - Far.Origin).GetAbs());
		Mesh->SetExtendedBounds(FBoxSphereBounds(Far.Origin, Extent, Extent.Size()));
		UE_LOG(LogTemp, Display, TEXT("GT_TREE_RANGE_BOUNDS mesh=%s centre_delta_cm=%.3f extent_delta_cm=%.3f"),
			*Mesh->GetName(), (Built.Origin - Far.Origin).Size(), (Extent - Far.BoxExtent).Size());
	}

	void TrialNearCanopy(const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::Game || Args.Num() < 2 || Args.Num() > 3 ||
			UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy")) return;
		FString ShapeFolder;
		if (Args.Num() == 3)
		{
			if ((Args[1] != TEXT("nanite_shadows_only") && Args[1] != TEXT("renderlod_nanite_shadows")) ||
				Args[2].Len() != 12) return;
			for (TCHAR Ch : Args[2])
			{
				if (!FChar::IsHexDigit(Ch)) return;
			}
			ShapeFolder = TEXT("ShadowShape/") + Args[2] + TEXT("/");
		}
		int32 Metres = 0;
		const bool bForceCasterLOD1 = Args[1] == TEXT("original_lod1_shadows_only");
		const bool bStaticCasterWind = Args[1] == TEXT("original_static_shadows_only");
		const bool bConventionalOnly = bForceCasterLOD1 || bStaticCasterWind || Args[1] == TEXT("original_shadows_only");
		const bool bOriginalShadows = bConventionalOnly || Args[1] == TEXT("renderlod_original_shadows");
		const bool bOriginalCameraTrees = bConventionalOnly || Args[1] == TEXT("nanite_shadows_only");
		const bool bNaniteShadows = Args[1] == TEXT("nanite_shadows_only") || Args[1] == TEXT("renderlod_nanite_shadows");
		const bool bFullRangeShadows = bOriginalShadows || bNaniteShadows;
		const bool bRenderLod = Args[1] == TEXT("renderlod") || bFullRangeShadows;
		if (!LexTryParseString(Metres, *Args[0]) || (bOriginalCameraTrees ? Metres != 0 : (Metres < 20 || Metres > 150)) ||
			(!bRenderLod && Args[1] != TEXT("paint") && Args[1] != TEXT("control"))) return;
		const int32 Radius = Metres * 100;
		const bool bPaint = !bConventionalOnly && (bRenderLod || Args[1] == TEXT("paint"));
		struct FSource { UInstancedStaticMeshComponent* Component; UStaticMesh* Near; UStaticMesh* Shadow; };
		TArray<FSource> Sources;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
			for (auto* C : Components)
			{
				if (!C->ComponentHasTag(TEXT("FloraWorldCanopy")) || !C->IsVisible()) continue;
				UStaticMesh* Original = C->GetStaticMesh();
				if (!Original || !Original->GetName().StartsWith(TEXT("SM_Canopy_")) ||
					C->InstanceMinDrawDistance || C->InstanceEndCullDistance || C->NumCustomDataFloats ||
					C->GetCollisionEnabled() != ECollisionEnabled::NoCollision || C->bVisibleInRayTracing || C->bAffectDistanceFieldLighting)
				{
					UE_LOG(LogTemp, Warning, TEXT("GT_TREE_RANGE incompatible component=%s min=%d end=%d"), *C->GetPathName(), C->InstanceMinDrawDistance, C->InstanceEndCullDistance);
					return;
				}
				if (bRenderLod && (!C->bOverrideMinLOD || C->MinLOD != 1)) return;
				if (bFullRangeShadows && !C->CastShadow) return;
				const FString Prefix = bRenderLod ? TEXT("SM_NaniteRenderLod1_") : TEXT("SM_NanitePainted_");
				const FString Folder = TEXT("/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/");
				const FString Asset = Prefix + Original->GetName().Right(1);
				const FString Path = Folder + Asset;
				UStaticMesh* Near = bPaint ? LoadObject<UStaticMesh>(nullptr, *Path) : Original;
				if (!Near || Near->GetStaticMaterials().Num() != C->GetNumMaterials())
				{
					UE_LOG(LogTemp, Warning, TEXT("GT_TREE_RANGE incompatible mesh=%s copy=%s"), *Original->GetName(), *GetNameSafe(Near));
					return;
				}
				UStaticMesh* Shadow = bNaniteShadows ? Near : Original;
				if (!ShapeFolder.IsEmpty())
				{
					Shadow = LoadObject<UStaticMesh>(nullptr, *(Folder + ShapeFolder + Asset));
					if (!Shadow || Shadow->GetNumSections(0) != Near->GetNumSections(0) ||
						Shadow->GetStaticMaterials().Num() != C->GetNumMaterials() ||
						Shadow->GetNaniteSettings().ShapePreservation != ENaniteShapePreservation::None) return;
					UE_LOG(LogTemp, Display, TEXT("GT_UNDILATED_SHADOW mesh=%s"), *Shadow->GetPathName());
				}
				Sources.Add({C, Near, Shadow});
			}
		}
		if (Sources.Num() != 3) return;
		int32 Total = 0;
		for (const auto& Entry : Sources)
		{
			auto* Source = Entry.Component;
			auto* Owner = Source->GetOwner();
			if (bPaint)
			{
				MatchStudyTreeBounds(Entry.Near, Source->GetStaticMesh());
				if (bNaniteShadows && Entry.Shadow != Entry.Near)
				{
					MatchStudyTreeBounds(Entry.Shadow, Source->GetStaticMesh());
				}
			}
			if (bFullRangeShadows)
			{
				// The camera's near/far transition must not change which trees
				// populate a cached shadow page. Preserve the full original caster.
				auto* Shadow = NewObject<UInstancedStaticMeshComponent>(Owner, NAME_None, RF_Transient, Source);
				Shadow->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
				Shadow->SetRelativeTransform(Source->GetRelativeTransform());
				Shadow->PerInstanceSMData = Source->PerInstanceSMData;
				Shadow->InstancingRandomSeed = Source->InstancingRandomSeed;
				Shadow->AdditionalRandomSeeds = Source->AdditionalRandomSeeds;
				UStaticMesh* ShadowMesh = Entry.Shadow;
				if (bForceCasterLOD1)
				{
					// The conventional renderer's override is one-based.
					Shadow->SetForcedLodModel(2);
				}
				if (bNaniteShadows && !Shadow->SetStaticMesh(ShadowMesh)) return;
				if (bNaniteShadows || bStaticCasterWind)
				{
					// Isolate shadow wind. The live LiDAR leaves can move within 55 m.
					Shadow->SetEvaluateWorldPositionOffset(false);
				}
				for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot)
					Shadow->SetMaterial(Slot, bNaniteShadows ? ShadowMesh->GetMaterial(Slot) : Source->GetMaterial(Slot));
				Shadow->ComponentTags.Reset();
				Shadow->ComponentTags.Add(bNaniteShadows ? TEXT("LidarFullNaniteShadow") : TEXT("LidarOriginalCanopyShadow"));
				Shadow->SetCastHiddenShadow(true);
				Shadow->SetHiddenInGame(true);
				Shadow->SetRenderInMainPass(false);
				Shadow->SetRenderInDepthPass(false);
				Owner->AddInstanceComponent(Shadow);
				Owner->AddOwnedComponent(Shadow);
				Shadow->RegisterComponent();
				if (!Shadow->IsRegistered() || Shadow->GetStaticMesh() != ShadowMesh ||
					Shadow->GetInstanceCount() != Source->GetInstanceCount()) return;
				Source->SetCastShadow(false);
				if (bConventionalOnly)
				{
					const auto* Proxy = Shadow->GetSceneProxy();
					if (!Proxy) return;
					const FString Name = ShadowMesh->GetName();
					ENQUEUE_RENDER_COMMAND(LidarAuditConventionalCaster)([Proxy, Name](FRHICommandListImmediate&)
					{
						UE_LOG(LogTemp, Display, TEXT("GT_CONVENTIONAL_CASTER mesh=%s nanite=%d evaluate_wpo=%d always_wpo=%d"),
							*Name, Proxy->IsNaniteMesh(), Proxy->EvaluateWorldPositionOffset(), Proxy->AnyMaterialAlwaysEvaluatesWorldPositionOffset());
					});
					FlushRenderingCommands();
				}
				if (bForceCasterLOD1)
				{
					UE_LOG(LogTemp, Display, TEXT("GT_CONVENTIONAL_SHADOW_LOD mesh=%s forced_model=%d instances=%d"),
						*ShadowMesh->GetName(), Shadow->GetForcedLodModel(), Shadow->GetInstanceCount());
				}
				UE_LOG(LogTemp, Display, TEXT("%s mesh=%s instances=%d"),
					bNaniteShadows ? TEXT("GT_FULL_NANITE_SHADOW") : TEXT("GT_ORIGINAL_CANOPY_SHADOW"),
					*Source->GetStaticMesh()->GetName(), Shadow->GetInstanceCount());
			}
			if (bOriginalCameraTrees)
			{
				UE_LOG(LogTemp, Display, TEXT("GT_CAMERA_TREE_UNCHANGED mesh=%s instances=%d min=%d max=%d"),
					*Source->GetStaticMesh()->GetName(), Source->GetInstanceCount(), Source->InstanceMinDrawDistance, Source->InstanceEndCullDistance);
				Total += Source->GetInstanceCount();
				continue;
			}
			auto* Near = NewObject<UInstancedStaticMeshComponent>(Owner, NAME_None, RF_Transient, Source);
			Near->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
			Near->SetRelativeTransform(Source->GetRelativeTransform());
			Near->PerInstanceSMData = Source->PerInstanceSMData;
			Near->InstancingRandomSeed = Source->InstancingRandomSeed;
			Near->AdditionalRandomSeeds = Source->AdditionalRandomSeeds;
			Near->SetStaticMesh(Entry.Near);
			if (bFullRangeShadows) Near->SetCastShadow(false);
			for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot)
			{
				Near->SetMaterial(Slot, bPaint ? Entry.Near->GetMaterial(Slot) : Source->GetMaterial(Slot));
			}
			Near->SetCullDistances(Radius, Radius);
			Near->ComponentTags = Source->ComponentTags;
			Near->ComponentTags.Add(TEXT("TrialNearCanopy"));
			Near->SetVisibility(Source->IsVisible());
			Owner->AddInstanceComponent(Near);
			Owner->AddOwnedComponent(Near);
			Near->RegisterComponent();
			UE_LOG(LogTemp, Display, TEXT("GT_TREE_RANGE_NEAR component=%s mesh=%s owner_visible=%d tagged=%d registered=%d instances=%d"),
				*Near->GetPathName(), *GetNameSafe(Near->GetStaticMesh()), Near->IsVisible(), Near->ComponentHasTag(TEXT("FloraWorldCanopy")), Near->IsRegistered(), Near->GetInstanceCount());
			Source->InstanceMinDrawDistance = Radius;
			// Unreal ignores the minimum entirely when the maximum is zero.
			// This limit is over 21,000 km away, outside the surveyed landscape.
			Source->SetCullDistances(0, MAX_int32);
			Source->MarkRenderStateDirty();
			Total += Source->GetInstanceCount();
		}
		UE_LOG(LogTemp, Display, TEXT("GT_TREE_RANGE groups=%d instances=%d radius_cm=%d painted=%d"),
			Sources.Num(), Total, Radius, bPaint);
	}
	FAutoConsoleCommandWithWorldAndArgs NearCanopy(TEXT("gt.Lidar.NearTreeStudy"),
		TEXT("Test paired near/far draw distances on the mature LiDAR tree instances."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(TrialNearCanopy));

	struct FTreeSections
	{
		UStaticMesh* Rigid = nullptr;
		UStaticMesh* Leaves = nullptr;
		int32 LeafSlot = INDEX_NONE;
	};

	void AuditVertexReuse(const UStaticMesh* Mesh)
	{
		const auto* Data = Mesh->GetRenderData();
		for (int32 Index = 1; Index <= 2; ++Index)
		{
			const auto& Lod = Data->LODResources[Index];
			const auto& Vertex = Lod.VertexBuffers.StaticMeshVertexBuffer;
			const auto& Color = Lod.VertexBuffers.ColorVertexBuffer;
			const int32 TangentBytes = Vertex.GetUseHighPrecisionTangentBasis() ? 16 : 8;
			const int32 UVBytes = Vertex.GetNumTexCoords() * (Vertex.GetUseFullPrecisionUVs() ? 8 : 4);
			const auto* Tangents = static_cast<const uint8*>(Vertex.GetTangentData());
			const auto* UVs = static_cast<const uint8*>(Vertex.GetTexCoordData());
			if (!Tangents || !UVs || !Lod.VertexBuffers.PositionVertexBuffer.GetVertexData())
			{
				UE_LOG(LogTemp, Warning, TEXT("GT_TREE_VERTICES CPU vertex data unavailable"));
				continue;
			}
			for (const auto& Section : Lod.Sections)
			{
				TArray<uint32> Indices;
				Lod.IndexBuffer.GetCopy(Indices);
				TSet<uint32> Seen;
				TSet<FString> Exact;
				for (uint32 i = Section.FirstIndex; i < Section.FirstIndex + Section.NumTriangles * 3; ++i)
				{
					if (!Indices.IsValidIndex(i))
					{
						UE_LOG(LogTemp, Warning, TEXT("GT_TREE_VERTICES CPU index data unavailable"));
						return;
					}
					const uint32 Id = Indices[i];
					if (Seen.Contains(Id))
					{
						continue;
					}
					Seen.Add(Id);
					const FVector3f& P = Lod.VertexBuffers.PositionVertexBuffer.VertexPosition(Id);
					FString Key = BytesToHex(reinterpret_cast<const uint8*>(&P), sizeof(P));
					Key += BytesToHex(Tangents + Id * TangentBytes, TangentBytes);
					Key += BytesToHex(UVs + Id * UVBytes, UVBytes);
					if (Color.GetNumVertices())
					{
						const FColor C = Color.VertexColor(Id);
						Key += BytesToHex(reinterpret_cast<const uint8*>(&C), sizeof(C));
					}
					Exact.Add(MoveTemp(Key));
				}
				UE_LOG(LogTemp, Display, TEXT("GT_TREE_VERTICES mesh=%s lod=%d material=%d referenced=%d exact=%d uv_channels=%d"),
					*Mesh->GetName(), Index, Section.MaterialIndex, Seen.Num(), Exact.Num(), Vertex.GetNumTexCoords());
			}
		}
	}

	// Each disposable asset has a separate render resource. Only change the
	// section draw ranges in memory, before any component has referenced it.
	// Both copies keep every original vertex, UV, tangent, LOD threshold and bound.
	bool SetSectionRanges(UStaticMesh* Source, const FTreeSections& Pair)
	{
		const FStaticMeshRenderData* Original = Source->GetRenderData();
		auto* Rigid = Pair.Rigid->GetRenderData();
		auto* Leaves = Pair.Leaves->GetRenderData();
		if (!Original || !Rigid || !Leaves || Rigid == Leaves || Rigid == Original || Leaves == Original ||
			Original->LODResources.Num() != 4 || Rigid->LODResources.Num() != 4 || Leaves->LODResources.Num() != 4)
		{
			return false;
		}
		for (int32 Index = 0; Index < Original->LODResources.Num(); ++Index)
		{
			const auto& Stock = Original->LODResources[Index];
			auto& A = Rigid->LODResources[Index];
			auto& B = Leaves->LODResources[Index];
			if (A.Sections.Num() != Stock.Sections.Num() || B.Sections.Num() != Stock.Sections.Num() ||
				A.GetNumVertices() != Stock.GetNumVertices() || B.GetNumVertices() != Stock.GetNumVertices())
			{
				return false;
			}
			// The unified shadow/depth buffer also contains the omitted sections.
			A.bHasDepthOnlyIndices = false;
			B.bHasDepthOnlyIndices = false;
			for (int32 Section = 0; Section < Stock.Sections.Num(); ++Section)
			{
				const auto& S = Stock.Sections[Section];
				auto& R = A.Sections[Section];
				auto& L = B.Sections[Section];
				if (S.MaterialIndex != R.MaterialIndex || S.MaterialIndex != L.MaterialIndex ||
					S.FirstIndex != R.FirstIndex || S.FirstIndex != L.FirstIndex ||
					S.NumTriangles != R.NumTriangles || S.NumTriangles != L.NumTriangles)
				{
					return false;
				}
				(S.MaterialIndex == Pair.LeafSlot ? R : L).NumTriangles = 0;
			}
		}
		return true;
	}

	bool ShareShadowVertices(UStaticMesh* Mesh, int32 LeafSlot)
	{
		// Shadow coverage samples UV0. The audited wind shader reads world
		// position, camera, time and amplitude. No painted colour atlas, tangent
		// or normal feeds either output. The original colour mesh stays intact.
		auto* Data = Mesh->GetRenderData();
		if (!Data || Data->LODResources.Num() != 4)
		{
			return false;
		}
		for (int32 Index = 0; Index < 3; ++Index)
		{
			auto& Lod = Data->LODResources[Index];
			auto& Buffer = Lod.IndexBuffer;
			TArray<uint32> Indices;
			Buffer.GetCopy(Indices);
			if (Indices.Num() != Buffer.GetNumIndices() || !Lod.VertexBuffers.PositionVertexBuffer.GetVertexData() ||
				!Lod.VertexBuffers.StaticMeshVertexBuffer.GetTexCoordData())
			{
				return false;
			}
			for (const auto& Section : Lod.Sections)
			{
				if (Section.MaterialIndex != LeafSlot)
				{
					continue;
				}
				TMap<FString, uint32> Representatives;
				TMap<uint32, uint32> Remap;
				for (uint32 i = Section.FirstIndex; i < Section.FirstIndex + Section.NumTriangles * 3; ++i)
				{
					const uint32 Id = Indices[i];
					if (const uint32* Cached = Remap.Find(Id))
					{
						Indices[i] = *Cached;
						continue;
					}
					const auto& P = Lod.VertexBuffers.PositionVertexBuffer.VertexPosition(Id);
					const auto UV = Lod.VertexBuffers.StaticMeshVertexBuffer.GetVertexUV(Id, 0);
					const FString Key = BytesToHex(reinterpret_cast<const uint8*>(&P), sizeof(P)) +
						BytesToHex(reinterpret_cast<const uint8*>(&UV), sizeof(UV));
					Indices[i] = Representatives.FindOrAdd(Key, Id);
					Remap.Add(Id, Indices[i]);
				}
				UE_LOG(LogTemp, Display, TEXT("GT_TREE_SHADOW_INDEX mesh=%s lod=%d before=%d after=%d triangles=%d"),
					*Mesh->GetName(), Index, Remap.Num(), Representatives.Num(), Section.NumTriangles);
			}
			BeginReleaseResource(&Buffer);
			FlushRenderingCommands();
			Buffer.SetIndices(Indices, EIndexBufferStride::AutoDetect);
			BeginInitResource(&Buffer);
		}
		FlushRenderingCommands();
		return true;
	}

	void TrialTreeSections(const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::Game || !FParse::Param(FCommandLine::Get(), TEXT("game")) ||
			UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy"))
		{
			return;
		}
		const bool bShadowOnly = Args.Num() == 1 && (Args[0] == TEXT("shadow") || Args[0] == TEXT("shadow_control"));
		if (!Args.IsEmpty() && !bShadowOnly)
		{
			return;
		}
		TArray<UInstancedStaticMeshComponent*> Trees;
		TMap<UStaticMesh*, FTreeSections> Pairs;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
			for (auto* C : Components)
			{
				if (C->ComponentHasTag(TEXT("LidarTreeSectionTrial")))
				{
					return;
				}
				if ((!C->ComponentHasTag(TEXT("FloraWorldCanopy")) && !C->ComponentHasTag(TEXT("FloraWorldSaplings"))) || !C->IsVisible())
				{
					continue;
				}
				UStaticMesh* Original = C->GetStaticMesh();
				if (!Original || C->GetCollisionEnabled() != ECollisionEnabled::NoCollision || C->bVisibleInRayTracing || C->bAffectDistanceFieldLighting)
				{
					UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS unexpected source %s"), *C->GetPathName());
					return;
				}
				FTreeSections& Pair = Pairs.FindOrAdd(Original);
				int32 LeafSlot = INDEX_NONE;
				for (int32 Slot = 0; Slot < C->GetNumMaterials(); ++Slot)
				{
					auto* Material = C->GetMaterial(Slot);
					if (Material && Material->GetName().StartsWith(TEXT("MI_Path_Leaf_")))
					{
						LeafSlot = Slot;
					}
				}
				if (LeafSlot == INDEX_NONE || (Pair.LeafSlot != INDEX_NONE && Pair.LeafSlot != LeafSlot))
				{
					UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS unknown leaf slot"));
					return;
				}
				Pair.LeafSlot = LeafSlot;
				Trees.Add(C);
			}
		}
		if (Trees.Num() != 6 || Pairs.Num() != 3)
		{
			UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS unexpected group counts"));
			return;
		}
		for (auto& Item : Pairs)
		{
			const FString Suffix = Item.Key->GetName().Right(1);
			const FString Base = TEXT("/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/SM_Section");
			auto& Pair = Item.Value;
			Pair.Rigid = LoadObject<UStaticMesh>(nullptr, *(Base + TEXT("Rigid_") + Suffix));
			Pair.Leaves = LoadObject<UStaticMesh>(nullptr, *(Base + TEXT("Leaves_") + Suffix));
			if (!Pair.Rigid || !Pair.Leaves || Pair.Rigid->bSupportRayTracing || Pair.Leaves->bSupportRayTracing)
			{
				UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS missing study copies"));
				return;
			}
		}
		FlushRenderingCommands();
		for (const auto& Item : Pairs)
		{
			AuditVertexReuse(Item.Key);
			if ((!bShadowOnly && !SetSectionRanges(Item.Key, Item.Value)) ||
				(bShadowOnly && Args[0] == TEXT("shadow") && !ShareShadowVertices(Item.Value.Leaves, Item.Value.LeafSlot)))
			{
				UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS source and scratch render resources differ"));
				return;
			}
		}
		int32 Total = 0;
		for (auto* Source : Trees)
		{
			const auto& Pair = Pairs.FindChecked(Source->GetStaticMesh());
			AActor* Owner = Source->GetOwner();
			for (auto* Part : {Pair.Rigid, Pair.Leaves})
			{
				if (bShadowOnly && Part == Pair.Rigid)
				{
					continue;
				}
				auto* C = NewObject<UInstancedStaticMeshComponent>(Owner, NAME_None, RF_Transient, Source);
				C->SetupAttachment(Source->GetAttachParent(), Source->GetAttachSocketName());
				C->SetRelativeTransform(Source->GetRelativeTransform());
				C->ComponentTags.Add(TEXT("LidarTreeSectionTrial"));
				// Instance transforms use custom bulk serialization in this component.
				// Explicitly retain the authored matrices regardless of template-copy rules.
				C->PerInstanceSMData = Source->PerInstanceSMData;
				C->InstancingRandomSeed = Source->InstancingRandomSeed;
				C->AdditionalRandomSeeds = Source->AdditionalRandomSeeds;
				if (!C->SetStaticMesh(Part))
				{
					UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS could not assign the scratch mesh"));
					return;
				}
				for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot)
				{
					C->SetMaterial(Slot, Source->GetMaterial(Slot));
				}
				if (bShadowOnly)
				{
					C->SetCastHiddenShadow(true);
					C->SetHiddenInGame(true);
					C->SetRenderInMainPass(false);
					C->SetRenderInDepthPass(false);
				}
				else if (Part == Pair.Rigid)
				{
					C->SetMaterial(Pair.LeafSlot, UMaterial::GetDefaultMaterial(MD_Surface));
					C->SetEvaluateWorldPositionOffset(false);
				}
				Owner->AddInstanceComponent(C);
				C->RegisterComponent();
				if (C->GetInstanceCount() != Source->GetInstanceCount())
				{
					UE_LOG(LogTemp, Error, TEXT("GT_TREE_SECTIONS instance count changed"));
					return;
				}
			}
			if (bShadowOnly)
			{
				Source->SetCastShadow(false);
			}
			else
			{
				Source->SetVisibility(false);
			}
			Total += Source->GetInstanceCount();
		}
		UE_LOG(LogTemp, Display, TEXT("GT_TREE_SECTIONS_READY groups=%d trees=%d parts=%d"), Trees.Num(), Total, bShadowOnly ? 6 : 12);
	}

	FAutoConsoleCommandWithWorldAndArgs SectionStudy(
		TEXT("gt.Lidar.TrialTreeSections"), TEXT("Separate rigid tree sections from wind-driven leaves in a disposable LiDAR driving test."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(TrialTreeSections));
}
#endif
