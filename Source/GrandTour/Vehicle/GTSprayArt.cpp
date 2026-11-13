// Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md): UGTSprayComponent's painterly layers - drawing only. The CPU pools' emission, their
// random stream and the thrown volumes are untouched; gt.Spray.Art 0 is the greybox exactly.
//   - One NS_GT_WheelSpray (Art/Unreal/setup_wheel_spray.py) per wheel at its contact: MudDroplets, GravelGrit, GravelDust, their
//     User rates set every tick from the wheel's kind and factors, in noise-driven bursts.
//   - The Mud kind's blobs drawn as the eight P1b clumps (M_GT_SprayClump, the slice of the patch each left).
#include "Vehicle/GTSprayComponent.h"
#include "Terrain/GTMudRunnerWheelEffects.h"
#include "Vehicle/GTMudFlickLab.h"

#include "Core/GTGameplayTags.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Vehicle/GTTractionComponent.h"
#include "Weather/GTWeatherSubsystem.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstanceController.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraEmitterInstance.h"

namespace GTSprayArt
{
	static TAutoConsoleVariable<int32> CVarArt(TEXT("gt.Spray.Art"), 1,
		TEXT("Wheel spray P2: 1 the painterly spray (Niagara droplets, grit and dust; the mud blobs drawn as clumps; no grey dust on gravel), 0 the greybox exactly."),
		ECVF_Default);
	static TAutoConsoleVariable<int32> CVarFine(TEXT("gt.Spray.Fine"), 1,
		TEXT("Wheel spray P2: 0 turns the Niagara layers (MudDroplets, GravelGrit, GravelDust) off; the clumps stay."), ECVF_Default);
	static TAutoConsoleVariable<float> CVarFineScale(TEXT("gt.Spray.FineScale"), 1.f,
		TEXT("Wheel spray P2: the multiplier on the three Niagara rates (default 1)."), ECVF_Default);
	static TAutoConsoleVariable<int32> CVarLazyFineActivation(TEXT("gt.Spray.LazyFineActivation"), 1,
		TEXT("Defer an inactive fine-spray system until it has a positive emission rate. Active systems retain their normal updates and particle tails. 0 restores eager activation."), ECVF_Default);

	static const TCHAR* SystemPath = TEXT("/Game/GrandTour/FX/NS_GT_WheelSpray.NS_GT_WheelSpray");
	static const FName MudRateName(TEXT("User.MudRate"));
	static const FName GritRateName(TEXT("User.GritRate"));
	static const FName DustRateName(TEXT("User.DustRate"));
	static const FName BaseVelocityName(TEXT("User.BaseVelocity"));
	static const FName MudTintName(TEXT("User.MudTint"));
	static const FName GritTintAName(TEXT("User.GritTintA"));
	static const FName GritTintBName(TEXT("User.GritTintB"));
	static const FName DustTintName(TEXT("User.DustTint"));
	static const FName ClumpSeedName(TEXT("User.ClumpSeed"));
	static const FName GritSizeMinName(TEXT("User.GritSizeMin"));
	static const FName GritSizeSpanName(TEXT("User.GritSizeSpan"));
	/** Benmore B1c: on a bGravelSpray surface the grit is 1.5-4 cm (min + span; the system's own 1-3 elsewhere) and its rate x1.5. */
	static constexpr float SurfaceGritSizeMin = 1.5f;
	static constexpr float SurfaceGritSizeSpan = 2.5f;
	static constexpr float SurfaceGritRateScale = 1.5f;
	// Authored road aggregate must remain readable through its existing dust.
	static constexpr float AuthoredGritSizeMin = 2.5f;
	static constexpr float AuthoredGritSizeSpan = 3.5f;
	/** P2d: the Water ISM's custom data - Codex's 0 (opacity) and 1 (family), then the muddy splash's 2 weight, 3-5 tint, 6 turbidity. */
	static constexpr int32 WaterCustomFloats = 7;
	static constexpr int32 Clumps = 8;
	/** The P1b strings (stretched along their flight); the others tumble. */
	static bool IsString(int32 Clump) { return Clump == 1 || Clump == 4 || Clump == 6; }

