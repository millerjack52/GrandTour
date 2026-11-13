#include "Vehicle/GTSprayComponent.h"
#include "Vehicle/GTHullComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterDomain.h"
#include "Terrain/GTWaterInteractionVisuals.h"
#include "Terrain/GTMudRunnerWheelEffects.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<int32> CVarWaterSpray(TEXT("gt.Water.InteractionSpray"),1,TEXT("Cosmetic tyre/bow spray; 0 disables. No effect on vehicle forces."));
static TAutoConsoleVariable<int32> CVarWaterTrails(TEXT("gt.Water.InteractionTrails"),1,TEXT("Cosmetic wheel/bow foam and sediment sources in the existing local field."));

namespace
{
void Trail(UWorld* World,const FVector& At,float Radius,float Activity,float Depth,float Dt)
{
	if(!World || Activity<=0 || CVarWaterTrails.GetValueOnGameThread()==0)return;
	if(UGTWaterSubsystem* Water=World->GetSubsystem<UGTWaterSubsystem>())
		if(AGTWaterSheet* Sheet=Water->SheetAt(FVector2D(At)))
			Sheet->GetMutableField().AddRiverDetail(FVector2D(At),Radius,Activity*Dt*1.8f,
				Activity*Dt*.65f*FMath::Clamp(1.f-Depth/.8f,0.f,1.f));
}
}

void UGTSprayComponent::SpawnWater(const FVector& Origin,const FVector& Travel,const FVector& Outward,const FVector& CarVelocity,float SpeedMps,float Activity,bool bBow)
{
	if(CVarWaterSpray.GetValueOnGameThread()==0 || PoolPerKind<=0)return;
	TArray<FParticle>& Pool=Particles[static_cast<int32>(EGTSprayKind::Water)];
	if(Pool.Num()>=PoolPerKind)
	{
		int32 Oldest=0;
		for(int32 I=1;I<Pool.Num();++I)if(Pool[I].Life/Pool[I].MaxLife>Pool[Oldest].Life/Pool[Oldest].MaxLife)Oldest=I;
		Pool.RemoveAtSwap(Oldest);
	}
	const float Speed=FMath::Clamp(SpeedMps,0.f,9.f)*100;
	FParticle P;P.GroundZ=Origin.Z;
	P.Position=Origin+Outward*WaterRandom.FRandRange(0,18)+FVector(0,0,5);
	P.Velocity=CarVelocity*.55f+Outward*WaterRandom.FRandRange(.4f,.85f)*(90+Speed*.7f)
		+Travel*(bBow ? .18f : -.3f)*Speed+FVector(0,0,WaterRandom.FRandRange(100,190)+Activity*220);
	P.Size=WaterRandom.FRandRange(4,10)*( .65f+Activity*.9f );
	P.MaxLife=WaterRandom.FRandRange(.55f,.95f);P.Growth=.18f;
	const float Family=WaterRandom.FRand();
	if(Family<.30f)
	{
		// Connected thin folds at the waterline. They fan out and break quickly, never large solid blobs.
		P.WaterShape=FVector(2.6f,1.45f,.10f);P.WaterOpacity=.65f;
		P.WaterFamily=1;
		P.Size*=1.65f;P.MaxLife=WaterRandom.FRandRange(.32f,.52f);P.Growth=1.3f;
		P.Velocity.Z*=.85f;
	}
	else if(Family>.90f && Activity>.35f)
	{
		// A sparse, low-opacity mist fringe above energetic splashes, still inside the same 120 slots.
		P.WaterShape=FVector(1.f);P.WaterOpacity=.12f;
		P.WaterFamily=2;
		P.Size*=2;P.Growth=1.8f;P.Velocity.Z*=1.1f;
	}
	else
	{
		P.WaterShape=FVector(1.7f,.65f,.65f);P.WaterOpacity=1.f;P.Size*=.5f;
	}
	Pool.Add(P);++TotalSpawned;
}

