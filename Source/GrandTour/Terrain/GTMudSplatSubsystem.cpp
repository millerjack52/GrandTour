#include "Terrain/GTMudSplatSubsystem.h"

#include "Terrain/GTTrackPaintSubsystem.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTWaterSheet.h"
#include "CollisionQueryParams.h"
#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/HitResult.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "MaterialShared.h"
#include "Math/RandomStream.h"
#include "SceneInterface.h"
#include "ShaderCore.h"

namespace
{
	const FName ParamSpawnTime(TEXT("SpawnTime"));
	const FName ParamTile(TEXT("Tile"));
	const FName ParamSizeCm(TEXT("SizeCm"));
	constexpr float BlotWindow = 0.88f;   // GTMudBlots::Window: a blot reaches this share of its square's half side
	constexpr int32 BlotTiles = 16;
}

bool UGTMudSplatSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGTMudSplatSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Collection.InitializeDependency<UGTTrackPaintSubsystem>();
	// Loaded now so an editor run queues its shaders before the first splat needs them.
	DecalMaterial = LoadObject<UMaterialInterface>(nullptr, *DecalMaterialPath);
	bMaterialLooked = true;
	// MR2 housekeeping 3: its shaders asked for now (in the editor they compile only when asked for), so the first splat finds them.
	IsDecalMaterialReady();
	if (!DecalMaterial)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTMudSplatSubsystem: %s missing (run Art/setup_mud_carry.ps1); thrown mud splats the landscape only"), *DecalMaterialPath);
	}
}

void UGTMudSplatSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	// MR2 housekeeping 3: decals placed before the material's shaders were ready show now (their own spawn times kept). Until
	// they are ready this asks for them every tick (the engine submits the jobs once).
	if (!bDecalReady && DecalMaterial)
	{
		IsDecalMaterialReady();
	}
	if (GetPendingDecalCount() > 0 && IsDecalMaterialReady())
	{
		for (int32 Index = 0; Index < Decals.Num(); ++Index)
		{
			if (DecalState[Index] == 1 && Decals[Index])
			{
				DecalState[Index] = 2;
				Decals[Index]->SetVisibility(true);
				Decals[Index]->MarkRenderStateDirty();
			}
		}
	}
	ExpireTimer += DeltaTime;
	if (ExpireTimer < 2.f || Decals.Num() == 0)
	{
		return;
	}
	ExpireTimer = 0.f;
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	for (int32 Index = 0; Index < Decals.Num(); ++Index)
	{
		UDecalComponent* Decal = Decals[Index];
		if (Decal && DecalState[Index] != 0 && Now - DecalBorn[Index] > DecalLifeSeconds)
		{
			Decal->SetVisibility(false);
			DecalState[Index] = 0;
		}
	}
}

bool UGTMudSplatSubsystem::IsDecalMaterialReady()
{
	// The renderer draws a decal whose material has no compiled shaders with the engine's fallback decal material
	// (DecalRenderingShared.cpp, TryGetDeferredDecalMaterial walks GetFallback): an unlit, opaque box.
	if (bDecalReady)
	{
		return true;
	}
	UWorld* World = GetWorld();
	if (!DecalMaterial || !World || !World->Scene)
	{
		return false;
	}
	FMaterialResource* Resource = DecalMaterial->GetMaterialResource(World->Scene->GetShaderPlatform());
	bDecalReady = Resource && Resource->IsCompilationFinished() && Resource->IsGameThreadShaderMapComplete() && Resource->GetCompileErrors().Num() == 0;
#if WITH_EDITOR
	// The editor submits a material's shader jobs when a primitive first draws with it; a decal held hidden never draws, so its
	// jobs are asked for here (once per priority: the engine skips a repeat).
	if (!bDecalReady && Resource)
	{
		Resource->SubmitCompileJobs_GameThread(EShaderCompileJobPriority::High);
	}
#endif
	return bDecalReady;
}

int32 UGTMudSplatSubsystem::GetPendingDecalCount() const
{
	int32 Pending = 0;
	for (const uint8 State : DecalState)
	{
		Pending += State == 1 ? 1 : 0;
	}
	return Pending;
}

