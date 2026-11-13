#include "Vehicle/GTDashboardComponent.h"

#include "Core/GTGameplayTags.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTTractionComponent.h"

#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	const FName DashParamBaseColor(TEXT("BaseColor"));
	const FName DashParamRoughness(TEXT("Roughness"));
	const FName ParamEmissiveColor(TEXT("EmissiveColor"));
	const FName ParamEmissiveStrength(TEXT("EmissiveStrength"));

	constexpr float LightOnStrength = 12.f;

	const FLinearColor LightColours[] = {
		FLinearColor(1.0f, 0.15f, 0.05f),   // Engine: red
		FLinearColor(0.2f, 0.5f, 1.0f),     // Coolant: blue
		FLinearColor(1.0f, 0.6f, 0.05f),    // Fuel: amber
		FLinearColor(1.0f, 0.6f, 0.05f),    // Bogged: amber
		FLinearColor(1.0f, 0.15f, 0.05f),   // Suspension: red
		FLinearColor(1.0f, 0.6f, 0.05f),    // Filter: amber
		FLinearColor(0.4f, 0.7f, 1.0f),     // Cold: ice blue
		FLinearColor(0.3f, 1.0f, 0.3f),     // Radiation: green
			FLinearColor(1.0f, 0.85f, 0.3f),    // Lock: diff lock, warm white
		FLinearColor(0.3f, 1.0f, 0.4f),     // Low: low range, green
	};
}

UGTDashboardComponent::UGTDashboardComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	CylinderMesh = Cylinder.Object;
	CubeMesh = Cube.Object;
	// M_GT_Prop is loaded when the greybox is built, not here: a constructor finder roots the
	// material (and MF_Weather behind it) for the run, and the setup scripts could not rebuild them.
	LightStates.Init(false, static_cast<int32>(ELight::Count));
}

void UGTDashboardComponent::OnRegister()
{
	Super::OnRegister();
	if (bBuildGreybox && !bBuilt && !HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) && GetOwner())
	{
		BuildGreybox();
	}
}

UMaterialInstanceDynamic* UGTDashboardComponent::MakeMaterial(const FLinearColor& BaseColor, float Roughness,
                                                              const FLinearColor& Emissive, float Strength)
{
	if (!PropMaterial)
	{
		return nullptr;
	}
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(PropMaterial, this);
	Material->SetVectorParameterValue(DashParamBaseColor, BaseColor);
	Material->SetScalarParameterValue(DashParamRoughness, Roughness);
	Material->SetVectorParameterValue(ParamEmissiveColor, Emissive);
	Material->SetScalarParameterValue(ParamEmissiveStrength, Strength);
	OwnedMaterials.Add(Material);
	return Material;
}

UStaticMeshComponent* UGTDashboardComponent::MakeMesh(const FString& Name, UStaticMesh* Mesh, USceneComponent* Parent,
                                                      const FVector& Location, const FRotator& Rotation, const FVector& Scale,
                                                      UMaterialInterface* Material)
{
	const FName ObjectName = MakeUniqueObjectName(GetOwner(), UStaticMeshComponent::StaticClass(), *FString::Printf(TEXT("Dash_%s"), *Name));
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(GetOwner(), ObjectName, RF_Transient);
	Component->SetStaticMesh(Mesh);
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetCastShadow(false);
	Component->SetupAttachment(Parent);
	Component->SetRelativeLocationAndRotation(Location, Rotation);
	Component->SetRelativeScale3D(Scale);
	if (Material)
	{
		Component->SetMaterial(0, Material);
	}
	Component->RegisterComponent();
	GreyboxMeshes.Add(Component);
	++GreyboxPartCount;
	return Component;
}

