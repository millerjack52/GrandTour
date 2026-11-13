#pragma once
#include "CoreMinimal.h"
/** Build 9640861: 0x1408f9476..0x1408f94cf and GRASS Plants_009 VS. */
namespace GTMudRunnerGrass
{
inline bool RemovedByContact(FVector2D InstanceCm,FVector2D ContactCm)
{ return FVector2D::Distance(InstanceCm,ContactCm)<=64.; }
inline uint8 Remove(uint8 Packed) { return Packed|0xf0; }
inline bool Hidden(uint8 Packed) { return FMath::FloorToInt(Packed/255.f*16.f)>14.9705887f; }
// Shader-space metres: preserve the source height envelope, direction decoding
// and 0.8 downward displacement. The host supplies the deflector texture input.
inline FVector Deflect(float HeightM,FVector4 Deflector)
{
    const float Root=FMath::Clamp((HeightM-.1f)*2.5f,0.f,1.f);
    const float Strength=Deflector.W*FMath::Clamp(HeightM-Deflector.Z*4.f,0.f,1.f)*Root;
    return FVector((Deflector.X-.5f)*2.f*Strength,(Deflector.Y-.5f)*2.f*Strength,-.8f*Strength);
}
}