	// The ground's palette (Art/Export/WheelSpray/manifest.json palette_linear, from the bakes): the bog slices' means (dry; x0.8 wet)
	// in EGTMudVariant order (Standard, Firm, Deep, Stony), and DG1b's Loose stone faces and matrix.
	static const FLinearColor BogMeans[4] = {
		FLinearColor(0.0705f, 0.0401f, 0.0186f), FLinearColor(0.0873f, 0.0584f, 0.0336f),
		FLinearColor(0.0491f, 0.0290f, 0.0134f), FLinearColor(0.0691f, 0.0441f, 0.0227f) };
	static const FLinearColor GritTintA(0.1582f, 0.1844f, 0.1933f);
	static const FLinearColor GritTintB(0.2941f, 0.2933f, 0.2617f);
	static const FLinearColor DustTint(0.2193f, 0.2292f, 0.2113f);

	/** Benmore B1b: a surface's spray tint where it is set (any channel over zero), else the code's own default. */
	static FLinearColor TintOr(const FLinearColor& Set, const FLinearColor& Default)
	{
		return (Set.R > 0.f || Set.G > 0.f || Set.B > 0.f) ? FLinearColor(Set.R, Set.G, Set.B, 1.f) : Default;
	}

	static uint32 Hash(uint32 X)
	{
		X ^= X >> 16;
		X *= 0x7feb352du;
		X ^= X >> 15;
		X *= 0x846ca68bu;
		X ^= X >> 16;
		return X;
	}

	static float Unit(uint32 X)
	{
		return static_cast<float>(Hash(X) & 0xFFFFFFu) / 16777216.f;
	}

	/** A noise lattice value 0..1: each block of 16 cells holds the 16 strata once, in its own shuffled order, jittered inside
	 *  the stratum - irregular in time, yet any few seconds' mean is close to the long-run mean (no lucky dry minute). */
	static float Level(uint32 Seed, int64 Cell)
	{
		const int64 Block = Cell >= 0 ? Cell / 16 : (Cell - 15) / 16;
		const int32 Slot = static_cast<int32>(Cell - Block * 16);
		int32 Perm[16];
		for (int32 I = 0; I < 16; ++I)
		{
			Perm[I] = I;
		}
		const uint32 B = Hash(Seed ^ static_cast<uint32>(Block * 0x9E3779B1ll));
		for (int32 I = 15; I > 0; --I)
		{
			const int32 J = static_cast<int32>(Hash(B + static_cast<uint32>(I) * 0x85EBCA6Bu) % static_cast<uint32>(I + 1));
			Swap(Perm[I], Perm[J]);
		}
		return (static_cast<float>(Perm[Slot]) + Unit(B ^ (static_cast<uint32>(Slot) * 0xC2B2AE35u))) / 16.f;
	}

	/** A smooth noise at one lattice cell per unit of T (smoothstep between the levels). */
	static float Noise(uint32 Seed, double T)
	{
		const double F = FMath::FloorToDouble(T);
		const float A = static_cast<float>(T - F);
		const float S = A * A * (3.f - 2.f * A);
		const int64 C = static_cast<int64>(F);
		return FMath::Lerp(Level(Seed, C), Level(Seed, C + 1), S);
	}

	static float RawBurst(float N)
	{
		const float V = 0.3f + 1.4f * N;
		return V * V;
	}

	/** The long-run mean of RawBurst(Noise), measured once (2048 blocks, 8 samples a cell). */
	static float BurstMean()
	{
		static const float Mean = []()
		{
			double Sum = 0.0;
			const int32 Cells = 2048 * 16;
			for (int32 C = 0; C < Cells; ++C)
			{
				for (int32 K = 0; K < 8; ++K)
				{
					Sum += RawBurst(Noise(0x5EED5EEDu, C + (K + 0.5) / 8.0));
				}
			}
			return static_cast<float>(Sum / (Cells * 8.0));
		}();
		return Mean;
	}
}

bool UGTSprayComponent::IsArtEnabled()
{
	return GTSprayArt::CVarArt.GetValueOnAnyThread() != 0;
}

bool UGTSprayComponent::IsFineEnabled()
{
	return GTSprayArt::CVarFine.GetValueOnAnyThread() != 0;
}

