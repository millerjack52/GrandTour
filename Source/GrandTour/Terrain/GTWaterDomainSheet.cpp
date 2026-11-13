#include "Terrain/GTWaterSheet.h"
#include "Core/GTPerfProbe.h"
#include "Terrain/GTWaterDomain.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Terrain/GTWaterInteractionVisuals.h"
#include "Weather/GTWeatherSubsystem.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "ProceduralMeshComponent.h"
#include "HAL/IConsoleManager.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "ProfilingDebugging/CsvProfiler.h"

CSV_DEFINE_CATEGORY(GTWater,true);
static TAutoConsoleVariable<int32> CVarDomainDetail(TEXT("gt.Water.Domain.Detail"),1,TEXT("0 disables cosmetic foam/sediment updates for comparisons."));
static TAutoConsoleVariable<float> CVarDomainUploadHz(TEXT("gt.Water.Domain.UploadHz"),30,TEXT("Moving water texture upload cap; physics still runs at its fixed timestep."));
static TAutoConsoleVariable<float> CVarWakeRelief(TEXT("gt.Water.WakeRelief"),1.5f,TEXT("Extra visual bow/wake height gain; 0 keeps physical displacement only. Does not change the solver."));
static TAutoConsoleVariable<float> CVarVehicleWaves(TEXT("gt.Water.VehicleWaves"),1.f,TEXT("Visible vehicle pressure ridge and widening wake, 0 disables. Rendering only; no fluid mass/force changes."));
static TAutoConsoleVariable<int32> CVarVisualWakeDebug(TEXT("gt.Water.VisualWakeDebug"),0,TEXT("Log cosmetic wake source and upload range. Functional diagnostics only."));

FVector2D AGTWaterSheet::GetVisualWakeMotion(AActor* Source) const
{
	const FVisualVehicleWake* W=VisualVehicleWakes.FindByPredicate([Source](const FVisualVehicleWake& V){return V.Source.Get()==Source;});
	return W ? W->MotionMps : FVector2D::ZeroVector;
}

void AGTWaterSheet::SetVisualVehicleWake(AActor* Source,FVector2D Centre,FVector2D Travel,float HalfLengthCm,float HalfWidthCm,float SpeedMps,float ImmersionM)
{
	if(!WaterDomain || !Source || Travel.IsNearlyZero())return;
	const float Now=GetWorld()->GetTimeSeconds();
	VisualVehicleWakes.RemoveAll([Now](const FVisualVehicleWake& W){return !W.Source.IsValid() || Now-W.Updated>2.4f;});
	FVisualVehicleWake* W=VisualVehicleWakes.FindByPredicate([Source](const FVisualVehicleWake& V){return V.Source.Get()==Source;});
	if(!W)
	{
		if(VisualVehicleWakes.Num()>=4)return;
		W=&VisualVehicleWakes.AddDefaulted_GetRef();W->Source=Source;
		W->MotionMps=Travel.GetSafeNormal()*SpeedMps;W->Travel=Travel.GetSafeNormal();
		W->Speed=SpeedMps;W->Immersion=ImmersionM;W->Updated=Now;
	}
	const float Response=1-FMath::Exp(-FMath::Max(0.f,Now-W->Updated)/.20f);
	W->Speed=FMath::Lerp(W->Speed,SpeedMps,Response);
	W->Immersion=FMath::Lerp(W->Immersion,ImmersionM,Response);
	W->MotionMps=GTWaterInteractionVisuals::FilterWakeVelocity(W->MotionMps,Travel.GetSafeNormal()*SpeedMps,Now-W->Updated);
	W->Centre=Centre;
	if(W->MotionMps.Size()>.15f)W->Travel=W->MotionMps.GetSafeNormal();
	W->HalfLength=HalfLengthCm;W->HalfWidth=HalfWidthCm;
	W->Updated=Now;
	VisualTrailWaves.RemoveAll([Now](const FVisualTrailWave& R){return Now-R.Born>=3.2f;});
	if(Now-W->LastRipple>=.16f && SpeedMps>.4f && ImmersionM>.025f)
	{
		W->LastRipple=Now;
		const FVector2D Side(-W->Travel.Y,W->Travel.X);
		for(float Sign:{-1.f,1.f})
		{
			if(VisualTrailWaves.Num()>=64)VisualTrailWaves.RemoveAt(0);
			FVisualTrailWave& R=VisualTrailWaves.AddDefaulted_GetRef();
			R.Centre=Centre-W->Travel*(HalfLengthCm*.65f)+Side*(Sign*HalfWidthCm);
			R.Outward=Side*Sign;R.FlowCmPerS=Field.VelocityAt(R.Centre)*100;
			R.Born=Now;R.Energy=GTWaterInteractionVisuals::Activity(SpeedMps,ImmersionM,.4f,4.f,.025f,.20f);
		}
	}
}

