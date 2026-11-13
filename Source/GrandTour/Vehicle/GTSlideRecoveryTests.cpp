#include "Vehicle/GTSlideRecovery.h"
#include "WheelSystem.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTSlideRecoveryTest,"GrandTour.Vehicle.SlideRecovery",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTSlideRecoveryTest::RunTest(const FString& Parameters)
{
    using namespace GTSlideRecovery;
    TestEqual(TEXT("low range unchanged even at speed"),Weight(100,true,0,0,0,.75f),0.f);
    TestEqual(TEXT("crawl unchanged"),Weight(25,false,0,0,0,.75f),0.f);
    TestEqual(TEXT("deep soil unchanged"),Weight(100,false,0,20,0,.75f),0.f);
    TestEqual(TEXT("soft mud unchanged"),Weight(100,false,.7f,0,0,.75f),0.f);
    TestEqual(TEXT("water unchanged"),Weight(100,false,0,0,30,.75f),0.f);
    TestEqual(TEXT("A/B disabled"),Weight(100,false,0,0,0,0),0.f);
    TestEqual(TEXT("pre-peak not boosted"),GraphScale(.76f,1,4,8,.75f),1.f);
    TestEqual(TEXT("peak not boosted"),GraphScale(1,1,8,8,.75f),1.f);
    TestTrue(TEXT("speed blends gradually"),Weight(45,false,0,0,0,.75f)>0 && Weight(45,false,0,0,0,.75f)<.75f);

    // Exercise the actual Chaos tyre solver, not only our blend arithmetic.
    Chaos::FSimpleWheelConfig Config;
    Config.FrictionMultiplier=1;
    Config.SideSlipModifier=.9f;
    Config.LateralSlipGraph.Add(Chaos::FVec2(0,0));Config.LateralSlipGraph.Add(Chaos::FVec2(8,1));Config.LateralSlipGraph.Add(Chaos::FVec2(40,.68f));
    auto Force=[&](float Angle,float Speed,float Strength,bool Low)
    {
        Chaos::FSimpleWheelSim Wheel(&Config);
        Wheel.SetWheelLoadForce(500000.f);
        Wheel.SetSurfaceFriction(.62f);
        Wheel.LateralSlipGraphMultiplier=310000.f;
        const float Value=Config.LateralSlipGraph.EvaluateY(Angle);
        Wheel.LateralSlipGraphMultiplier*=GraphScale(Value,1,Angle,8,Weight(Speed*.036f,Low,0,0,0,Strength));
        Wheel.SetVehicleGroundSpeed(FVector(Speed*FMath::Cos(FMath::DegreesToRadians(Angle)),Speed*FMath::Sin(FMath::DegreesToRadians(Angle)),0));
        Wheel.Simulate(1.f/60.f);
        return float(FMath::Abs(Wheel.GetForceFromFriction().Y));
    };
    const float Before=Force(40,2200,0,false),After=Force(40,2200,.75f,false);
    TestTrue(TEXT("sliding tyre retains more lateral force"),After>Before*1.25f);
    TestTrue(TEXT("retained force stays below surface/load grip"),After<=310000.1f);
    TestEqual(TEXT("low range force identical"),Force(40,2200,.75f,true),Before);
    TestEqual(TEXT("low speed force identical"),Force(40,500,.75f,false),Force(40,500,0,false));
    TestEqual(TEXT("peak force identical"),Force(8,2200,.75f,false),Force(8,2200,0,false));
    AddInfo(FString::Printf(TEXT("Slide at 79.2 km/h: lateral force %.1f -> %.1f; low range unchanged"),Before,After));
    return true;
}
#endif