UGTSprayComponent::FFineRates UGTSprayComponent::FineRates(bool bMud, float MudKindRate, bool bGravel, float SpeedFactor, float SlipFactor, float Wetness,
	float Burst, bool bFine, float FineScale, float MudPerRate, float GritPerFactor, float DustPerFactor)
{
	FFineRates R;
	if (!bFine)
	{
		return R;
	}
	const float K = FMath::Max(0.f, FineScale) * FMath::Max(0.f, Burst);
	if (bMud)
	{
		R.Mud = FMath::Max(0.f, MudPerRate) * FMath::Max(0.f, MudKindRate) * K;
	}
	if (bGravel)
	{
		const float F = FMath::Clamp(FMath::Max(SpeedFactor, SlipFactor), 0.f, 1.f);
		R.Grit = FMath::Max(0.f, GritPerFactor) * F * K;
		// The plan's (1 - wetness), reaching 0 at wetness 0.6 as it asks: 1 - wetness / 0.6.
		R.Dust = FMath::Max(0.f, DustPerFactor) * F * FMath::Clamp(1.f - Wetness / 0.6f, 0.f, 1.f) * K;
	}
	return R;
}

float UGTSprayComponent::BurstFactor(int32 Wheel, double TimeS, float Hz)
{
	const uint32 Seed = GTSprayArt::Hash(0x5EED5EEDu + static_cast<uint32>(Wheel) * 0x9E3779B9u);
	return GTSprayArt::RawBurst(GTSprayArt::Noise(Seed, TimeS * FMath::Max(0.01f, Hz))) / GTSprayArt::BurstMean();
}

int32 UGTSprayComponent::ClumpMeshFor(uint32 ParticleId)
{
	return static_cast<int32>(GTSprayArt::Hash(ParticleId * 2654435761u + 0x9E37u) % GTSprayArt::Clumps);
}

FLinearColor UGTSprayComponent::MudTintFor(int32 VariantSlice)
{
	const int32 Slice = FMath::Clamp(VariantSlice, 0, 3);
	FLinearColor Tint = GTSprayArt::BogMeans[Slice] * (Slice == 2 ? 1.f : 0.8f);   // P2d: Deep exempt from the wet x0.8
	Tint.A = 1.f;
	return Tint;
}

const UGTSurfacePhysMaterial* UGTSprayComponent::GravelSpraySurface(const FWheelStatus& Contact)
{
	const UGTSurfacePhysMaterial* Surface = Contact.bInContact ? Cast<UGTSurfacePhysMaterial>(Contact.PhysMaterial.Get()) : nullptr;
	return (Surface && Surface->bGravelSpray && !UGTMudSubsystem::IsInLiveMudZone(Contact.ContactPoint)) ? Surface : nullptr;   // Benmore B2c: no grit in a live mud zone
}

bool UGTSprayComponent::IsGravelContact(const FGTWheelTraction& Wheel, bool bLegacyGravel)
{
    const bool Gravel=Wheel.AuthoredSurface.IsNone() ? Wheel.bInGravelPatch || bLegacyGravel : Wheel.AuthoredSurface==TEXT("Gravel");
    return Wheel.bInContact && Gravel && !Wheel.bInMudPatch && !Wheel.bInSnowPatch
        && FMath::Max(Wheel.WaterDepthM*100.f,Wheel.GroundWaterDepthCm)<=2.5f;
}

