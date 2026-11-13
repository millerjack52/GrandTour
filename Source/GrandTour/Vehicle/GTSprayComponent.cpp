#include "Vehicle/GTSprayComponent.h"
#include "Terrain/GTMudRunnerWheelEffects.h"
#include "Vehicle/GTMudFlickLab.h"

#include "Core/GTGameplayTags.h"
#include "Vehicle/GTBodyStateComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTHullComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTMudSplatSubsystem.h"
#include "Terrain/GTTrackPaintSubsystem.h"
#include "CollisionQueryParams.h"
#include "Engine/HitResult.h"
#include "Engine/World.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
	constexpr int32 KindCount = static_cast<int32>(EGTSprayKind::Count);
	TAutoConsoleVariable<int32> CVarSpraySparseUpdates(TEXT("gt.Spray.SparseUpdates"), 1,
		TEXT("Submit live spray transforms plus newly retired slots only. 0 restores full-pool uploads; simulation and emission are unchanged."), ECVF_Default);
	const FName SprayParamBaseColor(TEXT("BaseColor"));
	const FName SprayParamRoughness(TEXT("Roughness"));
	const FName ParamOpacity(TEXT("Opacity"));

	struct FKindLook
	{
		const TCHAR* Material;
		FLinearColor Colour;
		float Opacity;
		float Roughness;
	};

	const FKindLook Looks[KindCount] = {
		{TEXT("/Game/GrandTour/Materials/M_GT_Prop.M_GT_Prop"), FLinearColor(0.25f, 0.18f, 0.11f), 1.f, 0.9f},    // mud: opaque blobs
		{TEXT("/Game/GrandTour/Materials/M_GT_Glass.M_GT_Glass"), FLinearColor(0.60f, 0.50f, 0.35f), 0.35f, 1.f},  // dust: translucent puffs
		{TEXT("/Game/GrandTour/Materials/M_GT_Glass.M_GT_Glass"), FLinearColor(0.95f, 0.96f, 1.00f), 0.7f, 0.8f},  // snow
		{TEXT("/Game/GrandTour/Materials/M_GT_Glass.M_GT_Glass"), FLinearColor(0.85f, 0.85f, 0.88f), 0.35f, 1.f},  // steam
		// Water stage W4: the thrown water. The existing droplet (the translucent glass sphere) with a water colour
		// on its own emitter's BaseColor - pale and cold against the mud's brown, and glossy, because a droplet of
		// river water is a lens and not a clod.
		{TEXT("/Game/GrandTour/Materials/M_GT_WaterSpray.M_GT_WaterSpray"), FLinearColor(0.72f, 0.80f, 0.77f), 0.82f, 0.24f},  // water: dedicated soft lit spray
	};

	const TCHAR* KindName(EGTSprayKind Kind)
	{
		switch (Kind)
		{
		case EGTSprayKind::Mud:  return TEXT("mud");
		case EGTSprayKind::Dust: return TEXT("dust");
		case EGTSprayKind::Snow: return TEXT("snow");
		case EGTSprayKind::Steam: return TEXT("steam");
		case EGTSprayKind::Water: return TEXT("water");
		default:                 return TEXT("?");
		}
	}
}

UGTSprayComponent::UGTSprayComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick after traction
	Random.Initialize(0x5AFE);
}

void UGTSprayComponent::BeginPlay()
{
	Super::BeginPlay();
	AActor* Owner = GetOwner();
	USceneComponent* Root = Owner ? Owner->GetRootComponent() : nullptr;
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UStaticMesh* SprayCard = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!Root || !Sphere)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTSprayComponent: no root or no engine sphere; no spray"));
		return;
	}
	Meshes.SetNum(KindCount);
	Materials.SetNum(KindCount);
	for (int32 Kind = 0; Kind < KindCount; ++Kind)
	{
		UInstancedStaticMeshComponent* Mesh = NewObject<UInstancedStaticMeshComponent>(Owner, *FString::Printf(TEXT("Spray_%s"), KindName(static_cast<EGTSprayKind>(Kind))), RF_Transient);
		Mesh->SetStaticMesh(Kind==static_cast<int32>(EGTSprayKind::Water) ? SprayCard : Sphere);
		if(Kind==static_cast<int32>(EGTSprayKind::Water))Mesh->NumCustomDataFloats=2;
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetCastShadow(false);
		Mesh->bAffectDynamicIndirectLighting = false;   // BO2: out of the Lumen scene
		Mesh->bVisibleInRayTracing = false;             // BO2: out of the ray-tracing scene
		Mesh->bAffectDistanceFieldLighting = false;
		Mesh->bReceivesDecals = false;
		Mesh->SetupAttachment(Root);
		Mesh->SetUsingAbsoluteLocation(true);
		Mesh->SetUsingAbsoluteRotation(true);
		Mesh->SetUsingAbsoluteScale(true);
		Mesh->SetWorldTransform(FTransform::Identity);
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, Looks[Kind].Material))
		{
			UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Base, this);
			Material->SetVectorParameterValue(SprayParamBaseColor, Looks[Kind].Colour);
			Material->SetScalarParameterValue(SprayParamRoughness, Looks[Kind].Roughness);
			Material->SetScalarParameterValue(ParamOpacity, Looks[Kind].Opacity);
			Mesh->SetMaterial(0, Material);
			Materials[Kind] = Material;
		}
		Mesh->RegisterComponent();
		// The pool: every instance exists from the start, dead ones at zero scale far below the world.
		Transforms[Kind].Init(FTransform(FRotator::ZeroRotator, FVector(0.f, 0.f, -100000.f), FVector::ZeroVector), PoolPerKind);
		Mesh->AddInstances(Transforms[Kind], false, true);
		SubmittedLiveCount[Kind] = 0;
		Meshes[Kind] = Mesh;
		Particles[Kind].Reserve(PoolPerKind);
	}
	// MR2: the car's own body (its collision is the root's: the chassis) and the state its mud goes into.
	BodyStateForThrow = Owner->FindComponentByClass<UGTBodyStateComponent>();
	if (UPrimitiveComponent* Body = Cast<UPrimitiveComponent>(Root))
	{
		BodyCollision = Body;
		BodyLocalBox = Body->CalcBounds(FTransform::Identity).GetBox().ExpandBy(FMath::Max(0.f, BodyTraceMarginCm));
	}
	// Wheel spray P2: the painterly layers (GTSprayArt.cpp).
	BeginArt(Root);
}

