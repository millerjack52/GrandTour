#include "GTLandscapeSurfaceSetupLibrary.h"

#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeEdit.h"
#include "LandscapeEditLayer.h"
#include "Misc/FileHelper.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpression.h"
#include "Terrain/GTLandscapeSurface.h"
#include "GTProceduralGround.h"
#include "Terrain/GTRoadReliefTile.h"
#include "ProceduralMeshComponent.h"

int32 UGTLandscapeSurfaceSetupLibrary::RoundShallowPondBank(AGTProceduralGround* Author,FVector Centre,FVector2D RadiusCm,float CollarCm)
{
    if(!Author || !Author->Surface || !Author->GetWorld() || Author->GetWorld()->IsGameWorld() ||
       RadiusCm.GetMin()<500 || RadiusCm.GetMax()>2500 || CollarCm<RadiusCm.GetMax() || CollarCm>3000)return -1;
    auto* Surface=Author->Surface.Get();const auto Origin=Surface->RoadTileOrigin;const float Span=Surface->RoadTileSpanCm;
    if(Span<=0 || !Author->ReliefMaterial)return -1;
    auto Original=[&](double X,double Y){return Surface->GroundHeightAt(FVector(X,Y,0)).Get(Author->BaseHeightAt(FVector2D(X,Y)));};
    auto Height=[&](double X,double Y){
        const double Old=Original(X,Y),DX=(X-Centre.X)/RadiusCm.X,DY=(Y-Centre.Y)/RadiusCm.Y,A=FMath::Atan2(DY,DX);
        const double R=FMath::Sqrt(DX*DX+DY*DY)/(1+.055*FMath::Sin(A*3+.4)+.025*FMath::Sin(A*5-1.2));
        const double Fade=(1-FMath::SmoothStep(double(CollarCm-300),double(CollarCm),FMath::Abs(X-Centre.X)))*
                          (1-FMath::SmoothStep(double(CollarCm-300),double(CollarCm),FMath::Abs(Y-Centre.Y)));
        const double Target=Centre.Z+FMath::Clamp((R-1)*190.,-65.,27.);
        return Old+FMath::Max(0.,Target-Old)*Fade;
    };
    struct FPatch {FIntPoint Key;FVector Position;int32 Intervals;TArray<float> Heights;TArray<FVector> Normals;AGTRoadReliefTile* Existing=nullptr;};
    TArray<FPatch> Patches;int32 Triangles=0;
    const int32 X0=FMath::FloorToInt((Centre.X-CollarCm-Origin.X)/Span),X1=FMath::FloorToInt((Centre.X+CollarCm-Origin.X)/Span);
    const int32 Y0=FMath::FloorToInt((Centre.Y-CollarCm-Origin.Y)/Span),Y1=FMath::FloorToInt((Centre.Y+CollarCm-Origin.Y)/Span);
    if((X1-X0+1)*(Y1-Y0+1)>100)return -1;
    // Compute and validate every sample before changing the world.
    for(int32 Y=Y0;Y<=Y1;++Y)for(int32 X=X0;X<=X1;++X){
        FPatch P;P.Key=FIntPoint(X,Y);P.Position=FVector(Origin+FVector2D(X,Y)*Span,0);P.Existing=Author->ReliefTiles.FindRef(P.Key);
        P.Intervals=P.Existing?P.Existing->Intervals:FMath::CeilToInt(Span/50);const int32 Row=P.Intervals+1;double MaxDelta=0;
        for(int32 J=0;J<Row;++J)for(int32 I=0;I<Row;++I){
            const double WX=P.Position.X+I*Span/P.Intervals,WY=P.Position.Y+J*Span/P.Intervals,Old=Original(WX,WY),H=Height(WX,WY);
            if(!FMath::IsFinite(H) || H-Old>160)return -1;
            MaxDelta=FMath::Max(MaxDelta,H-Old);P.Heights.Add(H+(P.Existing?0:.8));
            P.Normals.Add(FVector(-(Height(WX+20,WY)-Height(WX-20,WY))/40,-(Height(WX,WY+20)-Height(WX,WY-20))/40,1).GetSafeNormal());
        }
        if(MaxDelta>.1){Triangles+=P.Intervals*P.Intervals*2;Patches.Add(MoveTemp(P));}
    }
    if(Triangles>40000)return -1;
    Author->Modify();Surface->Modify();
    for(auto& P:Patches){
        auto* T=P.Existing?P.Existing:Author->GetWorld()->SpawnActor<AGTRoadReliefTile>(P.Position,FRotator::ZeroRotator);
        if(!T)return -1;
        T->Modify();if(!P.Existing)T->SetActorLabel(FString::Printf(TEXT("LidarWater_Shore_%d_%d"),P.Key.X,P.Key.Y));
        T->Surface=Surface;T->Intervals=P.Intervals;T->SpanCm=Span;T->Heights=MoveTemp(P.Heights);T->Normals=MoveTemp(P.Normals);
        T->Signature=TEXT("WaterRefinement-1");if(!P.Existing)T->Mesh->SetMaterial(0,Author->ReliefMaterial);
        T->BuildMesh();T->MarkPackageDirty();Author->ReliefTiles.Add(P.Key,T);Surface->RoadReliefTiles.Add(P.Key,T);
    }
    return Patches.Num();
}

