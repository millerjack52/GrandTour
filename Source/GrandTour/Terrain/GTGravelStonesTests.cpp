// Deformable gravel DG1 item 5 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): GrandTour.Gravel.Stones, -NullRHI, CPU only. L_GravelDeform's
// two gravel patches (DA_GravelDeform: Firm 30-55 m, Loose 80-110 m) built as play builds them (UGTMudSubsystem::BuildPatches)
// over a flat static ground box with its top at Z 0, with the plan's numbers on their profiles (stones 12 / 30 per m^2, the
// windrow lumps), so the test does not depend on the setup having run. Each row prints a "Gravel: " line.
#include "Terrain/GTGravelStones.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Terrain/GTMudPatch.h"
#include "Terrain/GTMudSubsystem.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Components/BoxComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTGravelStonesTest, "GrandTour.Gravel.Stones",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

namespace
{
	float GravelCV(const TArray<float>& Values)
	{
		if (Values.Num() < 2)
		{
			return 0.f;
		}
		double Sum = 0.0;
		for (const float V : Values)
		{
			Sum += V;
		}
		const double Mean = Sum / Values.Num();
		double Sq = 0.0;
		for (const float V : Values)
		{
			Sq += (V - Mean) * (V - Mean);
		}
		return Mean > 0.0 ? static_cast<float>(FMath::Sqrt(Sq / Values.Num()) / Mean) : 0.f;
	}

	double GravelSegmentDistance(const FVector2D& P, const FVector2D& A, const FVector2D& B)
	{
		const FVector2D AB = B - A;
		const double L2 = AB.SizeSquared();
		const double T = L2 > 1e-6 ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / L2, 0.0, 1.0) : 0.0;
		return FVector2D::Distance(P, A + AB * T);
	}

	uint32 StonesCrc(const UGTGravelStones& Stones)
	{
		uint32 Crc = 0;
		for (const UGTGravelStones::FStone& Stone : Stones.GetStones())
		{
			Crc = FCrc::MemCrc32(&Stone.XY, sizeof(Stone.XY), Crc);
			Crc = FCrc::MemCrc32(&Stone.SizeCm, sizeof(Stone.SizeCm), Crc);
			Crc = FCrc::MemCrc32(&Stone.Mesh, sizeof(Stone.Mesh), Crc);
		}
		return Crc;
	}
}