void UGTSprayComponent::Spawn(EGTSprayKind Kind, const FVector& Origin, const FVector& Forward, const FVector& Right, const FVector& CarVelocity, float Speed)
{
	TArray<FParticle>& Pool = Particles[static_cast<int32>(Kind)];
	if (Pool.Num() >= PoolPerKind)
	{
		// The pool is full: recycle the oldest slot. LM2a: a volumeless one first; a thrown blob recycled before it came
		// down puts its mud where it is now (on a patch) or counts it lost.
		int32 Victim = 0;
		while (Victim < Pool.Num() && Pool[Victim].VolumeCm3 > 0.0)
		{
			++Victim;
		}
		if (Victim >= Pool.Num())
		{
			Victim = 0;
			LandThrown(Pool[0], true);
		}
		Pool.RemoveAtSwap(Victim);
	}
	FParticle P;
	P.GroundZ = Origin.Z;
	P.Position = Origin + FVector(0.f, 0.f, 10.f) + Right * Random.FRandRange(-15.f, 15.f);
	const FVector Back = -Forward * (Speed >= 0.f ? 1.f : -1.f);
	switch (Kind)
	{
	case EGTSprayKind::Mud:
		P.Velocity = Back * Random.FRandRange(0.3f, 0.6f) * FMath::Abs(Speed) + FVector(0.f, 0.f, Random.FRandRange(150.f, 350.f))
			+ Right * Random.FRandRange(-120.f, 120.f) + CarVelocity * 0.2f;
		P.MaxLife = Random.FRandRange(0.6f, 1.0f);
		P.Size = Random.FRandRange(6.f, 12.f);
		break;
	case EGTSprayKind::Dust:
		P.Velocity = Back * Random.FRandRange(0.1f, 0.3f) * FMath::Abs(Speed) + FVector(0.f, 0.f, Random.FRandRange(50.f, 150.f))
			+ Right * Random.FRandRange(-80.f, 80.f);
		P.MaxLife = Random.FRandRange(1.5f, 2.5f);
		P.Size = Random.FRandRange(20.f, 35.f);
		P.Growth = 0.6f;   // doubles over its life
		break;
	case EGTSprayKind::Water:
		// Water stage W4: thrown out and up, wider than mud and shorter-lived, and it keeps more of the car's own
		// speed (a sheet of water leaves the tyre going where the tyre was going).
		P.Velocity = Back * Random.FRandRange(0.35f, 0.75f) * FMath::Abs(Speed) + FVector(0.f, 0.f, Random.FRandRange(180.f, 420.f))
			+ Right * Random.FRandRange(-180.f, 180.f) + CarVelocity * 0.3f;
		P.MaxLife = Random.FRandRange(0.45f, 0.85f);
		P.Size = Random.FRandRange(5.f, 14.f);
		P.Growth = 0.4f;
		break;
	case EGTSprayKind::Steam:
		// Rises off the bonnet and mostly keeps up with the car.
		P.Position = Origin + Right * Random.FRandRange(-25.f, 25.f);
		P.GroundZ = Origin.Z - 1000.f;
		P.Velocity = CarVelocity * 0.9f + FVector(0.f, 0.f, Random.FRandRange(60.f, 140.f)) + Right * Random.FRandRange(-30.f, 30.f);
		P.MaxLife = Random.FRandRange(1.2f, 2.0f);
		P.Size = Random.FRandRange(15.f, 25.f);
		P.Growth = 1.5f;
		break;
	default:
		P.Velocity = Back * Random.FRandRange(0.2f, 0.5f) * FMath::Abs(Speed) + FVector(0.f, 0.f, Random.FRandRange(100.f, 250.f))
			+ Right * Random.FRandRange(-100.f, 100.f) + CarVelocity * 0.1f;
		P.MaxLife = Random.FRandRange(0.9f, 1.5f);
		P.Size = Random.FRandRange(10.f, 20.f);
		break;
	}
	P.Id = NextParticleId++;   // wheel spray P2: drawing only
	P.Slice = SpawnSlice;
	Pool.Add(P);
	++TotalSpawned;
}

