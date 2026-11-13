#include "Terrain/GTEditorReconstruction.h"

namespace GTEditorReconstruction
{
FVector2f RoadUV(float S,float Across,float Width,float Aspect)
{return FVector2f(S/(Width*Aspect),.5f+Across/Width);}
float RoadOffsetCm(float Red,float Alpha){return (Red-.5f)*Alpha*384.f;}
float SampleRoadRed(const TArray<uint8>& Pixels,int32 W,int32 H,FVector2f UV)
{
    if(W<1||H<1||Pixels.Num()!=W*H*4)return .5f;
    const float X=(UV.X-FMath::FloorToFloat(UV.X))*W-.5f,Y=(UV.Y-FMath::FloorToFloat(UV.Y))*H-.5f;
    const int32 I=FMath::FloorToInt(X),J=FMath::FloorToInt(Y);
    auto Read=[&](int32 A,int32 B){return Pixels[(((B%H+H)%H)*W+(A%W+W)%W)*4+2]/255.f;};
    return FMath::Lerp(FMath::Lerp(Read(I,J),Read(I+1,J),X-I),FMath::Lerp(Read(I,J+1),Read(I+1,J+1),X-I),Y-J);
}
bool FCurve::Build(const TArray<float>& Knots,const TArray<float>& Values)
{
    X=Knots;Y=Values;B.Reset();C.Reset();D.Reset();
    const int32 N=X.Num()-1;
    if(N<1 || Y.Num()!=X.Num())return false;
    TArray<float> H,Q,A,V;H.SetNum(N);Q.SetNum(N);
    for(int32 I=0;I<N;++I)
    {
        if(!FMath::IsFinite(X[I]) || !FMath::IsFinite(Y[I]))return false;
        H[I]=X[I+1]-X[I];if(H[I]<=.00001f)return false;
        Q[I]=(Y[I+1]-Y[I])/H[I];
    }
    if(!FMath::IsFinite(X.Last()) || !FMath::IsFinite(Y.Last()))return false;
    A.Init(0,N);V.Init(0,N);B.Init(0,N);C.Init(0,N);D.Init(0,N);
    if(N==1){B[0]=Q[0];return true;}
    A[0]=-H[1]/((H[1]+H[0])*2.f);
    V[0]=((Q[1]-Q[0])*1.5f)/(H[0]+H[1]);
    for(int32 I=1;I<N-1;++I)
    {
        const float Den=(H[I]+H[I+1])*2.f+H[I]*A[I-1];
        A[I]=-H[I+1]/Den;
        V[I]=((Q[I+1]*3.f-Q[I]*3.f)-H[I]*V[I-1])/Den;
    }
    for(int32 I=N-2;I>=0;--I)C[I]=A[I]*C[I+1]+V[I];
    D[0]=C[0]/(H[0]*3.f);B[0]=(C[0]*2.f*H[0])/3.f+Q[0];
    for(int32 I=1;I<N;++I)
    {D[I]=(C[I]-C[I-1])/(H[I]*3.f);B[I]=(C[I]*2.f*H[I]+H[I]*C[I-1])/3.f+Q[I];}
    return true;
}
float FCurve::At(float T) const
{
    if(B.IsEmpty())return 0;
    int32 Lo=0,Hi=X.Num();
    while(Lo<Hi){const int32 Mid=(Lo+Hi)/2;if(X[Mid]<T)Lo=Mid+1;else Hi=Mid;}
    const int32 I=FMath::Clamp(Lo-1,0,B.Num()-1);
    const float Dt=T-X[I+1],TT=Dt*Dt;
    return ((Dt*B[I]+Y[I+1])+TT*C[I])+(TT*Dt)*D[I];
}
float FCurve::Derivative(float T) const
{
    if(B.IsEmpty())return 0;
    int32 Lo=0,Hi=X.Num();while(Lo<Hi){const int32 Mid=(Lo+Hi)/2;if(X[Mid]<T)Lo=Mid+1;else Hi=Mid;}
    const int32 I=FMath::Clamp(Lo-1,0,B.Num()-1);const float Dt=T-X[I+1];
    return (C[I]*2.f*Dt+B[I])+D[I]*3.f*(Dt*Dt);
}
FPatternBank Patterns(int32 Budget,uint32 Seed)
{
    FRandom Random(Seed);FPatternBank Bank;Bank.SetNum(16);
    for(auto& Points:Bank)for(int32 I=0;I<FMath::Clamp(Budget,0,800)/4;++I)
    {
        float BestScore=MAX_flt;FVector2f Best=FVector2f::ZeroVector;bool Found=false;
        for(int32 Trial=0;Trial<FMath::Min(2*Points.Num(),3)+1;++Trial)
        {
            const float Z=(Random.Unit()-.5f)*8.f,X=(Random.Unit()-.5f)*8.f;
            const float Radial=X*X*.005f+Z*Z*.005f;float Score=0;
            for(auto P:Points){const float DX=X-P.X,DZ=Z-P.Y;Score=(8.f/(DZ*DZ+DX*DX)+Score)+Radial;}
            if(Score<BestScore){BestScore=Score;Best=FVector2f(X,Z);Found=true;}
        }
        if(Found)Points.Add(Best);
    }
    return Bank;
}
bool Density(float Effective,float Minimum,float Multiplier,float Attenuation,FRandom& Random)
{
    const float Numerator=(Effective-Minimum)*Multiplier*Attenuation;
    if(Numerator<.0001f)return false;
    return Random.Unit()<=Numerator/(1.f-Minimum);
}
float Scale(float Green,float MinMap,float MaxMap,float MinSize,float MaxSize,float Jitter,FRandom& Random)
{
    const float Delta=MaxMap-MinMap;
    const float T=FMath::Clamp(Delta>.0001f?(Green-MinMap)/Delta:MinMap,0.f,1.f);
    return FMath::Clamp((1.f-T)*MinSize+T*MaxSize+(Random.Unit()-.5f)*Jitter,.25f,4.f);
}
uint8 RoadAlpha(float S,float L)
{
    float A=1;
    if(S<4)A=FMath::Clamp((S-2)*.5f,0.f,1.f);
    else if(S>L-2)A=1-FMath::Clamp((S-(L-2))*.5f,0.f,1.f);
    return uint8(A*255.f);
}
int32 SelectVariant(float Green,const TArray<FVector2f>& Ranges,FRandom& Random)
{
    TArray<int32,TInlineAllocator<16>> Eligible;
    for(int32 I=0;I<Ranges.Num();++I)if(Green>=Ranges[I].X && Green<=Ranges[I].Y)Eligible.Add(I);
    return Eligible.IsEmpty()?INDEX_NONE:Eligible[(Random.Next()*Eligible.Num())>>15];
}
uint32 CellSeed(int32 X,int32 Y,uint32 Seed,uint32 Channel)
{
    uint32 V=Seed^(uint32(X)*0x9e3779b9u)^(uint32(Y)*0x85ebca6bu)^(Channel*0xc2b2ae35u);
    V^=V>>16;V*=0x7feb352du;V^=V>>15;V*=0x846ca68bu;return V^(V>>16);
}
}
