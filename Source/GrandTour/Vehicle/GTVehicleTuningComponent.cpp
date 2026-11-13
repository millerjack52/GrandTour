#include "Vehicle/GTVehicleTuningComponent.h"
#include "Terrain/GTWaterSubsystem.h"

#include "Environment/GTEnvironmentComponent.h"
#include "Parts/GTPartSlotsComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTMudContactModel.h"
#include "Vehicle/GTSoilVehicleMovement.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LandscapeProxy.h"

#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/PrimitiveComponent.h"

UGTVehicleTuningComponent::UGTVehicleTuningComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick after traction and condition
}

void UGTVehicleTuningComponent::CaptureBase(const UChaosWheeledVehicleMovementComponent& Movement)
{
	const int32 NumWheels = Movement.WheelSetups.Num();
	if (Movement.Wheels.Num() < NumWheels)
	{
		return;   // Chaos has not created its wheels yet
	}
	Base.MaxEngineTorque = Movement.EngineSetup.MaxTorque;
	Base.TorqueScale = 1.f;
	Base.SteeringBias = 0.f;
	Base.DragCoefficient = Movement.DragCoefficient;
	Base.RollingScale = 1.f;
	Base.Wheels.SetNum(NumWheels);
	BaseWheelFriction.SetNum(NumWheels);
	AppliedWheelFriction.Init(-1.f, NumWheels);
	AppliedSlipGraph.Init(-1.f, NumWheels);
	BaseWheelRadius.SetNum(NumWheels);
	AppliedWheelRadius.Init(-1.f, NumWheels);
	GroundSupportCm.Init(0.f, NumWheels);
	MudYieldCm.Init(0.f, NumWheels);
	for (int32 Index = 0; Index < NumWheels; ++Index)
	{
		const UChaosVehicleWheel* Wheel = Movement.Wheels[Index];
		BaseWheelFriction[Index] = Wheel ? Wheel->FrictionForceMultiplier : 1.f;
		BaseWheelRadius[Index] = Wheel ? Wheel->WheelRadius : 38.f;
		Base.Wheels[Index] = FGTWheelTuning();
	}
	bBaseCaptured = true;
}

void UGTVehicleTuningComponent::UpdateAndApply(float DeltaSeconds, UChaosWheeledVehicleMovementComponent& Movement,
                                               const UGTTractionComponent* Traction, const UGTConditionComponent* Condition,
                                               const UGTEnvironmentComponent* Environment, const UGTPartSlotsComponent* Parts)
{
	if (!bBaseCaptured)
	{
		CaptureBase(Movement);
		if (!bBaseCaptured)
		{
			return;
		}
	}
	Current = Base;
	if (Parts)
	{
		Parts->ModifyTuning(Current);   // installed parts first: the base is the bare chassis
	}
	if (Traction)
	{
		Traction->ModifyTuning(Current);
		ApplyLandscapeSupport(DeltaSeconds, Movement, *Traction);
	}
	if (Environment)
	{
		Environment->ModifyTuning(Current);   // ARCHITECTURE 6c: the environment stage sits between traction and condition
	}
	if (Condition)
	{
		Condition->ModifyTuning(Current);
	}
	Current.TorqueScale = FMath::Clamp(Current.TorqueScale, 0.f, 2.f);
	Current.SteeringBias = FMath::Clamp(Current.SteeringBias, -1.f, 1.f);
	Apply(Movement);
	ApplyRollingResistance(Movement);
}

