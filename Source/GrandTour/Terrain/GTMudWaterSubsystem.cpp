// Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md items 2b, 3d, 3f): the switches and the water rings.
#include "Terrain/GTMudWaterSubsystem.h"

#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTTractionComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "Misc/App.h"
#include "NiagaraComponent.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraSystemInstanceController.h"

namespace GTMudWater
{
	static TAutoConsoleVariable<int32> CVarDeformDetail(TEXT("gt.Mud.DeformDetail"), 1,
		TEXT("Mud and water MW1: 1 the crisp non-sliding detail (the variant slice's normal and AO at 2.6x, turned 29 deg, in the field-normal frame) on moved mud and steep banks; 0 off."),
		ECVF_Default);
	static TAutoConsoleVariable<int32> CVarWaterMotion(TEXT("gt.Mud.WaterMotion"), 1,
		TEXT("Mud and water MW1: 1 the moving rut water (wind ruffle with gusts, calmer edges, settled roughness 0.2-0.3, the froth, mottle and flecks drifting downhill); 0 the water before MW1."),
		ECVF_Default);
	static TAutoConsoleVariable<int32> CVarOldTread(TEXT("gt.Mud.OldTread"), 1,
		TEXT("Mud roads MRD1: 1 the partial old tyre tread on a mud road's freshest old tracks (M_GT_Mud, MPC_TrackPaint MudOldTread); 0 off."),
		ECVF_Default);
	static TAutoConsoleVariable<int32> CVarWaterRings(TEXT("gt.Mud.WaterRings"), 1,
		TEXT("Mud and water MW1: 1 the water rings (NS_GT_WaterRings) where a wheel moves through rut water and at each footstep in it; 0 none."),
		ECVF_Default);

	static const TCHAR* CollectionPath = TEXT("/Game/GrandTour/Terrain/MPC_TrackPaint.MPC_TrackPaint");
	static const TCHAR* SystemPath = TEXT("/Game/GrandTour/FX/NS_GT_WaterRings.NS_GT_WaterRings");
	static const FName ParamDeformDetail(TEXT("MudDeformDetail"));
	static const FName ParamWaterMotion(TEXT("MudWaterMotion"));
	static const FName ParamOldTread(TEXT("MudOldTread"));
	static const FName RingRateName(TEXT("User.RingRate"));
	static const FName RingScaleName(TEXT("User.RingScale"));
	static constexpr uint64 TestKey = ~0ull;
	static constexpr double IdleSeconds = 3.0;    // a source quiet this long deactivates (every ring of it is gone by then)
	static constexpr double ForgetSeconds = 30.0; // and is dropped after this
}

bool UGTMudWaterSubsystem::IsDeformDetailEnabled() { return GTMudWater::CVarDeformDetail.GetValueOnGameThread() != 0; }
bool UGTMudWaterSubsystem::IsWaterMotionEnabled() { return GTMudWater::CVarWaterMotion.GetValueOnGameThread() != 0; }
bool UGTMudWaterSubsystem::IsWaterRingsEnabled() { return GTMudWater::CVarWaterRings.GetValueOnGameThread() != 0; }

float UGTMudWaterSubsystem::WheelRingRate(float SpeedCmS)
{
	if (SpeedCmS < RingMinSpeedCm)
	{
		return 0.f;
	}
	return 1.f + 5.f * FMath::Clamp((SpeedCmS - RingMinSpeedCm) / (RingFullSpeedCm - RingMinSpeedCm), 0.f, 1.f);
}

int32 UGTMudWaterSubsystem::RingsThisFrame(float& Carry, float RatePerS, float DeltaSeconds)
{
	if (RatePerS <= 0.f || DeltaSeconds <= 0.f)
	{
		return 0;
	}
	Carry += RatePerS * DeltaSeconds;
	const int32 N = FMath::FloorToInt(Carry);
	Carry -= static_cast<float>(N);
	return N;
}

int32 UGTMudWaterSubsystem::StepsThisFrame(float& Clock, bool bMovingInWater, float DeltaSeconds, float StepS)
{
	if (!bMovingInWater || StepS <= 0.f)
	{
		Clock = StepS;   // primed: the next foot that meets the water rings at once
		return 0;
	}
	Clock += DeltaSeconds;
	int32 N = 0;
	while (Clock >= StepS)
	{
		Clock -= StepS;
		++N;
	}
	return N;
}