void UGTSprayComponent::SpawnThrown(EGTSprayKind Kind, const FVector& Origin, const FVector& Forward, const FVector& Right, const FVector& CarVelocity, float Speed, float SlipCmPerS, float SizeCm, double VolumeCm3)
{
	// LM3b (housekeeping 2): a wheel in a snow patch throws through the Snow kind (white, its own lighter fall); the blob
	// still carries its volume and comes down on the patch under it (DepositThrown), whose clods are the snow ones.
	TArray<FParticle>& Pool = Particles[static_cast<int32>(Kind == EGTSprayKind::Snow ? EGTSprayKind::Snow : EGTSprayKind::Mud)];
	if (Pool.Num() >= PoolPerKind)
	{
		int32 Victim = 0;
		while (Victim < Pool.Num() && Pool[Victim].VolumeCm3 > 0.0)
		{
			++Victim;
		}
		if (Victim >= Pool.Num())
		{
			Victim = 0;
			LandThrown(Pool[0], true);
		}
		Pool.RemoveAtSwap(Victim);
	}
	// Backwards from the spin's own direction (a wheel spinning forward throws behind the car), as today's mud does from
	// the car's, faster with the spin; and up, more with the spin.
	const float Spin = FMath::Abs(SlipCmPerS);
	const float SpinSign = Spin > 1.f ? FMath::Sign(SlipCmPerS) : (Speed >= 0.f ? 1.f : -1.f);
	// LM2c: each blob's own heading, +-ThrowHeadingSpreadDeg off straight back, and its own speed, 1 +- ThrowSpeedSpread of
	// the throw (the car's carried share is not scaled).
	const float Spread = FMath::Clamp(ThrowHeadingSpreadDeg, 0.f, 89.f);
	const FVector Back = (-Forward * SpinSign).RotateAngleAxis(Random.FRandRange(-Spread, Spread), FVector::UpVector);
	const float SpeedScale = 1.f + FMath::Clamp(ThrowSpeedSpread, 0.f, 0.95f) * Random.FRandRange(-1.f, 1.f);
	FParticle P;
	P.GroundZ = Origin.Z;
	P.Position = Origin + FVector(0.f, 0.f, 10.f) + Right * Random.FRandRange(-15.f, 15.f);
	P.Velocity = SpeedScale * (Back * (Random.FRandRange(0.3f, 0.6f) * FMath::Abs(Speed) + Random.FRandRange(0.4f, 0.8f) * ThrowBackPerSpin * Spin)
		+ FVector(0.f, 0.f, Random.FRandRange(150.f, 350.f) + ThrowUpPerSpin * Spin) + Right * Random.FRandRange(-80.f, 80.f)) + CarVelocity * 0.2f;
	P.MaxLife = FMath::Max(0.5f, ThrowBlobMaxLifeS);
	P.Size = SizeCm;
	P.VolumeCm3 = VolumeCm3;
	P.TraceFrom = P.Position;
	P.BodyFrom = P.Position;
	P.Id = NextParticleId++;   // wheel spray P2: drawing only
	P.Slice = SpawnSlice;
	Pool.Add(P);
	++TotalSpawned;
	ThrowEmittedCm3 += VolumeCm3;
	++ThrowBlobsEmitted;
	if (Kind == EGTSprayKind::Snow)
	{
		++ThrowBlobsSnow;
	}
}

void UGTSprayComponent::LandThrown(const FParticle& P, bool bLanded)
{
	if (P.VolumeCm3 <= 0.0)
	{
		return;
	}
	AGTMudPatch* Patch = (bLanded && MudForThrow) ? MudForThrow->PatchAt(FVector2D(P.Position.X, P.Position.Y)) : nullptr;
	const double Put = Patch ? Patch->DepositThrown(FVector2D(P.Position.X, P.Position.Y), P.VolumeCm3, 0.5f * P.Size) : 0.0;
	if (Put > 0.0)
	{
		ThrowLandedCm3 += Put;
		++ThrowBlobsLanded;
	}
	else
	{
		ThrowLostCm3 += P.VolumeCm3;
		++ThrowBlobsLost;
	}
}

void UGTSprayComponent::ResetThrowStats()
{
	ThrowEmittedCm3 = 0.0;
	ThrowLandedCm3 = 0.0;
	ThrowLostCm3 = 0.0;
	ThrowBlobsEmitted = 0;
	ThrowBlobsLanded = 0;
	ThrowBlobsLost = 0;
	ThrowBlobsSnow = 0;
	ThrowSplattedCm3 = 0.0;
	ThrowBlobsSplatted = 0;
	ThrowBlobsOnCar = 0;
	ThrowOnCarCm3 = 0.0;
	ThrowBlobsUnderCar = 0;
}