bool UGTLandscapeSurfaceSetupLibrary::ImportLidarAuthoringHeights(ALandscape* L,const FString& Filename)
{
    constexpr int32 N=2017;
    if(!L || !L->GetWorld() || L->GetWorld()->IsGameWorld() || !L->GetLandscapeInfo() || L->GetEditLayers().Num()!=1)return false;
    int32 X1,Y1,X2,Y2;
    if(!L->GetLandscapeInfo()->GetLandscapeExtent(X1,Y1,X2,Y2) || X2-X1+1!=N || Y2-Y1+1!=N)return false;
    const FTransform T=L->GetActorTransform();
    const FVector Corner=T.TransformPosition(FVector(X1,Y1,0));
    if(!L->GetActorRotation().IsNearlyZero() || FMath::Abs(Corner.X+185000)>1 || FMath::Abs(Corner.Y+185000)>1 ||
       FMath::Abs(T.GetScale3D().X-370000./2016)>0.01 || FMath::Abs(T.GetScale3D().Y-370000./2016)>0.01)return false;
    TArray<uint8> Bytes;
    if(!FFileHelper::LoadFileToArray(Bytes,*Filename) || Bytes.Num()!=N*N*2)return false;
    TArray<uint16> Heights;Heights.SetNumUninitialized(N*N);FMemory::Memcpy(Heights.GetData(),Bytes.GetData(),Bytes.Num());
    L->Modify();
    {
        FHeightmapAccessor<false> Accessor(L->GetLandscapeInfo());
        Accessor.SetEditLayer(L->GetEditLayer(0)->GetGuid());
        Accessor.SetData(X1,Y1,X2,Y2,Heights.GetData());Accessor.Flush();
    }
    L->RequestLayersContentUpdate(ELandscapeLayerUpdateMode::Update_All);L->ForceUpdateLayersContent();L->MarkPackageDirty();
    TArray<uint16> Readback;Readback.SetNumUninitialized(N*N);
    FLandscapeEditDataInterface Edit(L->GetLandscapeInfo(),L->GetEditLayer(0)->GetGuid());
    Edit.GetHeightDataFast(X1,Y1,X2,Y2,Readback.GetData(),0);
    return Heights==Readback;
}

bool UGTLandscapeSurfaceSetupLibrary::ConnectDisplacement(UMaterial* M, UMaterialExpression* Expression, int32 OutputIndex, float UniformLandscapeScale)
{
    if (!M || !Expression || Expression->GetOuter() != M || OutputIndex < 0 || OutputIndex >= Expression->GetOutputs().Num()) return false;
    if (!FMath::IsFinite(UniformLandscapeScale) || UniformLandscapeScale <= 0.f) return false;
    M->Modify();
    Expression->ConnectExpression(M->GetExpressionInputForProperty(MP_Displacement), OutputIndex);
    M->bEnableTessellation = true;
    M->DisplacementScaling.Magnitude = 65.f / UniformLandscapeScale;
    M->DisplacementScaling.Center = 50.f / 65.f;
    M->PostEditChange();
    M->MarkPackageDirty();
    return true;
}

