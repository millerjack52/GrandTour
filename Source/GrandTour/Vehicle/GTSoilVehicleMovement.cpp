#include "Vehicle/GTSoilVehicleMovement.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTFerrariHandling.h"
#include "Vehicle/GTPersistentWheelSpin.h"
#include "Vehicle/GTSlideRecovery.h"
#include "HAL/IConsoleManager.h"
#include "Terrain/GTMudContactModel.h"
#include "Terrain/GTMudRunnerSubstance.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Engine/World.h"
#include "ChaosVehicleWheel.h"
#include "Terrain/GTRoadReliefTile.h"
#include "Terrain/GTLandscapeSurface.h"
#include "PhysicsEngine/BodySetup.h"
#include "Chaos/PBDSuspensionConstraintData.h"
#include "PhysicsProxy/SuspensionConstraintProxy.h"
#include "Vehicle/GTRangeRoverSuspension.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "Parts/GTPartSlotsComponent.h"

static TAutoConsoleVariable<int32> CVarGTSlideRecovery(TEXT("gt.Vehicle.SlideRecovery"),1,
    TEXT("High-speed post-peak lateral grip retention. 0 restores the original tyre response; 1 enables per-car strength."));
static TAutoConsoleVariable<int32> CVarGTRallyRide(TEXT("gt.Vehicle.RallyRide"),1,
    TEXT("Firm-ground suspension compliance above 30-60 km/h. 0 restores authored suspension. Low range/mud/water bypass."));
static TAutoConsoleVariable<int32> CVarGTPersistentSpin(TEXT("gt.Vehicle.PersistentSpin"),1,
    TEXT("Retain wheel angular momentum on firm ground for independent-engine cars. 0 enables the legacy wheel solver for comparison."));

bool FGTSoilContact::Sample(FVector2D XY,float& OutHeight,FVector2D& OutSlope) const
{
    const FVector2D P=(XY-Centre)/Spacing+FVector2D(4,4);
    if(!bActive || P.X<0 || P.Y<0 || P.X>=8 || P.Y>=8) return false;
    const int32 X=FMath::FloorToInt(P.X),Y=FMath::FloorToInt(P.Y);
    const float U=P.X-X,V=P.Y-Y;
    const float A=Height[Y*Side+X],B=Height[Y*Side+X+1],C=Height[(Y+1)*Side+X],D=Height[(Y+1)*Side+X+1];
    OutHeight=FMath::Lerp(FMath::Lerp(A,B,U),FMath::Lerp(C,D,U),V);
    OutSlope=FVector2D(FMath::Lerp(B-A,D-C,V),FMath::Lerp(C-A,D-B,U))/Spacing;
    return true;
}

float FGTSoilContact::EntryRise(FVector2D XY,FVector2D Direction,float ReachCm) const
{
    Direction=Direction.GetSafeNormal();
    const FVector2D Across(-Direction.Y,Direction.X);
    float Rise=0;int32 Count=0;
    for(float Offset : {-8.f,0.f,8.f})
    {
        float Base=0,Bank=0;FVector2D Slope;
        const FVector2D P=XY+Across*Offset;
        if(Sample(P,Base,Slope) && Sample(P+Direction*ReachCm,Bank,Slope))
        {
            Rise+=Bank-Base;++Count;
        }
    }
    return Count ? FMath::Max(0.f,Rise/Count) : 0.f;
}

