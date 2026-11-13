#pragma once

#include "CoreMinimal.h"
#include <initializer_list>
#include "Curves/CurveFloat.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "GTLegDefinition.generated.h"

class UGTWeatherStateDefinition;

/** One condition of a leg's profile: an Env.* tag and its intensity (0..1) against leg progress (0 = start, 1 = extraction). */
USTRUCT(BlueprintType)
struct FGTConditionCurve
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FGameplayTag Tag;

	/** Intensity along the leg; the X axis is progress 0..1. No keys = the tag is absent. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FRuntimeFloatCurve Intensity;

	float Sample(float Progress) const;
};

/**
 * What a leg asks of you (PROJECT_PLAN 6, leg mission types, 2026-09-14): the challenge kinds of
 * the TV specials. Every kind is scored by the leg time and placed against the rivals; what
 * differs is what the extraction accepts and what counts as a finish.
 */
UENUM(BlueprintType)
enum class EGTMissionType : uint8
{
	/** Clear the checkpoints in order and stop in the zone. Past the limit the result is marked overtime but still counts. */
	TimeTrial,
	/** Make it along the road inside the limit: past it the leg is a did-not-finish, no points, no prize. */
	Endurance,
	/** Find and photograph the subject (somewhere off the route), then extract; the zone refuses you without the picture. */
	Photograph
};

/**
 * A leg (ARCHITECTURE 4, 5, 6c): the map, the mission, the par time and time limit, the weather
 * it starts in, the conditions profile the car and the player sample along it, and the rivals'
 * fallback times. Checkpoints, the extraction zone and any photo subjects are placed actors in
 * the map; the map's AGTLegStart names the asset, or the run subsystem hands one over before
 * the level loads. DefaultLegs() is the tour's five legs: what Art/setup_m3_leg.bat and
 * Art/setup_m5_legs.bat write as DA_Leg_01..05 and what the headless tests build at runtime.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTLegDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FName LegId = TEXT("Leg01");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	int32 LegNumber = 1;

	/** The leg's map, as a long package path (/Game/GrandTour/Legs/L_Leg01). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FString MapPath;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg|Mission")
	EGTMissionType Mission = EGTMissionType::TimeTrial;

	/** The briefing's words for the leg, in the show's voice; one or two sentences. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg|Mission")
	FText MissionBrief;

	/** Photograph legs: what the subject is called ("spectacled bear"). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg|Mission")
	FString PhotoSubjectName;

	/** Photograph legs: pictures needed before the zone accepts you. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg|Mission", meta = (ClampMin = 1))
	int32 PhotosRequired = 1;

	/** A clean drive; rivals and the results screen compare against it. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg", meta = (ClampMin = 1))
	float ParTimeSeconds = 300.f;

	/** 0 = none. Past it a time trial is marked overtime; an endurance leg is a did-not-finish. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg", meta = (ClampMin = 0))
	float TimeLimitSeconds = 0.f;

	/** Weather the leg starts in; none = clear. A weather front in the map moves it from here. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	TObjectPtr<UGTWeatherStateDefinition> StartWeather;

	/** Fallback state name when StartWeather is not set (Clear, Overcast, Rain, Storm, Snow), for assets written without the weather ones. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FName StartWeatherName = TEXT("Clear");

	/** The conditions profile (ARCHITECTURE 6c). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	TArray<FGTConditionCurve> Conditions;

	/** Rival leg times in seconds: the fallback ranking when the leg is run outside a tour (the tour simulates its rivals instead). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	TArray<float> RivalTimesSeconds;

	/** Intensity of a condition tag at a leg progress, 0 if the tag is not in the profile. */
	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	float SampleCondition(FGameplayTag Tag, float Progress) const;

	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	bool HasCondition(FGameplayTag Tag) const;

	/** Rank 1..N+1 of a time against the fallback rivals (ties go to the player). */
	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	int32 RankForTime(float TimeSeconds) const;

	/** "Time trial", "Endurance", "Photograph". */
	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	static FString MissionName(EGTMissionType Type);

	/** One line of what the leg wants: "Clear 2 checkpoints and stop in the zone", "... inside 12:00", "Photograph the spectacled bear, then extract". */
	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	FString MissionObjective(int32 CheckpointCount) const;

	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	FString Describe() const;

	/** The tour's legs in order (five). */
	static int32 DefaultLegCount();

	/** Fills this leg with default leg Index (0-based) of the tour; Index 0 is Leg 01. */
	void ApplyDefault(int32 Index);

	/** Leg 01: the 1.2 km greybox time trial, par 300 s, limit 600 s, overcast, cold rising, dust in the middle, heat at the end, four rivals. */
	void ApplyDefaultLeg01() { ApplyDefault(0); }

	/** Asset name of default leg Index: DA_Leg_01... */
	static FString DefaultAssetName(int32 Index);

	/** Adds a condition with linear keys (progress, intensity) pairs. */
	void AddCondition(FGameplayTag Tag, std::initializer_list<TPair<float, float>> Keys);
};
