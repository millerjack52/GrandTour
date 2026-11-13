#include "Terrain/GTWaterDomain.h"
#include "Misc/FileHelper.h"

bool UGTWaterDomain::SampleEnvelope(const FVector2D& XY,float Margin,float& S,float& D,FVector2D& V) const
{
    if(Sample(XY,S,D,V))return true;
    for(const UGTWaterDomain* Child:RoadPatches)
        if(Child && Child!=this && Child->SampleEnvelope(XY,Margin,S,D,V))return true;
    if(CellCm<=0 || Samples.Num()!=int64(SizeX)*SizeY*4)return false;
    const FVector2D Q=(XY-OriginCm)/CellCm-FVector2D(.5,.5);
    const int32 Radius=FMath::Clamp(FMath::CeilToInt(Margin/CellCm),0,8);
    const int32 CX=FMath::RoundToInt(Q.X),CY=FMath::RoundToInt(Q.Y);
    double Best=FMath::Square(double(Margin));int32 Found=INDEX_NONE;
    for(int32 Y=FMath::Max(0,CY-Radius);Y<=FMath::Min(SizeY-1,CY+Radius);++Y)
        for(int32 X=FMath::Max(0,CX-Radius);X<=FMath::Min(SizeX-1,CX+Radius);++X)
        {
            const int32 I=(Y*SizeX+X)*4;
            const double Dist=FVector2D::DistSquared(Q,FVector2D(X,Y))*CellCm*CellCm;
            if(Samples[I+1]>.005f && Dist<=Best){Best=Dist;Found=I;}
        }
    if(Found==INDEX_NONE)return false;
    S=Samples[Found];D=Samples[Found+1];V=FVector2D(Samples[Found+2],Samples[Found+3]);return true;
}

bool UGTWaterDomain::SetChildDomains(const TArray<UGTWaterDomain*>& Domains)
{
#if WITH_EDITOR
    TSet<const UGTWaterDomain*> Visiting,Done;
    TFunction<bool(const UGTWaterDomain*)> Valid=[&](const UGTWaterDomain* D)
    {
        if(!D||D==this||Visiting.Contains(D))return false;
        if(Done.Contains(D))return true;
        Visiting.Add(D);
        for(const UGTWaterDomain* Child:D->RoadPatches)if(!Valid(Child))return false;
        Visiting.Remove(D);Done.Add(D);return true;
    };
    for(const UGTWaterDomain* D:Domains)if(!Valid(D))return false;
    Modify();RoadPatches.Reset();
    for(UGTWaterDomain* D:Domains)RoadPatches.Add(D);
    MarkPackageDirty();return true;
#else
    return false;
#endif
}

bool UGTWaterDomain::ImportBake(const FString& Filename)
{
#if WITH_EDITOR
	TArray<uint8> B;
	if(!FFileHelper::LoadFileToArray(B,*Filename) || B.Num()<32) return false;
	int32 H[5];float M[3];
	FMemory::Memcpy(H,B.GetData(),20); FMemory::Memcpy(M,B.GetData()+20,12);
	const int64 N=int64(H[1])*H[2], L=int64(H[3])*H[4];
	if(H[0]!=0x47545744 || H[1]<2 || H[2]<2 || N>4000000 || L<1 || L>4000000 || B.Num()!=32+N*16+L || M[2]<25) return false;
	TArray<float> Data;Data.SetNumUninitialized(N*4);FMemory::Memcpy(Data.GetData(),B.GetData()+32,N*16);
	for(float V:Data) if(!FMath::IsFinite(V)) return false;
	Modify();SizeX=H[1];SizeY=H[2];LakeSizeX=H[3];LakeSizeY=H[4];OriginCm=FVector2D(M[0],M[1]);CellCm=M[2];Samples=MoveTemp(Data);
	LakeMask.SetNumUninitialized(L);FMemory::Memcpy(LakeMask.GetData(),B.GetData()+32+N*16,L);
	MarkPackageDirty();return true;
#else
	return false;
#endif
}

bool UGTWaterDomain::Sample(const FVector2D& XY,float& Surface,float& Depth,FVector2D& Velocity) const
{
    for(const UGTWaterDomain* Patch:RoadPatches)if(Patch&&Patch!=this&&Patch->Sample(XY,Surface,Depth,Velocity))return true;
	Surface=LakeLevelCm;Depth=0;Velocity=FVector2D::ZeroVector;
	if(CellCm<=0 || SizeX<2 || SizeY<2 || Samples.Num()!=int64(SizeX)*SizeY*4) return false;
	const FVector2D Q=(XY-OriginCm)/CellCm-FVector2D(.5,.5);
	if(Q.X>=0 && Q.Y>=0 && Q.X<=SizeX-1 && Q.Y<=SizeY-1)
	{
		const int32 X=FMath::Min(FMath::FloorToInt(Q.X),SizeX-2),Y=FMath::Min(FMath::FloorToInt(Q.Y),SizeY-2);
		const float FX=Q.X-X,FY=Q.Y-Y;
		const int32 Indices[4]={Y*SizeX+X,Y*SizeX+X+1,(Y+1)*SizeX+X,(Y+1)*SizeX+X+1};
		const float Weights[4]={(1-FX)*(1-FY),FX*(1-FY),(1-FX)*FY,FX*FY};
		float Sum=0,S=0,H=0;FVector2D V=FVector2D::ZeroVector;
		for(int32 J=0;J<4;++J)
		{
			const int32 I=Indices[J]*4;const float W=Samples[I+1]>.005f?Weights[J]:0;
			Sum+=W;S+=W*Samples[I];H+=W*FMath::Max(0.f,Samples[I+1]);V+=W*FVector2D(Samples[I+2],Samples[I+3]);
		}
		if(Sum>0) Surface=S/Sum;
		if(Sum<.5f) return false;
		Depth=H/Sum;Velocity=V/Sum;return true;
	}
	const FVector2D UV=(XY-LakeMinCm)/LakeSpanCm;
	if(UV.X<0 || UV.Y<0 || UV.X>=1 || UV.Y>=1 || LakeSizeX<1 || LakeSizeY<1 || LakeMask.Num()!=int64(LakeSizeX)*LakeSizeY) return false;
	const int32 X=FMath::Clamp(int32(UV.X*LakeSizeX),0,LakeSizeX-1),Y=FMath::Clamp(int32(UV.Y*LakeSizeY),0,LakeSizeY-1);
	if(LakeMask[Y*LakeSizeX+X]<128) return false;
	Depth=1.5f;return true; // Effective surface-wave depth only, not claimed lake bathymetry.
}