void UGTSprayComponent::BeginArt(USceneComponent* Root)
{
	AActor* Owner = GetOwner();
	ClumpMeshes.Reset();
	ClumpLengthCm.Reset();
	FineSystem = nullptr;
	// P2d muddy rut splash: room on the Water ISM for its custom data 2-6 (zeros: the clean splash, exactly as before).
	const int32 WaterKind = static_cast<int32>(EGTSprayKind::Water);
	if (Meshes.IsValidIndex(WaterKind) && Meshes[WaterKind] && Meshes[WaterKind]->NumCustomDataFloats < GTSprayArt::WaterCustomFloats)
	{
		Meshes[WaterKind]->SetNumCustomDataFloats(GTSprayArt::WaterCustomFloats);
	}
	if (!FApp::CanEverRender())
	{
		// -NullRHI (the headless drive tests): nothing would draw, so no Niagara and no clumps; the CPU pools run as ever
		// (gt.Spray.Art still stops a gravel patch's grey dust).
		return;
	}
	FineSystem = LoadObject<UNiagaraSystem>(nullptr, GTSprayArt::SystemPath);
	if (!FineSystem)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTSprayComponent: no NS_GT_WheelSpray (Art/setup_wheel_spray.ps1); no painterly spray"));
	}
	for (int32 K = 0; K < GTSprayArt::Clumps; ++K)
	{
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/GrandTour/FX/Clumps/SM_GT_SprayClump_%d.SM_GT_SprayClump_%d"), K, K));
		if (!Mesh)
		{
			UE_LOG(LogTemp, Warning, TEXT("UGTSprayComponent: no SM_GT_SprayClump_%d (Art/setup_wheel_spray.ps1); the mud blobs stay spheres"), K);
			for (UInstancedStaticMeshComponent* Made : ClumpMeshes)
			{
				Made->DestroyComponent();
			}
			ClumpMeshes.Reset();
			ClumpLengthCm.Reset();
			break;
		}
		UInstancedStaticMeshComponent* Ism = NewObject<UInstancedStaticMeshComponent>(Owner, *FString::Printf(TEXT("Spray_MudClump_%d"), K), RF_Transient);
		Ism->SetStaticMesh(Mesh);
		Ism->NumCustomDataFloats = 1;   // the slice (M_GT_SprayClump's PerInstanceCustomData 0)
		Ism->SetMobility(EComponentMobility::Movable);
		Ism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Ism->SetCastShadow(false);
		Ism->bAffectDynamicIndirectLighting = false;   // BO2: out of the Lumen scene
		Ism->bVisibleInRayTracing = false;             // BO2: out of the ray-tracing scene
		Ism->bAffectDistanceFieldLighting = false;
		Ism->bReceivesDecals = false;
		Ism->SetupAttachment(Root);
		Ism->SetUsingAbsoluteLocation(true);
		Ism->SetUsingAbsoluteRotation(true);
		Ism->SetUsingAbsoluteScale(true);
		Ism->SetWorldTransform(FTransform::Identity);
		Ism->RegisterComponent();
		ClumpTransforms[K].Init(FTransform(FRotator::ZeroRotator, FVector(0.f, 0.f, -100000.f), FVector::ZeroVector), PoolPerKind);
		Ism->AddInstances(ClumpTransforms[K], false, true);
		ClumpMeshes.Add(Ism);
		ClumpLengthCm.Add(FMath::Max(0.1f, 2.f * static_cast<float>(Mesh->GetBounds().BoxExtent.GetMax())));
	}
}

