#pragma once
#include "CoreMinimal.h"
#include <queue>
/** Host authoring tool, not recovered MudRunner code. Priority flood finds
 * spill elevations without carving/flattening the supplied final road bed. */
namespace GTRoadBasin
{
inline TArray<float> Fill(const TArray<float>& Bed,const TArray<float>& Allow,int32 W,int32 H)
{
    TArray<float> Water;Water.Init(-FLT_MAX,Bed.Num());
    if(W<3||H<3||Bed.Num()!=W*H||Allow.Num()!=Bed.Num())return Water;
    struct FNode {float Z;int32 I;bool operator<(const FNode& B)const{return Z==B.Z?I>B.I:Z>B.Z;}};
    std::priority_queue<FNode> Queue;TArray<uint8> Seen;Seen.Init(0,Bed.Num());TArray<float> Spill=Bed;
    auto Add=[&](int32 I){if(!Seen[I]){Seen[I]=1;Queue.push({Bed[I],I});}};
    for(int32 X=0;X<W;++X){Add(X);Add((H-1)*W+X);}for(int32 Y=0;Y<H;++Y){Add(Y*W);Add(Y*W+W-1);}
    auto Neighbours=[&](int32 I,auto Visit){const int32 X=I%W,Y=I/W;for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)if((DX||DY)&&X+DX>=0&&X+DX<W&&Y+DY>=0&&Y+DY<H)Visit(I+DX+DY*W);};
    while(!Queue.empty())
    {const auto N=Queue.top();Queue.pop();Neighbours(N.I,[&](int32 J){if(!Seen[J]){Seen[J]=1;Spill[J]=FMath::Max(Bed[J],N.Z);Queue.push({Spill[J],J});}});}
    Seen.Init(0,Bed.Num());
    for(int32 I=0;I<Bed.Num();++I)if(!Seen[I]&&Spill[I]>Bed[I]+1&&Allow[I]>0)
    {
        TArray<int32> Basin;Basin.Add(I);Seen[I]=1;float Floor=Bed[I],Limit=Allow[I],Level=Spill[I]-.5f;bool Escapes=false;
        for(int32 K=0;K<Basin.Num();++K)Neighbours(Basin[K],[&](int32 J)
        {
            if(FMath::Abs(Spill[J]-Spill[I])>.1f||Spill[J]<=Bed[J]+1)return;
            if(Allow[J]<=0){Escapes=true;return;}
            if(!Seen[J]){Seen[J]=1;Basin.Add(J);Floor=FMath::Min(Floor,Bed[J]);Limit=FMath::Min(Limit,Allow[J]);}
        });
        // A basin crossing the editable wet region must be extended explicitly;
        // never cut a standing pool off at an invisible rectangular boundary.
        if(Escapes||Basin.Num()<6)continue;
        Level=FMath::Min(Level,Floor+Limit);
        for(int32 J:Basin)if(Level>Bed[J]+1)Water[J]=Level;
    }
    return Water;
}
}