USceneComponent* UGTDashboardComponent::MakeDial(const FString& Name, const FVector& LocalPosition, float Diameter)
{
	// Face: a thin cylinder whose axis (local Z) points at the driver. Needle: a bar along local X
	// hanging off a pivot just proud of the face; the pivot's yaw is the needle angle.
	UMaterialInterface* FaceMaterial = MakeMaterial(FLinearColor(0.03f, 0.03f, 0.035f), 0.4f, FLinearColor::Black, 0.f);
	MakeMesh(Name + TEXT("Face"), CylinderMesh, this, LocalPosition, FRotator::ZeroRotator,
		FVector(Diameter / 100.f, Diameter / 100.f, 0.01f), FaceMaterial);
	MakeMesh(Name + TEXT("Rim"), CylinderMesh, this, LocalPosition - FVector(0.f, 0.f, 0.3f), FRotator::ZeroRotator,
		FVector((Diameter + 1.2f) / 100.f, (Diameter + 1.2f) / 100.f, 0.008f),
		MakeMaterial(FLinearColor(0.25f, 0.25f, 0.27f), 0.5f, FLinearColor::Black, 0.f));

	USceneComponent* Pivot = NewObject<USceneComponent>(GetOwner(), NAME_None, RF_Transient);
	Pivot->SetupAttachment(this);
	Pivot->SetRelativeLocation(LocalPosition + FVector(0.f, 0.f, 0.7f));
	Pivot->RegisterComponent();

	const float Length = Diameter * 0.42f;
	UMaterialInterface* NeedleMaterial = MakeMaterial(FLinearColor(1.f, 0.35f, 0.05f), 0.6f, FLinearColor(1.f, 0.35f, 0.05f), 0.6f);
	MakeMesh(Name + TEXT("Needle"), CubeMesh, Pivot, FVector(Length * 0.5f - Diameter * 0.06f, 0.f, 0.f), FRotator::ZeroRotator,
		FVector(Length / 100.f, 0.006f, 0.002f), NeedleMaterial);
	MakeMesh(Name + TEXT("Hub"), CylinderMesh, Pivot, FVector::ZeroVector, FRotator::ZeroRotator,
		FVector(0.014f, 0.014f, 0.004f), NeedleMaterial);
	return Pivot;
}