class FGTSoilVehicleSimulation final : public UChaosWheeledVehicleSimulation
{
public:
    TArray<FGTSoilContact> Contacts;
    TArray<bool> ActiveHits;
    TArray<FGTBodySoilContact> BodyContacts;
    bool bLowRange=false;
    bool bFerrari=false;
    bool bIndependentEngine=false;
    bool bPersistentSpin=false;
    TArray<float> ReflectedEngineInertia;
    float CountersteerWeight=0.f;
    float SlideRecovery=0.f;
    float LastFilteredSteering=0.f;
    TArray<Chaos::FSimpleSuspensionConfig> OriginalSuspension,OwnedSuspension;
    TArray<float> OriginalRollbars;
    float RideScale=1.f;
    void OwnSuspension()
    {
        if(!OriginalSuspension.IsEmpty())return;
        for(const auto& Spring:PVehicle->Suspension)OriginalSuspension.Add(Spring.Setup());
        OwnedSuspension=OriginalSuspension;
        // Chaos setup pointers normally refer to wheel-class configuration. Never
        // mutate a shared class, or repeatedly allocate new suspension constraints.
        for(int32 I=0;I<PVehicle->Suspension.Num();++I)PVehicle->Suspension[I].SetupPtr=&OwnedSuspension[I];
        for(const auto& Axle:PVehicle->Axles)OriginalRollbars.Add(Axle.Setup.RollbarScaling);
    }
    TArray<FVector2D> SlideGraphPeaks;
    double BodyPeakPenetration=0,BodyForceN=0,BodyMinBaseGap=0;uint64 BodySteps=0;
    double BankWorkJ=0, LateralBankWorkJ=0, BankPeakN=0, BankTotalMs=0, BankPeakMs=0;
    uint64 BankSteps=0;
    uint64 NativeSteps=0,NativeWaterSteps=0;double NativeLinearImpulse=0,NativeAngularImpulse=0,NativeSeconds=0,NativeMaxWaterDepth=0;
    FString RallyReport() const
    {
        if(!PVehicle)return TEXT("{}");
        FString Result=FString::Printf(TEXT("{\"filtered\":%.6f,\"ride_scale\":%.6f,\"countersteer_weight\":%.6f,\"persistent_spin\":%s,\"wheels\":["),LastFilteredSteering,RideScale,CountersteerWeight,bPersistentSpin?TEXT("true"):TEXT("false"));
        for(int32 I=0;I<PVehicle->Wheels.Num();++I)
        {
            const auto& W=PVehicle->Wheels[I];const FVector F=W.GetForceFromFriction();
            Result+=FString::Printf(TEXT("%s{\"angle\":%.5f,\"slip_deg\":%.5f,\"fx_n\":%.3f,\"fy_n\":%.3f,\"load_n\":%.3f,\"contact\":%s}"),
                I?TEXT(","):TEXT(""),W.GetSteeringAngle(),FMath::RadiansToDegrees(W.GetSlipAngle()),F.X*.01,F.Y*.01,W.GetWheelLoadForce()*.01,W.InContact()?TEXT("true"):TEXT("false"));
        }
        return Result+TEXT("]}");
    }
    virtual void ProcessSteering(const FControlInputs& Inputs) override
    {
        LastFilteredSteering=Inputs.SteeringInput;
        UChaosWheeledVehicleSimulation::ProcessSteering(Inputs);
        CountersteerWeight=bFerrari ? GTFerrariHandling::CountersteerWeight(Inputs.SteeringInput,
            VehicleState.VehicleLocalVelocity.X,VehicleState.VehicleLocalVelocity.Y,bLowRange) : 0.f;
        if(!bFerrari || bLowRange || !PVehicle) return;
        auto& Steering=PVehicle->GetSteering();
        // The Ferrari's shorter wheelbase needs useful turn-in before it runs
        // onto the verge. Retain speed sensitivity and the authored full lock.
        const float BaseScale=FMath::Min(1.f,Steering.GetSteeringFromVelocity(VehicleState.ForwardSpeed*.02236936f)*1.25f);
        const float Scale=FMath::Lerp(BaseScale,1.f,CountersteerWeight);
        for(int32 I=0;I<PVehicle->Wheels.Num();++I)
        {
            auto& Wheel=PVehicle->Wheels[I];
            if(!Wheel.SteeringEnabled) continue;
            const float Side=PVehicle->GetSuspension(I).GetLocalRestingPosition().Y;
            Wheel.SetSteeringAngle(Steering.GetSteeringAngle(Inputs.SteeringInput*Scale,Wheel.MaxSteeringAngle,Side));
        }
    }
    virtual void PerformSuspensionTraces(const TArray<Chaos::FSuspensionTrace>& Traces,FCollisionQueryParams& Params,
        FCollisionResponseContainer& Response,TArray<FWheelTraceParams>& WheelParams) override
    {
        UChaosWheeledVehicleSimulation::PerformSuspensionTraces(Traces,Params,Response,WheelParams);
        ActiveHits.Init(false,Traces.Num());
        for(int32 I=0;I<Traces.Num();++I)
        {
            if(!Contacts.IsValidIndex(I) || !Contacts[I].bActive) continue;
            const auto& S=Contacts[I];auto& Hit=WheelState.TraceResult[I];
            // Extend only the soil query. Ordinary obstacle/bridge hits retain Chaos contact.
            FHitResult Ground=Hit;
            FCollisionResponseParams Responses;Responses.CollisionResponse=Response;
            if(!Ground.bBlockingHit)
                World->LineTraceSingleByChannel(Ground,Traces[I].Start+FVector(0,0,60),Traces[I].End-FVector(0,0,60),ECC_WorldDynamic,Params,Responses);
            if(!Ground.bBlockingHit || Ground.Component!=S.Component) continue;
            float Height=0;FVector2D Slope;
            if(!S.Sample(FVector2D(Ground.ImpactPoint),Height,Slope)) continue;
            Hit=Ground;
            Hit.ImpactPoint.Z+=Height-S.Penetration;
            // Keep macro landscape slope; cap sub-tyre roughness so individual texels
            // cannot turn a suspension support into a vertical wall.
            const FVector2D B(-Ground.Normal.X/FMath::Max(.2,Ground.Normal.Z),-Ground.Normal.Y/FMath::Max(.2,Ground.Normal.Z));
            // A yielding rut wall cannot act like a rigid kerb. Keep landscape
            // grade, but soften the small-scale soil normal under the loaded tyre.
            const float Firmness=1.f-FMath::Clamp(S.Softness,0.f,1.f);
            const float SoilSlopeLimit=S.SoilState.Enabled
                ? .11f+.16f*Firmness+.10f*S.SoilState.Cohesion*(1.f-S.SoilState.Wetness)
                : .06f+.16f*Firmness*Firmness+.12f*S.Grass;
            Slope=B+Slope.GetClampedToMaxSize(SoilSlopeLimit);
            Hit.Normal=Hit.ImpactNormal=FVector(-Slope.X,-Slope.Y,1).GetSafeNormal();
            const bool Sphere=WheelParams[I].SweepShape==ESweepShape::Spherecast;
            Hit.Location=Hit.ImpactPoint+(Sphere ? Hit.Normal*PVehicle->Wheels[I].GetEffectiveRadius() : FVector::ZeroVector);
            const FVector Start=Traces[I].Start+(Sphere ? VehicleState.VehicleUpAxis*PVehicle->Wheels[I].GetEffectiveRadius() : FVector::ZeroVector);
            Hit.Distance=FVector::Distance(Start,Hit.Location);
            Hit.Time=FMath::Clamp(Hit.Distance/FMath::Max(1.,FVector::Distance(Start,Traces[I].End)),0.,1.);
            Hit.bBlockingHit=FVector::DotProduct(Hit.Location-Traces[I].End,VehicleState.VehicleUpAxis)>=0;
            ActiveHits[I]=Hit.bBlockingHit;
        }
    }
    virtual void ApplyWheelFrictionForces(float Dt) override
    {
        // Preserve pre-step momentum: native Chaos replaces grounded omega with
        // road omega plus only this frame's excess torque, making slip depend on dt.
        TArray<FVector2D,TInlineAllocator<8>> PreviousSpin;
        bPersistentSpin=bIndependentEngine && !bLowRange && CVarGTPersistentSpin.GetValueOnAnyThread()!=0;
        for(const auto& C:Contacts)
            if(C.Softness>.15f || C.bNativeSubstance || C.NativeWaterDepth>.01f || C.TotalSink>2.f) bPersistentSpin=false;
        if(bPersistentSpin)
            for(const auto& W:PVehicle->Wheels)PreviousSpin.Add(FVector2D(W.Omega,W.AngularPosition));
        if(SlideGraphPeaks.Num()!=PVehicle->Wheels.Num())
        {
            SlideGraphPeaks.SetNumZeroed(PVehicle->Wheels.Num());
            for(int32 I=0;I<PVehicle->Wheels.Num();++I)
            {
                const auto& Graph=PVehicle->Wheels[I].Setup().LateralSlipGraph;
                if(Graph.IsEmpty())continue;
                for(int32 Angle=0;Angle<=90;++Angle)
                {
                    const float Value=Graph.EvaluateY(float(Angle));
                    if(Value>SlideGraphPeaks[I].Y)SlideGraphPeaks[I]=FVector2D(Angle,Value);
                }
            }
        }
        TArray<float,TInlineAllocator<8>> Friction,SlipGraph;
        Friction.SetNum(PVehicle->Wheels.Num());SlipGraph.SetNum(PVehicle->Wheels.Num());
        for(int32 I=0;I<PVehicle->Wheels.Num();++I)
        {
            auto& W=PVehicle->Wheels[I];Friction[I]=W.FrictionMultiplier;SlipGraph[I]=W.LateralSlipGraphMultiplier;
            const FVector V=FRotator(0,W.SteeringAngle,0).UnrotateVector(WheelState.LocalWheelVelocity[I]);
            const bool HasSoil=ActiveHits.IsValidIndex(I) && ActiveHits[I];
            if(HasSoil && !Contacts[I].bNativeSubstance)
            {
                const auto& S=Contacts[I];
                const auto Soil=GTMudContact::Evaluate(S.Softness,S.Grass,S.TotalSink,W.GetEffectiveRadius(),V.X,W.GetAngularVelocity()*W.GetEffectiveRadius(),S.SoilState);
                const auto& Hit=WheelState.TraceResult[I];
                const float Base=Hit.PhysMaterial.IsValid() ? Hit.PhysMaterial->Friction : FMath::Max(.1f,W.GetSurfaceFriction());
                W.FrictionMultiplier*=Soil.Grip/FMath::Max(.05f,Base);
                W.LateralSlipGraphMultiplier*=Soil.LateralGrip/FMath::Max(.05f,Base);
            }
            // Work on this wheel's runtime multiplier, never its shared class setup.
            // Chaos still applies load, surface friction and the combined friction circle.
            const FGTSoilContact* S=Contacts.IsValidIndex(I) ? &Contacts[I] : nullptr;
            const float Blend=GTSlideRecovery::Weight(float(V.Size2D())*.036f,bLowRange,
                HasSoil ? S->Softness : 0.f,HasSoil ? FMath::Max(S->TotalSink,S->NativeDepth*100.f) : 0.f,
                S ? S->NativeWaterDepth*100.f : 0.f,SlideRecovery);
            if(W.InContact() && Blend>0.f && !W.Setup().LateralSlipGraph.IsEmpty())
            {
                const float Peak=SlideGraphPeaks[I].Y,PeakAngle=SlideGraphPeaks[I].X;
                const float Angle=FMath::RadiansToDegrees(Chaos::FVehicleUtility::CalculateSlipAngle(V.Y,V.X));
                const float Value=W.Setup().LateralSlipGraph.EvaluateY(Angle);
                W.LateralSlipGraphMultiplier*=GTSlideRecovery::GraphScale(Value,Peak,Angle,PeakAngle,Blend);
            }
        }
        UChaosWheeledVehicleSimulation::ApplyWheelFrictionForces(Dt);
        if(bPersistentSpin)
            for(int32 I=0;I<PVehicle->Wheels.Num();++I)
            {
                auto& W=PVehicle->Wheels[I];
                const FVector OldForce=W.ForceFromFriction;
                // The engaged engine must accelerate with the driven wheels.
                // Without its ratio-squared inertia, a game-frame torque sample
                // can fling a light wheel thousands of shaft RPM past the limiter.
                const float Inertia=W.Inertia*.0001f+(ReflectedEngineInertia.IsValidIndex(I) ? ReflectedEngineInertia[I] : 0.f);
                const auto Result=GTPersistentWheelSpin::Step(Dt,PreviousSpin[I].X,W.GetRoadSpeed()*.01f,
                    W.Re*.01f,Inertia,W.MassPerWheel,W.DriveTorque*.0001f,W.BrakeTorque*.0001f,
                    W.AvailableGrip*.01f,W.InputForces.Y*.01f,W.Setup().SideSlipModifier,W.InContact());
                W.Omega=Result.Omega;
                W.AngularPosition=FMath::Fmod(PreviousSpin[I].Y+W.Omega*Dt,2.f*PI);
                W.ForceFromFriction=FVector(Result.Fx*100.f,Result.Fy*100.f,0);
                W.Sx=(W.Omega*W.Re-W.GetRoadSpeed())/FMath::Max(100.f,FMath::Abs(W.GetRoadSpeed()));
                if(W.InContact())
                {
                    const auto& Hit=WheelState.TraceResult[I];
                    const FVector Z=Hit.Normal,X=FVector::CrossProduct(VehicleState.VehicleRightAxis,Z),Y=FVector::CrossProduct(Z,X);
                    const FVector Local=FRotator(0,W.SteeringAngle,0).RotateVector(W.ForceFromFriction-OldForce);
                    const FVector Delta=X*Local.X+Y*Local.Y+Z*Local.Z;
                    const FVector Position=PVehicle->bLegacyWheelFrictionPosition ? FVector(WheelState.WheelWorldLocation[I]) : FVector(Hit.ImpactPoint);
                    AddForceAtPosition(Delta,Position);
                }
            }
        BodyForceN=0;BodyMinBaseGap=1.e9;
        for(const auto& C:BodyContacts)
        {
            const FVector P=VehicleState.VehicleWorldTransform.TransformPosition(C.LocalPoint);
            // Discard stale snapshots after teleports or rapid lateral movement.
            if(FVector2D::Distance(FVector2D(P),C.SampleXY)>60)continue;
            BodyMinBaseGap=FMath::Min(BodyMinBaseGap,P.Z-C.Base);
            const float Immersion=C.Top-P.Z;
            if(Immersion<=0)continue;
            const FVector V=VehicleState.VehicleWorldVelocity+FVector::CrossProduct(VehicleState.VehicleWorldAngularVelocity,P-VehicleState.VehicleWorldCOM);
            const float K=C.MassShare*980.f/FMath::Max(5.f,C.YieldCm);
            const float Compression=FMath::Max(0.f,C.Support-float(P.Z));
            const float Damping=1.2f*FMath::Sqrt(K*C.MassShare);
            const float Fraction=FMath::Clamp(Immersion/15.f,0.f,1.f);
            const float Up=FMath::Clamp(K*Compression-Damping*float(V.Z)*Fraction,0.f,C.MassShare*980.f*2.5f);
            const FVector Horizontal(V.X,V.Y,0);
            // Dissipative soil drag, bounded so this adapter cannot reverse motion.
            const float Drag=FMath::Min(C.MassShare*980.f*.65f*Fraction,C.MassShare*float(Horizontal.Size())/FMath::Max(Dt,.001f)*.5f);
            AddForceAtPosition(FVector(0,0,Up)-Horizontal.GetSafeNormal()*Drag,P);
            BodyForceN+=Up*.01;BodyPeakPenetration=FMath::Max(BodyPeakPenetration,double(Immersion));++BodySteps;
        }
        for(int32 I=0;I<PVehicle->Wheels.Num();++I)
        {
            auto& W=PVehicle->Wheels[I];W.FrictionMultiplier=Friction[I];W.LateralSlipGraphMultiplier=SlipGraph[I];
            if(!Contacts.IsValidIndex(I))continue;
            const bool Supported=ActiveHits.IsValidIndex(I) && ActiveHits[I] && W.InContact();
            const auto& S=Contacts[I];const FVector N=WheelState.TraceResult[I].Normal;
            if((S.bNativeSubstance && Supported) || S.bNativeWater)
            {
                using namespace GTMudRunnerSubstance;
                FInput Input;
                const FVector Forward=VehicleState.VehicleWorldTransform.TransformVectorNoScale(FRotator(0,W.SteeringAngle,0).RotateVector(FVector::ForwardVector)).GetSafeNormal();
                const FVector Right=FVector::CrossProduct(VehicleState.VehicleUpAxis,Forward).GetSafeNormal();
                // Polar swap is self-inverse. The native positive spin axis is the
                // wheel axle; its scalar sign is bridged to Chaos below.
                Input.Forward=PolarToUnreal(Forward);Input.Axle=PolarToUnreal(Right);
                Input.Velocity=PolarToUnreal(WheelState.WorldWheelVelocity[I]*.01);
                Input.PredictedDisplacement=Input.Velocity/60.;
                Input.Radius=W.GetEffectiveRadius()*.01;Input.Width=S.WidthCm*.01;
                Input.Omega=W.GetAngularVelocity();Input.RollingSpeed=FVector::DotProduct(Input.Velocity,Input.Forward);
                Input.WheelMass=S.NativeWheelMass;Input.MassPerWheel=S.NativeMassPerWheel;
                Input.DriveState=FMath::Abs(W.GetDriveTorque())>1.e-4?1:0;
                // Chaos owns one spin DOF instead of a wheel rigid body's tensor.
                const double Inertia=FMath::Max(1.e-6,double(W.Inertia)*.0001);
                Input.InertiaRows[0]=FVector(Inertia,0,0);Input.InertiaRows[1]=FVector(0,Inertia,0);Input.InertiaRows[2]=FVector(0,0,Inertia);
                Input.Depth=S.NativeDepth;Input.Q=S.NativeQ;
                // CL2: the mud evaluate takes the ground's own numbers (the struct defaults 2.2 / 10 / 36 except on clay); the water evaluate below overrides them as before.
                Input.Friction=S.NativeFriction;Input.LinearResistance=S.NativeLinearResistance;Input.PushResistance=S.NativePushResistance;
                const auto Mud=S.bNativeSubstance && Supported?Evaluate(Input):FOutput();
                Input.bWater=true;Input.Depth=S.NativeWaterDepth;Input.Q=0;
                if(Input.Depth>=.05){++NativeWaterSteps;NativeMaxWaterDepth=FMath::Max(NativeMaxWaterDepth,Input.Depth);}
                Input.Friction=.4;Input.LinearResistance=1;Input.FullPushDepth=2;Input.PushResistance=1;
                Input.FlowImpulse=1.5;Input.Flow=PolarToUnreal(S.NativeFlow);
                auto Water=Evaluate(Input);
                const FVector J=Mud.LinearImpulse+Water.LinearImpulse;
                const FVector L=Mud.AngularImpulse+Water.AngularImpulse;
                // Explicit 60-Hz action-rate adapter: J per invocation -> force.
                // Physics-step integration, never once per rendered frame.
                AddForceAtPosition(PolarToUnreal(J)*(100.*60.),Supported?WheelState.TraceResult[I].ImpactPoint:WheelState.WheelWorldLocation[I]);
                double Delta=FVector::DotProduct(L,Input.Axle)/Inertia*(60.*Dt);
                // Native torque acts on a constrained wheel rigid body. Chaos has a
                // single spin DOF: cap dissipative integration at rolling speed,
                // otherwise a light wheel can reverse every step from drag alone.
                const double Excess=Input.Omega-Input.RollingSpeed/FMath::Max(Input.Radius,.01);
                if(Delta*Excess<0 && FMath::Abs(Delta)>FMath::Abs(Excess))Delta=-Excess;
                W.SetAngularVelocity(W.GetAngularVelocity()+Delta);
                ++NativeSteps;NativeSeconds+=Dt;NativeLinearImpulse+=J.Size()*(60.*Dt);NativeAngularImpulse+=L.Size()*(60.*Dt);
                if(S.bNativeSubstance)continue; // No duplicate mud resistance.
            }
            if(!Supported)continue;
            const FVector V=FVector::VectorPlaneProject(WheelState.WorldWheelVelocity[I],N);
            const auto Soil=GTMudContact::Evaluate(S.Softness,S.Grass,S.TotalSink,W.GetEffectiveRadius(),V.Size(),W.GetAngularVelocity()*W.GetEffectiveRadius(),S.SoilState);
            // Local resistance can pitch/yaw the chassis; applied every physics step.
            // Limit impulse to avoid reversing a wheel's supported mass at very low speed.
            const float Load=FMath::Max(0.f,W.GetWheelLoadForce()*S.LoadCorrection);
            const float Force=FMath::Min(Load*Soil.Resistance,Load/980.f*float(V.Size())/FMath::Max(Dt,.001f)*.5f);
            AddForceAtPosition(-V.GetSafeNormal()*Force,WheelState.TraceResult[I].ImpactPoint);
            if(S.bRutInteraction)
            {
                const double Started=FPlatformTime::Seconds();
                const FVector Position=WheelState.TraceResult[I].ImpactPoint;
                const FVector Forward=FVector::VectorPlaneProject(FVector(S.Heading,0),N).GetSafeNormal();
                const FVector Side=FVector::CrossProduct(N,Forward).GetSafeNormal();
                const float Reach=FMath::Clamp(S.WidthCm*.5f+14.f,24.f,36.f);
                for(const FVector Axis : {Forward,Side})
                {
                    const float Speed=FVector::DotProduct(V,Axis);
                    const FVector Direction=Axis*FMath::Sign(Speed);
                    // At the rolling toe the circular tyre clears a rising surface before
                    // its tread intersects it. Sidewalls have no equivalent rolling arc.
                    const bool bToe=FMath::Abs(FVector::DotProduct(Axis,Forward))>.5f;
                    const float Radius=FMath::Max(1.f,W.GetEffectiveRadius());
                    const float ProbeReach=bToe ? FMath::Min(Reach,Radius*.85f) : Reach;
                    const float Clearance=bToe ? Radius-FMath::Sqrt(FMath::Max(0.f,Radius*Radius-ProbeReach*ProbeReach)) : 0.f;
                    const float Rise=FMath::Max(0.f,S.EntryRise(FVector2D(Position),FVector2D(Direction),ProbeReach)-Clearance);
                    const float Resistance=GTMudContact::BankResistance(Rise,ProbeReach,S.Softness,S.SoilState);
                    const float BankForce=GTMudContact::BankForce(Load,Resistance,Speed,Dt);
                    AddForceAtPosition(-Direction*BankForce,Position);
                    BankWorkJ+=BankForce*FMath::Abs(Speed)*Dt*.0001;
                    if(!bToe) LateralBankWorkJ+=BankForce*FMath::Abs(Speed)*Dt*.0001;
                    BankPeakN=FMath::Max(BankPeakN,double(BankForce*.01f));
                }
                const double Ms=(FPlatformTime::Seconds()-Started)*1000;
                BankTotalMs+=Ms;BankPeakMs=FMath::Max(BankPeakMs,Ms);++BankSteps;
            }
        }
    }
};

