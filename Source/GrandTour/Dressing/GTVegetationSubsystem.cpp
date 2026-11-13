#include "Dressing/GTVegetationSubsystem.h"

#include "Components/CapsuleComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Materials/MaterialInterface.h"
#include "PhysicsEngine/BodySetup.h"

namespace GTVeg
{
	const FName TagBrush(TEXT("GTVeg.Soft.Brush"));
	const FName TagSapling(TEXT("GTVeg.Soft.Sapling"));
	const FName TagYoung(TEXT("GTVeg.Soft.Young"));
	constexpr double LogEverySeconds = 5.0;
	constexpr float GravityMs2 = 9.81f;

	bool ClassFromTags(const UActorComponent& Component, EGTVegClass& OutClass)
	{
		for (const FName& Tag : Component.ComponentTags)
		{
			if (Tag == TagBrush)
			{
				OutClass = EGTVegClass::Brush;
				return true;
			}
			if (Tag == TagSapling)
			{
				OutClass = EGTVegClass::Sapling;
				return true;
			}
			if (Tag == TagYoung)
			{
				OutClass = EGTVegClass::Young;
				return true;
			}
		}
		return false;
	}

	/** gt.Look.Dressing (owned by UGTLookSubsystem); 1 when it does not exist. */
	int32 Dressing()
	{
		static IConsoleVariable* Var = nullptr;
		if (!Var)
		{
			Var = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Look.Dressing"));
		}
		return Var ? Var->GetInt() : 1;
	}

	FVector Horizontal(const FVector& V)
	{
		return FVector(V.X, V.Y, 0.0).GetSafeNormal();
	}

	static FAutoConsoleCommandWithWorld CmdReindex(
		TEXT("gt.Veg.Reindex"),
		TEXT("Leg dressing LD5: rebuild the soft vegetation index (every GTVeg.Soft.* ISM in the world), everything restored first."),
		FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
		{
			if (UGTVegetationSubsystem* Veg = World ? World->GetSubsystem<UGTVegetationSubsystem>() : nullptr)
			{
				Veg->Reindex();
			}
		}));

	static FAutoConsoleCommandWithWorld CmdStats(
		TEXT("gt.Veg.Stats"),
		TEXT("Leg dressing LD5: log the soft vegetation index, the active set, the debris and the per-frame work."),
		FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
		{
			if (const UGTVegetationSubsystem* Veg = World ? World->GetSubsystem<UGTVegetationSubsystem>() : nullptr)
			{
				float Mean = 0.f;
				float Max = 0.f;
				int32 Frames = 0;
				Veg->GetRollingTickMs(Mean, Max, Frames);
				UE_LOG(LogTemp, Display, TEXT("GTVEG %s; active %d, debris %d in use of %d; work %.3f ms mean, %.3f ms max over %d frames"),
					*Veg->DescribeIndex(), Veg->GetActiveCount(), Veg->GetDebrisInUse(), Veg->GetDebrisActorCount(), Mean, Max, Frames);
			}
		}));
}

// ---- debris ---------------------------------------------------------------------------------------------------------

AGTVegDebrisActor::AGTVegDebrisActor()
{
	PrimaryActorTick.bCanEverTick = false;
	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	Capsule->SetMobility(EComponentMobility::Movable);
	Capsule->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Capsule->SetSimulatePhysics(false);
	Capsule->SetCanEverAffectNavigation(false);
	Capsule->SetGenerateOverlapEvents(false);
	RootComponent = Capsule;
	SetActorHiddenInGame(true);
}

// ---- subsystem ------------------------------------------------------------------------------------------------------

bool UGTVegetationSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGTVegetationSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	bBegun = true;
	Index();
	RollingMs.Reset();
	RollingNext = 0;
	LastLogTime = InWorld.GetTimeSeconds();
	if (Instances.Num() > 0)
	{
		UE_LOG(LogTemp, Display, TEXT("GTVEG %s"), *DescribeIndex());
	}
}

void UGTVegetationSubsystem::Deinitialize()
{
	Slots.Reset();
	Instances.Reset();
	Components.Reset();
	ComponentLookup.Reset();
	Cells.Reset();
	Super::Deinitialize();
}

const TCHAR* UGTVegetationSubsystem::ClassName(EGTVegClass Class)
{
	switch (Class)
	{
	case EGTVegClass::Sapling: return TEXT("Sapling");
	case EGTVegClass::Young: return TEXT("Young");
	default: return TEXT("Brush");
	}
}

FIntPoint UGTVegetationSubsystem::CellOf(const FVector& Location) const
{
	return FIntPoint(FMath::FloorToInt32(Location.X / CellCm), FMath::FloorToInt32(Location.Y / CellCm));
}

void UGTVegetationSubsystem::ClearIndex()
{
	Instances.Reset();
	Components.Reset();
	ComponentLookup.Reset();
	Cells.Reset();
	OriginalLocal.Reset();
	MaxRadiusCm = 0.f;
	SkippedHidden = 0;
}

void UGTVegetationSubsystem::Index()
{
	ClearIndex();
	CellCm = FMath::Max(50.f, GetDefault<UGTVegetationSettings>()->HashCellCm);
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		TArray<UInstancedStaticMeshComponent*> Isms;
		It->GetComponents<UInstancedStaticMeshComponent>(Isms);
		for (UInstancedStaticMeshComponent* Ism : Isms)
		{
			IndexComponentInternal(Ism);
		}
	}
}

int32 UGTVegetationSubsystem::Reindex()
{
	RestoreAll();
	Index();
	UE_LOG(LogTemp, Display, TEXT("GTVEG reindexed: %s"), *DescribeIndex());
	return Instances.Num();
}