void UGTSprayComponent::UpdateWaterWheel(int32 Index,float Dt,const UGTTractionComponent& Traction,const UChaosWheeledVehicleMovementComponent& Move)
{
	const bool bNativeParticles=AGTMudRunnerWheelEffects::IsActive(this);
	const FGTWheelTraction& Wheel=Traction.Wheels[Index];
	const AActor* Owner=GetOwner();const FVector Contact=Move.GetWheelState(Index).ContactPoint;
	const FVector PointVelocity=Move.UpdatedPrimitive ? Move.UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(Contact) : Owner->GetVelocity();
	const FVector Relative=FVector(PointVelocity.X-Wheel.FlowCmPerS.X,PointVelocity.Y-Wheel.FlowCmPerS.Y,0);
	// Only excess tyre slip adds spray energy; rolling tread speed is already in Relative.
	const float Slip=Wheel.bSlipping ? FMath::Abs(Wheel.SlipMagnitude)*.01f : 0.f;
	const float Speed=FMath::Sqrt(FMath::Square(float(Relative.Size()*.01))+FMath::Square(Slip*.55f));
	const float A=GTWaterInteractionVisuals::Activity(Speed,Wheel.WaterDepthM,SplashSpeedMps,SplashFullSpeedMps,SplashDepthM,SplashFullDepthM);
	if(A<=0){SplashAccumulators[Index]=0;return;}
	WaterSpeedMps=FMath::Max(WaterSpeedMps,Speed);
	bWheelSplashing=true;++SplashWheels;SplashDeepestM=FMath::Max(SplashDeepestM,Wheel.WaterDepthM);
	const float Rate=SplashRate*A;SplashRateNow+=Rate;
	const FVector Right=Owner->GetActorRightVector();
	const FVector Outward=Right*(FVector::DotProduct(Contact-Owner->GetActorLocation(),Right)>=0 ? 1.f : -1.f);
	const FVector Travel=Relative.IsNearlyZero() ? Owner->GetActorForwardVector()*(Wheel.TreadCmPerS>=0?1.f:-1.f) : Relative.GetSafeNormal();
	const FVector Origin=Contact+FVector(0,0,Wheel.WaterDepthM*100)+Outward*12;
	Dt=FMath::Clamp(Dt,0.f,.1f);
	if(bNativeParticles)SplashAccumulators[Index]=0;
	else
	{
		SplashAccumulators[Index]+=Rate*Dt;
		while(SplashAccumulators[Index]>=1){SplashAccumulators[Index]-=1;SpawnWater(Origin,Travel,Outward,PointVelocity,Speed,A,false);}
	}
	// Preserve the existing field's foam/sediment disturbance independently of
	// which renderer owns airborne particles. This remains a host field adapter.
	Trail(GetWorld(),Origin+Outward*30-Travel*35,75,A,Wheel.WaterDepthM,Dt);
}

