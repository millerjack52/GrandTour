#include "Look/GTDistanceStyle.h"
#include "Components/SceneComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Components/PrimitiveComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Terrain/GTMixedGroundDetails.h"
#include "EngineUtils.h"
#if WITH_EDITOR
#include "ShaderCompiler.h"
#include "AssetCompilingManager.h"
#include "RenderingThread.h"
#endif

AGTDistanceStyleController::AGTDistanceStyleController()
{
 RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
 PrimaryActorTick.bCanEverTick=true;
 PrimaryActorTick.TickInterval=.25f;
}
void AGTDistanceStyleController::BeginPlay(){Super::BeginPlay();ApplyProfile();}
void AGTDistanceStyleController::OnConstruction(const FTransform& T){Super::OnConstruction(T);ApplyProfile();}
void AGTDistanceStyleController::Tick(float D){Super::Tick(D);ApplyProfile();}
void AGTDistanceStyleController::SetSurfaceReviewMode(int32 Mode)
{
#if !UE_BUILD_SHIPPING
 SurfaceReviewMode=FMath::Clamp(Mode,-1,2);ApplyProfile();
 UE_LOG(LogTemp,Display,TEXT("SURFACE_REVIEW mode=%d"),SurfaceReviewMode);
#endif
}
void AGTDistanceStyleController::SetLeafReviewStrength(float Strength)
{
#if !UE_BUILD_SHIPPING
 if(Parameters && GetWorld()){
  GetWorld()->GetParameterCollectionInstance(Parameters)->SetScalarParameterValue(TEXT("LeafReviewStrength"),FMath::Clamp(Strength,0.f,1.f));
  UE_LOG(LogTemp,Display,TEXT("LEAF_REVIEW strength=%.2f"),Strength);
 }
#endif
}
void AGTDistanceStyleController::FinishReviewShaders()
{
#if WITH_EDITOR && !UE_BUILD_SHIPPING
 FAssetCompilingManager::Get().FinishAllCompilation();
 if(GShaderCompilingManager)GShaderCompilingManager->FinishAllCompilation();
 FlushRenderingCommands();
 UE_LOG(LogTemp,Display,TEXT("STYLE_REVIEW pending asset and shader compilation finished"));
#endif
}
void AGTDistanceStyleController::SetCanopyDepthReview(float Strength)
{
#if !UE_BUILD_SHIPPING
 CanopyDepthReview=FMath::Clamp(Strength,0.f,3.f);ApplyProfile();
 UE_LOG(LogTemp,Display,TEXT("CANOPY_DEPTH_REVIEW strength=%.2f instances=%d"),CanopyDepthReview,InteriorInstances?InteriorInstances->GetInstanceCount():0);
 if(InteriorInstances)UE_LOG(LogTemp,Display,TEXT("INTERIOR_REVIEW visible=%d hidden=%d mesh=%s bounds=%s extents=%s"),InteriorInstances->IsVisible(),InteriorInstances->bHiddenInGame,*InteriorInstances->GetStaticMesh()->GetName(),*InteriorInstances->Bounds.Origin.ToString(),*InteriorInstances->Bounds.BoxExtent.ToString());
#endif
}
void AGTDistanceStyleController::ApplyInterior()
{
 if(!Profile || !GetWorld())return;
 auto* Data=Profile->ForestInterior.Get();
 if(Data!=LoadedInterior || (Data && !IsValid(InteriorInstances))){
  if(IsValid(InteriorInstances))InteriorInstances->DestroyComponent();
  InteriorInstances=nullptr;LoadedInterior=Data;
  if(Data && Data->Mesh && Data->Placements.Num()){
   InteriorInstances=NewObject<UHierarchicalInstancedStaticMeshComponent>(this,TEXT("ForestInterior"),RF_Transient);
   auto* C=InteriorInstances.Get();C->SetStaticMesh(Data->Mesh);C->SetMobility(EComponentMobility::Movable);
   C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);
   C->SetCastShadow(false);C->SetVisibleInRayTracing(false);C->bAffectDistanceFieldLighting=false;
   C->SetEvaluateWorldPositionOffset(true);C->SetWorldPositionOffsetDisableDistance(0);
   C->bAllowCullDistanceVolume=false;
   C->SetCullDistances(95000,130000);C->SetupAttachment(RootComponent);C->RegisterComponent();
   C->AddInstances(Data->Placements,false,true);
   UE_LOG(LogTemp,Display,TEXT("FOREST_INTERIOR instances=%d collision=off shadows=off cull=1300m"),Data->Placements.Num());
  }
 }
 if(InteriorInstances)InteriorInstances->SetVisibility(CanopyDepthReview!=3.f && (CanopyDepthReview>=0?CanopyDepthReview:Profile->CanopyDepthStrength)>.001f);
}
void AGTDistanceStyleController::SetReviewView(float X,float Y,float Z,float Pitch,float Yaw,float FOV)
{
#if !UE_BUILD_SHIPPING
 auto* W=GetWorld();if(!W || !W->IsGameWorld())return;
 auto* PC=W->GetFirstPlayerController();if(!PC)return;
 // Offscreen evidence must not react to input intended for another application.
 PC->SetInputMode(FInputModeUIOnly());PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);
 PC->DisableInput(PC);
 // The isolated capture process follows vegetation streaming without driving
 // or leaving tyre disturbance beneath the comparison camera.
 if(APawn* Pawn=PC->GetPawn()){
  if(auto* Body=Cast<UPrimitiveComponent>(Pawn->GetRootComponent()))Body->SetSimulatePhysics(false);
  Pawn->SetActorLocation(FVector(X,Y,Z+500));Pawn->SetActorHiddenInGame(true);
 }
 if(!IsValid(ReviewCamera)){FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;ReviewCamera=W->SpawnActor<ACameraActor>(Params);}
 if(!ReviewCamera)return;
 ReviewCamera->SetActorLocationAndRotation(FVector(X,Y,Z),FRotator(Pitch,Yaw,0));
 ReviewCamera->GetCameraComponent()->SetFieldOfView(FMath::Clamp(FOV,20.f,120.f));
 ReviewCamera->GetCameraComponent()->bConstrainAspectRatio=false;PC->SetViewTarget(ReviewCamera);
 for(TActorIterator<AGTMixedGroundDetails> It(W);It;++It){
  const bool Ready=It->FinishReviewStreaming();
  UE_LOG(LogTemp,Display,TEXT("SURFACE_REVIEW streaming_ready=%d"),Ready?1:0);
 }
 UE_LOG(LogTemp,Display,TEXT("SURFACE_REVIEW camera %.1f %.1f %.1f"),X,Y,Z);