bool UGTVegetationSubsystem::IndexComponent(UInstancedStaticMeshComponent* Component)
{
	const int32 Added = IndexComponentInternal(Component);
	if (Added > 0)
	{
		UE_LOG(LogTemp, Display, TEXT("GTVEG indexed %s: %d instance(s); %s"), *GetNameSafe(Component), Added, *DescribeIndex());
	}
	return Added > 0;
}

int32 UGTVegetationSubsystem::IndexComponentInternal(UInstancedStaticMeshComponent* Ism)
{
	EGTVegClass Class = EGTVegClass::Brush;
	if (!Ism || Ism->GetWorld() != GetWorld() || !GTVeg::ClassFromTags(*Ism, Class) || ComponentLookup.Contains(Ism))
	{
		return 0;
	}
	UStaticMesh* Mesh = Ism->GetStaticMesh();
	if (!Mesh)
	{
		return 0;
	}
	const UGTVegetationSettings* Settings = GetDefault<UGTVegetationSettings>();
	const FBoxSphereBounds Bounds = Mesh->GetBounds();
	const double MaxExtentXY = FMath::Max(Bounds.BoxExtent.X, Bounds.BoxExtent.Y);
	const double TopZ = FMath::Max(10.0, Bounds.Origin.Z + Bounds.BoxExtent.Z);
	// Trees bend about the base of their trunk and touch with the trunk: the mesh's trunk capsule (LD4 gives every tree
	// variant one), its XY and its radius.
	FVector TrunkOffset = FVector::ZeroVector;
	double TrunkRadius = -1.0;
	if (Class != EGTVegClass::Brush)
	{
		if (const UBodySetup* Body = Mesh->GetBodySetup())
		{
			if (Body->AggGeom.SphylElems.Num() > 0)
			{
				const FVector Centre = Body->AggGeom.SphylElems[0].Center;
				TrunkOffset = FVector(Centre.X, Centre.Y, 0.0);
				TrunkRadius = Body->AggGeom.SphylElems[0].Radius;
			}
		}
	}

	const int32 ComponentIndex = Components.AddDefaulted();
	FComponent& Entry = Components[ComponentIndex];
	Entry.Ism = Ism;
	Entry.Class = Class;
	Entry.bHism = Ism->IsA<UHierarchicalInstancedStaticMeshComponent>();
	ComponentLookup.Add(Ism, ComponentIndex);

	int32 Added = 0;
	const int32 Count = Ism->GetInstanceCount();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FTransform T;
		if (!Ism->GetInstanceTransform(Index, T, /*bWorldSpace*/ true))
		{
			continue;
		}
		const FVector Scale = T.GetScale3D().GetAbs();
		if (Scale.GetMax() < 1.e-3)
		{
			++SkippedHidden;   // already hidden by someone
			continue;
		}
		FInstance Inst;
		Inst.HeightCm = static_cast<float>(TopZ * Scale.Z);
		const double ScaleXY = FMath::Max(Scale.X, Scale.Y);
		if (Class == EGTVegClass::Brush)
		{
			// v2: the canopy's inner half resists: 0.5 x max(extent X, Y) x the XY scale.
			Inst.RadiusCm = static_cast<float>(Settings->BrushRadiusScale * MaxExtentXY * ScaleXY);
		}
		else
		{
			// v2: the trunk capsule's radius x the XY scale, at least 5 cm.
			const double Radius = TrunkRadius > 0.0 ? TrunkRadius * ScaleXY : Settings->TrunkRadiusPerHeight * Inst.HeightCm;
			Inst.RadiusCm = FMath::Max(Settings->MinTrunkRadiusCm, static_cast<float>(Radius));
		}
		Inst.Pivot = T.TransformPosition(TrunkOffset);
		Inst.Component = ComponentIndex;
		Inst.Index = Index;
		Inst.Class = Class;
		const int32 Id = Instances.Add(Inst);
		Cells.FindOrAdd(CellOf(Inst.Pivot)).Add(Id);
		MaxRadiusCm = FMath::Max(MaxRadiusCm, Inst.RadiusCm);
		++Added;
	}
	return Added;
}

// ---- the probe ------------------------------------------------------------------------------------------------------

