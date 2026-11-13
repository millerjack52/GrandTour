#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTLandscapeSurfaceField.h"
#include "Terrain/GTMudRestMap.h"
#include "Terrain/GTLandscapeSurface.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTSiberianSurfaceTest,"GrandTour.Showcase.SurfaceRegression",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTSiberianSurfaceTest::RunTest(const FString&)
{
    const TArray<float> Relief={-20,8,4,-12};
    TestEqual(TEXT("Rest relief preserves centimetre values at texel centres"),GTMudRestMap::SamplePeriodic(Relief,2,100,FVector2D(25,25)),-20.f);
    TestEqual(TEXT("Rest relief wraps negative world coordinates"),GTMudRestMap::SamplePeriodic(Relief,2,100,FVector2D(-75,25)),-20.f);
    TestEqual(TEXT("Rest relief joins continuously at tile edge"),GTMudRestMap::SamplePeriodic(Relief,2,100,FVector2D(0,25)),-6.f);
    TestEqual(TEXT("Sand suppresses initial mud relief"),GTMudRestMap::ReliefWeight(FLinearColor(1,0,1,0),100),0.f);
    TestEqual(TEXT("Rock suppresses initial mud relief"),GTMudRestMap::ReliefWeight(FLinearColor(0,0,0,1),100),0.f);
    TestEqual(TEXT("Deep bare mud keeps its full rest relief"),GTMudRestMap::ReliefWeight(FLinearColor(0,0,1,0),100),1.f);
    TestEqual(TEXT("Legacy sod retains its previous relief"),GTMudRestMap::ReliefWeight(FLinearColor(0,1,1,0),100),0.f);
    TestEqual(TEXT("Woodland grass cover preserves deep soil relief"),GTMudRestMap::ReliefWeight(FLinearColor(0,1,1,0),100,true),1.f);
    TestEqual(TEXT("Vegetation never makes rock deformable"),GTMudRestMap::ReliefWeight(FLinearColor(0,1,1,1),100,true),0.f);
    FGTLandscapeSurfaceSample Covered;Covered.SinkageCapCm=80;Covered.Softness=.8f;Covered.bGrassIsVisualCover=true;
    const float BareSettlement=Covered.LoadedSettlementCm(1);
    Covered.GrassCover=1;
    TestEqual(TEXT("Visual grass cannot reinforce the underlying mud"),Covered.LoadedSettlementCm(1),BareSettlement);
    auto Bed=[](const FVector2D& P){return FMath::Abs(P.Y)<100 ? -80.f : P.X>200 && P.Y>200 ? -180.f : 60.f;};
    FGTWaterBasin B;B.Fill(FVector2D::ZeroVector,FVector2D(1,0),50,1000,0,450,450,Bed,FVector2D(0,0));
    TestTrue(TEXT("Authored seed selects the channel instead of deeper disconnected hollow"),B.IsValid() && B.Wet[B.CellAt(FVector2D(-350,0))] && !B.Wet[B.CellAt(FVector2D(350,350))]);
    FGTWaterField F;F.bClosedBasin=true;F.HeadDropCm=0;F.WindScale=0;
    F.Init(FVector2D::ZeroVector,FVector2D(1,0),400,400,50,0,[](const FVector2D& P){return float(P.Y*.5);});
    const double Volume=F.VolumeM3();float MaxDryDisplacement=0;
    for(int32 I=0;I<F.NumCells();++I){auto C=AGTWaterSheet::ShoreTexel(F,0,I);MaxDryDisplacement=FMath::Max(MaxDryDisplacement,FMath::Abs(C.R));}
    TestTrue(TEXT("Still shoreline remains horizontal through dry bank vertices"),MaxDryDisplacement<.001f);
    const int32 Wet=F.CellIndexAt(FVector2D(0,-25)),Dry=F.CellIndexAt(FVector2D(0,25));
    const auto A=AGTWaterSheet::ShoreTexel(F,0,Wet),D=AGTWaterSheet::ShoreTexel(F,0,Dry);
    TestTrue(TEXT("Signed depth puts shoreline midway between opposite bank samples"),A.G>0 && D.G<0 && FMath::Abs(A.G+D.G)<.001f);
    F.StampLid(FVector2D(0,-150),FVector2D(1,0),100,60,-35,FVector2D::ZeroVector,20,.65f);
    for(int32 S=0;S<120;++S)F.Step(1.f/60,0,0);
    float Error=0;
    for(int32 I=0;I<F.NumCells();++I)if(F.DepthM[I]+F.LidM[I]>.00001f)Error=FMath::Max(Error,FMath::Abs(AGTWaterSheet::ShoreTexel(F,0,I).R-F.SurfaceCm[I]));
    TestTrue(TEXT("Disturbed wet surface matches physics exactly"),Error<.001f);
    TestTrue(TEXT("Rendering changes no conserved water volume"),FMath::Abs(F.VolumeM3()-Volume)<.0001);
    FGTLandscapeSurfaceField Mud;Mud.bNativeShaderUpdates=true;Mud.NativeBaseAlpha=[](FVector2D){return 1.f;};Mud.AuthoredHeightAt=[](FVector2D,float){return 0.f;};
    auto Paint=[](FVector2D){return FLinearColor(110,0,0,1);};Mud.Focus(FVector2D::ZeroVector,Paint);
    for(int32 S=0;S<180;++S){Mud.StampNative(FVector2D(-50,0),FVector2D(50,0),FVector2D(1,0),32,100,Paint,-100,1,{});Mud.StepNative();}
    const float Depth=-Mud.Sample(FVector2D::ZeroVector).DeltaCm;
    TestTrue(TEXT("Recovered native mud update can excavate beyond old 50 cm ceiling"),Depth>65 && Depth<=110);
    FGTLandscapeSurfaceField Mixed;Mixed.bNativeShaderUpdates=true;
    Mixed.NativeUpdateAt=[](FVector2D P){return P.X<0;};
    Mixed.NativeBaseAlpha=[](FVector2D){return 1.f;};Mixed.AuthoredHeightAt=[](FVector2D,float){return 0.f;};
    Mixed.Focus(FVector2D::ZeroVector,Paint);
    Mixed.StampWorked(FVector2D(100,0),FVector2D(150,0),FVector2D(1,0),32,8,Paint,-8,2,{true,.3f,1.f,true});
    TestTrue(TEXT("Sand in a mixed atlas uses host deformation instead of native mud queue"),Mixed.NativeAux.IsEmpty() && Mixed.Sample(FVector2D(125,0)).DeltaCm<0);
    Mixed.StampWorked(FVector2D(-150,0),FVector2D(-100,0),FVector2D(1,0),32,8,Paint,-8,2,{});
    TestTrue(TEXT("Mud in the same atlas enters the recovered update"),!Mixed.NativeAux.IsEmpty());
    AddInfo(FString::Printf(TEXT("Native deep stroke %.3f cm; water render error %.6f cm"),Depth,Error));
    return true;
}
#endif