TUniquePtr<Chaos::FSimpleWheeledVehicle> UGTSoilVehicleMovement::CreatePhysicsVehicle()
{
    RallyRideWeight=0;AppliedRideWeight=-1;AppliedSuspensionKit=-1;
    KitWheelOffsets.Reset();KitWheelFrames.Reset();
    VehicleSimulationPT=MakeUnique<FGTSoilVehicleSimulation>();
    return UChaosVehicleMovementComponent::CreatePhysicsVehicle();
}
void UGTSoilVehicleMovement::UpdateRallySuspension(float DeltaSeconds,float SurfaceWeight)
{
    int32 KitIndex=-1;
    if(UGTRangeRoverAudioComponent::IsRangeRover(GetOwner()))
        if(const auto* Parts=GetOwner()->FindComponentByClass<UGTPartSlotsComponent>())
            KitIndex=GTRangeRoverSuspension::Index(Parts->GetInstalled(FGameplayTag::RequestGameplayTag(TEXT("Slot.Suspension"))));
    const auto* Drive=GetOwner()->FindComponentByClass<UGTDrivetrainComponent>();
    const bool FixedFerrari=Drive && Drive->IsFerrari();
    const float Wanted=!FixedFerrari && CVarGTRallyRide.GetValueOnGameThread()!=0
        ? FMath::Clamp(SurfaceWeight,0.f,1.f)*FMath::SmoothStep(30.f,60.f,FMath::Abs(GetForwardSpeed())*.036f) : 0.f;
    // Off-road entry restores authored behaviour immediately; firm-road entry is gradual.
    RallyRideWeight=Wanted<=0 ? 0.f : FMath::FInterpTo(RallyRideWeight,Wanted,DeltaSeconds,4.f);
    const float Amount=RallyRideWeight*FMath::Clamp(RallySuspensionCompliance,0.f,.35f);
    if(KitIndex==AppliedSuspensionKit && FMath::Abs(Amount-AppliedRideWeight)<.001f && !(Amount==0 && AppliedRideWeight!=0))return;
    if(auto* Body=GetBodyInstance())FPhysicsCommand::ExecuteWrite(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
    {
        if(!VehicleSimulationPT)return;
        auto* S=static_cast<FGTSoilVehicleSimulation*>(VehicleSimulationPT.Get());
        if(!S->PVehicle || S->PVehicle->Suspension.IsEmpty())return;
        if(KitIndex<0 && Amount==0 && S->OriginalSuspension.IsEmpty()){AppliedRideWeight=0;return;}
        S->OwnSuspension();const float Scale=1.f-Amount;
        for(int32 I=0;I<S->OwnedSuspension.Num();++I)
        {
            const auto& Base=S->OriginalSuspension[I];auto& Config=S->OwnedSuspension[I];
            const auto& Kit=GTRangeRoverSuspension::Kit(KitIndex);
            const float RateScale=KitIndex>=0 ? Kit.Rate/340.f : 1.f;
            const float DampingScale=KitIndex>=0 ? Kit.Damping/.62f : 1.f;
            Config=Base;Config.SpringRate=Base.SpringRate*RateScale*Scale;
            Config.DampingRatio=Base.DampingRatio*DampingScale;
            Config.CompressionDamping=Base.CompressionDamping*FMath::Sqrt(RateScale*Scale)*DampingScale;
            Config.ReboundDamping=Base.ReboundDamping*FMath::Sqrt(RateScale*Scale)*DampingScale;
            if(KitIndex>=0)
            {
                Config.SetSuspensionMaxRaise(GTRangeRoverSuspension::Raise(I));
                Config.SetSuspensionMaxDrop(Kit.Drop);
            }
            if(S->ConstraintHandles.IsValidIndex(I))
                if(auto* C=static_cast<Chaos::FSuspensionConstraint*>(S->ConstraintHandles[I].Constraint))
                {
                    // Base.SpringRate is already in Chaos centimetre units. UE's
                    // public SetSuspensionParams uses inconsistent units for its
                    // two models; preserve their initial conversion here.
                    C->SetSpringStiffness(Config.SpringRate*.25f);
                    C->SetSpringDamping(Config.DampingRatio*5.f);
                    C->SetMinLength(-Config.SuspensionMaxRaise);
                    C->SetMaxLength(Config.SuspensionMaxDrop);
                }
        }
        for(int32 I=0;I<S->PVehicle->Axles.Num();++I)
            S->PVehicle->Axles[I].Setup.RollbarScaling=S->OriginalRollbars[I]*(KitIndex>=0 ? GTRangeRoverSuspension::Kit(KitIndex).Rollbar : 1.f)*(1.f-FMath::Clamp(Amount/.2f,0.f,1.f)*.65f);
        S->RideScale=Scale;AppliedRideWeight=Amount;AppliedSuspensionKit=KitIndex;
    });
}

