#include "Misc/AutomationTest.h"
#include "Terrain/GTMudRunnerGrass.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTNativeGrassTest,"GrandTour.MudRunner.GrassOracle",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTNativeGrassTest::RunTest(const FString&)
{
    using namespace GTMudRunnerGrass;
    TestTrue(TEXT("Recovered closed 0.64m radius"),RemovedByContact(FVector2D(64,0),FVector2D::ZeroVector));
    TestFalse(TEXT("Outside radius remains intact"),RemovedByContact(FVector2D(64.01,0),FVector2D::ZeroVector));
    TestFalse(TEXT("Radius is circular, not a square"),RemovedByContact(FVector2D(50,50),FVector2D::ZeroVector));
    for(int32 I=0;I<256;++I)
    {
        TestEqual(TEXT("Low nibble survives removal"),int32(Remove(I)&15),I&15);
        TestEqual(TEXT("Packed VS threshold matches high nibble"),Hidden(I),I>=240);
        TestTrue(TEXT("Removed state is hidden"),Hidden(Remove(I)));
    }
    TestTrue(TEXT("Grass roots remain fixed"),Deflect(.05f,FVector4(1,.5,0,1)).IsNearlyZero());
    TestTrue(TEXT("VS fixture at half metre"),Deflect(.5f,FVector4(1,.5,0,1)).Equals(FVector(.5,0,-.4),1.e-6));
    TestTrue(TEXT("Deflector height excludes submerged blade base"),Deflect(.5f,FVector4(1,.5,.2,1)).IsNearlyZero());
    return true;
}
#endif
