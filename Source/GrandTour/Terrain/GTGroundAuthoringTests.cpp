#include "Misc/AutomationTest.h"
#include "Terrain/GTEditorReconstruction.h"
#include "Terrain/GTGroundAuthoringOracle.inl"
#include "Terrain/GTRoadReliefOracle.inl"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTGroundAuthoringOracleTest,"GrandTour.Authoring.NativeOracle",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTGroundAuthoringOracleTest::RunTest(const FString&)
{
    using namespace GTEditorReconstruction;
    FCurve C;TestTrue(TEXT("Native cubic builds"),C.Build(GTGroundOracle::Knots,GTGroundOracle::Values));
    for(auto& Row:GTGroundOracle::Curve)TestTrue(TEXT("Native cubic evaluation"),FMath::IsNearlyEqual(C.At(Row[0]),Row[1],.00002f));
    const auto Bank=Patterns(26,962);int32 I=0;
    for(const auto& Pattern:Bank)for(auto P:Pattern){TestTrue(TEXT("Native candidate X"),FMath::IsNearlyEqual(P.X,GTGroundOracle::Pattern[I][0],.000002f));TestTrue(TEXT("Native candidate Y"),FMath::IsNearlyEqual(P.Y,GTGroundOracle::Pattern[I][1],.000002f));++I;}
    TestEqual(TEXT("Candidate count"),I,96);
    for(auto& Row:GTGroundOracle::Density){FRandom R(Row.Seed);TestEqual(TEXT("Native density gate"),Density(Row.D,.01f,Row.M,Row.A,R),Row.Accepted);}
    for(auto& Row:GTGroundOracle::Road)TestEqual(TEXT("Native road alpha"),int32(RoadAlpha(Row[0],Row[1])),int32(Row[2]));
    for(auto& Row:GTGroundOracle::Scale){FRandom R(Row.Seed);TestTrue(TEXT("Native scale"),FMath::IsNearlyEqual(Scale(Row.G,Row.MinMap,Row.MaxMap,Row.MinSize,Row.MaxSize,Row.Jitter,R),Row.Expected,.000002f));}
    FCurve Invalid;TestFalse(TEXT("Duplicate knots rejected"),Invalid.Build({0,0,2},{1,2,3}));
    for(const auto& Row:GTRoadReliefOracle::UV)
    {const auto UV=RoadUV(Row[0],-Row[3],Row[1],Row[2]);TestTrue(TEXT("Native road U"),FMath::IsNearlyEqual(UV.X,Row[4],.000002f));TestTrue(TEXT("Native road V"),FMath::IsNearlyEqual(UV.Y,Row[5],.000002f));}
    FCurve Derivative;Derivative.Build({0,3,9,17,25},{1,-2,4,2,8});
    for(const auto& Row:GTRoadReliefOracle::Derivative)TestTrue(TEXT("Native cubic derivative"),FMath::IsNearlyEqual(Derivative.Derivative(Row[0]),Row[1],.000002f));
    TestTrue(TEXT("Dirt relief minimum cm"),FMath::IsNearlyEqual(RoadOffsetCm(115.f/255,1),-18.823529f,.0001f));
    TestEqual(TEXT("Road alpha suppresses relief"),RoadOffsetCm(0,0),0.f);
    TArray<uint8> Pixels={0,0,0,255,0,0,255,255,0,0,128,255,0,0,64,255};
    TestEqual(TEXT("Texel centre"),SampleRoadRed(Pixels,2,2,FVector2f(.25,.25)),0.f);
    TestTrue(TEXT("Negative UV repeat"),FMath::IsNearlyEqual(SampleRoadRed(Pixels,2,2,FVector2f(-.1,.3)),SampleRoadRed(Pixels,2,2,FVector2f(.9,1.3)),.000001f));
    TestTrue(TEXT("Bilinear wrap seam"),FMath::IsNearlyEqual(SampleRoadRed(Pixels,2,2,FVector2f(0,.25)),.5f,.000001f));
    // Native ordinary-plant branch: filter first, inclusive boundaries, exactly
    // one random draw when nonempty. Empty lists must not alter RNG scheduling.
    const TArray<FVector2f> Ranges={{0,.4f},{.2f,1},{.4f,1}};
    for(float G:{0.f,.2f,.4f,1.f})for(uint32 Seed:{0u,1u,962u,123456u})
    {
        FRandom Actual(Seed),Expected(Seed);TArray<int32> Eligible;
        for(int32 J=0;J<Ranges.Num();++J)if(G>=Ranges[J].X&&G<=Ranges[J].Y)Eligible.Add(J);
        TestEqual(TEXT("Filter before selecting variant"),SelectVariant(G,Ranges,Actual),Eligible[(Expected.Next()*Eligible.Num())>>15]);
        TestEqual(TEXT("Variant random consumption"),Actual.State,Expected.State);
    }
    FRandom Empty(962);TestEqual(TEXT("No eligible variant"),SelectVariant(.9f,{{0,.4f}},Empty),INDEX_NONE);TestEqual(TEXT("No random draw for empty eligibility"),Empty.State,962u);
    TestEqual(TEXT("Native dense clod budget"),Patterns(800,958)[0].Num(),200);
    return true;
}
#endif