bool FGTGravelStonesTest::RunTest(const FString& Parameters)
{
	IConsoleVariable* StoneSwitch = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Gravel.Stones"));
	IConsoleVariable* DensitySwitch = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Gravel.StoneDensity"));
	if (!TestNotNull(TEXT("Gravel: gt.Gravel.Stones exists"), StoneSwitch) || !TestNotNull(TEXT("Gravel: gt.Gravel.StoneDensity exists"), DensitySwitch))
	{
		return false;
	}
	const int32 StonesWas = StoneSwitch->GetInt();
	const float DensityWas = DensitySwitch->GetFloat();
	StoneSwitch->Set(1, ECVF_SetByConsole);
	DensitySwitch->Set(1.f, ECVF_SetByConsole);

	// The strip's own spec (L_GravelDeform), its two gravel sections with the plan's numbers.
	const UGTTerrainSpecAsset* StripSpec = LoadObject<UGTTerrainSpecAsset>(nullptr, TEXT("/Game/GrandTour/ArtTests/DeformableGravel/DA_GravelDeform.DA_GravelDeform"));
	if (!TestNotNull(TEXT("Gravel: DA_GravelDeform (Art/deformable_gravel.ps1 -Mode Setup)"), StripSpec) || !TestEqual(TEXT("Gravel: two sections"), StripSpec->Spec.Sections.Num(), 2))
	{
		StoneSwitch->Set(StonesWas, ECVF_SetByConsole);
		DensitySwitch->Set(DensityWas, ECVF_SetByConsole);
		return false;
	}
	FGTTerrainSpec Spec = StripSpec->Spec;
	const float Target[2] = { 12.f, 30.f };   // Firm, Loose
	for (int32 Index = 0; Index < 2; ++Index)
	{
		FGTDeformProfile& Profile = Spec.Sections[Index].Deform;
		Profile.Medium = EGTDeformMedium::Gravel;
		Profile.GravelStonesPerM2 = Target[Index];
		Profile.LumpShare = 0.3f;
		Profile.LumpMaxCm = 2.5f;
		Profile.LumpRadiusCells = 1.5f;
		Profile.LumpVarietyRadiusJitter = 0.33f;
	}

	UWorld::InitializationValues Values;
	Values.CreatePhysicsScene(true).ShouldSimulatePhysics(false).EnableTraceCollision(true).CreateNavigation(false).CreateAISystem(false).AllowAudioPlayback(false);
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("GTGravelStonesTest"), nullptr, true, ERHIFeatureLevel::Num, &Values);
	if (!TestNotNull(TEXT("Gravel: a Game world"), World))
	{
		StoneSwitch->Set(StonesWas, ECVF_SetByConsole);
		DensitySwitch->Set(DensityWas, ECVF_SetByConsole);
		return false;
	}
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	auto Restore = [&]()
	{
		StoneSwitch->Set(StonesWas, ECVF_SetByConsole);
		DensitySwitch->Set(DensityWas, ECVF_SetByConsole);
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	};
	AActor* Ground = World->SpawnActor<AActor>();
	UBoxComponent* GroundBox = NewObject<UBoxComponent>(Ground, TEXT("Ground"));
	GroundBox->SetMobility(EComponentMobility::Static);
	GroundBox->SetBoxExtent(FVector(10000.0, 3000.0, 500.0), false);
	GroundBox->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	GroundBox->SetWorldLocation(FVector(7000.0, 0.0, -500.0));
	Ground->SetRootComponent(GroundBox);
	GroundBox->RegisterComponent();
	UGTMudSubsystem* Mud = World->GetSubsystem<UGTMudSubsystem>();
	const int32 Count = Mud ? Mud->BuildPatches(Spec) : 0;
	TestTrue(TEXT("Gravel: two patches"), Count == 2);
	AGTMudPatch* Patches[2] = { nullptr, nullptr };
	for (TActorIterator<AGTMudPatch> It(World); It; ++It)
	{
		if (It->SectionIndex >= 0 && It->SectionIndex < 2)
		{
			Patches[It->SectionIndex] = *It;
		}
	}
	const TCHAR* Names[2] = { TEXT("Firm"), TEXT("Loose") };
	for (int32 Index = 0; Index < 2; ++Index)
	{
		if (!TestNotNull(FString::Printf(TEXT("Gravel: %s - a patch"), Names[Index]), Patches[Index])
			|| !TestNotNull(FString::Printf(TEXT("Gravel: %s - stones (SM_GR_Stone1..4 imported)"), Names[Index]), Patches[Index]->GetGravelStones()))
		{
			Restore();
			return false;
		}
	}

	// ---- 1. placement: deterministic, and the density per section within 15 % of the target (over the road's interior) ----
	for (int32 Index = 0; Index < 2; ++Index)
	{
		AGTMudPatch* Patch = Patches[Index];
		UGTGravelStones* Stones = Patch->GetGravelStones();
		const uint32 CrcA = StonesCrc(*Stones);
		const int32 NumA = Stones->NumStones();
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		const bool bSame = CrcA == StonesCrc(*Stones) && NumA == Stones->NumStones();
		TestTrue(FString::Printf(TEXT("Gravel: %s - the placement is deterministic"), Names[Index]), bSame);
		// DG1b: the section's own span (its route line, where the placement renormalises), the road's full width.
		const TArray<FVector2D>& Route = Patch->GetRouteLine();
		const FVector2D A = Route[0];
		const FVector2D B = Route.Last();
		const FVector2D Dir = (B - A).GetSafeNormal();
		const double Span = FVector2D::Distance(A, B);
		int32 InInterior = 0;
		float SizeSum = 0.f;
		int32 Small = 0;
		for (const UGTGravelStones::FStone& Stone : Stones->GetStones())
		{
			const double Along = FVector2D::DotProduct(Stone.XY - A, Dir);
			const double Across = FMath::Abs(FVector2D::DotProduct(Stone.XY - A, FVector2D(-Dir.Y, Dir.X)));
			InInterior += (Along >= 0.0 && Along <= Span && Across <= Patch->RoadHalfWidthCm) ? 1 : 0;
			SizeSum += Stone.SizeCm;
			Small += Stone.SizeCm < 3.f ? 1 : 0;
		}
		const double AreaM2 = Span * 2.0 * Patch->RoadHalfWidthCm / 10000.0;
		const float Density = static_cast<float>(InInterior / FMath::Max(1.0, AreaM2));
		TestTrue(FString::Printf(TEXT("Gravel: %s - %.2f stones per m^2 over the section, the target %.0f (within 15 %%)"), Names[Index], Density, Target[Index]),
			FMath::Abs(Density / Target[Index] - 1.f) <= 0.15f);
		TestEqual(FString::Printf(TEXT("Gravel: %s - one instance per stone"), Names[Index]), Stones->NumInstances(), Stones->NumStones());
		// DG1b: the clustering - the CV of the stones' counts over 1 m^2 quadrats of the interior, at least 0.6 (and DG1's one octave,
		// x0.3-1.8, unsharpened, rebuilt for the record).
		auto QuadratCv = [&]()
		{
			const int32 NA = FMath::Max(1, FMath::FloorToInt(static_cast<float>(Span) / 100.f));
			const int32 NC = FMath::Max(1, FMath::FloorToInt(2.f * Patch->RoadHalfWidthCm / 100.f));
			TArray<float> Counts;
			Counts.Init(0.f, NA * NC);
			for (const UGTGravelStones::FStone& Stone : Stones->GetStones())
			{
				const double Along = FVector2D::DotProduct(Stone.XY - A, Dir);
				const double Across = FVector2D::DotProduct(Stone.XY - A, FVector2D(-Dir.Y, Dir.X)) + Patch->RoadHalfWidthCm;
				const int32 IA = FMath::FloorToInt(static_cast<float>(Along) / 100.f);
				const int32 IC = FMath::FloorToInt(static_cast<float>(Across) / 100.f);
				if (Along >= 0.0 && IA < NA && Across >= 0.0 && IC < NC)
				{
					Counts[IA * NC + IC] += 1.f;
				}
			}
			return GravelCV(Counts);
		};
		const float CvAfter = QuadratCv();
		const float Was[5] = { Stones->ClusterOctave2, Stones->ClusterSharpen, Stones->ClusterMin, Stones->ClusterMax, 0.f };
		Stones->ClusterOctave2 = 0.f;
		Stones->ClusterSharpen = 0.f;
		Stones->ClusterMin = 0.3f;
		Stones->ClusterMax = 1.8f;
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		const float CvBefore = QuadratCv();
		Stones->ClusterOctave2 = Was[0];
		Stones->ClusterSharpen = Was[1];
		Stones->ClusterMin = Was[2];
		Stones->ClusterMax = Was[3];
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		TestTrue(FString::Printf(TEXT("Gravel: %s - 1 m^2 quadrat count cv %.3f (at least 0.6; DG1's clustering %.3f)"), Names[Index], CvAfter, CvBefore), CvAfter >= 0.6f);
		TestTrue(FString::Printf(TEXT("Gravel: %s - the same stones after the comparison"), Names[Index]), CrcA == StonesCrc(*Stones));
		AddInfo(FString::Printf(TEXT("Gravel: clustering %s - 1 m^2 quadrats over the section: count cv %.3f (DG1: one 150 cm octave x0.3-1.8, %.3f)"), Names[Index], CvAfter, CvBefore));
		AddInfo(FString::Printf(TEXT("Gravel: placement %s - %d stones (target %d over %.1f m^2), deterministic %d, the section %d over %.1f m^2 = %.2f per m^2 (target %.0f), sizes mean %.2f cm, under 3 cm %.0f %%; %s"),
			Names[Index], Stones->NumStones(), Stones->GetTargetCount(), Stones->GetPlacedAreaM2(), bSame ? 1 : 0, InInterior, AreaM2, Density, Target[Index],
			SizeSum / FMath::Max(1, Stones->NumStones()), 100.f * Small / FMath::Max(1, Stones->NumStones()), *Patch->DescribeGravelStones()));
	}

	// ---- 2. a CPU stroke on the Loose section: the capsule empties, the band beside it gains the moved count, no row ----------
	{
		AGTMudPatch* Patch = Patches[1];
		UGTGravelStones* Stones = Patch->GetGravelStones();
		const FVector2D From(8800.0, -20.0);
		const FVector2D To(9400.0, -20.0);
		const float Half = 12.5f;
		auto CountIn = [&](float Lo, float Hi)
		{
			int32 N = 0;
			for (const UGTGravelStones::FStone& Stone : Stones->GetStones())
			{
				const double D = GravelSegmentDistance(Stone.XY, From, To);
				N += (D >= Lo && D <= Hi) ? 1 : 0;
			}
			return N;
		};
		const int32 InsideBefore = CountIn(0.f, Half - 0.001f);
		const int32 BandBefore = CountIn(1.5f * Half, 2.f * Half);
		const UGTGravelStones::FPushResult Push = Stones->PushUnderWheel(From, To, Half, FVector2D(1.0, 0.0), 0.f);
		const int32 InsideAfter = CountIn(0.f, Half - 0.001f);
		const int32 BandAfter = CountIn(1.5f * Half, 2.f * Half);
		TestTrue(FString::Printf(TEXT("Gravel: stroke - %d stones inside before"), InsideBefore), InsideBefore >= 10);
		TestTrue(FString::Printf(TEXT("Gravel: stroke - %d of %d stay inside (at most 15 %%)"), InsideAfter, InsideBefore), InsideAfter <= 0.15f * InsideBefore);
		TestEqual(TEXT("Gravel: stroke - the band 0.5-1.0 half-widths outside gains the moved count exactly"), BandAfter - BandBefore, Push.Pushed);
		TArray<float> Along;
		for (const int32 Index : Push.Moved)
		{
			Along.Add(static_cast<float>(Stones->GetStones()[Index].XY.X - From.X));
		}
		Along.Sort();
		TArray<float> Gaps;
		for (int32 K = 1; K < Along.Num(); ++K)
		{
			Gaps.Add(Along[K] - Along[K - 1]);
		}
		const float Cv = GravelCV(Gaps);
		TestTrue(FString::Printf(TEXT("Gravel: stroke - the moved stones' spacing along the stroke has cv %.3f (at least 0.4: no row)"), Cv), Cv >= 0.4f);
		AddInfo(FString::Printf(TEXT("Gravel: stroke - 6 m x 25 cm at slip 0: inside %d -> %d (%.1f %%), pushed %d, pressed %d, flicked %d; band %d -> %d (+%d); along-stroke spacing cv %.3f"),
			InsideBefore, InsideAfter, 100.f * InsideAfter / FMath::Max(1, InsideBefore), Push.Pushed, Push.Pressed, Push.Flicked, BandBefore, BandAfter, BandAfter - BandBefore, Cv));
	}

	// ---- 3. slip 0.5: the flicked share is the slip, landing 0.5-3 m back ------------------------------------------------------
	{
		AGTMudPatch* Patch = Patches[1];
		UGTGravelStones* Stones = Patch->GetGravelStones();
		const FVector2D From(9500.0, 15.0);
		const FVector2D To(10500.0, 15.0);
		const UGTGravelStones::FPushResult Push = Stones->PushUnderWheel(From, To, 15.f, FVector2D(1.0, 0.0), 0.5f);
		const float Share = static_cast<float>(Push.Flicked) / FMath::Max(1, Push.Inside);
		TestTrue(FString::Printf(TEXT("Gravel: slip 0.5 - %d stones inside"), Push.Inside), Push.Inside >= 30);
		TestTrue(FString::Printf(TEXT("Gravel: slip 0.5 - flicked share %.3f (0.5 +- 0.05)"), Share), FMath::Abs(Share - 0.5f) <= 0.05f);
		float Lo = 1.0e9f;
		float Hi = 0.f;
		int32 Back = 0;
		for (const int32 Index : Push.Thrown)
		{
			const FVector2D* Start = Stones->GetFlickStarts().Find(Index);
			if (Start)
			{
				const FVector2D Way = Stones->GetStones()[Index].XY - *Start;
				const float D = static_cast<float>(Way.Size());
				Lo = FMath::Min(Lo, D);
				Hi = FMath::Max(Hi, D);
				Back += Way.X < 0.0 ? 1 : 0;
			}
		}
		TestTrue(FString::Printf(TEXT("Gravel: slip 0.5 - landing distances %.1f-%.1f cm (in 50-300)"), Lo, Hi), Push.Flicked > 0 && Lo >= 50.f - 0.01f && Hi <= 300.f + 0.01f);
		TestEqual(TEXT("Gravel: slip 0.5 - every flicked stone lands behind the wheel"), Back, Push.Flicked);
		AddInfo(FString::Printf(TEXT("Gravel: slip 0.5 - 10 m x 30 cm: inside %d, flicked %d (share %.3f), pushed %d, pressed %d; landing %.1f-%.1f cm back"),
			Push.Inside, Push.Flicked, Share, Push.Pushed, Push.Pressed, Lo, Hi));
	}

	// ---- 4. the windrow heaps (DG1 item 4): the lumps' peaks along a Loose stroke, spacing cv at least 0.4 ---------------------
	{
		AGTMudPatch* Patch = Patches[1];
		FGTMudField& Field = Patch->GetField();
		for (int32 I = 0; I < 600; ++I)
		{
			Field.StampWheel(FVector2D(8500.0 + I * 5.0, -150.0), FVector2D(8505.0 + I * 5.0, -150.0), 25.f, 5.f, FVector2D(1.0, 0.0), I * 5.f);
		}
		TArray<FVector2D> Peaks[2];
		TArray<float> Heights;
		for (int32 Y = 2; Y < Field.SizeY - 2; ++Y)
		{
			for (int32 X = 2; X < Field.SizeX - 2; ++X)
			{
				const int32 Index = Y * Field.SizeX + X;
				const float L = Field.LumpCm.IsValidIndex(Index) ? Field.LumpCm[Index] : 0.f;
				const FVector2D P = Field.CellCentreCm(Index);
				if (L < 0.1f || P.X < 8700.0 || P.X > 11300.0 || FMath::Abs(P.Y + 150.0) > 80.0)
				{
					continue;
				}
				bool bPeak = true;
				for (int32 DY = -1; bPeak && DY <= 1; ++DY)
				{
					for (int32 DX = -1; DX <= 1; ++DX)
					{
						const int32 N = (Y + DY) * Field.SizeX + X + DX;
						if (N != Index && (Field.LumpCm[N] > L || (Field.LumpCm[N] == L && N < Index)))
						{
							bPeak = false;
							break;
						}
					}
				}
				if (bPeak)
				{
					Peaks[P.Y > -150.0 ? 0 : 1].Add(P);
					Heights.Add(L);
				}
			}
		}
		TArray<float> Spacing;
		for (int32 Side = 0; Side < 2; ++Side)
		{
			for (int32 I = 0; I < Peaks[Side].Num(); ++I)
			{
				double Best = TNumericLimits<double>::Max();
				for (int32 J = 0; J < Peaks[Side].Num(); ++J)
				{
					if (J != I)
					{
						Best = FMath::Min(Best, FVector2D::Distance(Peaks[Side][I], Peaks[Side][J]));
					}
				}
				if (Peaks[Side].Num() > 1)
				{
					Spacing.Add(static_cast<float>(Best));
				}
			}
		}
		const float Cv = GravelCV(Spacing);
		float MaxLump = 0.f;
		for (const float L : Heights)
		{
			MaxLump = FMath::Max(MaxLump, L);
		}
		TestTrue(FString::Printf(TEXT("Gravel: heaps - %d windrow peaks"), Peaks[0].Num() + Peaks[1].Num()), Peaks[0].Num() + Peaks[1].Num() >= 8);
		TestTrue(FString::Printf(TEXT("Gravel: heaps - peak spacing cv %.3f (at least 0.4)"), Cv), Cv >= 0.4f);
		TestTrue(FString::Printf(TEXT("Gravel: heaps - the highest lump %.2f cm (the dome cap 2.5)"), MaxLump), MaxLump <= 2.5f + 0.01f);
		AddInfo(FString::Printf(TEXT("Gravel: heaps - 30 m Loose stroke, 5 cm: peaks %d / %d, nearest-neighbour spacing cv %.3f, heights cv %.3f, highest %.2f cm; sites built %d, absent %d"),
			Peaks[0].Num(), Peaks[1].Num(), Cv, GravelCV(Heights), MaxLump, Field.LumpSitesBuilt, Field.LumpSitesAbsent));
	}

	// ---- 5. gt.Gravel.Stones 0: no instances; back on, the same stones ----------------------------------------------------------
	{
		AGTMudPatch* Patch = Patches[0];
		UGTGravelStones* Stones = Patch->GetGravelStones();
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		const uint32 CrcOn = StonesCrc(*Stones);
		StoneSwitch->Set(0, ECVF_SetByConsole);
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		const int32 Off = Stones->NumInstances() + Stones->NumStones();
		TestEqual(TEXT("Gravel: gt.Gravel.Stones 0 - no instances"), Off, 0);
		StoneSwitch->Set(1, ECVF_SetByConsole);
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		TestTrue(TEXT("Gravel: gt.Gravel.Stones 1 again - the same stones"), StonesCrc(*Stones) == CrcOn && Stones->NumInstances() > 0);
		DensitySwitch->Set(0.5f, ECVF_SetByConsole);
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		const int32 Half = Stones->NumStones();
		DensitySwitch->Set(1.f, ECVF_SetByConsole);
		Stones->Build(*Patch, Patch->SectionIndex, Patch->GravelStonesPerM2, Patch->RoadHalfWidthCm);
		TestTrue(FString::Printf(TEXT("Gravel: gt.Gravel.StoneDensity 0.5 - %d stones vs %d"), Half, Stones->NumStones()), FMath::Abs(Half - 0.5f * Stones->NumStones()) <= 2.f);
		AddInfo(FString::Printf(TEXT("Gravel: switches - gt.Gravel.Stones 0 leaves %d instances, 1 restores the same %d; gt.Gravel.StoneDensity 0.5 places %d of %d"), Off, Stones->NumStones(), Half, Stones->NumStones()));
	}
	Restore();
	return true;
}
#endif
