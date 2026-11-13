#pragma once
#include "Terrain/GTWaterField.h"
#include "HAL/PlatformTime.h"

/** Cosmetic concentration only. Reads the shared pond; never edits water or soil. */
struct FGTMudContactFoam
{
    TArray<float> Foam, Next, PreviousLid;
    float Carry=0;
    double MsSum=0, MsPeak=0;
    int32 Steps=0;

    void Reset(int32 Count)
    {
        Foam.Init(0,Count);Next=Foam;PreviousLid=Foam;Carry=0;MsSum=MsPeak=0;Steps=0;
    }

    bool Step(const FGTWaterField& F,float Dt)
    {
        if(!F.IsValid())return false;
        if(Foam.Num()!=F.NumCells())Reset(F.NumCells());
        Carry+=FMath::Max(0.f,Dt);
        if(Carry<1.f/30)return false;
        const double Start=FPlatformTime::Seconds();
        Dt=FMath::Min(Carry,.1f);Carry=0;
        const float Decay=FMath::Exp(-Dt/2.8f),CellM=F.CellCm*.01f;
        for(int32 I=0;I<F.NumCells();++I)
        {
            Next[I]=0;
            if(F.DepthM[I]<=F.DryDepthM)continue;
            const int32 X=I%F.SizeX,Y=I/F.SizeX;
            const float U=FMath::Clamp(F.VelXMps[I],-2.f,2.f),V=FMath::Clamp(F.VelYMps[I],-2.f,2.f);
            const float PX=X-U*Dt/CellM,PY=Y-V*Dt/CellM;
            const int32 LX=FMath::FloorToInt(PX),LY=FMath::FloorToInt(PY);
            const float FX=PX-LX,FY=PY-LY;
            float C=0,Source=0;
            for(int32 DY=0;DY<2;++DY)for(int32 DX=0;DX<2;++DX)
            {
                const int32 NX=LX+DX,NY=LY+DY;
                if(NX<0||NY<0||NX>=F.SizeX||NY>=F.SizeY)continue;
                const int32 J=NY*F.SizeX+NX;
                if(F.DepthM[J]>F.DryDepthM)C+=Foam[J]*(DX?FX:1-FX)*(DY?FY:1-FY);
            }
            // Neighbouring occupancy changes aerate the exposed water beside a tyre,
            // not just the hidden pixels underneath it. Quiescent lids generate none.
            for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)
            {
                const int32 NX=X+DX,NY=Y+DY;
                if(NX<0||NY<0||NX>=F.SizeX||NY>=F.SizeY)continue;
                const int32 J=NY*F.SizeX+NX;
                const float Change=FMath::Abs(F.LidM[J]-PreviousLid[J]);
                const float Edge=FMath::Max(0.f,F.LidM[J]-F.LidM[I]);
                Source=FMath::Max(Source,(Change*9.f+Edge*FMath::Sqrt(U*U+V*V)*Dt*2.f)/(1+DX*DX+DY*DY));
            }
            Next[I]=FMath::Clamp(C*Decay+Source,0.f,1.f);
        }
        PreviousLid=F.LidM;Swap(Foam,Next);
        const double Ms=(FPlatformTime::Seconds()-Start)*1000;
        MsSum+=Ms;MsPeak=FMath::Max(MsPeak,Ms);++Steps;
        return true;
    }
};
