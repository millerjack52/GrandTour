#include "Core/GTHUD.h"

#include "Character/GTExposureComponent.h"
#include "Character/GTPlayerCharacter.h"
#include "Core/GTGameplayTags.h"
#include "Core/GTPlayerController.h"
#include "Core/GTRunSubsystem.h"
#include "Crafting/GTCraftingStation.h"
#include "Environment/GTEnvironmentComponent.h"
#include "Parts/GTItemDefinition.h"
#include "Parts/GTItemRegistry.h"
#include "Race/GTStandings.h"
#include "Interaction/GTInteractionComponent.h"
#include "Inventory/GTInventoryComponent.h"
#include "Run/GTLegDefinition.h"
#include "Run/GTRunGameState.h"
#include "Tools/GTToolDefinition.h"
#include "Vehicle/GTBodyComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTWinchComponent.h"
#include "Weather/GTWeatherSubsystem.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

namespace
{
	const FLinearColor HudDimColour(0.8f, 0.8f, 0.8f, 0.8f);
	const FLinearColor Warn(1.f, 0.5f, 0.2f);
	const FLinearColor Bad(1.f, 0.2f, 0.15f);
	const FLinearColor Good(0.4f, 0.95f, 0.5f);

	FString Clock(float Seconds)
	{
		const int32 Whole = FMath::Max(0, FMath::FloorToInt(Seconds));
		return FString::Printf(TEXT("%02d:%02d"), Whole / 60, Whole % 60);
	}

	FString Ordinal(int32 N)
	{
		const int32 Mod100 = N % 100;
		const TCHAR* Suffix = (Mod100 >= 11 && Mod100 <= 13) ? TEXT("th") : (N % 10 == 1) ? TEXT("st") : (N % 10 == 2) ? TEXT("nd") : (N % 10 == 3) ? TEXT("rd") : TEXT("th");
		return FString::Printf(TEXT("%d%s"), N, Suffix);
	}
}

void AGTHUD::DrawLabel(const FString& Text, float X, float Y, const FLinearColor& Colour, float Scale)
{
	DrawText(Text, Colour, X, Y, GEngine ? GEngine->GetMediumFont() : nullptr, Scale);
}

void AGTHUD::DrawBar(float X, float Y, float Width, float Height, float Fraction, const FLinearColor& Colour)
{
	DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.5f), X, Y, Width, Height);
	DrawRect(Colour, X + 1.f, Y + 1.f, (Width - 2.f) * FMath::Clamp(Fraction, 0.f, 1.f), Height - 2.f);
}

