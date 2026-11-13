#include "Terrain/GTLandscapeSurfaceField.h"
#include "Terrain/GTMudContactModel.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTSandResponseTest,"GrandTour.LandscapeMud.GranularSand",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTSandResponseTest::RunTest(const FString& Parameters)
{
    const GTMudContact::FState Loose={true,.02f,.04f,0,0,true},Packed={true,.02f,.04f,1,10,true};
    auto L=GTMudContact::Evaluate(.9,0,16,32,120,160,Loose);
    auto P=GTMudContact::Evaluate(.9,0,16,32,120,160,Packed);
    auto Spin=GTMudContact::Evaluate(.9,0,16,32,120,650,Loose);
    TestTrue(TEXT("Packed sand supports more traction and less rolling work"),P.Grip>L.Grip && P.Resistance<L.Resistance);
    TestTrue(TEXT("Excessive spin loses usable traction"),Spin.Grip<L.Grip);
    TestTrue(TEXT("Deeper sand demands more work"),GTMudContact::Evaluate(.9,0,20,32,120,160,Loose).Resistance>GTMudContact::Evaluate(.9,0,3,32,120,160,Loose).Resistance);
    auto Paint=[](FVector2D){return FLinearColor(38,-50,0,.9);};
    FGTLandscapeSurfaceField F;
    F.AuthoredHeightAt=[](FVector2D,float){return 0.f;};
    F.ShapeAt=[](FVector2D){return FLinearColor(.02,.04,1,1);};F.Focus(FVector2D::ZeroVector,Paint);
    for(int32 I=0;I<100;++I)F.StampWorked(FVector2D(I*2,0),FVector2D(I*2+2,0),FVector2D(1,0),28,16,Paint,-13,.8,{true,.4,1,true});
    double Net=0;float Outside=0,Min=0;bool Finite=true;
    for(const auto& T:F.Tiles)for(int32 I=0;I<T.Value.Cells.Num();++I)
    {
        const auto& C=T.Value.Cells[I];Net+=C.DeltaCm;Min=FMath::Min(Min,C.DeltaCm);
        Finite&=FMath::IsFinite(C.DeltaCm)&&C.DeltaCm>=-38&&C.DeltaCm<=15.001;
        const FVector2D XY=F.Centre(T.Key*F.TileCells+FIntPoint(I%F.TileCells,I/F.TileCells));
        if(FMath::Abs(XY.Y)>38)Outside+=FMath::Max(0.f,C.DeltaCm);
    }
    TestTrue(TEXT("Dry granular response cuts a tyre depression and spreads shoulders"),Min< -5 && Outside>1);
    TestTrue(TEXT("Actual dry sand volume is conserved"),FMath::Abs(Net*F.CellCm*F.CellCm)<.5);
    TestTrue(TEXT("Finite bounded sand field"),Finite);
    return true;
}
#endif
