// LM1 housekeeping (docs/LIVING_MUD_PLAN.md LM1, item 3): Play In Editor at a fixed viewport size, for the drive check's
// frame-time profile. The level viewport's size is whatever the editor layout last was (951x257 on 2026-10-05, 1478x592
// on 2026-09-29), so a profile from it is not comparable run to run. Editor-only, called from
// Art/Unreal/check_live_mud_drive.py:
//   unreal.GTPlayWindowLibrary.request_play_in_new_window(1440, 900) -> bool

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"

#include "GTPlayWindowLibrary.generated.h"

UCLASS()
class UGTPlayWindowLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Requests a Play In Editor session in a new window whose viewport is Width x Height (the editor's own new-window
	 * path, started on the next editor tick), from a copy of the play settings so the editor's own preferences are not
	 * edited. False when there is no editor or a session is already running.
	 */
	UFUNCTION(BlueprintCallable, Category = "GT|Test")
	static bool RequestPlayInNewWindow(int32 Width, int32 Height);
};
