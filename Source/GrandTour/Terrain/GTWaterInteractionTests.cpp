#include "Terrain/GTWaterInteractionVisuals.h"
#include "Terrain/GTWaterField.h"
#include "Vehicle/GTWaterDrag.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTWaterInteractionTest,"GrandTour.Water.InteractionVisuals",EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FGTWaterInteractionTest::RunTest(const FString& Parameters)
{
	using namespace GTWaterInteractionVisuals;
	const FVector2D SlipVelocity(2,1);
	TestTrue(TEXT("Stable sideways motion keeps its direction regardless of body orientation"),FilterWakeVelocity(SlipVelocity,SlipVelocity,.1f).Equals(SlipVelocity,1.e-6));
	TestTrue(TEXT("Repeated registration in one frame cannot reset bow heading"),FilterWakeVelocity(FVector2D(2,0),FVector2D(0,2),0).Equals(FVector2D(2,0),1.e-6));
	const FVector2D Start(2,0),Turn(0,2);
	const FVector2D Full=FilterWakeVelocity(Start,Turn,.1f);
	const FVector2D Halves=FilterWakeVelocity(FilterWakeVelocity(Start,Turn,.05f),Turn,.05f);
	TestTrue(TEXT("Bow direction filtering is independent of frame partition"),Full.Equals(Halves,1.e-5));
	TestTrue(TEXT("A brief velocity change does not instantly rotate the bow"),FilterWakeVelocity(Start,Turn,1.f/60).X>1.5);
	TestTrue(TEXT("Sustained reverse motion reverses the bow"),FilterWakeVelocity(Start,-Start,.7f).X<-1.9);
	// Directional regression: the old unsigned rolling coefficient braked a car
	// travelling slower than a following current and could not push a parked car.
	auto Drag=[](FVector2D Car,FVector2D Flow){return GTWaterDrag::FlowingWheelFraction(Car-Flow,.25f,2.f,.9f);};
	TestTrue(TEXT("Following current pushes a slower car downstream"),Drag(FVector2D(50,0),FVector2D(150,0)).X>0);
	TestTrue(TEXT("Current pushes a stopped car along its axis"),Drag(FVector2D::ZeroVector,FVector2D(150,0)).X>0);
	TestTrue(TEXT("Car faster than current is resisted"),Drag(FVector2D(250,0),FVector2D(150,0)).X<0);
	TestTrue(TEXT("Drifting with current has zero water drag"),Drag(FVector2D(150,40),FVector2D(150,40)).IsNearlyZero());
	TestTrue(TEXT("Reversing current reverses wheel force"),Drag(FVector2D::ZeroVector,FVector2D(-150,0)).X<0);
	TestTrue(TEXT("Force is capped as a vector, not once per axis"),GTWaterDrag::FlowingWheelFraction(FVector2D(10000,10000),2,10,.3).Size()<=.300001);
	for(FVector2D V:{FVector2D(300,100),FVector2D(-150,80),FVector2D(0,-200)})
		TestTrue(TEXT("Wheel drag dissipates relative motion"),FVector2D::DotProduct(V,GTWaterDrag::FlowingWheelFraction(V,.25f,2,.9f))<0);
	TestTrue(TEXT("Dry wheel has no water force"),GTWaterDrag::FlowingWheelFraction(FVector2D(500,0),0,2,.9f).IsNearlyZero());
	TestEqual(TEXT("Dry tyres never emit"),Activity(8,0,.35,5,.025,.25),0.f);
	TestEqual(TEXT("Still relative water never emits"),Activity(0,.3,.35,5,.025,.25),0.f);
	TestTrue(TEXT("Slow shallow crossing is readable"),Activity(1.5,.15,.35,5,.025,.25)>.3f);
	TestTrue(TEXT("Fast crossing is stronger than a crawl"),Activity(4,.15,.35,5,.025,.25)>Activity(1.5,.15,.35,5,.025,.25));
	TestEqual(TEXT("Full response is bounded"),Activity(100,10,.35,5,.025,.25),1.f);
	TestEqual(TEXT("Neutral height packs exactly"),UnpackHeight(PackHeight(0)),0.f);
	TestEqual(TEXT("Dry car emits no contact foam"),VehicleContactFoam(275,0,220,95,4,0),0.f);
	TestEqual(TEXT("No relative motion emits no contact foam"),VehicleContactFoam(275,0,220,95,0,.3f),0.f);
	TestTrue(TEXT("Contact foam forms a strong bow front"),VehicleContactFoam(275,0,220,95,4,.3f)>.9f);
	TestTrue(TEXT("Side contact exceeds the quiet water beside it"),VehicleContactFoam(0,120,220,95,4,.3f)>VehicleContactFoam(0,320,220,95,4,.3f)+.6f);
	TestTrue(TEXT("Foam concentrates ahead of the hull instead of filling its footprint"),VehicleContactFoam(275,0,220,95,4,.3f)>VehicleContactFoam(0,0,220,95,4,.3f)+.7f);
	TestTrue(TEXT("Short wake aerates behind the rear wheels"),VehicleContactFoam(-320,155,220,95,4,.3f)>.4f);
	TestEqual(TEXT("Long wake remains free of fresh contact foam"),VehicleContactFoam(-900,355,220,95,4,.3f),0.f);
	TestEqual(TEXT("Contact front is symmetric before bank clipping"),VehicleContactFoam(210,120,220,95,4,.3f),VehicleContactFoam(210,-120,220,95,4,.3f));
	bool FoamBounded=true;
	for(float X=-1000;X<=600;X+=25)for(float Y=-650;Y<=650;Y+=25)
	{
		const float Foam=VehicleContactFoam(X,Y,220,95,20,5);
		FoamBounded&=FMath::IsFinite(Foam) && Foam>=0 && Foam<=1;
	}
	TestTrue(TEXT("Focused aeration remains finite and bounded"),FoamBounded);
	TestEqual(TEXT("Released packet starts without a pop"),TrailWaveCm(45,0,1),0.f);
	TestEqual(TEXT("Released packet expires"),TrailWaveCm(400,3.2f,1),0.f);
	TestEqual(TEXT("No wake energy produces no trail"),TrailWaveCm(160,1,0),0.f);
	TestTrue(TEXT("Released crest propagates away from its source"),TrailWaveCm(160,1,1)>TrailWaveCm(45,1,1)+2.f);
	bool TrailBounded=true;
	for(float Age=.05f;Age<3.3f;Age+=.05f)for(float Radius=0;Radius<650;Radius+=10)
		TrailBounded&=FMath::Abs(TrailWaveCm(Radius,Age,2))<=7.f;
	TestTrue(TEXT("Trail packets remain bounded through their lifetime"),TrailBounded);
	TestEqual(TEXT("Mean water is never displaced by the gain"),ExtraHeightCm(0,.5,1.5),0.f);
	TestEqual(TEXT("Disable keeps physical shape"),ExtraHeightCm(12,.5,0),0.f);
	TestEqual(TEXT("Dry cells get no extra height"),ExtraHeightCm(20,0,1.5),0.f);
	TestEqual(TEXT("Dry hull cannot create a visible wake"),VehicleWaveCm(275,0,220,95,5,0),0.f);
	TestEqual(TEXT("Dry car has no visual immersion"),WakeImmersionM(0,0,0),0.f);
	TestEqual(TEXT("Airborne tyres do not reconstruct a wake"),WakeImmersionM(0,.2f,0),0.f);
	const float TyreEntry=WakeImmersionM(0,.15f,.5f);
	TestTrue(TEXT("Tyres entering before the keel make a readable surface wave"),VehicleWaveCm(275,0,220,95,3.5f,TyreEntry)>4.f);
	TestTrue(TEXT("Full tyre contact exceeds partial entry"),WakeImmersionM(0,.15f,1)>TyreEntry);
	TestEqual(TEXT("Deeper hull immersion dominates tyre contribution"),WakeImmersionM(.4f,.2f,1),.4f);
	TestEqual(TEXT("Stationary relative hull has no authored pressure ridge"),VehicleWaveCm(275,0,220,95,0,.3),0.f);
	TestTrue(TEXT("Crawl bow rises visibly ahead of the body"),VehicleWaveCm(275,0,220,95,1.5,.3)>10.f);
	TestTrue(TEXT("Shallow moving hull has relief below the ten-centimetre spray threshold"),VehicleWaveCm(275,0,220,95,3.5,.06)>1.f);
	TestTrue(TEXT("Fast bow response exceeds crawl"),VehicleWaveCm(275,0,220,95,4,.3)>VehicleWaveCm(275,0,220,95,1.5,.3));
	TestTrue(TEXT("Wake arms widen behind the car"),VehicleWaveCm(-380,435,220,95,3,.3)>VehicleWaveCm(-380,0,220,95,3,.3)+3.f);
	TestEqual(TEXT("Wake sides are symmetric before shoreline clipping"),VehicleWaveCm(-380,435,220,95,3,.3),VehicleWaveCm(-380,-435,220,95,3,.3));
	TestEqual(TEXT("Wake has bounded reach"),VehicleWaveCm(-1700,300,220,95,4,.3),0.f);
	bool Bounded=true;
	for(float Depth:{.02f,.1f,.3f,.8f,1.5f})for(int32 Eta=-100;Eta<=100;++Eta)
	{
		const float Height=ExtraHeightCm(Eta,Depth,1.5f);
		Bounded&=FMath::Abs(Height)<=18 && FMath::Abs(Height)<=Depth*35+.0001f;
		Bounded&=FMath::Abs(UnpackHeight(PackHeight(Height))-Height)<=.12501f;
	}
	TestTrue(TEXT("Height bound and byte precision across shallow/deep cells"),Bounded);
	// Exercise real wake heights, not a fabricated eta. Visual packing must not change one cell of physics.
	FGTWaterField F;F.bRiverVisuals=true;F.WindScale=0;
	F.Init(FVector2D::ZeroVector,FVector2D(1,0),3000,3000,62.5,50,[](const FVector2D&){return 0.f;});
	TArray<float> H,X,Y;H.Init(.5f,F.NumCells());X.Init(.5f*.625f*.6f,F.NumCells());Y.Init(0,F.NumCells());F.SetRiverReference(H,X,Y,true);
	FGTWaterField Control=F;float MaxEta=0,MaxVisual=0;
	for(int32 Step=0;Step<120;++Step)
	{
		const FVector2D At(-300+Step*5,0);
		F.StampLid(At,FVector2D(1,0),220,95,20,FVector2D::ZeroVector,170,.24f);
		Control.StampLid(At,FVector2D(1,0),220,95,20,FVector2D::ZeroVector,170,.24f);
		F.Step(1.f/60,50,1);Control.Step(1.f/60,50,1);
		for(int32 I=0;I<F.NumCells();++I)
		{
			const float Eta=F.SurfaceCm[I]-50;
			const float Visual=Eta+UnpackHeight(PackHeight(ExtraHeightCm(Eta,.5,1.5)));
			MaxEta=FMath::Max(MaxEta,FMath::Abs(Eta));MaxVisual=FMath::Max(MaxVisual,FMath::Abs(Visual));
		}
	}
	TestTrue(TEXT("Physical bow/wake receives visible extra relief"),MaxEta>.1 && MaxVisual>MaxEta*1.2);
	TestTrue(TEXT("Cosmetic relief leaves solver exactly unchanged"),F.DepthM==Control.DepthM && F.SurfaceCm==Control.SurfaceCm && F.VolumeM3()==Control.VolumeM3());
	AddInfo(FString::Printf(TEXT("Physical maximum %.3f cm, displayed maximum %.3f cm; exact physics match"),MaxEta,MaxVisual));
	return true;
}
#endif
