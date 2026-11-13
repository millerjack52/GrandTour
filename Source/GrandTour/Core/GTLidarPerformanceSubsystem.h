#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GTLidarPerformanceSubsystem.generated.h"

/** Use the measured LiDAR play preset for both PIE and standalone launches. */
UCLASS()
class GRANDTOUR_API UGTLidarPerformanceSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(const EWorldType::Type Type) const override;
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
private:
    bool bOwnsProfile=false;
};
