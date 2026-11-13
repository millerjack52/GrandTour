#include "Terrain/GTWaterSheet.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTWaterSubsystem.h"
#include "Terrain/GTWaterDomain.h"
#include "Core/GTPerfProbe.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "RenderUtils.h"
#include "ShaderCore.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

static TAutoConsoleVariable<int32> CVarMudWaterActive(TEXT("gt.Water.Mud.MaxActive"),1,
    TEXT("Maximum simultaneously stepping mud ponds (0..4). Sleeping ponds retain water volume."),ECVF_Scalability);

static TAutoConsoleVariable<int32> CVarMudFoam(TEXT("gt.Water.Mud.Foam"),1,
    TEXT("Mud water contact foam; 0 disables cosmetic simulation and shading."),ECVF_Scalability);

static bool MudVisualMaterialReady(UMaterialInterface* Material)
{
#if WITH_EDITOR
    // Kismet's DrawMaterialToRenderTarget calls EnsureIsComplete, which can
    // FinishCompilation synchronously in standalone editor builds. Request the
    // same feature-level jobs without waiting; retain the last water image.
    bool Ready=true;
    const uint32 Levels=UMaterialInterface::GetFeatureLevelsToCompileForAllMaterials();
    for(uint32 I=0;I<uint32(ERHIFeatureLevel::Num);++I)
        if(Levels & (1u<<I))
            if(FMaterialResource* Resource=Material->GetMaterialResource(GetFeatureLevelShaderPlatform_Checked(ERHIFeatureLevel::Type(I))))
                if(!Resource->IsGameThreadShaderMapComplete())
                {
                    Resource->SubmitCompileJobs_GameThread(EShaderCompileJobPriority::Normal);
                    Ready=false;
                }
    return Ready;
#else
    return true;
#endif
}

bool AGTWaterSheet::BindResearchSimulation(UMaterialInstanceDynamic* Material)
{
    if(!Material || !bFieldBuilt || !FieldTexture || !MudBaseTexture)return false;
    Material->SetTextureParameterValue(TEXT("FieldTex"),FieldTexture);
    Material->SetTextureParameterValue(TEXT("MudBaseTex"),MudBaseTexture);
    Material->SetVectorParameterValue(TEXT("FieldMin"),FLinearColor(Field.OriginCm.X,Field.OriginCm.Y,0,0));
    Material->SetVectorParameterValue(TEXT("FieldSize"),FLinearColor(Field.SizeX*Field.CellCm,Field.SizeY*Field.CellCm,0,0));
    Material->SetVectorParameterValue(TEXT("FieldTexels"),FLinearColor(Field.SizeX,Field.SizeY,0,0));
    Material->SetScalarParameterValue(TEXT("FieldLevelCm"),GetLevelCm());
    return true;
}
void AGTWaterSheet::SetResearchWaterTextures(UTextureRenderTarget2D* State,UTextureRenderTarget2D* Sediment,UTextureRenderTarget2D* Waves)
{
    if(!SurfaceMaterial)return;
    SurfaceMaterial->SetTextureParameterValue(TEXT("MRWaterState"),State);
    SurfaceMaterial->SetTextureParameterValue(TEXT("MRWaterSediment"),Sediment);
    SurfaceMaterial->SetTextureParameterValue(TEXT("MRWaves"),Waves);
    SurfaceMaterial->SetScalarParameterValue(TEXT("MR_WaterReady"),1);
}

void AGTWaterSheet::UploadMudFoam()
{
    if(!MudFoamTexture || !MudFoamTexture->GetResource())return;
    auto* Data=new TArray<FColor>();Data->SetNumUninitialized(Field.NumCells());
    for(int32 I=0;I<Field.NumCells();++I)
        (*Data)[I]=FColor(FMath::RoundToInt(MudFoam.Foam[I]*255),0,0,255);
    auto* Region=new FUpdateTextureRegion2D(0,0,0,0,Field.SizeX,Field.SizeY);
    MudFoamTexture->UpdateTextureRegions(0,1,Region,Field.SizeX*sizeof(FColor),sizeof(FColor),
        reinterpret_cast<uint8*>(Data->GetData()),[Data](uint8*,const FUpdateTextureRegion2D* R){delete Data;delete R;});
}

