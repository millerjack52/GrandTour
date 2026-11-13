#include "Terrain/GTWaterField.h"
#include "HAL/PlatformTime.h"

void FGTWaterField::AddRiverDetail(FVector2D XY,float RadiusCm,float Foam,float Sediment)
{
	if(!bRiverVisuals || RiverDetail.Num()!=NumCells() || RadiusCm<=0) return;
	const FVector2D P=ToFieldCm(XY)/CellCm;
	const float R=RadiusCm/CellCm;
	for(int32 Y=FMath::Max(0,FMath::FloorToInt(P.Y-R));Y<=FMath::Min(SizeY-1,FMath::CeilToInt(P.Y+R));++Y)
	for(int32 X=FMath::Max(0,FMath::FloorToInt(P.X-R));X<=FMath::Min(SizeX-1,FMath::CeilToInt(P.X+R));++X)
	{
		const int32 I=Y*SizeX+X;if(RiverDepthM[I]<=0)continue;
		const float W=FMath::Max(0.f,1.f-FVector2D(X+.5-P.X,Y+.5-P.Y).SizeSquared()/(R*R));
		RiverDetail[I].X=FMath::Clamp(RiverDetail[I].X+Foam*W,0.f,1.f);
		RiverDetail[I].Y=FMath::Clamp(RiverDetail[I].Y+Sediment*W,0.f,1.f);
	}
}

void FGTWaterField::StepRiverDetail(float DeltaSeconds)
{
	RiverDetailMs=0;
	if(!bRiverVisuals || RiverDetail.Num()!=NumCells() || !HasRiverReference()) return;
	RiverDetailCarry+=FMath::Max(0.f,DeltaSeconds);
	if(RiverDetailCarry<1.f/30) return;
	// Cosmetic work is capped independently of physics. A long hitch advances at most 0.1 s.
	const float Dt=FMath::Min(RiverDetailCarry,.1f);RiverDetailCarry=0;
	const double Start=FPlatformTime::Seconds();
	const float DecayFoam=FMath::Exp(-Dt/4.f),DecaySilt=FMath::Exp(-Dt/12.f);
	const float CellM=CellCm*.01f;
	for(int32 I:RiverWetCells)
	{
		const int32 X=I%SizeX,Y=I/SizeX;
		// Semi-Lagrangian transport: bounded concentrations, no fluid mass or force writes.
		// Use the same actual velocity as the rendered water; cap only cosmetic backtracing.
		const float U=FMath::Clamp(VelXMps[I],-3.f,3.f),V=FMath::Clamp(VelYMps[I],-3.f,3.f);
		const float PX=X-U*Dt/CellM,PY=Y-V*Dt/CellM;
		const int32 LX=FMath::FloorToInt(PX),LY=FMath::FloorToInt(PY);
		const float FX=PX-LX,FY=PY-LY;
		FVector2f C=FVector2f::ZeroVector;
		for(int32 DY=0;DY<2;++DY)for(int32 DX=0;DX<2;++DX)
		{
			const int32 NX=LX+DX,NY=LY+DY;
			if(NX<0 || NY<0 || NX>=SizeX || NY>=SizeY)continue;
			const int32 J=NY*SizeX+NX;
			if(RiverDepthM[J]>0) C+=RiverDetail[J]*((DX?FX:1-FX)*(DY?FY:1-FY));
		}
		const float Change=FMath::Abs(LidM[I]-RiverDetailLid[I]);
		RiverDetailLid[I]=LidM[I];
		// Moving occupancy stirs shallow sediment. A stationary immersed solid in a current
		// makes a small foam source; calm undisturbed water generates neither field.
		const float Speed=FMath::Sqrt(U*U+V*V);
		const float FoamSource=Change*2.5f+FMath::Min(LidM[I],.15f)*Speed*Dt*.45f;
		const float SiltSource=Change*4.f*FMath::Clamp(1.f-RiverDepthM[I]/1.2f,0.f,1.f);
		const float Edge=FMath::Clamp(RiverEdgeCells[I]*CellM/3.f,0.f,1.f);
		RiverDetailNext[I]=FVector2f(FMath::Clamp(C.X*DecayFoam+FoamSource,0.f,1.f),FMath::Clamp(C.Y*DecaySilt+SiltSource,0.f,1.f))*Edge;
	}
	Swap(RiverDetail,RiverDetailNext);
	RiverDetailMs=(FPlatformTime::Seconds()-Start)*1000;
}
