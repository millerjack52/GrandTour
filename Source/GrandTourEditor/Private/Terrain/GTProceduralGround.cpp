#include "GTProceduralGround.h"
#include "GTRoadConditionShape.h"
#include "Terrain/GTEditorReconstruction.h"
#include "Terrain/GTRoadReliefTile.h"
#include "Terrain/GTRoadWaterMesh.h"
#include "Terrain/GTRoadBasin.h"
#include "ProceduralMeshComponent.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTWaterDomain.h"
#include "Components/SplineComponent.h"
#include "Components/BoxComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeEdit.h"
#include "LandscapeEditLayer.h"
#include "PhysicsEngine/BodySetup.h"
#include "Materials/MaterialInterface.h"
#include "DrawDebugHelpers.h"
#include "Misc/Crc.h"
#include "Misc/SecureHash.h"
#include "UObject/Package.h"

namespace GTGroundAuthoring
{
using namespace GTEditorReconstruction;
FString Digest(const void* P,int64 Size)
{FMD5 MD5;MD5.Update(static_cast<const uint8*>(P),Size);uint8 Bytes[16];MD5.Final(Bytes);return BytesToHex(Bytes,16);}
float Smooth(float A,float B,float X){const float T=FMath::Clamp((X-A)/(B-A),0.f,1.f);return T*T*(3-2*T);}
float FirmProfileBlend(const AGTProceduralRoad* Road,float S,float Length)
{
    if(!Road->bFirmGravel)return 0;
    const float Preserve=Road->FirmProfileEndPreserveMetres;
    return Preserve>0?Smooth(Preserve,Preserve+16,Length-S):1.f;
}
float Noise(FVector2D P,int32 Seed,float Scale)
{return FMath::PerlinNoise2D(FVector2D(P.X/Scale+Seed%193,P.Y/Scale+Seed%97))*.5f+.5f;}
struct FRoadPoint {FVector P;float S,Width;};
struct FRoad
{
    TMap<FIntPoint,TArray<int32>> NearbySegments; // 32m cells for opt-in sparse map corridors.
    AGTProceduralRoad* Actor=nullptr;TArray<FRoadPoint> Points;float Length=0;
    TArray<uint8> Pixels;int32 TextureWidth=0,TextureHeight=0;
    struct FVertex {FVector2D P;FVector2f UV;float Alpha;};
    TArray<FVertex> Ribbon;
    float ReliefAt(FVector2D P,int32 NearSegment) const
    {
        if(Pixels.IsEmpty())return 0;
        for(int32 I=FMath::Max(0,NearSegment-2);I<=FMath::Min(Points.Num()-2,NearSegment+2);++I)
        for(int32 Half=0;Half<2;++Half)
        {
            const auto& A=Ribbon[2*I];const auto& B=Ribbon[2*I+(Half?3:1)];const auto& C=Ribbon[2*I+(Half?2:3)];
            const double Den=FVector2D::CrossProduct(B.P-A.P,C.P-A.P);if(FMath::Abs(Den)<.001)continue;
            const double V=FVector2D::CrossProduct(P-A.P,C.P-A.P)/Den,W=FVector2D::CrossProduct(B.P-A.P,P-A.P)/Den,U=1-V-W;
            if(U<-.000001||V<-.000001||W<-.000001)continue;
            const FVector2f UV=A.UV*float(U)+B.UV*float(V)+C.UV*float(W);
            return RoadOffsetCm(SampleRoadRed(Pixels,TextureWidth,TextureHeight,UV),A.Alpha*U+B.Alpha*V+C.Alpha*W)*Actor->ReliefStrength;
        }
        return 0;
    }
};
TArray<FRoad> Roads(AGTProceduralGround* Author)
{
    TArray<AGTProceduralRoad*> Actors;
    for(TActorIterator<AGTProceduralRoad> It(Author->GetWorld());It;++It)if(It->Author==Author)Actors.Add(*It);
    Actors.Sort([](const AGTProceduralRoad& A,const AGTProceduralRoad& B){return A.GetName()<B.GetName();});
    TArray<FRoad> Result;
    for(auto* Actor:Actors)
    {
        auto* Spline=Actor->ControlPoints.Get();const int32 N=Spline->GetNumberOfSplinePoints();if(N<2)continue;
        TArray<float> Knots,X,Y,Z,W;const FVector Origin=Spline->GetLocationAtSplinePoint(0,ESplineCoordinateSpace::World);FVector Previous=Origin;
        float Length=0;
        for(int32 I=0;I<N;++I)
        {
            const FVector P=Spline->GetLocationAtSplinePoint(I,ESplineCoordinateSpace::World);
            if(I)Length+=float(FVector::Distance(P,Previous)*.01);
            if(I && Length<=Knots.Last()+.001f){Knots.Reset();break;}
            Knots.Add(Length);X.Add(float((P.X-Origin.X)*.01));Y.Add(float((P.Y-Origin.Y)*.01));Z.Add(float((P.Z-Origin.Z)*.01));
            W.Add(FMath::Clamp(float(Spline->GetScaleAtSplinePoint(I).Y)*Actor->WidthCm,200.f,2000.f));Previous=P;
        }
        FCurve CX,CY,CZ,CW;
        if(!CX.Build(Knots,X)||!CY.Build(Knots,Y)||!CZ.Build(Knots,Z)||!CW.Build(Knots,W))continue;
        FRoad Road;Road.Actor=Actor;Road.Length=Length;
        // Native interval count and cubic evaluation. Width shares knot distance
        // here; the exact native road caller width parameter remains unproven.
        const int32 Intervals=FMath::Max(1,int32(Length*.5f+.5f));
        for(int32 I=0;I<=Intervals;++I)
        {
            const float T=I*2.f;
            float ZValue=CZ.At(T);
            const float Radius=Actor->ProfileSmoothingMetres*.5f;
            if(Radius>0)
            {
                // Symmetric filter retains a constant grade. Fade at endpoints so
                // junction elevations remain fixed; never move the route in XY.
                float Sum=0,Weights=0;
                for(int32 J=-8;J<=8;++J)
                {
                    const float Offset=Radius*J/8.f,Wt=1.f-FMath::Abs(J)/9.f;
                    Sum+=CZ.At(FMath::Clamp(T+Offset,0.f,Length))*Wt;Weights+=Wt;
                }
                const float Blend=Smooth(0,Radius,T)*Smooth(0,Radius,Length-T)*(Actor->bFirmGravel?FirmProfileBlend(Actor,T,Length):1.f);
                ZValue=FMath::Lerp(ZValue,Sum/Weights,Blend);
            }
            const FVector P=Origin+FVector(CX.At(T),CY.At(T),ZValue)*100;
            const float Width=FMath::Clamp(CW.At(T),200.f,2000.f);
            Road.Points.Add({P,T,Width});
            const FVector2D Tangent=FVector2D(CX.Derivative(T),CY.Derivative(T)).GetSafeNormal();
            const FVector2D Side(Tangent.Y,-Tangent.X);
            for(int32 Sign:{-1,1})Road.Ribbon.Add({FVector2D(P)+Side*(Sign*Width*.5f),RoadUV(T,Sign*Width*.005f,Actor->ReliefDefaultWidthCm*.01f,Actor->ReliefDiffuseAspect),RoadAlpha(T,Length)/255.f});
        }
        if(Actor->bApplyRelief&&Actor->ReliefTexture)
        {
            TArray64<uint8> Bytes;auto* Texture=Actor->ReliefTexture.Get();
            if(Texture->Source.GetFormat()==TSF_BGRA8&&Texture->Source.GetMipData(Bytes,0))
            {Road.Pixels.Append(Bytes.GetData(),Bytes.Num());Road.TextureWidth=Texture->Source.GetSizeX();Road.TextureHeight=Texture->Source.GetSizeY();}
        }
        Result.Add(MoveTemp(Road));
    }
    return Result;
}
struct FField {float Height=0,Relief=0,Road=0,FirmRoad=0,Grass=0,Wet=0,Mud=0,Firm=0,Softness=0,Condition=0,WaterFill=0,Forest=1,Exclude=0,Distance=MAX_flt,HalfWidth=0;};
struct FContext
{
    AGTProceduralGround* Author;TArray<FRoad> Paths;TArray<AGTProceduralGroundRegion*> Regions;
    explicit FContext(AGTProceduralGround* A):Author(A),Paths(Roads(A))
    {for(TActorIterator<AGTProceduralGroundRegion> It(A->GetWorld());It;++It)if(It->Author==A)Regions.Add(*It);
     Regions.Sort([](const AGTProceduralGroundRegion& A,const AGTProceduralGroundRegion& B){return A.GetName()<B.GetName();});
     if(A->bAllowLargeSparseRoadBounds)for(auto& Path:Paths)for(int32 I=0;I<Path.Points.Num()-1;++I)
     {
         const auto& P=Path.Points[I];const auto& Q=Path.Points[I+1];
         const float Pad=FMath::Max(P.Width,Q.Width)*.5f+2000;
         const FVector2D Lo(FMath::Min(P.P.X,Q.P.X)-Pad,FMath::Min(P.P.Y,Q.P.Y)-Pad),Hi(FMath::Max(P.P.X,Q.P.X)+Pad,FMath::Max(P.P.Y,Q.P.Y)+Pad);
         for(int32 Y=FMath::FloorToInt(Lo.Y/3200);Y<=FMath::FloorToInt(Hi.Y/3200);++Y)for(int32 X=FMath::FloorToInt(Lo.X/3200);X<=FMath::FloorToInt(Hi.X/3200);++X)Path.NearbySegments.FindOrAdd(FIntPoint(X,Y)).Add(I);
     }}
    FField At(FVector2D P) const
    {
        FField F;F.Height=Author->BaseHeightAt(P);F.Grass=.7f;
        F.Forest=.35f+.65f*Noise(P,Author->Seed,4500);
        for(auto* R:Regions)
        {
            const FVector Q=R->Bounds->GetComponentTransform().InverseTransformPosition(FVector(P,R->GetActorLocation().Z));
            const FVector E=R->Bounds->GetUnscaledBoxExtent();
            const float Radius=FMath::Sqrt(FMath::Square(Q.X/E.X)+FMath::Square(Q.Y/E.Y));
            const float Weight=(1-Smooth(.6f,1.f,Radius+(Noise(P,Author->Seed+17,1700)-.5f)*.16f))*R->Strength;
            if(R->Kind==EGTGroundRegionKind::Exclusion)F.Exclude=FMath::Max(F.Exclude,Weight);
            if(R->Kind==EGTGroundRegionKind::Clearing)F.Forest*=1-Weight;
            if(R->Kind==EGTGroundRegionKind::Woodland)F.Forest=FMath::Lerp(F.Forest,1.f,Weight);
            if(R->Kind==EGTGroundRegionKind::WetGround){F.Wet=FMath::Lerp(F.Wet,R->Wetness,Weight);F.Mud=FMath::Lerp(F.Mud,R->MudDepthCm,Weight);}
            F.Grass=FMath::Lerp(F.Grass,R->GrassCover,Weight);
        }
        F.Softness=F.Wet;
        for(const auto& Path:Paths)
        {
            const auto* Nearby=Author->bAllowLargeSparseRoadBounds?Path.NearbySegments.Find(FIntPoint(FMath::FloorToInt(P.X/3200),FMath::FloorToInt(P.Y/3200))):nullptr;
            if(Author->bAllowLargeSparseRoadBounds&&!Nearby)continue;
            float Best=MAX_flt,T=0;int32 Index=0;
            const int32 Count=Nearby?Nearby->Num():Path.Points.Num()-1;
            for(int32 J=0;J<Count;++J)
            {
                const int32 I=Nearby?(*Nearby)[J]:J;
                const FVector2D A(Path.Points[I].P),B(Path.Points[I+1].P),D=B-A;
                const float U=FMath::Clamp(float(FVector2D::DotProduct(P-A,D)/FMath::Max(1.,D.SizeSquared())),0.f,1.f);
                const float Dist=float(FVector2D::DistSquared(P,A+D*U));
                if(Dist<Best){Best=Dist;T=U;Index=I;}
            }
            const auto& A=Path.Points[Index];const auto& B=Path.Points[Index+1];
            const float Distance=FMath::Sqrt(Best),Width=FMath::Lerp(A.Width,B.Width,T)*.5f,S=FMath::Lerp(A.S,B.S,T);
            if(Distance<F.Distance){F.Distance=Distance;F.HalfWidth=Width;}
            const float Weight=1-Smooth(Width,Width+200,Distance); // recovered 2m shoulder
            const float Cover=1-Smooth(Width*.72f,Width+100,Distance);
            const float End=Smooth(0,2,S)*(1-Smooth(Path.Length-2,Path.Length,S)); // host end cap
            const float Wet=FMath::Clamp(Path.Actor->Wetness+(.5f-Noise(P,Author->Seed+43,2300))*.7f,0.f,1.f);
            const float FirmBlend=FirmProfileBlend(Path.Actor,S,Path.Length);
            const float Target=FMath::Lerp(float(A.P.Z),float(B.P.Z),T)-Path.Actor->BedDepthCm*(1-FirmBlend)*(RoadAlpha(S,Path.Length)/255.f);
            const float CutFill=FMath::Lerp(Path.Actor->MaximumCutFillCm,Path.Actor->FirmMaximumCutFillCm,FirmBlend);
            const float Delta=FMath::Clamp(Target-F.Height,-CutFill,CutFill);
            F.Height+=Delta*Weight*End;F.Road=FMath::Max(F.Road,Cover*End);
            F.Grass*=1-Cover*End*.96f;
            const float Patch=Smooth(.22f,.72f,Noise(P,Author->Seed+191,1200));
            const float Centre=1-Smooth(Width*.12f,Width*.32f,Distance);
            const float Verge=Smooth(Width*.68f,Width*.98f,Distance)*(1-Smooth(Width+50,Width+250,Distance));
            F.Grass=FMath::Max(F.Grass,End*Patch*(Centre*Path.Actor->CentreGrassCover+Verge*Path.Actor->VergeGrassCover));
            F.Wet=FMath::Lerp(F.Wet,Wet,Cover*End);
            F.Mud=FMath::Lerp(F.Mud,Path.Actor->MudDepthCm*Smooth(.2f,.65f,Wet),Cover*End);
            F.Firm=FMath::Lerp(F.Firm,(1-Wet)*.7f,Cover*End);
            F.Softness=FMath::Lerp(F.Softness,Wet,Cover*End);
            const FVector2D Tangent=(FVector2D(B.P)-FVector2D(A.P)).GetSafeNormal();
            const float Across=FVector2D::CrossProduct(Tangent,P-FMath::Lerp(FVector2D(A.P),FVector2D(B.P),T));
            // Independent authored-mud stage. Correlated along-road channels
            // produce unequal, wandering ruts; the native road texture stays below.
            for(const auto& C:Path.Actor->Conditions)
            {
                const float Blend=FMath::Min(C.BlendMetres,(C.EndMetres-C.StartMetres)*.5f);
                const float Long=Smooth(C.StartMetres,C.StartMetres+Blend,S)*(1-Smooth(C.EndMetres-Blend,C.EndMetres,S));
                const float Mask=Long*Cover*End;
                if(Mask<=0)continue;
                const auto Shape=GTRoadConditionShape::Evaluate(S,Across,Width,Path.Actor->DetailSeed,
                    C.RutDepthCm,C.TrackSpreadCm,C.Churn,C.CrossingTracks,C.BreakupCm);
                const float Soft=Shape.Soft;
                const float Mottle=.65f+.35f*Noise(P,Path.Actor->DetailSeed+39,400);
                F.Relief+=Shape.Relief*Mask*(1-FirmBlend);
                // Host-authored bog bowl. Its ends blend along the condition and
                // its shoulders retain a spill rim; no pre-existing wheel ruts required.
                F.Relief-=C.BasinDepthCm*Long*End*(1-Smooth(Width*.5f,Width+40,Distance))*(1-FirmBlend);
                F.Mud=FMath::Lerp(F.Mud,C.MudDepthCm*Mottle*(.55f+.45f*Soft),Mask);
                F.Wet=FMath::Lerp(F.Wet,C.Wetness,Mask);F.Firm=FMath::Lerp(F.Firm,C.Firmness,Mask);
                F.Softness=FMath::Lerp(F.Softness,1-C.Firmness,Mask);
                F.Grass=FMath::Lerp(F.Grass,C.GrassCover*(1-Shape.Worked*.9f),Mask);F.Condition=FMath::Max(F.Condition,Mask);
                // A connected bog has one fill cap above its lowest bed. Fading
                // that cap at the bowl's rim drains the entire basin via Min(Allow).
                // Long still bounds the authored footprint through Mask above.
                const float Fill=C.WaterFillCm*(C.BasinDepthCm>0?1.f:Long);
                if(!Path.Actor->bFirmGravel)F.WaterFill=FMath::Max(F.WaterFill,Fill*(1-Smooth(Width+100,Width+300,Distance)));
            }
            // Native offset rasterization uses interpolated UV and quantized alpha.
            // Host 75cm edge blend prevents a hard boundary on replacement tiles.
            F.Relief+=Path.ReliefAt(P,Index)*(1-Smooth(FMath::Max(0.f,Width-75),Width,Distance))*(1-FirmBlend);
            if(Path.Actor->bFirmGravel)
            {
                // Shallow irregular relief is independent of yielding soil.
                // Positive relief keeps it above the shallow backing landscape.
                const float Rough=FMath::Clamp(Path.Actor->FirmRoughnessCm,0.f,6.f);
                const float Phase=Path.Actor->DetailSeed*.173f;
                const float Wave=.5f*FMath::Sin(S*2*PI/2.7f+Across*.004f+Phase)
                    +.3f*FMath::Sin(S*2*PI/7.3f-Across*.009f)
                    +.2f*FMath::Sin(S*2*PI/1.8f+Across*.013f+Phase*.7f);
                F.Relief+=Rough*(1.f+Wave)*.5f*(1-Smooth(Width*.65f,Width,Distance))*End*FirmBlend;
                // Include a 50cm guard for fine-mesh interpolation at the road edge.
                // Wet appearance is independent of yielding depth. Shoulder blends
                // into the existing soil; the carriageway is exactly zero depth.
                const float FirmCover=1-Smooth(Width+50,Width+200,Distance);
                F.FirmRoad=FMath::Max(F.FirmRoad,FirmCover);
            }
            // LiDAR ford controls edit the bed separately. A track must never raise an
            // embankment through the river (the sheet queries its child domains too).
            if(Path.Actor->ActorHasTag(TEXT("LidarMudTrack")) && Author->Surface && Author->Surface->SimulatedWater)
            {
                const auto* Water=Author->Surface->SimulatedWater.Get();
                const auto* Domain=Author->BaseWaterDomain?Author->BaseWaterDomain.Get():Water->WaterDomain.Get();
                const float Base=Author->BaseHeightAt(P);
                float Level=0,Depth=0;FVector2D Velocity;
                if(Domain && Domain->Sample(P,Level,Depth,Velocity) && Level>Base+1)
                {F.Height=Base;F.Relief=0;F.WaterFill=0;}
            }
        }
        // Resolve rigidity after all roads, so an overlapping shoulder cannot
        // reintroduce a thin yielding layer at a firm-road junction.
        F.Mud*=1-F.FirmRoad;F.Softness*=1-F.FirmRoad;
        F.Firm=FMath::Lerp(F.Firm,1.f,F.FirmRoad);
        F.Condition=FMath::Max(F.Condition,F.FirmRoad);
        // Exclusion removes procedural changes, including terrain and masks.
        F.Height=FMath::Lerp(F.Height,Author->BaseHeightAt(P),F.Exclude);
        F.Relief*=1-F.Exclude;
        // Existing river/pond beds are protected in this first milestone.
        // Water authoring will be a separate terrain/domain operation.
        if(Author->Surface && Author->Surface->SimulatedWater && Author->Surface->SimulatedWater->WaterDomain)
        {
            const auto* Domain=Author->BaseWaterDomain?Author->BaseWaterDomain.Get():Author->Surface->SimulatedWater->WaterDomain.Get();
            // Continuous wet coverage at the original domain's grid boundary,
            // instead of a boolean switch between different bed elevations.
            const FVector2D Q=(P-Domain->OriginCm)/Domain->CellCm-FVector2D(.5,.5);
            float WetWeight=0;
            if(Q.X>=0&&Q.Y>=0&&Q.X<Domain->SizeX-1&&Q.Y<Domain->SizeY-1)
            {
                const int32 X=FMath::FloorToInt(Q.X),Y=FMath::FloorToInt(Q.Y);const float U=Q.X-X,V=Q.Y-Y;
                for(int32 DY=0;DY<2;++DY)for(int32 DX=0;DX<2;++DX)
                {const int32 I=((Y+DY)*Domain->SizeX+X+DX)*4+1;if(Domain->Samples.IsValidIndex(I)&&Domain->Samples[I]>.005f)WetWeight+=(DX?U:1-U)*(DY?V:1-V);}
            }
            const float Preserve=Smooth(0,.5f,WetWeight);
            F.Height=FMath::Lerp(F.Height,Author->BaseHeightAt(P),Preserve);F.Relief*=1-Preserve;F.WaterFill*=1-Preserve;
        }
        return F;
    }
};
bool Read(UTexture2D* T,TArray<uint8>& Out)
{TArray64<uint8> Bytes;if(!T||T->Source.GetFormat()!=TSF_BGRA8||!T->Source.GetMipData(Bytes,0))return false;Out.Reset();Out.Append(Bytes.GetData(),Bytes.Num());return true;}
void Write(UTexture2D* T,const TArray<uint8>& Bytes,int32 N)
{T->Modify();T->Source.Init(N,N,1,1,TSF_BGRA8,Bytes.GetData());T->SRGB=false;T->CompressionSettings=TC_VectorDisplacementmap;T->MipGenSettings=TMGS_NoMipmaps;T->PostEditChange();T->MarkPackageDirty();}
void WriteHeights(ALandscape* Landscape,const FIntRect& Full,const TArray<uint16>& Heights,int32 X1,int32 Y1,int32 X2,int32 Y2)
{
    TArray<uint16> Region;Region.SetNum((X2-X1+1)*(Y2-Y1+1));
    for(int32 Y=Y1;Y<=Y2;++Y)FMemory::Memcpy(Region.GetData()+(Y-Y1)*(X2-X1+1),Heights.GetData()+(Y-Full.Min.Y)*Full.Width()+X1-Full.Min.X,(X2-X1+1)*sizeof(uint16));
    {
        // Same persistent layer-aware path used by Unreal's heightmap importer.
        FHeightmapAccessor<false> Accessor(Landscape->GetLandscapeInfo());
        Accessor.SetEditLayer(Landscape->GetEditLayer(0)->GetGuid());
        Accessor.SetData(X1,Y1,X2,Y2,Region.GetData());Accessor.Flush();
    }
    Landscape->RequestLayersContentUpdate(ELandscapeLayerUpdateMode::Update_All);
    Landscape->ForceUpdateLayersContent();Landscape->MarkPackageDirty();
}
}