float AGTWaterSheet::MudWaterDepthCmAt(FVector2D XY) const
{
    if(!MudSurface || !MudSurface->Landscape || !Covers(XY)) return 0.f;
    const auto Base=MudSurface->GroundHeightAt(FVector(XY,0));
    if(!Base.IsSet()) return 0.f;
    const float FineDepth=FMath::Max(0.f,SurfaceCmAt(XY)-Base.GetValue()-MudSurface->BedDeltaCm(XY));
    return FMath::Min(FineDepth,Field.DepthMAt(XY)*100.f);
}

void AGTWaterSheet::TickMudWater(float Dt)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(MudWater);
    GT_PERF_SCOPE(PerfMudWater,"Water.MudTick");
    if (!MudSurface || !MudSurface->Landscape || !MudSurface->HasActorBegunPlay()) return;
    auto* Water=GetWorld()->GetSubsystem<UGTWaterSubsystem>();
    const bool Active=Water && Water->ShouldSimulateMudSheet(this,CVarMudWaterActive.GetValueOnGameThread());
    if (!Active)
    {
        if (bMudAwake) { Field.ClearLids();MudFoam.Reset(Field.NumCells());UploadMudFoam(); if(bFieldBuilt) UploadField(); }
        bMudAwake=false;
        if(bFieldBuilt || !bBuildSleepingMudBasin)return;
    }
    bMudAwake=Active;
    if (!bFieldBuilt)
    {
        const float Half=FMath::Clamp(MudHalfSizeCm,100.f,3200.f);
        // Quantize the requested cell count, then fit it to the authored extent.
        // This is a connected pond budget, not an unlimited grid per puddle.
        const int32 Side=FMath::Clamp(FMath::CeilToInt(2*Half/FMath::Max(10.f,MudCellCm)),8,128);
        const float Cell=2*Half/Side;
        Field=FGTWaterField();Field.bClosedBasin=true;Field.bOpenEnds=false;
        Field.HeadDropCm=0;Field.NominalFlowMps=0;Field.SpongeTauS=0;Field.SpongeFluxDamp=0;
        Field.WindScale=0;Field.RainIntensity=0;Field.DryDepthM=.002f;
        Field.BedFriction=.025f;Field.PipeDamping=.004f;Field.MaxFlowSpeedMps=2.f;
        Field.LidRateMps=.65f;Field.LidBlend=.25f;
        Field.Init(FVector2D(GetActorLocation()),FVector2D(1,0),Half,Half,Cell,BaseLevelCm,[this](FVector2D XY)
        {
            const auto Base=MudSurface->GroundHeightAt(FVector(XY,0));
            return Base.IsSet() ? Base.GetValue()+MudSurface->BedDeltaCm(XY) : BaseLevelCm+100.f;
        });
        if(MudInitialDomain)
        {
            // Seed only the authored water volume, not every hollow below one
            // flat elevation. Separate puddles may have different initial heads.
            for(int32 I=0;I<Field.NumCells();++I)
            {
                float S,D;FVector2D V;
                Field.DepthM[I]=MudInitialDomain->Sample(Field.CellCentreCm(I),S,D,V)?D:0.f;
            }
            Field.UpdateClosedBed(Field.BedCm);
        }
        MudBaseCm.SetNumUninitialized(Field.NumCells());MudBedCm=Field.BedCm;
        for(int32 I=0;I<Field.NumCells();++I) MudBaseCm[I]=Field.BedCm[I]-MudSurface->BedDeltaCm(Field.CellCentreCm(I));
        MudInitialVolume=Field.VolumeM3();MudBedRevision=MudSurface->BedRevision();
        BuildSurfaceMesh();MudSurface->RegisterResearchMaterial(SurfaceMaterial);
        MudFoam.Reset(Field.NumCells());
        MudFoamTexture=UTexture2D::CreateTransient(Field.SizeX,Field.SizeY,PF_B8G8R8A8);
        if(MudFoamTexture)
        {
            MudFoamTexture->SRGB=false;MudFoamTexture->Filter=TF_Bilinear;
            MudFoamTexture->AddressX=TA_Clamp;MudFoamTexture->AddressY=TA_Clamp;
            auto& Mip=MudFoamTexture->GetPlatformData()->Mips[0];
            void* Data=Mip.BulkData.Lock(LOCK_READ_WRITE);FMemory::Memzero(Data,Mip.BulkData.GetBulkDataSize());
            Mip.BulkData.Unlock();MudFoamTexture->UpdateResource();
            if(SurfaceMaterial)SurfaceMaterial->SetTextureParameterValue(TEXT("MudFoamTex"),MudFoamTexture);
        }
        // Soil heights are relative to the original landscape. Keep that base
        // in full-precision centimetres so elevated/sloping shores clip correctly.
        MudBaseTexture=UTexture2D::CreateTransient(Field.SizeX,Field.SizeY,PF_R32_FLOAT);
        if(MudBaseTexture)
        {
            MudBaseTexture->SRGB=false;MudBaseTexture->Filter=TF_Bilinear;
            MudBaseTexture->AddressX=TA_Clamp;MudBaseTexture->AddressY=TA_Clamp;
            auto& Mip=MudBaseTexture->GetPlatformData()->Mips[0];
            void* Data=Mip.BulkData.Lock(LOCK_READ_WRITE);
            FMemory::Memcpy(Data,MudBaseCm.GetData(),MudBaseCm.Num()*sizeof(float));
            Mip.BulkData.Unlock();MudBaseTexture->UpdateResource();
            if(SurfaceMaterial) SurfaceMaterial->SetTextureParameterValue(TEXT("MudBaseTex"),MudBaseTexture);
        }
        bFieldBuilt=true;return;
    }
    MudBedTime+=Dt;MudUploadTime+=Dt;
    if (MudBedTime>=.1f && MudBedRevision!=MudSurface->BedRevision())
    {
        const double Start=FPlatformTime::Seconds();
        TArray<FBox2D> Regions;MudSurface->BedChangesSince(MudBedRevision,Regions);
        for(const auto& R:Regions)
        {
            const int32 X0=FMath::Clamp(FMath::FloorToInt((R.Min.X-Field.OriginCm.X)/Field.CellCm-.5),0,Field.SizeX);
            const int32 Y0=FMath::Clamp(FMath::FloorToInt((R.Min.Y-Field.OriginCm.Y)/Field.CellCm-.5),0,Field.SizeY);
            const int32 X1=FMath::Clamp(FMath::CeilToInt((R.Max.X-Field.OriginCm.X)/Field.CellCm+.5),0,Field.SizeX);
            const int32 Y1=FMath::Clamp(FMath::CeilToInt((R.Max.Y-Field.OriginCm.Y)/Field.CellCm+.5),0,Field.SizeY);
            for(int32 Y=Y0;Y<Y1;++Y) for(int32 X=X0;X<X1;++X)
            {
                const int32 I=Y*Field.SizeX+X;
                MudBedCm[I]=MudBaseCm[I]+MudSurface->BedDeltaCm(Field.CellCentreCm(I));
            }
        }
        Field.UpdateClosedBed(MudBedCm);
        MudBedRevision=MudSurface->BedRevision();MudBedTime=0;++MudBedUpdates;
        MudBedPeakMs=FMath::Max(MudBedPeakMs,(FPlatformTime::Seconds()-Start)*1000.);
    }
    static const IConsoleVariable* Lids=IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Water.Lids"));
    bLidsOn=!Lids || Lids->GetInt()!=0;
    if(!bLidsOn) Field.ClearLids();
    Field.Step(Dt,BaseLevelCm,0);AccumulateStats(Dt);
    const bool FoamOn=CVarMudFoam.GetValueOnGameThread()!=0;
    if(SurfaceMaterial)SurfaceMaterial->SetScalarParameterValue(TEXT("ContactFoamEnabled"),FoamOn?1.f:0.f);
    if(FoamOn) { if(MudFoam.Step(Field,Dt))UploadMudFoam(); }
    else if(MudFoam.Steps>0) { MudFoam.Reset(Field.NumCells());MudFoam.Steps=0;UploadMudFoam(); }
    if(MudUploadTime>=1.f/30.f) { UploadField();MudUploadTime=0; }
    StepNativeMudVisual(Dt);
}