ALandscape* UGTLandscapeSurfaceSetupLibrary::CreatePrototypeLandscape(UObject* Context, UMaterial* Material)
{
    UWorld* World = Context ? Context->GetWorld() : nullptr;
    if (!World || !Material || World->IsGameWorld()) return nullptr;
    for (TActorIterator<ALandscapeProxy> It(World); It; ++It) return nullptr;
    if (auto* Live = IConsoleManager::Get().FindConsoleVariable(TEXT("landscape.Nanite.LiveRebuildOnModification"))) Live->Set(0, ECVF_SetByCode);
    constexpr int32 N = 64;
    TArray<uint16> Heights; Heights.Init(32768, N*N);
    TMap<FGuid, TArray<uint16>> HeightLayers; HeightLayers.Add(FGuid(), MoveTemp(Heights));
    TMap<FGuid, TArray<FLandscapeImportLayerInfo>> PaintLayers; PaintLayers.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());
    auto* L = World->SpawnActor<ALandscape>();
    if (!L) return nullptr;
    L->SetActorLocation(FVector(-1575, -1575, 0));
    L->SetActorScale3D(FVector(50, 50, 50));
    L->ShadowCacheInvalidationBehavior = EShadowCacheInvalidationBehavior::Always;
    L->LandscapeMaterial = Material;
    L->bUseDynamicMaterialInstance = true;
    L->Import(FGuid::NewGuid(), 0, 0, N-1, N-1, 1, N-1, HeightLayers, TEXT(""), PaintLayers,
        ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
    L->SetActorLabel(TEXT("Landscape_SurfacePrototype_31m"));
    L->MarkPackageDirty();
    // PreSave builds Nanite after registration. Never turn on LiveRebuildOnModification.
    return L;
}

ALandscape* UGTLandscapeSurfaceSetupLibrary::CreateStudyLandscape(UObject* Context,UMaterial* Material,FVector Origin,const TArray<float>& HeightsCm)
{
    UWorld* World=Context?Context->GetWorld():nullptr;
    constexpr int32 N=127;
    if(!World || World->IsGameWorld() || !Material || HeightsCm.Num()!=N*N)return nullptr;
    TArray<uint16> Heights;Heights.Reserve(N*N);
    for(float H:HeightsCm)
    {
        if(!FMath::IsFinite(H) || FMath::Abs(H)>10000)return nullptr;
        Heights.Add(uint16(FMath::Clamp(FMath::RoundToInt(H*128.f/50.f)+32768,0,65535)));
    }
    auto* L=World->SpawnActor<ALandscape>();if(!L)return nullptr;
    L->SetActorLocation(Origin);L->SetActorScale3D(FVector(50));
    L->LandscapeMaterial=Material;L->bUseDynamicMaterialInstance=true;
    TMap<FGuid,TArray<uint16>> H;H.Add(FGuid(),MoveTemp(Heights));
    TMap<FGuid,TArray<FLandscapeImportLayerInfo>> P;P.Add(FGuid(),{});
    L->Import(FGuid::NewGuid(),0,0,N-1,N-1,1,63,H,TEXT(""),P,ELandscapeImportAlphamapType::Additive,TArrayView<const FLandscapeLayer>());
    L->SetActorLabel(TEXT("MixedRoute_Landscape"));L->MarkPackageDirty();return L;
}

bool UGTLandscapeSurfaceSetupLibrary::ImportPaint(AGTLandscapeSurface* Surface, UTexture2D* Texture)
{
    if (!Surface || !Texture || Texture->Source.GetSizeX() < 2 || Texture->Source.GetSizeX() > 2048
        || Texture->Source.GetSizeX() != Texture->Source.GetSizeY() || !Surface->GetWorld() || Surface->GetWorld()->IsGameWorld()) return false;
    const auto Format = Texture->Source.GetFormat();
    if (Format != TSF_BGRA8) return false;
    TArray64<uint8> Bytes;
    if (!Texture->Source.GetMipData(Bytes, 0)) return false;
    const int32 N = Texture->Source.GetSizeX();
    if (Bytes.Num() != int64(N)*N*4) return false;
    TArray<FLinearColor> Cells;
    Cells.SetNum(N*N);
    for (int32 I = 0; I < N*N; ++I)
    {
        const uint8* B = Bytes.GetData() + I*4;
        // Edge is firm, making bilinear clamp sampling outside the authored area harmless.
        const int32 X = I%N, Y = I/N;
        if ((X == 0 || Y == 0 || X == N-1 || Y == N-1) && (B[2] || B[0])) return false;
        Cells[I] = FLinearColor(B[2]*(50.f/255.f), -B[1]*(50.f/255.f), B[0]/255.f, B[3]/255.f);
    }
    Surface->Modify();
    Surface->PaintResolution = N;
    Surface->PaintCells = MoveTemp(Cells);
    Surface->PaintTexture = Texture;
    Texture->SRGB = false;
    Texture->CompressionSettings = TC_VectorDisplacementmap;
    Texture->MipGenSettings = TMGS_NoMipmaps;
    Texture->Filter = TF_Bilinear;
    Texture->AddressX = TA_Clamp; Texture->AddressY = TA_Clamp;
    Texture->PostEditChange(); Texture->MarkPackageDirty();
    Surface->MarkPackageDirty();
    return true;
}

