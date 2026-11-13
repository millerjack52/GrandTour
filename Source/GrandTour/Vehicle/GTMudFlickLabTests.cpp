#include "Vehicle/GTMudFlickLab.h"
#include "Vehicle/GTTractionComponent.h"
#include "Core/GTGameplayTags.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudFlickLabTest,"GrandTour.DustLab.MudFlick",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTMudFlickLabTest::RunTest(const FString& Parameters)
{
    const auto A=&AGTMudFlickLab::Activity;
    TestEqual(TEXT("Airborne wheel cannot mine mud"),A(false,true,1200,500,10000),0.f);
    TestEqual(TEXT("Clean solid ground cannot make mud"),A(true,false,1200,500,10000),0.f);
    TestEqual(TEXT("Idle cannot spray"),A(true,true,0,0,0),0.f);
    TestEqual(TEXT("Locked wheel cannot flick"),A(true,true,0,-800,10000),0.f);
    TestTrue(TEXT("Rolling through mud flicks"),A(true,true,500,0,0)>0.f);
    TestTrue(TEXT("Digging adds spray"),A(true,true,500,300,10000)>A(true,true,500,0,0));
    TestEqual(TEXT("Reverse is symmetric"),A(true,true,500,300,10000),A(true,true,-500,-300,10000));
    TestEqual(TEXT("Counter slip adds no spin spray"),A(true,true,500,-300,0),A(true,true,500,0,0));
    TestTrue(TEXT("Rate remains bounded"),A(true,true,1.e8f,1.e8f,1.e8f)<=1.5f);
    FGTWheelTraction W;
    TestFalse(TEXT("Firm ground is not mud"),AGTMudFlickLab::CoversWheel(W));
    W.SurfaceTag=GTTags::Surface_Mud.GetTag();
    TestTrue(TEXT("Benmore static muddy ground is covered"),AGTMudFlickLab::CoversWheel(W));
    W.bInGravelPatch=true;
    TestFalse(TEXT("Gravel patch overrides underlying mud tag"),AGTMudFlickLab::CoversWheel(W));
    return true;
}
#endif