bool UGTMudSplatSubsystem::LandscapeHeightAt(const FVector& Point, float& OutZ)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	const double Now = World->GetTimeSeconds();
	if (!bLandscapesLooked || (Landscapes.Num() == 0 && Now - LandscapesLookedAt > 2.0))
	{
		// Every proxy of one landscape answers for all of it (ULandscapeInfo's collision map), so one per landscape would do;
		// the few the levels have are kept.
		Landscapes.Reset();
		for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
		{
			Landscapes.Add(*It);
		}
		bLandscapesLooked = true;
		LandscapesLookedAt = Now;
	}
	for (const TWeakObjectPtr<ALandscapeProxy>& Entry : Landscapes)
	{
		if (const ALandscapeProxy* Landscape = Entry.Get())
		{
			const TOptional<float> Height = Landscape->GetHeightAtLocation(Point);
			if (Height.IsSet())
			{
				OutZ = Height.GetValue();
				return true;
			}
		}
	}
	return false;
}

bool UGTMudSplatSubsystem::SplatGround(const FVector& Point, float BlobRadiusCm, int32 Seed)
{
	if (!UGTTrackPaintSubsystem::IsSplatsEnabled() || BlobRadiusCm <= 0.f)
	{
		return false;
	}
	UGTTrackPaintSubsystem* Paint = GetWorld() ? GetWorld()->GetSubsystem<UGTTrackPaintSubsystem>() : nullptr;
	if (!Paint)
	{
		return false;
	}
	FRandomStream Random(Seed);
	const float Reach = BlobRadiusCm * Random.FRandRange(SplatRadiusMin, SplatRadiusMax);
	Paint->AddSplat(Point, Reach, static_cast<int32>(Random.GetUnsignedInt() & 0x7fffffff));
	++LandscapeSplats;
	++HeightSplats;
	return true;
}

bool UGTMudSplatSubsystem::ReserveTrace()
{
	if (GFrameCounter != TraceFrame)
	{
		TraceFrame = GFrameCounter;
		TracesThisFrame = 0;
	}
	if (TracesThisFrame >= MaxTracesPerFrame)
	{
		++CappedTraces;
		return false;
	}
	++TracesThisFrame;
	++TraceCount;
	return true;
}

int32 UGTMudSplatSubsystem::GetLiveDecalCount() const
{
	int32 Live = 0;
	for (const uint8 State : DecalState)
	{
		Live += State != 0 ? 1 : 0;
	}
	return Live;
}

TArray<FString> UGTMudSplatSubsystem::DescribeDecals() const
{
	TArray<FString> Out;
	for (int32 Index = 0; Index < Decals.Num(); ++Index)
	{
		if (Decals[Index] && DecalState[Index] != 0)
		{
			Out.Add(DecalState[Index] == 1 ? DecalOn[Index] + TEXT(" (waiting for its shaders)") : DecalOn[Index]);
		}
	}
	return Out;
}

UDecalComponent* UGTMudSplatSubsystem::TakeDecal(int32& OutIndex)
{
	UWorld* World = GetWorld();
	if (!World || !DecalMaterial)
	{
		return nullptr;
	}
	// A free one (its life ran out), else a new one under the cap, else the oldest.
	for (int32 Index = 0; Index < Decals.Num(); ++Index)
	{
		if (Decals[Index] && DecalState[Index] == 0)
		{
			OutIndex = Index;
			return Decals[Index];
		}
	}
	if (Decals.Num() < FMath::Max(1, MaxDecals))
	{
		if (!PoolActor)
		{
			FActorSpawnParameters Params;
			Params.ObjectFlags |= RF_Transient;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			PoolActor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
			if (!PoolActor)
			{
				return nullptr;
			}
			USceneComponent* Root = NewObject<USceneComponent>(PoolActor, TEXT("MudSplatRoot"));
			PoolActor->SetRootComponent(Root);
			Root->RegisterComponent();
		}
		UDecalComponent* Decal = NewObject<UDecalComponent>(PoolActor);
		Decal->SetFadeScreenSize(0.001f);
		Decal->SetVisibility(false);
		Decal->RegisterComponent();
		UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(DecalMaterial, PoolActor);
		Decal->SetDecalMaterial(Instance);
		OutIndex = Decals.Add(Decal);
		DecalMaterials.Add(Instance);
		DecalBorn.Add(0.0);
		DecalOn.Add(FString());
		DecalState.Add(0);
		return Decal;
	}
	int32 Oldest = 0;
	for (int32 Index = 1; Index < Decals.Num(); ++Index)
	{
		if (DecalBorn[Index] < DecalBorn[Oldest])
		{
			Oldest = Index;
		}
	}
	OutIndex = Oldest;
	return Decals[Oldest];
}

