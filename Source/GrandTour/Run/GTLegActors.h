#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GTLegActors.generated.h"

class AGTCarPawn;
class UBoxComponent;
class UGTLegDefinition;
class UStaticMeshComponent;

/** Shared by the leg volumes: a query-only box plus a flat greybox marker slab on the ground under it. */
UCLASS(Abstract)
class GRANDTOUR_API AGTLegVolume : public AActor
{
	GENERATED_BODY()

public:
	AGTLegVolume();

	virtual void BeginPlay() override;

	/** True when a world point is inside the box (oriented test; no overlap events needed for the vehicle mesh). */
	UFUNCTION(BlueprintPure, Category = "GT|Leg")
	bool ContainsPoint(const FVector& WorldLocation) const;

	/** Half extents, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Leg")
	FVector Extent = FVector(300.f, 1000.f, 400.f);

	UPROPERTY(EditAnywhere, Category = "GT|Leg|Greybox")
	FLinearColor MarkerColour = FLinearColor(0.9f, 0.7f, 0.1f);

	UPROPERTY(EditAnywhere, Category = "GT|Leg|Greybox")
	bool bBuildMarker = true;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	TObjectPtr<UBoxComponent> Box;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	TObjectPtr<UStaticMeshComponent> Marker;
};

/**
 * An ordered checkpoint (ARCHITECTURE 5, AGTRunGameMode). The run game state clears it when the
 * player's car drives through it and it is the next one in order; earlier ones must be cleared
 * first, later ones are ignored until then. Greybox: a slab across the road and two posts.
 */
UCLASS()
class GRANDTOUR_API AGTCheckpoint : public AGTLegVolume
{
	GENERATED_BODY()

public:
	AGTCheckpoint();

	/** 1-based order along the leg. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Leg")
	int32 Index = 1;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Leg")
	bool bCleared = false;
};

/**
 * Where the leg ends: with every checkpoint cleared, stop the car inside it for HoldSeconds and
 * the leg is complete (the game mode builds the result and shows the results screen). Driving
 * through does nothing; the HUD says why when the checkpoints are not done.
 */
UCLASS()
class GRANDTOUR_API AGTExtractionZone : public AGTLegVolume
{
	GENERATED_BODY()

public:
	AGTExtractionZone();

	/** Seconds the car must sit still inside the zone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Leg")
	float HoldSeconds = 2.f;

	/** The car counts as stopped below this speed (cm/s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "GT|Leg")
	float StopSpeed = 100.f;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Leg")
	float HoldProgress = 0.f;
};

/** Names the leg a map runs (the run subsystem's pending leg wins when set). Place one per leg map, at the start. */
UCLASS()
class GRANDTOUR_API AGTLegStart : public AActor
{
	GENERATED_BODY()

public:
	AGTLegStart();

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	TObjectPtr<UGTLegDefinition> Leg;

	/** Asset path used when Leg is unset (/Game/GrandTour/Legs/DA_Leg_01), so a script-built map needs no object reference. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "GT|Leg")
	FString LegAssetPath;
};
