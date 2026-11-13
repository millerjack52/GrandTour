#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GTLandscapeSurfaceSetupLibrary.generated.h"

class UMaterial;
class UMaterialExpression;
class UTexture2D;
class AGTLandscapeSurface;
class ALandscape;
class AGTProceduralGround;

UCLASS()
class UGTLandscapeSurfaceSetupLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Raise a bounded shallow bank into an irregular oval. Uses the existing relief
     * tile collision/query path; leaves landscape source heights and roads outside the collar intact.
     * Returns changed tile count, or -1 if validation/budget checks fail before mutation. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Water Authoring")
    static int32 RoundShallowPondBank(AGTProceduralGround* Author, FVector Centre, FVector2D RadiusCm, float CollarCm=2050.f);
    /** Replace the derived LiDAR terrain from a 2017-square R16, with collision and readback verification. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|LiDAR Authoring")
    static bool ImportLidarAuthoringHeights(ALandscape* Landscape, const FString& Filename);
    /** Expression returns (delta world cm + 50) / 65. Nanite magnitude is LOCAL units, before scale.
     * Use only uniform landscape transforms; nonuniform landscape displacement has an engine defect. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ConnectDisplacement(UMaterial* Material, UMaterialExpression* Expression, int32 OutputIndex = 0, float UniformLandscapeScale = 50.f);
    /** Creates only a new 31.5 m flat landscape; refuses a world containing any landscape. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface", meta=(WorldContext="WorldContext"))
    static ALandscape* CreatePrototypeLandscape(UObject* WorldContext, UMaterial* Material);
    /** Adds a separate 63m study tile, with real heightfield collision. Heights: 127x127 world cm. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface", meta=(WorldContext="WorldContext"))
    static ALandscape* CreateStudyLandscape(UObject* WorldContext,UMaterial* Material,FVector Origin,const TArray<float>& HeightsCm);
    /** R8 thickness / 50 cm, G8 water-table depth / 50 cm, B8 gravel, A8 softness; no sRGB. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ImportPaint(AGTLandscapeSurface* Surface, UTexture2D* Texture);
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ImportMaterialAtlas(AGTLandscapeSurface* Surface, UTexture2D* Texture);
    /** CL2 clay atlas (R clay weight, G orange cut face, B bush slurry), same origin and span as the material atlas. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ImportClayAtlas(AGTLandscapeSurface* Surface, UTexture2D* Texture);
    /** Import unchanged scan heights into the CPU rest field. Only the explicitly supplied actor is edited. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ImportRestHeights(AGTLandscapeSurface* Surface, UTexture2D* Mud, UTexture2D* Clay);
    /** Unique world map: RG stores a 16-bit unsigned height mapped from -50 to +15 cm. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ImportWorldRestHeights(AGTLandscapeSurface* Surface, UTexture2D* Texture);
    /** Periodic physical rest detail. Same RG centimetre encoding as the world rest map. */
    UFUNCTION(BlueprintCallable, Category="GrandTour|Landscape Surface")
    static bool ImportMudRelief(AGTLandscapeSurface* Surface, UTexture2D* Texture, float TileCm = 12800.f);
};