void UGTSprayComponent::UpdateArt(float DeltaSeconds, const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move,
	float ForwardSpeed, float SpeedFactor)
{
	AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	const int32 NumWheels = FMath::Min(Traction.Wheels.Num(), Move.GetNumWheels());
	if (FineSpray.Num() != NumWheels)
	{
		for (UNiagaraComponent* Old : FineSpray)
		{
			if (Old)
			{
				Old->DestroyComponent();
			}
		}
		FineSpray.Reset();
		if (UNiagaraSystem* System = FineSystem)
		{
			for (int32 Index = 0; Index < NumWheels; ++Index)
			{
				UNiagaraComponent* Nc = NewObject<UNiagaraComponent>(Owner, *FString::Printf(TEXT("Spray_Fine_%d"), Index), RF_Transient);
				Nc->SetAsset(System);
				Nc->SetAutoActivate(false);
				Nc->SetupAttachment(Owner->GetRootComponent());
				Nc->SetUsingAbsoluteLocation(true);
				Nc->SetUsingAbsoluteRotation(true);   // world-aligned: the cone axis is BaseVelocity's world direction
				Nc->SetUsingAbsoluteScale(true);
				Nc->SetWorldTransform(FTransform::Identity);
				Nc->RegisterComponent();
				FineSpray.Add(Nc);
			}
		}
		else
		{
			FineSpray.SetNum(NumWheels);   // nulls: no system
		}
	}
	FineRateNow.Init(0.f, NumWheels * 3);
	FineBaseVelocity.Init(FVector::ZeroVector, NumWheels);
	StampWaterMud(Traction, Move);
	const bool bFine = IsArtEnabled() && IsFineEnabled();
	const float FineScale = GTSprayArt::CVarFineScale.GetValueOnGameThread();
	const UGTWeatherSubsystem* Weather = World ? World->GetSubsystem<UGTWeatherSubsystem>() : nullptr;
	const UGTMudSubsystem* MudPatches = World ? World->GetSubsystem<UGTMudSubsystem>() : nullptr;
	const float Wetness = Weather ? Weather->GetWetness() : 0.f;
	const double Now = World ? World->GetTimeSeconds() : 0.0;
	const FVector Forward = Owner->GetActorForwardVector();
	const FVector CarVelocity = Owner->GetVelocity();
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		UNiagaraComponent* Nc = FineSpray[Index];
		if (!Nc)
		{
			continue;
		}
		if (!bFine)
		{
			if (Nc->IsActive())
			{
				Nc->DeactivateImmediate();   // off is off: no droplets left hanging (gt.Spray.Art 0 is the greybox exactly)
			}
			continue;
		}
		const FGTWheelTraction& Wheel = Traction.Wheels[Index];
		const bool bMud = Wheel.bInContact && (Wheel.SurfaceTag == GTTags::Surface_Mud.GetTag() || Wheel.SurfaceTag == GTTags::Surface_Bog.GetTag());
		// Benmore B1b: the contact's physical material - one with bGravelSpray throws the grit and dust as a gravel patch does, in its
		// own tints where they are set.
		const UGTSurfacePhysMaterial* GravelSurface = GravelSpraySurface(Move.GetWheelState(Index));
		const bool bGravel = IsGravelContact(Wheel,GravelSurface!=nullptr);
		const bool AuthoredGravel = bGravel && Wheel.AuthoredSurface==TEXT("Gravel");
		// The CPU Mud kind's own rate on this wheel (Update's MudRate x min(1, speed + spin)), and the Dust kind's factors.
		const float Spin = Wheel.bSlipping ? FMath::Clamp(Wheel.SlipMagnitude / 300.f, 0.f, 1.f) : 0.f;
		const float MudKindRate = bMud ? MudRate * FMath::Min(1.f, SpeedFactor + Spin) : 0.f;
		FFineRates R = FineRates(bMud, MudKindRate, bGravel, SpeedFactor, Spin, FMath::Max(Wetness,Wheel.GroundWetness), BurstFactor(Index, Now, BurstHz), true, FineScale,
			FineMudPerRate, FineGritPerFactor, FineDustPerFactor);
		if (bGravel && (GravelSurface || AuthoredGravel))
		{
			R.Grit *= GTSprayArt::SurfaceGritRateScale;
		}
        if (bExternalDustEffects) R.Dust = 0.f;
        if ((bExternalMudEffects && AGTMudFlickLab::CoversWheel(Wheel)) || AGTMudRunnerWheelEffects::IsActive(this)) R.Mud = 0.f;
		// Mud roads (MRD1 item 4, wired in B1b): a patch whose MudRoadSprayScale is over 1 throws that much more fine mud.
		if (R.Mud > 0.f && Wheel.bInPatchBox && MudPatches)
		{
			const FVector Contact = Move.GetWheelState(Index).ContactPoint;
			const AGTMudPatch* Patch = MudPatches->PatchAt(FVector2D(Contact.X, Contact.Y));
			if (Patch && Patch->MudRoadSprayScale > 1.f)
			{
				R.Mud *= Patch->MudRoadSprayScale;
			}
		}
		FineRateNow[Index * 3 + 0] = R.Mud;
		FineRateNow[Index * 3 + 1] = R.Grit;
		FineRateNow[Index * 3 + 2] = R.Dust;
		// Where and how the CPU throw sends its blobs (SpawnThrown's mean): back from the spin's own direction, up, a share of
		// the car's own speed.
		const float SlipCm = Wheel.SlipMagnitude;
		const float SpinCm = FMath::Abs(SlipCm);
		const float SpinSign = SpinCm > 1.f ? FMath::Sign(SlipCm) : (ForwardSpeed >= 0.f ? 1.f : -1.f);
		FVector Back = -Forward * SpinSign;
		FVector Base = Back * (0.45f * FMath::Abs(ForwardSpeed) + 0.6f * ThrowBackPerSpin * SpinCm)
			+ FVector(0.f, 0.f, 250.f + ThrowUpPerSpin * SpinCm) + CarVelocity * 0.2f;
		if (AuthoredGravel)
		{
			FVector Heading(Wheel.TyreHeading.X,Wheel.TyreHeading.Y,0.f);
			if(!Heading.Normalize())Heading=Forward;
			// Braking slip has the opposite sign to tread travel; it must not
			// throw chips forward. Front-wheel fans follow their steering angle.
			const float Travel=FMath::Abs(Wheel.TreadCmPerS)>10.f ? Wheel.TreadCmPerS : FVector::DotProduct(CarVelocity,Heading);
			Back=-Heading*FMath::Sign(Travel);
			Base=CarVelocity*.2f+Back*FMath::Min(1000.f,.45f*FMath::Abs(Travel)+.3f*SpinCm)
				+FVector(0,0,300.f+FMath::Min(170.f,SpinCm*.1f));
		}
		// Where the mud leaves the tyre: behind it at about hub height (P2b; P2 25 cm up), clear of the tyre's own surface and of the
		// mud piled behind it (a droplet born inside either's depth meets it at once and dies on the depth-buffer collision).
		FineBaseVelocity[Index] = Base;
		// With no particles and no requested emission there is no system to tick
		// or parameter buffer to upload. Never interrupt an already active system:
		// its existing particles, update timing and natural tails remain intact.
		if (GTSprayArt::CVarLazyFineActivation.GetValueOnGameThread() != 0 && !Nc->IsActive()
			&& R.Mud <= 0.f && R.Grit <= 0.f && R.Dust <= 0.f)
		{
			continue;
		}
		Nc->SetWorldLocation(Move.GetWheelState(Index).ContactPoint + Back * 50.f + FVector(0.f, 0.f, 40.f));
		Nc->SetVariableFloat(GTSprayArt::ClumpSeedName, static_cast<float>(Index + 1));
		Nc->SetVariableFloat(GTSprayArt::MudRateName, R.Mud);
		Nc->SetVariableFloat(GTSprayArt::GritRateName, R.Grit);
		Nc->SetVariableFloat(GTSprayArt::DustRateName, R.Dust);
		Nc->SetVariableFloat(GTSprayArt::GritSizeMinName, AuthoredGravel ? GTSprayArt::AuthoredGritSizeMin : GravelSurface ? GTSprayArt::SurfaceGritSizeMin : 1.f);
		Nc->SetVariableFloat(GTSprayArt::GritSizeSpanName, AuthoredGravel ? GTSprayArt::AuthoredGritSizeSpan : GravelSurface ? GTSprayArt::SurfaceGritSizeSpan : 2.f);
		Nc->SetVariableVec3(GTSprayArt::BaseVelocityName, Base);
		Nc->SetVariableLinearColor(GTSprayArt::MudTintName, MudTintFor(Wheel.PatchVariant));
		Nc->SetVariableLinearColor(GTSprayArt::GritTintAName, GravelSurface ? GTSprayArt::TintOr(GravelSurface->SprayTintA, GTSprayArt::GritTintA) : GTSprayArt::GritTintA);
		Nc->SetVariableLinearColor(GTSprayArt::GritTintBName, GravelSurface ? GTSprayArt::TintOr(GravelSurface->SprayTintB, GTSprayArt::GritTintB) : GTSprayArt::GritTintB);
		Nc->SetVariableLinearColor(GTSprayArt::DustTintName, GravelSurface ? GTSprayArt::TintOr(GravelSurface->DustTint, GTSprayArt::DustTint) : GTSprayArt::DustTint);
		if (!Nc->IsActive())
		{
			// Populate parameters before activation so the first frame uses the
			// current wheel contact, launch velocity, tint and emission rates.
			Nc->Activate(true);
		}
	}
}