bool UGTMudWaterSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGTMudWaterSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	ParameterCollection = LoadObject<UMaterialParameterCollection>(nullptr, GTMudWater::CollectionPath);
	UE_LOG(LogTemp, Display, TEXT("UGTMudWaterSubsystem: gt.Mud.DeformDetail %d gt.Mud.WaterMotion %d gt.Mud.WaterRings %d; MPC_TrackPaint %s (MudDeformDetail %d, MudWaterMotion %d)"),
		IsDeformDetailEnabled() ? 1 : 0, IsWaterMotionEnabled() ? 1 : 0, IsWaterRingsEnabled() ? 1 : 0, ParameterCollection ? TEXT("loaded") : TEXT("missing"),
		ParameterCollection && ParameterCollection->GetScalarParameterByName(GTMudWater::ParamDeformDetail) ? 1 : 0,
		ParameterCollection && ParameterCollection->GetScalarParameterByName(GTMudWater::ParamWaterMotion) ? 1 : 0);
}

void UGTMudWaterSubsystem::Deinitialize()
{
	for (UNiagaraComponent* C : Components)
	{
		if (C)
		{
			C->DestroyComponent();
		}
	}
	Components.Reset();
	Sources.Reset();
	Super::Deinitialize();
}

void UGTMudWaterSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	WriteSwitches();
	UpdateRings(DeltaTime);
}

void UGTMudWaterSubsystem::WriteSwitches()
{
	const int32 Detail = IsDeformDetailEnabled() ? 1 : 0;
	const int32 Motion = IsWaterMotionEnabled() ? 1 : 0;
	const int32 OldTread = GTMudWater::CVarOldTread.GetValueOnGameThread() != 0 ? 1 : 0;   // MRD1
	if (!ParameterCollection || (Detail == WrittenDeformDetail && Motion == WrittenWaterMotion && OldTread == WrittenOldTread))
	{
		return;
	}
	for (const TPair<FName, int32>& Switch : { TPair<FName, int32>(GTMudWater::ParamDeformDetail, Detail), TPair<FName, int32>(GTMudWater::ParamWaterMotion, Motion),
		TPair<FName, int32>(GTMudWater::ParamOldTread, OldTread) })
	{
		if (ParameterCollection->GetScalarParameterByName(Switch.Key))
		{
			UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), ParameterCollection, Switch.Key, static_cast<float>(Switch.Value));
		}
	}
	WrittenDeformDetail = Detail;
	WrittenWaterMotion = Motion;
	WrittenOldTread = OldTread;
}

float UGTMudWaterSubsystem::WaterSurfaceZAt(FVector2D XYCm, float& OutDepthCm) const
{
	OutDepthCm = 0.f;
	const UWorld* World = GetWorld();
	const UGTMudSubsystem* Mud = World ? World->GetSubsystem<UGTMudSubsystem>() : nullptr;
	const AGTMudPatch* Patch = Mud ? Mud->PatchAt(XYCm) : nullptr;
	if (!Patch)
	{
		return 0.f;
	}
	OutDepthCm = Patch->WaterDepthCmAt(XYCm);
	return Patch->MeshRestZAt(XYCm) + (OutDepthCm > 0.f ? Patch->CurrentWaterTableCm() : 0.f);
}

UGTMudWaterSubsystem::FSource& UGTMudWaterSubsystem::Source(uint64 Key)
{
	FSource& S = Sources.FindOrAdd(Key);
	if (const UWorld* W = GetWorld())
	{
		S.LastTouch = W->GetTimeSeconds();
	}
	if (!S.Component.IsValid() && RingSystem && FApp::CanEverRender())
	{
		UWorld* World = GetWorld();
		UNiagaraComponent* Nc = NewObject<UNiagaraComponent>(World, NAME_None, RF_Transient);
		Nc->SetAsset(RingSystem);
		Nc->SetAutoActivate(false);
		Nc->SetUsingAbsoluteLocation(true);
		Nc->SetUsingAbsoluteRotation(true);
		Nc->SetUsingAbsoluteScale(true);
		Nc->SetCastShadow(false);
		Nc->SetTranslucentSortPriority(2);   // over the rut water (AGTMudPatch's WaterMesh is 1)
		Nc->RegisterComponentWithWorld(World);
		Components.Add(Nc);
		S.Component = Nc;
	}
	return S;
}

void UGTMudWaterSubsystem::Emit(FSource& S, const FVector& Location, int32 Count, float DeltaSeconds)
{
	const UWorld* World = GetWorld();
	S.LastEmit = World ? World->GetTimeSeconds() : 0.0;
	UNiagaraComponent* Nc = S.Component.Get();
	if (!Nc)
	{
		return;
	}
	// The rate that spawns exactly Count in the next simulation step (it ticks once with this frame's step: a fixed one in the checks).
	const float Rate = static_cast<float>(Count) / FMath::Max(DeltaSeconds, 1e-4f);
	Nc->SetWorldLocation(Location);
	Nc->SetVariableFloat(GTMudWater::RingRateName, Rate);
	Nc->SetVariableFloat(GTMudWater::RingScaleName, 1.f);
	S.WrittenRate = Rate;
	if (!Nc->IsActive())
	{
		Nc->Activate(true);
	}
}

