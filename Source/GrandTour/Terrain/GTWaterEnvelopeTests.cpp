#include "Terrain/GTWaterDomain.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTWaterEnvelopeTest,"GrandTour.Water.ShoreEnvelope",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTWaterEnvelopeTest::RunTest(const FString&)
{
 UGTWaterDomain* D=NewObject<UGTWaterDomain>();D->SizeX=D->SizeY=5;D->CellCm=100;D->OriginCm=FVector2D::ZeroVector;
 D->Samples.Init(0,100);for(int32 I=0;I<25;++I)D->Samples[I*4+1]=-1;
 D->Samples[48]=1234;D->Samples[49]=.3f;D->Samples[50]=.7f;
 float S,H;FVector2D V;
 TestFalse(TEXT("Dry bank remains dry in authored domain"),D->Sample(FVector2D(350,250),S,H,V));
 TestTrue(TEXT("Nearby bank can receive live-bed water"),D->SampleEnvelope(FVector2D(350,250),150,S,H,V));
 TestEqual(TEXT("Support retains water elevation, never bank elevation"),S,1234.f);
 TestTrue(TEXT("Support retains current"),FMath::Abs(V.X-.7)<1.e-6);
 TestFalse(TEXT("No unbounded flooding beyond margin"),D->SampleEnvelope(FVector2D(500,250),150,S,H,V));
 TestFalse(TEXT("No invalid-grid support"),NewObject<UGTWaterDomain>()->SampleEnvelope(FVector2D::ZeroVector,250,S,H,V));
 return true;
}
#endif
