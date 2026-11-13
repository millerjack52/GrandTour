#include "Core/GTFordDiagRunner.h"

#include "Core/GTPlayerController.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTProvingGround.h"
#include "Terrain/GTSurfacePhysMaterial.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTDrivetrainComponent.h"
#include "Vehicle/GTTractionComponent.h"
#include "Vehicle/GTWaterDiag.h"

#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "LandscapeProxy.h"

namespace
{
	enum EPhase : int32 { FindCar = 0, PadSettle, DoSurvey, RunSetup, RunSettle, RunDrive, AllDone };
	constexpr float RunSettleS = 3.f;
	constexpr float RunTimeoutS = 60.f;
	constexpr float DryLengthM = 30.f;
	constexpr float BeforeM = 15.f;     // the start before the entry waterline, and the end past the exit
	constexpr float BankWindowM = 4.f;  // the bank statistics' window either side of a waterline
	constexpr float TickWindowM = 6.f;  // gt.Water.Diag 2 (every tick) within this of a waterline
	constexpr float BogRunTimeoutS = 45.f;   // RIVERBED S2: a bog run that has not left the box by then is logged as such
	constexpr float WetCm = 2.f;             // RIVERBED S4: GTFORDRUT's "under the water" (a dry cell under a placed box reads its bed, a few mm off the landscape)
}

// ---- RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): the mud patch box's edge ----------------------------------

float FGTFordDiagRunner::PastEdgeM(const FVector& XY) const
{
	// How far past the nearest side of the box, m: negative inside, positive outside (the larger axis at a corner).
	const float DX = FMath::Max(BoxMin.X - static_cast<float>(XY.X), static_cast<float>(XY.X) - BoxMax.X);
	const float DY = FMath::Max(BoxMin.Y - static_cast<float>(XY.Y), static_cast<float>(XY.Y) - BoxMax.Y);
	return FMath::Max(DX, DY) * 0.01f;
}

bool FGTFordDiagRunner::BeginBogRun(FVector& OutLocation, float& OutYaw)
{
	const FRunDef& Run = Runs[RunIndex];
	if (!Spec.Sections.IsValidIndex(BogSection))
	{
		return false;
	}
	const FGTRouteSection& Section = Spec.Sections[BogSection];
	// Sideways: from 4.5 m off the axis at the section's middle, 35 degrees off the route, so the wheels leave the box
	// through its side some metres on. To the right (1) the Mud reaches the box's side (the case where the shrink is still
	// deep at the edge); to the left (3) L_Proving's box reaches past the bend, so there is scrub inside it first. Along
	// (2): 4 m before the section's end on the axis, out past the end and the box beyond it.
	const bool bSide = Run.Bog == 1 || Run.Bog == 3;
	const float SideSign = Run.Bog == 1 ? -1.f : 1.f;   // -1 the route's right, +1 its left
	const float ArcM = bSide ? 0.5f * (Section.StartM + Section.EndM) : Section.EndM - 4.f;
	FVector2D Left;
	FVector2D Point = RoutePoint(ArcM, Left);
	float RouteYaw = 0.f;
	GTTerrain::PointOnPolyline(Spec.RouteM, ArcM, RouteYaw);
	OutYaw = bSide ? RouteYaw + SideSign * 35.f : RouteYaw;
	if (bSide)
	{
		Point += Left * (SideSign * 450.f);
	}
	const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const AGTMudPatch* Patch = Mud ? Mud->PatchAt(Point) : nullptr;
	if (!Patch)
	{
		return false;
	}
	BoxMin = Patch->BoundsMin;
	BoxMax = Patch->BoundsMax;
	DryStart = Point;
	DryDir = FVector2D(FMath::Cos(FMath::DegreesToRadians(OutYaw)), FMath::Sin(FMath::DegreesToRadians(OutYaw)));
	OutLocation = FVector(Point.X, Point.Y, 0.f);
	for (int32 Index = 0; Index < 4; ++Index)
	{
		EdgeCrossed[Index] = false;
		VisAtEdgeCm[Index] = RawAtEdgeCm[Index] = SpeedAtEdge[Index] = MaxVisPastCm[Index] = 0.f;
		CapPastM[Index] = -1.f;
	}
	EdgeMaxRiseCm = EdgeRisePastM = EdgeRiseDtMs = EdgeRiseSpeed = RunMaxRiseCm = EdgeMaxRadiusRiseCm = 0.f;
	EdgeRadiusWheel = -1;
	bPrevChassis = false;
	EdgeTicks = 0;
	if (const UGTTractionComponent* Traction = Car->GetTraction())
	{
		CapM = Traction->OutsidePatchSinkCapM;
	}
	SetCvar(TEXT("gt.Mud.SinkRiseRate"), Run.RiseRate);
	Log(FString::Printf(TEXT("run %s: the bog's box x %.0f..%.0f y %.0f..%.0f cm, start %.2f m from its nearest side, heading %.1f (route %.1f); cap %.1f cm, rise rate %.2f m/m, gt.Mud.SinkCap %s"),
		*Run.Name, BoxMin.X, BoxMax.X, BoxMin.Y, BoxMax.Y, -PastEdgeM(OutLocation), OutYaw, RouteYaw, CapM * 100.f,
		Run.RiseRate >= 0.f ? Run.RiseRate : (Car->GetTraction() ? Car->GetTraction()->VisibleSinkRiseRate : 0.f),
		IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.SinkCap")) ? *IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.SinkCap"))->GetString() : TEXT("(none)")));
	return true;
}