void UGTSprayComponent::UpdateWaterBow(float Dt,const UGTTractionComponent& Traction,const UChaosWheeledVehicleMovementComponent& Move,const UGTHullComponent* Hull)
{
	BowSubmergedM=Hull ? Hull->SubmergedHeightM : 0;BowRateNow=0;bBowSpraying=false;
	UGTWaterSubsystem* Water=GetWorld()->GetSubsystem<UGTWaterSubsystem>();
	if(!Hull || !Water)
	{BowAccumulators[0]=BowAccumulators[1]=0;return;}
	const AActor* Owner=GetOwner();const FTransform Frame=Owner->GetActorTransform();
	const FVector Velocity=Move.UpdatedPrimitive ? Move.UpdatedPrimitive->GetPhysicsLinearVelocity() : Owner->GetVelocity();
	float WetDepth=0;int32 WetTyres=0;FVector2D WetFlow=FVector2D::ZeroVector;
	for(const FGTWheelTraction& Wheel:Traction.Wheels)
	{
		if(!Wheel.bInContact || Wheel.WaterDepthM<=SplashDepthM || !Water->SheetAt(FVector2D(Wheel.ContactPoint)))continue;
		WetDepth+=Wheel.WaterDepthM;WetFlow+=Wheel.FlowCmPerS;++WetTyres;
	}
	const float WakeImmersion=GTWaterInteractionVisuals::WakeImmersionM(BowSubmergedM,
		WetTyres?WetDepth/WetTyres:0,float(WetTyres)/FMath::Max(1,Traction.Wheels.Num()));
	FVector2D Flow=WetTyres ? WetFlow/WetTyres : Hull->LastFlowMps*100;
	// Direction must not chase the tyre/hull's own disturbed local current.
	// Use the authored mean for this cosmetic pressure front only; forces and
	// individual tyre spray continue to sample the live fluid.
	FVector2D MeanFlow=FVector2D::ZeroVector;int32 MeanSamples=0;
	for(const FGTWheelTraction& Wheel:Traction.Wheels)
	{
		if(!Wheel.bInContact || Wheel.WaterDepthM<=SplashDepthM)continue;
		if(const AGTWaterSheet* Sheet=Water->SheetAt(FVector2D(Wheel.ContactPoint)))
			if(Sheet->WaterDomain)
			{
				float Surface,Depth;FVector2D V;
				if(Sheet->WaterDomain->Sample(FVector2D(Wheel.ContactPoint),Surface,Depth,V)){MeanFlow+=V*100;++MeanSamples;}
			}
	}
	if(MeanSamples)Flow=MeanFlow/MeanSamples;
	if(const AGTWaterSheet* Sheet=Water->SheetAt(FVector2D(Owner->GetActorLocation())))
		if(Sheet->WaterDomain)
		{
			float Surface,Depth;FVector2D V;
			if(Sheet->WaterDomain->Sample(FVector2D(Owner->GetActorLocation()),Surface,Depth,V))Flow=V*100;
		}
	const FVector Relative=FVector(Velocity.X-Flow.X,Velocity.Y-Flow.Y,0);
	const float Speed=Relative.Size()*.01f;WaterSpeedMps=FMath::Max(WaterSpeedMps,Speed);
	// Surface pressure starts below the spray threshold. Gating this registration
	// on BowSprayHeightM suppressed shallow wakes despite wet hull contact.
	if(WakeImmersion>GTWaterInteractionVisuals::VehicleWaveStartDepthM)
	{
		const FVector2D Travel=FVector2D(Relative).GetSafeNormal();
		const FVector2D Forward=FVector2D(Owner->GetActorForwardVector()).GetSafeNormal();
		const float C=FMath::Abs(FVector2D::DotProduct(Travel,Forward)),S=FMath::Sqrt(FMath::Max(0.f,1-C*C));
		auto Register=[&](AGTWaterSheet* Sheet)
		{
			if(Sheet)Sheet->SetVisualVehicleWake(GetOwner(),FVector2D(Owner->GetActorLocation()),Travel,
				50*(Hull->HullLengthM*C+Hull->HullWidthM*S),50*(Hull->HullWidthM*C+Hull->HullLengthM*S),Speed,WakeImmersion);
		};
		Register(Water->SheetAt(FVector2D(Owner->GetActorLocation())));
		// The first wet tyre can precede the actor centre and hull contact.
		for(const FGTWheelTraction& Wheel:Traction.Wheels)
			if(Wheel.bInContact && Wheel.WaterDepthM>SplashDepthM)Register(Water->SheetAt(FVector2D(Wheel.ContactPoint)));
	}
	// Surface waves can start at the tyres; airborne bow spray still requires a wet hull.
	if(BowSubmergedM<=FMath::Min(BowSprayHeightM,GTWaterInteractionVisuals::VehicleWaveStartDepthM))
	{BowAccumulators[0]=BowAccumulators[1]=0;return;}
	float BaseZ=0;int32 Contacts=0;
	for(const FGTWheelTraction& W:Traction.Wheels)if(W.bInContact){BaseZ+=Frame.InverseTransformPosition(W.ContactPoint).Z;++Contacts;}
	if(Contacts)BaseZ/=Contacts;
	const FVector LocalV=Frame.InverseTransformVectorNoScale(Relative);
	const bool Front=FMath::Abs(LocalV.X)>=FMath::Abs(LocalV.Y);
	const FVector Face=Front ? FVector(FMath::Sign(LocalV.X)*Hull->HullLengthM*50,0,BaseZ) : FVector(0,FMath::Sign(LocalV.Y)*Hull->HullWidthM*50,BaseZ);
	const FVector Across=Front ? Frame.GetUnitAxis(EAxis::Y) : Frame.GetUnitAxis(EAxis::X);
	const float Span=Front ? Hull->HullWidthM*50 : Hull->HullLengthM*50;
	const FVector Centre=Frame.TransformPosition(Face),Travel=Relative.GetSafeNormal();
	Dt=FMath::Clamp(Dt,0.f,.1f);
	// Query both leading corners, including pitch/roll. A wet rear axle never sprays from a dry bonnet.
	for(int32 Side:{-1,1})
	{
		FVector Origin=Centre+Across*((Span+12)*Side)+Travel*15;
		const FGTWaterSample Sample=Water->Sample(Origin);
		float& BowAccumulator=BowAccumulators[Side<0?0:1];
		if(Sample.Kind!=EGTWaterKind::Ford){BowAccumulator=0;continue;}
		// Leading tyres/corners can enter before the actor centre is over water.
		// Register on that wet sheet too, so the visible entry bow is not delayed.
		if(BowSubmergedM>GTWaterInteractionVisuals::VehicleWaveStartDepthM && Sample.DepthCm>GTWaterInteractionVisuals::VehicleWaveStartDepthM*100)
		{
			if(AGTWaterSheet* EntrySheet=Water->SheetAt(FVector2D(Origin)))
			{
				const FVector2D T=FVector2D(Travel).GetSafeNormal(),F=FVector2D(Owner->GetActorForwardVector()).GetSafeNormal();
				const float C=FMath::Abs(FVector2D::DotProduct(T,F)),S=FMath::Sqrt(FMath::Max(0.f,1-C*C));
				EntrySheet->SetVisualVehicleWake(GetOwner(),FVector2D(Owner->GetActorLocation()),T,
					50*(Hull->HullLengthM*C+Hull->HullWidthM*S),50*(Hull->HullWidthM*C+Hull->HullLengthM*S),Speed,WakeImmersion);
			}
		}
		// Spray retains its original hull and corner depth gates; only surface
		// pressure registration is allowed through the shallower branch above.
		const float A=BowSubmergedM>BowSprayHeightM ? GTWaterInteractionVisuals::Activity(Speed,Sample.DepthCm*.01f,BowSprayMps,BowSprayFullSpeedMps,BowSprayHeightM,BowSprayFullHeightM) : 0.f;
		if(A<=0){BowAccumulator=0;continue;}
		Origin.Z=Sample.SurfaceZCm;const FVector Outward=Across*Side;
		bBowSpraying=true;const float Rate=BowSprayRate*.5f*A;BowRateNow+=Rate;
		// Independent clocks keep both fans alive even at a slow crawl.
		BowAccumulator+=Rate*Dt;
		while(BowAccumulator>=1){BowAccumulator-=1;SpawnWater(Origin,Travel,Outward,Velocity,Speed,A,true);}
		Trail(GetWorld(),Origin+Travel*45+Outward*30,105,A,Sample.DepthCm*.01f,Dt);
	}
	if(!bBowSpraying)BowAccumulators[0]=BowAccumulators[1]=0;
}
