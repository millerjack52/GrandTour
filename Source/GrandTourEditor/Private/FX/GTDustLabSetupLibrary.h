#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GTDustLabSetupLibrary.generated.h"
class UMaterialInterface;

UCLASS()
class UGTDustLabSetupLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="GrandTour|Dust Lab")
    static FString BuildDust(const FString& AssetPath, const FString& AssetName, UMaterialInterface* Material);
    UFUNCTION(BlueprintCallable, Category="GrandTour|Dust Lab")
    static FString BuildMudFlick(const FString& AssetPath, const FString& AssetName, UMaterialInterface* Material);
};