bool UGTSprayComponent::TraceBody(FParticle& P)
{
	UPrimitiveComponent* Body = BodyCollision.Get();
	if (!Body || !BodyStateForThrow || !BodyLocalBox.IsValid)
	{
		return false;
	}
	const FTransform CarTransform = Body->GetComponentTransform();
	// Only a rising blob near the body is traced: thrown from under the car it meets the floor or a face going up, and falling it
	// moves away (the first clean run traced 578 a second against the body and its 32 a frame refused 418).
	if (P.Velocity.Z <= 0.f || !BodyLocalBox.IsInsideOrOn(CarTransform.InverseTransformPosition(P.Position)))
	{
		P.BodyFrom = P.Position;
		return false;
	}
	if (GFrameCounter != BodyTraceFrame)
	{
		BodyTraceFrame = GFrameCounter;
		BodyTracesThisFrame = 0;
	}
	if (BodyTracesThisFrame >= FMath::Max(0, MaxBodyTracesPerFrame))
	{
		++BodyTracesCapped;   // BodyFrom kept: the next frame traces the longer path
		return false;
	}
	++BodyTracesThisFrame;
	++BodyTraces;
	const FVector From = P.BodyFrom;
	P.BodyFrom = P.Position;
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTMudBodyTrace), false);
	if (!Body->LineTraceComponent(Hit, From, P.Position, Params) || Hit.bStartPenetrating || Hit.Distance < 0.5f)
	{
		return false;   // a path that starts inside the body (a blob born under the arch, on its way out) never counts
	}
	const FVector LocalNormal = CarTransform.InverseTransformVectorNoScale(Hit.ImpactNormal);
	BodyStateForThrow->AddThrowHit(CarTransform.InverseTransformPosition(Hit.ImpactPoint), LocalNormal, P.VolumeCm3);
	if (LocalNormal.Z < -0.6f)
	{
		// The underside (the chassis box's floor, right over the wheels): it coats there and drops back, its mud still landing in
		// the field (most of a spin's throw meets the floor first: consumed there, 56 % of a spin-up's blobs never reached the bog).
		P.Position = Hit.ImpactPoint + Hit.ImpactNormal * 2.f;
		P.Velocity = FVector(P.Velocity.X * 0.5f, P.Velocity.Y * 0.5f, -FMath::Abs(P.Velocity.Z) * 0.3f);
		P.BodyFrom = P.Position;
		P.TraceFrom = P.Position;
		++ThrowBlobsUnderCar;
		return false;
	}
	LandThrown(P, false);   // lost to the fields, as a splat is
	ThrowOnCarCm3 += P.VolumeCm3;
	++ThrowBlobsOnCar;
	return true;
}

bool UGTSprayComponent::TraceThrown(FParticle& P, bool bInBox)
{
	// MR1: the path since the blob was last traced (a frame over the cap traces next frame from the same point, so nothing
	// is skipped). The owner's car is ignored (a blob on the body is MR2's); only world static and dynamic objects block.
	UWorld* World = GetWorld();
	if (!World || !SplatsForThrow || !SplatsForThrow->ReserveTrace())
	{
		return false;
	}
	const FVector From = P.TraceFrom;
	P.TraceFrom = P.Position;
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTMudSplatTrace), false, GetOwner());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	if (!World->LineTraceSingleByObjectType(Hit, From, P.Position, Objects, Params))
	{
		return false;
	}
	const FVector2D HitXY(Hit.ImpactPoint.X, Hit.ImpactPoint.Y);
	if (bInBox)
	{
		// Inside a box: a post or a rock on the way catches it; anything else and it flies on to the field.
		const int32 MeshSeed = static_cast<int32>(HashCombine(GetTypeHash(Hit.ImpactPoint), static_cast<uint32>(ThrowBlobsSplatted + ThrowBlobsLanded)) & 0x7fffffff);
		if (!SplatsForThrow->Splat(Hit, 0.5f * P.Size, MeshSeed, true))
		{
			return false;
		}
		LandThrown(P, false);
		ThrowSplattedCm3 += P.VolumeCm3;
		++ThrowBlobsSplatted;
		return true;
	}
	if (MudForThrow && MudForThrow->PatchAt(HitXY))
	{
		// Came down inside a patch's box after all: into its field, as LM2a lands it.
		FParticle Landed = P;
		Landed.Position = Hit.ImpactPoint;
		LandThrown(Landed, true);
		return true;
	}
	// The splat's own seed from where it hit (the spray's stream stays as it was).
	const int32 Seed = static_cast<int32>(HashCombine(GetTypeHash(Hit.ImpactPoint), static_cast<uint32>(ThrowBlobsSplatted + ThrowBlobsLost)) & 0x7fffffff);
	const bool bSplat = SplatsForThrow->Splat(Hit, 0.5f * P.Size, Seed);
	LandThrown(P, false);   // lost to the fields, as before MR1
	if (bSplat)
	{
		ThrowSplattedCm3 += P.VolumeCm3;
		++ThrowBlobsSplatted;
	}
	return true;
}