void AGTHUD::DrawLeg(const AGTRunGameState* RunState, float W)
{
	if (!RunState || RunState->GetPhase() == EGTLegPhase::None || RunState->GetPhase() == EGTLegPhase::Finished)
	{
		return;
	}
	const UGTLegDefinition* Leg = RunState->GetLeg();
	const float X = W - 260.f;
	float Y = 20.f;
	if (RunState->GetPhase() == EGTLegPhase::Staging)
	{
		DrawLabel(FString::Printf(TEXT("%s"), Leg ? *Leg->DisplayName.ToString() : TEXT("Leg")), X, Y, HudDimColour);
		DrawLabel(TEXT("Leg starts when you move"), X, Y + 20.f, HudDimColour);
		return;
	}
	const bool bOvertime = RunState->IsOvertime();
	DrawLabel(FString::Printf(TEXT("Leg %d   %s%s"), Leg ? Leg->LegNumber : 0, *Clock(RunState->GetLegTime()), bOvertime ? TEXT("  OVERTIME") : TEXT("")), X, Y, bOvertime ? Bad : FLinearColor::White, 1.2f);
	Y += 24.f;
	if (Leg)
	{
		DrawLabel(FString::Printf(TEXT("par %s%s"), *Clock(Leg->ParTimeSeconds), Leg->TimeLimitSeconds > 0.f ? *FString::Printf(TEXT("   limit %s"), *Clock(Leg->TimeLimitSeconds)) : TEXT("")), X, Y, HudDimColour);
		Y += 20.f;
	}
	float Distance = 0.f;
	float Bearing = 0.f;
	const bool bHaveObjective = RunState->GetObjectiveBearing(Distance, Bearing);
	const int32 Cleared = RunState->GetCheckpointsCleared();
	const int32 Count = RunState->GetCheckpointCount();
	if (!RunState->AllCheckpointsCleared())
	{
		DrawLabel(FString::Printf(TEXT("Checkpoint %d / %d"), Cleared + 1, Count), X, Y);
	}
	else
	{
		DrawLabel(TEXT("Extraction"), X, Y, Good);
	}
	Y += 20.f;
	if (bHaveObjective)
	{
		const TCHAR* Side = FMath::Abs(Bearing) < 10.f ? TEXT("ahead") : (Bearing < 0.f ? TEXT("left") : TEXT("right"));
		DrawLabel(FString::Printf(TEXT("%.0f m   %.0f deg %s"), Distance / 100.f, FMath::Abs(Bearing), Side), X, Y, HudDimColour);
		Y += 20.f;
	}
	// The mission beyond the checkpoints: the picture still to take, the endurance clock, a failed limit.
	const FString MissionLine = RunState->GetMissionLine();
	if (!MissionLine.IsEmpty())
	{
		const bool bFailed = RunState->IsMissionFailed();
		const bool bDone = RunState->IsMissionSatisfied();
		DrawLabel(MissionLine, X, Y, bFailed ? Bad : bDone ? Good : Warn);
		Y += 20.f;
	}
	const float Hold = RunState->GetExtractionProgress();
	if (Hold > 0.f)
	{
		DrawLabel(TEXT("Hold still to extract"), X, Y, Good);
		DrawBar(X, Y + 20.f, 220.f, 10.f, Hold, Good);
	}
	else if (RunState->AllCheckpointsCleared() && Distance < 1500.f && bHaveObjective)
	{
		const FString Refusal = RunState->GetExtractionRefusal();
		DrawLabel(Refusal.IsEmpty() ? TEXT("Stop inside the zone") : *FString::Printf(TEXT("Zone: %s"), *Refusal), X, Y, Refusal.IsEmpty() ? HudDimColour : Warn);
	}
}

void AGTHUD::DrawWeather(float Y)
{
	const UGTWeatherSubsystem* Weather = GetWorld()->GetSubsystem<UGTWeatherSubsystem>();
	if (!Weather)
	{
		return;
	}
	const FGTWeatherValues& V = Weather->GetCurrent();
	FString Line = FString::Printf(TEXT("%s   %s %.0f%%   wet %.0f%%   %.0f C"),
		*Weather->GetStateName(), V.TemperatureC < 0.f ? TEXT("snow") : TEXT("rain"), V.RainIntensity * 100.f, Weather->GetWetness() * 100.f, V.TemperatureC);
	if (Weather->GetStormPressure() > 0.f)
	{
		Line += FString::Printf(TEXT("   STORM %.0f%%"), Weather->GetStormPressure() * 100.f);
	}
	DrawLabel(Line, 20.f, Y, Weather->GetStormPressure() > 0.5f ? Warn : HudDimColour);
}

void AGTHUD::DrawConditions(const AGTCarPawn* Car, float W, float& Y)
{
	if (!Car)
	{
		return;
	}
	if (Car->IsInHazard(GTTags::Hazard_Radiation))
	{
		DrawLabel(TEXT("RADIATION"), 20.f, Y, Bad, 1.2f);
		Y += 24.f;
	}
	if (Car->IsInHazard(GTTags::Hazard_Weather))
	{
		DrawLabel(TEXT("STORM FRONT"), 20.f, Y, Warn, 1.2f);
		Y += 24.f;
	}
	const UGTEnvironmentComponent* Env = Car->GetEnvironment();
	if (!Env)
	{
		return;
	}
	struct FCue { FGameplayTag Tag; const TCHAR* Warning; const TCHAR* Damage; };
	const FCue Cues[] = {
		{GTTags::Env_Heat, TEXT("OVERHEATING - ease off"), TEXT("ENGINE COOKING")},
		{GTTags::Env_Dust, TEXT("FILTER CLOGGING - slow down"), TEXT("FILTER CHOKED - engine scoring")},
		{GTTags::Env_Cold, TEXT("COLD - engine down on power"), TEXT("COLD")},
	};
	for (const FCue& Cue : Cues)
	{
		const EGTConditionStage Stage = Env->GetStage(Cue.Tag);
		if (Stage == EGTConditionStage::Warning)
		{
			DrawLabel(Cue.Warning, 20.f, Y, Warn);
			Y += 20.f;
		}
		else if (Stage == EGTConditionStage::Damage)
		{
			DrawLabel(Cue.Damage, 20.f, Y, Bad);
			Y += 20.f;
		}
	}
}