AGTProceduralRoad::AGTProceduralRoad()
{bIsEditorOnlyActor=true;ControlPoints=CreateDefaultSubobject<USplineComponent>(TEXT("RoadControlPoints"));SetRootComponent(ControlPoints);}
void AGTProceduralRoad::Rebuild(){if(Author)Author->Rebuild();}
void AGTProceduralRoad::ProjectPointsToBase()
{if(!Author||!Author->bHasBase)return;Modify();ControlPoints->Modify();for(int32 I=0;I<ControlPoints->GetNumberOfSplinePoints();++I){FVector P=ControlPoints->GetLocationAtSplinePoint(I,ESplineCoordinateSpace::World);P.Z=Author->BaseHeightAt(FVector2D(P));ControlPoints->SetLocationAtSplinePoint(I,P,ESplineCoordinateSpace::World,false);}ControlPoints->UpdateSpline();MarkPackageDirty();}
AGTProceduralGroundRegion::AGTProceduralGroundRegion()
{bIsEditorOnlyActor=true;Bounds=CreateDefaultSubobject<UBoxComponent>(TEXT("Region"));SetRootComponent(Bounds);Bounds->SetBoxExtent(FVector(3000,2000,500));Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);Bounds->ShapeColor=FColor(70,180,160);}
void AGTProceduralGroundRegion::Rebuild(){if(Author)Author->Rebuild();}
AGTProceduralGround::AGTProceduralGround()
{bIsEditorOnlyActor=true;GenerationBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("GenerationBounds"));SetRootComponent(GenerationBounds);GenerationBounds->SetBoxExtent(FVector(25600,16000,15000));GenerationBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);}
bool AGTProceduralGround::Report(const FString& Message,bool Success)
{LastMessage=Message;UE_LOG(LogTemp,Display,TEXT("PROCEDURAL GROUND: %s"),*Message);MarkPackageDirty();return Success;}
bool AGTProceduralGround::Validate(bool RequireBase)
{
    if(!GetWorld()||GetWorld()->IsGameWorld()||!Landscape||!Landscape->GetLandscapeInfo()||!Surface)return Report(TEXT("Assign the landscape and surface in an editor world."),false);
    if(Landscape->GetEditLayers().Num()!=1)return Report(TEXT("This first version requires one base landscape edit layer; multilayer composition is not yet supported."),false);
    for(TActorIterator<AGTProceduralGround> It(GetWorld());It;++It)if(*It!=this && It->Landscape==Landscape && It->bHasBase)return Report(TEXT("Use one controller per landscape; add roads and regions to that controller."),false);
    if(!Landscape->GetActorRotation().IsNearlyZero()||!GetActorRotation().IsNearlyZero())return Report(TEXT("Landscape/controller rotation is unsupported; rotate roads or regions instead."),false);
    if(OutputAssetRoot.Len()<12||!OutputAssetRoot.StartsWith(TEXT("/Game/"))||!OutputAssetRoot.EndsWith(TEXT("/")))return Report(TEXT("Set a dedicated output asset folder ending in / ."),false);
    for(auto* T:{PaintTexture.Get(),StyleTexture.Get(),MacroTexture.Get()})
        if(!T||!T->GetPathName().StartsWith(OutputAssetRoot)||T->Source.GetSizeX()!=T->Source.GetSizeY()||T->Source.GetFormat()!=TSF_BGRA8)
            return Report(TEXT("All three masks must be owned BGRA textures in the dedicated output folder."),false);
    if(PaintTexture->Source.GetSizeX()>2048||PaintTexture->Source.GetSizeX()<2||StyleTexture->Source.GetSizeX()!=PaintTexture->Source.GetSizeX()||MacroTexture->Source.GetSizeX()!=PaintTexture->Source.GetSizeX())return Report(TEXT("Masks must share a resolution between 2 and 2048."),false);
    const FVector Extent=GenerationBounds->GetScaledBoxExtent();
    const double MaxExtent=bAllowLargeSparseRoadBounds?204800.:51200.;
    if(Extent.X<100||Extent.Y<100||Extent.X>MaxExtent||Extent.Y>MaxExtent)return Report(TEXT("Generation bounds exceed the selected 1024m standard / 4096m sparse-road limit."),false);
    if(bAllowLargeSparseRoadBounds)
    {
        if(!ScatterRules.IsEmpty())return Report(TEXT("Large sparse-road bounds cannot scatter vegetation; use the map ecology layer."),false);
        for(TActorIterator<AGTProceduralGroundRegion> It(GetWorld());It;++It)if(It->Author==this)return Report(TEXT("Large sparse-road bounds cannot contain broad ground regions."),false);
    }
    if(RequireBase)
    {
        if(!bHasBase||CapturedLandscape!=Landscape||!BaseTransform.Equals(Landscape->GetActorTransform())||AtlasSize!=PaintTexture->Source.GetSizeX()||AtlasOrigin!=Surface->PaintOriginCm||AtlasSpan!=Surface->PaintSizeCm)return Report(TEXT("Base capture missing or bindings changed. Clear the old output before capturing a new base."),false);
        const TArray<FString> Paths={PaintTexture->GetPathName(),StyleTexture->GetPathName(),MacroTexture->GetPathName()};
        if(Paths!=CapturedTexturePaths)return Report(TEXT("Captured texture bindings changed; restore the original bindings first."),false);
    }
    return true;
}
bool AGTProceduralGround::CaptureBase()
{
    if(!Validate(false))return false;
    if(bHasBase)return Report(TEXT("Base already captured. Rebuild/Clear reuse it; no accidental recapture of generated terrain."),false);
    auto* Info=Landscape->GetLandscapeInfo();int32 X1,Y1,X2,Y2;
    if(!Info->GetLandscapeExtent(X1,Y1,X2,Y2)||int64(X2-X1+1)*(Y2-Y1+1)>4200000)return Report(TEXT("Unsupported or unloaded landscape extent."),false);
    TArray<uint8> P,S,M;if(!GTGroundAuthoring::Read(PaintTexture,P)||!GTGroundAuthoring::Read(StyleTexture,S)||!GTGroundAuthoring::Read(MacroTexture,M))return Report(TEXT("Could not read base masks."),false);
    Modify();HeightBounds=FIntRect(X1,Y1,X2+1,Y2+1);BaseTransform=Landscape->GetActorTransform();CapturedLandscape=Landscape;
    BaseHeights.SetNum(HeightBounds.Width()*HeightBounds.Height());FLandscapeEditDataInterface Edit(Info,Landscape->GetEditLayer(0)->GetGuid());Edit.GetHeightDataFast(X1,Y1,X2,Y2,BaseHeights.GetData(),0);
    BasePaint=MoveTemp(P);BaseStyle=MoveTemp(S);BaseMacro=MoveTemp(M);AtlasSize=PaintTexture->Source.GetSizeX();AtlasOrigin=Surface->PaintOriginCm;AtlasSpan=Surface->PaintSizeCm;
    CapturedTexturePaths={PaintTexture->GetPathName(),StyleTexture->GetPathName(),MacroTexture->GetPathName()};bHasBase=true;
    return Report(FString::Printf(TEXT("Base captured: %dx%d terrain, %dx%d masks. Rebuild is non-accumulating."),HeightBounds.Width(),HeightBounds.Height(),AtlasSize,AtlasSize),true);
}
float AGTProceduralGround::BaseHeightAt(FVector2D XY) const
{
    if(!bHasBase||BaseHeights.IsEmpty())return 0;
    const FVector Q=BaseTransform.InverseTransformPosition(FVector(XY,0));
    const double X=FMath::Clamp(Q.X-double(HeightBounds.Min.X),0.,double(HeightBounds.Width()-1)),Y=FMath::Clamp(Q.Y-double(HeightBounds.Min.Y),0.,double(HeightBounds.Height()-1));
    const int32 I=FMath::Min(int32(X),HeightBounds.Width()-2),J=FMath::Min(int32(Y),HeightBounds.Height()-2);const float U=X-I,V=Y-J;
    auto H=[&](int32 A,int32 B){return float(BaseHeights[B*HeightBounds.Width()+A]);};
    // Match the landscape's two-triangle interpolation, not bilinear smoothing.
    const float A=H(I,J),B=H(I+1,J),C=H(I,J+1),D=H(I+1,J+1);
    const float Enc=U>=V?A+(B-A)*U+(D-B)*V:A+(D-C)*U+(C-A)*V;
    return BaseTransform.TransformPosition(FVector(0,0,(Enc-32768.f)/128.f)).Z;
}
FString AGTProceduralGround::BaseTerrainDigest() const{return GTGroundAuthoring::Digest(BaseHeights.GetData(),BaseHeights.Num()*sizeof(uint16));}
FString AGTProceduralGround::CurrentTerrainDigest() const
{
    if(!Landscape||!bHasBase)return TEXT("Missing base");TArray<uint16> Data;Data.SetNum(BaseHeights.Num());
    FLandscapeEditDataInterface Edit(Landscape->GetLandscapeInfo(),Landscape->GetEditLayer(0)->GetGuid());Edit.GetHeightDataFast(HeightBounds.Min.X,HeightBounds.Min.Y,HeightBounds.Max.X-1,HeightBounds.Max.Y-1,Data.GetData(),0);
    return GTGroundAuthoring::Digest(Data.GetData(),Data.Num()*sizeof(uint16));
}
void AGTProceduralGround::WriteTextures(const TArray<uint8>& P,const TArray<uint8>& S,const TArray<uint8>& M)
{
    GTGroundAuthoring::Write(PaintTexture,P,AtlasSize);GTGroundAuthoring::Write(StyleTexture,S,AtlasSize);GTGroundAuthoring::Write(MacroTexture,M,AtlasSize);
    Surface->Modify();Surface->PaintTexture=PaintTexture;Surface->PaintResolution=AtlasSize;Surface->MaterialResolution=AtlasSize;
    Surface->PaintCells.SetNum(AtlasSize*AtlasSize);Surface->MaterialCells.SetNum(AtlasSize*AtlasSize);
    for(int32 I=0;I<AtlasSize*AtlasSize;++I)
    {const uint8* A=P.GetData()+I*4;const uint8* B=S.GetData()+I*4;Surface->PaintCells[I]=FLinearColor(A[2]*50.f/255,-A[1]*50.f/255,A[0]/255.f,A[3]/255.f);Surface->MaterialCells[I]=FLinearColor(B[2]/255.f,B[1]/255.f,B[0]/255.f,B[3]/255.f);}
    Surface->MarkPackageDirty();
}
bool AGTProceduralGround::Rebuild()
{
    using namespace GTGroundAuthoring;
    if(!Validate(true))return false;
    // Validate before touching saved data or output actors.
    for(const auto& Rule:ScatterRules)
    {
        if(Rule.Meshes.IsEmpty()||Rule.CandidateBudget<4||Rule.CandidateBudget>800||Rule.MinMapDensity<=0||Rule.MinMapDensity>=1||Rule.MinimumScale>Rule.MaximumScale||Rule.ClusterScaleCm<100||Rule.VergeWidthCm<100||Rule.MeshFootprintCm<0||Rule.MeshHeightCm<0||(Rule.MeshFootprintCm>0&&Rule.MeshHeightCm>0)||Rule.ClusterStrength<0||Rule.ClusterStrength>1||Rule.ScaleMapContrast<1||Rule.ScaleMapContrast>4)return Report(TEXT("Invalid scatter rule; no changes applied."),false);
        if(!Rule.Variants.IsEmpty()&&Rule.Variants.Num()!=Rule.Meshes.Num())return Report(TEXT("Provide one variant range per mesh, or leave variants empty."),false);
        for(const auto& V:Rule.Variants)if(V.MinMapScale<0||V.MaxMapScale>1||V.MinMapScale>V.MaxMapScale||V.MinSize<.25f||V.MaxSize>4||V.MinSize>V.MaxSize||V.ScaleRandom<0||V.ScaleRandom>2)return Report(TEXT("Invalid native plant variant range; no changes applied."),false);
        for(UStaticMesh* Mesh:Rule.Meshes)if(!Mesh||(Rule.bSolid&&(!Mesh->GetBodySetup()||Mesh->GetBodySetup()->AggGeom.GetElementCount()==0)))return Report(TEXT("A scatter mesh is missing, or solid debris lacks prepared simple collision."),false);
    }
    FContext Context(this);
    int32 ExpectedRoads=0;for(TActorIterator<AGTProceduralRoad> It(GetWorld());It;++It)if(It->Author==this)++ExpectedRoads;
    if(ExpectedRoads!=Context.Paths.Num())return Report(TEXT("A road has duplicate/invalid control points. No changes applied."),false);
    bool HaveRelief=false;
    bool WantsWater=false;
    for(const auto& Path:Context.Paths)for(const auto& C:Path.Actor->Conditions)
    {
        if(!FMath::IsFinite(C.BasinDepthCm)||C.BasinDepthCm<0||C.BasinDepthCm>100)return Report(TEXT("Bog basin depth must be 0..100 cm; no changes applied."),false);
        if(!FMath::IsFinite(C.StartMetres)||!FMath::IsFinite(C.EndMetres)||!FMath::IsFinite(C.BlendMetres)||!FMath::IsFinite(C.MudDepthCm)||!FMath::IsFinite(C.RutDepthCm)||!FMath::IsFinite(C.Wetness)||!FMath::IsFinite(C.Firmness)||!FMath::IsFinite(C.GrassCover)||!FMath::IsFinite(C.WaterFillCm)||C.StartMetres<0||C.EndMetres<=C.StartMetres||C.BlendMetres<1||C.MudDepthCm<0||C.MudDepthCm>100||C.RutDepthCm<0||C.RutDepthCm>70||C.Wetness<0||C.Wetness>1||C.Firmness<0||C.Firmness>1||C.GrassCover<0||C.GrassCover>1||C.WaterFillCm<0||C.WaterFillCm>40||!FMath::IsFinite(C.TrackSpreadCm)||C.TrackSpreadCm<0||C.TrackSpreadCm>300||!FMath::IsFinite(C.Churn)||C.Churn<0||C.Churn>1||!FMath::IsFinite(C.CrossingTracks)||C.CrossingTracks<0||C.CrossingTracks>1||!FMath::IsFinite(C.BreakupCm)||C.BreakupCm<0||C.BreakupCm>20)return Report(TEXT("Invalid road condition. Check metre range, blend and soil/water limits; no changes applied."),false);
        HaveRelief=true;WantsWater|=!Path.Actor->bFirmGravel && C.WaterFillCm>0;
    }
    if(WantsWater&&(!RoadWaterMaterial||!Surface->SimulatedWater||!Surface->SimulatedWater->WaterDomain))return Report(TEXT("Road pools require a water material and an existing simulated water domain."),false);
    for(const auto& Path:Context.Paths)if(Path.Actor->bApplyRelief && Path.Actor->ReliefTexture)
    {
        if(Path.Pixels.IsEmpty()||Path.Actor->ReliefDefaultWidthCm<100||Path.Actor->ReliefDiffuseAspect<.1f||!FMath::IsFinite(Path.Actor->ReliefStrength)||Path.Actor->ReliefStrength<0||Path.Actor->ReliefStrength>2)
            return Report(TEXT("Invalid road relief texture/parameters. No changes applied."),false);
        HaveRelief=true;
    }
    if(HaveRelief&&(!ReliefMaterial||ReliefSpacingCm<12.5f||ReliefSpacingCm>50||!FMath::IsNearlyEqual(BaseTransform.GetScale3D().X,BaseTransform.GetScale3D().Y)))return Report(TEXT("Fine relief needs a material, 12.5–50cm spacing and square landscape cells."),false);
    const FVector Centre=GenerationBounds->GetComponentLocation(),Extent=GenerationBounds->GetScaledBoxExtent();
    const FBox2D Bounds(FVector2D(Centre-Extent),FVector2D(Centre+Extent));
    FBox2D RoadWaterBounds(ForceInit);
    if(WantsWater)
    {
        for(const auto& Path:Context.Paths)for(const auto& C:Path.Actor->Conditions)if(C.WaterFillCm>0)
            for(const auto& P:Path.Points)if(P.S>=C.StartMetres-2&&P.S<=C.EndMetres+2)
            {const FVector2D Margin(P.Width*.5+1000,P.Width*.5+1000);RoadWaterBounds+=FVector2D(P.P)-Margin;RoadWaterBounds+=FVector2D(P.P)+Margin;}
        if(!RoadWaterBounds.bIsValid)return Report(TEXT("Wet condition lies outside the road; check its metre range."),false);
        RoadWaterBounds.Min.X=FMath::Max(RoadWaterBounds.Min.X,Bounds.Min.X);RoadWaterBounds.Min.Y=FMath::Max(RoadWaterBounds.Min.Y,Bounds.Min.Y);
        RoadWaterBounds.Max.X=FMath::Min(RoadWaterBounds.Max.X,Bounds.Max.X);RoadWaterBounds.Max.Y=FMath::Min(RoadWaterBounds.Max.Y,Bounds.Max.Y);
        const auto Size=RoadWaterBounds.GetSize();
        // LT3's separated hollows over 714m need ~1.63M samples. Keep a finite
        // authoring allocation guard; this does not increase per-frame simulation.
        if(Size.X<=0||Size.Y<=0||int64(FMath::CeilToInt(Size.X/25)+2)*(FMath::CeilToInt(Size.Y/25)+2)>2000000)return Report(TEXT("Road pool survey is outside bounds or exceeds 2M samples; reduce wet stretches."),false);
    }
    const FVector Min=BaseTransform.InverseTransformPosition(FVector(Bounds.Min,0)),Max=BaseTransform.InverseTransformPosition(FVector(Bounds.Max,0));
    if(Min.X<HeightBounds.Min.X||Min.Y<HeightBounds.Min.Y||Max.X>=HeightBounds.Max.X-1||Max.Y>=HeightBounds.Max.Y-1)return Report(TEXT("Generation bounds must remain inside the captured landscape."),false);
    const double PatchSpan=BaseTransform.GetScale3D().X*4;
    const FVector2D PatchOrigin(BaseTransform.GetLocation());
    TSet<FIntPoint> PatchKeys;
    if(HaveRelief)for(int32 Y=FMath::FloorToInt(Min.Y/4);Y<=FMath::FloorToInt(Max.Y/4);++Y)
    for(int32 X=FMath::FloorToInt(Min.X/4);X<=FMath::FloorToInt(Max.X/4);++X)
    {
        const FVector2D P=PatchOrigin+FVector2D(X,Y)*PatchSpan;
        if(!Bounds.IsInside(P)||!Bounds.IsInside(P+FVector2D(PatchSpan,PatchSpan)))continue;
        const auto F=Context.At(P+FVector2D(PatchSpan*.5,PatchSpan*.5));
        if(F.Distance<F.HalfWidth+PatchSpan*.71+200)PatchKeys.Add(FIntPoint(X,Y));
    }
    const int32 PatchIntervals=FMath::CeilToInt(PatchSpan/FMath::Max(12.5f,ReliefSpacingCm));
    if(int64(PatchKeys.Num())*FMath::Square(PatchIntervals+1)>1200000)return Report(TEXT("Fine relief exceeds 1.2M vertex budget; reduce bounds/roads or increase spacing."),false);
    auto PatchFade=[&](FVector2D P)
    {
        const FVector2D Q=(P-PatchOrigin)/PatchSpan;const FIntPoint K(FMath::FloorToInt(Q.X),FMath::FloorToInt(Q.Y));
        if(!PatchKeys.Contains(K))return 0.f;
        double Distance=PatchSpan;
        for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)if(!PatchKeys.Contains(K+FIntPoint(X,Y)))
        {
            const FVector2D Lo=PatchOrigin+FVector2D(K.X+X,K.Y+Y)*PatchSpan,Hi=Lo+FVector2D(PatchSpan,PatchSpan);
            Distance=FMath::Min(Distance,FVector2D::Distance(P,FVector2D(FMath::Clamp(P.X,Lo.X,Hi.X),FMath::Clamp(P.Y,Lo.Y,Hi.Y))));
        }
        return Smooth(0,PatchSpan*.25f,Distance);
    };
    Modify();TArray<uint16> Heights=BaseHeights;TArray<uint8> Paint=BasePaint,Style=BaseStyle,Macro=BaseMacro;
    auto Weight=[&](FVector2D P){return Smooth(0,800,FMath::Min(FMath::Min(P.X-Bounds.Min.X,Bounds.Max.X-P.X),FMath::Min(P.Y-Bounds.Min.Y,Bounds.Max.Y-P.Y)));};
    const int32 X1=FMath::FloorToInt(Min.X),Y1=FMath::FloorToInt(Min.Y),X2=FMath::CeilToInt(Max.X),Y2=FMath::CeilToInt(Max.Y);
    for(int32 Y=Y1;Y<=Y2;++Y)for(int32 X=X1;X<=X2;++X)
    {
        const FVector P=BaseTransform.TransformPosition(FVector(X,Y,0));const FVector2D XY(P);const auto F=Context.At(XY);
        const float H=FMath::Lerp(BaseHeightAt(XY),F.Height,Weight(XY));
        Heights[(Y-HeightBounds.Min.Y)*HeightBounds.Width()+X-HeightBounds.Min.X]=uint16(FMath::Clamp(FMath::RoundToInt((H-BaseTransform.GetLocation().Z)/BaseTransform.GetScale3D().Z*128+32768),0,65535));
    }
    // Restore the previous footprint too when the authoring box or roads move.
    FBox2D Dirty=Bounds;if(PreviousBounds.bIsValid)Dirty+=PreviousBounds;
    const FVector DMin=BaseTransform.InverseTransformPosition(FVector(Dirty.Min,0)),DMax=BaseTransform.InverseTransformPosition(FVector(Dirty.Max,0));
    const int32 DX1=FMath::Clamp(FMath::FloorToInt(DMin.X)-1,HeightBounds.Min.X,HeightBounds.Max.X-1),DY1=FMath::Clamp(FMath::FloorToInt(DMin.Y)-1,HeightBounds.Min.Y,HeightBounds.Max.Y-1);
    const int32 DX2=FMath::Clamp(FMath::CeilToInt(DMax.X)+1,HeightBounds.Min.X,HeightBounds.Max.X-1),DY2=FMath::Clamp(FMath::CeilToInt(DMax.Y)+1,HeightBounds.Min.Y,HeightBounds.Max.Y-1);
    auto NewHeight=[&](FVector2D XY)
    {
        const FVector Q=BaseTransform.InverseTransformPosition(FVector(XY,0));const double X=Q.X-HeightBounds.Min.X,Y=Q.Y-HeightBounds.Min.Y;
        const int32 I=FMath::Clamp(int32(X),0,HeightBounds.Width()-2),J=FMath::Clamp(int32(Y),0,HeightBounds.Height()-2);const float U=FMath::Clamp(float(X-I),0.f,1.f),V=FMath::Clamp(float(Y-J),0.f,1.f);
        auto H=[&](int32 A,int32 B){return float(Heights[B*HeightBounds.Width()+A]);};const float A=H(I,J),B=H(I+1,J),C=H(I,J+1),D=H(I+1,J+1);
        return float(BaseTransform.TransformPosition(FVector(0,0,((U>=V?A+(B-A)*U+(D-B)*V:A+(D-C)*U+(C-A)*V)-32768)/128)).Z);
    };
    // Build all new samples before removing old outputs. Tiles align with four
    // landscape quads; outer boundaries retain the exact coarse triangle heights.
    auto FineHeight=[&](FVector2D P)
    {
        const auto F=Context.At(P);const float Fade=PatchFade(P)*Weight(P);
        return NewHeight(P)+(F.Height-NewHeight(P)+F.Relief)*Fade;
    };
    TMap<FIntPoint,TObjectPtr<AGTRoadReliefTile>> NextTiles;
    ChangedReliefTiles=RetainedReliefTiles=ReliefTriangles=0;
    TArray<FIntPoint> OrderedKeys=PatchKeys.Array();OrderedKeys.Sort([](FIntPoint A,FIntPoint B){return A.Y==B.Y?A.X<B.X:A.Y<B.Y;});
    for(FIntPoint Key:OrderedKeys)
    {
        const FVector2D O=PatchOrigin+FVector2D(Key)*PatchSpan;const double Step=PatchSpan/PatchIntervals;
        TArray<float> Samples;TArray<FVector> Normals;TArray<FLinearColor> Soil;Samples.Reserve(FMath::Square(PatchIntervals+1));Normals.Reserve(Samples.Max());
        // Sample a halo once for continuous geometric normals across tile edges.
        const int32 HaloRow=PatchIntervals+3;TArray<float> Halo;Halo.SetNum(HaloRow*HaloRow);
        for(int32 Y=-1;Y<=PatchIntervals+1;++Y)for(int32 X=-1;X<=PatchIntervals+1;++X)Halo[(Y+1)*HaloRow+X+1]=FineHeight(O+FVector2D(X,Y)*Step);
        for(int32 Y=0;Y<=PatchIntervals;++Y)for(int32 X=0;X<=PatchIntervals;++X)
        {
            const int32 I=(Y+1)*HaloRow+X+1;Samples.Add(Halo[I]);
            Normals.Add(FVector(-(Halo[I+1]-Halo[I-1])/(2*Step),-(Halo[I+HaloRow]-Halo[I-HaloRow])/(2*Step),1).GetSafeNormal());
            const FVector2D P=O+FVector2D(X,Y)*Step;const auto F=Context.At(P);
            // Keep old paint exactly where there are no condition overrides.
            // Captured atlas supplies the blend at section/tile boundaries.
            const int32 PX=FMath::Clamp(int32((P.X-AtlasOrigin.X)/AtlasSpan*AtlasSize),0,AtlasSize-1),PY=FMath::Clamp(int32((P.Y-AtlasOrigin.Y)/AtlasSpan*AtlasSize),0,AtlasSize-1),PaintIndex=(PY*AtlasSize+PX)*4;
            const float DepthScale=Surface->bUseSoilShearResponse?FMath::Clamp(Surface->LayerDepthScale,.1f,3.f):1.f;
            FLinearColor Base(BasePaint[PaintIndex+2]*50.f/255*DepthScale,-BasePaint[PaintIndex+1]*50.f/255,BasePaint[PaintIndex]/255.f,BasePaint[PaintIndex+3]/255.f);
            Soil.Add(F.Condition>0?FMath::Lerp(Base,FLinearColor(F.Mud,Base.G,F.Firm,F.Condition>0?F.Softness:F.Wet),PatchFade(P)*Weight(P)*(1-F.Exclude)):FLinearColor(-1,0,0,0));
        }
        const FString Signature=Digest(Samples.GetData(),Samples.Num()*sizeof(float))+Digest(Normals.GetData(),Normals.Num()*sizeof(FVector))+Digest(Soil.GetData(),Soil.Num()*sizeof(FLinearColor))+ReliefMaterial->GetPathName();
        AGTRoadReliefTile* Tile=ReliefTiles.FindRef(Key);
        if(IsValid(Tile)&&Tile->Signature==Signature)++RetainedReliefTiles;
        else
        {
            auto* New=GetWorld()->SpawnActor<AGTRoadReliefTile>(FVector(O,0),FRotator::ZeroRotator);
            New->SetActorLabel(FString::Printf(TEXT("RoadRelief_%d_%d"),Key.X,Key.Y));New->Surface=Surface;New->Intervals=PatchIntervals;New->SpanCm=PatchSpan;
            New->Heights=MoveTemp(Samples);New->Normals=MoveTemp(Normals);New->Soil=MoveTemp(Soil);New->Signature=Signature;New->Mesh->SetMaterial(0,ReliefMaterial);New->BuildMesh();New->MarkPackageDirty();
            if(IsValid(Tile))GetWorld()->DestroyActor(Tile);Tile=New;++ChangedReliefTiles;
        }
        NextTiles.Add(Key,Tile);ReliefTriangles+=Tile->TriangleCount();
    }
    for(auto& Pair:ReliefTiles)if(!NextTiles.Contains(Pair.Key)&&IsValid(Pair.Value))GetWorld()->DestroyActor(Pair.Value);
    ReliefTiles=MoveTemp(NextTiles);Surface->Modify();Surface->RoadReliefTiles=ReliefTiles;Surface->RoadTileOrigin=PatchOrigin;Surface->RoadTileSpanCm=PatchSpan;
    auto GroundHeight=[&](FVector2D P)
    {
        const FVector2D Q=(P-PatchOrigin)/PatchSpan;
        if(AGTRoadReliefTile* Tile=ReliefTiles.FindRef(FIntPoint(FMath::FloorToInt(Q.X),FMath::FloorToInt(Q.Y))))return Tile->HeightAt(P);
        return NewHeight(P);
    };