void AGTWaterSheet::RasterVisualVehicleWakes(TArray<FColor>& Data)
{
	const float Strength=FMath::Clamp(CVarVehicleWaves.GetValueOnGameThread(),0.f,2.f);
	if(Strength<=0)return;
	const float Now=GetWorld()->GetTimeSeconds();
	VisualVehicleWakes.RemoveAll([Now](const FVisualVehicleWake& W){return !W.Source.IsValid() || Now-W.Updated>2.4f;});
	const TArray<float>& Depth=Field.GetRiverDepthM();
	float Peak=0;int32 Changed=0;
	for(const FVisualVehicleWake& W:VisualVehicleWakes)
	{
		const float Age=FMath::Max(0.f,Now-W.Updated);
		const float Fade=1-FMath::SmoothStep(.20f,2.4f,Age);
		// A released wake drifts with the current instead of freezing on the bed.
		const FVector2D Centre=W.Centre+Field.VelocityAt(W.Centre)*100*Age;
		const FVector2D Right(-W.Travel.Y,W.Travel.X),P=Field.ToFieldCm(Centre);
		// Work only in the bounded near-car region, using the already allocated 96-square upload.
		const int32 MinX=FMath::Max(0,FMath::FloorToInt((P.X-1700)/Field.CellCm)),MaxX=FMath::Min(Field.SizeX-1,FMath::CeilToInt((P.X+1700)/Field.CellCm));
		const int32 MinY=FMath::Max(0,FMath::FloorToInt((P.Y-1700)/Field.CellCm)),MaxY=FMath::Min(Field.SizeY-1,FMath::CeilToInt((P.Y+1700)/Field.CellCm));
		for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
		{
			const int32 I=Y*Field.SizeX+X;if(!Depth.IsValidIndex(I) || Depth[I]<=.015f)continue;
			const FVector2D Delta=Field.CellCentreCm(I)-Centre;
			const float Shore=FMath::SmoothStep(.015f,.18f,Depth[I]);
			const float Contact=GTWaterInteractionVisuals::VehicleContactFoam(FVector2D::DotProduct(Delta,W.Travel),FVector2D::DotProduct(Delta,Right),W.HalfLength,W.HalfWidth,W.Speed,W.Immersion)*Strength*Fade*Shore;
			// A is fresh, spatially focused contact aeration. R remains the
			// transported history. Never write either mask into the solver.
			Data[I].A=FMath::Max(Data[I].A,uint8(FMath::Clamp(FMath::RoundToInt(Contact*255),0,255)));
			const float Height=GTWaterInteractionVisuals::VehicleWaveCm(FVector2D::DotProduct(Delta,W.Travel),FVector2D::DotProduct(Delta,Right),W.HalfLength,W.HalfWidth,W.Speed,W.Immersion)*Strength*Fade;
			if(FMath::Abs(Height)<.01f)continue;
			Peak=FMath::Max(Peak,FMath::Abs(Height));++Changed;
			const float Combined=GTWaterInteractionVisuals::UnpackHeight(Data[I].B)+Height*Shore;
			Data[I].B=GTWaterInteractionVisuals::PackHeight(FMath::Clamp(Combined,-FMath::Min(18.f,Depth[I]*30),FMath::Min(30.f,Depth[I]*85)));
			// Broken aeration stays on the raised crest; the existing pixel material provides fine breakup.
			Data[I].R=FMath::Max(Data[I].R,uint8(FMath::Clamp(FMath::RoundToInt(FMath::Max(0.f,Height)*Shore*3),0,150)));
		}
	}
	VisualTrailWaves.RemoveAll([Now](const FVisualTrailWave& R){return Now-R.Born>=3.2f;});
	for(const FVisualTrailWave& R:VisualTrailWaves)
	{
		const float Age=Now-R.Born;
		const FVector2D Centre=R.Centre+R.FlowCmPerS*Age,P=Field.ToFieldCm(Centre);
		const int32 X0=FMath::Max(0,FMath::FloorToInt((P.X-600)/Field.CellCm)),X1=FMath::Min(Field.SizeX-1,FMath::CeilToInt((P.X+600)/Field.CellCm));
		const int32 Y0=FMath::Max(0,FMath::FloorToInt((P.Y-600)/Field.CellCm)),Y1=FMath::Min(Field.SizeY-1,FMath::CeilToInt((P.Y+600)/Field.CellCm));
		for(int32 Y=Y0;Y<=Y1;++Y)for(int32 X=X0;X<=X1;++X)
		{
			const int32 I=Y*Field.SizeX+X;if(!Depth.IsValidIndex(I) || Depth[I]<=.015f)continue;
			const FVector2D Delta=Field.CellCentreCm(I)-Centre;
			const float Arc=FMath::SmoothStep(-80.f,80.f,float(FVector2D::DotProduct(Delta,R.Outward)));
			const float H=GTWaterInteractionVisuals::TrailWaveCm(Delta.Size(),Age,R.Energy)*Arc*Strength*FMath::SmoothStep(.015f,.18f,Depth[I]);
			Data[I].B=GTWaterInteractionVisuals::PackHeight(FMath::Clamp(GTWaterInteractionVisuals::UnpackHeight(Data[I].B)+H,-FMath::Min(18.f,Depth[I]*30),FMath::Min(30.f,Depth[I]*85)));
			Data[I].R=FMath::Max(Data[I].R,uint8(FMath::Clamp(FMath::RoundToInt(FMath::Max(0.f,H)*5),0,100)));
		}
	}
	static float LastLog=-100;
	if(CVarVisualWakeDebug.GetValueOnGameThread() && (Now-LastLog>1 || Now<LastLog))
	{
		LastLog=Now;uint8 Lo=128,Hi=128,ContactPeak=0;int32 ContactCells=0;
		for(const FColor& C:Data){Lo=FMath::Min(Lo,C.B);Hi=FMath::Max(Hi,C.B);ContactPeak=FMath::Max(ContactPeak,C.A);ContactCells+=C.A>64?1:0;}
		UE_LOG(LogTemp,Display,TEXT("GTWATER_VISUAL_WAKE sources=%d changed=%d modelPeak=%.2fcm upload=[%.2f,%.2f]cm contactPeak=%d contactCells=%d"),VisualVehicleWakes.Num(),Changed,Peak,GTWaterInteractionVisuals::UnpackHeight(Lo),GTWaterInteractionVisuals::UnpackHeight(Hi),int32(ContactPeak),ContactCells);
	}
}