bool UGTLandscapeSurfaceSetupLibrary::ImportWorldRestHeights(AGTLandscapeSurface* Surface,UTexture2D* Texture)
{
    if(!Surface || !Texture || !Surface->GetWorld() || Surface->GetWorld()->IsGameWorld()) return false;
    const int32 N=Texture->Source.GetSizeX();
    if(N<2 || N>1024 || Texture->Source.GetSizeY()!=N || Texture->Source.GetFormat()!=TSF_BGRA8) return false;
    TArray64<uint8> Bytes;
    if(!Texture->Source.GetMipData(Bytes,0) || Bytes.Num()!=int64(N)*N*4) return false;
    TArray<float> Heights;Heights.SetNumUninitialized(N*N);
    for(int32 I=0;I<N*N;++I)
    {
        const uint8* B=Bytes.GetData()+I*4;
        Heights[I]=(uint32(B[2])*256u+B[1])*(65.f/65535.f)-50.f;
    }
    Surface->Modify();Surface->WorldRestHeights=MoveTemp(Heights);Surface->WorldRestResolution=N;
    Texture->SRGB=false;Texture->CompressionSettings=TC_VectorDisplacementmap;
    Texture->MipGenSettings=TMGS_NoMipmaps;Texture->Filter=TF_Bilinear;
    Texture->AddressX=TA_Clamp;Texture->AddressY=TA_Clamp;
    Texture->PostEditChange();Texture->MarkPackageDirty();Surface->MarkPackageDirty();return true;
}

bool UGTLandscapeSurfaceSetupLibrary::ImportMudRelief(AGTLandscapeSurface* Surface,UTexture2D* Texture,float TileCm)
{
    if(!Surface || !Texture || !Surface->GetWorld() || Surface->GetWorld()->IsGameWorld() || !FMath::IsFinite(TileCm) || TileCm<=0)return false;
    const int32 N=Texture->Source.GetSizeX();
    if(N<2 || N>1024 || Texture->Source.GetSizeY()!=N || Texture->Source.GetFormat()!=TSF_BGRA8)return false;
    TArray64<uint8> Bytes;if(!Texture->Source.GetMipData(Bytes,0) || Bytes.Num()!=int64(N)*N*4)return false;
    Surface->Modify();Surface->MudReliefResolution=N;Surface->MudReliefTileCm=TileCm;Surface->MudReliefHeights.SetNumUninitialized(N*N);
    for(int32 I=0;I<N*N;++I){const uint8* B=Bytes.GetData()+I*4;Surface->MudReliefHeights[I]=(uint32(B[2])*256u+B[1])*(65.f/65535.f)-50.f;}
    Texture->SRGB=false;Texture->CompressionSettings=TC_VectorDisplacementmap;Texture->MipGenSettings=TMGS_NoMipmaps;Texture->Filter=TF_Bilinear;
    Texture->AddressX=TA_Wrap;Texture->AddressY=TA_Wrap;Texture->PostEditChange();Texture->MarkPackageDirty();Surface->MarkPackageDirty();return true;
}