void UGTSprayComponent::Integrate(EGTSprayKind Kind, float DeltaSeconds)
{
	TArray<FParticle>& Pool = Particles[static_cast<int32>(Kind)];
	const float Gravity = Kind == EGTSprayKind::Mud || Kind == EGTSprayKind::Water ? 980.f
		: Kind == EGTSprayKind::Snow ? 500.f : Kind == EGTSprayKind::Steam ? -40.f : 80.f;
	const float Drag = Kind == EGTSprayKind::Dust ? 1.5f : Kind == EGTSprayKind::Steam ? 1.0f : 0.3f;
	for (int32 Index = Pool.Num() - 1; Index >= 0; --Index)
	{
		FParticle& P = Pool[Index];
		P.Life += DeltaSeconds;
		const bool FineMist=Kind==EGTSprayKind::Water && P.WaterOpacity<.2f;
		P.Velocity.Z -= Gravity * (FineMist ? .2f : 1.f) * DeltaSeconds;
		P.Velocity *= FMath::Max(0.f, 1.f - (FineMist ? 3.f : Drag) * DeltaSeconds);
		P.Position += P.Velocity * DeltaSeconds;
		if (P.VolumeCm3 > 0.0)
		{
			// MR2: a mud blob meeting the car's own body coats it (its own trace budget), before anything else.
			if (Kind == EGTSprayKind::Mud && UGTBodyStateComponent::IsCarMudEnabled() && TraceBody(P))
			{
				Pool.RemoveAtSwap(Index);
				continue;
			}
			// LM2a: a thrown blob comes down on the surface of the patch under it (the mesh's rest height plus the field's
			// surface there) and puts its mud into that field; outside every patch it dies as the spray does, and its mud
			// is lost.
			const FVector2D XY(P.Position.X, P.Position.Y);
			AGTMudPatch* Patch = MudForThrow ? MudForThrow->PatchAt(XY) : nullptr;
			if (Patch)
			{
				const float SurfaceZ = Patch->MeshRestZAt(XY) + Patch->GetField().HeightAt(XY);
				// MR1: inside the box the path is traced for posts and rocks (the ground is the field's); with splats off the
				// trace starts afresh here. MR2 housekeeping 4: only while the blob is descending within TraceBandCm of the
				// field's surface; above the band, or rising, the path is not traced (and starts afresh).
				if (SplatsForThrow && UGTTrackPaintSubsystem::IsSplatsEnabled())
				{
					if (P.Velocity.Z < 0.f && P.Position.Z - SurfaceZ < SplatsForThrow->TraceBandCm)
					{
						if (TraceThrown(P, true))
						{
							Pool.RemoveAtSwap(Index);
							continue;
						}
					}
					else
					{
						SplatsForThrow->NoteSkippedTrace();
						P.TraceFrom = P.Position;
					}
				}
				else
				{
					P.TraceFrom = P.Position;
				}
				if (P.Velocity.Z <= 0.f && P.Position.Z <= SurfaceZ)
				{
					LandThrown(P, true);
					Pool.RemoveAtSwap(Index);
				}
				else if (P.Life >= P.MaxLife)
				{
					LandThrown(P, false);
					Pool.RemoveAtSwap(Index);
				}
			}
			else if (SplatsForThrow && UGTTrackPaintSubsystem::IsSplatsEnabled())
			{
				// MR1: outside every patch the path is traced; a blob that finds nothing in its life or falls SplatFallCm below
				// its wheel's contact is lost. MR2 housekeeping 4: traced only while descending within TraceBandCm of the
				// landscape's height under it (a heightfield lookup, no trace; with no landscape under it, as MR1); a blob that
				// goes under that height splats the landscape there without a trace.
				float GroundZ = 0.f;
				const bool bGround = SplatsForThrow->LandscapeHeightAt(P.Position, GroundZ);
				bool bGone = false;
				if (P.Velocity.Z < 0.f && (!bGround || P.Position.Z - GroundZ < SplatsForThrow->TraceBandCm))
				{
					bGone = TraceThrown(P, false);
				}
				else
				{
					SplatsForThrow->NoteSkippedTrace();
					P.TraceFrom = P.Position;
				}
				if (!bGone && bGround && P.Position.Z <= GroundZ)
				{
					const int32 Seed = static_cast<int32>(HashCombine(GetTypeHash(P.Position), static_cast<uint32>(ThrowBlobsSplatted + ThrowBlobsLost)) & 0x7fffffff);
					const bool bSplat = SplatsForThrow->SplatGround(FVector(P.Position.X, P.Position.Y, GroundZ), 0.5f * P.Size, Seed);
					LandThrown(P, false);   // lost to the fields, as before MR1
					if (bSplat)
					{
						ThrowSplattedCm3 += P.VolumeCm3;
						++ThrowBlobsSplatted;
					}
					bGone = true;
				}
				if (bGone)
				{
					Pool.RemoveAtSwap(Index);
				}
				else if (P.Life >= P.MaxLife || P.Position.Z < P.GroundZ - SplatFallCm)
				{
					LandThrown(P, false);
					Pool.RemoveAtSwap(Index);
				}
			}
			else if (P.Life >= P.MaxLife || P.Position.Z < P.GroundZ - 2.f)
			{
				LandThrown(P, false);
				Pool.RemoveAtSwap(Index);
			}
			continue;
		}
		if (P.Life >= P.MaxLife || P.Position.Z < P.GroundZ - 2.f)
		{
			Pool.RemoveAtSwap(Index);
		}
	}
}

bool UGTSprayComponent::UseSparseRenderUpdates()
{
	return CVarSpraySparseUpdates.GetValueOnGameThread() != 0;
}