bool AGTWaterSheet::SampleDomainWater(FVector2D XY,float& S,float& D,FVector2D& V) const
{
    if(!WaterDomain)return false;
    if(!DomainGroundSurface)return WaterDomain->Sample(XY,S,D,V);
    if(!WaterDomain->SampleEnvelope(XY,DomainShoreMarginCm,S,D,V))return false;
    const auto Bed=DomainGroundSurface->GroundHeightAt(FVector(XY,0));
    if(!Bed.IsSet())return false;
    D=FMath::Max(0.f,(S-Bed.GetValue()-DomainGroundSurface->BedDeltaCm(XY))*.01f);
    return D>.002f;
}

void AGTWaterSheet::RefreshDomainBed()
{
    if(!DomainGroundSurface || DomainGroundCm.Num()!=Field.NumCells())return;
    GT_PERF_SCOPE(PerfRiverBed,"Water.LiveRiverBed");
    TArray<float> H;H.Init(0,Field.NumCells());
    const auto& OldDepth=Field.GetRiverDepthM();
    bool Changed=OldDepth.Num()!=Field.NumCells();
    for(int32 I=0;I<Field.NumCells();++I)
    {
        if(DomainSupported[I])
        {
            const float Bed=DomainGroundCm[I]+DomainGroundSurface->BedDeltaCm(Field.CellCentreCm(I));
            H[I]=FMath::Clamp((DomainMeanCm[I]-Bed)*.01f,0.f,1.5f);
        }
        if(H[I]<.002f)H[I]=0;
        Changed|=!OldDepth.IsValidIndex(I) || H[I]!=OldDepth[I];
    }
    DomainBedRevision=DomainGroundSurface->BedRevision();
    // A global terrain revision can be outside this water window. Preserve the
    // entire live field in that case, without copies, flux rebuilds or resets.
    if(!Changed)return;
    TArray<float> X,Y;X.Init(0,Field.NumCells());Y=X;
    // Preserve disturbance and current history while replacing the authored mean depth.
    // Arrays are bounded to the existing 96-square window; no world-sized simulation.
    FGTWaterField Previous=Field;
    for(int32 I=0;I<Field.NumCells();++I)
    {
        Field.BedCm[I]=DomainMeanCm[I]-H[I]*100;
        if(I%Field.SizeX+1<Field.SizeX)X[I]=FMath::Min(H[I],H[I+1])*Field.CellCm*.01f*.5f*(DomainCurrent[I].X+DomainCurrent[I+1].X);
        if(I/Field.SizeX+1<Field.SizeY)Y[I]=FMath::Min(H[I],H[I+Field.SizeX])*Field.CellCm*.01f*.5f*(DomainCurrent[I].Y+DomainCurrent[I+Field.SizeX].Y);
    }
    if(Field.SetRiverReference(H,X,Y,true))Field.CopyRiverOverlap(Previous);
    DomainBedRevision=DomainGroundSurface->BedRevision();
    PerfRiverBed.Work=Field.NumCells();
}