FVector UGTVegetationSubsystem::ProbeCar(UPrimitiveComponent& Chassis, const FTransform& CarTransform, const FBox& LocalBodyBox, float CarMassKg,
	float DeltaSeconds, int32& OutContacts)
{
	OutContacts = 0;
	if (!bBegun || !IsActive() || !LocalBodyBox.IsValid)
	{
		return FVector::ZeroVector;
	}
	const double StartSeconds = FPlatformTime::Seconds();
	const UGTVegetationSettings* Settings = GetDefault<UGTVegetationSettings>();
	const double Now = GetWorld()->GetTimeSeconds();
	const uint64 Frame = GFrameCounter;

	const FVector Velocity = Chassis.GetPhysicsLinearVelocity();
	const FVector Planar(Velocity.X, Velocity.Y, 0.0);
	const double SpeedCms = Planar.Size();
	const FVector VelocityDir = SpeedCms > 1.0 ? Planar / SpeedCms : FVector::ZeroVector;
	const FVector CarForward = GTVeg::Horizontal(CarTransform.GetUnitAxis(EAxis::X));
	const FVector CarRight = GTVeg::Horizontal(CarTransform.GetUnitAxis(EAxis::Y));

	// The footprint: the body box plus the pad on every side (XY); its world XY bounds grown by the largest probe
	// radius are the cells to visit.
	const FVector Centre = LocalBodyBox.GetCenter();
	const FVector Half = LocalBodyBox.GetExtent() + FVector(Settings->FootprintPadCm, Settings->FootprintPadCm, 0.0);
	FBox2D Area(ForceInit);
	for (int32 Corner = 0; Corner < 4; ++Corner)
	{
		const FVector Local = Centre + FVector((Corner & 1) ? Half.X : -Half.X, (Corner & 2) ? Half.Y : -Half.Y, 0.0);
		const FVector World = CarTransform.TransformPositionNoScale(Local);
		Area += FVector2D(World.X, World.Y);
	}
	Area = Area.ExpandBy(MaxRadiusCm);
	const FIntPoint Lo = CellOf(FVector(Area.Min.X, Area.Min.Y, 0.0));
	const FIntPoint Hi = CellOf(FVector(Area.Max.X, Area.Max.Y, 0.0));

	FVector ClassForceN[3] = { FVector::ZeroVector, FVector::ZeroVector, FVector::ZeroVector };
	int32 Contacts = 0;
	// v2: s(v) = floor + (1 - floor) x saturate(|v| / full speed).
	const float SpeedFactor = Settings->ResistSpeedFloor + (1.f - Settings->ResistSpeedFloor)
		* FMath::Clamp(static_cast<float>(SpeedCms / 100.0) / Settings->ResistFullSpeedMs, 0.f, 1.f);
	for (int32 CX = Lo.X; CX <= Hi.X; ++CX)
	{
		for (int32 CY = Lo.Y; CY <= Hi.Y; ++CY)
		{
			const TArray<int32>* Cell = Cells.Find(FIntPoint(CX, CY));
			if (!Cell)
			{
				continue;
			}
			for (const int32 Id : *Cell)
			{
				FInstance& Inst = Instances[Id];
				if (Inst.bSnapped)
				{
					continue;
				}
				const FVector L = CarTransform.InverseTransformPositionNoScale(Inst.Pivot) - Centre;
				if (L.Z > Half.Z || L.Z < -Half.Z - Settings->BelowBodyCm)
				{
					continue;   // above the car's body, or on another level of ground far below it
				}
				const double DepthX = Half.X + Inst.RadiusCm - FMath::Abs(L.X);
				const double DepthY = Half.Y + Inst.RadiusCm - FMath::Abs(L.Y);
				if (DepthX <= 0.0 || DepthY <= 0.0)
				{
					continue;
				}
				const float Push = static_cast<float>(FMath::Clamp(FMath::Min(DepthX, DepthY) / Settings->PushDepthCm, 0.0, 1.0));
				++Contacts;
				const FGTVegClassDials& Dials = Settings->ForClass(Inst.Class);
				ClassForceN[static_cast<int32>(Inst.Class)] -= VelocityDir * (Dials.StiffnessN * Push * SpeedFactor);

				// The bend: along the car's horizontal velocity; crawling, away from the car's centreline.
				FVector Dir = VelocityDir;
				if (SpeedCms < Settings->LowSpeedBendMs * 100.0 || Dir.IsNearlyZero())
				{
					Dir = FMath::Abs(L.Y) > 1.0 ? CarRight * FMath::Sign(L.Y) : CarForward;
				}
				if (!Inst.bStatContact)
				{
					Inst.bStatContact = true;
					++Stats.Contacted;
				}
				int32 SlotIndex = Inst.Slot;
				if (SlotIndex == INDEX_NONE)
				{
					SlotIndex = AcquireSlot(Id);
				}
				if (SlotIndex != INDEX_NONE)
				{
					FSlot& Slot = Slots[SlotIndex];
					Slot.Push = Slot.LastContactFrame == Frame ? FMath::Max(Slot.Push, Push) : Push;
					Slot.bContact = true;
					Slot.Dir = Dir;
					Slot.CarSpeedMs = static_cast<float>(SpeedCms / 100.0);
					Slot.CarVelocityDir = VelocityDir.IsNearlyZero() ? CarForward : VelocityDir;
					Slot.Car = &Chassis;
					Slot.LastContactFrame = Frame;
					Slot.ContactEndTime = -1.0;
					Slot.bSettleTimed = false;
				}
			}
		}
	}

	FVector ForceN = FVector::ZeroVector;
	if (Contacts > 0)
	{
		// Each class's sum under its own cap (v2), the total under the total cap, and never more than stops the car's
		// horizontal motion within this step (the force opposes the motion; it never pushes a stopped car backwards).
		const double WeightN = CarMassKg * GTVeg::GravityMs2;
		for (int32 Class = 0; Class < 3; ++Class)
		{
			const double ClassCapN = Settings->ForClass(static_cast<EGTVegClass>(Class)).CapG * WeightN;
			const double ClassMagnitude = ClassForceN[Class].Size();
			if (ClassMagnitude > ClassCapN && ClassMagnitude > 0.0)
			{
				ClassForceN[Class] *= ClassCapN / ClassMagnitude;
			}
			ForceN += ClassForceN[Class];
		}
		const double CapN = Settings->ForceCapG * WeightN;
		const double Magnitude = ForceN.Size();
		if (Magnitude > CapN && Magnitude > 0.0)
		{
			ForceN *= CapN / Magnitude;
		}
		if (DeltaSeconds > 0.f)
		{
			const double StopN = CarMassKg * (SpeedCms / 100.0) / DeltaSeconds;
			if (ForceN.Size() > StopN)
			{
				ForceN = ForceN.GetSafeNormal() * StopN;
			}
		}
		++Stats.ContactFrames;
		Stats.MaxContacts = FMath::Max(Stats.MaxContacts, Contacts);
		Stats.MaxForceN = FMath::Max(Stats.MaxForceN, static_cast<float>(ForceN.Size()));
		if (Stats.FirstContactTime < 0.0)
		{
			Stats.FirstContactTime = Now;
		}
		Stats.LastContactTime = Now;
		bActivitySinceLog = true;
	}
	LastProbeContacts = Contacts;
	LastForceN = static_cast<float>(ForceN.Size());
	OutContacts = Contacts;
	AddFrameWork(FPlatformTime::Seconds() - StartSeconds);
	return ForceN;
}

// ---- the active set -------------------------------------------------------------------------------------------------

