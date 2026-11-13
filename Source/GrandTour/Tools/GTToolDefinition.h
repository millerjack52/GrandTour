#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "GTToolDefinition.generated.h"

/**
 * A hand tool (ARCHITECTURE 4): the tag it grants (Tool.Cut, Tool.Pry, Tool.Repair), how it
 * scales a node's harvest time, and a greybox box to hold until the tool meshes exist (M6).
 * Assets live under /Game/GrandTour/Tools (Art/setup_m2_character.bat writes DA_Tool_*); when
 * none are found the character builds the three defaults from DefaultTools() at runtime.
 */
UCLASS(BlueprintType)
class GRANDTOUR_API UGTToolDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tool")
	FName ToolId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tool")
	FText DisplayName;

	/** Requirement this tool satisfies on nodes, wrecks and repairs. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tool")
	FGameplayTag GrantedTag;

	/** Multiplies the target's hold time (a better cutter cuts faster). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tool", meta = (ClampMin = 0.1, ClampMax = 5))
	float UseTimeScale = 1.f;

	/** Greybox: box dimensions (cm) shown in the hand. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tool|Greybox")
	FVector GreyboxSize = FVector(30.f, 6.f, 6.f);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Tool|Greybox")
	FLinearColor GreyboxColour = FLinearColor(0.6f, 0.6f, 0.6f);

	bool GrantsTag(const FGameplayTag& Tag) const { return Tag.IsValid() && GrantedTag.MatchesTag(Tag); }

	/** The three Tier 1 tools with their defaults, in the order they cycle: cutter, pry bar, repair kit. */
	struct FDefault
	{
		const TCHAR* AssetName;
		const TCHAR* Id;
		const TCHAR* Name;
		const TCHAR* Tag;
		float UseTimeScale;
		FVector Size;
		FLinearColor Colour;
	};
	static TArrayView<const FDefault> DefaultTools();

	/** Fills this definition from a default row (used by the runtime fallback and the asset writer). */
	void ApplyDefault(const FDefault& Row);
};