bool AGTWaterSheet::MoveWaterWindow(FVector2D Focus,bool Force)
{
	if(!WaterDomain) return false;
	constexpr float Cell=62.5f;
	constexpr int32 Side=96;
	// Re-centre in 10 m blocks. Every overlapping cell/face keeps the same world coordinates.
	const FVector2D Mid(FMath::FloorToDouble(Focus.X/1000)*1000,FMath::FloorToDouble(Focus.Y/1000)*1000);
	if(!Force && Field.HasRiverReference() && (Focus-DomainFocus).GetAbsMax()<1000) return false;
	GT_PERF_SCOPE(PerfWMove,"Water.MoveWindow");
	DomainFocus=Mid;
	FGTWaterField Previous=MoveTemp(Field);Field=FGTWaterField();
	Field.WindRippleCm=WindRippleCm;Field.RainDropCm=RainDropCm;Field.RainDropsPerM2S=RainDropsPerM2S;
	Field.HeadDropCm=0;Field.WindScale=0;Field.RiverAbsorbWidthM=6;
	Field.bRiverVisuals=true;
	Field.Init(Mid,FVector2D(1,0),Side*Cell*.5f,Side*Cell*.5f,Cell,BaseLevelCm,[](const FVector2D&){return 0.f;});
	TArray<float> H,X,Y;H.Init(0,Field.NumCells());X=H;Y=H;
	TArray<FVector2D> V;V.Init(FVector2D::ZeroVector,Field.NumCells());
	TArray<float> Mean;Mean.Init(0,Field.NumCells());
	DomainGroundCm.Init(0,Field.NumCells());DomainSupported.Init(0,Field.NumCells());
	for(int32 I=0;I<Field.NumCells();++I)
	{
		float S,D;FVector2D Flow;
		const FVector2D XY=Field.CellCentreCm(I);
		bool Wet=false;
		if(DomainGroundSurface)
		{
			const bool Supported=WaterDomain->SampleEnvelope(XY,DomainShoreMarginCm,S,D,Flow);
			// Outside the authored shore envelope this cell cannot become wet.
			// Avoid thousands of unused terrain queries when travelling inland.
			const auto Bed=Supported ? DomainGroundSurface->GroundHeightAt(FVector(XY,0)) : TOptional<float>();
			DomainSupported[I]=Supported && Bed.IsSet();
			DomainGroundCm[I]=Bed.IsSet()?Bed.GetValue():S+100;
			D=DomainSupported[I] ? (S-DomainGroundCm[I]-DomainGroundSurface->BedDeltaCm(XY))*.01f : 0.f;
			Wet=DomainSupported[I] && D>.002f;
		}
		else Wet=WaterDomain->Sample(XY,S,D,Flow);
		// Deep lakes use an effective 1.5 m surface-wave layer; hull depth queries still read the
		// actual world water elevation, not this numerical bed. This is not a deep-water solver.
		H[I]=Wet?FMath::Clamp(D,.008f,1.5f):0;Mean[I]=S;
		V[I]=(Wet || DomainSupported[I])?Flow.GetClampedToMaxSize(1.5):FVector2D::ZeroVector;
	}
	// Extend wet heights into dry vertices. Blurring with dry sentinels pulled shoreline triangles
	// down toward lake level and made angular stripes even though the wet cell heights were correct.
	TArray<int32> Queue;TArray<uint8> Filled;Filled.Init(0,Field.NumCells());
	for(int32 I=0;I<Field.NumCells();++I) if(H[I]>0 || DomainSupported[I]) {Queue.Add(I);Filled[I]=1;}
	for(int32 Head=0;Head<Queue.Num();++Head)
	{
		const int32 I=Queue[Head],CX=I%Side,CY=I/Side;
		for(int32 J:{CX>0?I-1:-1,CX+1<Side?I+1:-1,CY>0?I-Side:-1,CY+1<Side?I+Side:-1})
			if(J>=0 && !Filled[J]) {Mean[J]=Mean[I];Filled[J]=1;Queue.Add(J);}
	}
	for(int32 I=0;I<Field.NumCells();++I)
	{
		Field.BedCm[I]=Mean[I]-H[I]*100;
		if(I%Side+1<Side) X[I]=FMath::Min(H[I],H[I+1])*(Cell*.01f)*.5f*(V[I].X+V[I+1].X);
		if(I/Side+1<Side) Y[I]=FMath::Min(H[I],H[I+Side])*(Cell*.01f)*.5f*(V[I].Y+V[I+Side].Y);
	}
	if(!Field.SetRiverReference(H,X,Y,true)) {Field=MoveTemp(Previous);return false;}
	DomainMeanCm=Mean;DomainCurrent=V;
	if(DomainGroundSurface)DomainBedRevision=DomainGroundSurface->BedRevision();
	const int32 Kept=Field.CopyRiverOverlap(Previous);
	LastSubStepsAsked=0;LastSubStepsRun=0;LastClamps=0;LastDeficitSeconds=0;
	float S,D;FVector2D Flow;WaterDomain->Sample(Focus,S,D,Flow);BaseLevelCm=S;
	if(!FieldTexture) BuildSurfaceMesh();
	if(DomainGroundSurface)
	{
		if(!DomainGroundTexture)
		{
			DomainGroundTexture=UTexture2D::CreateTransient(Side,Side,PF_G32R32F);
			DomainGroundTexture->SRGB=false;DomainGroundTexture->Filter=TF_Bilinear;
			DomainGroundTexture->AddressX=TA_Clamp;DomainGroundTexture->AddressY=TA_Clamp;
			DomainGroundTexture->UpdateResource();
		}
		auto* Data=new TArray<FVector2f>();Data->SetNumUninitialized(Field.NumCells());
		for(int32 I=0;I<Field.NumCells();++I)(*Data)[I]=FVector2f(DomainGroundCm[I],DomainSupported[I]);
		auto* Region=new FUpdateTextureRegion2D(0,0,0,0,Side,Side);
		DomainGroundTexture->UpdateTextureRegions(0,1,Region,Side*sizeof(FVector2f),sizeof(FVector2f),reinterpret_cast<uint8*>(Data->GetData()),
			[Data](uint8*,const FUpdateTextureRegion2D* R){delete Data;delete R;});
	}
	SurfaceMesh->SetWorldLocation(FVector(Mid.X,Mid.Y,BaseLevelCm));
	PerfWMove.Work=Field.NumCells();
	BindWaterWindow();UploadField();UploadRiverDetail();bFieldBuilt=true;
	UpdateAmbientWaves(GetWorld()->GetTimeSeconds(),true);
	UE_LOG(LogTemp,Display,TEXT("GTWATERDOMAIN window %.1f %.1f: %d cells, %d retained; discarded disturbance %.6fm3"),Mid.X*.01,Mid.Y*.01,Field.NumCells(),Kept,Field.RiverWindowDiscardM3);
	return true;
}