void UGTSprayComponent::PushTransforms(EGTSprayKind Kind)
{
	TRACE_CPUPROFILER_EVENT_SCOPE(GTSpray_PushTransforms);
	const int32 K = static_cast<int32>(Kind);
	if (!Meshes.IsValidIndex(K) || !Meshes[K])
	{
		return;
	}
	const TArray<FParticle>& Pool = Particles[K];
	TArray<FTransform>& Out = Transforms[K];
	// Wheel spray P2: at gt.Spray.Art 1 the Mud kind draws as clumps; its spheres are hidden once, when that starts.
	if (Kind == EGTSprayKind::Mud)
	{
		const bool bWasDrawn = bArtDrawn;
		bArtDrawn = PushClumps();
		if (bArtDrawn)
		{
			if (!bWasDrawn || SubmittedLiveCount[K] > 0)
			{
				for (FTransform& T : Out)
				{
					T = FTransform(FRotator::ZeroRotator, FVector(0.f, 0.f, -100000.f), FVector::ZeroVector);
				}
				// BO2: no proxy recreate; the instance tracker flushes transform and custom-data changes itself.
				if (Meshes[K]->BatchUpdateInstancesTransforms(0, Out, true, false, true))
				{
					SubmittedLiveCount[K] = 0;
				}
			}
			return;
		}
	}
	const int32 LiveCount = FMath::Min(Pool.Num(), Out.Num());
	// RemoveAtSwap keeps live particles in a prefix. Include the old prefix to
	// hide expired slots, then leave the already hidden tail untouched. Empty
	// emitters do no transform work after their final visible batch is retired.
	const int32 UpdateCount = UseSparseRenderUpdates()
		? FMath::Min(FMath::Max(LiveCount, SubmittedLiveCount[K]), Out.Num()) : Out.Num();
	if (UpdateCount == 0)
	{
		return;
	}
	FVector Camera=GetOwner()->GetActorLocation()+FVector(0,0,500);
	if(Kind==EGTSprayKind::Water)
		if(const APlayerController* PC=GetWorld()->GetFirstPlayerController())
			if(PC->PlayerCameraManager)Camera=PC->PlayerCameraManager->GetCameraLocation();
	for (int32 Index = 0; Index < UpdateCount; ++Index)
	{
		if (Index < Pool.Num())
		{
			const FParticle& P = Pool[Index];
			const float Scale = P.Size * (1.f + P.Growth * P.Life / FMath::Max(P.MaxLife, 0.01f)) / 100.f;   // the engine sphere is 100 cm
			if (Kind == EGTSprayKind::Water)
			{
				// Short tapered streaks/sheets, aligned with flight. Fade by shrinking at the end,
				// without allocating per-particle materials or another emitter.
				const float Fade=FMath::Clamp((1.f-P.Life/P.MaxLife)*4.f,0.f,1.f);
				const FVector Facing=(Camera-P.Position).GetSafeNormal();
				FVector Flight=P.Velocity-Facing*FVector::DotProduct(P.Velocity,Facing);
				if(Flight.IsNearlyZero())Flight=FVector::CrossProduct(Facing,FVector::RightVector);
				Out[Index]=FTransform(FRotationMatrix::MakeFromXZ(Flight.GetSafeNormal(),Facing).ToQuat(),P.Position,P.WaterShape*Scale);
				Meshes[K]->SetCustomDataValue(Index,0,P.WaterOpacity*Fade,false);
				Meshes[K]->SetCustomDataValue(Index,1,P.WaterFamily,false);
			}
			else Out[Index] = FTransform(FRotator::ZeroRotator, P.Position, FVector(Scale));
		}
		else
		{
			Out[Index] = FTransform(FRotator::ZeroRotator, FVector(0.f, 0.f, -100000.f), FVector::ZeroVector);
		}
	}
	if (Meshes[K]->BatchUpdateInstancesTransforms(0, TArrayView<const FTransform>(Out.GetData(), UpdateCount), true, false, true))
	{
		SubmittedLiveCount[K] = LiveCount;
	}
}