float UGTSoilVehicleMovement::GetSuspensionOffset(int32 I)
{
    // The engine implementation clamps against shared wheel-class defaults. Kits own their
    // travel on this instance, so animation must use the same limits as the solver.
    if(AppliedSuspensionKit<0 || !Wheels.IsValidIndex(I) || !PVehicleOutput || !PVehicleOutput->Wheels.IsValidIndex(I))
        return Super::GetSuspensionOffset(I);
    const float Drop=GTRangeRoverSuspension::Kit(AppliedSuspensionKit).Drop;
    const bool bContact=GetWheelState(I).bInContact;
    const float Offset=bContact ? PVehicleOutput->Wheels[I].SuspensionOffset : -Drop;
    if(KitWheelOffsets.Num()!=Wheels.Num()) { KitWheelOffsets.Init(Offset,Wheels.Num()); KitWheelFrames.Init(MAX_uint64,Wheels.Num()); }
    if(KitWheelFrames[I]!=GFrameCounter)
    {
        const float Smoothed=bContact && KitWheelFrames[I]!=MAX_uint64 ? FMath::Lerp(KitWheelOffsets[I],Offset,9.f/11.f) : Offset;
        KitWheelOffsets[I]=FMath::Clamp(Smoothed,-Drop,GTRangeRoverSuspension::Raise(I));KitWheelFrames[I]=GFrameCounter;
    }
    return KitWheelOffsets[I];
}