bool FGTFordDiagRunner::TickBogRun(float DeltaSeconds)
{
	const FRunDef& Run = Runs[RunIndex];
	AGTCarPawn* TheCar = Car.Get();
	const FGTWaterDiagSample S = GTWaterDiag::Measure(*TheCar);
	Steer(S.SpeedMps);
	DriveTime += DeltaSeconds;
	DtSum += DeltaSeconds;
	++Ticks;
	VEnd = S.SpeedMps;
	const float Z = static_cast<float>(TheCar->GetActorLocation().Z);
	float Past[4] = { 0.f, 0.f, 0.f, 0.f };
	float MinPast = 1.e9f;
	float MaxPast = -1.e9f;
	const int32 N = FMath::Min(4, S.NumWheels);
	for (int32 Index = 0; Index < N; ++Index)
	{
		const FGTWaterDiagWheel& W = S.Wheels[Index];
		Past[Index] = PastEdgeM(W.ContactCm);
		MinPast = FMath::Min(MinPast, Past[Index]);
		MaxPast = FMath::Max(MaxPast, Past[Index]);
		if (!EdgeCrossed[Index] && Past[Index] >= 0.f)
		{
			EdgeCrossed[Index] = true;
			VisAtEdgeCm[Index] = W.VisSinkM * 100.f;
			RawAtEdgeCm[Index] = W.SinkM * 100.f;
			SpeedAtEdge[Index] = S.Speed2DMps;
		}
		if (EdgeCrossed[Index])
		{
			MaxVisPastCm[Index] = FMath::Max(MaxVisPastCm[Index], W.VisSinkM * 100.f);
			if (CapPastM[Index] < 0.f && W.VisSinkM <= CapM + 0.001f)
			{
				CapPastM[Index] = Past[Index];
			}
		}
	}
	const bool bNear = MaxPast > -3.f && MinPast < 3.f;
	const bool bWindow = MaxPast >= -1.f && MinPast <= 2.f;   // the gate's window: a wheel within 1 m before the edge to all 2 m past
	SetCvar(TEXT("gt.Water.Diag"), bNear ? 2.f : 1.f);
	if (bPrevChassis)
	{
		const float Rise = Z - PrevChassisZ;
		if (DriveTime > 2.f)
		{
			RunMaxRiseCm = FMath::Max(RunMaxRiseCm, Rise);
		}
		if (bWindow)
		{
			++EdgeTicks;
			if (Rise > EdgeMaxRiseCm)
			{
				EdgeMaxRiseCm = Rise;
				EdgeRisePastM = MaxPast;
				EdgeRiseDtMs = DeltaSeconds * 1000.f;
				EdgeRiseSpeed = S.Speed2DMps;
			}
			for (int32 Index = 0; Index < N; ++Index)
			{
				if (bHavePrev && S.Wheels[Index].RadiusCm - PrevR[Index] > EdgeMaxRadiusRiseCm)
				{
					EdgeMaxRadiusRiseCm = S.Wheels[Index].RadiusCm - PrevR[Index];
					EdgeRadiusWheel = Index;
				}
			}
		}
	}
	if (bNear)
	{
		FString Line = FString::Printf(TEXT("edge %s t=%.3f dt=%.1f z=%.2f dz=%+.2f v=%.2f"), *Run.Name, DriveTime, DeltaSeconds * 1000.f, Z, bPrevChassis ? Z - PrevChassisZ : 0.f, S.Speed2DMps);
		for (int32 Index = 0; Index < N; ++Index)
		{
			const FGTWaterDiagWheel& W = S.Wheels[Index];
			Line += FString::Printf(TEXT(" | w%d past=%+.3f vis=%.2f raw=%.2f r=%.1f box=%d c=%d tg=%s"), Index, Past[Index], W.VisSinkM * 100.f, W.SinkM * 100.f, W.RadiusCm, W.bInPatchBox ? 1 : 0, W.bContact ? 1 : 0, *W.Tag);
		}
		Log(Line);
	}
	PrevChassisZ = Z;
	bPrevChassis = true;
	for (int32 Index = 0; Index < N; ++Index)
	{
		PrevR[Index] = S.Wheels[Index].RadiusCm;
	}
	bHavePrev = true;
	if (MinPast >= 3.f)
	{
		EndRun(TEXT("through"));
		return true;
	}
	StuckTime = (DriveTime > 4.f && FMath::Abs(S.Speed2DMps) < 0.2f) ? StuckTime + DeltaSeconds : 0.f;
	if (StuckTime > 6.f)
	{
		EndRun(FString::Printf(TEXT("stuck %.2f m from the edge"), MaxPast));
		return true;
	}
	if (DriveTime > BogRunTimeoutS)
	{
		EndRun(FString::Printf(TEXT("timeout %.2f m from the edge"), MaxPast));
		return true;
	}
	return false;
}

FString FGTFordDiagRunner::EndBogRun(const FString& Why, float MeanDtMs)
{
	const FRunDef& Run = Runs[RunIndex];
	FString Wheels;
	bool bCapOk = true;
	int32 Crossed = 0;
	float WorstCapM = 0.f;
	for (int32 Index = 0; Index < 4; ++Index)
	{
		if (!EdgeCrossed[Index])
		{
			Wheels += FString::Printf(TEXT(" w%d did not cross;"), Index);
			bCapOk = false;
			continue;
		}
		++Crossed;
		const bool bAbove = VisAtEdgeCm[Index] > CapM * 100.f + 0.1f;
		const bool bOk = CapPastM[Index] >= 0.f && CapPastM[Index] <= 1.0f;
		bCapOk &= bOk;
		WorstCapM = FMath::Max(WorstCapM, CapPastM[Index] < 0.f ? 99.f : CapPastM[Index]);
		Wheels += FString::Printf(TEXT(" w%d at the edge vis %.1f raw %.1f cm at %.2f m/s, %s %s;"), Index, VisAtEdgeCm[Index], RawAtEdgeCm[Index], SpeedAtEdge[Index],
			bAbove ? TEXT("down to the cap") : TEXT("at the cap on crossing,"),
			CapPastM[Index] >= 0.f ? *FString::Printf(TEXT("%+.2f m past"), CapPastM[Index]) : TEXT("never"));
	}
	const bool bRiseOk = EdgeTicks > 0 && EdgeMaxRiseCm < 2.f;
	Digest.Add(FString::Printf(TEXT("%s %s rise %.2f cm cap by %.2f m"), *Run.Name, *Why, EdgeMaxRiseCm, WorstCapM));
	return FString::Printf(TEXT("end %s: %s; per wheel:%s biggest one-tick chassis rise %.2f cm (dt %.1f ms, the leading wheel %+.2f m past, %.2f m/s) over %d ticks from a wheel 1 m before the edge to all 2 m past; %.2f cm over the whole run after 2 s; biggest one-tick radius rise in the window %.2f cm (w%d); deepest visible sinkage past the edge %.1f %.1f %.1f %.1f cm; mean frame %.2f ms -> gates: rise %d (asked < 2 cm), at the cap within 1.0 m %d"),
		*Run.Name, *Why, *Wheels, EdgeMaxRiseCm, EdgeRiseDtMs, EdgeRisePastM, EdgeRiseSpeed, EdgeTicks, RunMaxRiseCm, EdgeMaxRadiusRiseCm, EdgeRadiusWheel,
		MaxVisPastCm[0], MaxVisPastCm[1], MaxVisPastCm[2], MaxVisPastCm[3], MeanDtMs, bRiseOk ? 1 : 0, (bCapOk && Crossed == 4) ? 1 : 0);
}

FGTFordDiagRunner::FGTFordDiagRunner(UWorld* InWorld)
	: World(InWorld)
{
}

void FGTFordDiagRunner::Log(const FString& Line) const
{
	UE_LOG(LogTemp, Display, TEXT("GTFORDDIAG %s"), *Line);
}

void FGTFordDiagRunner::SetCvar(const TCHAR* Name, float Value) const
{
	if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name))
	{
		Var->Set(*FString::SanitizeFloat(Value), ECVF_SetByConsole);
	}
	else
	{
		Log(FString::Printf(TEXT("no cvar %s"), Name));
	}
}

float FGTFordDiagRunner::LandscapeZ(float XCm, float YCm, bool& bOk) const
{
	for (const TWeakObjectPtr<ALandscapeProxy>& Proxy : Landscapes)
	{
		if (Proxy.IsValid())
		{
			const TOptional<float> Height = Proxy->GetHeightAtLocation(FVector(XCm, YCm, 0.f));
			if (Height.IsSet())
			{
				bOk = true;
				return Height.GetValue();
			}
		}
	}
	bOk = false;
	return 0.f;
}