int32 UGTVegetationSubsystem::AcquireSlot(int32 InstanceIndex)
{
	const UGTVegetationSettings* Settings = GetDefault<UGTVegetationSettings>();
	if (Slots.Num() >= Settings->PoolSize)
	{
		// The pool is the active set: the oldest instance not touched this frame recovers first.
		int32 Oldest = INDEX_NONE;
		for (int32 Index = 0; Index < Slots.Num(); ++Index)
		{
			if (Slots[Index].LastContactFrame != GFrameCounter && (Oldest == INDEX_NONE || Slots[Index].StartTime < Slots[Oldest].StartTime))
			{
				Oldest = Index;
			}
		}
		if (Oldest == INDEX_NONE)
		{
			++Stats.NoSlot;
			return INDEX_NONE;
		}
		++Stats.Evicted;
		RecoverSlot(Oldest);
	}
	FInstance& Inst = Instances[InstanceIndex];
	UInstancedStaticMeshComponent* Ism = Components[Inst.Component].Ism.Get();
	if (!Ism)
	{
		return INDEX_NONE;
	}
	// The instance's own transform: from the first time it was hidden (the component may hold a pending hide for it).
	FTransform Local;
	if (const FTransform* Known = OriginalLocal.Find(InstanceIndex))
	{
		Local = *Known;
	}
	else if (Ism->GetInstanceTransform(Inst.Index, Local, /*bWorldSpace*/ false))
	{
		OriginalLocal.Add(InstanceIndex, Local);
	}
	else
	{
		return INDEX_NONE;
	}
	const int32 Proxy = AcquireProxy();
	if (Proxy == INDEX_NONE)
	{
		return INDEX_NONE;
	}
	if (ProxyConfiguredFor[Proxy] != Inst.Component)
	{
		ConfigureProxy(Proxy, *Ism);
		ProxyConfiguredFor[Proxy] = Inst.Component;
	}
	FSlot Slot;
	Slot.Instance = InstanceIndex;
	Slot.Proxy = Proxy;
	Slot.Local = Local;
	Slot.World = Local * Ism->GetComponentTransform();
	Slot.StartTime = GetWorld()->GetTimeSeconds();
	UStaticMeshComponent* ProxyComponent = Proxies[Proxy];
	ProxyComponent->SetCastShadow(Settings->bProxyCastsShadow && Ism->CastShadow);   // v2: no shadow while bending
	ProxyComponent->SetWorldTransform(Slot.World, false, nullptr, ETeleportType::TeleportPhysics);
	ProxyComponent->SetVisibility(true);
	FTransform Hidden = Local;
	Hidden.SetScale3D(FVector::ZeroVector);
	QueueInstance(InstanceIndex, Hidden);
	Inst.Slot = Slots.Add(Slot);
	return Inst.Slot;
}

void UGTVegetationSubsystem::RemoveSlot(int32 SlotIndex)
{
	Instances[Slots[SlotIndex].Instance].Slot = INDEX_NONE;
	Slots.RemoveAtSwap(SlotIndex);
	if (SlotIndex < Slots.Num())
	{
		Instances[Slots[SlotIndex].Instance].Slot = SlotIndex;
	}
}

void UGTVegetationSubsystem::RecoverSlot(int32 SlotIndex)
{
	FSlot& Slot = Slots[SlotIndex];
	if (!Slot.bSettleTimed && Slot.ContactEndTime >= 0.0)
	{
		Slot.bSettleTimed = true;
		++Stats.Recovered;
		Stats.MaxRecoverS = FMath::Max(Stats.MaxRecoverS, static_cast<float>(GetWorld()->GetTimeSeconds() - Slot.ContactEndTime));
	}
	QueueInstance(Slot.Instance, Slot.Local);
	ReleaseProxy(Slot.Proxy);
	RemoveSlot(SlotIndex);
}

FTransform UGTVegetationSubsystem::BentTransform(const FSlot& Slot, const FInstance& Inst) const
{
	const FVector Axis = FVector::CrossProduct(FVector::UpVector, Slot.Dir).GetSafeNormal();
	if (Axis.IsNearlyZero() || Slot.TiltRad <= 0.f)
	{
		return Slot.World;
	}
	// A rotation about the pivot that carries the top toward Dir.
	const FQuat Tilt(Axis, Slot.TiltRad);
	FTransform Out = Slot.World;
	Out.SetRotation(Tilt * Slot.World.GetRotation());
	Out.SetLocation(Inst.Pivot + Tilt.RotateVector(Slot.World.GetLocation() - Inst.Pivot));
	return Out;
}