void UGTVehicleTuningComponent::ApplyLandscapeSupport(float Dt, UChaosWheeledVehicleMovementComponent& Movement, const UGTTractionComponent& Traction)
{
	auto* SoilMove=Cast<UGTSoilVehicleMovement>(&Movement);
	TArray<FGTSoilContact> Contacts;Contacts.SetNum(Current.Wheels.Num());
	for (int32 I=0;I<Current.Wheels.Num();++I)
	{
		auto& T=Current.Wheels[I];
		FGTLandscapeSurfaceSample S;
		FHitResult SoilGround;
		if (Traction.Wheels.IsValidIndex(I))
		{
			const auto& W=Traction.Wheels[I];
			const float Width=Movement.Wheels.IsValidIndex(I) && Movement.Wheels[I] ? Movement.Wheels[I]->WheelWidth : 25.f;
			if(SoilMove && Movement.Wheels.IsValidIndex(I) && Movement.Wheels[I])
			{
				// Terrain must exist before contact is solved, including while airborne.
				// Using the previous contact made a dropped wheel alternate between the
				// buried mud floor and the original landscape. Query from the current
				// suspension origin instead, so recovery/teleports cannot retain stale XY.
				const UChaosVehicleWheel* Wheel=Movement.Wheels[I];
				const FVector Origin=SoilMove->SoilQueryOrigin(I);
				FCollisionQueryParams Params(SCENE_QUERY_STAT(MudContactSnapshot),false,GetOwner());
				if(GetWorld()->LineTraceSingleByChannel(SoilGround,Origin+FVector(0,0,Wheel->SuspensionMaxRaise+64),
					Origin-FVector(0,0,Wheel->SuspensionMaxDrop+Wheel->WheelRadius+128),ECC_Visibility,Params))
					S=AGTLandscapeSurface::QueryWheelSurface(GetOwner(),SoilGround.ImpactPoint,W.TyreHeading,Width);
			}
			else if(W.bInContact)
				S=AGTLandscapeSurface::QueryWheelSurface(GetOwner(),W.ContactPoint,W.TyreHeading,Width);
		}
		if(SoilMove && S.bAuthored && S.bNativeWaterResponse && Movement.Wheels.IsValidIndex(I) && Movement.Wheels[I])
		{
			auto& C=Contacts[I];const auto* Wheel=Movement.Wheels[I].Get();
			C.bNativeWater=true;C.WidthCm=Wheel->WheelWidth;C.NativeWheelMass=Wheel->WheelMass;
			C.NativeMassPerWheel=Movement.Mass/FMath::Max(1,Current.Wheels.Num());
			if(const auto* Water=GetWorld()->GetSubsystem<UGTWaterSubsystem>())
			{
                const auto Sample=Water->Sample(SoilMove->SoilWheelCentre(I)-FVector(0,0,Wheel->WheelRadius));
				C.NativeWaterDepth=Sample.DepthCm*.01;C.NativeFlow=FVector(Sample.FlowCmPerS,0)*.01;
			}
		}
		const float SupportFloor=S.bSoilShearResponse ? -S.SinkageCapCm : -FMath::Min(20.f,BaseWheelRadius[I]*.55f);
		const float Target=S.bWheelSupport ? FMath::Clamp(S.WheelSupportCm,SupportFloor,12.f) : 0.f;
		GroundSupportCm[I]=FMath::FInterpConstantTo(GroundSupportCm[I],Target,FMath::Clamp(Dt,0.f,.1f),60.f);
		T.GroundSupportCm=GroundSupportCm[I];T.bLandscapeSupport=S.bWheelSupport;
		if (!S.bWheelSupport)
		{
			MudYieldCm[I]=0.f;
			continue;
		}
		// Permanent compression is already in the field. Additional loaded penetration
		// models yielding soil under the tyre, without stamping that depth into every rut.
		const float Compression=FMath::Max(0.f,S.RestWheelSupportCm-T.GroundSupportCm);
		const float Firmed=FMath::Clamp(Compression/12.f,0.f,1.f);
		const float Load=FMath::Clamp(Traction.Wheels[I].Load/FMath::Max(1.f,Movement.Mass*980.f/Current.Wheels.Num()),0.f,1.6f);
		const float YieldTarget=FMath::Max(2.f*S.Softness*FMath::Lerp(1.f,.3f,S.GrassCover),
			S.LoadedSettlementCm(Load)-Compression);
		// The physical support point must stay above the painted mineral base, including
		// footprint averaging and rate-limited relief following.
		const float Available=FMath::Max(0.f,S.SinkageCapCm+T.GroundSupportCm);
		// Relief and penetration together must retain a positive collision radius,
		// including vehicles with smaller wheels than the study estate.
		const float DeepCap=S.MaximumSettlementCm();
		const float YieldCap=FMath::Max(0.f,FMath::Min3(DeepCap,Available,BaseWheelRadius[I]*.8f+T.GroundSupportCm));
		const float YieldRate=YieldTarget>MudYieldCm[I] ? FMath::Lerp(5.f,12.f,S.Softness)*S.SettlementSpeedScale : 20.f;
		MudYieldCm[I]=FMath::Clamp(FMath::FInterpConstantTo(MudYieldCm[I],FMath::Min(YieldTarget,YieldCap),FMath::Clamp(Dt,0.f,.1f),YieldRate),0.f,YieldCap);
		T.SinkageCm=MudYieldCm[I];
		if(SoilMove)
		{
			const auto& W=Traction.Wheels[I];auto& C=Contacts[I];
			const FHitResult& Hit=SoilGround;
			if(Hit.bBlockingHit)
			{
				C.bActive=true;C.Component=Hit.Component;C.Centre=FVector2D(Hit.ImpactPoint);
				C.Penetration=T.SinkageCm;C.TotalSink=Compression+T.SinkageCm;
				C.Softness=S.Softness;C.Grass=S.GrassCover;C.LoadCorrection=T.LoadCorrection;
				C.SoilState={S.bSoilShearResponse,S.Wetness,S.Cohesion,S.Disturbance,Compression,S.bGranularResponse};
				AGTLandscapeSurface* Source=nullptr;
				for(TActorIterator<AGTLandscapeSurface> It(GetWorld());It;++It)
					if(It->bEnableWheelSupport && It->OwnsGroundActor(Hit.GetActor())) { Source=*It;break; }
				C.bActive=Source!=nullptr;
				C.bRutInteraction=Source && Source->bUseRutInteraction;
				C.Heading=W.TyreHeading;
				C.WidthCm=Movement.Wheels.IsValidIndex(I) && Movement.Wheels[I] ? Movement.Wheels[I]->WheelWidth : 25.f;
                C.bNativeSubstance=Source && S.bNativeSubstanceResponse;
				// Native H and coarse physical E are separate from visible mud displacement.
				C.NativeQ=S.NativeExtrudeCm*.01f;
				// CL2: clay's own substance numbers and, wet, a slicker Chaos tyre (T.FrictionScale; the sample's FrictionScale is only applied on the non-soil path below).
				C.NativeFriction=S.NativeFriction;C.NativeLinearResistance=S.NativeLinearResistance;C.NativePushResistance=S.NativePushResistance;C.Clay=S.ClayWeight;
				T.FrictionScale*=S.ClayFrictionScale;
				const auto LandscapeH=Source?Source->GroundHeightAt(W.ContactPoint):TOptional<float>();
				C.NativeDepth=FMath::Max(0.f,float((LandscapeH.IsSet()?LandscapeH.GetValue():Hit.ImpactPoint.Z)+S.NativeUpperCm-W.ContactPoint.Z))*.01f;
				if(!C.bNativeWater){C.NativeWaterDepth=W.WaterDepthM;C.NativeFlow=FVector(W.FlowCmPerS,0)*.01;}
				C.NativeMassPerWheel=Movement.Mass/FMath::Max(1,Current.Wheels.Num());
				C.NativeWheelMass=Movement.Wheels.IsValidIndex(I) && Movement.Wheels[I] ? Movement.Wheels[I]->WheelMass : 20.f;
				// Legacy traction reports travel direction outside patch actors. Rut forces
				// require the actual steered tyre axis, otherwise lateral velocity vanishes.
				if(C.bRutInteraction && Movement.UpdatedPrimitive && Movement.Wheels.IsValidIndex(I) && Movement.Wheels[I])
					C.Heading=FVector2D(Movement.UpdatedPrimitive->GetForwardVector()).GetSafeNormal().GetRotated(Movement.Wheels[I]->GetSteerAngle());
				if(!C.bNativeSubstance)
				{
					for(int32 Y=0;Source && Y<FGTSoilContact::Side;++Y) for(int32 X=0;X<FGTSoilContact::Side;++X)
					{
						const FVector2D P=C.Centre+FVector2D(X-4,Y-4)*FGTSoilContact::Spacing;
						C.Height[Y*FGTSoilContact::Side+X]=Source->ContactHeightCm(P,false);
					}
					// Native contacts replace this grid entirely; only legacy contacts
					// need footprint bias and the settlement floor.
					const float HeightBias=T.GroundSupportCm-C.Height[4*FGTSoilContact::Side+4];
					for(float& Height : C.Height) Height=FMath::Max(Height+HeightBias,-S.SinkageCapCm+C.Penetration);
				}
				if(C.bNativeSubstance)
				{
					C.Penetration=0;C.TotalSink=C.NativeDepth*100;T.SinkageCm=C.TotalSink;
					for(int32 Y=0;Y<FGTSoilContact::Side;++Y)for(int32 X=0;X<FGTSoilContact::Side;++X)
					{
						C.Height[Y*FGTSoilContact::Side+X]=Source->ContactHeightCm(C.Centre+FVector2D(X-4,Y-4)*FGTSoilContact::Spacing,true);
					}
				}
				const FVector V=Movement.UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(W.ContactPoint);
				const float Forward=FVector2D::DotProduct(FVector2D(V),W.TyreHeading);
				const auto Response=GTMudContact::Evaluate(S.Softness,S.GrassCover,C.TotalSink,BaseWheelRadius[I],Forward,W.TreadCmPerS,C.SoilState);
				T.SoilGrip=Response.Grip;T.SoilSlip=Response.Slip;T.SoilDragN=Response.Resistance*W.Load*.01f;
				T.SoilContactOffsetCm=T.GroundSupportCm-T.SinkageCm;
				// The simulation applies this soil resistance at each wheel, once per step.
				T.RollingResistance=0.f;
			}
		}
		else
		{
			T.FrictionScale*=S.FrictionScale;
			T.RollingResistance+=FMath::Lerp(.025f,.065f,S.Softness)*FMath::Lerp(1.f,.45f,Firmed)*FMath::Lerp(1.f,.4f,S.GrassCover);
		}
	}
	if(SoilMove) SoilMove->SetSoilContacts(Contacts);
}

