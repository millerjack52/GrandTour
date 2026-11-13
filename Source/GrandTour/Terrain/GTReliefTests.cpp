// Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md GR1 items 1-3 and 5): GrandTour.Relief.Strips, CPU only (-NullRHI). The three
// strips' specs as their setup scripts leave them (DA_MudVariants, DA_GravelDeform, DA_MudDrive): the route's grade and
// cross-slope, the hummock field's gates, determinism, and the grass variation on a placement grid. "Relief: " lines.
#include "Terrain/GTReliefLibrary.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Terrain/GTTerrainSpecAsset.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTReliefStripsTest, "GrandTour.Relief.Strips",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTReliefStripsTest::RunTest(const FString& Parameters)
{
	struct FStrip
	{
		const TCHAR* Name;
		const TCHAR* Path;
	};
	const FStrip Strips[3] = {
		{ TEXT("L_MudVariants"), TEXT("/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants.DA_MudVariants") },
		{ TEXT("L_GravelDeform"), TEXT("/Game/GrandTour/ArtTests/DeformableGravel/DA_GravelDeform.DA_GravelDeform") },
		{ TEXT("L_MudDrive"), TEXT("/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive.DA_MudDrive") } };
	for (const FStrip& Strip : Strips)
	{
		const UGTTerrainSpecAsset* Asset = LoadObject<UGTTerrainSpecAsset>(nullptr, Strip.Path);
		if (!TestNotNull(FString::Printf(TEXT("Relief: %s's spec"), Strip.Name), Asset))
		{
			continue;
		}
		const FGTTerrainSpec& Spec = Asset->Spec;
		const FGTReliefStats S = GTRelief::Measure(Spec);
		AddInfo(FString::Printf(TEXT("Relief: %s - land %.2f m at %.0f m, %d octaves; relief %d octaves at %.0f m, scrub %.2f m, mud %.2f m; hummocks %.1f per 100 m2"),
			Strip.Name, Spec.BaseAmplitudeM, Spec.BaseWavelengthM, Spec.Octaves, Spec.RoughnessOctaves, Spec.RoughnessWavelengthM, Spec.ScrubRoughnessM, Spec.MudRoughnessM,
			Spec.Hummocks.Density));
		// The strip's ground before GR1 (its setup's land and the stage-2 relief, no hummocks) for the comparison.
		FGTTerrainSpec Before = Spec;
		const bool bGravel = FString(Strip.Name) == TEXT("L_GravelDeform");
		Before.BaseAmplitudeM = bGravel ? 0.4f : 1.2f;
		Before.BaseWavelengthM = bGravel ? 100.f : 90.f;
		Before.Octaves = 2;
		Before.Persistence = 0.5f;
		Before.RoughnessOctaves = 2;
		Before.RoughnessWavelengthM = 4.f;
		Before.ScrubRoughnessM = 0.25f;
		Before.MudRoughnessM = 0.12f;
		Before.Hummocks = FGTHummockField();
		const FGTReliefStats B = GTRelief::Measure(Before);
		AddInfo(FString::Printf(TEXT("Relief: %s - route grade p50 %.2f p95 %.2f max %.2f %%, cross-slope p50 %.2f p95 %.2f max %.2f %% (%d samples); away from fords p95 grade %.2f cross %.2f %%; ")
			TEXT("before GR1 p95 grade %.2f cross %.2f %% (away from fords %.2f / %.2f)"),
			Strip.Name, S.GradeP50, S.GradeP95, S.GradeMax, S.CrossP50, S.CrossP95, S.CrossMax, S.RouteSamples, S.GradeP95OffFord, S.CrossP95OffFord,
			B.GradeP95, B.CrossP95, B.GradeP95OffFord, B.CrossP95OffFord));
		if (S.GradeP95OffFord > 10.f || S.CrossP95 > 6.f)
		{
			// The plan's remedy (lower the amplitude only if these fail): the grade at lower land amplitudes, for the setup to pick.
			FString Sweep;
			for (float Amplitude = Spec.BaseAmplitudeM - 0.25f; Amplitude >= 1.f; Amplitude -= 0.25f)
			{
				FGTTerrainSpec Lower = Spec;
				Lower.BaseAmplitudeM = Amplitude;
				const FGTReliefStats L = GTRelief::Measure(Lower);
				Sweep += FString::Printf(TEXT(" %.2f m: %.2f / %.2f;"), Amplitude, L.GradeP95OffFord, L.CrossP95);
			}
			AddInfo(FString::Printf(TEXT("Relief: %s - the amplitude sweep (grade p95 away from fords / cross-slope p95, %%):%s"), Strip.Name, *Sweep));
		}
		// The gate away from the fords: a ford's own drop into its channel (FordGradePercent 25) is the section's, there before GR1.
		TestTrue(FString::Printf(TEXT("Relief: %s - the route's grade p95 at most 10 %% away from fords (%.2f; whole route %.2f)"), Strip.Name, S.GradeP95OffFord, S.GradeP95), S.GradeP95OffFord <= 10.f);
		TestTrue(FString::Printf(TEXT("Relief: %s - the route's cross-slope p95 at most 6 %% (%.2f)"), Strip.Name, S.CrossP95), S.CrossP95 <= 6.f);
		if (Spec.Hummocks.Density <= 0.f)
		{
			AddInfo(FString::Printf(TEXT("Relief: %s - no hummock field"), Strip.Name));
			continue;
		}
		FString Bins;
		for (int32 K = 0; K < S.PairBins.Num() && K < 16; ++K)
		{
			Bins += FString::Printf(TEXT("%s%.2f"), K ? TEXT(" ") : TEXT(""), S.PairBins[K]);
		}
		AddInfo(FString::Printf(TEXT("Relief: %s - hummocks %d in the grid (%.2f per 100 m2), %d stamped; nearest %.2f m, CV %.3f (stamped %.3f); g(r) peak beyond it %.3f at %.2f m; g per 0.5 m to 8 m: %s; ")
			TEXT("the field's steepest %.1f deg (0.25 m), its tallest %.3f m; the ground on hummocks at 1 m: max %.1f deg, p99 %.1f deg"),
			Strip.Name, S.HummocksRaw, S.Density, S.HummocksStamped, S.NearestMeanM, S.NearestCV, S.StampedNearestCV, S.PairPeak, S.PairPeakAtM, *Bins,
			S.FieldSlopeMaxDeg, S.HummockMaxM, S.GroundSlopeMaxDeg, S.GroundSlopeP99Deg));
		TestTrue(FString::Printf(TEXT("Relief: %s - the hummocks' nearest-neighbour CV at least 0.4 (%.3f)"), Strip.Name, S.NearestCV), S.NearestCV >= 0.4f);
		TestTrue(FString::Printf(TEXT("Relief: %s - no pair-correlation peak above 1.3 beyond the first neighbour (%.3f at %.2f m)"), Strip.Name, S.PairPeak, S.PairPeakAtM), S.PairPeak <= 1.3f);
		TestTrue(FString::Printf(TEXT("Relief: %s - the hummock field's steepest slope at most 35 deg (%.1f)"), Strip.Name, S.FieldSlopeMaxDeg), S.FieldSlopeMaxDeg <= 35.f);
		TestTrue(FString::Printf(TEXT("Relief: %s - the hummocks stand %.2f-%.2f m at most (%.3f)"), Strip.Name, Spec.Hummocks.HeightMinM, Spec.Hummocks.HeightMaxM * 1.42f, S.HummockMaxM),
			S.HummockMaxM >= Spec.Hummocks.HeightMinM && S.HummockMaxM <= Spec.Hummocks.HeightMaxM * 1.42f);
		const FGTReliefStats Again = GTRelief::Measure(Spec);
		TestTrue(FString::Printf(TEXT("Relief: %s - deterministic"), Strip.Name), Again.HummocksRaw == S.HummocksRaw && Again.GradeP95 == S.GradeP95 && Again.FieldSlopeMaxDeg == S.FieldSlopeMaxDeg);
		// The grass: a jittered 0.7 m placement over the strip's off-road ground (|y| 8-22 m, its first 100 m), through Spec.Grass.
		const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
		TArray<FTransform> Grid;
		for (float X = 2.f; X < 100.f; X += 0.7f)
		{
			for (float Y = 8.f; Y < 22.f; Y += 0.7f)
			{
				for (const float Side : { -1.f, 1.f })
				{
					const float PX = X + 0.2f * FMath::Sin(Y * 3.1f);
					const float PY = Side * (Y + 0.2f * FMath::Cos(X * 2.3f));
					Grid.Add(FTransform(FRotator(0.f, X * 37.f, 0.f), FVector(PX * 100.f, PY * 100.f, GTTerrain::HeightM(Spec, Profiles, PX, PY) * 100.f), FVector(0.9f)));
				}
			}
		}
		TArray<FTransform> Varied;
		FGTGrassStats G;
		GTTerrain::VaryGrass(Spec, Profiles, Grid, true, Varied, &G);
		const float Bare = G.In > 0 ? static_cast<float>(G.Bare) / G.In : 0.f;
		AddInfo(FString::Printf(TEXT("Relief: %s - grass on a %d-point grid: %d bare (%.1f %%), %d out, %d crest companions, height x%.3f-%.3f, lean at most %.1f deg"),
			Strip.Name, G.In, G.Bare, 100.f * Bare, G.Out, G.CrestExtra, G.ScaleMin, G.ScaleMax, G.TiltMaxDeg));
		if (Spec.Grass.IsActive())
		{
			TestTrue(FString::Printf(TEXT("Relief: %s - the bare share within %.0f-%.0f %% (%.1f)"), Strip.Name, 100.f * Spec.Grass.BareShareMin, 100.f * Spec.Grass.BareShareMax, 100.f * Bare),
				Bare >= Spec.Grass.BareShareMin - 0.02f && Bare <= Spec.Grass.BareShareMax + 0.02f);
			TestTrue(FString::Printf(TEXT("Relief: %s - the height scale within 1 +- %.2f"), Strip.Name, Spec.Grass.HeightJitter),
				G.ScaleMin >= 1.f - Spec.Grass.HeightJitter - 1.e-3f && G.ScaleMax <= 1.f + Spec.Grass.HeightJitter + 1.e-3f && G.ScaleMax - G.ScaleMin >= Spec.Grass.HeightJitter);
			TestTrue(FString::Printf(TEXT("Relief: %s - the lean at most %.0f deg"), Strip.Name, Spec.Grass.TiltDegrees), G.TiltMaxDeg <= Spec.Grass.TiltDegrees + 1.e-3f);
		}
		// Every GR1 number at its default: the placement exactly as given.
		FGTTerrainSpec Plain = Spec;
		Plain.Grass = FGTGrassVariation();
		TArray<FTransform> Same;
		GTTerrain::VaryGrass(Plain, Profiles, Grid, true, Same, nullptr);
		bool bSame = Same.Num() == Grid.Num();
		for (int32 K = 0; bSame && K < Grid.Num(); ++K)
		{
			bSame = Same[K].Equals(Grid[K], 0.f);
		}
		TestTrue(FString::Printf(TEXT("Relief: %s - FGTGrassVariation's defaults leave the placement as given"), Strip.Name), bSame);
		FGTTerrainSpec NoHummocks = Spec;
		NoHummocks.Hummocks.Density = 0.f;
		TestTrue(FString::Printf(TEXT("Relief: %s - Density 0 adds no hummock"), Strip.Name), GTTerrain::HummockHeightM(NoHummocks, 50.f, 15.f) == 0.f);
	}
	return true;
}
#endif