void UGTDashboardComponent::BuildGreybox()
{
	bBuilt = true;
	if (!PropMaterial)
	{
		PropMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/GrandTour/Materials/M_GT_Prop.M_GT_Prop"));
	}
	if (!CylinderMesh || !CubeMesh)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTDashboardComponent: engine basic shapes not found, no greybox dash"));
		return;
	}
	if (!PropMaterial)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTDashboardComponent: M_GT_Prop missing (run Art/setup_m1_cockpit.bat); dash will be untextured"));
	}

	// Cluster: speedo left, tacho right, fuel below, lights in a row underneath.
	SpeedNeedle = MakeDial(TEXT("Speedo"), FVector(0.f, -11.5f, 0.f), 10.f);
	RpmNeedle = MakeDial(TEXT("Tacho"), FVector(0.f, 11.5f, 0.f), 10.f);
	FuelNeedle = MakeDial(TEXT("Fuel"), FVector(-6.5f, -3.5f, 0.f), 5.f);
	TempNeedle = MakeDial(TEXT("Temp"), FVector(-6.5f, 3.5f, 0.f), 5.f);

	LightMaterials.SetNum(static_cast<int32>(ELight::Count));
	for (int32 Index = 0; Index < static_cast<int32>(ELight::Count); ++Index)
	{
		UMaterialInstanceDynamic* Material = MakeMaterial(LightColours[Index] * 0.15f, 0.3f, LightColours[Index], 0.f);
		LightMaterials[Index] = Material;
		MakeMesh(FString::Printf(TEXT("Light%d"), Index), CubeMesh, this, FVector(-12.5f, -14.f + 4.f * Index, 0.f),
			FRotator::ZeroRotator, FVector(0.015f, 0.025f, 0.006f), Material);
	}

	// Dash slab, binnacle and steering wheel live in the car frame, not the tilted cluster frame.
	USceneComponent* CarFrame = GetAttachParent() ? GetAttachParent() : this;
	UMaterialInterface* DashMaterial = MakeMaterial(FLinearColor(0.08f, 0.075f, 0.07f), 0.85f, FLinearColor::Black, 0.f);
	MakeMesh(TEXT("Slab"), CubeMesh, CarFrame, DashSlabCentre, FRotator::ZeroRotator, DashSlabSize / 100.f, DashMaterial);
	MakeMesh(TEXT("Binnacle"), CubeMesh, CarFrame, BinnacleCentre, FRotator::ZeroRotator, BinnacleSize / 100.f, DashMaterial);

	// Steering wheel: a fixed tilted pivot (the axis) and a spinner child that yaws about it. The
	// rim is a ring of cylinder segments so the driver can see the dials through it.
	SteeringWheel = NewObject<USceneComponent>(GetOwner(), NAME_None, RF_Transient);
	SteeringWheel->SetupAttachment(CarFrame);
	SteeringWheel->SetRelativeLocationAndRotation(SteeringWheelCentre, FRotator(SteeringWheelPitch, 0.f, 0.f));
	SteeringWheel->RegisterComponent();
	SteeringWheelSpinner = NewObject<USceneComponent>(GetOwner(), NAME_None, RF_Transient);
	SteeringWheelSpinner->SetupAttachment(SteeringWheel);
	SteeringWheelSpinner->RegisterComponent();

	UMaterialInterface* WheelMaterial = MakeMaterial(FLinearColor(0.12f, 0.12f, 0.12f), 0.55f, FLinearColor::Black, 0.f);
	const float Radius = SteeringWheelDiameter * 0.5f;
	constexpr int32 Segments = 12;
	const float SegmentLength = 2.f * PI * Radius / Segments * 1.12f;   // slight overlap closes the ring
	for (int32 Index = 0; Index < Segments; ++Index)
	{
		const float Angle = 360.f * Index / Segments;
		const float Radians = FMath::DegreesToRadians(Angle);
		// Segment axis (cylinder local Z) lies tangent to the ring: pitch 90 puts Z along -X, yaw then aims it.
		MakeMesh(FString::Printf(TEXT("Rim%d"), Index), CylinderMesh, SteeringWheelSpinner,
			FVector(Radius * FMath::Cos(Radians), Radius * FMath::Sin(Radians), 0.f), FRotator(90.f, Angle - 90.f, 0.f),
			FVector(0.032f, 0.032f, SegmentLength / 100.f), WheelMaterial);
	}
	for (float SpokeYaw : { 90.f, -90.f, 180.f })   // right, left, down (local X is the wheel's "up")
	{
		MakeMesh(TEXT("Spoke"), CubeMesh, SteeringWheelSpinner,
			FRotator(0.f, SpokeYaw, 0.f).RotateVector(FVector(Radius * 0.5f, 0.f, 0.f)), FRotator(0.f, SpokeYaw, 0.f),
			FVector(Radius / 100.f, 0.025f, 0.018f), WheelMaterial);
	}
	MakeMesh(TEXT("WheelHub"), CylinderMesh, SteeringWheelSpinner, FVector::ZeroVector, FRotator::ZeroRotator,
		FVector(0.09f, 0.09f, 0.035f), WheelMaterial);
	MakeMesh(TEXT("WheelColumn"), CylinderMesh, CarFrame, SteeringWheelCentre + FVector(9.f, 0.f, -3.f),
		FRotator(SteeringWheelPitch, 0.f, 0.f), FVector(0.05f, 0.05f, 0.22f), WheelMaterial);
}

void UGTDashboardComponent::SetLight(ELight Light, bool bOn)
{
	const int32 Index = static_cast<int32>(Light);
	if (LightStates.IsValidIndex(Index) && LightStates[Index] != bOn)
	{
		LightStates[Index] = bOn;
		if (LightMaterials.IsValidIndex(Index) && LightMaterials[Index])
		{
			LightMaterials[Index]->SetScalarParameterValue(ParamEmissiveStrength, bOn ? LightOnStrength : 0.f);
		}
	}
}