void UGTVehicleTuningComponent::Apply(UChaosWheeledVehicleMovementComponent& Movement)
{
	const float Torque = Current.MaxEngineTorque * Current.TorqueScale;
	if (!FMath::IsNearlyEqual(Torque, AppliedTorque, 0.5f))
	{
		Movement.SetMaxEngineTorque(Torque);
		AppliedTorque = Torque;
	}
	if (!FMath::IsNearlyEqual(Current.DragCoefficient, AppliedDrag, 0.001f))
	{
		Movement.SetDragCoefficient(Current.DragCoefficient);
		AppliedDrag = Current.DragCoefficient;
	}
	const int32 Count = FMath::Min(Current.Wheels.Num(), BaseWheelFriction.Num());
	for (int32 Index = 0; Index < Count; ++Index)
	{
		// Chaos's friction circle is its spring-based load x surface friction x this multiplier; LoadCorrection turns
		// that load into the true one (UGTTractionComponent), the rest is the tyre's state.
		const float Friction = BaseWheelFriction[Index] * Current.Wheels[Index].FrictionScale * Current.Wheels[Index].LoadCorrection;
		if (!FMath::IsNearlyEqual(Friction, AppliedWheelFriction[Index], 0.005f))
		{
			Movement.SetWheelFrictionMultiplier(Index, Friction);
			AppliedWheelFriction[Index] = Friction;
		}
		// The lateral slip graph is written in fractions of the grip available (GTVehicleWheel.cpp): scale it by the
		// true load x surface friction x the tyre's multiplier so a loaded outer wheel gives more, an unloaded one less.
		const float SlipGraph = Current.Wheels[Index].SlipGraphScale * BaseWheelFriction[Index] * Current.Wheels[Index].FrictionScale;
		if (!FMath::IsNearlyEqual(SlipGraph, AppliedSlipGraph[Index], FMath::Max(0.05f, FMath::Abs(AppliedSlipGraph[Index]) * 0.01f)))
		{
			Movement.SetWheelSlipGraphMultiplier(Index, SlipGraph);
			AppliedSlipGraph[Index] = SlipGraph;
		}
		// Sinking (stage 3): the wheel's contact drops by the sinkage, so the suspension droops and then the body follows
		// into the mud, while the drawn wheel keeps its size and buries itself; capped at "sunk to the rims".
		const bool SoilContact=Current.Wheels[Index].bLandscapeSupport && Movement.IsA<UGTSoilVehicleMovement>();
		const float Radius = SoilContact ? BaseWheelRadius[Index] : BaseWheelRadius[Index] - FMath::Min(FMath::Max(0.f, Current.Wheels[Index].SinkageCm), MaxVisibleSinkFraction * BaseWheelRadius[Index]) + Current.Wheels[Index].GroundSupportCm;
		if (!FMath::IsNearlyEqual(Radius, AppliedWheelRadius[Index], 0.5f))
		{
			Movement.SetWheelRadius(Index, Radius);
			AppliedWheelRadius[Index] = Radius;
		}
	}
}

void UGTVehicleTuningComponent::ApplyRollingResistance(UChaosWheeledVehicleMovementComponent& Movement) const
{
	UPrimitiveComponent* Body = Movement.UpdatedPrimitive;
	if (!Body || Current.Wheels.Num() == 0)
	{
		return;
	}
	const FVector Velocity = Body->GetPhysicsLinearVelocity();
	const float Speed = Velocity.Size();
	if (Speed < 1.f)
	{
		return;
	}
	float TotalCoefficient = 0.f;
	for (const FGTWheelTuning& Wheel : Current.Wheels)
	{
		if (Wheel.bInContact)
		{
			TotalCoefficient += Wheel.RollingResistance;
		}
	}
	if (TotalCoefficient <= 0.f)
	{
		return;
	}
	const float LoadPerWheel = Movement.Mass * 980.f / Current.Wheels.Num();   // kg cm/s^2
	const float Fade = FMath::Clamp(Speed / FMath::Max(1.f, DragFadeSpeed), 0.f, 1.f);
	Body->AddForce(-Velocity / Speed * TotalCoefficient * FMath::Max(0.f, Current.RollingScale) * LoadPerWheel * Fade);
}