#include "GTProceduralRoadWater.inl"
    for(int32 Y=1;Y<AtlasSize-1;++Y)for(int32 X=1;X<AtlasSize-1;++X)
    {
        const FVector2D P=AtlasOrigin+FVector2D(X+.5,Y+.5)*(AtlasSpan/AtlasSize);if(!Bounds.IsInside(P))continue;
        auto F=Context.At(P);const float Corridor=bAllowLargeSparseRoadBounds?1-Smooth(F.HalfWidth,F.HalfWidth+300,F.Distance):1.f;if(Corridor<=0)continue;const float A=Weight(P)*(1-F.Exclude)*Corridor;const int32 I=(Y*AtlasSize+X)*4;
        auto Byte=[&](float V){return uint8(FMath::Clamp(FMath::RoundToInt(V*255),0,255));};
        const float DepthScale=Surface->bUseSoilShearResponse?FMath::Clamp(Surface->LayerDepthScale,.1f,3.f):1.f;
        Paint[I+2]=Byte(FMath::Lerp(BasePaint[I+2]/255.f,F.Mud/(50.f*DepthScale),A));
        Paint[I]=Byte(FMath::Lerp(BasePaint[I]/255.f,F.Firm,A));Paint[I+3]=Byte(FMath::Lerp(BasePaint[I+3]/255.f,F.Condition>0?F.Softness:F.Wet,A));
        Style[I+2]=Byte(FMath::Lerp(BaseStyle[I+2]/255.f,0.f,A));Style[I+1]=Byte(FMath::Lerp(BaseStyle[I+1]/255.f,F.Grass,A));Style[I]=Byte(FMath::Lerp(BaseStyle[I]/255.f,F.Wet,A));
        // Authored soil conditions override exposed-rock material only in their mask.
        Style[I+3]=Byte(BaseStyle[I+3]/255.f*(1-A*F.Condition));
        const uint16 Packed=uint16(FMath::Clamp(FMath::RoundToInt(GroundHeight(P)/65536.f*65535.f),0,65535));Macro[I+2]=Packed>>8;Macro[I+1]=Packed&255;
    }
    WriteTextures(Paint,Style,Macro);
    // Cell outputs are generated first, compared by their actual instance hash,
    // and only changed cells are replaced. No dependence on traversal order.
    TArray<FGTGeneratedGroundCell> Next;ChangedCells=RetainedCells=InstanceCount=0;FMD5 Combined;
    TArray<FPatternBank> Banks;for(int32 R=0;R<ScatterRules.Num();++R)Banks.Add(Patterns(ScatterRules[R].CandidateBudget,CellSeed(0,0,Seed,R+1)));
    constexpr double Tile=6400;
    for(int32 TY=FMath::FloorToInt(Bounds.Min.Y/Tile);TY<=FMath::FloorToInt((Bounds.Max.Y-.01)/Tile);++TY)
    for(int32 TX=FMath::FloorToInt(Bounds.Min.X/Tile);TX<=FMath::FloorToInt((Bounds.Max.X-.01)/Tile);++TX)
    {
        TArray<TArray<TArray<FTransform>>> Groups;Groups.SetNum(ScatterRules.Num());uint32 Hash=0;int32 Count=0;
        for(int32 R=0;R<ScatterRules.Num();++R)
        {
            const auto& Rule=ScatterRules[R];Groups[R].SetNum(Rule.Meshes.Num());
            TArray<FVector2f> Ranges;for(const auto& V:Rule.Variants)Ranges.Add(FVector2f(V.MinMapScale,V.MaxMapScale));
            Hash=FCrc::StrCrc32(*Rule.Name.ToString(),Hash);Hash=FCrc::MemCrc32(&Rule.bSolid,sizeof(bool),Hash);Hash=FCrc::MemCrc32(&Rule.CullDistanceCm,sizeof(float),Hash);
            const bool Shadow=Rule.bCastShadow&&!Rule.bRoadDebris;Hash=FCrc::MemCrc32(&Shadow,sizeof(bool),Hash);
            for(UStaticMesh* Mesh:Rule.Meshes)Hash=FCrc::StrCrc32(*Mesh->GetPathName(),Hash);
            for(UMaterialInterface* Material:Rule.MaterialOverrides)Hash=FCrc::StrCrc32(Material?*Material->GetPathName():TEXT("None"),Hash);
            for(int32 SY=0;SY<8;++SY)for(int32 SX=0;SX<8;++SX)
            {
                const int32 GX=TX*8+SX,GY=TY*8+SY;FRandom Random(CellSeed(GX,GY,Seed,R+100));const int32 Pattern=(Random.Next()*16)>>15;
                for(auto Point:Banks[R][Pattern])
                {
                    const FVector2D P((GX+.5)*800+Point.X*100,(GY+.5)*800+Point.Y*100);if(!Bounds.IsInside(P))continue;
                    const auto F=Context.At(P);float D=Rule.Density*Weight(P)*(1-F.Exclude);
                    const auto Habitat=Rule.bRoadDebris?EGTScatterHabitat::Road:Rule.Habitat;
                    if(Habitat==EGTScatterHabitat::Woodland)D*=F.Forest;
                    if(Habitat==EGTScatterHabitat::Road)D*=F.Road;
                    else D*=Smooth(F.HalfWidth+Rule.RoadClearanceCm,F.HalfWidth+Rule.RoadClearanceCm+150,F.Distance);
                    if(Habitat==EGTScatterHabitat::Verge)D*=1-Smooth(F.HalfWidth+Rule.VergeWidthCm*.5f,F.HalfWidth+Rule.VergeWidthCm,F.Distance);
                    const int32 Channel=Seed+Rule.SeedOffset;
                    const float Cluster=Smooth(.22f,.78f,Noise(P,Channel+167,Rule.ClusterScaleCm));
                    D*=FMath::Lerp(1.f,Cluster,Rule.ClusterStrength);
                    if(!Density(D,Rule.MinMapDensity,1,1,Random))continue;
                    const float H=GroundHeight(P),DX=(GroundHeight(P+FVector2D(100,0))-GroundHeight(P-FVector2D(100,0)))/200,DY=(GroundHeight(P+FVector2D(0,100))-GroundHeight(P-FVector2D(0,100)))/200;
                    if(FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(DX*DX+DY*DY)))>Rule.MaximumSlopeDegrees)continue;
                    if(Surface->SimulatedWater&&Surface->SimulatedWater->Covers(P)&&Surface->SimulatedWater->SurfaceCmAt(P)>H+2)continue;
                    const float Green=FMath::Clamp(.5f+(Noise(P,Channel+73,1900)-.5f)*Rule.ScaleMapContrast,0.f,1.f);
                    const int32 Variant=Ranges.IsEmpty()?int32((Random.Next()*Rule.Meshes.Num())>>15):SelectVariant(Green,Ranges,Random);
                    if(Variant==INDEX_NONE)continue;
                    const auto Box=Rule.Meshes[Variant]->GetBounds();
                    const auto V=Rule.Variants.IsEmpty()?FGTGroundPlantVariant():Rule.Variants[Variant];
                    const float Size=Scale(Green,V.MinMapScale,V.MaxMapScale,Rule.Variants.IsEmpty()?Rule.MinimumScale:V.MinSize,Rule.Variants.IsEmpty()?Rule.MaximumScale:V.MaxSize,Rule.Variants.IsEmpty()?Rule.ScaleRandom:V.ScaleRandom,Random)*(Rule.MeshHeightCm>0?Rule.MeshHeightCm/FMath::Max(1.f,float(2*Box.BoxExtent.Z)):Rule.MeshFootprintCm>0?Rule.MeshFootprintCm/FMath::Max(1.f,float(2*FMath::Max(Box.BoxExtent.X,Box.BoxExtent.Y))):1.f),Yaw=Random.Unit()*360;
                    const float Root=(Box.Origin.Z-Box.BoxExtent.Z)*Size;
                    const FQuat Rotation=Rule.bAlignToGround?FQuat::FindBetweenNormals(FVector::UpVector,FVector(-DX,-DY,1).GetSafeNormal())*FRotator(0,Yaw,0).Quaternion():FRotator(0,Yaw,0).Quaternion();
                    const FVector Position(P,H-Root-2);const FTransform T(Rotation,Position,FVector(Size));Groups[R][Variant].Add(T);++Count;
                    const double Orientation[]={Rotation.X,Rotation.Y,Rotation.Z,Rotation.W};Hash=FCrc::MemCrc32(Orientation,sizeof(Orientation),Hash);
                    const double Values[]={Position.X,Position.Y,Position.Z,double(Yaw),double(Size),double(R),double(Variant)};Hash=FCrc::MemCrc32(Values,sizeof(Values),Hash);
                }
            }
        }
        const FIntPoint Key(TX,TY);auto* Old=GeneratedCells.FindByPredicate([&](const auto& C){return C.Key==Key;});
        FGTGeneratedGroundCell Cell;Cell.Key=Key;Cell.Signature=Hash;Cell.Instances=Count;
        if(Old&&Old->Signature==Hash&&IsValid(Old->Output)){Cell.Output=Old->Output;++RetainedCells;}
        else
        {
            if(Old&&IsValid(Old->Output)){Old->Output->Modify();GetWorld()->DestroyActor(Old->Output);}
            auto* Output=GetWorld()->SpawnActor<AActor>();Output->SetActorLabel(FString::Printf(TEXT("GeneratedGround_%d_%d"),TX,TY));Output->Tags.Add(TEXT("GT.ProceduralGround.Output"));
            auto* Root=NewObject<USceneComponent>(Output,TEXT("Root"),RF_Transactional);Root->SetMobility(EComponentMobility::Static);Output->AddInstanceComponent(Root);Output->SetRootComponent(Root);Root->RegisterComponent();Output->SetActorLocation(FVector(TX*Tile,TY*Tile,0));
            for(int32 R=0;R<Groups.Num();++R)for(int32 V=0;V<Groups[R].Num();++V)
            {
                if(Groups[R][V].IsEmpty())continue;const auto& Rule=ScatterRules[R];
                auto* C=NewObject<UHierarchicalInstancedStaticMeshComponent>(Output,NAME_None,RF_Transactional);Output->AddInstanceComponent(C);C->SetupAttachment(Root);C->SetStaticMesh(Rule.Meshes[V]);C->SetMobility(EComponentMobility::Static);
                for(int32 Slot=0;Slot<Rule.MaterialOverrides.Num();++Slot)if(Rule.MaterialOverrides[Slot])C->SetMaterial(Slot,Rule.MaterialOverrides[Slot]);
                C->ComponentTags.Add(Rule.Name);C->SetCollisionProfileName(Rule.bSolid?TEXT("BlockAll"):TEXT("NoCollision"));C->SetCollisionEnabled(Rule.bSolid?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);C->SetCullDistances(int32(Rule.CullDistanceCm*.75f),Rule.CullDistanceCm);C->SetCastShadow(Rule.bCastShadow&&!Rule.bRoadDebris);C->bVisibleInRayTracing=false;C->bAffectDistanceFieldLighting=false;C->RegisterComponent();C->AddInstances(Groups[R][V],false,true);C->MarkRenderStateDirty();
            }
            Output->MarkPackageDirty();Cell.Output=Output;++ChangedCells;
        }
        Combined.Update(reinterpret_cast<const uint8*>(&Hash),sizeof(Hash));Next.Add(Cell);InstanceCount+=Count;
    }
    for(auto& Old:GeneratedCells)if(!Next.ContainsByPredicate([&](const auto& C){return C.Key==Old.Key;}))if(IsValid(Old.Output))GetWorld()->DestroyActor(Old.Output);
    GeneratedCells=MoveTemp(Next);PreviousBounds=Bounds;
    // Recess the covered coarse collision/render surface, never the patch's
    // shared outer edge. This prevents a hidden flat landscape filling the ruts.
    for(int32 Y=Y1;Y<=Y2;++Y)for(int32 X=X1;X<=X2;++X)
    {
        const FVector P=BaseTransform.TransformPosition(FVector(X,Y,0));const float Lower=FMath::Clamp(LandscapeRecessDepthCm,0.f,400.f)*PatchFade(FVector2D(P))*Weight(FVector2D(P));
        const int32 I=(Y-HeightBounds.Min.Y)*HeightBounds.Width()+X-HeightBounds.Min.X;
        Heights[I]=uint16(FMath::Clamp(FMath::RoundToInt(Heights[I]-Lower/BaseTransform.GetScale3D().Z*128),0,65535));
    }
    Landscape->Modify();WriteHeights(Landscape,HeightBounds,Heights,DX1,DY1,DX2,DY2);
    for(auto Key:OrderedKeys)Combined.Update(reinterpret_cast<const uint8*>(*ReliefTiles[Key]->Signature),ReliefTiles[Key]->Signature.Len()*sizeof(TCHAR));
    if(GeneratedWaterDomain&&Surface->SimulatedWater&&Surface->SimulatedWater->WaterDomain==GeneratedWaterDomain)for(const UGTWaterDomain* P:GeneratedWaterDomain->RoadPatches)Combined.Update(reinterpret_cast<const uint8*>(P->Samples.GetData()),P->Samples.Num()*sizeof(float));
    Combined.Update(reinterpret_cast<const uint8*>(Heights.GetData()),Heights.Num()*2);Combined.Update(Paint.GetData(),Paint.Num());Combined.Update(Style.GetData(),Style.Num());uint8 Sum[16];Combined.Final(Sum);OutputDigest=BytesToHex(Sum,16);
    ShowGeneratedRoads();return Report(FString::Printf(TEXT("Generated %d instances in %d scatter cells; %d relief tiles, %d triangles (%.1fcm spacing). Save All to retain map + masks."),InstanceCount,GeneratedCells.Num(),ReliefTiles.Num(),ReliefTriangles,PatchSpan/PatchIntervals),true);
}
bool AGTProceduralGround::ClearGenerated()
{
    if(!Validate(true))return false;Modify();Landscape->Modify();
    if(PreviousBounds.bIsValid)
    {
        const FVector Min=BaseTransform.InverseTransformPosition(FVector(PreviousBounds.Min,0)),Max=BaseTransform.InverseTransformPosition(FVector(PreviousBounds.Max,0));
        const int32 X1=FMath::Clamp(FMath::FloorToInt(Min.X)-1,HeightBounds.Min.X,HeightBounds.Max.X-1),Y1=FMath::Clamp(FMath::FloorToInt(Min.Y)-1,HeightBounds.Min.Y,HeightBounds.Max.Y-1);
        const int32 X2=FMath::Clamp(FMath::CeilToInt(Max.X)+1,HeightBounds.Min.X,HeightBounds.Max.X-1),Y2=FMath::Clamp(FMath::CeilToInt(Max.Y)+1,HeightBounds.Min.Y,HeightBounds.Max.Y-1);
        GTGroundAuthoring::WriteHeights(Landscape,HeightBounds,BaseHeights,X1,Y1,X2,Y2);
    }
    WriteTextures(BasePaint,BaseStyle,BaseMacro);for(auto& Cell:GeneratedCells)if(IsValid(Cell.Output)){Cell.Output->Modify();GetWorld()->DestroyActor(Cell.Output);}
    for(auto& Pair:ReliefTiles)if(IsValid(Pair.Value))GetWorld()->DestroyActor(Pair.Value);
    ReliefTiles.Reset();Surface->RoadReliefTiles.Reset();ReliefTriangles=ChangedReliefTiles=RetainedReliefTiles=0;
    if(Surface->SimulatedWater)
    {
        auto* Sheet=Surface->SimulatedWater.Get();Sheet->Modify();
        if(BaseWaterDomain)Sheet->WaterDomain=BaseWaterDomain;
        if(IsValid(RoadWaterMesh)){Sheet->RoadPoolSurfaces.Remove(RoadWaterMesh->Mesh);GetWorld()->DestroyActor(RoadWaterMesh);RoadWaterMesh=nullptr;}
    }
    RoadPoolWetSamples=0;
    GeneratedCells.Reset();PreviousBounds=FBox2D(ForceInit);ChangedCells=RetainedCells=InstanceCount=0;OutputDigest=TEXT("");
    return Report(TEXT("Generated terrain/masks restored to the captured base; owned scatter removed. Road/region controls retained."),true);
}
void AGTProceduralGround::ShowGeneratedRoads()
{for(const auto& Road:GTGroundAuthoring::Roads(this))for(int32 I=1;I<Road.Points.Num();++I)DrawDebugLine(GetWorld(),Road.Points[I-1].P+FVector(0,0,35),Road.Points[I].P+FVector(0,0,35),FColor::Yellow,false,20,0,4);}

