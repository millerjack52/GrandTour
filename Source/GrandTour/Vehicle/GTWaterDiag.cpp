#include "Vehicle/GTWaterDiag.h"

#include "Terrain/GTProvingGround.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTHullComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTVehicleTuningComponent.h"

#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

/** Diagnostic only: logs nothing and costs one cvar read a tick when 0. */
static TAutoConsoleVariable<int32> CVarWaterDiag(
	TEXT("gt.Water.Diag"), 0,
	TEXT("1 logs a GTWATERDIAG line (water, traction, hull, drivetrain) every 0.1 s, 2 every tick, 0 off. Read-only."));

int32 GTWaterDiag::GetMode()
{
	return CVarWaterDiag.GetValueOnGameThread();
}

FGTWaterDiagSample GTWaterDiag::Measure(const AGTCarPawn& Car)
{
	FGTWaterDiagSample S;
	UWorld* World = Car.GetWorld();
	UChaosWheeledVehicleMovementComponent* Move = Car.GetChaosMovement();
	const UGTTractionComponent* Traction = Car.GetTraction();
	const UGTHullComponent* Hull = Car.GetHull();
	const UGTConditionComponent* Condition = Car.GetCondition();
	const UGTDrivetrainComponent* Train = Car.GetDrivetrain();
	const UGTVehicleTuningComponent* Tuning = Car.GetTuning();
	USkeletalMeshComponent* Mesh = Car.GetMesh();
	if (!World || !Move || !Traction || !Hull || !Condition || !Train || !Tuning || !Mesh)
	{
		return S;
	}
	S.bValid = true;
	S.TimeS = World->GetTimeSeconds();
	S.LocationCm = Car.GetActorLocation();
	const FRotator Rot = Car.GetActorRotation();
	S.PitchDeg = Rot.Pitch;
	S.RollDeg = Rot.Roll;
	const FVector Velocity = Mesh->GetPhysicsLinearVelocity();
	const FVector Forward = Car.GetActorForwardVector();
	S.SpeedMps = static_cast<float>(FVector::DotProduct(Velocity, Forward)) * 0.01f;
	S.Speed2DMps = static_cast<float>(Velocity.Size2D()) * 0.01f;
	S.VerticalMps = static_cast<float>(Velocity.Z) * 0.01f;
	const UGTTerrainSpecAsset* SpecAsset = GTProving::FindSpecAsset(World);
	if (SpecAsset && SpecAsset->Spec.RouteM.Num() >= 2)
	{
		const FGTRouteHit Hit = GTTerrain::RouteAtCm(SpecAsset->Spec, S.LocationCm.X, S.LocationCm.Y);
		S.bHaveArc = true;
		S.ArcM = Hit.ArcM;
		S.OffM = Hit.SignedM;
	}
	S.Throttle = Move->GetThrottleInput();
	S.Gear = Train->GetGear();
	S.bLow = Train->IsLowRange();
	S.bLock = Train->IsDiffLocked();
	S.Rpm = Train->GetEngineRpm();
	S.EngineNm = Train->GetEngineTorqueNm();
	S.TorqueScale = Tuning->GetCurrent().TorqueScale;
	S.MaxEngineNm = Tuning->GetCurrent().MaxEngineTorque;
	S.bFlooded = Condition->bFlooded;
	S.bBogged = Traction->bBogged;
	S.LoadCorrection = Traction->LoadCorrection;
	S.WeightN = Move->Mass * 9.8f;
	S.HullDragN = Hull->LastWaterForceN;
	const FVector VelDir = Velocity.GetSafeNormal();
	S.HullDragAlongN = -static_cast<float>(FVector::DotProduct(Hull->LastWaterForce, VelDir));
	S.HullLiftN = Hull->LiftN;
	S.bLiftCapped = Hull->bLiftCapped;
	S.bDragCapped = Hull->bCapped;
	S.SubmergedM = Hull->SubmergedHeightM;
	S.KeelDepthM = Hull->KeelDepthM;
	S.FrontDepthM = Traction->FrontWaterDepthM;
	const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	if (Water)
	{
		if (const AGTWaterSheet* Sheet = Water->SheetAt(FVector2D(S.LocationCm.X, S.LocationCm.Y)))
		{
			S.SheetLevelCm = Sheet->GetLevelCm();
		}
	}

	const FGTVehicleTuning& Current = Tuning->GetCurrent();
	S.NumWheels = FMath::Min3(4, Traction->Wheels.Num(), Move->Wheels.Num());
	const float LoadPerWheelN = S.NumWheels > 0 ? S.WeightN / Traction->Wheels.Num() : 0.f;
	const float Fade = FMath::Clamp(static_cast<float>(Velocity.Size()) / FMath::Max(1.f, Tuning->DragFadeSpeed), 0.f, 1.f);
	const float Scale = FMath::Max(0.f, Current.RollingScale) * LoadPerWheelN * (Velocity.Size() < 1.0 ? 0.f : Fade);
	for (int32 Index = 0; Index < S.NumWheels; ++Index)
	{
		const FGTWheelTraction& T = Traction->Wheels[Index];
		FGTWaterDiagWheel& W = S.Wheels[Index];
		const UChaosVehicleWheel* Setup = Move->Wheels[Index];
		const FWheelStatus& Status = Move->GetWheelState(Index);
		W.bContact = T.bInContact;
		W.ContactCm = T.ContactPoint;
		if (SpecAsset && SpecAsset->Spec.RouteM.Num() >= 2)
		{
			W.ArcM = GTTerrain::RouteAtCm(SpecAsset->Spec, W.ContactCm.X, W.ContactCm.Y).ArcM;
		}
		W.DepthM = T.WaterDepthM;
		if (Water && T.bInContact)
		{
			if (const AGTWaterSheet* Sheet = Water->SheetAt(FVector2D(W.ContactCm.X, W.ContactCm.Y)))
			{
				W.StillDepthM = FMath::Max(0.f, Sheet->GetLevelCm() - static_cast<float>(W.ContactCm.Z)) * 0.01f;
			}
		}
		W.LoadN = T.Load * 0.01f;
		W.SpringN = T.SpringForce * 0.01f;
		W.ChaosSlip = T.SlipMagnitude;
		W.bChaosSlipping = T.bSlipping;
		W.SinkM = T.Sinkage;
		W.VisSinkM = T.VisibleSinkage;
		W.bInPatchBox = T.bInPatchBox;
		W.RadiusCm = Setup ? Setup->GetWheelRadius() : 0.f;
		W.SuspNorm = Status.NormalizedSuspensionLength;
		W.SuspOffsetCm = Setup ? Setup->GetSuspensionOffset() : 0.f;
		W.RollingResistance = T.RollingResistance;
		const float NonWater = FMath::Min(Traction->MaxRollingResistance, T.DiagSurfaceDrag + T.DiagPloughDrag + T.DiagBellyDrag + T.DiagRutDrag);
		W.WaterShare = FMath::Max(0.f, T.RollingResistance - NonWater);
		W.SurfaceDrag = T.DiagSurfaceDrag;
		W.PloughDrag = T.DiagPloughDrag;
		W.BellyDrag = T.DiagBellyDrag;
		W.RutDrag = T.DiagRutDrag;
		W.WaterDrag = T.DiagWaterDrag;
		W.SinkRate = T.DiagSinkRate;
		W.MaxSink = T.DiagMaxSink;
		W.FrictionScale = T.FrictionScale;
		W.Tag = T.SurfaceTag.IsValid() ? T.SurfaceTag.ToString().Replace(TEXT("Surface."), TEXT("")) : TEXT("-");
		const float RadiusM = FMath::Max(0.05f, W.RadiusCm * 0.01f);
		if (Train->Wheels.IsValidIndex(Index))
		{
			W.DriveNm = Train->Wheels[Index].DriveTorqueNm;
			W.CapNm = Train->Wheels[Index].CapNm;
			W.OmegaRadS = Train->Wheels[Index].OmegaRadS;
		}
		if (T.bInContact)
		{
			const float Vx = static_cast<float>(FVector::DotProduct(Mesh->GetPhysicsLinearVelocityAtPoint(T.ContactPoint), Forward)) * 0.01f;
			W.SlipRatio = (W.OmegaRadS * RadiusM - Vx) / FMath::Max(0.5f, FMath::Abs(Vx));
			S.SpringSumN += W.SpringN;
			S.LoadSumN += W.LoadN;
			S.RollingForceN += W.RollingResistance * Scale;
			S.WaterForceN += W.WaterShare * Scale + T.WaterForceN.Size();
			S.WaterForceRawN += W.WaterDrag * Scale;
		}
		S.TractiveN += W.DriveNm / RadiusM;
		S.TractiveCapN += W.CapNm / RadiusM;
	}
	return S;
}