void UGTVegetationSubsystem::SnapSlot(int32 SlotIndex, bool bSustained)
{
	const UGTVegetationSettings* Settings = GetDefault<UGTVegetationSettings>();
	const FSlot Slot = Slots[SlotIndex];
	FInstance& Inst = Instances[Slot.Instance];
	const FGTVegClassDials& Dials = Settings->ForClass(Inst.Class);
	const double Now = GetWorld()->GetTimeSeconds();
	Inst.bSnapped = true;   // hidden (scale 0) for the rest of the run
	++Stats.Snaps;
	++Stats.SnapsByClass[static_cast<int32>(Inst.Class)];
	++(bSustained ? Stats.SnapsSustained : Stats.SnapsImpact);

	UStaticMeshComponent* Proxy = Proxies[Slot.Proxy];
	// Fallen, it is no longer bending: the debris casts the instance's own shadow.
	const UInstancedStaticMeshComponent* SourceIsm = Components[Inst.Component].Ism.Get();
	Proxy->SetCastShadow(SourceIsm && SourceIsm->CastShadow);
	Proxy->SetWorldTransform(BentTransform(Slot, Inst), false, nullptr, ETeleportType::TeleportPhysics);
	const FVector ImpulseKgCms = Slot.CarVelocityDir * (Dials.DebrisMassKg * Slot.CarSpeedMs * 100.f * Settings->DebrisImpulseScale);
	AGTVegDebrisActor* Actor = AcquireDebris();
	if (Actor && Actor->Capsule)
	{
		// The trunk: the probe radius, the instance's height long, tilted as the tree was, its foot at the pivot.
		const FVector Axis = FVector::CrossProduct(FVector::UpVector, Slot.Dir).GetSafeNormal();
		const FQuat Tilt = Axis.IsNearlyZero() ? FQuat::Identity : FQuat(Axis, Slot.TiltRad);
		const float Radius = FMath::Max(Inst.RadiusCm, 5.f);
		const float HalfHeight = FMath::Max(Inst.HeightCm * 0.5f, Radius);
		UCapsuleComponent* Capsule = Actor->Capsule;
		Capsule->SetSimulatePhysics(false);
		Capsule->SetCapsuleSize(Radius, HalfHeight, false);
		Actor->SetActorLocationAndRotation(Inst.Pivot + Tilt.RotateVector(FVector(0.0, 0.0, HalfHeight)), Tilt, false, nullptr, ETeleportType::TeleportPhysics);
		Actor->SetActorHiddenInGame(false);
		Capsule->SetCollisionProfileName(UCollisionProfile::PhysicsActor_ProfileName);
		Capsule->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Capsule->SetMassOverrideInKg(NAME_None, Dials.DebrisMassKg, true);
		Capsule->SetSimulatePhysics(true);
		Capsule->SetPhysicsLinearVelocity(FVector::ZeroVector);
		Capsule->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
		Proxy->AttachToComponent(Capsule, FAttachmentTransformRules::KeepWorldTransform);
		Capsule->AddImpulse(ImpulseKgCms, NAME_None, /*bVelChange*/ false);
		Actor->Proxy = Slot.Proxy;
		Actor->Instance = Slot.Instance;
		Actor->LaunchTime = Now;
		Actor->bInUse = true;
		Actor->bFrozen = false;
	}
	else
	{
		ReleaseProxy(Slot.Proxy);
	}
	// Equal and opposite: the car gets the debris' impulse back.
	if (UPrimitiveComponent* Car = Slot.Car.Get())
	{
		Car->AddImpulse(-ImpulseKgCms, NAME_None, /*bVelChange*/ false);
	}
	UE_LOG(LogTemp, Display, TEXT("GTVEG snap (%s): %s at %.1f m/s, tilt %.1f deg (break %.0f), p %.2f held %.2f s, %.0f kg of debris, impulse %.0f N s each way"),
		bSustained ? TEXT("sustained push") : TEXT("impact"), ClassName(Inst.Class), Slot.CarSpeedMs, FMath::RadiansToDegrees(Slot.TiltRad),
		Dials.BreakTiltDeg, Slot.Push, Slot.SustainS, Dials.DebrisMassKg, ImpulseKgCms.Size() / 100.0);
	RemoveSlot(SlotIndex);
}

void UGTVegetationSubsystem::QueueInstance(int32 InstanceIndex, const FTransform& Local)
{
	const FInstance& Inst = Instances[InstanceIndex];
	Components[Inst.Component].Pending.Emplace(Inst.Index, Local);
}

int32 UGTVegetationSubsystem::FlushInstances()
{
	// One pass per component per frame: plain ISMs send only the changed instances to the renderer (no render-state
	// rebuild), so every update is made without MarkRenderStateDirty.
	int32 Updates = 0;
	for (FComponent& Entry : Components)
	{
		if (Entry.Pending.Num() == 0)
		{
			continue;
		}
		if (UInstancedStaticMeshComponent* Ism = Entry.Ism.Get())
		{
			for (const TPair<int32, FTransform>& Change : Entry.Pending)
			{
				Ism->UpdateInstanceTransform(Change.Key, Change.Value, /*bWorldSpace*/ false, /*bMarkRenderStateDirty*/ false, /*bTeleport*/ true);
				++Updates;
			}
		}
		Entry.Pending.Reset();
	}
	return Updates;
}

// ---- the proxy pool -------------------------------------------------------------------------------------------------

void UGTVegetationSubsystem::EnsurePoolActor()
{
	if (PoolActor)
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	PoolActor = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
	if (!PoolActor)
	{
		return;
	}
	USceneComponent* Root = NewObject<USceneComponent>(PoolActor, TEXT("Root"), RF_Transient);
	Root->SetMobility(EComponentMobility::Movable);
	PoolActor->SetRootComponent(Root);
	Root->RegisterComponent();
#if WITH_EDITOR
	PoolActor->SetActorLabel(TEXT("GTVegetationPool"));
#endif
}

int32 UGTVegetationSubsystem::AcquireProxy()
{
	if (FreeProxies.Num() > 0)
	{
		return FreeProxies.Pop(EAllowShrinking::No);
	}
	EnsurePoolActor();
	if (!PoolActor)
	{
		return INDEX_NONE;
	}
	UStaticMeshComponent* Proxy = NewObject<UStaticMeshComponent>(PoolActor, NAME_None, RF_Transient);
	Proxy->SetMobility(EComponentMobility::Movable);
	Proxy->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Proxy->SetGenerateOverlapEvents(false);
	Proxy->SetCanEverAffectNavigation(false);
	Proxy->SetupAttachment(PoolActor->GetRootComponent());
	Proxy->RegisterComponent();
	Proxy->SetVisibility(false);
	ProxyConfiguredFor.Add(INDEX_NONE);
	return Proxies.Add(Proxy);
}

void UGTVegetationSubsystem::ReleaseProxy(int32 ProxyIndex)
{
	if (!Proxies.IsValidIndex(ProxyIndex))
	{
		return;
	}
	if (UStaticMeshComponent* Proxy = Proxies[ProxyIndex])
	{
		if (PoolActor && Proxy->GetAttachParent() != PoolActor->GetRootComponent())
		{
			Proxy->AttachToComponent(PoolActor->GetRootComponent(), FAttachmentTransformRules::KeepWorldTransform);
		}
		Proxy->SetVisibility(false);
	}
	FreeProxies.Add(ProxyIndex);
}