FString UGTSoilVehicleMovement::SuspensionReport()
{
    FString Result=FString::Printf(TEXT("{\"kit\":%d,\"wheels\":["),AppliedSuspensionKit);
    if(auto* Body=GetBodyInstance())FPhysicsCommand::ExecuteRead(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
    {
        if(!VehicleSimulationPT || !VehicleSimulationPT->PVehicle)return;
        const auto& Springs=VehicleSimulationPT->PVehicle->Suspension;
        for(int32 I=0;I<Springs.Num();++I)
        {
            const auto& C=Springs[I].Setup();
            Result+=FString::Printf(TEXT("%s{\"raise\":%.3f,\"drop\":%.3f,\"rate\":%.3f,\"damping\":%.3f}"),I?TEXT(","):TEXT(""),C.SuspensionMaxRaise,C.SuspensionMaxDrop,C.SpringRate,C.DampingRatio);
        }
    });
    return Result+TEXT("]}");
}
void UGTSoilVehicleMovement::SetSoilContacts(const TArray<FGTSoilContact>& Contacts)
{
    const auto BodySoil=GatherBodySoil();
    const auto* Drivetrain=GetOwner() ? GetOwner()->FindComponentByClass<UGTDrivetrainComponent>() : nullptr;
    const bool Low=Drivetrain && Drivetrain->IsLowRange();
    const bool Ferrari=Drivetrain && Drivetrain->IsFerrari();
    const bool Independent=Drivetrain && (Ferrari || Drivetrain->GetRangeRoverSetup()>=0);
    TArray<float> Inertia;
    if(Independent)for(int32 I=0;I<WheelSetups.Num();++I)Inertia.Add(Drivetrain->GetReflectedEngineInertia(I));
    const float Recovery=CVarGTSlideRecovery.GetValueOnGameThread()!=0 ? HighSpeedSlideRecovery : 0.f;
    if(auto* Body=GetBodyInstance())
        FPhysicsCommand::ExecuteWrite(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
        {
            if(VehicleSimulationPT){auto* S=static_cast<FGTSoilVehicleSimulation*>(VehicleSimulationPT.Get());S->Contacts=Contacts;S->BodyContacts=BodySoil;S->bLowRange=Low;S->SlideRecovery=Recovery;S->bFerrari=Ferrari;S->bIndependentEngine=Independent;S->ReflectedEngineInertia=Inertia;}
        });
}
TArray<FGTBodySoilContact> UGTSoilVehicleMovement::GatherBodySoil()
{
    TArray<FGTBodySoilContact> Result;
    const auto* Body=GetBodyInstance();
    if(!Body||!Body->GetBodySetup()||!GetWorld())return Result;
    const auto& Boxes=Body->GetBodySetup()->AggGeom.BoxElems;
    // Current vehicles use one root box. Unknown hulls retain mineral collision
    // but do not receive guessed forces from their cosmetic/rendering bounds.
    if(Boxes.Num()!=1)return Result;
    BodyContactCarry=FMath::Min(.1f,BodyContactCarry+GetWorld()->GetDeltaSeconds());
    const int32 StampSteps=FMath::FloorToInt(BodyContactCarry*60.f);
    BodyContactCarry-=StampSteps/60.f;
    const auto& Box=Boxes[0];const FTransform Frame=Body->GetUnrealWorldTransform();
    for(float X:{-.9f,0.f,.9f})for(float Y:{-.9f,0.f,.9f})
    {
        FGTBodySoilContact C;C.LocalPoint=Box.GetTransform().TransformPosition(FVector(X*Box.X*.5f,Y*Box.Y*.5f,-Box.Z*.5f));
        const FVector P=Frame.TransformPosition(C.LocalPoint);C.SampleXY=FVector2D(P);
        FHitResult Hit;FCollisionQueryParams Params(SCENE_QUERY_STAT(BodySoilSnapshot),true,GetOwner());
        if(!GetWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,180),P-FVector(0,0,240),ECC_Visibility,Params))continue;
        const auto* Tile=Cast<AGTRoadReliefTile>(Hit.GetActor());
        if(!Tile||!Tile->Surface)continue;
        const auto S=Tile->Surface->SampleSurface(C.SampleXY);
        const float H=Tile->HeightAt(C.SampleXY);C.Base=Tile->MineralHeightAt(C.SampleXY);
        if(!S.bNativeSubstanceResponse||H-C.Base<1)continue;
        C.Top=H+S.SurfaceDeltaCm;
        C.Support=FMath::Clamp(H+S.NativeUpperCm-5.f-S.NativeExtrudeCm,C.Base,H);
        C.YieldCm=FMath::Clamp((H-C.Base)*.3f,5.f,30.f);C.MassShare=Mass/9.f;
        Result.Add(C);
        for(int32 Step=0;Step<StampSteps;++Step)
            Tile->Surface->ApplyBodySoilContact(P,UpdatedPrimitive->GetPhysicsLinearVelocityAtPoint(P),Mass,FMath::Clamp(Box.Y/3.f,20.f,90.f),1.f/60.f);
    }
    return Result;
}
FString UGTSoilVehicleMovement::BodySoilReport()
{
    FString Result=TEXT("body_samples=0 body_steps=0");
    if(auto* Body=GetBodyInstance())FPhysicsCommand::ExecuteRead(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
    {
        if(!VehicleSimulationPT)return;const auto* S=static_cast<FGTSoilVehicleSimulation*>(VehicleSimulationPT.Get());
        Result=FString::Printf(TEXT("body_samples=%d body_steps=%llu peak_immersion_cm=%.3f support_n=%.3f base_gap_cm=%.3f"),S->BodyContacts.Num(),S->BodySteps,S->BodyPeakPenetration,S->BodyForceN,S->BodyMinBaseGap);
    });return Result;
}
FString UGTSoilVehicleMovement::RallyHandlingReport()
{
    FString Result=TEXT("{}");
    if(auto* Body=GetBodyInstance())FPhysicsCommand::ExecuteRead(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
    {
        if(VehicleSimulationPT)Result=static_cast<FGTSoilVehicleSimulation*>(VehicleSimulationPT.Get())->RallyReport();
    });
    return Result;
}
FVector UGTSoilVehicleMovement::SoilQueryOrigin(int32 WheelIndex)
{
    if(const auto* Body=GetBodyInstance(); Body && WheelSetups.IsValidIndex(WheelIndex))
        return Body->GetUnrealWorldTransform().TransformPosition(GetWheelRestingPosition(WheelSetups[WheelIndex]));
    return FVector::ZeroVector;
}
FVector UGTSoilVehicleMovement::SoilWheelCentre(int32 WheelIndex)
{
    if(const auto* Body=GetBodyInstance();Body && WheelSetups.IsValidIndex(WheelIndex) && Wheels.IsValidIndex(WheelIndex) && Wheels[WheelIndex])
    {
        const FVector Local=GetWheelRestingPosition(WheelSetups[WheelIndex])+FVector(0,0,GetSuspensionOffset(WheelIndex));
        return Body->GetUnrealWorldTransform().TransformPosition(Local);
    }
    return SoilQueryOrigin(WheelIndex);
}
bool UGTSoilVehicleMovement::ReviewSuspensionObstacle(AActor* Obstacle)
{
    if(!Obstacle || !GetWorld())return false;
    FVector Centre,Extent;Obstacle->GetActorBounds(false,Centre,Extent);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NativeClodSuspension),true,GetOwner());
    FCollisionResponseParams Response;Response.CollisionResponse=WheelTraceCollisionResponses;
    FHitResult Hit;
    return GetWorld()->LineTraceSingleByChannel(Hit,Centre+FVector(0,0,Extent.Z+100),Centre-FVector(0,0,Extent.Z+100),ECC_WorldDynamic,Params,Response) && Hit.GetActor()==Obstacle;
}
FString UGTSoilVehicleMovement::RutInteractionReport()
{
    FString Result=TEXT("work_j=0 lateral_j=0 peak_n=0 mean_ms=0 peak_ms=0 wheel_steps=0");
    if(auto* Body=GetBodyInstance())
        FPhysicsCommand::ExecuteRead(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
        {
            if(!VehicleSimulationPT) return;
            const auto* S=static_cast<FGTSoilVehicleSimulation*>(VehicleSimulationPT.Get());
            Result=FString::Printf(TEXT("work_j=%.4f lateral_j=%.4f peak_n=%.3f mean_ms=%.6f peak_ms=%.6f wheel_steps=%llu"),
                S->BankWorkJ,S->LateralBankWorkJ,S->BankPeakN,S->BankSteps ? S->BankTotalMs/S->BankSteps : 0.,S->BankPeakMs,S->BankSteps);
        });
    return Result;
}