FString GTWaterDiag::Format(const FGTWaterDiagSample& S)
{
	if (!S.bValid)
	{
		return TEXT("invalid");
	}
	FString Line = FString::Printf(
		TEXT("t=%.3f arc=%.2f off=%.2f x=%.1f y=%.1f z=%.1f pitch=%.2f roll=%.2f v=%.3f v2=%.3f vz=%.3f thr=%.2f gear=%d low=%d lock=%d rpm=%.0f eng=%.0f tqs=%.2f maxeng=%.0f flood=%d bog=%d")
		TEXT(" lc=%.3f springN=%.0f loadN=%.0f weightN=%.0f hullN=%.0f hullAlongN=%.0f liftN=%.0f liftcap=%d dragcap=%d sub=%.3f keel=%.3f rollN=%.0f waterN=%.0f waterRawN=%.0f tracN=%.0f capN=%.0f level=%.1f front=%.3f"),
		S.TimeS, S.ArcM, S.OffM, S.LocationCm.X, S.LocationCm.Y, S.LocationCm.Z, S.PitchDeg, S.RollDeg, S.SpeedMps, S.Speed2DMps, S.VerticalMps,
		S.Throttle, S.Gear, S.bLow ? 1 : 0, S.bLock ? 1 : 0, S.Rpm, S.EngineNm, S.TorqueScale, S.MaxEngineNm, S.bFlooded ? 1 : 0, S.bBogged ? 1 : 0,
		S.LoadCorrection, S.SpringSumN, S.LoadSumN, S.WeightN, S.HullDragN, S.HullDragAlongN, S.HullLiftN, S.bLiftCapped ? 1 : 0, S.bDragCapped ? 1 : 0,
		S.SubmergedM, S.KeelDepthM, S.RollingForceN, S.WaterForceN, S.WaterForceRawN, S.TractiveN, S.TractiveCapN, S.SheetLevelCm, S.FrontDepthM);
	for (int32 Index = 0; Index < S.NumWheels; ++Index)
	{
		const FGTWaterDiagWheel& W = S.Wheels[Index];
		Line += FString::Printf(
			TEXT(" | w%d c=%d a=%.2f cz=%.1f d=%.3f ds=%.3f L=%.0f sp=%.0f sr=%.3f cs=%.1f sl=%d sink=%.3f vs=%.3f pb=%d r=%.1f su=%.3f so=%.1f rr=%.3f ws=%.3f sd=%.3f pd=%.3f bd=%.3f hd=%.3f wd=%.3f rate=%.3f max=%.3f fs=%.2f tg=%s tq=%.0f cap=%.0f om=%.2f"),
			Index, W.bContact ? 1 : 0, W.ArcM, W.ContactCm.Z, W.DepthM, W.StillDepthM, W.LoadN, W.SpringN, W.SlipRatio, W.ChaosSlip, W.bChaosSlipping ? 1 : 0,
			W.SinkM, W.VisSinkM, W.bInPatchBox ? 1 : 0, W.RadiusCm, W.SuspNorm, W.SuspOffsetCm, W.RollingResistance, W.WaterShare, W.SurfaceDrag, W.PloughDrag, W.BellyDrag, W.RutDrag, W.WaterDrag,
			W.SinkRate, W.MaxSink, W.FrictionScale, *W.Tag, W.DriveNm, W.CapNm, W.OmegaRadS);
	}
	return Line;
}

void GTWaterDiag::TickCar(const AGTCarPawn& Car)
{
	const int32 Mode = CVarWaterDiag.GetValueOnGameThread();
	if (Mode <= 0)
	{
		return;
	}
	const UWorld* World = Car.GetWorld();
	if (!World)
	{
		return;
	}
	static TMap<uint32, double> LastLogged;
	double& Last = LastLogged.FindOrAdd(Car.GetUniqueID(), -1.0);
	const double Now = World->GetTimeSeconds();
	if (Mode == 1 && Last >= 0.0 && Now - Last < 0.0999 && Now >= Last)
	{
		return;
	}
	Last = Now;
	UE_LOG(LogTemp, Display, TEXT("GTWATERDIAG %s"), *Format(Measure(Car)));
}