void UGTVegetationSubsystem::ConfigureProxy(int32 ProxyIndex, const UInstancedStaticMeshComponent& Ism)
{
	UStaticMeshComponent* Proxy = Proxies[ProxyIndex];
	Proxy->SetStaticMesh(Ism.GetStaticMesh());
	Proxy->EmptyOverrideMaterials();
	for (int32 Slot = 0; Slot < Ism.GetNumMaterials(); ++Slot)
	{
		Proxy->SetMaterial(Slot, Ism.GetMaterial(Slot));
	}
	Proxy->SetCastShadow(Ism.CastShadow);
	Proxy->SetEvaluateWorldPositionOffset(Ism.bEvaluateWorldPositionOffset);
	Proxy->SetWorldPositionOffsetDisableDistance(Ism.WorldPositionOffsetDisableDistance);
	Proxy->SetReceivesDecals(Ism.bReceivesDecals);
	Proxy->SetCullDistance(Ism.InstanceEndCullDistance > 0 ? static_cast<float>(Ism.InstanceEndCullDistance) : Ism.LDMaxDrawDistance);
}

// ---- debris ---------------------------------------------------------------------------------------------------------

AGTVegDebrisActor* UGTVegetationSubsystem::AcquireDebris()
{
	for (AGTVegDebrisActor* Actor : Debris)
	{
		if (Actor && !Actor->bInUse)
		{
			return Actor;
		}
	}
	if (Debris.Num() < GetDefault<UGTVegetationSettings>()->MaxDebris)
	{
		FActorSpawnParameters Params;
		Params.ObjectFlags |= RF_Transient;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AGTVegDebrisActor* Actor = GetWorld()->SpawnActor<AGTVegDebrisActor>(AGTVegDebrisActor::StaticClass(), FTransform::Identity, Params);
		if (Actor)
		{
			Debris.Add(Actor);
		}
		return Actor;
	}
	// The cap: the oldest frozen debris becomes a no-collision ISM instance and its actor is reused; none frozen, the oldest.
	AGTVegDebrisActor* Pick = nullptr;
	for (int32 Pass = 0; Pass < 2 && !Pick; ++Pass)
	{
		for (AGTVegDebrisActor* Actor : Debris)
		{
			if (Actor && Actor->bInUse && (Pass == 1 || Actor->bFrozen) && (!Pick || Actor->LaunchTime < Pick->LaunchTime))
			{
				Pick = Actor;
			}
		}
	}
	if (Pick)
	{
		ConvertDebris(*Pick);
	}
	return Pick;
}

void UGTVegetationSubsystem::FreezeDebris(AGTVegDebrisActor& Actor)
{
	Actor.Capsule->SetSimulatePhysics(false);
	Actor.Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Actor.bFrozen = true;
}

void UGTVegetationSubsystem::ConvertDebris(AGTVegDebrisActor& Actor)
{
	UStaticMeshComponent* Proxy = Proxies.IsValidIndex(Actor.Proxy) ? Proxies[Actor.Proxy].Get() : nullptr;
	if (Proxy && Proxy->GetStaticMesh() && PoolActor)
	{
		UInstancedStaticMeshComponent* Target = nullptr;
		for (UInstancedStaticMeshComponent* Ism : DebrisIsms)
		{
			if (Ism && Ism->GetStaticMesh() == Proxy->GetStaticMesh() && Ism->GetMaterial(0) == Proxy->GetMaterial(0))
			{
				Target = Ism;
				break;
			}
		}
		if (!Target)
		{
			Target = NewObject<UInstancedStaticMeshComponent>(PoolActor, NAME_None, RF_Transient);
			Target->SetMobility(EComponentMobility::Movable);
			Target->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
			Target->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Target->SetCanEverAffectNavigation(false);
			Target->SetStaticMesh(Proxy->GetStaticMesh());
			for (int32 Slot = 0; Slot < Proxy->GetNumMaterials(); ++Slot)
			{
				Target->SetMaterial(Slot, Proxy->GetMaterial(Slot));
			}
			Target->SetCastShadow(Proxy->CastShadow);
			Target->SetupAttachment(PoolActor->GetRootComponent());
			Target->RegisterComponent();
			DebrisIsms.Add(Target);
		}
		Target->AddInstance(Proxy->GetComponentTransform(), /*bWorldSpace*/ true);
		++Stats.DebrisConverted;
	}
	ParkDebris(Actor);
}

void UGTVegetationSubsystem::ParkDebris(AGTVegDebrisActor& Actor)
{
	if (Actor.Proxy != INDEX_NONE)
	{
		ReleaseProxy(Actor.Proxy);
	}
	Actor.Capsule->SetSimulatePhysics(false);
	Actor.Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Actor.SetActorHiddenInGame(true);
	Actor.Proxy = INDEX_NONE;
	Actor.Instance = INDEX_NONE;
	Actor.bInUse = false;
	Actor.bFrozen = false;
}

void UGTVegetationSubsystem::TickDebris(double Now)
{
	const float FreezeS = GetDefault<UGTVegetationSettings>()->DebrisFreezeS;
	for (AGTVegDebrisActor* Actor : Debris)
	{
		if (!Actor || !Actor->bInUse || Actor->bFrozen)
		{
			continue;
		}
		const double Age = Now - Actor->LaunchTime;
		if (Age >= FreezeS || (Age > 0.5 && !Actor->Capsule->IsAnyRigidBodyAwake()))
		{
			FreezeDebris(*Actor);
		}
	}
}

// ---- inert / restore ------------------------------------------------------------------------------------------------