void UGTSprayComponent::Update(float DeltaSeconds, const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move, float ForwardSpeed,
                               const UGTConditionComponent& Condition, const UGTHullComponent* Hull)
{
	const AActor* Owner = GetOwner();
	if (!Owner || Meshes.Num() != KindCount)
	{
		return;
	}
	const FVector Forward = Owner->GetActorForwardVector();
	const FVector Right = Owner->GetActorRightVector();
	const FVector CarVelocity = Owner->GetVelocity();
	const float SpeedFactor = FMath::Clamp(FMath::Abs(ForwardSpeed) / FMath::Max(1.f, SprayFullSpeed), 0.f, 1.f);
	const int32 NumWheels = FMath::Min(Traction.Wheels.Num(), Move.GetNumWheels());
	if (SpawnAccumulators.Num() != NumWheels)
	{
		SpawnAccumulators.Init(0.f, NumWheels);
	}
	// Water stage W4: the car's own speed in m/s, which is what both water rates ride on (the whole velocity and not
	// the forward component: a car being carried sideways down a ford is still throwing water).
	WaterSpeedMps = 0.f; // Filled from the local relative water speed by the water-only emitters.
	if (SplashAccumulators.Num() != NumWheels)
	{
		SplashAccumulators.Init(0.f, NumWheels);
	}
	// LM2a: the thrown mud's bookkeeping per wheel, and the patches the blobs come down on.
	if (ThrowSpentCm3.Num() != NumWheels)
	{
		ThrowSpentCm3.Init(0.0, NumWheels);
		ThrowNextBlobCm.Init(0.f, NumWheels);
		ThrowSeenCm3.Init(0.0, NumWheels);
		ThrowHazard.Init(0.0, NumWheels);
		ThrowNextGap.Init(-1.0, NumWheels);
		for (int32 Index = 0; Index < NumWheels; ++Index)
		{
			ThrowSpentCm3[Index] = Traction.Wheels[Index].ThrownCm3;   // what was thrown before this component looked is not owed
			ThrowSeenCm3[Index] = Traction.Wheels[Index].ThrownCm3;
		}
	}
	MudForThrow = GetWorld() ? GetWorld()->GetSubsystem<UGTMudSubsystem>() : nullptr;
	SplatsForThrow = GetWorld() ? GetWorld()->GetSubsystem<UGTMudSplatSubsystem>() : nullptr;
	ThrowPendingCm3 = 0.0;
	const float MinCm = FMath::Max(1.f, ThrowBlobMinCm);
	const float MaxCm = FMath::Max(MinCm, ThrowBlobMaxCm);
	const float SizePower = FMath::Max(0.1f, ThrowSizePower);
	const float Fill = FMath::Max(0.01f, ThrowBlobFill);
	auto BlobVolume = [Fill](float SizeCm) { const double R = 0.5 * SizeCm; return 4.0 / 3.0 * PI * R * R * R * Fill; };
	if (ThrowMeanKey != FVector3f(MinCm, MaxCm, SizePower) || ThrowMeanFill != Fill)
	{
		// LM2c: the mean blob volume under the power law, by the midpoint rule over u (256 steps).
		ThrowMeanKey = FVector3f(MinCm, MaxCm, SizePower);
		ThrowMeanFill = Fill;
		double Sum = 0.0;
		for (int32 K = 0; K < 256; ++K)
		{
			Sum += BlobVolume(MinCm + (MaxCm - MinCm) * FMath::Pow((K + 0.5f) / 256.f, SizePower));
		}
		ThrowMeanBlobCm3 = FMath::Max(1.0, Sum / 256.0);
	}
	const double Reserve0 = FMath::Max(0.5, static_cast<double>(ThrowReserveBlobs)) * ThrowMeanBlobCm3;
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		const FGTWheelTraction& Wheel = Traction.Wheels[Index];
		ThrowSpentCm3[Index] = FMath::Min(ThrowSpentCm3[Index], Wheel.ThrownCm3);
		// LM2c: the Poisson stream. Its clock runs with the volume thrown this tick, over the mean blob, times what waits at
		// the wheel over Reserve0 (at most 4x), so the waiting mud settles at about Reserve0 and the mean rate is LM2a's
		// (one mean blob per mean blob of mud). A blob leaves when the clock passes an exponential gap, if its mud is there.
		const double Flow = FMath::Max(0.0, Wheel.ThrownCm3 - ThrowSeenCm3[Index]);
		ThrowSeenCm3[Index] = Wheel.ThrownCm3;
		const double Waiting = Wheel.ThrownCm3 - ThrowSpentCm3[Index];
		ThrowHazard[Index] += Flow / ThrowMeanBlobCm3 * FMath::Min(4.0, Waiting / Reserve0);
		if (ThrowNextGap[Index] < 0.0)
		{
			ThrowNextGap[Index] = -FMath::Loge(FMath::Max(1.e-6, 1.0 - Random.FRand()));
		}
		int32 Blobs = 0;
		while (Blobs < ThrowBlobsPerTick && ThrowHazard[Index] >= ThrowNextGap[Index])
		{
			if (ThrowNextBlobCm[Index] <= 0.f)
			{
				ThrowNextBlobCm[Index] = MinCm + (MaxCm - MinCm) * FMath::Pow(Random.FRand(), SizePower);
			}
			const double Volume = BlobVolume(ThrowNextBlobCm[Index]);
			if (Wheel.ThrownCm3 - ThrowSpentCm3[Index] < Volume)
			{
				break;   // its mud is not all there yet: it goes when it is
			}
			SpawnSlice = Wheel.PatchVariant;
			SpawnThrown(Wheel.bInSnowPatch ? EGTSprayKind::Snow : EGTSprayKind::Mud, Move.GetWheelState(Index).ContactPoint, Forward, Right, CarVelocity, ForwardSpeed, Wheel.SlipMagnitude, ThrowNextBlobCm[Index], Volume);
			ThrowSpentCm3[Index] += Volume;
			ThrowNextBlobCm[Index] = 0.f;
			ThrowHazard[Index] -= ThrowNextGap[Index];
			ThrowNextGap[Index] = -FMath::Loge(FMath::Max(1.e-6, 1.0 - Random.FRand()));
			++Blobs;
		}
		ThrowPendingCm3 += Wheel.ThrownCm3 - ThrowSpentCm3[Index];
	}
	bWheelSplashing = false;
	SplashWheels = 0;
	SplashDeepestM = 0.f;
	SplashRateNow = 0.f;
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		const FGTWheelTraction& Wheel = Traction.Wheels[Index];
		if (!Wheel.bInContact)
		{
			SplashAccumulators[Index] = 0.f;
			continue;
		}
		UpdateWaterWheel(Index, DeltaSeconds, Traction, Move);
		EGTSprayKind Kind = EGTSprayKind::Count;
		float Rate = 0.f;
		if (Wheel.SurfaceTag == GTTags::Surface_Mud.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Bog.GetTag())
		{
			Kind = EGTSprayKind::Mud;
			Rate = MudRate;
		}
		else if ((Wheel.SurfaceTag == GTTags::Surface_Dirt.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Sand.GetTag()) && Wheel.WaterDepthM <= SplashDepthM)
		{
			Kind = EGTSprayKind::Dust;
			Rate = DustRate;
		}
		else if (Wheel.SurfaceTag == GTTags::Surface_Snow.GetTag())
		{
			Kind = EGTSprayKind::Snow;
			Rate = SnowRate;
		}
		// Wheel spray P2: at gt.Spray.Art 1 a gravel patch's dust is the Niagara GravelDust; the grey Dust spheres stop there (Benmore
		// B1b: and on a gravel surface's physical material).
        if ((Kind == EGTSprayKind::Dust && bExternalDustEffects)
            || (Kind == EGTSprayKind::Mud && AGTMudRunnerWheelEffects::IsActive(this))
            || (Kind == EGTSprayKind::Mud && bExternalMudEffects && AGTMudFlickLab::CoversWheel(Wheel))
            || Kind == EGTSprayKind::Count || (Kind == EGTSprayKind::Dust && IsArtEnabled()
			&& (Wheel.bInGravelPatch || GravelSpraySurface(Move.GetWheelState(Index)))))
		{
			SpawnAccumulators[Index] = 0.f;
			continue;
		}
		SpawnSlice = Wheel.PatchVariant;
		const float Spin = Wheel.bSlipping ? FMath::Clamp(Wheel.SlipMagnitude / 300.f, 0.f, 1.f) : 0.f;
		const float Spray = FMath::Min(1.f, SpeedFactor + Spin);
		SpawnAccumulators[Index] += Rate * Spray * DeltaSeconds;
		const FVector Contact = Move.GetWheelState(Index).ContactPoint;
		while (SpawnAccumulators[Index] >= 1.f)
		{
			SpawnAccumulators[Index] -= 1.f;
			Spawn(Kind, Contact, Forward, Right, CarVelocity, ForwardSpeed);
		}
	}
	UpdateWaterBow(DeltaSeconds, Traction, Move, Hull);
	// Steam: a radiator below half health boils over at the bonnet, more the worse it is.
	const float Radiator = Condition.GetPartHealth(EGTCarPart::Radiator);
	if (Radiator < 0.5f)
	{
		SteamAccumulator += SteamRate * ((0.5f - Radiator) / 0.5f) * DeltaSeconds;
		const FVector Origin = Owner->GetActorTransform().TransformPosition(SteamOrigin);
		while (SteamAccumulator >= 1.f)
		{
			SteamAccumulator -= 1.f;
			Spawn(EGTSprayKind::Steam, Origin, Forward, Right, CarVelocity, ForwardSpeed);
		}
	}
	UpdateArt(DeltaSeconds, Traction, Move, ForwardSpeed, SpeedFactor);
	for (int32 Kind = 0; Kind < KindCount; ++Kind)
	{
		Integrate(static_cast<EGTSprayKind>(Kind), DeltaSeconds);
		PushTransforms(static_cast<EGTSprayKind>(Kind));
	}
	PushWaterMud();   // wheel spray P2d: the muddy rut splash's colour, after the Water kind's transforms
}

int32 UGTSprayComponent::GetLiveCount(EGTSprayKind Kind) const
{
	const int32 K = static_cast<int32>(Kind);
	return K >= 0 && K < KindCount ? Particles[K].Num() : 0;
}

FString UGTSprayComponent::Describe() const
{
	return FString::Printf(TEXT("spray mud=%d dust=%d snow=%d steam=%d water=%d spawned=%d"),
		GetLiveCount(EGTSprayKind::Mud), GetLiveCount(EGTSprayKind::Dust), GetLiveCount(EGTSprayKind::Snow), GetLiveCount(EGTSprayKind::Steam),
		GetLiveCount(EGTSprayKind::Water), TotalSpawned);
}

FString UGTSprayComponent::DescribeWater() const
{
	return FString::Printf(TEXT("spray water: %.2f m/s, %d wheel(s) splashing (deepest %.2f m of %.2f asked, %.0f/s), bow %d (submerged %.2f m of %.2f asked, %.0f/s), %d live"),
		WaterSpeedMps, SplashWheels, SplashDeepestM, SplashDepthM, SplashRateNow,
		bBowSpraying ? 1 : 0, BowSubmergedM, BowSprayHeightM, BowRateNow, GetLiveCount(EGTSprayKind::Water));
}
