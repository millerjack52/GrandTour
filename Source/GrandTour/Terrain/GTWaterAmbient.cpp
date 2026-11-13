#include "Terrain/GTWaterSheet.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<int32> CVarAmbientWaves(TEXT("gt.Water.Domain.Ambient"),1,
	TEXT("0 disables the shared cosmetic wave precombine; interaction physics is unchanged."));
static TAutoConsoleVariable<float> CVarAmbientWaveHz(TEXT("gt.Water.Domain.AmbientHz"),30,
	TEXT("Shared wave data update rate, 15..60 Hz. Not a physics timestep."));

void AGTWaterSheet::UpdateAmbientWaves(float Seconds,bool Force)
{
	if(!AmbientWaveMaterial || !SurfaceMaterial || !GetWorld())return;
	const bool Enabled=CVarAmbientWaves.GetValueOnGameThread()!=0;
	const float Interval=1.f/FMath::Clamp(CVarAmbientWaveHz.GetValueOnGameThread(),15.f,60.f);
	const bool Due=Force || AmbientWaveLastTime<0 || Seconds<AmbientWaveLastTime || Seconds-AmbientWaveLastTime+1.e-4f>=Interval;
	if(!Force && Enabled==bAmbientWaveWasEnabled && (!Enabled || !Due))return;
	// A stopped/disabled field never accumulates work or allocates a larger simulation.
	if(Enabled && Due)
	{
		if(!AmbientWaveTarget)
		{
			AmbientWaveTarget=NewObject<UTextureRenderTarget2D>(this);
			AmbientWaveTarget->RenderTargetFormat=RTF_RGBA16f;
			AmbientWaveTarget->ClearColor=FLinearColor(0,0,0,1);
			AmbientWaveTarget->bForceLinearGamma=true;
			AmbientWaveTarget->bAutoGenerateMips=true;
			AmbientWaveTarget->AddressX=TA_Wrap;AmbientWaveTarget->AddressY=TA_Wrap;
			AmbientWaveTarget->Filter=TF_Trilinear;
			const int32 Side=AmbientWaveResolution>0 ? FMath::Clamp(AmbientWaveResolution,64,1024) : WaterDomain?256:512;
			AmbientWaveTarget->InitAutoFormat(Side,Side);
			AmbientWaveTarget->UpdateResourceImmediate(true);
			AmbientWavePrecombine=UMaterialInstanceDynamic::Create(AmbientWaveMaterial,this);
		}
		AmbientWavePrecombine->SetScalarParameterValue(TEXT("WaveClock"),Seconds);
		// AlphaComposite stores RGB without multiplying by foam opacity. With an alpha-1
		// clear, A carries remaining transmittance (1 - foam), not accumulated history.
		UKismetRenderingLibrary::ClearRenderTarget2D(this,AmbientWaveTarget,FLinearColor(0,0,0,1));
		UKismetRenderingLibrary::DrawMaterialToRenderTarget(this,AmbientWaveTarget,AmbientWavePrecombine);
		AmbientWaveLastTime=Seconds;
	}
	TArray<UMaterialInstanceDynamic*,TInlineAllocator<4>> All;All.Add(SurfaceMaterial);
	for(UMaterialInstanceDynamic* M:DomainMaterials)All.Add(M);
	for(UMaterialInstanceDynamic* M:All)if(M)
	{
		if(AmbientWaveTarget)M->SetTextureParameterValue(TEXT("AmbientTex"),AmbientWaveTarget);
		M->SetScalarParameterValue(TEXT("AmbientReady"),Enabled && AmbientWaveTarget?1:0);
		// Sampling advection and texture evolution use the SAME clock, including pauses.
		M->SetScalarParameterValue(TEXT("AmbientClock"),FMath::Max(0.f,AmbientWaveLastTime));
	}
	bAmbientWaveWasEnabled=Enabled;
}

void AGTWaterSheet::PreviewAmbientWaves(float Seconds)
{
	if(!GetWorld() || GetWorld()->IsGameWorld())return;
	UpdateAmbientWaves(FMath::Max(0.f,Seconds),true);
}
