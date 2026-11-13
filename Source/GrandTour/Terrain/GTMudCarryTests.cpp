// MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 item 7): GrandTour.Mud.Carry, CPU only (the track paint's mud grid under
// -NullRHI). Each row prints a "Carry: " line for Art/mud_shape_test.ps1.
#include "Terrain/GTTrackPaintSubsystem.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Vehicle/GTTractionComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGTMudCarryTest, "GrandTour.Mud.Carry",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGTMudCarryTest::RunTest(const FString& Parameters)
{
	const UGTTractionComponent* Traction = GetDefault<UGTTractionComponent>();
	auto StepLoad = [Traction](float Load, const FGTMudLoadStep& Step)
	{
		return UGTTractionComponent::StepMudLoad(Load, Step, Traction->MudLoadRate, Traction->MudShedHalfM, Traction->MudWashHalfM, Traction->MudWashDepthM);
	};
	auto Within = [](float Value, float Asked, float Share) { return FMath::Abs(Value - Asked) <= FMath::Abs(Asked) * Share; };
	const float Dt = 1.f / 60.f;

	// ---- 1. the load: its rise in a patch, its shed over distance, its wash in water, none in snow ------------------------
	{
		FGTMudLoadStep In;
		In.bInContact = true;
		In.bInMudPatch = true;
		In.SinkageFraction = 0.5f;
		In.DeltaSeconds = Dt;
		float Plain = 0.f;
		for (int32 Tick = 0; Tick < 60; ++Tick)
		{
			Plain = StepLoad(Plain, In);
		}
		In.SlipShare = 1.f;
		float Spun = 0.f;
		for (int32 Tick = 0; Tick < 30; ++Tick)
		{
			Spun = StepLoad(Spun, In);
		}
		const float AskedPlain = Traction->MudLoadRate * (0.5f + 0.5f) * 1.f;
		const float AskedSpun = Traction->MudLoadRate * (0.5f + 0.5f) * 2.f * 0.5f;
		TestTrue(TEXT("Carry: the load rises in a patch at MudLoadRate x (0.5 + sinkage) x (1 + slip)"), Within(Plain, AskedPlain, 0.01f) && Within(Spun, AskedSpun, 0.01f));
		AddInfo(FString::Printf(TEXT("Carry: rise - 1 s in a patch at sinkage 0.5, no slip: %.3f (asked %.3f); 0.5 s at full slip: %.3f (asked %.3f); MudLoadRate %.2f /s"),
			Plain, AskedPlain, Spun, AskedSpun, Traction->MudLoadRate));

		FGTMudLoadStep Firm;
		Firm.bInContact = true;
		Firm.DeltaSeconds = Dt;
		Firm.DistanceCm = 800.f * Dt;   // 8 m/s
		float Load = 1.f;
		float At15 = -1.f;
		float At30 = -1.f;
		float Covered = 0.f;
		while (Covered < 3000.f - 1.e-3f)
		{
			Load = StepLoad(Load, Firm);
			Covered += Firm.DistanceCm;
			if (At15 < 0.f && Covered >= 1500.f - 1.e-3f)
			{
				At15 = Load;
			}
		}
		At30 = Load;
		TestTrue(TEXT("Carry: on firm ground the load halves over MudShedHalfM 15 m (within 10 %)"), Within(At15, 0.5f, 0.1f) && Within(At30, 0.25f, 0.1f));
		AddInfo(FString::Printf(TEXT("Carry: shed - from 1.0 at 8 m/s on firm ground: %.3f at 15 m (asked 0.5), %.3f at 30 m (asked 0.25); MudShedHalfM %.1f m"),
			At15, At30, Traction->MudShedHalfM));

		FGTMudLoadStep Wet = Firm;
		Wet.WaterDepthM = 0.10f;
		float Washed = 1.f;
		for (Covered = 0.f; Covered < 200.f - 1.e-3f; Covered += Wet.DistanceCm)
		{
			Washed = StepLoad(Washed, Wet);
		}
		FGTMudLoadStep Shallow = Wet;
		Shallow.WaterDepthM = 0.03f;
		float Puddled = 1.f;
		for (Covered = 0.f; Covered < 200.f - 1.e-3f; Covered += Shallow.DistanceCm)
		{
			Puddled = StepLoad(Puddled, Shallow);
		}
		FGTMudLoadStep Snow = Firm;
		Snow.bInSnowPatch = true;
		const float Snowed = StepLoad(0.8f, Snow);
		FGTMudLoadStep Air = Firm;
		Air.bInContact = false;
		const float Airborne = StepLoad(0.8f, Air);
		const float ShallowAsked = FMath::Pow(0.5f, 2.f / Traction->MudShedHalfM);
		TestTrue(TEXT("Carry: in water over 5 cm the load halves over 2 m (within 10 %); 3 cm of water sheds as firm ground"), Within(Washed, 0.5f, 0.1f) && Within(Puddled, ShallowAsked, 0.01f));
		TestTrue(TEXT("Carry: a snow patch carries none; a wheel in the air keeps its load"), Snowed == 0.f && Airborne == 0.8f);
		AddInfo(FString::Printf(TEXT("Carry: wash - 2 m in 10 cm of water: %.3f (asked 0.5); 2 m in 3 cm: %.3f (firm ground's %.3f); in a snow patch %.2f -> %.2f; airborne %.2f -> %.2f"),
			Washed, Puddled, ShallowAsked, 0.8f, Snowed, 0.8f, Airborne));
	}

	// ---- 2. the track paint's mud grid ---------------------------------------------------------------------------------------
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("GTMudCarryTest"));
	if (!TestNotNull(TEXT("Carry: a Game world"), World))
	{
		return false;
	}
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	UGTTrackPaintSubsystem* Paint = World->GetSubsystem<UGTTrackPaintSubsystem>();
	if (TestNotNull(TEXT("Carry: the track paint in the Game world"), Paint))
	{
		IConsoleVariable* CarryVar = IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Mud.Carry"));
		const int32 CarryWas = CarryVar ? CarryVar->GetInt() : 1;
		if (CarryVar)
		{
			CarryVar->Set(1, ECVF_SetByCode);
		}
		Paint->SetFocus(FVector(2500.f, 0.f, 0.f));
		const float Width = 27.f;
		const float LineY = 12.5f;   // through the mud cells' centres (the window's edge is on a 25 cm line)

		// 2a. A 50 m exit: one tyre leaves a patch with a full load at 8 m/s; the load sheds as the car does.
		FGTMudCarryState Stroke;
		Stroke.Seed = 4242;
		FGTMudLoadStep Firm;
		Firm.bInContact = true;
		Firm.DeltaSeconds = Dt;
		Firm.DistanceCm = 800.f * Dt;
		float Load = 1.f;
		float X = 0.f;
		const int32 BlotsBefore = Paint->GetCarriedBlotCount();
		while (X < 5000.f)
		{
			const float Next = FMath::Min(5000.f, X + Firm.DistanceCm);
			Paint->AddCarriedMud(Stroke, FVector(X, LineY, 0.f), FVector(Next, LineY, 0.f), Width, Load);
			Load = StepLoad(Load, Firm);
			X = Next;
			Paint->Tick(Dt);
		}
		const int32 Blots = Paint->GetCarriedBlotCount() - BlotsBefore;
		// The grid along the tyre's line every 25 cm (a mud cell each), in five 10 m bins.
		float Bins[5] = { 0.f, 0.f, 0.f, 0.f, 0.f };
		int32 Gaps = 0;
		int32 Samples = 0;
		int32 BinGaps[5] = { 0, 0, 0, 0, 0 };
		for (int32 Index = 0; Index < 200; ++Index)
		{
			const float G = Paint->SampleCoverage(FVector(12.5f + 25.f * Index, LineY, 0.f));
			Bins[Index / 40] += G / 40.f;
			const bool bGap = G < 0.02f;
			Gaps += bGap ? 1 : 0;
			BinGaps[Index / 40] += bGap ? 1 : 0;
			++Samples;
		}
		bool bDecreasing = true;
		bool bUnderFirst = true;
		for (int32 Bin = 1; Bin < 5; ++Bin)
		{
			bDecreasing &= Bins[Bin] <= Bins[Bin - 1];
			bUnderFirst &= Bins[Bin] <= Bins[0];
		}
		const float GapShare = static_cast<float>(Gaps) / FMath::Max(1, Samples);
		// MR2 housekeeping 1: the strength along the track follows a 1-3 m noise, so a 10 m bin may hold more than the one before
		// it (a smear after a gap); the track still thins: no bin over the first, the last 20 m under a third of the first 20 m,
		// the last bin under half the first. (MR1's row asked bin by bin; reported as "monotone".)
		const bool bThins = bUnderFirst && (Bins[3] + Bins[4]) < (Bins[0] + Bins[1]) / 3.f && Bins[4] < 0.5f * Bins[0];
		TestTrue(TEXT("Carry: G along the 50 m exit thins (no 10 m bin over the first, the last 20 m under a third of the first 20 m, the last bin under half the first)"), bThins);
		TestTrue(TEXT("Carry: at least 20 % of the line is gaps (G under 0.02): broken, not a solid band"), GapShare >= 0.2f);
		// Across the line: the band is clumps, not a stripe of constant width - the share of cells with mud 25 cm to each side.
		int32 Beside = 0;
		for (int32 Index = 0; Index < 200; ++Index)
		{
			Beside += Paint->SampleCoverage(FVector(12.5f + 25.f * Index, LineY + 25.f, 0.f)) >= 0.02f ? 1 : 0;
			Beside += Paint->SampleCoverage(FVector(12.5f + 25.f * Index, LineY - 25.f, 0.f)) >= 0.02f ? 1 : 0;
		}
		AddInfo(FString::Printf(TEXT("Carry: exit - %d blots over 50 m (load 1.00 -> %.3f), G by 10 m bin %.3f / %.3f / %.3f / %.3f / %.3f (asked thinning; monotone %s), gaps %.1f %% of %d cells (asked at least 20; by bin %d / %d / %d / %d / %d of 40); cells 25 cm either side with mud %.1f %%"),
			Blots, Load, Bins[0], Bins[1], Bins[2], Bins[3], Bins[4], bDecreasing ? TEXT("yes") : TEXT("no"), 100.f * GapShare, Samples, BinGaps[0], BinGaps[1], BinGaps[2], BinGaps[3], BinGaps[4], 100.f * Beside / 400.f));
		TestTrue(TEXT("Carry: the exit's mud left R (the ruts) alone"), Paint->GetMaxDepth() == 0.f);

		// 2a'. MR2 housekeeping 1: no beads. A 30 m exit from a full load (its own line, 6 m aside): G every 25 cm along the line
		// (the most across the tyre's band, as the check reads a track); its autocorrelation at lags of 1-10 blot spacings has no
		// peak (a lag above both neighbours) over 0.3. A regular bead spacing would show as such a peak; MR1's stamping had one.
		{
			const float LineY2 = LineY + 600.f;
			FGTMudCarryState Exit;
			Exit.Seed = 9001;
			float Load2 = 1.f;
			float X2 = 0.f;
			const int32 Blots0 = Paint->GetCarriedBlotCount();
			const int32 Gaps0 = Paint->GetCarriedGapCount();
			while (X2 < 3000.f)
			{
				const float Next = FMath::Min(3000.f, X2 + Firm.DistanceCm);
				Paint->AddCarriedMud(Exit, FVector(X2, LineY2, 0.f), FVector(Next, LineY2, 0.f), Width, Load2);
				Load2 = StepLoad(Load2, Firm);
				X2 = Next;
				Paint->Tick(Dt);
			}
			const int32 Laid = Paint->GetCarriedBlotCount() - Blots0;
			const int32 Places = Laid + Paint->GetCarriedGapCount() - Gaps0;
			const float Spacing = 3000.f / FMath::Max(1, Places);
			TArray<float> Line;
			for (int32 Index = 0; Index < 120; ++Index)
			{
				float Most = 0.f;
				for (int32 Across = -2; Across <= 2; ++Across)
				{
					Most = FMath::Max(Most, Paint->SampleCoverage(FVector(12.5f + 25.f * Index, LineY2 + 25.f * Across, 0.f)));
				}
				Line.Add(Most);
			}
			float Mean = 0.f;
			for (const float V : Line)
			{
				Mean += V / Line.Num();
			}
			float Var = 0.f;
			for (const float V : Line)
			{
				Var += FMath::Square(V - Mean);
			}
			const int32 LagLo = FMath::Max(1, FMath::RoundToInt(Spacing / 25.f));
			const int32 LagHi = FMath::Max(LagLo + 1, FMath::CeilToInt(10.f * Spacing / 25.f));
			TArray<float> R;
			for (int32 Lag = 0; Lag <= LagHi + 1; ++Lag)
			{
				float Sum = 0.f;
				for (int32 Index = 0; Index + Lag < Line.Num(); ++Index)
				{
					Sum += (Line[Index] - Mean) * (Line[Index + Lag] - Mean);
				}
				R.Add(Var > 0.f ? Sum / Var : 0.f);
			}
			float WorstPeak = -1.f;
			int32 WorstLag = 0;
			FString Rs;
			for (int32 Lag = LagLo; Lag <= LagHi; ++Lag)
			{
				Rs += FString::Printf(TEXT("%s%.2f"), Rs.IsEmpty() ? TEXT("") : TEXT(" / "), R[Lag]);
				if (R[Lag] > R[Lag - 1] && R[Lag] >= R[Lag + 1] && R[Lag] > WorstPeak)
				{
					WorstPeak = R[Lag];
					WorstLag = Lag;
				}
			}
			TestTrue(TEXT("Carry: along a 30 m exit G's autocorrelation at lags of 1-10 blot spacings has no peak over 0.3 (no beads)"), WorstPeak <= 0.3f && Var > 0.f);
			AddInfo(FString::Printf(TEXT("Carry: beads - 30 m exit, %d blots and %d gap places (spacing %.1f cm); G's autocorrelation at lags %d-%d cells (25 cm): %s; highest peak %s (asked none over 0.3)"),
				Laid, Places - Laid, Spacing, LagLo, LagHi, *Rs, WorstPeak < 0.f ? TEXT("none") : *FString::Printf(TEXT("%.2f at lag %d"), WorstPeak, WorstLag)));
		}

		// 2b. A splat on the ground adds G only within its reach.
		const FVector SplatAt(4000.f, -3000.f, 0.f);
		const float Reach = 60.f;
		Paint->AddSplat(SplatAt, Reach, 77);
		Paint->Tick(0.f);
		int32 Inside = 0;
		int32 Outside = 0;
		float Farthest = 0.f;
		for (float DY = -150.f; DY <= 150.f; DY += 25.f)
		{
			for (float DX = -150.f; DX <= 150.f; DX += 25.f)
			{
				const FVector P = SplatAt + FVector(DX, DY, 0.f);
				const float G = Paint->SampleCoverage(P);
				// The cell's centre, not the probe: the grid's value is the blot at its cell's centre.
				const float CellCm = Paint->WindowSizeCm / Paint->MudGridSize;
				const FVector2D Lo = Paint->GetOrigin() - FVector2D(Paint->WindowSizeCm * 0.5f);
				const FVector2D Cell = Lo + FVector2D((FMath::FloorToFloat((P.X - Lo.X) / CellCm) + 0.5f) * CellCm, (FMath::FloorToFloat((P.Y - Lo.Y) / CellCm) + 0.5f) * CellCm);
				const float Distance = static_cast<float>(FVector2D::Distance(Cell, FVector2D(SplatAt)));
				if (G > 0.f)
				{
					Farthest = FMath::Max(Farthest, Distance);
					(Distance <= Reach * 1.06f ? Inside : Outside) += 1;
				}
			}
		}
		TestTrue(TEXT("Carry: a splat on the landscape adds G only within its reach (and some inside it)"), Outside == 0 && Inside >= 2);
		AddInfo(FString::Printf(TEXT("Carry: splat - reach %.0f cm: %d cells with G inside it, %d outside (asked 0), the farthest cell centre %.1f cm; G at the centre %.3f, B %.3f"),
			Reach, Inside, Outside, Farthest, Paint->SampleCoverage(SplatAt), Paint->SampleWetness(SplatAt)));

		// 2c. Fading and drying: a splat's centre cell over 700 s at 0.5 s ticks; the time to 1/e of each.
		const FVector Fresh(-3000.f, 2000.f, 0.f);
		Paint->AddSplat(Fresh, 80.f, 5);
		Paint->Tick(0.f);
		const float G0 = Paint->SampleCoverage(Fresh);
		const float B0 = Paint->SampleWetness(Fresh);
		float GTime = -1.f;
		float BTime = -1.f;
		float Clock = 0.f;
		while (Clock < 700.f && (GTime < 0.f || BTime < 0.f))
		{
			Paint->Tick(0.5f);
			Clock += 0.5f;
			if (BTime < 0.f && Paint->SampleWetness(Fresh) <= B0 / UE_EULERS_NUMBER)
			{
				BTime = Clock;
			}
			if (GTime < 0.f && Paint->SampleCoverage(Fresh) <= G0 / UE_EULERS_NUMBER)
			{
				GTime = Clock;
			}
		}
		TestTrue(TEXT("Carry: G fades to 1/e in MudFadeSeconds and B dries to 1/e in MudDrySeconds (within 10 %)"),
			G0 > 0.f && B0 > 0.f && Within(GTime, Paint->MudFadeSeconds, 0.1f) && Within(BTime, Paint->MudDrySeconds, 0.1f));
		AddInfo(FString::Printf(TEXT("Carry: decay - G %.3f to 1/e at %.1f s (asked %.0f), B %.3f to 1/e at %.1f s (asked %.0f); G every %.1f s, B every %.1f s"),
			G0, GTime, Paint->MudFadeSeconds, B0, BTime, Paint->MudDrySeconds, Paint->CoverDecayInterval, Paint->WetDecayInterval));

		// 2d. gt.Mud.Carry 0 lays nothing.
		if (CarryVar)
		{
			CarryVar->Set(0, ECVF_SetByCode);
			FGTMudCarryState Off;
			const int32 Before = Paint->GetCarriedBlotCount();
			Paint->AddCarriedMud(Off, FVector(-2000.f, -2000.f, 0.f), FVector(-1000.f, -2000.f, 0.f), Width, 1.f);
			Paint->Tick(Dt);
			const bool bNone = Paint->GetCarriedBlotCount() == Before && Paint->SampleCoverage(FVector(-1500.f, -2000.f, 0.f)) == 0.f;
			CarryVar->Set(CarryWas, ECVF_SetByCode);
			TestTrue(TEXT("Carry: gt.Mud.Carry 0 lays no carried mud"), bNone);
			AddInfo(FString::Printf(TEXT("Carry: switch - gt.Mud.Carry 0 over 10 m at a full load: %d blots"), Paint->GetCarriedBlotCount() - Before));
		}
	}
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
#endif
