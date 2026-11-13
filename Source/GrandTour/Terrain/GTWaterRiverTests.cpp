#include "Terrain/GTWaterField.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterDomain.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTRiverFieldTest, "GrandTour.Water.RiverReference",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTRiverFieldTest::RunTest(const FString& Parameters)
{
	// Legacy still ford remains hydrostatic, with the reference feature absent.
	FGTWaterField Legacy; Legacy.HeadDropCm=0; Legacy.WindScale=0;
	Legacy.Init(FVector2D::ZeroVector,FVector2D(1,0),400,200,25,80,[](const FVector2D&){return 20.f;});
	for(int32 I=0;I<120;++I) Legacy.Step(1.f/60,80,0);
	TestFalse(TEXT("Legacy ford has no reference path"),Legacy.HasRiverReference());
	TestTrue(TEXT("Legacy lake stays at rest"),FMath::Abs(Legacy.SurfaceCmAt(FVector2D::ZeroVector)-80)<.001f);

	FGTWaterField F; F.WindScale=0;
	F.Init(FVector2D::ZeroVector,FVector2D(1,0),2400,1200,37.5,0,[](const FVector2D& P){return -P.X*.06f;});
	TArray<float> H,X,Y;H.Init(0,F.NumCells());X.Init(0,F.NumCells());Y.Init(0,F.NumCells());
	for(int32 I=0;I<F.NumCells();++I)
	{
		const int32 Row=I/F.SizeX;
		if(Row>=24 && Row<40) { H[I]=.25f; if(I%F.SizeX<F.SizeX-1) X[I]=.6f*.375f*.25f; }
	}
	TestTrue(TEXT("Accept balanced sloped reference"),F.SetRiverReference(H,X,Y));
	const double V0=F.VolumeM3();
	for(int32 I=0;I<3600;++I) F.Step(1.f/60,0,1);
	float Drift=0;
	for(int32 I=0;I<F.NumCells();++I) Drift=FMath::Max(Drift,FMath::Abs(F.DepthM[I]-H[I]));
	TestTrue(TEXT("Sloping reference does not flatten or drift over 60s"),Drift<1.e-5f);
	TestTrue(TEXT("Quiescent reference volume is stable"),FMath::Abs(F.VolumeM3()-V0)<1.e-4);
	// A real height impulse; compare symmetric probes, not merely changing material pixels.
	const double Added=F.AddImpulse(FVector2D::ZeroVector,60,2);
	float Down=0,Up=0; double MaxMassError=0;
	for(int32 I=0;I<600;++I)
	{
		F.Step(1.f/60,0,1);
		Down=FMath::Max(Down,FMath::Abs(F.DepthMAt(FVector2D(400,0))-.25f));
		Up=FMath::Max(Up,FMath::Abs(F.DepthMAt(FVector2D(-400,0))-.25f));
		MaxMassError=FMath::Max(MaxMassError,FMath::Abs(F.VolumeM3()-V0-Added-F.RiverBoundaryM3));
	}
	TestTrue(TEXT("Disturbance reaches downstream probe"),Down>.00005f);
	TestTrue(TEXT("No unaccounted water source in interior"),MaxMassError<.001);
	F.ResetRiverReference();
	float Crest=0;
	for(int32 I=0;I<120;++I)
	{
		F.StampLid(FVector2D((I-60)*2.f,0),FVector2D(1,0),80,50,F.SurfaceCmAt(FVector2D::ZeroVector)-8,FVector2D::ZeroVector,8,1);
		F.Step(1.f/60,0,1);
		for(int32 J=0;J<F.NumCells();++J) Crest=FMath::Max(Crest,F.DepthM[J]-H[J]);
	}
	TestTrue(TEXT("Moving solid displaces adjacent water"),Crest>.001);
	TestTrue(TEXT("Moving solid conserves fluid volume with boundary exchange"),FMath::Abs(F.VolumeM3()-V0-F.RiverBoundaryM3)<.002);
	for(int32 I=0;I<3600;++I) F.Step(1.f/60,0,1);
	float Return=0;
	for(int32 I=0;I<F.NumCells();++I) Return=FMath::Max(Return,FMath::Abs(F.DepthM[I]-H[I]));
	TestTrue(TEXT("Released wake returns within 1mm of mean"),Return<.001f);
	TestEqual(TEXT("No depth safety clamps"),F.DepthClamps,0);
	AddInfo(FString::Printf(TEXT("Synthetic: drift %.8fm, downstream %.6fm / upstream %.6fm, moving-lid crest %.6fm, return %.6fm, mass residual %.8fm3, flux limiters %d"),Drift,Down,Up,Crest,Return,MaxMassError,F.FluxClamps));

	// Actual imported Benmore planes, shared with the asset importer.
	TArray<uint8> Bytes;
	if(!TestTrue(TEXT("Benmore reference fixture exists"),FFileHelper::LoadFileToArray(Bytes,*(FPaths::ProjectDir()/TEXT("Art/Export/BenmoreGaea/RiverScale/live-reference.bin"))))) return false;
	int32 NX=0,NY=0; float Meta[5];
	if(!TestTrue(TEXT("Reference header length"),Bytes.Num()>=28)) return false;
	FMemory::Memcpy(&NX,Bytes.GetData(),4); FMemory::Memcpy(&NY,Bytes.GetData()+4,4); FMemory::Memcpy(Meta,Bytes.GetData()+8,20);
	if(!TestTrue(TEXT("Reference bounded payload"),NX>1 && NY>1 && int64(NX)*NY<=8192 && Bytes.Num()==28+NX*NY*16))return false;
	TArray<float> Bed; Bed.SetNum(NX*NY);H.SetNum(NX*NY);X.SetNum(NX*NY);Y.SetNum(NX*NY);
	FMemory::Memcpy(Bed.GetData(),Bytes.GetData()+28,NX*NY*4);
	FMemory::Memcpy(H.GetData(),Bytes.GetData()+28+NX*NY*4,NX*NY*4);
	FMemory::Memcpy(X.GetData(),Bytes.GetData()+28+NX*NY*8,NX*NY*4);
	FMemory::Memcpy(Y.GetData(),Bytes.GetData()+28+NX*NY*12,NX*NY*4);
	const FVector2D AX(Meta[3],Meta[4]),AY(-Meta[4],Meta[3]),Origin(Meta[1],Meta[2]);
	F.Init(Origin+(AX*NX+AY*NY)*Meta[0]*.5,AX,NX*Meta[0]*.5,NY*Meta[0]*.5,Meta[0],1585,[](const FVector2D&){return 0.f;});
	F.BedCm=Bed;
	TestTrue(TEXT("Actual Benmore projected flux accepted"),F.SetRiverReference(H,X,Y));
	const double BenmoreV=F.VolumeM3();
	for(int32 I=0;I<3600;++I)F.Step(1.f/60,1585,1);
	Drift=0;for(int32 I=0;I<F.NumCells();++I)Drift=FMath::Max(Drift,FMath::Abs(F.DepthM[I]-H[I]));
	TestTrue(TEXT("Benmore no-load drift below 0.1mm"),Drift<.0001f);
	const FVector2D Ford(-66125,17750);
	const double RiverAdded=F.AddImpulse(Ford,60,2);
	float Response=0;
	for(int32 I=0;I<600;++I)
	{
		F.Step(1.f/60,1585,1);
		const int32 Probe=F.CellIndexAt(Ford+AX*200);
		Response=FMath::Max(Response,FMath::Abs(F.DepthM[Probe]-H[Probe]));
	}
	TestTrue(TEXT("Benmore disturbance propagates two metres"),Response>.00001);
	TestTrue(TEXT("Benmore mass balance including imposed boundaries"),FMath::Abs(F.VolumeM3()-BenmoreV-RiverAdded-F.RiverBoundaryM3)<.003);
	bool Finite=true,Dry=true;float RenderError=0;
	for(int32 I=0;I<F.NumCells();++I)
	{
		Finite &= FMath::IsFinite(F.DepthM[I]) && F.DepthM[I]>=0;
		if(H[I]==0) Dry &= F.DepthM[I]==0;
		const FLinearColor Texel=AGTWaterSheet::FieldTexel(F,1585,I);
		RenderError=FMath::Max(RenderError,FMath::Abs(Texel.R+1585-F.SurfaceCmAt(F.CellCentreCm(I))));
	}
	TestTrue(TEXT("Finite positive field; dry banks stay dry"),Finite&&Dry);
	TestTrue(TEXT("Uploaded height and physics query agree at texel centres"),RenderError<.002f);
	AddInfo(FString::Printf(TEXT("Benmore: drift %.8fm, downstream response %.7fm, render/query error %.7fcm, mass residual %.8fm3"),Drift,Response,RenderError,F.VolumeM3()-BenmoreV-RiverAdded-F.RiverBoundaryM3));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMovingRiverTest,"GrandTour.Water.MovingDomain",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMovingRiverTest::RunTest(const FString& Parameters)
{
	UGTWaterDomain* Domain=NewObject<UGTWaterDomain>();
	if(!TestTrue(TEXT("Whole-water bake imports"),Domain->ImportBake(FPaths::ProjectDir()/TEXT("Art/Export/BenmoreGaea/RiverScale/water-domain.bin")))) return false;
	float S,H;FVector2D V;
	TestTrue(TEXT("Ford has water before any local simulation"),Domain->Sample(FVector2D(-66125,17750),S,H,V));
	TestTrue(TEXT("Ford current flows southwest"),V.X<0 && V.Y<0);
	TestTrue(TEXT("Upper bridge has water without a second solver"),Domain->Sample(FVector2D(-40625,43875),S,H,V));
	TestFalse(TEXT("Known dry valley is not flooded"),Domain->Sample(FVector2D(0,100000),S,H,V));
	int32 Wet=0,Errors=0;
	for(int32 I=0;I<Domain->SizeX*Domain->SizeY;++I)
	{
		if(Domain->Samples[I*4+1]<=.005) continue;
		++Wet;const FVector2D P=Domain->OriginCm+FVector2D((I%Domain->SizeX+.5)*Domain->CellCm,(I/Domain->SizeX+.5)*Domain->CellCm);
		if(!Domain->Sample(P,S,H,V) || FMath::Abs(S-Domain->Samples[I*4])>.002f) ++Errors;
	}
	TestTrue(TEXT("All baked water cell centres query the authored surface"),Wet>18000 && Errors==0);
	bool Lake=false;
	for(int32 I=0;I<Domain->LakeMask.Num();I+=79) if(Domain->LakeMask[I]>=128)
	{
		const FVector2D P=Domain->LakeMinCm+FVector2D((I%Domain->LakeSizeX+.5)/Domain->LakeSizeX,(I/Domain->LakeSizeX+.5)/Domain->LakeSizeY)*Domain->LakeSpanCm;
		if(P.X<-200000 && Domain->Sample(P,S,H,V)) {Lake=FMath::Abs(S-60)<.001 && V.IsNearlyZero();break;}
	}
	TestTrue(TEXT("Distant lake has still-water queries"),Lake);
	auto Make=[](FVector2D Centre)
	{
		FGTWaterField F;F.HeadDropCm=0;F.WindScale=0;
		F.Init(Centre,FVector2D(1,0),3000,3000,62.5,100,[](const FVector2D&){return 0.f;});
		TArray<float> H,X,Y;H.Init(.5f,F.NumCells());X.Init(0,F.NumCells());Y=X;
		for(int32 I=0;I<F.NumCells();++I) if(I%F.SizeX<F.SizeX-1) X[I]=.625f*.5f*(.4f+.2f*FMath::Sin(F.CellCentreCm(I).X*.001f));
		F.SetRiverReference(H,X,Y,true);return F;
	};
	FGTWaterField A=Make(FVector2D::ZeroVector);
	for(int32 I=0;I<600;++I) A.Step(1.f/60,100,1);
	TestTrue(TEXT("Resampled prescribed current produces no phantom water"),FMath::Abs(A.DepthMAt(FVector2D::ZeroVector)-.5f)<1.e-6f);
	A.AddImpulse(FVector2D::ZeroVector,150,4);
	for(int32 I=0;I<20;++I) A.Step(1.f/60,100,1);
	A.StampLid(FVector2D::ZeroVector,FVector2D(1,0),100,100,40,FVector2D::ZeroVector,10,1);
	FGTWaterField B=Make(FVector2D(1000,0));const int32 Copied=B.CopyRiverOverlap(A);
	TestTrue(TEXT("10 m handoff retains overlapping wet cells"),Copied==80*96);
	float MaxError=0;
	for(int32 I=0;I<B.NumCells();++I)
	{
		const FVector2D P=B.CellCentreCm(I);
		if(P.X<2900 && FMath::Abs(P.Y)<2800) MaxError=FMath::Max(MaxError,FMath::Abs(B.SurfaceCmAt(P)-A.SurfaceCmAt(P)));
	}
	TestTrue(TEXT("No height pop on relocation"),MaxError<.001f);
	TestTrue(TEXT("Retained plus discarded disturbance balances"),FMath::Abs(A.VolumeM3()-B.VolumeM3()-B.RiverWindowDiscardM3)<.001);
	B.Step(1.f/60,100,1);
	TestTrue(TEXT("Pending hull stamps survive handoff"),B.LidCellCount>0);
	TestEqual(TEXT("Local cell count stays bounded"),B.NumCells(),9216);
	AddInfo(FString::Printf(TEXT("Whole domain: %d wet samples, %d mismatches; handoff %d cells, maximum height change %.7f cm"),Wet,Errors,Copied,MaxError));
	return true;
}
#endif