void AGTWaterSheet::BindWaterWindow()
{
	if(!SurfaceMaterial || !FieldTexture) return;
	if(!RiverDetailTexture)
	{
		RiverDetailTexture=UTexture2D::CreateTransient(Field.SizeX,Field.SizeY,PF_B8G8R8A8);
		RiverDetailTexture->SRGB=false;RiverDetailTexture->Filter=TF_Bilinear;
		RiverDetailTexture->AddressX=TA_Clamp;RiverDetailTexture->AddressY=TA_Clamp;
		FTexture2DMipMap& Mip=RiverDetailTexture->GetPlatformData()->Mips[0];
		void* Pixels=Mip.BulkData.Lock(LOCK_READ_WRITE);
		for(int32 I=0;I<Field.NumCells();++I) static_cast<FColor*>(Pixels)[I]=FColor(0,0,128,0);
		Mip.BulkData.Unlock();RiverDetailTexture->UpdateResource();
	}
	if(DomainMaterials.IsEmpty())
	{
		// DomainMaterials is Transient: a PIE copy (or a reload) starts empty while each surface still
		// carries the MID an editor-world bind (PreviewWaterAt) put on it. Reuse our own MID; never wrap a
		// MID in another MID (an invalid parent leaves the surface drawing the default material).
		auto Bind=[this](UMeshComponent* C)
		{
			UMaterialInterface* Base=C->GetMaterial(0);
			UMaterialInstanceDynamic* M=Cast<UMaterialInstanceDynamic>(Base);
			if(M && M->GetOuter()!=this){Base=M->Parent;M=nullptr;}
			if(!M)
			{
				if(!Base)return;
				M=UMaterialInstanceDynamic::Create(Base,this);C->SetMaterial(0,M);
			}
			DomainMaterials.AddUnique(M);
		};
		for(UMeshComponent* C:RoadPoolSurfaces)if(IsValid(C))Bind(C);
		for(AStaticMeshActor* A:DomainSurfaces)if(A && A->GetStaticMeshComponent())Bind(A->GetStaticMeshComponent());
	}
	TArray<UMaterialInstanceDynamic*> All;All.Add(SurfaceMaterial);
	for(UMaterialInstanceDynamic* M:DomainMaterials) All.Add(M);
	for(UMaterialInstanceDynamic* M:All)
	{
		M->SetTextureParameterValue(TEXT("FieldTex"),FieldTexture);
		M->SetTextureParameterValue(TEXT("DetailTex"),RiverDetailTexture);
		M->SetVectorParameterValue(TEXT("FieldMin"),FLinearColor(Field.OriginCm.X,Field.OriginCm.Y,0,0));
		M->SetVectorParameterValue(TEXT("FieldSize"),FLinearColor(Field.SizeX*Field.CellCm,Field.SizeY*Field.CellCm,0,0));
		M->SetVectorParameterValue(TEXT("FieldTexels"),FLinearColor(Field.SizeX,Field.SizeY,0,0));
		M->SetScalarParameterValue(TEXT("FieldLevelCm"),BaseLevelCm);
		M->SetScalarParameterValue(TEXT("FieldActive"),1);
		M->SetScalarParameterValue(TEXT("WakeDetailReady"),1);
		M->SetScalarParameterValue(TEXT("LocalSurface"),M==SurfaceMaterial?1:0);
		if(DomainGroundTexture && DomainGroundSurface)
		{
			M->SetTextureParameterValue(TEXT("RiverGroundTex"),DomainGroundTexture);
			M->SetScalarParameterValue(TEXT("RiverGroundReady"),1);
			DomainGroundSurface->RegisterResearchMaterial(M);
		}
	}
}

