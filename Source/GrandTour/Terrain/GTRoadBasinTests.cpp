#include "Misc/AutomationTest.h"
#include "Terrain/GTRoadBasin.h"
#include "Terrain/GTWaterDomain.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTRoadBasinTest,"GrandTour.Authoring.RoadBasins",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTRoadBasinTest::RunTest(const FString&)
{
    TArray<float> Bed,Allow;Bed.Init(100,81);Allow.Init(25,81);
    for(int32 Y=2;Y<7;++Y)for(int32 X=2;X<7;++X)Bed[Y*9+X]=10+X;
    auto Water=GTRoadBasin::Fill(Bed,Allow,9,9);
    TestEqual(TEXT("Limited fill above lowest bed"),Water[4*9+4],37.f);
    TestEqual(TEXT("One level throughout connected basin"),Water[4*9+3],Water[4*9+5]);
    TestEqual(TEXT("Unmodified bed"),Bed[4*9+4],14.f);
    // Opening a drainage channel to the map edge must remove trapped water.
    for(int32 X=0;X<5;++X)Bed[4*9+X]=0;
    Water=GTRoadBasin::Fill(Bed,Allow,9,9);TestTrue(TEXT("Open channel drains"),Water[4*9+4]<-1e20f);
    for(int32 Y=0;Y<9;++Y)for(int32 X=0;X<9;++X)Bed[Y*9+X]=X*10;
    Water=GTRoadBasin::Fill(Bed,Allow,9,9);TestFalse(TEXT("No floating pools on a slope"),Water.ContainsByPredicate([](float V){return V>-1e20f;}));
    Bed.Init(100,81);for(int32 Y=2;Y<7;++Y)for(int32 X=2;X<7;++X)Bed[Y*9+X]=0;
    Allow[4*9+4]=0;Water=GTRoadBasin::Fill(Bed,Allow,9,9);
    TestFalse(TEXT("No artificial vertical edge at authoring boundary"),Water.ContainsByPredicate([](float V){return V>-1e20f;}));
    auto* Base=NewObject<UGTWaterDomain>();auto* Patch=NewObject<UGTWaterDomain>(Base);Base->RoadPatches.Add(Patch);
    Patch->SizeX=Patch->SizeY=3;Patch->CellCm=50;Patch->Samples.Init(0,36);
    for(int32 I=0;I<9;++I){Patch->Samples[I*4]=200;Patch->Samples[I*4+1]=.1f;}
    float S,D;FVector2D V;TestTrue(TEXT("Fine pool feeds existing domain queries"),Base->Sample(FVector2D(75,75),S,D,V));TestEqual(TEXT("Pool water level"),S,200.f);
    TestFalse(TEXT("No coverage outside pool"),Base->Sample(FVector2D(500,500),S,D,V));
    return true;
}
#endif
