#pragma once

#include "CoreMinimal.h"

/** An optional conversion, independent of engine/gearing packages. Missing old-save entries are Factory. */
namespace GTDriveLayout
{
    inline float NormalizeAWDFrontShare(float Share)
    {
        return FMath::IsFinite(Share) ? FMath::Clamp(FMath::RoundToFloat(FMath::Clamp(Share,.1f,.9f)*20.f)/20.f,.1f,.9f) : .5f;
    }
    inline const TCHAR* Id(int32 Choice)
    {
        static const TCHAR* Ids[]={TEXT("Part.DriveFactory"),TEXT("Part.DriveFWD"),TEXT("Part.DriveRWD"),TEXT("Part.DriveAWD")};
        return Ids[FMath::Clamp(Choice,0,3)];
    }
    inline int32 Index(FName Part)
    {
        for(int32 I=1;I<4;++I) if(Part==FName(Id(I))) return I;
        return 0;
    }
    inline float FrontShare(int32 Choice,float Factory)
    {
        return Choice==1 ? 1.f : Choice==2 ? 0.f : Choice==3 ? .5f : FMath::Clamp(Factory,0.f,1.f);
    }
    inline const TCHAR* Name(int32 Choice)
    {
        static const TCHAR* Names[]={TEXT("Factory layout"),TEXT("FWD / front-wheel drive"),TEXT("RWD / rear-wheel drive"),TEXT("AWD / all-wheel drive")};
        return Names[FMath::Clamp(Choice,0,3)];
    }
}