bool UGTSprayComponent::PushClumps()
{
	if (ClumpMeshes.Num() != GTSprayArt::Clumps)
	{
		ClumpsDrawn = 0;
		return false;
	}
	const FTransform Hidden(FRotator::ZeroRotator, FVector(0.f, 0.f, -100000.f), FVector::ZeroVector);
	if (!IsArtEnabled())
	{
		if (bArtDrawn)
		{
			for (int32 K = 0; K < GTSprayArt::Clumps; ++K)
			{
				for (FTransform& T : ClumpTransforms[K])
				{
					T = Hidden;
				}
				ClumpMeshes[K]->BatchUpdateInstancesTransforms(0, ClumpTransforms[K], true, false, true);
			}
		}
		ClumpsDrawn = 0;
		return false;
	}
	const TArray<FParticle>& Pool = Particles[static_cast<int32>(EGTSprayKind::Mud)];
	// The previous nonempty frame still takes the clearing path below. Once
	// retired, all eight clump pools are already hidden: no repeat uploads.
	if (UseSparseRenderUpdates() && Pool.IsEmpty() && ClumpsDrawn == 0)
	{
		return true;
	}
	for (int32 K = 0; K < GTSprayArt::Clumps; ++K)
	{
		for (FTransform& T : ClumpTransforms[K])
		{
			T = Hidden;
		}
	}
	ClumpsDrawn = 0;
	for (int32 Index = 0; Index < Pool.Num() && Index < PoolPerKind; ++Index)
	{
		const FParticle& P = Pool[Index];
		const int32 K = ClumpMeshFor(P.Id);
		// The blob's size as the sphere had it (its growth included), as the clump's longest side.
		const float SizeCm = P.Size * (1.f + P.Growth * P.Life / FMath::Max(P.MaxLife, 0.01f));
		const float S = SizeCm / ClumpLengthCm[K];
		FQuat Rotation;
		FVector Scale(S);
		if (GTSprayArt::IsString(K))
		{
			// A string stretches x1.5 along its flight (its long side is the mesh's X).
			const FVector Dir = P.Velocity.IsNearlyZero() ? FVector::ForwardVector : P.Velocity.GetSafeNormal();
			Rotation = FRotationMatrix::MakeFromX(Dir).ToQuat();
			Scale.X *= 1.5f;
		}
		else
		{
			// The others tumble: a random axis, 2-8 rev/s, a random start.
			const FVector Axis = FVector(GTSprayArt::Unit(P.Id * 3u + 1u) - 0.5f, GTSprayArt::Unit(P.Id * 3u + 2u) - 0.5f,
				GTSprayArt::Unit(P.Id * 3u + 3u) - 0.5f).GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
			const float Rev = 2.f + 6.f * GTSprayArt::Unit(P.Id * 7u + 5u);
			const float Angle = UE_TWO_PI * (Rev * P.Life + GTSprayArt::Unit(P.Id * 11u + 9u));
			Rotation = FQuat(Axis, Angle);
		}
		ClumpTransforms[K][Index] = FTransform(Rotation, P.Position, Scale);
		ClumpMeshes[K]->SetCustomDataValue(Index, 0, static_cast<float>(P.Slice), false);
		++ClumpsDrawn;
	}
	for (int32 K = 0; K < GTSprayArt::Clumps; ++K)
	{
		ClumpMeshes[K]->BatchUpdateInstancesTransforms(0, ClumpTransforms[K], true, false, true);
	}
	return true;
}

