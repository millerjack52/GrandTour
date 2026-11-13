// Ground relief GR2 phase B item 3 (docs/GROUND_RELIEF_PLAN.md GR2): GrandTour.Relief.Scatter, CPU only (-NullRHI). The ground
// scatter's placement (AGTGroundScatter::Plan, no world) over each strip's spec with a synthetic tussock field: determinism, open
// ground only (off the road's paving, every patch box + 3 m, every channel), the families' densities, the clustering, litter only
// near a tussock, one mound per tussock of 25 cm or more. "Scatter: " lines.
#include "Terrain/GTGroundScatter.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Terrain/GTTerrainGenerator.h"
#include "Terrain/GTTerrainSpecAsset.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTGroundScatterTest, "GrandTour.Relief.Scatter",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTGroundScatterTest::RunTest(const FString& Parameters)
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
	// The manifest's meshes (sizes only; Plan needs no mesh).
	TArray<FGTGroundScatterMesh> Meshes;
	auto Add = [&Meshes](const TCHAR* Family, float SizeCm)
	{
		FGTGroundScatterMesh& Row = Meshes.AddDefaulted_GetRef();
		Row.Family = FName(Family);
		Row.SizeCm = SizeCm;
	};
	for (float Size : { 3.f, 4.5f, 6.f, 8.f, 10.f, 12.f }) { Add(TEXT("Clods"), Size); }
	for (float Size : { 1.2f, 2.2f, 3.5f, 5.f }) { Add(TEXT("Pebbles"), Size); }
	for (float Size : { 15.f, 26.f, 40.f }) { Add(TEXT("Twigs"), Size); }
	for (float Size : { 12.f, 16.f, 21.f, 26.f }) { Add(TEXT("Litter"), Size); }
	for (float Size : { 26.f, 38.f, 50.f }) { Add(TEXT("TussockBases"), Size); }
	const AGTGroundScatter* Scatter = GetDefault<AGTGroundScatter>();
	for (const FStrip& Strip : Strips)
	{
		const UGTTerrainSpecAsset* Asset = LoadObject<UGTTerrainSpecAsset>(nullptr, Strip.Path);
		if (!TestNotNull(FString::Printf(TEXT("Scatter: %s's spec"), Strip.Name), Asset))
		{
			continue;
		}
		const FGTTerrainSpec& Spec = Asset->Spec;
		// Tussocks: 400 on hashed spots 9-20 m either side of x 10-200 m, footprints 15-60 cm.
		TArray<FTransform> Tussocks;
		TArray<float> Feet;
		FRandomStream Random(4242);
		for (int32 T = 0; T < 400; ++T)
		{
			const float X = Random.FRandRange(1000.f, 20000.f);
			const float Y = (Random.FRand() < 0.5f ? -1.f : 1.f) * Random.FRandRange(900.f, 2000.f);
			Tussocks.Add(FTransform(FVector(X, Y, 0.f)));
			Feet.Add(Random.FRandRange(15.f, 60.f));
		}
		TArray<AGTGroundScatter::FPoint> A;
		TArray<AGTGroundScatter::FPoint> B;
		AGTGroundScatter::FPlanStats SA;
		AGTGroundScatter::FPlanStats SB;
		Scatter->Plan(Spec, Meshes, Tussocks, Feet, A, SA);
		Scatter->Plan(Spec, Meshes, Tussocks, Feet, B, SB);
		bool bSame = A.Num() == B.Num();
		for (int32 I = 0; bSame && I < A.Num(); ++I)
		{
			bSame = A[I].XYCm.Equals(B[I].XYCm, 1e-3) && A[I].Mesh == B[I].Mesh && A[I].Scale == B[I].Scale && A[I].YawDeg == B[I].YawDeg;
		}
		TestTrue(FString::Printf(TEXT("Scatter: %s - deterministic (%d points)"), Strip.Name, A.Num()), bSame);
		// Every 7th point on open ground.
		const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
		TArray<FBox2D> Boxes;
		for (int32 Index = 0; Index < Spec.Sections.Num(); ++Index)
		{
			FBox2D Box(ForceInit);
			if (GTTerrain::DeformPatchBoxCm(Spec, Index, Box))
			{
				Boxes.Add(Box.ExpandBy(static_cast<double>(Scatter->PatchMarginCm)));
			}
		}
		int32 Closed = 0;
		int32 Checked = 0;
		for (int32 I = 0; I < A.Num(); I += 7)
		{
			++Checked;
			Closed += Scatter->IsOpenGround(Spec, Profiles, Boxes, A[I].XYCm) ? 0 : 1;
			for (const FBox2D& Box : Boxes)
			{
				Closed += Box.IsInside(A[I].XYCm) ? 1 : 0;
			}
		}
		TestEqual(FString::Printf(TEXT("Scatter: %s - none on the road, a patch (+3 m) or a channel (%d checked)"), Strip.Name, Checked), Closed, 0);
		// The densities over the open area.
		auto Count = [&A, &Meshes](const TCHAR* Family)
		{
			int32 N = 0;
			for (const AGTGroundScatter::FPoint& P : A)
			{
				N += Meshes[P.Mesh].Family == FName(Family) ? 1 : 0;
			}
			return N;
		};
		const double Open = FMath::Max(1.0, SA.OpenAreaM2);
		const float Clods = static_cast<float>(Count(TEXT("Clods")) / Open);
		const float Pebbles = static_cast<float>(Count(TEXT("Pebbles")) / Open);
		const float Twigs = static_cast<float>(Count(TEXT("Twigs")) / Open);
		const float Litter = static_cast<float>(Count(TEXT("Litter")) / FMath::Max(1.0, SA.LitterAreaM2));
		const int32 Bases = Count(TEXT("TussockBases"));
		AddInfo(FString::Printf(TEXT("Scatter: %s - open %.0f m2: clods %.3f, pebbles %.3f, twigs %.4f per m2; litter %.3f per m2 over %.0f m2 near tussocks; %d mounds under %d tussocks (%d under 25 cm); %d points refused"),
			Strip.Name, SA.OpenAreaM2, Clods, Pebbles, Twigs, Litter, SA.LitterAreaM2, Bases, SA.Tussocks, SA.TussocksUnderFootprint, SA.Rejected));
		TestTrue(FString::Printf(TEXT("Scatter: %s - clods 0.6 per m2 +-20 %% (%.3f)"), Strip.Name, Clods), FMath::Abs(Clods / 0.6f - 1.f) <= 0.2f);
		TestTrue(FString::Printf(TEXT("Scatter: %s - pebbles 1.5 per m2 +-20 %% (%.3f)"), Strip.Name, Pebbles), FMath::Abs(Pebbles / 1.5f - 1.f) <= 0.2f);
		TestTrue(FString::Printf(TEXT("Scatter: %s - twigs 0.05 per m2 +-30 %% (%.4f)"), Strip.Name, Twigs), FMath::Abs(Twigs / 0.05f - 1.f) <= 0.3f);
		TestTrue(FString::Printf(TEXT("Scatter: %s - litter 0.25 per m2 near tussocks +-30 %% (%.3f)"), Strip.Name, Litter), FMath::Abs(Litter / 0.25f - 1.f) <= 0.3f);
		int32 Wide = 0;
		for (float Foot : Feet)
		{
			Wide += Foot >= Scatter->BaseMinFootprintCm ? 1 : 0;
		}
		TestTrue(FString::Printf(TEXT("Scatter: %s - mounds %d of %d wide tussocks (some may lie off open ground)"), Strip.Name, Bases, Wide), Bases <= Wide && Bases >= Wide * 8 / 10);
		// Litter within 1.5 m of a tussock.
		int32 Far = 0;
		for (const AGTGroundScatter::FPoint& P : A)
		{
			if (Meshes[P.Mesh].Family != FName(TEXT("Litter")))
			{
				continue;
			}
			double Best = 1e18;
			for (const FTransform& T : Tussocks)
			{
				Best = FMath::Min(Best, FVector2D::DistSquared(P.XYCm, FVector2D(T.GetLocation())));
			}
			Far += Best > FMath::Square(Scatter->LitterReachCm + 0.5) ? 1 : 0;
		}
		TestEqual(FString::Printf(TEXT("Scatter: %s - litter only within 1.5 m of a tussock"), Strip.Name), Far, 0);
		// Clustered: the pebbles' count over 3 m cells of open ground varies well beyond a Poisson's.
		TMap<FIntPoint, int32> Cells;
		for (const AGTGroundScatter::FPoint& P : A)
		{
			if (Meshes[P.Mesh].Family == FName(TEXT("Pebbles")))
			{
				Cells.FindOrAdd(FIntPoint(FMath::FloorToInt32(P.XYCm.X / 300.0), FMath::FloorToInt32(P.XYCm.Y / 300.0)))++;
			}
		}
		double Sum = 0.0;
		double Sum2 = 0.0;
		for (const TPair<FIntPoint, int32>& C : Cells)
		{
			Sum += C.Value;
			Sum2 += static_cast<double>(C.Value) * C.Value;
		}
		const double Mean = Cells.Num() > 0 ? Sum / Cells.Num() : 0.0;
		const float Cv = Mean > 0.0 ? static_cast<float>(FMath::Sqrt(FMath::Max(0.0, Sum2 / Cells.Num() - Mean * Mean)) / Mean) : 0.f;
		const float PoissonCv = Mean > 0.0 ? static_cast<float>(1.0 / FMath::Sqrt(Mean)) : 0.f;
		// The cluster multiplier over the open ground (a 2 m grid), renormalised: it spans the plan's x0.1-2.5.
		TArray<float> Mult;
		const float Side = (GTTerrain::VertsPerSide(Spec) - 1) * Spec.QuadSizeCm;
		for (float Y = Spec.OriginYCm + 100.f; Y < Spec.OriginYCm + Side - 100.f; Y += 200.f)
		{
			for (float X = Spec.OriginXCm + 100.f; X < Spec.OriginXCm + Side - 100.f; X += 200.f)
			{
				if (Scatter->IsOpenGround(Spec, Profiles, Boxes, FVector2D(X, Y)))
				{
					Mult.Add(Scatter->ClusterMultiplier(FVector2D(X, Y)));
				}
			}
		}
		double MSum = 0.0;
		for (float V : Mult)
		{
			MSum += V;
		}
		const float MMean = Mult.Num() > 0 ? static_cast<float>(MSum / Mult.Num()) : 1.f;
		Mult.Sort();
		const float P10 = Mult.Num() > 0 ? Mult[Mult.Num() / 10] / MMean : 0.f;
		const float P90 = Mult.Num() > 0 ? Mult[Mult.Num() * 9 / 10] / MMean : 0.f;
		AddInfo(FString::Printf(TEXT("Scatter: %s - pebbles per 3 m cell: mean %.1f, CV %.2f (a Poisson's %.2f); the cluster multiplier over the open ground p10 %.2f p90 %.2f of its mean"),
			Strip.Name, Mean, Cv, PoissonCv, P10, P90));
		TestTrue(FString::Printf(TEXT("Scatter: %s - the multiplier spans the range (p10 %.2f under 0.5, p90 %.2f over 1.4)"), Strip.Name, P10, P90), P10 < 0.5f && P90 > 1.4f);
		TestTrue(FString::Printf(TEXT("Scatter: %s - clustered (CV %.2f over 1.5 x a Poisson's %.2f)"), Strip.Name, Cv, PoissonCv), Cv > 1.5f * PoissonCv);
	}
	return true;
}
#endif
