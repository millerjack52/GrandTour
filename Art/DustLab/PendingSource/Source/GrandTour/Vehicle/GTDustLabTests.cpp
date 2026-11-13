#include "Vehicle/GTDustLab.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTDustLabTest, "GrandTour.DustLab.Emission",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTDustLabTest::RunTest(const FString& Parameters)
{
    const auto Rate = &AGTDustLab::EmissionStrength;
    TestEqual(TEXT("Idle doesn't raise dust"), Rate(true, true, 0, 0, 0), 0.f);
    TestEqual(TEXT("Tiny resting slip doesn't raise dust"), Rate(true, true, 0, 15, 0), 0.f);
    TestEqual(TEXT("Airborne spinning wheel doesn't mine dust"), Rate(false, true, 2000, 900, 0), 0.f);
    TestEqual(TEXT("Tarmac has no dust source"), Rate(true, false, 2000, 900, 0), 0.f);
    TestEqual(TEXT("Wet ground suppresses new dust"), Rate(true, true, 2000, 900, 0.6f), 0.f);
    TestTrue(TEXT("Dry rolling emits without wheelspin"), Rate(true, true, 1000, 0, 0) > 0.f);
    TestTrue(TEXT("Stationary wheelspin disturbs loose ground"), Rate(true, true, 0, 900, 0) > 0.f);
    TestEqual(TEXT("Reverse gives equal disturbance"), Rate(true, true, -1000, -500, 0), Rate(true, true, 1000, 500, 0));
    TestTrue(TEXT("Braking slip adds dust"), Rate(true, true, 1000, -500, 0) > Rate(true, true, 1000, 0, 0));
    TestTrue(TEXT("Damp ground gives less than dry"), Rate(true, true, 1000, 0, 0.3f) < Rate(true, true, 1000, 0, 0));
    TestTrue(TEXT("Extreme velocity is bounded"), Rate(true, true, 1.e8f, 1.e8f, 0) <= 1.5f);
    return true;
}
#endif