void UGTSprayComponent::StampWaterMud(const UGTTractionComponent& Traction, const UChaosWheeledVehicleMovementComponent& Move)
{
	// The Water kind's new particles (SpawnWater gives them no id) take the mud of the wheel they left: the nearest contact within
	// 1.2 m (the bow spray is further from every contact and stays clean). In a Mud patch the colour is the variant's MudTint at a
	// weight sqrt(turbidity), at least 0.6; outside one, nothing (the clean splash, exactly as before). Off at gt.Spray.Art 0.
	TArray<FParticle>& Pool = Particles[static_cast<int32>(EGTSprayKind::Water)];
	UGTMudSubsystem* Mud = GetWorld() ? GetWorld()->GetSubsystem<UGTMudSubsystem>() : nullptr;
	const bool bArt = IsArtEnabled();
	const int32 NumWheels = FMath::Min(Traction.Wheels.Num(), Move.GetNumWheels());
	for (FParticle& P : Pool)
	{
		if (P.Id != 0)
		{
			continue;
		}
		P.Id = NextParticleId++;
		if (!bArt || !Mud)
		{
			continue;
		}
		int32 Best = INDEX_NONE;
		double BestD2 = FMath::Square(120.0);
		for (int32 W = 0; W < NumWheels; ++W)
		{
			if (!Traction.Wheels[W].bInContact)
			{
				continue;
			}
			const FVector C = Move.GetWheelState(W).ContactPoint;
			const double D2 = FVector2D::DistSquared(FVector2D(C.X, C.Y), FVector2D(P.Position.X, P.Position.Y));
			if (D2 < BestD2)
			{
				BestD2 = D2;
				Best = W;
			}
		}
		if (Best == INDEX_NONE)
		{
			continue;
		}
		const FVector C = Move.GetWheelState(Best).ContactPoint;
		const AGTMudPatch* Patch = Mud->PatchAt(FVector2D(C.X, C.Y));
		if (!Patch || Patch->Medium != EGTDeformMedium::Mud)
		{
			continue;
		}
		P.MudTurbidity = FMath::Clamp(Patch->TurbidityAt(FVector2D(C.X, C.Y)), 0.f, 1.f);
		P.MudShare = FMath::Max(0.6f, FMath::Sqrt(P.MudTurbidity));
		P.MudTint = MudTintFor(static_cast<int32>(Patch->MudVariant));
	}
}