void AGTHUD::DrawResults(const AGTRunGameState* RunState, float W, float H)
{
	const FGTLegResult& R = RunState->GetResult();
	UGTRunSubsystem* Run = GetWorld() && GetWorld()->GetGameInstance() ? GetWorld()->GetGameInstance()->GetSubsystem<UGTRunSubsystem>() : nullptr;
	const bool bTourOver = Run && Run->IsTourComplete();
	const TArray<FGTStandingRow> Standings = Run ? Run->BuildStandings() : TArray<FGTStandingRow>();

	// Two columns: the leg on the left, the placings and the tour table on the right.
	const float PanelW = 760.f;
	const float ColW = 370.f;
	const float X = W * 0.5f - PanelW * 0.5f;
	const float X2 = X + ColW + 20.f;
	const float Top = H * 0.12f;
	DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.78f), X - 20.f, Top - 20.f, PanelW + 40.f, H * 0.78f);
	float Y = Top;
	DrawLabel(bTourOver ? TEXT("TOUR OVER") : R.bCompleted ? TEXT("LEG COMPLETE") : TEXT("DID NOT FINISH"), X, Y, bTourOver ? FLinearColor::White : R.bCompleted ? Good : Bad, 1.6f);
	Y += 40.f;
	DrawLabel(FString::Printf(TEXT("%s   %s"), *UGTLegDefinition::MissionName(R.Mission), *R.MissionText), X, Y, R.bCompleted ? Good : Bad);
	Y += 26.f;
	DrawLabel(FString::Printf(TEXT("Time   %s   (par %s)%s"), *Clock(R.TimeSeconds), *Clock(R.ParTimeSeconds), R.bOvertime ? TEXT("   OVERTIME") : TEXT("")), X, Y, R.bOvertime ? Bad : FLinearColor::White, 1.2f);
	Y += 26.f;
	DrawLabel(FString::Printf(TEXT("Checkpoints   %d / %d%s"), R.CheckpointsCleared, R.CheckpointCount, R.Mission == EGTMissionType::Photograph ? *FString::Printf(TEXT("     Photographs   %d"), R.PhotosTaken) : TEXT("")), X, Y);
	Y += 30.f;
	DrawLabel(FString::Printf(TEXT("Haul   %.1f kg   worth %d at base prices"), R.HaulWeightKg, R.HaulValue), X, Y, Good);
	Y += 22.f;
	for (const FGTItemStack& Stack : R.Haul)
	{
		DrawLabel(FString::Printf(TEXT("   %s x%d"), *GTItems::DisplayName(Stack.ItemId), Stack.Count), X, Y, HudDimColour);
		Y += 18.f;
	}
	if (R.Haul.Num() == 0)
	{
		DrawLabel(TEXT("   nothing"), X, Y, HudDimColour);
		Y += 18.f;
	}

	// Right column: the leg's placings by time, then the tour table.
	float Y2 = Top + 40.f;
	DrawLabel(FString::Printf(TEXT("Leg placing   %s of %d   +%d pts   +%d credits"), *Ordinal(R.Rank), R.RivalCount + 1, R.Points, R.PrizeCredits), X2, Y2, R.bCompleted ? FLinearColor::White : HudDimColour);
	Y2 += 24.f;
	{
		// Everyone on the leg, quickest first; the player in the list by their own time.
		struct FLine { FString Name; float Time; bool bFinished; bool bPlayer; };
		TArray<FLine> Lines;
		Lines.Add({ TEXT("You"), R.TimeSeconds, R.bCompleted, true });
		for (const FGTRivalLegOutcome& Rival : R.Rivals)
		{
			Lines.Add({ Rival.Name, Rival.TimeSeconds, Rival.bFinished, false });
		}
		Lines.StableSort([](const FLine& A, const FLine& B) { return A.bFinished != B.bFinished ? A.bFinished : A.Time < B.Time; });
		for (int32 Index = 0; Index < Lines.Num(); ++Index)
		{
			const FLine& Line = Lines[Index];
			DrawLabel(FString::Printf(TEXT("  %d. %-16s %s"), Index + 1, *Line.Name, Line.bFinished ? *Clock(Line.Time) : TEXT("DNF")), X2, Y2, Line.bPlayer ? Good : HudDimColour);
			Y2 += 18.f;
		}
	}
	Y2 += 10.f;
	DrawLabel(bTourOver ? TEXT("Final standings") : TEXT("Tour standings"), X2, Y2, FLinearColor::White, 1.1f);
	Y2 += 22.f;
	for (const FGTStandingRow& Row : Standings)
	{
		DrawLabel(FString::Printf(TEXT("  %d. %-16s %3d pts   %d/%d legs   %s"), Row.Place, *Row.Name, Row.Points, Row.LegsFinished, Row.LegsRun, *Clock(Row.TotalTimeSeconds)), X2, Y2, Row.bPlayer ? Good : HudDimColour);
		Y2 += 18.f;
	}
	if (bTourOver && Run)
	{
		Y2 += 10.f;
		DrawLabel(Run->EndingLine(), X2, Y2, FLinearColor::White);
		Y2 += 22.f;
	}
	const float YEnd = FMath::Max(Y, Y2) + 16.f;
	DrawLabel(bTourOver ? TEXT("Enter / Start: back to camp") : TEXT("Enter / Start: continue"), X, YEnd, HudDimColour);
}