void AGTProceduralRoad::AddExampleConditions()
{
    if(!Conditions.IsEmpty())return; // Never replace the user's section edits.
    Modify();float Length=0;for(int32 I=1;I<ControlPoints->GetNumberOfSplinePoints();++I)Length+=FVector::Distance(ControlPoints->GetLocationAtSplinePoint(I-1,ESplineCoordinateSpace::World),ControlPoints->GetLocationAtSplinePoint(I,ESplineCoordinateSpace::World))*.01f;
    const float End=FMath::Min(Length,180.f);if(End<30)return;
    const TCHAR* Names[]={TEXT("Firm dirt"),TEXT("Worn grassy track"),TEXT("Shallow mud"),TEXT("Deep mud and rut pools")};
    const float Depth[]={2,10,25,65},Ruts[]={3,8,23,55},Wet[]={.2f,.45f,.75f,.95f},Firm[]={.85f,.55f,.2f,.05f},Grass[]={0,.65f,.08f,0};
    for(int32 I=0;I<4;++I){FGTRoadCondition C;C.Name=Names[I];C.StartMetres=I*End/4;C.EndMetres=(I+1)*End/4;C.BlendMetres=4;C.MudDepthCm=Depth[I];C.RutDepthCm=Ruts[I];C.Wetness=Wet[I];C.Firmness=Firm[I];C.GrassCover=Grass[I];C.WaterFillCm=I==3?18:0;Conditions.Add(C);}
    MarkPackageDirty();
}