FString UGTSoilVehicleMovement::NativeSubstanceReport()
{
    FString Result=TEXT("native_steps=0");
    if(auto* Body=GetBodyInstance()) FPhysicsCommand::ExecuteRead(Body->GetPhysicsActor(),[&](const FPhysicsActorHandle&)
    {
        if(!VehicleSimulationPT)return;
        const auto* S=static_cast<FGTSoilVehicleSimulation*>(VehicleSimulationPT.Get());
        Result=FString::Printf(TEXT("native_steps=%llu wheel_seconds=%.4f linear_ns=%.4f angular_nms=%.4f water_steps=%llu max_water_m=%.4f action_rate_adapter_hz=60 contacts=Chaos"),S->NativeSteps,S->NativeSeconds,S->NativeLinearImpulse,S->NativeAngularImpulse,S->NativeWaterSteps,S->NativeMaxWaterDepth);
        int32 Active=0,Native=0,Supported=0;
        for(const auto& C:S->Contacts){Active+=C.bActive;Native+=C.bActive&&C.bNativeSubstance;}
        for(bool Hit:S->ActiveHits)Supported+=Hit;
        Result+=FString::Printf(TEXT(" soil_contacts=%d soil_hits=%d native_mud_contacts=%d"),Active,Supported,Native);
    });
    return Result;
}