#endif
}
void AGTDistanceStyleController::SetStylePreset(FName Name)
{
 UGTDistanceStyleProfile* Next=Name==TEXT("Subtle")?Subtle.Get():Name==TEXT("Strong")?Strong.Get():Name==TEXT("Medium")?Medium.Get():Name==TEXT("Cohesive")?Cohesive.Get():nullptr;
#if !UE_BUILD_SHIPPING
 if(Name==TEXT("BeforePalette"))Next=LoadObject<UGTDistanceStyleProfile>(nullptr,TEXT("/Game/GrandTour/ArtTests/LidarStudy/CohesiveStyle/DA_Lidar_BeforePalette.DA_Lidar_BeforePalette"));
 if(Name==TEXT("MutedPalette"))Next=LoadObject<UGTDistanceStyleProfile>(nullptr,TEXT("/Game/GrandTour/ArtTests/LidarStudy/CohesiveStyle/DA_Lidar_MutedPalette.DA_Lidar_MutedPalette"));
#endif
 if(Next){Profile=Next;ApplyProfile();UE_LOG(LogTemp,Display,TEXT("DISTANCE_STYLE preset=%s strength=%.3f fog=%.3f"),*Name.ToString(),Profile->Strength,Profile->HazeIntensity);}
 else UE_LOG(LogTemp,Warning,TEXT("DISTANCE_STYLE unknown preset %s"),*Name.ToString());
}
void AGTDistanceStyleController::ApplyProfile()
{
 if(!Profile || !Parameters || !GetWorld())return;
 auto* I=GetWorld()->GetParameterCollectionInstance(Parameters);if(!I)return;
 const auto& P=*Profile;
 ApplyInterior();
 if(!DepthParameters)DepthParameters=LoadObject<UMaterialParameterCollection>(nullptr,TEXT("/Game/GrandTour/ArtTests/LidarStudy/CanopyInterior/MPC_CanopyDepth.MPC_CanopyDepth"));
 if(DepthParameters)GetWorld()->GetParameterCollectionInstance(DepthParameters)->SetScalarParameterValue(TEXT("DepthStrength"),CanopyDepthReview==2.f?0.f:CanopyDepthReview>=0?FMath::Min(1.f,CanopyDepthReview):FMath::Clamp(P.CanopyDepthStrength,0.f,1.f));
 auto S=[I](const TCHAR* N,float V){I->SetScalarParameterValue(FName(N),V);};
 auto V=[I](const TCHAR* N,FLinearColor C){I->SetVectorParameterValue(FName(N),C);};
 S(TEXT("Strength"),FMath::Clamp(P.Strength,0.f,1.f));
 S(TEXT("StartCm"),FMath::Max(0.f,P.StartMetres)*100.f);
 S(TEXT("FullCm"),FMath::Max(P.StartMetres+1.f,P.FullMetres)*100.f);
 S(TEXT("NormalSimplification"),FMath::Clamp(P.NormalSimplification,0.f,1.f));
 S(TEXT("PatchVariation"),FMath::Clamp(P.PatchVariation,0.f,.5f));
 S(TEXT("PatchSizeCm"),FMath::Max(5.f,P.PatchSizeMetres)*100.f);
 S(TEXT("PaletteStrength"),FMath::Clamp(P.PaletteStrength,0.f,1.f));
 S(TEXT("PaletteStartCm"),FMath::Max(0.f,P.PaletteStartMetres)*100.f);
 S(TEXT("PaletteFullCm"),FMath::Max(P.PaletteStartMetres+1.f,P.PaletteFullMetres)*100.f);
 S(TEXT("CrownDefinition"),FMath::Clamp(P.CrownDefinition,0.f,1.f));
 S(TEXT("SkyPaletteStrength"),FMath::Clamp(P.SkyPaletteStrength,0.f,1.f));
 // Keep the finish independent of the established surface/distance uniform layout.
 if(!FinishParameters)FinishParameters=LoadObject<UMaterialParameterCollection>(nullptr,TEXT("/Game/GrandTour/ArtTests/LidarStudy/CohesiveStyle/MPC_PaletteFinish.MPC_PaletteFinish"));
 if(FinishParameters){
  auto* Finish=GetWorld()->GetParameterCollectionInstance(FinishParameters);
  Finish->SetScalarParameterValue(TEXT("FinishStrength"),FMath::Clamp(P.FinishStrength,0.f,1.f));
  Finish->SetScalarParameterValue(TEXT("FinishSaturation"),FMath::Clamp(P.FinishSaturation,0.f,1.5f));
  Finish->SetScalarParameterValue(TEXT("GreenRestraint"),FMath::Clamp(P.GreenRestraint,0.f,1.f));
  Finish->SetScalarParameterValue(TEXT("HighlightCompression"),FMath::Clamp(P.HighlightCompression,0.f,.5f));
  Finish->SetScalarParameterValue(TEXT("MidtoneGain"),FMath::Clamp(P.MidtoneGain,.5f,1.5f));
  Finish->SetScalarParameterValue(TEXT("SunlightWarmth"),FMath::Clamp(P.SunlightWarmth,0.f,1.f));
  Finish->SetScalarParameterValue(TEXT("SunlightLift"),FMath::Clamp(P.SunlightLift,0.f,.5f));
 }
 S(TEXT("SurfaceDetailStrength"),SurfaceReviewMode>=0?(SurfaceReviewMode==0?0.f:1.f):FMath::Clamp(P.SurfaceDetailStrength,0.f,1.f));
 S(TEXT("SurfaceParallaxStrength"),SurfaceReviewMode>=0?(SurfaceReviewMode==1?0.f:1.f):FMath::Clamp(P.SurfaceParallaxStrength,0.f,1.f));
 S(TEXT("GravelDepthCm"),FMath::Clamp(P.GravelDepthCm,0.f,5.f));
 S(TEXT("GroundDepthCm"),FMath::Clamp(P.GroundDepthCm,0.f,5.f));
 S(TEXT("GravelTileCm"),FMath::Max(25.f,P.GravelTileCm));
 S(TEXT("GroundTileCm"),FMath::Max(25.f,P.GroundTileCm));
 S(TEXT("SurfaceNearCm"),FMath::Max(0.f,P.SurfaceNearMetres)*100.f);
 S(TEXT("SurfaceFarCm"),FMath::Max(P.SurfaceNearMetres+1.f,P.SurfaceFarMetres)*100.f);
 S(TEXT("SurfaceMaxSteps"),float(FMath::Clamp(P.SurfaceMaxSteps,8,32)));
 V(TEXT("SunlitColour"),P.SunlitColour);V(TEXT("ClearingColour"),P.ClearingColour);
 V(TEXT("ClearingShadowColour"),P.ClearingShadowColour);
 V(TEXT("SkyHorizonColour"),P.SkyHorizonColour);V(TEXT("SkyZenithColour"),P.SkyZenithColour);
 S(TEXT("HazeIntensity"),FMath::Clamp(P.HazeIntensity,0.f,1.f));
 S(TEXT("HazeStartCm"),FMath::Max(0.f,P.HazeStartMetres)*100.f);
 S(TEXT("HazeFullCm"),FMath::Max(P.HazeStartMetres+1.f,P.HazeFullMetres)*100.f);
 V(TEXT("ForestColour"),P.ForestColour);V(TEXT("ShadowColour"),P.ShadowColour);
 V(TEXT("GroundTint"),P.GroundTint);V(TEXT("HazeColour"),P.HazeColour);
 V(TEXT("FieldDomain"),FLinearColor(P.FieldOriginCm.X,P.FieldOriginCm.Y,FMath::Max(1.,P.FieldSpanCm.X),FMath::Max(1.,P.FieldSpanCm.Y)));
 const FVector Direction=Sun?-Sun->GetActorForwardVector():FVector(-.1586355,.8996666,.4067366);
 V(TEXT("SunDirection"),FLinearColor(Direction.X,Direction.Y,Direction.Z,0));
}
