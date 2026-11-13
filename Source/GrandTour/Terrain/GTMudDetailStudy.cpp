#include "Terrain/GTMudDetailStudy.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"

AGTMudDetailStudy::AGTMudDetailStudy()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=.5f;
    PrimaryActorTick.TickGroup=TG_PostPhysics;
}

void AGTMudDetailStudy::SeedTracks()
{
    if (!Surface || !Surface->HasActorBegunPlay() || bSeeded) return;
    const FVector2D Origin(GetActorLocation());
    // Seed a route section only when its tiles are resident around the player.
    if (const APawn* Pawn=UGameplayStatics::GetPlayerPawn(this,0))
        if(FVector2D::Distance(FVector2D(Pawn->GetActorLocation()),Origin)>1500.f) return;
    auto Centre=[](float X) { return 110.f*FMath::Sin(X/410.f)+45.f*FMath::Sin(X/180.f); };
    for (int32 Pass=0;Pass<3;++Pass)
        for (int32 I=0;I<176;++I)
        {
            const float A=-1100.f+I*12.5f,B=A+12.5f;
            auto Line=[&](float X) { return Centre(X)+(Pass==2 ? 42.f*FMath::Sin(X/250.f+.7f) : 0.f); };
            const FVector2D Direction=FVector2D(B-A,Line(B)-Line(A)).GetSafeNormal();
            const FVector2D Side(-Direction.Y,Direction.X);
            const float Depth=(Pass==0 ? 7.f : 12.f)+6.f*(.5f+.5f*FMath::Sin(A/215.f+Pass*.8f));
            for (float Offset : {-88.f,88.f})
                Surface->StampWheel(Origin+FVector2D(A,Line(A))+Side*Offset,Origin+FVector2D(B,Line(B))+Side*Offset,Direction,28.f,Depth*SeedDepthScale);
        }
    bSeeded=true;
}

void AGTMudDetailStudy::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Surface || !Surface->HasActorBegunPlay()) return;
    if (!bReady)
    {
        for (AActor* Group : DebrisGroups)
        {
            if (!IsValid(Group)) continue;
            TArray<UInstancedStaticMeshComponent*> Components;
            Group->GetComponents(Components);
            for (auto* Component : Components)
            {
                FAnchors& A=Anchors.AddDefaulted_GetRef();A.Component=Component;
                A.bFloat=Group->Tags.Contains(TEXT("MudStudyFloat"));
                A.bGrass=Group->Tags.Contains(TEXT("MudStudyGrass"));
                Component->SetMobility(EComponentMobility::Movable);
                for (int32 I=0;I<Component->GetInstanceCount();++I)
                {
                    FTransform T;Component->GetInstanceTransform(I,T,true);A.Rest.Add(T);
                }
            }
        }
        bReady=true;
    }
    if (bSeedTracksOnPlay && !bSeeded) SeedTracks();
    for (FAnchors& A : Anchors)
    {
        auto* Component=A.Component.Get();
        if (!Component || !Component->GetStaticMesh()) continue;
        const FVector Extent=Component->GetStaticMesh()->GetBounds().BoxExtent;
        bool Changed=false;
        for (int32 I=0;I<A.Rest.Num() && I<Component->GetInstanceCount();++I)
        {
            FTransform T=A.Rest[I];FVector P=T.GetLocation();
            const auto Sample=Surface->SampleSurface(FVector2D(P));
            if (A.bGrass)
            {
                const float Flatten=Sample.Disturbance*Sample.GrassCover;
                FVector Scale=T.GetScale3D();Scale.Z*=FMath::Lerp(1.f,.15f,Flatten);T.SetScale3D(Scale);
            }
            float Support=Sample.SurfaceDeltaCm+(A.bFloat ? Sample.WaterDepthCm : 0.f);
            // A rigid branch can bridge small hollows. Leaves/pebbles follow their centre.
            if (Extent.GetMax()*T.GetScale3D().GetMax()>24.f)
                for (float Side : {-1.f,1.f})
                {
                    const FVector D=T.TransformVector(FVector(Extent.X*.55f*Side,0,0));
                    Support=FMath::Max(Support,Surface->SampleSurface(FVector2D(P+D)).SurfaceDeltaCm-1.f);
                }
            P.Z+=Support;T.SetLocation(P);
            FTransform Current;Component->GetInstanceTransform(I,Current,true);
            if (FMath::Abs(Current.GetLocation().Z-P.Z)>.2f || !Current.GetScale3D().Equals(T.GetScale3D(),.001))
            {
                Component->UpdateInstanceTransform(I,T,true,false,true);Changed=true;
            }
        }
        if (Changed) Component->MarkRenderStateDirty();
    }
}
