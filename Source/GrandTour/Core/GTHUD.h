#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "GTHUD.generated.h"

class AGTCarPawn;
class AGTPlayerCharacter;
class AGTRunGameState;

/**
 * Greybox HUD drawn with the canvas, so nothing has to be authored headless: crosshair, the
 * interaction prompt and hold bar, the current tool, the exposure meter, the inventory and boot
 * lists, the winch state and the key hints; from M3 the leg timer and next objective, the
 * weather line, hazard and condition warnings, and the results screen at extraction.
 * UMG/CommonUI replaces it in M7 (ARCHITECTURE 2, UI).
 */
UCLASS()
class GRANDTOUR_API AGTHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

private:
	void DrawBar(float X, float Y, float Width, float Height, float Fraction, const FLinearColor& Colour);
	void DrawLabel(const FString& Text, float X, float Y, const FLinearColor& Colour = FLinearColor::White, float Scale = 1.f);
	void DrawLeg(const AGTRunGameState* RunState, float W);
	void DrawWeather(float Y);
	void DrawConditions(const AGTCarPawn* Car, float W, float& Y);
	void DrawResults(const AGTRunGameState* RunState, float W, float H);
	void DrawCredits(float W);
protected:
	void DrawStation(const AGTPlayerCharacter* Character, float W, float H);
};
