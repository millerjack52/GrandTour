#include "Misc/AutomationTest.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTRoadReliefTile.h"
#include "Engine/World.h"
#include "Landscape.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTRoadSoilOwnership,"GrandTour.Authoring.RoadSoilOwnership",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTRoadSoilOwnership::RunTest(const FString&)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    auto* Surface=World->SpawnActor<AGTLandscapeSurface>();
    auto* Other=World->SpawnActor<AGTLandscapeSurface>();
    auto* Tile=World->SpawnActor<AGTRoadReliefTile>();Tile->Surface=Surface;
    auto* Rock=World->SpawnActor<AActor>();
    auto* Land=World->SpawnActor<ALandscape>();Surface->Landscape=Land;
    TestTrue(TEXT("Landscape belongs to soil source"),Surface->OwnsGroundActor(Land));
    TestTrue(TEXT("Generated road belongs to SAME soil source"),Surface->OwnsGroundActor(Tile));
    TestFalse(TEXT("Other surface cannot claim tile"),Other->OwnsGroundActor(Tile));
    TestFalse(TEXT("Rock/bridge stays a rigid obstacle"),Surface->OwnsGroundActor(Rock));
    TestFalse(TEXT("Missing hit is not soil"),Surface->OwnsGroundActor(nullptr));
    Tile->Intervals=1;Tile->SpanCm=100;Tile->Heights={200,200,200,200};
    Surface->RoadTileOrigin=FVector2D::ZeroVector;Surface->RoadTileSpanCm=100;Surface->RoadReliefTiles.Add(FIntPoint(0,0),Tile);
    const auto H=Surface->GroundHeightAt(FVector(50,50,0));
    TestTrue(TEXT("Native reference height uses road, not recessed landscape"),H.IsSet()&&H.GetValue()==200);
    World->DestroyWorld(false);
    return true;
}
#endif
