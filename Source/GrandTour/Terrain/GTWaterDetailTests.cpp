#include "Terrain/GTWaterField.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTWaterDetailTest,"GrandTour.Water.PassiveDetail",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTWaterDetailTest::RunTest(const FString& Parameters)
{
	auto Make=[](FVector2D Centre)
	{
		FGTWaterField F;F.bRiverVisuals=true;F.WindScale=0;F.HeadDropCm=0;
		F.Init(Centre,FVector2D(1,0),3000,3000,62.5,50,[](const FVector2D&){return 0.f;});
		TArray<float> H,X,Y;H.Init(0,F.NumCells());X=H;Y=H;
		for(int32 I=0;I<F.NumCells();++I)if(I/F.SizeX>=36 && I/F.SizeX<60)
		{H[I]=.5f;if(I%F.SizeX+1<F.SizeX)X[I]=.625f*.5f*.6f;}
		F.SetRiverReference(H,X,Y,true);return F;
	};
	FGTWaterField A=Make(FVector2D::ZeroVector),Control=A;
	const double Volume=A.VolumeM3();A.AddRiverDetail(FVector2D::ZeroVector,150,.8f,.7f);
	auto Moments=[](const FGTWaterField& F)
	{
		FVector2D M=FVector2D::ZeroVector;
		for(int32 I=0;I<F.NumCells();++I){M.X+=F.RiverDetail[I].X;M.Y+=F.RiverDetail[I].X*F.CellCentreCm(I).X;}
		return FVector2D(M.X,M.X>0?M.Y/M.X:0);
	};
	const FVector2D Initial=Moments(A);
	float MaxPhysicsError=0;
	for(int32 Step=0;Step<240;++Step)
	{
		A.Step(1.f/60,50,1);Control.Step(1.f/60,50,1);A.StepRiverDetail(1.f/60);
		for(int32 I=0;I<A.NumCells();++I)MaxPhysicsError=FMath::Max(MaxPhysicsError,FMath::Abs(A.DepthM[I]-Control.DepthM[I]));
	}
	const FVector2D After=Moments(A);
	TestTrue(TEXT("Foam travels 2.4 m downstream in four seconds"),FMath::Abs(After.Y-Initial.Y-240)<12);
	TestTrue(TEXT("Foam decays on four-second timescale"),FMath::Abs(After.X/Initial.X-FMath::Exp(-1.))<.02);
	TestTrue(TEXT("Visual field never changes physics or water volume"),MaxPhysicsError==0 && FMath::Abs(A.VolumeM3()-Volume)<1.e-6);
	bool Clean=true;for(int32 I=0;I<A.NumCells();++I)
	{const FVector2f C=A.RiverDetail[I];Clean&=FMath::IsFinite(C.X)&&FMath::IsFinite(C.Y)&&C.X>=0&&C.X<=1&&C.Y>=0&&C.Y<=1;if(A.GetRiverDepthM()[I]==0)Clean&=C.IsNearlyZero();}
	TestTrue(TEXT("Finite bounded concentrations and dry banks"),Clean);
	FGTWaterField B=Make(FVector2D(1000,0));B.CopyRiverOverlap(A);
	TestTrue(TEXT("Foam retained through window handoff"),FMath::Abs(Moments(B).X-After.X)<.0001);
	B.ResetRiverReference();TestTrue(TEXT("Reset clears visual residue"),Moments(B).X==0);
	B.StampLid(FVector2D(1000,0),FVector2D(1,0),130,70,40,FVector2D::ZeroVector,10,1);
	B.Step(1.f/30,50,1);B.StepRiverDetail(1.f/30);
	TestTrue(TEXT("Immersed solid generates foam and sediment"),Moments(B).X>0 && B.RiverDetail[B.CellIndexAt(FVector2D(1000,0))].Y>0);
	AddInfo(FString::Printf(TEXT("Detail: centre %.2f -> %.2f cm, foam retention %.5f, max physics error %.9f m; %d active of %d cells"),Initial.Y,After.Y,After.X/Initial.X,MaxPhysicsError,A.RiverActiveCells(),A.NumCells()));
	return true;
}
#endif