void AGTWaterSheet::StepNativeMudVisual(float Dt)
{
    if(!MudStateMaterial || !MudSedimentMaterial || !MudWaveMaterial)return;
    GT_PERF_SCOPE(PerfNativeWater,"Water.NativeMudVisual");
    if(!MudStateDynamic)
    {
        GT_PERF_SCOPE(PerfInit,"Water.NativeMudVisualInit");
        MudStateDynamic=UMaterialInstanceDynamic::Create(MudStateMaterial,this);
        MudSedimentDynamic=UMaterialInstanceDynamic::Create(MudSedimentMaterial,this);
        MudSurface->RegisterResearchMaterial(MudStateDynamic);
        MudSurface->RegisterResearchMaterial(MudSedimentDynamic);
        return;
    }
    // Waking a basin must not allocate all five render targets and issue its
    // first material draws in one frame. Keep the ordinary water visible while
    // the cosmetic buffers are prepared, one per frame; no physics is delayed.
    if(MudStateTargets.Num()<2)
    {
        GT_PERF_SCOPE(PerfInit,"Water.NativeMudVisualInit");
        MudStateTargets.Add(UKismetRenderingLibrary::CreateRenderTarget2D(this,Field.SizeX,Field.SizeY,RTF_RGBA16f,FLinearColor(.5f,128.f/255.f,128.f/255.f,1)));
        return;
    }
    if(MudSedimentTargets.Num()<2)
    {
        GT_PERF_SCOPE(PerfInit,"Water.NativeMudVisualInit");
        MudSedimentTargets.Add(UKismetRenderingLibrary::CreateRenderTarget2D(this,Field.SizeX,Field.SizeY,RTF_RGBA16f,FLinearColor(0,0,0,1)));
        return;
    }
    if(!MudWaves)
    {
        GT_PERF_SCOPE(PerfInit,"Water.NativeMudVisualInit");
        MudWaves=UKismetRenderingLibrary::CreateRenderTarget2D(this,512,512,RTF_RGBA16f,FLinearColor(.5f,.5f,1,1));
        return;
    }
    if(!BindResearchSimulation(MudStateDynamic) || !BindResearchSimulation(MudSedimentDynamic))return;
    const bool StateReady=MudVisualMaterialReady(MudStateDynamic);
    const bool SedimentReady=MudVisualMaterialReady(MudSedimentDynamic);
    const bool WavesReady=MudVisualMaterialReady(MudWaveMaterial);
    if(!StateReady || !SedimentReady || !WavesReady)
    {
        GT_PERF_SCOPE(PerfWait,"Water.NativeMudVisualShaderWait");
        return;
    }
    MudNativeCarry+=FMath::Min(Dt,.1f);if(MudNativeCarry<1.f/30.f)return;
    MudNativeCarry=FMath::Fmod(MudNativeCarry,1.f/30.f);
    const int32 Next=1-MudPrevious;
    for(auto* M:{MudStateDynamic.Get(),MudSedimentDynamic.Get()})
    {
        M->SetTextureParameterValue(TEXT("MRWaterState"),MudStateTargets[MudPrevious]);
        M->SetTextureParameterValue(TEXT("MRWaterSediment"),MudSedimentTargets[MudPrevious]);
    }
    // Same recovered MRT arithmetic/packing as GTMudRunnerVisual. Each sleeping
    // basin retains its own targets; only the budgeted awake basin draws them.
    GT_PERF_SCOPE(PerfDraw,"Water.NativeMudVisualDraw");
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,MudStateTargets[Next],MudStateDynamic);
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,MudSedimentTargets[Next],MudSedimentDynamic);
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,MudWaves,MudWaveMaterial);
    MudPrevious=Next;++MudNativeSteps;
    SetResearchWaterTextures(MudStateTargets[Next],MudSedimentTargets[Next],MudWaves);
}

FString AGTWaterSheet::MudWaterDiagnostics() const
{
    float PeakFoam=0;for(float C:MudFoam.Foam)PeakFoam=FMath::Max(PeakFoam,C);
    return FString::Printf(TEXT("native_steps=%d cells=%d cell_cm=%.3f awake=%d volume_m3=%.8f initial_m3=%.8f delta_m3=%.8f bed_updates=%d bed_peak_ms=%.3f step_mean_ms=%.3f step_peak_ms=%.3f wet=%d lids=%d deficit_s=%.4f clamps=%d foam_peak=%.4f foam_mean_ms=%.4f foam_peak_ms=%.4f"),MudNativeSteps,
        Field.NumCells(),Field.CellCm,bMudAwake?1:0,Field.VolumeM3(),MudInitialVolume,Field.VolumeM3()-MudInitialVolume,
        MudBedUpdates,MudBedPeakMs,Field.StepMsCount?Field.StepMsSum/Field.StepMsCount:0.,Field.StepMsMax,
        Field.WetCellCount,Field.LidCellCount,Field.DeficitSeconds,Field.DepthClamps,PeakFoam,
        MudFoam.Steps?MudFoam.MsSum/MudFoam.Steps:0.,MudFoam.MsPeak);
}