void AGTHUD::DrawCredits(float W)
{
	const UGameInstance* GameInstance = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
	const UGTRunSubsystem* Run = GameInstance ? GameInstance->GetSubsystem<UGTRunSubsystem>() : nullptr;
	if (Run)
	{
		DrawLabel(FString::Printf(TEXT("Credits %d"), Run->GetCurrency()), W - 260.f, 130.f, HudDimColour);
	}
}

void AGTHUD::DrawStation(const AGTPlayerCharacter* Character, float W, float H)
{
	const AGTCraftingStation* Station = Character->GetStation();
	TArray<FGTScreenRow> Rows;
	Station->BuildRows(const_cast<AGTPlayerCharacter*>(Character), Rows);
	const float X = 40.f;
	float Y = 70.f;
	// Long lists (the trader) scroll with the cursor instead of running off the bottom of the screen.
	const int32 Selected = Character->GetStationSelection();
	const int32 VisibleRows = FMath::Max(3, FMath::FloorToInt((H - 220.f) / 20.f));
	const int32 FirstRow = Rows.Num() > VisibleRows ? FMath::Clamp(Selected - VisibleRows / 2, 0, Rows.Num() - VisibleRows) : 0;
	const int32 EndRow = FMath::Min(Rows.Num(), FirstRow + VisibleRows);
	const int32 ShownLines = EndRow - FirstRow + (FirstRow > 0 ? 1 : 0) + (EndRow < Rows.Num() ? 1 : 0);
	DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.7f), X - 16.f, Y - 12.f, W * 0.62f, FMath::Min(H - 60.f, 20.f * ShownLines + 130.f));
	DrawLabel(Station->DisplayName.ToUpper(), X, Y, Good, 1.3f);
	Y += 30.f;
	if (FirstRow > 0)
	{
		DrawLabel(FString::Printf(TEXT("  ... %d more above"), FirstRow), X, Y, HudDimColour);
		Y += 20.f;
	}
	for (int32 Index = FirstRow; Index < EndRow; ++Index)
	{
		const FGTScreenRow& Row = Rows[Index];
		if (Row.bHeader)
		{
			DrawLabel(Row.Text, X, Y, HudDimColour);
		}
		else
		{
			const bool bSel = Index == Selected;
			DrawLabel(FString::Printf(TEXT("%s %s"), bSel ? TEXT(">") : TEXT(" "), *Row.Text), X, Y, Row.bEnabled ? (bSel ? FLinearColor::White : FLinearColor(0.85f, 0.85f, 0.85f)) : FLinearColor(0.5f, 0.5f, 0.5f));
			if (bSel && !Row.Hint.IsEmpty())
			{
				DrawLabel(Row.Hint, X + W * 0.62f - 320.f, Y, Row.bEnabled ? Good : Warn);
			}
		}
		Y += 20.f;
	}
	if (EndRow < Rows.Num())
	{
		DrawLabel(FString::Printf(TEXT("  ... %d more below"), Rows.Num() - EndRow), X, Y, HudDimColour);
		Y += 20.f;
	}
	Y += 10.f;
	if (!Station->LastMessage.IsEmpty())
	{
		DrawLabel(Station->LastMessage, X, Y, Good);
		Y += 20.f;
	}
	DrawLabel(Character->IsStationSelectionArmed() ? TEXT("scroll: select   T: act   Tab or E on the station: close") : TEXT("scroll to pick the next row   Tab or E on the station: close"), X, Y, HudDimColour);
}

void AGTHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas || !bShowHUD)
	{
		return;
	}
	const AGTPlayerController* PC = Cast<AGTPlayerController>(GetOwningPlayerController());
	if (!PC)
	{
		return;
	}
	const float W = Canvas->ClipX;
	const float H = Canvas->ClipY;
	const AGTRunGameState* RunState = GetWorld()->GetGameState<AGTRunGameState>();

	AGTCarPawn* Car = PC->GetCar();
	AGTPlayerCharacter* Character = PC->GetPlayerCharacter();
	if (RunState && RunState->GetPhase() == EGTLegPhase::Finished)
	{
		DrawResults(RunState, W, H);
		return;
	}
	DrawLeg(RunState, W);
	DrawCredits(W);

	if (PC->IsDriving() && Car)
	{
		DrawLabel(TEXT("F  get out     R  winch reel (hold)"), 20.f, 20.f, HudDimColour);
		DrawWeather(40.f);
		float Y = 64.f;
		if (const UGTWinchComponent* Winch = Car->GetWinch())
		{
			switch (Winch->GetState())
			{
			case EGTWinchState::Attached:
				DrawLabel(FString::Printf(TEXT("Winch attached  %.1f m  %.0f kN   G  release"), Winch->GetCableDistance() / 100.f, Winch->GetTensionN() / 1000.f), 20.f, Y);
				Y += 20.f;
				break;
			case EGTWinchState::HookCarried:
				DrawLabel(TEXT("Winch hook is outside"), 20.f, Y, Warn);
				Y += 20.f;
				break;
			case EGTWinchState::Snapped:
				DrawLabel(TEXT("Winch cable snapped"), 20.f, Y, Warn);
				Y += 20.f;
				break;
			default:
				break;
			}
		}
		DrawConditions(Car, W, Y);
		if (const UGTBodyComponent* Body = Car->GetBody())
		{
			FString Open;
			for (int32 Door = 0; Door < Body->GetDoorCount(); ++Door)
			{
				if (Body->IsDoorOpen(Door) && !Body->IsDoorDetached(Door))
				{
					Open += (Open.IsEmpty() ? FString() : FString(TEXT(", "))) + Body->DoorName(Door);
				}
			}
			if (!Open.IsEmpty())
			{
				DrawLabel(TEXT("Open: ") + Open, 20.f, Y, Warn);
				Y += 20.f;
			}
		}
		if (Character && Character->GetExposure())
		{
			DrawLabel(TEXT("Exposure"), W - 240.f, H - 60.f, HudDimColour);
			DrawBar(W - 240.f, H - 40.f, 220.f, 14.f, Character->GetExposure()->GetFraction(), FLinearColor(0.3f, 0.8f, 1.f));
		}
		return;
	}
	if (!Character)
	{
		return;
	}
	DrawWeather(20.f);
	const bool bStation = Character->IsStationOpen();
	if (bStation)
	{
		DrawStation(Character, W, H);
	}

	// Crosshair (kept under a station screen: E still acts on whatever it points at)
	DrawRect(FLinearColor(1.f, 1.f, 1.f, 0.8f), W * 0.5f - 2.f, H * 0.5f - 2.f, 4.f, 4.f);

	// Prompt and hold bar, beside the screen when one is open
	if (const UGTInteractionComponent* Interaction = Character->GetInteraction())
	{
		const FString Prompt = Interaction->GetPrompt();
		if (!Prompt.IsEmpty())
		{
			const float PromptX = bStation ? W * 0.62f + 40.f : W * 0.5f - 120.f;
			const bool bAvailable = Interaction->IsOfferAvailable();
			const FString Line = bAvailable ? FString::Printf(TEXT("[E]  %s"), *Prompt) : Prompt;
			DrawLabel(Line, PromptX, H * 0.5f + 24.f, bAvailable ? FLinearColor::White : HudDimColour);
			if (bAvailable && Interaction->GetCurrentOffer().HoldTime > 0.f)
			{
				DrawBar(PromptX + 60.f, H * 0.5f + 46.f, 120.f, 8.f, Interaction->GetHoldProgress(), FLinearColor(1.f, 0.85f, 0.3f));
			}
		}
	}
	if (bStation)
	{
		return;   // the tool line, exposure and inventory stay out from under the screen
	}

	// What is draining the meter out here
	float Y = 44.f;
	if (Character->EnvironmentDrainRate > 0.f)
	{
		DrawLabel(FString::Printf(TEXT("Exposure -%.1f/s%s"), Character->EnvironmentDrainRate, Character->bUnderCover ? TEXT("  (sheltered from the rain)") : TEXT("")), 20.f, Y, Warn);
		Y += 20.f;
	}
	else if (Character->bUnderCover)
	{
		DrawLabel(TEXT("Sheltered"), 20.f, Y, HudDimColour);
		Y += 20.f;
	}

	// Tool, hook, collapse
	const UGTToolDefinition* Tool = Character->GetCurrentTool();
	DrawLabel(FString::Printf(TEXT("Tool: %s   (scroll to change, Tab inventory, H head bob)"), Tool ? *Tool->DisplayName.ToString() : TEXT("hands")), 20.f, H - 40.f, HudDimColour);
	if (Character->IsCarryingHook())
	{
		DrawLabel(TEXT("Winch hook in hand (G to drop)"), 20.f, H - 60.f, Warn);
	}
	if (Character->GetExposure())
	{
		if (Character->GetExposure()->IsCollapsed())
		{
			DrawLabel(TEXT("COLLAPSED - get back to the car"), W * 0.5f - 110.f, H * 0.3f, Warn, 1.3f);
		}
		DrawLabel(TEXT("Exposure"), W - 240.f, H - 60.f, HudDimColour);
		DrawBar(W - 240.f, H - 40.f, 220.f, 14.f, Character->GetExposure()->GetFraction(), FLinearColor(0.3f, 0.8f, 1.f));
	}

	// Inventory and boot
	if (Character->IsInventoryOpen() && Character->GetInventory())
	{
		const UGTInventoryComponent* Mine = Character->GetInventory();
		Y = FMath::Max(Y, 80.f);
		DrawLabel(FString::Printf(TEXT("Carrying  %.1f / %.0f kg"), Mine->GetTotalWeightKg(), Mine->MaxWeightKg), 20.f, Y);
		Y += 20.f;
		const bool bBoot = Character->IsBootOpen();
		const int32 Selected = bBoot ? Character->GetBootSelection() : Character->GetInventorySelection();
		const UGTItemRegistry* Registry = UGTItemRegistry::Get(this);
		for (int32 Index = 0; Index < Mine->Items.Num(); ++Index)
		{
			const FGTItemStack& Stack = Mine->Items[Index];
			const bool bUsable = !bBoot && Registry && Registry->FindConsumable(Stack.ItemId) != nullptr;
			DrawLabel(FString::Printf(TEXT("%s %s x%d%s"), Selected == Index ? TEXT(">") : TEXT(" "), *GTItems::DisplayName(Stack.ItemId), Stack.Count,
				(bUsable && Selected == Index) ? TEXT("   T: use") : TEXT("")), 20.f, Y);
			Y += 18.f;
		}
		if (!bBoot && !Character->LastUseMessage.IsEmpty())
		{
			DrawLabel(Character->LastUseMessage, 20.f, Y + 4.f, HudDimColour);
			Y += 22.f;
		}
		if (bBoot && Character->GetBootCar() && Character->GetBootCar()->GetBoot())
		{
			const UGTInventoryComponent* Boot = Character->GetBootCar()->GetBoot();
			Y += 12.f;
			DrawLabel(FString::Printf(TEXT("Boot  %.1f / %.0f kg"), Boot->GetTotalWeightKg(), Boot->MaxWeightKg), 20.f, Y);
			Y += 20.f;
			for (int32 Index = 0; Index < Boot->Items.Num(); ++Index)
			{
				const FGTItemStack& Stack = Boot->Items[Index];
				DrawLabel(FString::Printf(TEXT("%s %s x%d"), Selected == Mine->Items.Num() + Index ? TEXT(">") : TEXT(" "), *GTItems::DisplayName(Stack.ItemId), Stack.Count), 20.f, Y);
				Y += 18.f;
			}
			Y += 8.f;
			DrawLabel(TEXT("scroll: select   T: move stack   Tab or E on the boot: close"), 20.f, Y, HudDimColour);
		}
	}
}