void AGTWaterSheet::UploadRiverDetail()
{
	if(!RiverDetailTexture || !RiverDetailTexture->GetResource() || Field.RiverDetail.Num()!=Field.NumCells()) return;
	GT_PERF_SCOPE(PerfWDetail,"Water.UploadRiverDetail");PerfWDetail.Work=Field.NumCells();
	TArray<FColor>* Data=new TArray<FColor>();Data->SetNumUninitialized(Field.NumCells());
	const bool Enabled=CVarDomainDetail.GetValueOnGameThread()!=0;
	const TArray<float>& ReferenceDepth=Field.GetRiverDepthM();
	for(int32 I=0;I<Field.NumCells();++I)
	{
		const FVector2f V=Enabled?Field.RiverDetail[I]:FVector2f::ZeroVector;
		const float Extra=ReferenceDepth.IsValidIndex(I) ? GTWaterInteractionVisuals::ExtraHeightCm(
			Field.SurfaceCm[I]-Field.BedCm[I]-ReferenceDepth[I]*100,ReferenceDepth[I],CVarWakeRelief.GetValueOnGameThread()) : 0;
		(*Data)[I]=FColor(FMath::Clamp(FMath::RoundToInt(V.X*255),0,255),FMath::Clamp(FMath::RoundToInt(V.Y*255),0,255),GTWaterInteractionVisuals::PackHeight(Extra),0);
	}
	RasterVisualVehicleWakes(*Data);
	FUpdateTextureRegion2D* Region=new FUpdateTextureRegion2D(0,0,0,0,Field.SizeX,Field.SizeY);
	RiverDetailTexture->UpdateTextureRegions(0,1,Region,Field.SizeX*sizeof(FColor),sizeof(FColor),reinterpret_cast<uint8*>(Data->GetData()),
		[Data](uint8*,const FUpdateTextureRegion2D* R){delete Data;delete R;});
}

