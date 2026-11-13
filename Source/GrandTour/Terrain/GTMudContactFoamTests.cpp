#include "Terrain/GTMudContactFoam.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudContactFoamTest,"GrandTour.Water.MudContactFoam",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FGTMudContactFoamTest::RunTest(const FString& Parameters)
{
    FGTWaterField F;F.bClosedBasin=true;F.HeadDropCm=0;F.NominalFlowMps=0;F.WindScale=0;F.DryDepthM=.002f;
    F.Init(FVector2D::ZeroVector,FVector2D(1,0),400,400,25,20,[](FVector2D P){return P.Y>300?30.f:0.f;});
    FGTMudContactFoam A;A.Step(F,1.f/30);
    auto Sum=[](const FGTMudContactFoam& C){double S=0;for(float V:C.Foam)S+=V;return S;};
    TestEqual(TEXT("Calm water generates no wake foam"),Sum(A),0.);
    const int32 I=F.CellIndexAt(FVector2D::ZeroVector);
    F.LidM[I]=.1f;
    const auto Bed=F.BedCm,Depth=F.DepthM,Flux=F.FluxX,Lids=F.LidM;
    A.Step(F,1.f/30);const double Initial=Sum(A);
    TestTrue(TEXT("Contact creates exposed fringe"),Initial>0 && A.Foam[I+1]>0);
    // Frozen occupancy and still water stop production and let the trail decay.
    for(int32 S=0;S<84;++S)A.Step(F,1.f/30);
    TestTrue(TEXT("Stationary contact settles on a 2.8 second timescale"),FMath::Abs(Sum(A)/Initial-FMath::Exp(-1.))<.001);
    TestTrue(TEXT("Foam never changes bed, water depth, flux or occupancy"),F.BedCm==Bed && F.DepthM==Depth && F.FluxX==Flux && F.LidM==Lids);
    F.LidM[I]=0;A.Step(F,1.f/30);
    // Test advection without a new source.
    A.PreviousLid=F.LidM;F.VelXMps.Init(.5f,F.NumCells());
    auto Centre=[&F](const FGTMudContactFoam& C){double M=0,S=0;for(int32 J=0;J<C.Foam.Num();++J){M+=C.Foam[J]*F.CellCentreCm(J).X;S+=C.Foam[J];}return M/FMath::Max(S,1.e-9);};
    const double Before=Centre(A);
    for(int32 S=0;S<30;++S)A.Step(F,1.f/30);
    TestTrue(TEXT("Foam follows actual current"),FMath::Abs(Centre(A)-Before-50)<2);
    bool Bounded=true;for(int32 J=0;J<F.NumCells();++J)
        Bounded&=FMath::IsFinite(A.Foam[J]) && A.Foam[J]>=0 && A.Foam[J]<=1 && (F.DepthM[J]>F.DryDepthM || A.Foam[J]==0);
    TestTrue(TEXT("Dry cells clear and concentrations stay bounded"),Bounded);
    F.DepthM.Init(0,F.NumCells());A.Step(F,1.f/30);TestEqual(TEXT("Drained water cannot retain foam"),Sum(A),0.);
    A.Reset(F.NumCells());TestEqual(TEXT("Sleeping/reset clears residue"),Sum(A),0.);
    return true;
}
#endif