void UGTMudWaterSubsystem::Quiet(FSource& S, float DeltaSeconds)
{
	UNiagaraComponent* Nc = S.Component.Get();
	if (!Nc)
	{
		return;
	}
	if (S.WrittenRate != 0.f)
	{
		Nc->SetVariableFloat(GTMudWater::RingRateName, 0.f);
		S.WrittenRate = 0.f;
	}
	const UWorld* World = GetWorld();
	if (Nc->IsActive() && World && World->GetTimeSeconds() - S.LastEmit > GTMudWater::IdleSeconds)
	{
		Nc->Deactivate();
	}
}

void UGTMudWaterSubsystem::UpdateRings(float DeltaSeconds)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (!IsWaterRingsEnabled())
	{
		for (TPair<uint64, FSource>& Pair : Sources)
		{
			if (UNiagaraComponent* Nc = Pair.Value.Component.Get())
			{
				if (Nc->IsActive())
				{
					Nc->DeactivateImmediate();   // off is off: no rings left on the water
				}
			}
			Pair.Value.Carry = 0.f;
		}
		return;
	}
	if (!bRingSystemLooked && FApp::CanEverRender())
	{
		bRingSystemLooked = true;
		RingSystem = LoadObject<UNiagaraSystem>(nullptr, GTMudWater::SystemPath);
		if (!RingSystem)
		{
			UE_LOG(LogTemp, Warning, TEXT("UGTMudWaterSubsystem: no NS_GT_WaterRings (Art/setup_mud_water.ps1); rings are counted, not drawn"));
		}
	}
	TSet<uint64> Fed;
	++DiagTicks;
	// The wheels: every car's wheels in rut water over RingMinDepthCm, at 1-6 rings a second by the car's ground speed.
	for (TActorIterator<AGTCarPawn> It(World); It; ++It)
	{
		AGTCarPawn* Car = *It;
		const UGTTractionComponent* Traction = Car ? Car->GetTraction() : nullptr;
		if (!Traction)
		{
			continue;
		}
		const float Speed = static_cast<float>(Car->GetVelocity().Size2D());
		const float Rate = WheelRingRate(Speed);
		DiagMaxSpeed = FMath::Max(DiagMaxSpeed, Speed);
		for (int32 W = 0; W < Traction->Wheels.Num(); ++W)
		{
			const FGTWheelTraction& Wheel = Traction->Wheels[W];
			++DiagWheelTicks;
			DiagContact += Wheel.bInContact ? 1 : 0;
			DiagRut += Wheel.bRutWater ? 1 : 0;
			DiagDeep += Wheel.WaterDepthM * 100.f > RingMinDepthCm ? 1 : 0;
			DiagMoving += Rate > 0.f ? 1 : 0;
			const bool bIn = Wheel.bInContact && Wheel.bRutWater && Wheel.WaterDepthM * 100.f > RingMinDepthCm && Rate > 0.f;
			const uint64 Key = (static_cast<uint64>(Car->GetUniqueID()) << 8) | static_cast<uint64>(W & 0x7F);
			if (!bIn)
			{
				if (FSource* S = Sources.Find(Key))
				{
					S->Carry = 0.f;
				}
				continue;
			}
			FSource& S = Source(Key);
			const int32 N = RingsThisFrame(S.Carry, Rate, DeltaSeconds);
			if (N > 0)
			{
				const FVector2D XY(Wheel.ContactPoint.X, Wheel.ContactPoint.Y);
				float Depth = 0.f;
				float Z = WaterSurfaceZAt(XY, Depth);
				if (Depth <= 0.f)
				{
					Z = Wheel.ContactPoint.Z + Wheel.WaterDepthM * 100.f;
				}
				WheelRings += N;
				Emit(S, FVector(XY.X, XY.Y, Z + RingLiftCm), N, DeltaSeconds);
				Fed.Add(Key);
			}
		}
	}
	// The footsteps: the player on foot, moving on the ground in rut water over RingMinDepthCm, one ring every StepSeconds
	// (the character has no step event), alternating 12 cm either side of its path.
	if (ACharacter* Walker = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(World, 0)))
	{
		const FVector At = Walker->GetActorLocation();
		const FVector2D XY(At.X, At.Y);
		float Depth = 0.f;
		const float Z = WaterSurfaceZAt(XY, Depth);
		const UCharacterMovementComponent* Move = Walker->GetCharacterMovement();
		const FVector Vel = Walker->GetVelocity();
		const bool bMoving = Vel.Size2D() > StepMinSpeedCm && Move && Move->IsMovingOnGround();
		const uint64 Key = (static_cast<uint64>(Walker->GetUniqueID()) << 8) | 0xFFull;
		++DiagWalkerTicks;
		DiagWalkerWet += Depth > RingMinDepthCm ? 1 : 0;
		DiagWalkerMoving += bMoving ? 1 : 0;
		DiagWalkerMaxDepth = FMath::Max(DiagWalkerMaxDepth, Depth);
		FSource& S = Sources.FindOrAdd(Key);
		S.LastTouch = World->GetTimeSeconds();
		const int32 N = StepsThisFrame(S.Clock, bMoving && Depth > RingMinDepthCm, DeltaSeconds, StepSeconds);
		if (N > 0)
		{
			FSource& Src = Source(Key);
			const FVector2D Dir = FVector2D(Vel.X, Vel.Y).GetSafeNormal();
			const FVector2D Off = FVector2D(-Dir.Y, Dir.X) * 12.f * Src.Side;
			Src.Side = -Src.Side;
			FeetRings += N;
			Emit(Src, FVector(XY.X + Off.X, XY.Y + Off.Y, Z + RingLiftCm), N, DeltaSeconds);
			Fed.Add(Key);
		}
	}
	// Everything not fed this frame: the rate back to 0, idle ones deactivated, ones untouched for ForgetSeconds dropped (a source
	// in the water keeps its carry and its step clock from tick to tick).
	const double Now = World->GetTimeSeconds();
	for (auto It = Sources.CreateIterator(); It; ++It)
	{
		if (Fed.Contains(It.Key()))
		{
			continue;
		}
		Quiet(It.Value(), DeltaSeconds);
		if (Now - FMath::Max(It.Value().LastEmit, It.Value().LastTouch) > GTMudWater::ForgetSeconds && It.Key() != GTMudWater::TestKey)
		{
			if (UNiagaraComponent* Nc = It.Value().Component.Get())
			{
				Components.Remove(Nc);
				Nc->DestroyComponent();
			}
			It.RemoveCurrent();
		}
	}
}