void AGTWaterSheet::TickWaterDomain(float Dt)
{
	CSV_SCOPED_TIMING_STAT(GTWater,DomainTick);
	GT_PERF_SCOPE(PerfWTick,"Water.TickDomain");
	FVector Focus=GetActorLocation();
	if(const APlayerController* PC=GetWorld()->GetFirstPlayerController())
	{
		if(PC->GetPawn()) Focus=PC->GetPawn()->GetActorLocation();
		else if(PC->PlayerCameraManager) Focus=PC->PlayerCameraManager->GetCameraLocation();
	}
	MoveWaterWindow(FVector2D(Focus));
	DomainBedCarry+=Dt;
	if(DomainGroundSurface && DomainBedCarry>=.1f)
	{
		DomainBedCarry=0;
		if(DomainBedRevision!=DomainGroundSurface->BedRevision())
		{
			TArray<FBox2D> Changed;DomainGroundSurface->BedChangesSince(DomainBedRevision,Changed);
			const FBox2D Window(Field.OriginCm,Field.OriginCm+FVector2D(Field.SizeX*Field.CellCm,Field.SizeY*Field.CellCm));
			if(Changed.ContainsByPredicate([&](const FBox2D& Box){return Window.Intersect(Box);}))RefreshDomainBed();
			else DomainBedRevision=DomainGroundSurface->BedRevision();
		}
	}
	// Independent of local wet-cell count: distant river/lake still need ambient motion.
	UpdateAmbientWaves(GetWorld()->GetTimeSeconds());
	if(!Field.HasRiverReference()) return;
	static const IConsoleVariable* Lids=IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Water.Lids"));
	static const IConsoleVariable* Wind=IConsoleManager::Get().FindConsoleVariable(TEXT("gt.Water.Wind"));
	bLidsOn=!Lids || Lids->GetFloat()>0;
	if(!bLidsOn) Field.ClearLids();
	const UGTWeatherSubsystem* Weather=GetWorld()->GetSubsystem<UGTWeatherSubsystem>();
	Field.WindScale=Wind?Wind->GetFloat():1;Field.RainIntensity=Weather?Weather->GetRainAt(Focus):0;
	if(Field.WetCellCount==0) return;
	{GT_PERF_SCOPE(PerfWStep,"Water.FieldStep");PerfWStep.Work=Field.WetCellCount;Field.Step(Dt,BaseLevelCm,1);}
	const int32 DetailOn=CVarDomainDetail.GetValueOnGameThread()!=0;
	if(DetailOn){GT_PERF_SCOPE(PerfWRiver,"Water.RiverDetailStep");PerfWRiver.Work=Field.RiverActiveCells();Field.StepRiverDetail(Dt);}else Field.RiverDetailMs=0;
	if(DomainDetailEnabled!=DetailOn)
	{
		DomainDetailEnabled=DetailOn;
		if(SurfaceMaterial)SurfaceMaterial->SetScalarParameterValue(TEXT("DetailEnabled"),DetailOn);
		for(UMaterialInstanceDynamic* M:DomainMaterials)if(M)M->SetScalarParameterValue(TEXT("DetailEnabled"),DetailOn);
	}
	DomainUploadCarry+=Dt;
	const float Interval=1.f/FMath::Clamp(CVarDomainUploadHz.GetValueOnGameThread(),15.f,60.f);
	if(DomainUploadCarry>=Interval){DomainUploadCarry=FMath::Fmod(DomainUploadCarry,Interval);UploadField();UploadRiverDetail();}
	CSV_CUSTOM_STAT(GTWater,DetailMs,Field.RiverDetailMs,ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(GTWater,ActiveCells,Field.RiverActiveCells(),ECsvCustomStatOp::Set);
	AccumulateStats(Dt);
}

void AGTWaterSheet::PreviewWaterAt(FVector2D WorldXY,float Seconds,bool Reset)
{
	if(!WaterDomain || !GetWorld() || GetWorld()->IsGameWorld()) return;
	MoveWaterWindow(WorldXY);if(!Field.HasRiverReference()) return;
	if(Reset) Field.ResetRiverReference();Field.WindScale=0;Field.RainIntensity=0;
	for(int32 I=0;I<FMath::Clamp(FMath::RoundToInt(Seconds*60),0,600);++I){Field.Step(1.f/60,BaseLevelCm,1);Field.StepRiverDetail(1.f/60);}
	UploadField();UploadRiverDetail();
}

void AGTWaterSheet::PreviewWaterWake(FVector2D Start,FVector2D End,float Seconds)
{
	if(!WaterDomain || !GetWorld() || GetWorld()->IsGameWorld())return;
	MoveWaterWindow((Start+End)*.5);Field.WindScale=0;Field.RainIntensity=0;
	const int32 Steps=FMath::Clamp(FMath::RoundToInt(Seconds*60),1,600);
	const FVector2D Forward=(End-Start).GetSafeNormal();
	for(int32 I=0;I<Steps;++I)
	{
		const FVector2D P=FMath::Lerp(Start,End,float(I)/Steps);
		if(Covers(P))Field.StampLid(P,Forward,140,75,Field.SurfaceCmAt(P)-12,FVector2D::ZeroVector,12,.65f);
		Field.Step(1.f/60,BaseLevelCm,1);Field.StepRiverDetail(1.f/60);
	}
	UploadField();UploadRiverDetail();
}