bool UGTMudSplatSubsystem::TraceSplat(FVector Start, FVector End, float BlobRadiusCm, int32 Seed)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTMudSplatSynthetic), false);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	if (!World->LineTraceSingleByObjectType(Hit, Start, End, Objects, Params))
	{
		return false;
	}
	const bool bMade = Splat(Hit, BlobRadiusCm, Seed, false);
	SyntheticSplats += bMade ? 1 : 0;
	return bMade;
}

bool UGTMudSplatSubsystem::Splat(const FHitResult& Hit, float BlobRadiusCm, int32 Seed, bool bMeshesOnly)
{
	if (!UGTTrackPaintSubsystem::IsSplatsEnabled() || BlobRadiusCm <= 0.f)
	{
		return false;
	}
	UWorld* World = GetWorld();
	AActor* Actor = Hit.GetActor();
	UPrimitiveComponent* Component = Hit.GetComponent();
	FRandomStream Random(Seed);
	const float Reach = BlobRadiusCm * Random.FRandRange(SplatRadiusMin, SplatRadiusMax);
	if (Actor && (Actor->IsA<AGTMudPatch>() || (bMeshesOnly && Actor->IsA<ALandscapeProxy>())))
	{
		return false;   // a patch's own mesh and clods, or the ground inside a box: the field takes the blob as before
	}
	if (Actor && Actor->IsA<ALandscapeProxy>())
	{
		if (UGTTrackPaintSubsystem* Paint = World ? World->GetSubsystem<UGTTrackPaintSubsystem>() : nullptr)
		{
			Paint->AddSplat(Hit.ImpactPoint, Reach, static_cast<int32>(Random.GetUnsignedInt() & 0x7fffffff));
			++LandscapeSplats;
			return true;
		}
		return false;
	}
	UStaticMeshComponent* Mesh = Cast<UStaticMeshComponent>(Component);
	if (!Mesh || !World || Cast<APawn>(Actor) || (Actor && Actor->IsA<AGTWaterSheet>()) || Mesh->IsSimulatingPhysics())
	{
		++IgnoredHits;
		return false;
	}
	int32 Index = INDEX_NONE;
	UDecalComponent* Decal = TakeDecal(Index);
	if (!Decal)
	{
		++IgnoredHits;
		return false;
	}
	// Projected into the surface along -normal, turned about it at random; the tile's square spans the decal's Y and Z.
	const float Half = Reach / BlotWindow;
	const FVector Normal = Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
	const FQuat Facing = FRotationMatrix::MakeFromX(-Normal).ToQuat() * FQuat(FVector::XAxisVector, Random.FRandRange(0.f, UE_TWO_PI));
	Decal->DecalSize = FVector(FMath::Max(2.f, Reach * DecalDepthScale), Half, Half);
	Decal->SetWorldLocationAndRotation(Hit.ImpactPoint, Facing);
	const double Now = World->GetTimeSeconds();
	if (UMaterialInstanceDynamic* Instance = DecalMaterials[Index])
	{
		Instance->SetScalarParameterValue(ParamSpawnTime, static_cast<float>(Now));
		Instance->SetScalarParameterValue(ParamTile, static_cast<float>(Random.RandRange(0, BlotTiles - 1)));
		Instance->SetScalarParameterValue(ParamSizeCm, 2.f * Half);
	}
	// MR2 housekeeping 3: shown only once the material's shaders are compiled (else the engine's fallback draws a black box).
	if (IsDecalMaterialReady())
	{
		DecalState[Index] = 2;
		Decal->SetVisibility(true);
	}
	else
	{
		DecalState[Index] = 1;
		Decal->SetVisibility(false);
		++HeldDecals;
	}
	Decal->MarkRenderStateDirty();
	DecalBorn[Index] = Now;
	DecalOn[Index] = Actor ? Actor->GetActorNameOrLabel() : (Component ? Component->GetName() : FString(TEXT("?")));
	++DecalSplats;
	return true;
}
