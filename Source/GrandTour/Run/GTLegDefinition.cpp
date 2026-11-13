#include "Run/GTLegDefinition.h"

#include "Core/GTGameplayTags.h"

float FGTConditionCurve::Sample(float Progress) const
{
	const FRichCurve* Curve = Intensity.GetRichCurveConst();
	if (!Curve || Curve->GetNumKeys() == 0)
	{
		return 0.f;
	}
	return FMath::Clamp(Curve->Eval(FMath::Clamp(Progress, 0.f, 1.f)), 0.f, 1.f);
}

float UGTLegDefinition::SampleCondition(FGameplayTag Tag, float Progress) const
{
	float Result = 0.f;
	for (const FGTConditionCurve& Condition : Conditions)
	{
		if (Condition.Tag == Tag)
		{
			Result = FMath::Max(Result, Condition.Sample(Progress));
		}
	}
	return Result;
}

bool UGTLegDefinition::HasCondition(FGameplayTag Tag) const
{
	for (const FGTConditionCurve& Condition : Conditions)
	{
		if (Condition.Tag == Tag && Condition.Intensity.GetRichCurveConst() && Condition.Intensity.GetRichCurveConst()->GetNumKeys() > 0)
		{
			return true;
		}
	}
	return false;
}

int32 UGTLegDefinition::RankForTime(float TimeSeconds) const
{
	int32 Rank = 1;
	for (const float Rival : RivalTimesSeconds)
	{
		if (Rival < TimeSeconds)
		{
			++Rank;
		}
	}
	return Rank;
}

FString UGTLegDefinition::MissionName(EGTMissionType Type)
{
	switch (Type)
	{
	case EGTMissionType::Endurance: return TEXT("Endurance");
	case EGTMissionType::Photograph: return TEXT("Photograph");
	default: return TEXT("Time trial");
	}
}

namespace
{
	FString ClockText(float Seconds)
	{
		const int32 Whole = FMath::Max(0, FMath::RoundToInt(Seconds));
		return FString::Printf(TEXT("%d:%02d"), Whole / 60, Whole % 60);
	}
}

FString UGTLegDefinition::MissionObjective(int32 CheckpointCount) const
{
	const FString Checkpoints = CheckpointCount > 0 ? FString::Printf(TEXT("%d checkpoints"), CheckpointCount) : FString(TEXT("the checkpoints"));
	switch (Mission)
	{
	case EGTMissionType::Endurance:
		return TimeLimitSeconds > 0.f
			? FString::Printf(TEXT("Make it through %s to the zone inside %s"), *Checkpoints, *ClockText(TimeLimitSeconds))
			: FString::Printf(TEXT("Make it through %s to the zone"), *Checkpoints);
	case EGTMissionType::Photograph:
		return FString::Printf(TEXT("Photograph the %s%s, clear %s, then extract"), *PhotoSubjectName, PhotosRequired > 1 ? *FString::Printf(TEXT(" x%d"), PhotosRequired) : TEXT(""), *Checkpoints);
	default:
		return FString::Printf(TEXT("Clear %s in order and stop in the zone"), *Checkpoints);
	}
}

FString UGTLegDefinition::Describe() const
{
	FString Profile;
	for (const FGTConditionCurve& Condition : Conditions)
	{
		Profile += FString::Printf(TEXT(" %s(%.1f/%.1f/%.1f)"), *Condition.Tag.ToString(), Condition.Sample(0.f), Condition.Sample(0.5f), Condition.Sample(1.f));
	}
	return FString::Printf(TEXT("%s #%d map=%s mission=%s par=%.0f limit=%.0f weather=%s conditions=[%s] rivals=%d"),
		*LegId.ToString(), LegNumber, *MapPath, *MissionName(Mission), ParTimeSeconds, TimeLimitSeconds, *StartWeatherName.ToString(), *Profile.TrimStart(), RivalTimesSeconds.Num());
}

void UGTLegDefinition::AddCondition(FGameplayTag Tag, std::initializer_list<TPair<float, float>> Keys)
{
	FGTConditionCurve Condition;
	Condition.Tag = Tag;
	FRichCurve* Curve = Condition.Intensity.GetRichCurve();
	for (const TPair<float, float>& Key : Keys)
	{
		const FKeyHandle Handle = Curve->AddKey(Key.Key, Key.Value);
		Curve->SetKeyInterpMode(Handle, RCIM_Linear);
	}
	Conditions.Add(MoveTemp(Condition));
}

int32 UGTLegDefinition::DefaultLegCount()
{
	return 5;
}

FString UGTLegDefinition::DefaultAssetName(int32 Index)
{
	return FString::Printf(TEXT("DA_Leg_%02d"), Index + 1);
}