bool FGTFordDiagRunner::TraceZ(float XCm, float YCm, float& OutZ, const UGTSurfacePhysMaterial*& OutSurface, FString& OutWhat) const
{
	OutSurface = nullptr;
	OutWhat = TEXT("-");
	UWorld* W = World.Get();
	if (!W)
	{
		return false;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GTFordDiag), false);
	Params.bReturnPhysicalMaterial = true;
	if (Car.IsValid())
	{
		Params.AddIgnoredActor(Car.Get());
	}
	FHitResult Hit;
	if (!W->LineTraceSingleByObjectType(Hit, FVector(XCm, YCm, 50000.f), FVector(XCm, YCm, -50000.f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		return false;
	}
	OutZ = static_cast<float>(Hit.ImpactPoint.Z);
	OutSurface = Cast<UGTSurfacePhysMaterial>(Hit.PhysMaterial.Get());
	const AActor* Actor = Hit.GetActor();
	OutWhat = !Actor ? TEXT("?") : (Actor->IsA<ALandscapeProxy>() ? TEXT("L") : Actor->GetClass()->GetName());
	return true;
}

FVector2D FGTFordDiagRunner::RoutePoint(float ArcM, FVector2D& OutLeft) const
{
	float Yaw = 0.f;
	const FVector2D P = GTTerrain::PointOnPolyline(Spec.RouteM, ArcM, Yaw);
	const float Rad = FMath::DegreesToRadians(Yaw);
	OutLeft = FVector2D(-FMath::Sin(Rad), FMath::Cos(Rad));
	return P * 100.f;
}

void FGTFordDiagRunner::Survey()
{
	for (TActorIterator<ALandscapeProxy> It(World.Get()); It; ++It)
	{
		Landscapes.Add(*It);
	}
	Log(FString::Printf(TEXT("survey: %d landscape proxies, the car's half track %.3f m, half wheelbase %.3f m"), Landscapes.Num(), HalfTrackM, HalfBaseM));
	const TCHAR* Names[] = { TEXT("forda"), TEXT("fordb"), TEXT("fordc"), TEXT("fordd") };
	for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
	{
		const FGTRouteSection& Section = Spec.Sections[Index];
		if (Section.Kind != EGTRouteSectionKind::Ford || Fords.Num() >= 4)
		{
			continue;
		}
		FFord Ford;
		Ford.Name = Names[Fords.Num()];
		Ford.Section = Index;
		Ford.StartM = Section.StartM;
		Ford.EndM = Section.EndM;
		Ford.DepthM = Section.DepthM;
		SurveyFord(Ford);
		Fords.Add(Ford);
	}
	SurveyRocks();
	for (const UGTSurfacePhysMaterial* Row : RowsSeen)
	{
		if (Row)
		{
			Log(FString::Printf(TEXT("row %s tag=%s Friction=%.3f RollingResistance=%.3f SinkageRate=%.3f MaxSinkage=%.3f WetSinkageScale=%.2f SinkageDragScale=%.2f PloughDrag=%.3f SinkageGripLoss=%.3f WetRollingResistanceScale=%.2f WetFrictionScale=%.2f TrackDepth=%.2f"),
				*Row->GetName(), *Row->SurfaceTag.ToString(), Row->Friction, Row->RollingResistance, Row->SinkageRate, Row->MaxSinkage, Row->WetSinkageScale,
				Row->SinkageDragScale, Row->PloughDrag, Row->SinkageGripLoss, Row->WetRollingResistanceScale, Row->WetFrictionScale, Row->TrackDepth));
		}
	}
}

void FGTFordDiagRunner::SurveyFord(FFord& Ford)
{
	UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	FVector2D Left;
	const FVector2D Mid = RoutePoint((Ford.StartM + Ford.EndM) * 0.5f, Left);
	const AGTWaterSheet* Sheet = Water ? Water->SheetAt(Mid) : nullptr;
	if (!Sheet)
	{
		Log(FString::Printf(TEXT("%s: no water sheet at the section's middle"), *Ford.Name));
		return;
	}
	Ford.LevelCm = Sheet->GetLevelCm();
	// The waterlines along the centre line: every 5 cm, the heightfield and the trace against the still level.
	TArray<FString> Stretches;
	TArray<FString> TraceStretches;
	bool bWasWet = false, bWasTraceWet = false;
	float WetFrom = 0.f, TraceWetFrom = 0.f;
	float FirstWet = -1.f, LastWet = -1.f;
	float Deepest = 0.f, DeepestArc = 0.f;
	for (float Arc = Ford.StartM - 25.f; Arc <= Ford.EndM + 25.f; Arc += 0.05f)
	{
		const FVector2D P = RoutePoint(Arc, Left);
		bool bOk = false;
		const float Z = LandscapeZ(P.X, P.Y, bOk);
		float TZ = 0.f;
		const UGTSurfacePhysMaterial* Row = nullptr;
		FString What;
		const bool bTrace = TraceZ(P.X, P.Y, TZ, Row, What);
		const bool bWet = bOk && Z < Ford.LevelCm && Sheet->Covers(P);
		const bool bTraceWet = bTrace && TZ < Ford.LevelCm && Sheet->Covers(P);
		if (bWet && Ford.LevelCm - Z > Deepest)
		{
			Deepest = Ford.LevelCm - Z;
			DeepestArc = Arc;
		}
		if (bWet != bWasWet)
		{
			if (bWet) { WetFrom = Arc; if (FirstWet < 0.f) { FirstWet = Arc; } }
			else { Stretches.Add(FString::Printf(TEXT("%.2f-%.2f"), WetFrom, Arc)); LastWet = Arc; }
			bWasWet = bWet;
		}
		if (bTraceWet != bWasTraceWet)
		{
			if (bTraceWet) { TraceWetFrom = Arc; }
			else { TraceStretches.Add(FString::Printf(TEXT("%.2f-%.2f"), TraceWetFrom, Arc)); }
			bWasTraceWet = bTraceWet;
		}
	}
	Ford.EntryM = FirstWet;
	Ford.ExitM = LastWet;
	Ford.bValid = FirstWet >= 0.f && LastWet > FirstWet;
	Log(FString::Printf(TEXT("%s: section %d %.2f-%.2f m depth %.2f m; sheet %s level %.1f cm; wet along the centre (heightfield) %s; (trace) %s; entry %.2f exit %.2f (%.2f m of water); deepest %.1f cm at %.2f"),
		*Ford.Name, Ford.Section, Ford.StartM, Ford.EndM, Ford.DepthM, *Sheet->GetName(), Ford.LevelCm, *FString::Join(Stretches, TEXT(",")), *FString::Join(TraceStretches, TEXT(",")),
		Ford.EntryM, Ford.ExitM, Ford.ExitM - Ford.EntryM, Deepest, DeepestArc));
	if (!Ford.bValid)
	{
		return;
	}
	// The profile, every 25 cm, on the centre line and both wheel lines: heightfield, trace, the generator's analytic
	// height; the centre's surface and what the trace hit (L the landscape).
	for (float Arc = Ford.EntryM - 6.f; Arc <= Ford.ExitM + 6.001f; Arc += 0.25f)
	{
		FString Parts;
		const FVector2D C = RoutePoint(Arc, Left);
		const float Offsets[3] = { 0.f, HalfTrackM, -HalfTrackM };
		const TCHAR* Keys[3] = { TEXT("c"), TEXT("l"), TEXT("r") };
		for (int32 K = 0; K < 3; ++K)
		{
			const FVector2D P = C + Left * (Offsets[K] * 100.f);
			bool bOk = false;
			const float Z = LandscapeZ(P.X, P.Y, bOk);
			float TZ = -1.e6f;
			const UGTSurfacePhysMaterial* Row = nullptr;
			FString What;
			TraceZ(P.X, P.Y, TZ, Row, What);
			if (Row)
			{
				RowsSeen.Add(Row);
			}
			const float AZ = GTTerrain::SampleHeightCm(Spec, P.X, P.Y);
			Parts += FString::Printf(TEXT(" %s=%.1f,%.1f,%.1f,%s,%s"), Keys[K], bOk ? Z : -1.e6f, TZ, AZ,
				Row ? *Row->SurfaceTag.ToString().Replace(TEXT("Surface."), TEXT("")) : TEXT("-"), *What);
		}
		UE_LOG(LogTemp, Display, TEXT("GTFORDPROF %s a=%.2f level=%.1f%s"), *Ford.Name, Arc, Ford.LevelCm, *Parts);
	}
	// Where the surface under each line changes, every 5 cm from 15 m before the section to 15 m past it.
	const float Offsets[3] = { 0.f, HalfTrackM, -HalfTrackM };
	const TCHAR* Keys[3] = { TEXT("c"), TEXT("l"), TEXT("r") };
	for (int32 K = 0; K < 3; ++K)
	{
		FString Previous;
		TArray<FString> Changes;
		for (float Arc = Ford.StartM - 15.f; Arc <= Ford.EndM + 15.f; Arc += 0.05f)
		{
			const FVector2D P = RoutePoint(Arc, Left) + Left * (Offsets[K] * 100.f);
			float TZ = 0.f;
			const UGTSurfacePhysMaterial* Row = nullptr;
			FString What;
			TraceZ(P.X, P.Y, TZ, Row, What);
			if (Row)
			{
				RowsSeen.Add(Row);
			}
			const FString Tag = Row ? Row->SurfaceTag.ToString().Replace(TEXT("Surface."), TEXT("")) : FString(TEXT("-"));
			const FString Now = Tag + TEXT("/") + What;
			if (Now != Previous)
			{
				Changes.Add(FString::Printf(TEXT("%.2f:%s"), Arc, *Now));
				Previous = Now;
			}
		}
		Log(FString::Printf(TEXT("%s surface line %s (offset %+.2f m) changes: %s"), *Ford.Name, Keys[K], Offsets[K], *FString::Join(Changes, TEXT(" "))));
	}
}

void FGTFordDiagRunner::SurveyRocks()
{
	TArray<FGTTerrainStone> Rocks;
	GTTerrain::FordRocks(Spec, Rocks);
	Log(FString::Printf(TEXT("rocks: %d from GTTerrain::FordRocks"), Rocks.Num()));
	for (int32 Index = 0; Index < Rocks.Num(); ++Index)
	{
		const FGTTerrainStone& Rock = Rocks[Index];
		const float XCm = Rock.PositionM.X * 100.f;
		const float YCm = Rock.PositionM.Y * 100.f;
		const FGTRouteHit Hit = GTTerrain::RouteAtCm(Spec, XCm, YCm);
		const FFord* Owner = nullptr;
		for (const FFord& Ford : Fords)
		{
			if (Hit.ArcM >= Ford.StartM - 5.f && Hit.ArcM <= Ford.EndM + 5.f)
			{
				Owner = &Ford;
			}
		}
		bool bOk = false;
		const float Ground = LandscapeZ(XCm, YCm, bOk);
		float Top = 0.f;
		const UGTSurfacePhysMaterial* Row = nullptr;
		FString What;
		const bool bTrace = TraceZ(XCm, YCm, Top, Row, What);
		Log(FString::Printf(TEXT("rock %d at (%.2f, %.2f) m size %.2f m: arc %.2f offset %+.2f m (%s: %+.2f m from the entry waterline, %+.2f m from the exit); top %.1f cm over the landscape (hit %s), planned exposure %.1f cm; the still level %.1f cm over the landscape there"),
			Index, Rock.PositionM.X, Rock.PositionM.Y, Rock.SizeM, Hit.ArcM, Hit.SignedM, Owner ? *Owner->Name : TEXT("none"),
			Owner ? Hit.ArcM - Owner->EntryM : 0.f, Owner ? Hit.ArcM - Owner->ExitM : 0.f,
			(bTrace && bOk) ? Top - Ground : -1.f, *What, GTTerrain::FordRockExposedCm(Rock.SizeM), Owner && bOk ? Owner->LevelCm - Ground : 0.f));
	}
}

void FGTFordDiagRunner::BeginRun()
{
	const FRunDef& Run = Runs[RunIndex];
	AGTCarPawn* TheCar = Car.Get();
	SetCvar(TEXT("gt.Water.Hull"), static_cast<float>(Run.Hull));
	SetCvar(TEXT("gt.Water.Buoyancy"), static_cast<float>(Run.Buoyancy));
	SetCvar(TEXT("gt.Water.Diag"), 0.f);
	FVector Location;
	float Yaw = 0.f;
	if (Run.Bog > 0)
	{
		if (!BeginBogRun(Location, Yaw))
		{
			Log(FString::Printf(TEXT("run %s: no Mud section or no patch over its start; the car stays on the pad"), *Run.Name));
			Location = FVector(-2700.f, -1000.f, 0.f);
		}
	}
	else if (Run.Ford == INDEX_NONE)
	{
		DryStart = FVector2D(-2700.f, -1000.f);
		DryDir = FVector2D(1.f, 0.f);
		Location = FVector(DryStart.X, DryStart.Y, 0.f);
	}
	else
	{
		const FFord& Ford = Fords[Run.Ford];
		StartArcM = Ford.EntryM - BeforeM;
		// RIVERBED S4: past the bed patch's box as well, so the run crosses its edge (where the shrink goes back to the cap).
		EndArcM = Ford.ExitM + BeforeM;
		BoxExitArcM = -1.f;
		if (const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>())
		{
			FVector2D MidLeft;
			const AGTMudPatch* Bed = Mud->PatchAt(RoutePoint(0.5f * (Ford.EntryM + Ford.ExitM), MidLeft));
			for (float A = Ford.ExitM; Bed && A < Ford.ExitM + 60.f; A += 0.25f)
			{
				FVector2D ALeft;
				if (Mud->PatchAt(RoutePoint(A, ALeft)) != Bed)
				{
					BoxExitArcM = A;
					EndArcM = FMath::Max(EndArcM, A + 5.f);
					break;
				}
			}
		}
		FVector2D Left;
		const FVector2D P = RoutePoint(StartArcM, Left);
		GTTerrain::PointOnPolyline(Spec.RouteM, StartArcM, Yaw);
		Location = FVector(P.X, P.Y, 0.f);
	}
	float Ground = 0.f;
	if (!GTProving::GroundZ(World.Get(), Location.X, Location.Y, Ground, TheCar))
	{
		Ground = GTTerrain::SampleHeightCm(Spec, Location.X, Location.Y);
	}
	Location.Z = Ground + 60.f;
	TheCar->SetActorLocationAndRotation(Location, FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	TheCar->GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	TheCar->GetMesh()->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
	TheCar->ResetDrivingInputs();
	TheCar->SetRawSteer(0.f);
	if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
	{
		Move->SetThrottleInput(0.f);
		Move->SetBrakeInput(0.f);
		Move->SetHandbrakeInput(true);
	}
	if (UGTDrivetrainComponent* Train = TheCar->GetDrivetrain())
	{
		// RIVERBED S2: the bog runs start from a dead stop in the mud, so low range with the lock (the terrain test's escape).
		Train->SetLowRange(Run.Bog > 0);
		Train->SetDiffLock(Run.Bog > 0);
	}
	if (UGTConditionComponent* Condition = TheCar->GetCondition())
	{
		Condition->bFlooded = false;
	}
	AGTWaterSheet::CalmAll(World.Get());
	// Reset the run's measurements.
	DriveTime = StuckTime = DtSum = 0.f;
	Ticks = 0;
	TEntry = TFrontEntry = TExit = TFrontExit = T15 = T30 = -1.f;
	VEntry = VExit = V15 = V30 = 0.f;
	VMin = 1.e9f;
	ArcMin = 0.f;
	BudgetAtMin.Reset();
	PeakSlip = 0.f;
	PeakSlipWheel = -1;
	PeakSlipArc = 0.f;
	SlippingTicks = WaterTicks = 0;
	MaxFront = 0.f;
	FloodArc = -1.f;
	VEnd = 0.f;
	EntryBank = FBankStats();
	ExitBank = FBankStats();
	RunWide = FBankStats();
	for (int32 Index = 0; Index < 4; ++Index)
	{
		MaxSinkInWaterCm[Index] = 0.f;
		MaxVisInWaterCm[Index] = 0.f;
	}
	MaxRowSinkCm = 0.f;
	MinRadiusInWaterCm = 1.e9f;
	ProfiledTicks = 0;
	InWaterWheelTicks = 0;
	bHavePrev = false;
	Log(FString::Printf(TEXT("run %s start: at (%.0f, %.0f, %.0f) yaw %.1f, arc %.2f; gt.Water.Hull %d gt.Water.Buoyancy %d; %s"),
		*Run.Name, Location.X, Location.Y, Location.Z, Yaw, Run.Ford == INDEX_NONE ? 0.f : StartArcM, Run.Hull, Run.Buoyancy, Run.Bog > 0 ? TEXT("low range, locked") : TEXT("high range, diffs open")));
}

void FGTFordDiagRunner::Steer(float SpeedMps)
{
	AGTCarPawn* TheCar = Car.Get();
	const FRunDef& Run = Runs[RunIndex];
	const FVector Location = TheCar->GetActorLocation();
	FVector2D Target;
	if (Run.Ford == INDEX_NONE)
	{
		const float Along = static_cast<float>(FVector2D::DotProduct(FVector2D(Location.X, Location.Y) - DryStart, DryDir));
		Target = DryStart + DryDir * (Along + 800.f);
	}
	else
	{
		const FGTRouteHit Hit = GTTerrain::RouteAtCm(Spec, Location.X, Location.Y);
		FVector2D Left;
		Target = RoutePoint(Hit.ArcM + FMath::Clamp(SpeedMps * 0.8f, 4.f, 25.f), Left);
	}
	const FVector ToTarget = (FVector(Target.X, Target.Y, Location.Z) - Location).GetSafeNormal2D();
	const FVector Forward = TheCar->GetActorForwardVector().GetSafeNormal2D();
	const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(FVector::CrossProduct(Forward, ToTarget).Z, FVector::DotProduct(Forward, ToTarget)));
	TheCar->SetRawSteer(FMath::Clamp(AngleDeg / 20.f, -1.f, 1.f));
	if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
	{
		Move->SetThrottleInput(1.f);
		Move->SetBrakeInput(0.f);
		Move->SetHandbrakeInput(false);
	}
}

void FGTFordDiagRunner::LogFordRuts(const TCHAR* When, int32 FordIndex) const
{
	if (!Fords.IsValidIndex(FordIndex) || !World.IsValid())
	{
		return;
	}
	const FFord& Ford = Fords[FordIndex];
	const UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const UGTWaterSubsystem* Water = World->GetSubsystem<UGTWaterSubsystem>();
	FVector2D Left;
	const float MidArc = 0.5f * (Ford.EntryM + Ford.ExitM);
	const FVector2D Mid = RoutePoint(MidArc, Left);
	const AGTMudPatch* Patch = Mud ? Mud->PatchAt(Mid) : nullptr;
	if (!Patch || !Water)
	{
		Log(FString::Printf(TEXT("GTFORDRUT %s %s: no %s at the ford's middle"), *Ford.Name, When, Patch ? TEXT("water subsystem") : TEXT("mud patch")));
		return;
	}
	const FGTMudField& Field = Patch->GetField();
	// Across the ford's middle, the centre line and both wheel lines: what the car reads (the sheet's surface over the
	// landscape contact, the wheels sweep the landscape) and the field there. The ruts never reach the solver's bed.
	FString Points;
	for (const float Off : { -HalfTrackM, 0.f, HalfTrackM })
	{
		const FVector2D P = Mid + Left * (Off * 100.f);
		bool bOk = false;
		const float Z = LandscapeZ(P.X, P.Y, bOk);
		const FGTWaterSample W = Water->Sample(FVector(P.X, P.Y, Z));
		const float Rut = Field.HeightAt(P);
		Points += FString::Printf(TEXT(" [%+.2f m: landscape %.1f, surface %.1f, depth read %.1f cm, field %.1f cm, surface over the field %.1f cm]"),
			Off, Z, W.SurfaceZCm, W.DepthCm, Rut, W.SurfaceZCm - (Z + Rut));
	}
	// The field under the water: every cell a wheel touched whose landscape lies under the sheet's water.
	int32 Touched = 0, Wet = 0, Rutted = 0, Deep5 = 0;
	double RutSum = 0.0;
	float Deepest = 0.f;
	float Highest = 0.f;
	for (int32 Index = 0; Index < Field.Tracks.Num(); ++Index)
	{
		if (Field.Tracks[Index] == 0)
		{
			continue;
		}
		++Touched;
		const FVector2D C = Field.CellCentreCm(Index);
		bool bOk = false;
		const float Z = LandscapeZ(C.X, C.Y, bOk);
		const FGTWaterSample W = Water->Sample(FVector(C.X, C.Y, Z));
		if (W.Kind != EGTWaterKind::Ford || W.DepthCm <= WetCm)
		{
			continue;
		}
		++Wet;
		const float H = Field.CellHeightCm(Index);
		Deepest = FMath::Min(Deepest, H);
		Highest = FMath::Max(Highest, H);
		if (H < -1.f)
		{
			++Rutted;
			RutSum += H;
			Deep5 += H < -5.f ? 1 : 0;
		}
	}
	Log(FString::Printf(TEXT("GTFORDRUT %s %s: patch over section %d (profile %d: MaxSinkage %.1f cm, SinkageRate %.3f m/s), lowered %.0f cm3 in all; touched cells %d, %d under the ford's water: %d cut past 1 cm (mean %.2f cm, %d past 5 cm), deepest %.2f cm, highest %.2f cm; across the middle (arc %.2f):%s"),
		*Ford.Name, When, Patch->SectionIndex, Patch->bHasProfile ? 1 : 0, Patch->ProfileMaxSinkageM * 100.f, Patch->ProfileSinkageRate, Field.LoweredCm3,
		Touched, Wet, Rutted, Rutted > 0 ? static_cast<float>(RutSum / Rutted) : 0.f, Deep5, Deepest, Highest, MidArc, *Points));
}

void FGTFordDiagRunner::TrackBank(FBankStats& Stats, float BankArcM, const FGTWaterDiagSample& S, float WindowM) const
{
	for (int32 Index = 0; Index < S.NumWheels; ++Index)
	{
		const FGTWaterDiagWheel& W = S.Wheels[Index];
		const float Rel = W.ArcM - BankArcM;
		if (FMath::Abs(Rel) > WindowM || !W.bContact)
		{
			continue;
		}
		if (W.LoadN > Stats.MaxLoadN)
		{
			Stats.MaxLoadN = W.LoadN; Stats.LoadWheel = Index; Stats.LoadRelM = Rel;
		}
		if (!bHavePrev || !PrevContact[Index])
		{
			continue;
		}
		const float Step = FMath::Abs(static_cast<float>(W.ContactCm.Z) - PrevCz[Index]);
		if (Step > Stats.MaxContactStepCm)
		{
			Stats.MaxContactStepCm = Step; Stats.StepWheel = Index; Stats.StepRelM = Rel;
		}
		const float RStep = FMath::Abs(W.RadiusCm - PrevR[Index]);
		if (RStep > Stats.MaxRadiusStepCm)
		{
			Stats.MaxRadiusStepCm = RStep; Stats.RadiusWheel = Index; Stats.RadiusRelM = Rel;
		}
		const float LStep = W.LoadN - PrevL[Index];
		if (LStep > Stats.MaxLoadStepN)
		{
			Stats.MaxLoadStepN = LStep; Stats.LoadStepWheel = Index; Stats.LoadStepRelM = Rel;
		}
	}
}

bool FGTFordDiagRunner::TickRun(float DeltaSeconds)
{
	const FRunDef& Run = Runs[RunIndex];
	if (Run.Bog > 0)
	{
		return TickBogRun(DeltaSeconds);
	}
	AGTCarPawn* TheCar = Car.Get();
	const FGTWaterDiagSample S = GTWaterDiag::Measure(*TheCar);
	const float Speed = S.SpeedMps;
	Steer(Speed);
	DriveTime += DeltaSeconds;
	DtSum += DeltaSeconds;
	++Ticks;
	VEnd = Speed;
	if (Run.Ford == INDEX_NONE)
	{
		const float Along = static_cast<float>(FVector2D::DotProduct(FVector2D(S.LocationCm.X, S.LocationCm.Y) - DryStart, DryDir)) * 0.01f;
		SetCvar(TEXT("gt.Water.Diag"), 1.f);
		if (T15 < 0.f && Along >= 15.f) { T15 = DriveTime; V15 = Speed; }
		if (T30 < 0.f && Along >= DryLengthM) { T30 = DriveTime; V30 = Speed; }
		if (T30 >= 0.f)
		{
			EndRun(TEXT("through"));
			return true;
		}
	}
	else
	{
		const FFord& Ford = Fords[Run.Ford];
		const float Arc = S.ArcM;
		const float FrontArc = S.NumWheels >= 2 ? 0.5f * (S.Wheels[0].ArcM + S.Wheels[1].ArcM) : Arc;
		const bool bNearBank = FMath::Abs(Arc - Ford.EntryM) < TickWindowM || FMath::Abs(Arc - Ford.ExitM) < TickWindowM;
		SetCvar(TEXT("gt.Water.Diag"), bNearBank ? 2.f : 1.f);
		if (TFrontEntry < 0.f && FrontArc >= Ford.EntryM) { TFrontEntry = DriveTime; }
		if (TEntry < 0.f && Arc >= Ford.EntryM) { TEntry = DriveTime; VEntry = Speed; }
		if (TFrontExit < 0.f && FrontArc >= Ford.ExitM) { TFrontExit = DriveTime; }
		if (TExit < 0.f && Arc >= Ford.ExitM) { TExit = DriveTime; VExit = Speed; }
		if (Arc >= Ford.EntryM && Arc <= Ford.ExitM)
		{
			++WaterTicks;
			if (Speed < VMin)
			{
				VMin = Speed;
				ArcMin = Arc;
				BudgetAtMin = GTWaterDiag::Format(S);
			}
			for (int32 Index = 0; Index < S.NumWheels; ++Index)
			{
				if (S.Wheels[Index].bContact && FMath::Abs(S.Wheels[Index].SlipRatio) > FMath::Abs(PeakSlip))
				{
					PeakSlip = S.Wheels[Index].SlipRatio; PeakSlipWheel = Index; PeakSlipArc = Arc;
				}
				SlippingTicks += S.Wheels[Index].bChaosSlipping ? 1 : 0;
			}
			// RIVERBED S4: the sinkage in the water, per wheel (raw and visible), the row's (or the profile's) MaxSink
			// and the smallest Chaos radius; how many wheel-ticks the traction had the bed's profile.
			const UGTTractionComponent* Traction = TheCar->GetTraction();
			for (int32 Index = 0; Index < FMath::Min(S.NumWheels, 4); ++Index)
			{
				const FGTWaterDiagWheel& W = S.Wheels[Index];
				if (!W.bContact)
				{
					continue;
				}
				++InWaterWheelTicks;
				MaxSinkInWaterCm[Index] = FMath::Max(MaxSinkInWaterCm[Index], W.SinkM * 100.f);
				MaxVisInWaterCm[Index] = FMath::Max(MaxVisInWaterCm[Index], W.VisSinkM * 100.f);
				MaxRowSinkCm = FMath::Max(MaxRowSinkCm, W.MaxSink * 100.f);
				MinRadiusInWaterCm = FMath::Min(MinRadiusInWaterCm, W.RadiusCm);
				ProfiledTicks += (Traction && Traction->Wheels.IsValidIndex(Index) && Traction->Wheels[Index].bInProfiledPatch) ? 1 : 0;
			}
		}
		MaxFront = FMath::Max(MaxFront, S.FrontDepthM);
		if (S.bFlooded && FloodArc < 0.f)
		{
			FloodArc = Arc;
		}
		TrackBank(EntryBank, Ford.EntryM, S);
		TrackBank(ExitBank, Ford.ExitM, S);
		TrackBank(RunWide, Ford.ExitM, S, 1.e6f);
		if (Arc >= EndArcM)
		{
			EndRun(TEXT("through"));
			return true;
		}
	}
	for (int32 Index = 0; Index < S.NumWheels; ++Index)
	{
		PrevCz[Index] = static_cast<float>(S.Wheels[Index].ContactCm.Z);
		PrevR[Index] = S.Wheels[Index].RadiusCm;
		PrevL[Index] = S.Wheels[Index].LoadN;
		PrevContact[Index] = S.Wheels[Index].bContact;
	}
	bHavePrev = true;
	StuckTime = (DriveTime > 4.f && FMath::Abs(Speed) < 0.2f) ? StuckTime + DeltaSeconds : 0.f;
	if (StuckTime > 6.f)
	{
		EndRun(FString::Printf(TEXT("stuck at arc %.2f"), S.ArcM));
		return true;
	}
	if (DriveTime > RunTimeoutS)
	{
		EndRun(FString::Printf(TEXT("timeout at arc %.2f"), S.ArcM));
		return true;
	}
	return false;
}

void FGTFordDiagRunner::EndRun(const FString& Why)
{
	const FRunDef& Run = Runs[RunIndex];
	SetCvar(TEXT("gt.Water.Diag"), 0.f);
	if (AGTCarPawn* TheCar = Car.Get())
	{
		if (UChaosWheeledVehicleMovementComponent* Move = TheCar->GetChaosMovement())
		{
			Move->SetThrottleInput(0.f);
			Move->SetHandbrakeInput(true);
		}
		TheCar->SetRawSteer(0.f);
	}
	const float MeanDtMs = Ticks > 0 ? DtSum / Ticks * 1000.f : 0.f;
	FString Line;
	if (Run.Bog > 0)
	{
		Line = EndBogRun(Why, MeanDtMs);
	}
	else if (Run.Ford == INDEX_NONE)
	{
		Line = FString::Printf(TEXT("end %s: %s; 15 m at %.2f s %.2f m/s, 30 m at %.2f s %.2f m/s; mean frame %.2f ms"), *Run.Name, *Why, T15, V15, T30, V30, MeanDtMs);
		Digest.Add(FString::Printf(TEXT("%s v15 %.2f v30 %.2f"), *Run.Name, V15, V30));
	}
	else
	{
		auto Bank = [](const FBankStats& B)
		{
			return FString::Printf(TEXT("contact step %.1f cm (w%d at %+.2f m), radius step %.1f cm (w%d at %+.2f m), max load %.0f N (w%d at %+.2f m), load step +%.0f N (w%d at %+.2f m)"),
				B.MaxContactStepCm, B.StepWheel, B.StepRelM, B.MaxRadiusStepCm, B.RadiusWheel, B.RadiusRelM, B.MaxLoadN, B.LoadWheel, B.LoadRelM, B.MaxLoadStepN, B.LoadStepWheel, B.LoadStepRelM);
		};
		const float Crossing = (TEntry >= 0.f && TExit >= 0.f) ? TExit - TEntry : -1.f;
		Line = FString::Printf(TEXT("end %s: %s; entry (centre) at %.2f s %.2f m/s (front wheels at %.2f s); exit at %.2f s %.2f m/s (front %.2f s); waterline to waterline %.2f s; min %.2f m/s at arc %.2f (%+.2f m from the entry); end speed %.2f m/s; peak slip ratio %.3f (w%d at arc %.2f); Chaos slipping %d of %d wheel-ticks in the water; max front depth %.3f m; flooded at arc %.2f; mean frame %.2f ms"),
			*Run.Name, *Why, TEntry, VEntry, TFrontEntry, TExit, VExit, TFrontExit, Crossing, VMin < 1.e8f ? VMin : -1.f, ArcMin,
			ArcMin - Fords[Run.Ford].EntryM, VEnd, PeakSlip, PeakSlipWheel, PeakSlipArc, SlippingTicks, WaterTicks * 4, MaxFront, FloodArc, MeanDtMs);
		Log(Line);
		Log(FString::Printf(TEXT("end %s entry bank (+-%.0f m, per tick): %s"), *Run.Name, BankWindowM, *Bank(EntryBank)));
		Log(FString::Printf(TEXT("end %s exit bank (+-%.0f m, per tick): %s"), *Run.Name, BankWindowM, *Bank(ExitBank)));
		Log(FString::Printf(TEXT("end %s at the slowest point: %s"), *Run.Name, *BudgetAtMin));
		// RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54).
		Log(FString::Printf(TEXT("end %s whole run to arc %.2f (the bed patch's box left at arc %.2f, %+.2f m from the exit waterline; per tick, relative to the exit): %s"),
			*Run.Name, EndArcM, BoxExitArcM, BoxExitArcM >= 0.f ? BoxExitArcM - Fords[Run.Ford].ExitM : 0.f, *Bank(RunWide)));
		Log(FString::Printf(TEXT("end %s sinkage in the water (max per wheel, raw / visible cm): w0 %.1f/%.1f w1 %.1f/%.1f w2 %.1f/%.1f w3 %.1f/%.1f; MaxSink read %.1f cm; smallest Chaos radius %.1f cm; the bed's profile on %d of %d wheel-ticks in contact"),
			*Run.Name, MaxSinkInWaterCm[0], MaxVisInWaterCm[0], MaxSinkInWaterCm[1], MaxVisInWaterCm[1], MaxSinkInWaterCm[2], MaxVisInWaterCm[2], MaxSinkInWaterCm[3], MaxVisInWaterCm[3],
			MaxRowSinkCm, MinRadiusInWaterCm < 1.e8f ? MinRadiusInWaterCm : -1.f, ProfiledTicks, InWaterWheelTicks));
		LogFordRuts(TEXT("after the crossing"), Run.Ford);
		Digest.Add(FString::Printf(TEXT("%s %s vmin %.2f cross %.2f s"), *Run.Name, *Why, VMin < 1.e8f ? VMin : -1.f, Crossing));
		Line.Reset();
	}
	if (!Line.IsEmpty())
	{
		Log(Line);
	}
	SetCvar(TEXT("gt.Water.Hull"), 1.f);
	SetCvar(TEXT("gt.Water.Buoyancy"), 1.f);
	SetCvar(TEXT("gt.Mud.SinkRiseRate"), -1.f);
}

bool FGTFordDiagRunner::Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary)
{
	Elapsed += DeltaSeconds;
	PhaseTime += DeltaSeconds;
	bOutPass = true;
	auto Finish = [&](const FString& Note)
	{
		SetCvar(TEXT("gt.Water.Diag"), 0.f);
		SetCvar(TEXT("gt.Water.Hull"), 1.f);
		SetCvar(TEXT("gt.Water.Buoyancy"), 1.f);
		OutSummary = FString::Printf(TEXT("ford diagnostic (off the gates)%s: %s"), *Note, *FString::Join(Digest, TEXT("; ")));
		return true;
	};
	if (!World.IsValid())
	{
		return Finish(TEXT(", no world"));
	}
	if (Elapsed > 900.f)
	{
		return Finish(FString::Printf(TEXT(", timed out in phase %d run %d"), Phase, RunIndex));
	}
	switch (Phase)
	{
	case FindCar:
	{
		PC = Cast<AGTPlayerController>(UGameplayStatics::GetPlayerController(World.Get(), 0));
		Car = PC.IsValid() ? (PC->GetCar() ? PC->GetCar() : Cast<AGTCarPawn>(PC->GetPawn())) : nullptr;
		const UGTTerrainSpecAsset* Asset = GTProving::FindSpecAsset(World.Get());
		if (!Car.IsValid() || !Asset)
		{
			if (PhaseTime > 10.f)
			{
				return Finish(TEXT(", no car or no spec asset"));
			}
			return false;
		}
		Spec = Asset->Spec;
		if (!PC->IsDriving())
		{
			const bool bEntered = PC->EnterCar();
			Log(FString::Printf(TEXT("the player was on foot; EnterCar %s"), bEntered ? TEXT("ok") : TEXT("failed")));
		}
		SetCvar(TEXT("t.MaxFPS"), 60.f);
		for (const TCHAR* Name : { TEXT("gt.Water.Hull"), TEXT("gt.Water.Buoyancy"), TEXT("gt.Water.Lids"), TEXT("gt.Water.RutWater"), TEXT("gt.Water.FlowScale"), TEXT("gt.Water.Wind") })
		{
			const IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name);
			Log(FString::Printf(TEXT("cvar %s = %s"), Name, Var ? *Var->GetString() : TEXT("(none)")));
		}
		Phase = PadSettle;
		PhaseTime = 0.f;
		return false;
	}
	case PadSettle:
	{
		if (PhaseTime < 3.f)
		{
			return false;
		}
		// The wheel geometry from the contacts at rest, in the car's frame.
		const UGTTractionComponent* Traction = Car->GetTraction();
		const FTransform Frame = Car->GetMesh()->GetComponentTransform();
		float Lat = 0.f, Lon = 0.f;
		int32 N = 0;
		for (const FGTWheelTraction& Wheel : Traction->Wheels)
		{
			if (Wheel.bInContact)
			{
				const FVector Local = Frame.InverseTransformPosition(Wheel.ContactPoint);
				Lat += FMath::Abs(static_cast<float>(Local.Y));
				Lon += FMath::Abs(static_cast<float>(Local.X));
				++N;
			}
		}
		if (N == 4)
		{
			HalfTrackM = Lat / N * 0.01f;
			HalfBaseM = Lon / N * 0.01f;
		}
		const UChaosWheeledVehicleMovementComponent* Move = Car->GetChaosMovement();
		Log(FString::Printf(TEXT("the car on the pad: mass %.0f kg, %d wheels in contact, location %s"), Move ? Move->Mass : 0.f, N, *Car->GetActorLocation().ToCompactString()));
		Phase = DoSurvey;
		PhaseTime = 0.f;
		return false;
	}
	case DoSurvey:
	{
		Survey();
		// RIVERBED S2 (2026-09-23, VEHICLE_BUILD_SYSTEM 52): no Mud or Bog on the landscape outside the mud patches' boxes.
		Log(GTProving::DescribeMudSurvey(GTProving::SurveyMud(World.Get(), Spec, 100.f, Car.Get())));
		for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
		{
			if (Spec.Sections[Index].Kind == EGTRouteSectionKind::Mud)
			{
				BogSection = Index;
				break;
			}
		}
		Runs.Add({ TEXT("dry_pad"), INDEX_NONE, 1, 1 });
		const TCHAR* Variants[3][3] = { { TEXT("base"), TEXT("1"), TEXT("1") }, { TEXT("hull0"), TEXT("0"), TEXT("1") }, { TEXT("buoy0"), TEXT("1"), TEXT("0") } };
		for (int32 F = 0; F < Fords.Num(); ++F)
		{
			if (!Fords[F].bValid)
			{
				continue;
			}
			for (int32 V = 0; V < 3; ++V)
			{
				Runs.Add({ Fords[F].Name + TEXT("_") + Variants[V][0], F, FCString::Atoi(Variants[V][1]), FCString::Atoi(Variants[V][2]) });
			}
		}
		if (Fords.Num() > 0 && Fords[0].bValid)
		{
			Runs.Add({ Fords[0].Name + TEXT("_base_repeat"), 0, 1, 1 });
		}
		if (BogSection != INDEX_NONE)
		{
			Runs.Add({ TEXT("bog_right"), INDEX_NONE, 1, 1, 1 });
			Runs.Add({ TEXT("bog_right_noramp"), INDEX_NONE, 1, 1, 1, 1000.f });
			Runs.Add({ TEXT("bog_left"), INDEX_NONE, 1, 1, 3 });
			Runs.Add({ TEXT("bog_end"), INDEX_NONE, 1, 1, 2 });
		}
		Log(FString::Printf(TEXT("%d runs; gt.Water.Diag carries the car's state (GTWATERDIAG); no cvar exists for WaterDragPerMetre, so that variant is not run"), Runs.Num()));
		RunIndex = 0;
		Phase = RunSetup;
		PhaseTime = 0.f;
		return false;
	}
	case RunSetup:
	{
		if (RunIndex >= Runs.Num())
		{
			Phase = AllDone;
			return false;
		}
		BeginRun();
		Phase = RunSettle;
		PhaseTime = 0.f;
		return false;
	}
	case RunSettle:
	{
		if (PhaseTime < RunSettleS)
		{
			return false;
		}
		AGTWaterSheet::CalmAll(World.Get());
		// A car teleported out of deep water re-floods on its first tick there (the wheels' contacts are last frame's),
		// and the drain takes FloodDrainSeconds: cleared again at the go, on dry ground.
		UGTConditionComponent* Condition = Car->GetCondition();
		const bool bWasFlooded = Condition && Condition->bFlooded;
		if (Condition)
		{
			Condition->bFlooded = false;
		}
		Log(FString::Printf(TEXT("run %s go at t=%.3f (flooded at the go: %d, cleared)"), *Runs[RunIndex].Name, World->GetTimeSeconds(), bWasFlooded ? 1 : 0));
		if (Runs[RunIndex].Ford != INDEX_NONE && Runs[RunIndex].Bog == 0)
		{
			LogFordRuts(TEXT("at the go (the water calmed)"), Runs[RunIndex].Ford);
		}
		Phase = RunDrive;
		PhaseTime = 0.f;
		return false;
	}
	case RunDrive:
	{
		if (TickRun(DeltaSeconds))
		{
			++RunIndex;
			Phase = RunSetup;
			PhaseTime = 0.f;
		}
		return false;
	}
	default:
		return Finish(TEXT(""));
	}
}