void UGTDashboardComponent::UpdateFromVehicle(float DeltaSeconds, const UChaosWheeledVehicleMovementComponent& Movement,
                                              const UGTConditionComponent& Condition, const UGTTractionComponent& Traction,
                                              const UGTEnvironmentComponent* Environment, bool bRadiation,
                                              float EngineRpm, bool bDiffLock, bool bLowRange)
{
	const float Kph = FMath::Abs(Movement.GetForwardSpeed()) * 0.036f;
	const float Rpm = EngineRpm;   // the drivetrain's engine (Chaos's mechanical sim is off)
	bLockLight = bDiffLock;
	bLowLight = bLowRange;
	const float Half = NeedleSweepDegrees * 0.5f;
	TargetSpeedDegrees = -Half + NeedleSweepDegrees * FMath::Clamp(Kph / FMath::Max(1.f, SpeedoMaxKph), 0.f, 1.f);
	TargetRpmDegrees = -Half + NeedleSweepDegrees * FMath::Clamp(Rpm / FMath::Max(1.f, TachoMaxRpm), 0.f, 1.f);
	TargetFuelDegrees = -FuelSweepDegrees * 0.5f + FuelSweepDegrees * FMath::Clamp(Condition.GetFuelFraction(), 0.f, 1.f);
	TargetTempDegrees = -FuelSweepDegrees * 0.5f + FuelSweepDegrees * FMath::Clamp(Environment ? Environment->Heat : 0.f, 0.f, 1.f);
	TempNeedleDegrees = FMath::FInterpTo(TempNeedleDegrees, TargetTempDegrees, DeltaSeconds, NeedleLagSpeed * 0.25f);

	SpeedNeedleDegrees = FMath::FInterpTo(SpeedNeedleDegrees, TargetSpeedDegrees, DeltaSeconds, NeedleLagSpeed);
	RpmNeedleDegrees = FMath::FInterpTo(RpmNeedleDegrees, TargetRpmDegrees, DeltaSeconds, NeedleLagSpeed);
	FuelNeedleDegrees = FMath::FInterpTo(FuelNeedleDegrees, TargetFuelDegrees, DeltaSeconds, NeedleLagSpeed * 0.25f);
	// Follow the front wheels' actual steer angle (Chaos rate-limits it) rather than the raw input,
	// which is binary from a keyboard and made the wheel snap.
	float SteerAngleSum = 0.f;
	int32 SteeredWheels = 0;
	float MaxSteer = 35.f;
	for (const UChaosVehicleWheel* Wheel : Movement.Wheels)
	{
		if (Wheel && Wheel->bAffectedBySteering)
		{
			SteerAngleSum += Wheel->GetSteerAngle();
			MaxSteer = FMath::Max(1.f, Wheel->MaxSteerAngle);
			++SteeredWheels;
		}
	}
	const float TargetWheel = SteeredWheels ? (SteerAngleSum / SteeredWheels) / MaxSteer * SteeringWheelDegrees : 0.f;
	SteeringWheelAngle = FMath::FInterpTo(SteeringWheelAngle, TargetWheel, DeltaSeconds, 12.f);

	if (SpeedNeedle) { SpeedNeedle->SetRelativeRotation(FRotator(0.f, SpeedNeedleDegrees, 0.f)); }
	if (RpmNeedle)   { RpmNeedle->SetRelativeRotation(FRotator(0.f, RpmNeedleDegrees, 0.f)); }
	if (FuelNeedle)  { FuelNeedle->SetRelativeRotation(FRotator(0.f, FuelNeedleDegrees, 0.f)); }
	if (TempNeedle)  { TempNeedle->SetRelativeRotation(FRotator(0.f, TempNeedleDegrees, 0.f)); }
	if (SteeringWheelSpinner)
	{
		SteeringWheelSpinner->SetRelativeRotation(FRotator(0.f, SteeringWheelAngle, 0.f));   // about the wheel's own axis
	}

	bEngineLight = Condition.GetPartHealth(EGTCarPart::Engine) < WarningHealth || Condition.bMisfiring || Condition.bFlooded;
	bCoolantLight = Condition.GetPartHealth(EGTCarPart::Radiator) < WarningHealth
		|| (Environment && Environment->GetStage(GTTags::Env_Heat) >= EGTConditionStage::Warning);
	bFilterLight = Environment && Environment->GetStage(GTTags::Env_Dust) >= EGTConditionStage::Warning;
	bColdLight = Environment && Environment->GetStage(GTTags::Env_Cold) >= EGTConditionStage::Warning;
	bRadiationLight = bRadiation;
	bFuelLight = Condition.GetFuelFraction() < LowFuelFraction;
	bBoggedLight = Traction.bBogged;
	bSuspensionLight =
		FMath::Min(FMath::Min(Condition.GetPartHealth(EGTCarPart::SuspensionFL), Condition.GetPartHealth(EGTCarPart::SuspensionFR)),
		           FMath::Min(Condition.GetPartHealth(EGTCarPart::SuspensionRL), Condition.GetPartHealth(EGTCarPart::SuspensionRR))) < WarningHealth;
	SetLight(ELight::Engine, bEngineLight);
	SetLight(ELight::Coolant, bCoolantLight);
	SetLight(ELight::Fuel, bFuelLight);
	SetLight(ELight::Bogged, bBoggedLight);
	SetLight(ELight::Suspension, bSuspensionLight);
	SetLight(ELight::Filter, bFilterLight);
	SetLight(ELight::Cold, bColdLight);
	SetLight(ELight::Radiation, bRadiationLight);
	SetLight(ELight::Lock, bLockLight);
	SetLight(ELight::Low, bLowLight);
}