void UGTMudWaterSubsystem::EmitRingsForTest(FVector WorldLocation, int32 Count)
{
	if (!bRingSystemLooked && FApp::CanEverRender())
	{
		bRingSystemLooked = true;
		RingSystem = LoadObject<UNiagaraSystem>(nullptr, GTMudWater::SystemPath);
	}
	FSource& S = Source(GTMudWater::TestKey);
	const UWorld* World = GetWorld();
	WheelRings += FMath::Max(0, Count);
	Emit(S, WorldLocation, FMath::Max(0, Count), World ? FMath::Max(World->GetDeltaSeconds(), 1e-3f) : 1.f / 60.f);
}

FString UGTMudWaterSubsystem::DescribeRings() const
{
	return FString::Printf(TEXT("ticks %d; wheel-ticks %d: in contact %d, in rut water %d, over %.0f cm %d, moving %d; fastest car %.0f cm/s; walker ticks %d: in water %d, moving %d, deepest %.1f cm; rings wheels %d feet %d; system %s, sources %d, components %d; switch %d"),
		DiagTicks, DiagWheelTicks, DiagContact, DiagRut, RingMinDepthCm, DiagDeep, DiagMoving, DiagMaxSpeed, DiagWalkerTicks, DiagWalkerWet, DiagWalkerMoving,
		DiagWalkerMaxDepth, WheelRings, FeetRings, RingSystem ? TEXT("loaded") : TEXT("none"), Sources.Num(), Components.Num(), IsWaterRingsEnabled() ? 1 : 0);
}

int32 UGTMudWaterSubsystem::GetRingLiveParticles() const
{
	int32 Total = 0;
	for (UNiagaraComponent* Nc : Components)
	{
		if (!Nc)
		{
			continue;
		}
		FNiagaraSystemInstanceControllerConstPtr Controller = Nc->GetSystemInstanceController();
		const FNiagaraSystemInstance* Instance = Controller.IsValid() ? Controller->GetSystemInstance_Unsafe() : nullptr;
		if (!Instance)
		{
			continue;
		}
		for (const auto& Emitter : Instance->GetEmitters())
		{
			Total += Emitter->GetNumParticles();
		}
	}
	return Total;
}