void UGTLegDefinition::ApplyDefault(int32 Index)
{
	Index = FMath::Clamp(Index, 0, DefaultLegCount() - 1);
	LegNumber = Index + 1;
	LegId = *FString::Printf(TEXT("Leg%02d"), LegNumber);
	MapPath = FString::Printf(TEXT("/Game/GrandTour/Legs/L_Leg%02d"), LegNumber);
	Conditions.Reset();
	PhotoSubjectName.Reset();
	PhotosRequired = 1;
	// The fallback rivals (outside a tour): a quick one, two around par, one slow. The tour simulates its own.
	auto Rivals = [this](float Par) { RivalTimesSeconds = { Par * 0.83f, Par * 0.93f, Par * 1.07f, Par * 1.33f }; };
	switch (Index)
	{
	case 0:   // the 1.2 km flats: the warm-up time trial
		DisplayName = FText::FromString(TEXT("Leg 1: The Flats"));
		Mission = EGTMissionType::TimeTrial;
		MissionBrief = FText::FromString(TEXT("A warm-up, they said. Two checkpoints, a storm somewhere behind you. Keep it there."));
		ParTimeSeconds = 300.f;
		TimeLimitSeconds = 600.f;
		StartWeatherName = TEXT("Overcast");
		// Cold sets in over the second half, dust is the dirt section in the middle, heat is the last stretch.
		AddCondition(GTTags::Env_Cold, { {0.f, 0.f}, {0.5f, 0.1f}, {1.f, 0.8f} });
		AddCondition(GTTags::Env_Dust, { {0.f, 0.f}, {0.25f, 0.f}, {0.35f, 0.7f}, {0.6f, 0.7f}, {0.7f, 0.f} });
		AddCondition(GTTags::Env_Heat, { {0.f, 0.f}, {0.75f, 0.f}, {1.f, 0.6f} });
		RivalTimesSeconds = { 250.f, 280.f, 320.f, 400.f };
		return;
	case 1:   // the 1.6 km river road: three mud crossings in the rain with the front on your tail; the limit is real
		DisplayName = FText::FromString(TEXT("Leg 2: The Washout"));
		Mission = EGTMissionType::Endurance;
		MissionBrief = FText::FromString(TEXT("The river road, three crossings, and the front is already behind you. Make it inside the limit; past it nobody is waiting."));
		ParTimeSeconds = 420.f;
		TimeLimitSeconds = 720.f;
		StartWeatherName = TEXT("Rain");
		AddCondition(GTTags::Env_Cold, { {0.f, 0.2f}, {1.f, 0.5f} });
		Rivals(ParTimeSeconds);
		return;
	case 2:   // the 1.4 km hide: find the bear off the road past the first checkpoint, near the radiation pocket
		DisplayName = FText::FromString(TEXT("Leg 3: The Hide"));
		Mission = EGTMissionType::Photograph;
		MissionBrief = FText::FromString(TEXT("Somewhere off the road past the first checkpoint lives a bear nobody has photographed. Photograph it. Get close and it leaves; get closer and so does your skin."));
		PhotoSubjectName = TEXT("spectacled bear");
		PhotosRequired = 1;
		ParTimeSeconds = 480.f;
		TimeLimitSeconds = 900.f;
		StartWeatherName = TEXT("Clear");
		AddCondition(GTTags::Env_Dust, { {0.f, 0.f}, {0.3f, 0.6f}, {0.8f, 0.6f}, {1.f, 0.2f} });
		AddCondition(GTTags::Env_Heat, { {0.f, 0.3f}, {1.f, 0.5f} });
		Rivals(ParTimeSeconds);
		return;
	case 3:   // the 2 km pass: snow lanes and the cold, all the way up and over
		DisplayName = FText::FromString(TEXT("Leg 4: The Pass"));
		Mission = EGTMissionType::TimeTrial;
		MissionBrief = FText::FromString(TEXT("Up and over. It is cold, the road is white, and the heater is not optional."));
		ParTimeSeconds = 540.f;
		TimeLimitSeconds = 1000.f;
		StartWeatherName = TEXT("Snow");
		AddCondition(GTTags::Env_Cold, { {0.f, 0.5f}, {0.5f, 1.f}, {1.f, 0.8f} });
		Rivals(ParTimeSeconds);
		return;
	default:   // the 2.4 km salt: flat, hot, long; the engine cooks and the filter chokes
		DisplayName = FText::FromString(TEXT("Leg 5: The Salt"));
		Mission = EGTMissionType::Endurance;
		MissionBrief = FText::FromString(TEXT("The last one: flat, hot and long. The engine cooks, the filter chokes, and the finish is the finish."));
		ParTimeSeconds = 600.f;
		TimeLimitSeconds = 1080.f;
		StartWeatherName = TEXT("Clear");
		AddCondition(GTTags::Env_Heat, { {0.f, 0.4f}, {0.6f, 0.9f}, {1.f, 1.f} });
		AddCondition(GTTags::Env_Dust, { {0.f, 0.3f}, {1.f, 0.8f} });
		Rivals(ParTimeSeconds);
		return;
	}
}