void UGTVegetationSubsystem::RestoreAll()
{
	for (int32 Index = Slots.Num() - 1; Index >= 0; --Index)
	{
		QueueInstance(Slots[Index].Instance, Slots[Index].Local);
		ReleaseProxy(Slots[Index].Proxy);
		Instances[Slots[Index].Instance].Slot = INDEX_NONE;
	}
	Slots.Reset();
	for (const TPair<int32, FTransform>& Entry : OriginalLocal)
	{
		if (Instances.IsValidIndex(Entry.Key) && Instances[Entry.Key].bSnapped)
		{
			Instances[Entry.Key].bSnapped = false;
			QueueInstance(Entry.Key, Entry.Value);
		}
	}
	for (AGTVegDebrisActor* Actor : Debris)
	{
		if (Actor && Actor->bInUse)
		{
			ParkDebris(*Actor);
		}
	}
	for (UInstancedStaticMeshComponent* Ism : DebrisIsms)
	{
		if (Ism)
		{
			Ism->ClearInstances();
		}
	}
	FlushInstances();
}

void UGTVegetationSubsystem::MakeInert()
{
	RestoreAll();
	bInert = true;
	UE_LOG(LogTemp, Display, TEXT("GTVEG gt.Look.Dressing 0: inert, every instance restored (%d indexed)"), Instances.Num());
}

// ---- tick -----------------------------------------------------------------------------------------------------------

void UGTVegetationSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!bBegun || Instances.Num() == 0)
	{
		FrameWorkSeconds = 0.0;
		return;   // no soft vegetation: nothing to do
	}
	const double StartSeconds = FPlatformTime::Seconds();
	if (GTVeg::Dressing() == 0)
	{
		if (!bInert)
		{
			MakeInert();
		}
		FrameWorkSeconds = 0.0;
		return;
	}
	if (bInert)
	{
		bInert = false;
		UE_LOG(LogTemp, Display, TEXT("GTVEG gt.Look.Dressing 1: active again (%d indexed)"), Instances.Num());
	}

	const UGTVegetationSettings* Settings = GetDefault<UGTVegetationSettings>();
	const double Now = GetWorld()->GetTimeSeconds();
	const float Dt = FMath::Max(DeltaTime, 0.f);
	const float RiseAlpha = 1.f - FMath::Exp(-Dt / FMath::Max(Settings->RiseTauS, 1.e-3f));
	const float RecoverAlpha = 1.f - FMath::Exp(-Dt / FMath::Max(Settings->RecoverTauS, 1.e-3f));
	const float RecoveredRad = FMath::DegreesToRadians(Settings->RecoveredDeg);
	for (int32 Index = Slots.Num() - 1; Index >= 0; --Index)
	{
		FSlot& Slot = Slots[Index];
		FInstance& Inst = Instances[Slot.Instance];
		const FGTVegClassDials& Dials = Settings->ForClass(Inst.Class);
		const float Target = Slot.bContact ? FMath::DegreesToRadians(Dials.MaxTiltDeg) * Slot.Push : 0.f;
		Slot.TiltRad += (Target - Slot.TiltRad) * (Target > Slot.TiltRad ? RiseAlpha : RecoverAlpha);
		const float TiltDeg = FMath::RadiansToDegrees(Slot.TiltRad);
		Stats.MaxTiltDeg = FMath::Max(Stats.MaxTiltDeg, TiltDeg);
		if (Slot.bContact)
		{
			if (!Inst.bStatBent && TiltDeg > Stats.BendDeg)
			{
				Inst.bStatBent = true;
				++Stats.BentOver;
			}
			const bool bAtBreak = Dials.CanSnap() && TiltDeg >= Dials.BreakTiltDeg;
			// v2: a sustained push (tilt at the break and p >= 0.9) for the class's hold also snaps it.
			Slot.SustainS = (bAtBreak && Slot.Push >= Settings->SustainPush) ? Slot.SustainS + Dt : 0.f;
			const bool bImpact = bAtBreak && Dials.BreakSpeedMs > 0.f && Slot.CarSpeedMs >= Dials.BreakSpeedMs;
			const bool bSustained = bAtBreak && Dials.SustainHoldS > 0.f && Slot.SustainS >= Dials.SustainHoldS;
			if (bImpact || bSustained)
			{
				SnapSlot(Index, !bImpact);
				continue;
			}
		}
		else
		{
			Slot.SustainS = 0.f;
			if (Slot.ContactEndTime < 0.0)
			{
				Slot.ContactEndTime = Now;
			}
			if (!Slot.bSettleTimed && TiltDeg < Stats.SettledDeg)
			{
				Slot.bSettleTimed = true;
				++Stats.Recovered;
				Stats.MaxRecoverS = FMath::Max(Stats.MaxRecoverS, static_cast<float>(Now - Slot.ContactEndTime));
			}
			if (Slot.TiltRad < RecoveredRad)
			{
				RecoverSlot(Index);
				continue;
			}
		}
		Proxies[Slot.Proxy]->SetWorldTransform(BentTransform(Slot, Inst), false, nullptr, ETeleportType::TeleportPhysics);
		Slot.bContact = false;
	}
	TickDebris(Now);
	Stats.InstanceUpdates += FlushInstances();

	// The per-frame work: this frame's probe calls and this tick.
	const float Ms = static_cast<float>((FrameWorkSeconds + FPlatformTime::Seconds() - StartSeconds) * 1000.0);
	FrameWorkSeconds = 0.0;
	if (RollingMs.Num() < RollingFrames)
	{
		RollingMs.Add(Ms);
	}
	else
	{
		RollingMs[RollingNext] = Ms;
	}
	RollingNext = (RollingNext + 1) % RollingFrames;
	Stats.TickMsSum += Ms;
	Stats.TickMsMax = FMath::Max(Stats.TickMsMax, Ms);
	++Stats.TickFrames;
	if (Slots.Num() > 0)
	{
		bActivitySinceLog = true;
	}
	if (bActivitySinceLog && Now - LastLogTime >= GTVeg::LogEverySeconds)
	{
		float Mean = 0.f;
		float Max = 0.f;
		int32 Frames = 0;
		GetRollingTickMs(Mean, Max, Frames);
		UE_LOG(LogTemp, Display, TEXT("GTVEG work %.3f ms mean, %.3f ms max over the last %d frames; active %d, debris %d in use; contacts now %d, resist %.0f N; snaps %d"),
			Mean, Max, Frames, Slots.Num(), GetDebrisInUse(), LastProbeContacts, LastForceN, Stats.Snaps);
		LastLogTime = Now;
		bActivitySinceLog = false;
	}
}