void UGTSprayComponent::PushWaterMud()
{
	const int32 K = static_cast<int32>(EGTSprayKind::Water);
	UInstancedStaticMeshComponent* Ism = Meshes.IsValidIndex(K) ? Meshes[K].Get() : nullptr;
	MuddySplashCount = 0;
	if (!Ism || Ism->NumCustomDataFloats < GTSprayArt::WaterCustomFloats || Ism->GetInstanceCount() <= 0)
	{
		return;
	}
	const TArray<FParticle>& Pool = Particles[K];
	const int32 Capacity = FMath::Min(Ism->GetInstanceCount(), PoolPerKind);
	const int32 LiveCount = FMath::Min(Pool.Num(), Capacity);
	// Match the transform upload's sparse prefix. Clear expired slots once,
	// then leave the already-zero tail alone, including entirely idle vehicles.
	// This changes only rendering uploads; particles and mud transfer still run.
	const int32 N = UseSparseRenderUpdates()
		? FMath::Min(FMath::Max(LiveCount, SubmittedWaterMudCount), Capacity) : Capacity;
	bool bAny = false;
	for (int32 I = 0; I < N; ++I)
	{
		const FParticle* P = I < Pool.Num() ? &Pool[I] : nullptr;
		const float Share = P ? P->MudShare : 0.f;
		bAny |= Share > 0.f;
		MuddySplashCount += Share > 0.f ? 1 : 0;
		Ism->SetCustomDataValue(I, 2, Share, false);
		Ism->SetCustomDataValue(I, 3, P ? P->MudTint.R : 0.f, false);
		Ism->SetCustomDataValue(I, 4, P ? P->MudTint.G : 0.f, false);
		Ism->SetCustomDataValue(I, 5, P ? P->MudTint.B : 0.f, false);
		Ism->SetCustomDataValue(I, 6, P ? P->MudTurbidity : 0.f, false);
	}
	if (bAny || bWaterMudDrawn)
	{
		Ism->MarkRenderInstancesDirty();   // BO2: custom data only; no proxy recreate
	}
	bWaterMudDrawn = bAny;
	SubmittedWaterMudCount = LiveCount;
}

int32 UGTSprayComponent::GetNiagaraLiveCount(UNiagaraComponent* Component, int32 Emitter)
{
	if (!Component)
	{
		return 0;
	}
	FNiagaraSystemInstanceControllerConstPtr Controller = Component->GetSystemInstanceController();
	const FNiagaraSystemInstance* Instance = Controller.IsValid() ? Controller->GetSystemInstance_Unsafe() : nullptr;
	return Instance && Instance->GetEmitters().IsValidIndex(Emitter) ? Instance->GetEmitters()[Emitter]->GetNumParticles() : 0;
}

int32 UGTSprayComponent::GetFineLiveCount(int32 Emitter) const
{
	int32 Total = 0;
	for (UNiagaraComponent* Nc : FineSpray)
	{
		Total += GetNiagaraLiveCount(Nc, Emitter);
	}
	return Total;
}

float UGTSprayComponent::GetFineRate(int32 Wheel, int32 Emitter) const
{
	const int32 I = Wheel * 3 + Emitter;
	return Emitter >= 0 && Emitter < 3 && FineRateNow.IsValidIndex(I) ? FineRateNow[I] : 0.f;
}
