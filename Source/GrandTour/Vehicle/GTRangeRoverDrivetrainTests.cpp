#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTRangeRoverDrivetrain.h"
#include "Vehicle/GTFerrariHandling.h"
#include "Vehicle/GTPersistentWheelSpin.h"
#include "Misc/AutomationTest.h"
#include "Core/GTSaveGame.h"
#include "Core/GTGameplayTags.h"
#include "Kismet/GameplayStatics.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTRangeRoverDrivetrainTest,"GrandTour.RangeRover.Drivetrain",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTRangeRoverDrivetrainTest::RunTest(const FString&)
{
    using namespace GTRangeRoverDrivetrain;
    auto* Drive=NewObject<UGTDrivetrainComponent>();
    // Reproduce the production wheel's dt-dependent momentum reset and require
    // the replacement to retain spin, transfer reaction, coast and lock brakes.
    TArray<float> SpinEnds,SpeedEnds;
    for(int32 Hz : {30,60,120})
    {
        float Omega=0,Speed=0;
        for(int32 I=0;I<Hz*2;++I)
        {
            const auto S=GTPersistentWheelSpin::Step(1.f/Hz,Omega,Speed,.4f,2.f,350.f,300.f,0,200.f,0,.9f,true);
            TestTrue(TEXT("tyre reaction stays inside grip"),FMath::Abs(S.Fx)<=200.01f);
            const float Reaction=Omega+(300.f-S.Fx*.4f)/2.f/Hz;
            TestTrue(TEXT("wheel acceleration includes equal tyre reaction"),FMath::IsNearlyEqual(S.Omega,Reaction,.001f));
            Omega=S.Omega;Speed+=S.Fx/350.f/Hz;
        }
        SpinEnds.Add(Omega);SpeedEnds.Add(Speed);
        TestTrue(TEXT("grounded excess wheelspin accumulates"),Omega>200);
        const float Powered=Omega;
        for(int32 I=0;I<Hz*2;++I)
        {
            const auto S=GTPersistentWheelSpin::Step(1.f/Hz,Omega,Speed,.4f,2.f,350.f,0,0,200.f,0,.9f,true);
            Omega=S.Omega;Speed+=S.Fx/350.f/Hz;
        }
        TestTrue(TEXT("lifting dissipates retained spin through tyre reaction"),Omega<Powered-50);
    }
    TestTrue(TEXT("wheel momentum consistent at 30/60/120 Hz"),FMath::Abs(SpinEnds[0]-SpinEnds[2])<1);
    TestTrue(TEXT("body reaction consistent at 30/60/120 Hz"),FMath::Abs(SpeedEnds[0]-SpeedEnds[2])<.01f);
    const auto Locked=GTPersistentWheelSpin::Step(1.f/60,0,10,.4f,2,350,0,3000,2000,0,.9f,true);
    TestTrue(TEXT("handbrake holds wheel locked while car is moving"),FMath::IsNearlyZero(Locked.Omega,.001f) && Locked.Fx<0);
    const auto Parked=GTPersistentWheelSpin::Step(1.f/60,0,.01f,.4f,2,350,0,3000,2000,0,.9f,true);
    TestTrue(TEXT("parked locked wheel reacts supported mass without a free rotation DOF"),FMath::IsNearlyEqual(Parked.Fx,-210.f,.01f) && FMath::IsNearlyZero(Parked.Omega,.001f));
    const auto Combined=GTPersistentWheelSpin::Step(1.f/60,100,10,.4f,2,350,300,0,2000,1800,.9f,true);
    TestTrue(TEXT("powered slide retains bounded lateral force"),Combined.Fy>500 && FMath::Sqrt(Combined.Fx*Combined.Fx+Combined.Fy*Combined.Fy)<=2000.01f);
    const auto Air=GTPersistentWheelSpin::Step(1.f/60,10,0,.4f,2,350,100,0,0,0,.9f,false);
    TestTrue(TEXT("airborne wheel spins without chassis force"),Air.Omega>10 && Air.Fx==0 && Air.Fy==0);
    TestTrue(TEXT("Ferrari driver can countersteer into an established slide"),GTFerrariHandling::CountersteerWeight(1,1800,400,false)>.99f);
    TestTrue(TEXT("left and right countersteer have equal authority"),GTFerrariHandling::CountersteerWeight(-1,1800,-400,false)>.99f);
    TestTrue(TEXT("no automatic steering on release"),GTFerrariHandling::CountersteerWeight(0,1800,400,false)==0);
    TestTrue(TEXT("normal turn-in retains speed limit"),GTFerrariHandling::CountersteerWeight(-1,1800,400,false)==0);
    TestTrue(TEXT("low range retains original steering curve"),GTFerrariHandling::CountersteerWeight(1,1800,400,true)==0);
    TestTrue(TEXT("reverse retains original steering curve"),GTFerrariHandling::CountersteerWeight(1,-1800,400,false)==0);
    float OpenA,OpenB,LimitedA,LimitedB,LockedA,LockedB;
    // One wheel on slime/air, its partner on firm ground. Exercise the production splitter.
    Drive->Split(1200,40,2000,15,5,0,OpenA,OpenB);
    Drive->Split(1200,40,2000,15,5,Setup(1).RearLSD,LimitedA,LimitedB);
    Drive->Split(1200,40,2000,15,5,1,LockedA,LockedB);
    TestTrue(TEXT("LSD feeds more torque to the gripping wheel than open diff"),LimitedB>OpenB);
    TestTrue(TEXT("full lock improves on partial LSD"),LockedB>LimitedB);
    TestTrue(TEXT("coupling slows the faster wheel"),LimitedA<OpenA);
    TestTrue(TEXT("coupling cannot create net drive torque"),LimitedA+LimitedB<=1200.01f && FMath::IsNearlyEqual(LockedA+LockedB,1200.f));
    float ReverseA,ReverseB;
    Drive->Split(-1200,40,2000,-15,-5,Setup(1).RearLSD,ReverseA,ReverseB);
    TestTrue(TEXT("reverse split is sign symmetric"),FMath::IsNearlyEqual(ReverseA,-LimitedA) && FMath::IsNearlyEqual(ReverseB,-LimitedB));
    Drive->Split(0,40,2000,15,5,Setup(1).RearLSD,LimitedA,LimitedB);
    TestTrue(TEXT("coast coupling sums to zero and opposes wheel speed difference"),FMath::IsNearlyZero(LimitedA+LimitedB) && LimitedA<0 && LimitedB>0);
    for(float Input : {1200.f,-1200.f,0.f}) for(float Lock : {0.f,.35f,1.f})
    {
        float A,B;Drive->Split(Input,40,60,15,5,Lock,A,B,true);
        TestTrue(TEXT("RR does not delete torque when both wheels lose grip"),FMath::IsNearlyEqual(A+B,Input,.001f));
        if(Lock==0) TestTrue(TEXT("open diff transmits equal shaft torque"),FMath::IsNearlyEqual(A,B));
        else TestTrue(TEXT("LSD/lock still transfers torque away from faster wheel"),A<B);
    }
    Drive->Split(1200,40,60,15,5,0,OpenA,OpenB);
    TestTrue(TEXT("legacy fleet grip cap is unchanged"),FMath::IsNearlyEqual(OpenA+OpenB,100.f));
    TestTrue(TEXT("wheelspin detected on any surface"),IsWheelspin(4500,2000,800,4));
    TestFalse(TEXT("wheelspin cannot trigger upshift"),CanShiftUp(IsWheelspin(4500,2000,800,4)));
    TestFalse(TEXT("sliding cannot downshift an already fast engine"),CanShiftDown(true,4400,1800));
    TestTrue(TEXT("genuinely low engine speed can downshift"),CanShiftDown(true,1000,1800));
    TestFalse(TEXT("airborne wheels do not request upshift"),CanShiftUp(IsWheelspin(4200,4200,800,0)));
    TestTrue(TEXT("gripping wheels allow normal shifts"),CanShiftUp(IsWheelspin(4300,4200,800,4)));
    TestTrue(TEXT("RWD engine follows rear wheels without front dilution"),GTIndependentDrivetrain::DrivenOmega(10,100,0)==100);
    TestTrue(TEXT("FWD engine follows fronts"),GTIndependentDrivetrain::DrivenOmega(10,100,1)==10);
    TestTrue(TEXT("equal AWD split retains original wheel average"),GTIndependentDrivetrain::DrivenOmega(10,100,.5f)==55);
    float FerrariRPM=900,FerrariClutch=1;
    for(int32 I=0;I<480;++I)
    {
        const float T=StepClutch(1.f/120.f,0,FerrariRPM<7500 ? 350.f : 0.f,450,900,7500,true,FerrariRPM,FerrariClutch,13.94f,.38f,3.333333f);
        TestTrue(TEXT("Ferrari handbrake opens wheel drive"),T==0);
    }
    TestTrue(TEXT("Ferrari free revs use its own higher limit"),FerrariRPM>7000 && FerrariRPM<=7650);
    float RPM=800.f,Clutch=1.f;
    for(int32 I=0;I<360;++I)
    {
        const float T=StepClutch(1.f/120.f,0,RPM<5000 ? 300.f : 0.f,480,800,5000,true,RPM,Clutch);
        TestTrue(TEXT("handbrake disconnects all engine drive"),T==0 && Clutch==0);
    }
    TestTrue(TEXT("locked wheels cannot pin free engine RPM"),RPM>4500 && RPM<=5100);
    const float HighRPM=RPM;
    for(int32 I=0;I<240;++I) StepClutch(1.f/120.f,0,0,480,800,5000,true,RPM,Clutch);
    TestTrue(TEXT("free engine loses revs on throttle lift"),RPM<HighRPM-900 && RPM>=800);
    const float BeforeRelease=RPM;
    const float LaunchT=StepClutch(1.f/120.f,0,300,480,800,5000,false,RPM,Clutch);
    TestTrue(TEXT("release feeds torque progressively without snapping RPM to wheels"),LaunchT>0 && LaunchT<30 && Clutch<.03f && FMath::Abs(RPM-BeforeRelease)<100);
    RPM=2000;Clutch=1;
    const float Reaction=StepClutch(1.f/120.f,1900,300,480,800,5000,false,RPM,Clutch);
    const float Expected=2000+(300-Reaction)/.65f*60.f/(2*PI)/120.f;
    TestTrue(TEXT("wheel torque produces equal engine reaction"),FMath::IsNearlyEqual(RPM,Expected,.01f));
    RPM=1100;Clutch=1;
    TestTrue(TEXT("forward drive opposes rollback instead of accelerating it"),StepClutch(1.f/120.f,-2000,100,480,800,5000,false,RPM,Clutch)>0);
    RPM=800;Clutch=1;
    StepClutch(1.f/120.f,2000,0,480,800,5000,false,RPM,Clutch);
    TestTrue(TEXT("engaged gearbox back-drives engine without slow RPM lag"),RPM>1950 && RPM<=2000);
    RPM=1500;Clutch=1;
    StepClutch(1.f/120.f,8000,0,480,800,5000,false,RPM,Clutch,45);
    TestTrue(TEXT("low-range shaft overspeed reaches engine limiter"),RPM>4950 && RPM<=5100);
    for(int32 I=0;I<3;++I)
    {
        TestTrue(TEXT("pedal closed is zero"),FMath::IsNearlyZero(Pedal(I,0)));
        TestTrue(TEXT("pedal full is full"),FMath::IsNearlyEqual(Pedal(I,1),1.f));
        float Previous=0;
        for(int32 P=0;P<=100;++P) { const float Value=Pedal(I,P*.01f); TestTrue(TEXT("monotonic pedal"),Value>=Previous && Value<=1.f); Previous=Value; }
        for(int32 CurveRPM=0;CurveRPM<=6000;CurveRPM+=50) TestTrue(TEXT("bounded finite torque multiplier"),FMath::IsFinite(TorqueScale(I,CurveRPM)) && TorqueScale(I,CurveRPM)>.5f && TorqueScale(I,CurveRPM)<1.5f);
    }
    TestTrue(TEXT("Rally gains high-rev torque but sacrifices idle pull"),TorqueScale(1,4500)>1.25f && TorqueScale(1,800)<1.f);
    TestTrue(TEXT("Expedition trades high-rev output for low-rev torque"),TorqueScale(2,800)>1.15f && TorqueScale(2,4500)<.9f);
    TestTrue(TEXT("Expedition is gentler at half pedal despite low-RPM torque gain"),Pedal(2,.5f)*TorqueScale(2,800)<.5f);
    TestTrue(TEXT("Expedition gives substantially lower crawl gearing"),Setup(2).FinalRatio*Setup(2).Gears[0]*Setup(2).LowRatio>Setup(0).FinalRatio*Setup(0).Gears[0]*Setup(0).LowRatio*1.5f);
    TestTrue(TEXT("Rally revs remain inside original audio/limiter range"),Setup(1).UpRPM<5000 && Setup(1).DownRPM<Setup(1).UpRPM);
    // Exercise the real save class and disk serializer, without accessing the player's slot.
    for(int32 I=1;I<3;++I)
    {
        const FString Slot=TEXT("GT_Drivetrain_NativeQA_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        auto* Save=Cast<UGTSaveGame>(UGameplayStatics::CreateSaveGameObject(UGTSaveGame::StaticClass()));
        Save->Snapshot.bValid=true;
        FGTSlotEntry Entry; Entry.Slot=GTTags::Slot_Engine; Entry.PartId=Setup(I).Id;
        Save->Snapshot.Loadout.Add(Entry);
        Save->Snapshot.PartHealth.Add(EGTCarPart::Engine,.63f);
        TestTrue(TEXT("drivetrain package writes to isolated disk save"),UGameplayStatics::SaveGameToSlot(Save,Slot,0));
        const auto* Loaded=Cast<UGTSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot,0));
        TestTrue(TEXT("package ID survives production disk serialization"),Loaded && Loaded->Snapshot.bValid && Loaded->Snapshot.Loadout.Num()==1 && Loaded->Snapshot.Loadout[0].PartId==Entry.PartId);
        TestTrue(TEXT("save does not repair engine condition"),Loaded && FMath::IsNearlyEqual(Loaded->Snapshot.PartHealth.FindRef(EGTCarPart::Engine),.63f));
        TestTrue(TEXT("isolated native QA save removed"),UGameplayStatics::DeleteGameInSlot(Slot,0));
    }
    return true;
}
#endif