bool UGTLandscapeSurfaceSetupLibrary::ImportMaterialAtlas(AGTLandscapeSurface* Surface,UTexture2D* Texture)
{
    if(!Surface || !Texture || !Surface->GetWorld() || Surface->GetWorld()->IsGameWorld())return false;
    const int32 N=Texture->Source.GetSizeX();
    if(N<2 || N>2048 || Texture->Source.GetSizeY()!=N || Texture->Source.GetFormat()!=TSF_BGRA8)return false;
    TArray64<uint8> Bytes;
    if(!Texture->Source.GetMipData(Bytes,0) || Bytes.Num()!=int64(N)*N*4)return false;
    Surface->Modify();Surface->MaterialResolution=N;Surface->MaterialCells.SetNumUninitialized(N*N);
    for(int32 I=0;I<N*N;++I)
    {
        const uint8* B=Bytes.GetData()+I*4;
        Surface->MaterialCells[I]=FLinearColor(B[2]/255.f,B[1]/255.f,B[0]/255.f,B[3]/255.f);
    }
    Surface->MarkPackageDirty();return true;
}

bool UGTLandscapeSurfaceSetupLibrary::ImportClayAtlas(AGTLandscapeSurface* Surface,UTexture2D* Texture)
{
    if(!Surface || !Texture || !Surface->GetWorld() || Surface->GetWorld()->IsGameWorld())return false;
    const int32 N=Texture->Source.GetSizeX();
    if(N<2 || N>2048 || Texture->Source.GetSizeY()!=N || Texture->Source.GetFormat()!=TSF_BGRA8)return false;
    TArray64<uint8> Bytes;
    if(!Texture->Source.GetMipData(Bytes,0) || Bytes.Num()!=int64(N)*N*4)return false;
    Surface->Modify();Surface->ClayResolution=N;Surface->ClayCells.SetNumUninitialized(N*N);
    for(int32 I=0;I<N*N;++I)
    {
        const uint8* B=Bytes.GetData()+I*4;
        Surface->ClayCells[I]=FColor(B[2],B[1],B[0],B[3]);
    }
    Surface->MarkPackageDirty();return true;
}

bool UGTLandscapeSurfaceSetupLibrary::ImportRestHeights(AGTLandscapeSurface* Surface, UTexture2D* Mud, UTexture2D* Clay)
{
    if (!Surface || !Surface->GetWorld() || Surface->GetWorld()->IsGameWorld()) return false;
    // Broad relief must be filtered to the 6.25 cm simulation grid; fine scan detail belongs in POM.
    constexpr int32 Dest=32;
    auto Import=[](UTexture2D* Texture, TArray<float>& Out)
    {
        if (!Texture || Texture->SRGB) return false;
        const int32 N=Texture->Source.GetSizeX();
        const auto Format=Texture->Source.GetFormat();
        if (N<Dest || N>4096 || N%Dest || Texture->Source.GetSizeY()!=N
            || (Format!=TSF_G8 && Format!=TSF_G16 && Format!=TSF_BGRA8)) return false;
        TArray64<uint8> Bytes;
        const int32 Stride=Format==TSF_G8 ? 1 : Format==TSF_G16 ? 2 : 4;
        if (!Texture->Source.GetMipData(Bytes,0) || Bytes.Num()!=int64(N)*N*Stride) return false;
        Out.SetNum(Dest*Dest);
        const int32 Step=N/Dest;
        for (int32 Y=0;Y<Dest;++Y) for (int32 X=0;X<Dest;++X)
        {
            double Sum=0.;
            for (int32 J=0;J<Step;++J) for (int32 I=0;I<Step;++I)
            {
                const uint8* Pixel=Bytes.GetData()+((Y*Step+J)*N+X*Step+I)*Stride;
                if (Format==TSF_G16) { uint16 V;FMemory::Memcpy(&V,Pixel,2);Sum+=V/65535.; }
                else Sum+=Pixel[Format==TSF_BGRA8 ? 2 : 0]/255.;
            }
            Out[Y*Dest+X]=float(Sum/(Step*Step));
        }
        return true;
    };
    TArray<float> MudData,ClayData;
    if (!Import(Mud,MudData) || !Import(Clay,ClayData)) return false;
    Surface->Modify();
    Surface->MudRestHeights=MoveTemp(MudData);Surface->ClayRestHeights=MoveTemp(ClayData);
    Surface->RestHeightResolution=Dest;
    Surface->MarkPackageDirty();
    return true;
}
