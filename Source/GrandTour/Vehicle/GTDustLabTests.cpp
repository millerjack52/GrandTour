#include "Vehicle/GTDustLab.h"
#include "Vehicle/GTTractionComponent.h"
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
    FGTWheelTraction Wheel;
    Wheel.bInContact = true;
    Wheel.AuthoredSurface = TEXT("Gravel");
    TestTrue(TEXT("Firm authored gravel needs no deformable patch"), AGTDustLab::IsDustyContact(Wheel, false));
    Wheel.GroundWaterDepthCm = 3.f;
    TestFalse(TEXT("Authored puddle suppresses gravel dust"), AGTDustLab::IsDustyContact(Wheel, false));
    Wheel.GroundWaterDepthCm = 0.f;
    Wheel.WaterDepthM = .03f;
    TestFalse(TEXT("Water subsystem suppresses gravel dust"), AGTDustLab::IsDustyContact(Wheel, false));
    Wheel.WaterDepthM = 0.f;
    Wheel.bInContact = false;
    TestFalse(TEXT("Cached gravel cannot emit airborne"), AGTDustLab::IsDustyContact(Wheel, false));
    Wheel.bInContact = true;
    for (const TCHAR* Surface : {TEXT("Mud"), TEXT("Grass"), TEXT("FirmGround")})
    {
        Wheel.AuthoredSurface = Surface;
        TestFalse(TEXT("Authored non-dust surface overrides legacy gravel"), AGTDustLab::IsDustyContact(Wheel, true));
    }
    Wheel.AuthoredSurface = NAME_None;
    TestTrue(TEXT("Legacy gravel remains supported"), AGTDustLab::IsDustyContact(Wheel, true));
    Wheel.bInSnowPatch = true;
    TestFalse(TEXT("Snow excludes dust"), AGTDustLab::IsDustyContact(Wheel, true));
    return true;
}
#endif
