#include "Environment/GTEnvironmentComponent.h"

#include "Core/GTGameplayTags.h"
#include "Run/GTLegDefinition.h"
#include "Vehicle/GTConditionComponent.h"
#include "Vehicle/GTVehicleTuning.h"

UGTEnvironmentComponent::UGTEnvironmentComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick before the tuning
}

float UGTEnvironmentComponent::Resisted(FGameplayTag Tag, float Intensity) const
{
	const float* R = Resistance.Find(Tag);
	return FMath::Clamp(Intensity * (1.f - (R ? FMath::Clamp(*R, 0.f, 1.f) : 0.f)), 0.f, 1.f);
}

EGTConditionStage UGTEnvironmentComponent::StageFor(float Level) const
{
	if (Level >= DamageLevel)
	{
		return EGTConditionStage::Damage;
	}
	if (Level >= WarningLevel)
	{
		return EGTConditionStage::Warning;
	}
	if (Level >= PerformanceLevel)
	{
		return EGTConditionStage::Performance;
	}
	return EGTConditionStage::None;
}

void UGTEnvironmentComponent::Update(float DeltaSeconds, const UGTLegDefinition* Leg, float InProgress, float ThrottleInput, float SpeedCmPerSec, UGTConditionComponent* Condition)
{
	Progress = InProgress;
	bHasProfile = Leg && Leg->Conditions.Num() > 0;
	HeatIntensity = Leg ? Resisted(GTTags::Env_Heat, Leg->SampleCondition(GTTags::Env_Heat, Progress)) : 0.f;
	DustIntensity = Leg ? Resisted(GTTags::Env_Dust, Leg->SampleCondition(GTTags::Env_Dust, Progress)) : 0.f;
	Cold = Leg ? Resisted(GTTags::Env_Cold, Leg->SampleCondition(GTTags::Env_Cold, Progress)) : 0.f;

	// Heat: sources are the environment times engine load; the sink is rest and a cool environment.
	const float Load = FMath::Clamp(ThrottleInput, 0.f, 1.f);
	const float HeatIn = HeatIntensity * (0.3f + 0.7f * Load) * HeatRate;
	const float HeatOut = CoolRate * (1.f - HeatIntensity) * (1.f - 0.5f * Load);
	Heat = FMath::Clamp(Heat + (HeatIn - HeatOut) * DeltaSeconds, 0.f, 1.f);

	// Dust: the filter clogs with distance driven through it and stays clogged until the base.
	Clog = FMath::Clamp(Clog + DustIntensity * ClogPerKm * (FMath::Abs(SpeedCmPerSec) * DeltaSeconds / 100000.f), 0.f, 1.f);

	// Damage only in the last stage, slowly: the warning stage is the readable window.
	if (Condition)
	{
		float Damage = 0.f;
		if (StageFor(Heat) == EGTConditionStage::Damage)
		{
			Damage += HeatDamagePerSecond * DeltaSeconds;
		}
		if (StageFor(Clog) == EGTConditionStage::Damage)
		{
			Damage += ClogDamagePerSecond * DeltaSeconds;
		}
		if (Damage > 0.f)
		{
			Condition->DamagePart(EGTCarPart::Engine, Damage);
			TotalConditionDamage += Damage;
		}
	}
}

void UGTEnvironmentComponent::ModifyTuning(FGTVehicleTuning& Tuning) const
{
	float Scale = 1.f;
	if (Heat >= PerformanceLevel)
	{
		Scale *= 1.f - HeatTorqueLoss * FMath::Clamp((Heat - PerformanceLevel) / FMath::Max(0.01f, 1.f - PerformanceLevel), 0.f, 1.f);
	}
	if (Clog >= PerformanceLevel)
	{
		Scale *= 1.f - ClogTorqueLoss * FMath::Clamp((Clog - PerformanceLevel) / FMath::Max(0.01f, 1.f - PerformanceLevel), 0.f, 1.f);
	}
	if (Cold >= PerformanceLevel)
	{
		Scale *= 1.f - ColdTorqueLoss * Cold;
	}
	Tuning.TorqueScale *= Scale;
}

float UGTEnvironmentComponent::GetIntensity(FGameplayTag Tag) const
{
	if (Tag == GTTags::Env_Heat) { return HeatIntensity; }
	if (Tag == GTTags::Env_Dust) { return DustIntensity; }
	if (Tag == GTTags::Env_Cold) { return Cold; }
	return 0.f;
}

EGTConditionStage UGTEnvironmentComponent::GetStage(FGameplayTag Tag) const
{
	if (Tag == GTTags::Env_Heat) { return StageFor(Heat); }
	if (Tag == GTTags::Env_Dust) { return StageFor(Clog); }
	if (Tag == GTTags::Env_Cold) { return FMath::Min(StageFor(Cold), EGTConditionStage::Warning); }   // cold never damages the car
	return EGTConditionStage::None;
}

EGTConditionStage UGTEnvironmentComponent::GetWorstStage() const
{
	return FMath::Max(FMath::Max(GetStage(GTTags::Env_Heat), GetStage(GTTags::Env_Dust)), GetStage(GTTags::Env_Cold));
}

const TCHAR* UGTEnvironmentComponent::StageName(EGTConditionStage Stage)
{
	switch (Stage)
	{
	case EGTConditionStage::Performance: return TEXT("performance");
	case EGTConditionStage::Warning:     return TEXT("warning");
	case EGTConditionStage::Damage:      return TEXT("damage");
	default:                             return TEXT("none");
	}
}

FString UGTEnvironmentComponent::Describe() const
{
	return FString::Printf(TEXT("progress=%.2f heat=%.2f(%s, env %.2f) clog=%.2f(%s, env %.2f) cold=%.2f(%s) damage=%.3f"),
		Progress, Heat, StageName(StageFor(Heat)), HeatIntensity, Clog, StageName(StageFor(Clog)), DustIntensity, Cold, StageName(GetStage(GTTags::Env_Cold)), TotalConditionDamage);
}