// ---- queries --------------------------------------------------------------------------------------------------------

void UGTVegetationSubsystem::ResetStats(float BendDeg, float SettledDeg)
{
	Stats = FGTVegStats();
	Stats.BendDeg = BendDeg;
	Stats.SettledDeg = SettledDeg;
	for (FInstance& Inst : Instances)
	{
		Inst.bStatContact = false;
		Inst.bStatBent = false;
	}
}

int32 UGTVegetationSubsystem::GetDebrisInUse() const
{
	int32 Count = 0;
	for (const AGTVegDebrisActor* Actor : Debris)
	{
		Count += (Actor && Actor->bInUse) ? 1 : 0;
	}
	return Count;
}

int32 UGTVegetationSubsystem::CountTiltedOver(float Deg) const
{
	const float Rad = FMath::DegreesToRadians(Deg);
	int32 Count = 0;
	for (const FSlot& Slot : Slots)
	{
		Count += Slot.TiltRad > Rad ? 1 : 0;
	}
	return Count;
}

int32 UGTVegetationSubsystem::GetIndexedCount(EGTVegClass Class) const
{
	int32 Count = 0;
	for (const FInstance& Inst : Instances)
	{
		Count += Inst.Class == Class ? 1 : 0;
	}
	return Count;
}

void UGTVegetationSubsystem::CountComponents(int32 OutIsm[3], int32 OutHism[3]) const
{
	for (int32 Index = 0; Index < 3; ++Index)
	{
		OutIsm[Index] = 0;
		OutHism[Index] = 0;
	}
	for (const FComponent& Entry : Components)
	{
		(Entry.bHism ? OutHism : OutIsm)[static_cast<int32>(Entry.Class)]++;
	}
}

void UGTVegetationSubsystem::GetRollingTickMs(float& OutMean, float& OutMax, int32& OutFrames) const
{
	OutMean = 0.f;
	OutMax = 0.f;
	OutFrames = RollingMs.Num();
	for (const float Ms : RollingMs)
	{
		OutMean += Ms;
		OutMax = FMath::Max(OutMax, Ms);
	}
	OutMean = OutFrames > 0 ? OutMean / OutFrames : 0.f;
}

void UGTVegetationSubsystem::ForEachInstance(TFunctionRef<void(const FVector&, EGTVegClass, float, float, bool)> Visit) const
{
	for (const FInstance& Inst : Instances)
	{
		Visit(Inst.Pivot, Inst.Class, Inst.RadiusCm, Inst.HeightCm, Inst.bSnapped);
	}
}

FString UGTVegetationSubsystem::DescribeIndex() const
{
	int32 Ism[3];
	int32 Hism[3];
	CountComponents(Ism, Hism);
	return FString::Printf(TEXT("index: %d soft instance(s) - Brush %d, Sapling %d, Young %d - in %d component(s) (plain ISM %d/%d/%d, HISM %d/%d/%d by class), %d hash cell(s) of %.0f m, largest probe radius %.0f cm, %d already-hidden instance(s) skipped"),
		Instances.Num(), GetIndexedCount(EGTVegClass::Brush), GetIndexedCount(EGTVegClass::Sapling), GetIndexedCount(EGTVegClass::Young),
		Components.Num(), Ism[0], Ism[1], Ism[2], Hism[0], Hism[1], Hism[2], Cells.Num(), CellCm / 100.f, MaxRadiusCm, SkippedHidden);
}

// ---- setup helper ---------------------------------------------------------------------------------------------------

UInstancedStaticMeshComponent* UGTVegetationSubsystem::AddTaggedInstances(AActor* Actor, UStaticMesh* Mesh, const TArray<FTransform>& WorldTransforms,
	FName ComponentTag, FName CollisionProfile, bool bCastShadow)
{
	if (!Actor || !Mesh)
	{
		return nullptr;
	}
	Actor->Modify();
	USceneComponent* Root = Actor->GetRootComponent();
	if (!Root)
	{
		Root = NewObject<USceneComponent>(Actor, TEXT("Root"), RF_Transactional);
		Root->SetMobility(EComponentMobility::Static);
		Actor->SetRootComponent(Root);
		Actor->AddInstanceComponent(Root);
		Root->RegisterComponent();
	}
	const FName Name = MakeUniqueObjectName(Actor, UInstancedStaticMeshComponent::StaticClass(), FName(*FString::Printf(TEXT("ISM_%s"), *Mesh->GetName())));
	UInstancedStaticMeshComponent* Ism = NewObject<UInstancedStaticMeshComponent>(Actor, UInstancedStaticMeshComponent::StaticClass(), Name, RF_Transactional);
	Ism->SetMobility(EComponentMobility::Static);
	Ism->SetStaticMesh(Mesh);
	Ism->SetCollisionProfileName(CollisionProfile);
	Ism->SetCastShadow(bCastShadow);
	Ism->ComponentTags.Add(ComponentTag);
	Ism->SetupAttachment(Root);
	Actor->AddInstanceComponent(Ism);
	Ism->RegisterComponent();
	Ism->AddInstances(WorldTransforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
	return Ism;
}