FString UGTDashboardComponent::CheckDialVisibility(const FVector& EyeLocation) const
{
	FString Report;
	const TPair<const TCHAR*, USceneComponent*> Dials[] = { {TEXT("speedo"), SpeedNeedle}, {TEXT("tacho"), RpmNeedle}, {TEXT("fuel"), FuelNeedle}, {TEXT("temp"), TempNeedle} };
	for (const auto& Dial : Dials)
	{
		if (!Dial.Value)
		{
			continue;
		}
		const FVector Target = Dial.Value->GetComponentLocation();
		const FVector Direction = Target - EyeLocation;
		for (const UStaticMeshComponent* Mesh : GreyboxMeshes)
		{
			// Skip the dial's own needle and hub (children of its pivot).
			if (!Mesh || Mesh->GetAttachParent() == Dial.Value)
			{
				continue;
			}
			const FBox Box = Mesh->Bounds.GetBox();
			// Ignore the face and rim the pivot sits on: the segment ends on them.
			if (Box.IsInside(Target) || FVector::Dist(Box.GetCenter(), Target) < 8.f)
			{
				continue;
			}
			if (FMath::LineBoxIntersection(Box, EyeLocation, Target, Direction))
			{
				Report += FString::Printf(TEXT(" %s<-%s"), Dial.Key, *Mesh->GetName());
			}
		}
	}
	return Report.IsEmpty() ? TEXT("clear") : Report.TrimStart();
}

FString UGTDashboardComponent::Describe() const
{
	FString Lights;
	if (bEngineLight)     { Lights += TEXT(" ENGINE"); }
	if (bCoolantLight)    { Lights += TEXT(" COOLANT"); }
	if (bFuelLight)       { Lights += TEXT(" FUEL"); }
	if (bBoggedLight)     { Lights += TEXT(" BOGGED"); }
	if (bSuspensionLight) { Lights += TEXT(" SUSPENSION"); }
	if (bFilterLight)     { Lights += TEXT(" FILTER"); }
	if (bColdLight)       { Lights += TEXT(" COLD"); }
	if (bRadiationLight)  { Lights += TEXT(" RADIATION"); }
	return FString::Printf(TEXT("speedo=%.0f deg tacho=%.0f deg fuel=%.0f deg temp=%.0f deg wheel=%.0f deg lights=[%s] greyboxParts=%d material=%s"),
		SpeedNeedleDegrees, RpmNeedleDegrees, FuelNeedleDegrees, TempNeedleDegrees, SteeringWheelAngle,
		Lights.IsEmpty() ? TEXT("none") : *Lights.TrimStart(), GreyboxPartCount, PropMaterial ? TEXT("M_GT_Prop") : TEXT("missing"));
}
