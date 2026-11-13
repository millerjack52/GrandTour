#include "Vehicle/GTBodyComponent.h"

#include "Vehicle/GTBodyStateComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Vehicle/GTRangeRoverAudioComponent.h"
#include "UI/GTWorkshopComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Parts/GTPartSlotsComponent.h"

#include "AnimationRuntime.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "Terrain/GTLandscapeSurface.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "PhysicsEngine/BodySetup.h"

namespace
{
	const FName ParamBaseColor(TEXT("BaseColor"));
	const FName ParamImpactTex(TEXT("ImpactTex"));
	const FName ParamImpactCount(TEXT("ImpactCount"));
	const FName ParamCrack(TEXT("Crack"));
	const FName ParamDirt(TEXT("Dirt"));
	const FName ParamWetness(TEXT("Wetness"));
	const FName ParamSnow(TEXT("Snow"));
	// MudRunner MR2: the muddy vehicle (setup_m1_body.py's Grime node, M_GT_Tyre, M_GT_Glass).
	const FName ParamCarMud(TEXT("CarMud"));
	const FName ParamMudBaseZ(TEXT("MudBaseZ"));
	const FName ParamMudLineCm(TEXT("MudLineCm"));
	const FName ParamWashCm(TEXT("WashCm"));
	const FName ParamWashAmount(TEXT("WashAmount"));
	const FName ParamMudWet(TEXT("MudWet"));
	const FName ParamCoatEnds(TEXT("CoatEnds"));
	const FName ParamCoatArches(TEXT("CoatArches"));
	const FName ParamCoatSides(TEXT("CoatSides"));
	const FName ParamWheelGeom(TEXT("WheelGeom"));
	const FName ParamTyreCoat(TEXT("TyreCoat"));
	// MR2b: the wheels' spray fans (FL, FR, RL, RR): each fan's coat and the side it opens to (+1 behind the arch).
	const FName ParamFanCoat(TEXT("FanCoat"));
	const FName ParamFanDir(TEXT("FanDir"));
	const FName ParamGlassSizeX(TEXT("GlassSizeX"));
	const FName ParamGlassSizeY(TEXT("GlassSizeY"));
	const TCHAR* TyreMaterialPath = TEXT("/Game/GrandTour/Materials/M_GT_Tyre.M_GT_Tyre");
	// Look L1 follow-up 3: M_GT_Vehicle's painted path (setup_m1_body.py).
	const FName ParamUsePaint(TEXT("UsePaint"));
	const FName ParamPaintAlbedo(TEXT("PaintAlbedo"));
	const FName ParamPaintMask(TEXT("PaintMask"));
	const FName ParamPaintNormal(TEXT("PaintNormal"));
	constexpr int32 ImpactTextureWidth = 32;

	struct FRegionRule
	{
		const TCHAR* Prefix;
		EGTDamageRegion Region;
	};

	// Panel name (after SM_RR_) prefix -> damage region. Structural parts map to None and never detach.
	const FRegionRule RegionRules[] = {
		{TEXT("Bonnet"), EGTDamageRegion::Front},
		{TEXT("FrontPanel"), EGTDamageRegion::Front},
		{TEXT("Bumper"), EGTDamageRegion::Front},
		{TEXT("FrontWheelArch_L"), EGTDamageRegion::ArchFL},
		{TEXT("FrontWheelArch_R"), EGTDamageRegion::ArchFR},
		{TEXT("FrontDoors_L"), EGTDamageRegion::SideL},
		{TEXT("FrontDoors_R"), EGTDamageRegion::SideR},
		{TEXT("PassengerDoors_L"), EGTDamageRegion::SideL},
		{TEXT("PassengerDoors_R"), EGTDamageRegion::SideR},
		{TEXT("RearArches_L"), EGTDamageRegion::ArchRL},
		{TEXT("RearArches_R"), EGTDamageRegion::ArchRR},
		{TEXT("Boot"), EGTDamageRegion::Rear},
		{TEXT("RearPanel"), EGTDamageRegion::Rear},
		{TEXT("Roof"), EGTDamageRegion::Roof},
		{TEXT("RearBumper"), EGTDamageRegion::Rear},
		{TEXT("BaseInterior"), EGTDamageRegion::None},
		{TEXT("Pillars"), EGTDamageRegion::None},
	};

	const TCHAR* RegionName(EGTDamageRegion Region)
	{
		switch (Region)
		{
		case EGTDamageRegion::Front:  return TEXT("Front");
		case EGTDamageRegion::Rear:   return TEXT("Rear");
		case EGTDamageRegion::ArchFL: return TEXT("ArchFL");
		case EGTDamageRegion::ArchFR: return TEXT("ArchFR");
		case EGTDamageRegion::ArchRL: return TEXT("ArchRL");
		case EGTDamageRegion::ArchRR: return TEXT("ArchRR");
		case EGTDamageRegion::SideL:  return TEXT("SideL");
		case EGTDamageRegion::SideR:  return TEXT("SideR");
		case EGTDamageRegion::Roof:   return TEXT("Roof");
		case EGTDamageRegion::Glass:  return TEXT("Glass");
		default:                      return TEXT("Structure");
		}
	}

	/** Look L1 follow-up 3: the owner's GT Paint bake for one panel. The bake is keyed by the panel's name with a
	 *  trailing _L/_R stripped (export_rangerover.py splits a mirrored Blender object into _L/_R; a one-object bake keeps
	 *  that object's UV, so both halves read it). With T_GT_<Asset>_D and _M found, the instance gets them and UsePaint 1,
	 *  plus PaintNormal when a _N exists (else M_GT_Vehicle's flat default). Returns false, the instance untouched, when
	 *  there is no _D; Got says what was set. */
	bool ApplyPanelPaint(const FString& PanelName, UMaterialInstanceDynamic* Material, const TMap<FString, FAssetData>& PaintAssets, FString& Got)
	{
		FString Asset = PanelName;
		if (Asset.EndsWith(TEXT("_L")) || Asset.EndsWith(TEXT("_R")))
		{
			Asset.LeftChopInline(2);
		}
		auto Find = [&PaintAssets, &Asset](const TCHAR* Suffix) -> UTexture*
		{
			const FAssetData* Data = PaintAssets.Find(FString::Printf(TEXT("T_GT_%s_%s"), *Asset, Suffix));
			return Data ? Cast<UTexture>(Data->GetAsset()) : nullptr;
		};
		UTexture* Albedo = Find(TEXT("D"));
		if (!Material || !Albedo)
		{
			return false;
		}
		UTexture* Mask = Find(TEXT("M"));
		if (!Mask)
		{
			UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: %s has T_GT_%s_D but no _M; left unpainted (rerun Art/setup_look_l1.bat)"), *PanelName, *Asset);
			return false;
		}
		Material->SetTextureParameterValue(ParamPaintAlbedo, Albedo);
		Material->SetTextureParameterValue(ParamPaintMask, Mask);
		UTexture* Normal = Find(TEXT("N"));
		if (Normal)
		{
			Material->SetTextureParameterValue(ParamPaintNormal, Normal);
		}
		Material->SetScalarParameterValue(ParamUsePaint, 1.f);
		Got = FString::Printf(TEXT("%s=%s%s"), *PanelName, *Asset, Normal ? TEXT("+N") : TEXT(""));
		return true;
	}
}

UGTBodyComponent::UGTBodyComponent()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AGTCarPawn::Tick after the condition update
	// The materials are loaded in BeginPlay, not by a constructor finder: assets loaded at startup
	// are rooted, and Art/setup_m1_body.bat could then no longer rebuild them (engine assertion).
}

EGTDamageRegion UGTBodyComponent::RegionForPanel(const FString& Name, const FBox& LocalBounds)
{
	for (const FRegionRule& Rule : RegionRules)
	{
		if (Name.StartsWith(Rule.Prefix))
		{
			return Rule.Region;
		}
	}
	return UGTConditionComponent::ResolveRegion(LocalBounds.GetCenter());
}

FVector UGTBodyComponent::OutwardDirection(EGTDamageRegion Region)
{
	// Car space: X forward, Y right, Z up.
	switch (Region)
	{
	case EGTDamageRegion::Front:  return FVector(1.f, 0.f, 0.f);
	case EGTDamageRegion::Rear:   return FVector(-1.f, 0.f, 0.f);
	case EGTDamageRegion::SideL:  return FVector(0.f, -1.f, 0.f);
	case EGTDamageRegion::SideR:  return FVector(0.f, 1.f, 0.f);
	case EGTDamageRegion::ArchFL: return FVector(0.5f, -1.f, 0.f).GetSafeNormal();
	case EGTDamageRegion::ArchFR: return FVector(0.5f, 1.f, 0.f).GetSafeNormal();
	case EGTDamageRegion::ArchRL: return FVector(-0.5f, -1.f, 0.f).GetSafeNormal();
	case EGTDamageRegion::ArchRR: return FVector(-0.5f, 1.f, 0.f).GetSafeNormal();
	default:                      return FVector(0.f, 0.f, 1.f);
	}
}

void UGTBodyComponent::BeginPlay()
{
	Super::BeginPlay();
	USkeletalMeshComponent* Mesh = GetOwner() ? GetOwner()->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
	if (!Mesh)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: no skeletal mesh on %s"), *GetNameSafe(GetOwner()));
		return;
	}
	VehicleMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/GrandTour/Materials/M_GT_Vehicle.M_GT_Vehicle"));
	if (UGTRangeRoverAudioComponent::IsRangeRover(GetOwner()))
	{
		if (auto* WorkshopMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/GrandTour/UI/Workshop/M_GT_WorkshopVehicle.M_GT_WorkshopVehicle")))
		{
			VehicleMaterial = WorkshopMaterial;
			bWorkshopReady = true;
		}
	}
	GlassMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/GrandTour/Materials/M_GT_Glass.M_GT_Glass"));
	if (!VehicleMaterial)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: M_GT_Vehicle missing (run Art/setup_m1_body.bat); panels will be untextured"));
	}
	ImpactTexture = UTexture2D::CreateTransient(ImpactTextureWidth, 2, PF_A32B32G32R32F);
	ImpactTexture->SRGB = false;
	ImpactTexture->Filter = TF_Nearest;
	ImpactTexture->NeverStream = true;
	ImpactTexture->UpdateResource();

	ComputeWheelGeometry(Mesh);
	AttachPanels(Mesh);
	if (Panels.Num() > 0)
	{
		HideSkeletalSections(Mesh);
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: no %s* static meshes in %s; the skeletal mesh keeps drawing the body"), *PanelPrefix, *PanelFolder);
	}
	if (bBuildWindscreen)
	{
		BuildWindscreen(Mesh);
	}
	DressTyres(Mesh);
	if (bWorkshopReady)
	{
		BuildWorkshopWheels(Mesh);
		BuildWorkshopEquipment(Mesh);
		if (auto* Save = Cast<UGTWorkshopSave>(UGameplayStatics::LoadGameFromSlot(UGTWorkshopComponent::SaveSlot(), 0)))
		{
			SetWorkshopAppearance(Save->Paint, Save->RimModel >= 0 ? Save->RimModel : Save->Rims==3 ? 1 : Save->Rims==2 ? 2 : 0, 0);
			SetWorkshopEquipment(Save->Equipment);
		}
		else SetWorkshopAppearance(0,0,0);
	}
}

void UGTBodyComponent::SetWorkshopAppearance(int32 Paint, int32 Rims, int32 Tyres)
{
	if (!bWorkshopReady) return;
	WorkshopPaint = FMath::Clamp(Paint, 0, 5);
	ApplyWorkshopWheels(FMath::Clamp(Rims,0,2),FMath::Clamp(Tyres,0,2));
	WorkshopRims = FMath::Clamp(Rims, 0, 2);
	WorkshopTyres = FMath::Clamp(Tyres, 0, 2);
	for (const auto& Panel : Panels)
	{
		// Paint includes the roof; black trim, chassis and interior retain their own finishes.
		const bool bBody = Panel.Name.StartsWith(TEXT("Bonnet")) || Panel.Name.StartsWith(TEXT("FrontPanel")) ||
			Panel.Name.StartsWith(TEXT("FrontDoors")) || Panel.Name.StartsWith(TEXT("PassengerDoors")) ||
			Panel.Name.StartsWith(TEXT("FrontWheelArch")) || Panel.Name.StartsWith(TEXT("RearArches")) ||
			Panel.Name.StartsWith(TEXT("Boot")) || Panel.Name.StartsWith(TEXT("RearPanel")) || Panel.Name.StartsWith(TEXT("Pillars")) ||
			Panel.Name.StartsWith(TEXT("Roof"));
		if (PanelMaterials.IsValidIndex(Panel.Index) && PanelMaterials[Panel.Index])
		{
			PanelMaterials[Panel.Index]->SetScalarParameterValue(TEXT("WorkshopPaintAmount"), bBody && WorkshopPaint>0 ? 1.f : 0.f);
			PanelMaterials[Panel.Index]->SetVectorParameterValue(TEXT("WorkshopPaint"), UGTWorkshopComponent::PaintColour(WorkshopPaint));
		}
	}
	if (TyreMaterial)
	{
		TyreMaterial->SetVectorParameterValue(TEXT("RimColour"), UGTWorkshopComponent::RimColour(WorkshopRims));
		TyreMaterial->SetScalarParameterValue(TEXT("WorkshopTread"), Tyres>0 ? 1.f : 0.f);
	}
}

void UGTBodyComponent::BuildWorkshopEquipment(USkeletalMeshComponent* Mesh)
{
    const TCHAR* Names[]={TEXT("SM_RR_RoofRack"),TEXT("SM_RR_BullBar"),TEXT("SM_RR_Snorkel")};
    TArray<UStaticMesh*> Assets;
    for(const TCHAR* Name:Names)
    {
        const FString Path=FString::Printf(TEXT("/Game/GrandTour/UI/Workshop/Equipment/%s.%s"),Name,Name);
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path);
        if(!Asset)return;
        Assets.Add(Asset);
    }
    for(int32 I=0;I<3;++I)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner(),*FString::Printf(TEXT("WorkshopEquipment_%d"),I),RF_Transient);
        C->SetupAttachment(Mesh);C->SetMobility(EComponentMobility::Movable);
        C->SetStaticMesh(Assets[I]);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);
        C->SetVisibility(false);C->RegisterComponent();WorkshopEquipmentComponents.Add(C);
        for(int32 M=0;M<C->GetNumMaterials();++M)
            if(auto* MID=C->CreateDynamicMaterialInstance(M)) { WorkshopEquipmentMaterials.Add(MID);WorkshopEquipmentMaterialParts.Add(I); }
    }
}

void UGTBodyComponent::SetWorkshopEquipment(int32 Mask)
{
    if(!WorkshopEquipmentReady())return;
    WorkshopEquipment=Mask&7;
    for(int32 I=0;I<3;++I)WorkshopEquipmentComponents[I]->SetVisibility((WorkshopEquipment&(1<<I))!=0);
}

void UGTBodyComponent::BuildWorkshopWheels(USkeletalMeshComponent* Mesh)
{
	const TCHAR* Names[]={TEXT("SM_Rim_Pressed"),TEXT("SM_Rim_Alloy"),TEXT("SM_Rim_Heavy"),TEXT("SM_Tyre_Road"),TEXT("SM_Tyre_AllTerrain"),TEXT("SM_Tyre_Mud")};
	TArray<UStaticMesh*> Assets;
	for(const TCHAR* Name:Names)
	{
		const FString Path=FString::Printf(TEXT("/Game/GrandTour/UI/Workshop/Wheels/%s.%s"),Name,Name);
		auto* Asset=LoadObject<UStaticMesh>(nullptr,*Path);
		if(!Asset) { UE_LOG(LogTemp,Warning,TEXT("Workshop wheel missing: %s"),*Path); return; }
		Assets.Add(Asset);
	}
	const FName Bones[]={TEXT("Wheel_FL"),TEXT("Wheel_FR"),TEXT("Wheel_RL"),TEXT("Wheel_RR")};
	for(FName Bone:Bones) if(Mesh->GetBoneIndex(Bone)==INDEX_NONE) return;
	for(int32 I=0;I<3;++I) { WorkshopRimMeshes.Add(Assets[I]); WorkshopTyreMeshes.Add(Assets[I+3]); }
	for(int32 Wheel=0;Wheel<4;++Wheel)
	{
		for(int32 Kind=0;Kind<2;++Kind)
		{
			auto* Component=NewObject<UStaticMeshComponent>(GetOwner(),*FString::Printf(TEXT("Workshop%s_%d"),Kind==0?TEXT("Rim"):TEXT("Tyre"),Wheel),RF_Transient);
			Component->SetMobility(EComponentMobility::Movable);
			Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetGenerateOverlapEvents(false); Component->SetCanEverAffectNavigation(false);
			Component->SetupAttachment(Mesh,Bones[Wheel]);
			Component->SetRelativeRotation(FRotator(0,Wheel%2 ? 180.f : 0.f,0));
			Component->RegisterComponent();
			(Kind==0?WorkshopRimComponents:WorkshopTyreComponents).Add(Component);
		}
	}
	ApplyWorkshopWheels(0,0);
	for(FName Slot:KeepSkeletalSlots)
	{
		const int32 Index=Mesh->GetMaterialIndex(Slot);
		if(Index!=INDEX_NONE) for(int32 LOD=0;LOD<Mesh->GetSkeletalMeshAsset()->GetLODNum();++LOD) Mesh->ShowMaterialSection(Index,0,false,LOD);
	}
}

void UGTBodyComponent::ApplyWorkshopWheels(int32 Rims,int32 Tyres)
{
	if(!WorkshopWheelsReady()) return;
	if(WorkshopRimComponents[0]->GetStaticMesh()==WorkshopRimMeshes[Rims] && WorkshopTyreComponents[0]->GetStaticMesh()==WorkshopTyreMeshes[Tyres]) return;
	WorkshopWheelMaterials.Reset(); WorkshopMaterialWheels.Reset();
	const FLinearColor Coats=TyreMaterial ? TyreMaterial->K2_GetVectorParameterValue(ParamTyreCoat) : FLinearColor::Black;
	const float Wet=TyreMaterial ? TyreMaterial->K2_GetScalarParameterValue(ParamWetness) : 0.f;
	for(int32 Wheel=0;Wheel<4;++Wheel)
	{
		for(int32 Kind=0;Kind<2;++Kind)
		{
			auto* Component=(Kind==0?WorkshopRimComponents:WorkshopTyreComponents)[Wheel].Get();
			auto* Asset=(Kind==0?WorkshopRimMeshes[Rims]:WorkshopTyreMeshes[Tyres]).Get();
			Component->EmptyOverrideMaterials(); Component->SetStaticMesh(Asset);
			for(int32 Slot=0;Slot<Asset->GetStaticMaterials().Num();++Slot)
			{
				auto* Material=Component->CreateDynamicMaterialInstance(Slot);
				if(Material) { Material->SetScalarParameterValue(TEXT("Coat"),Coats.Component(Wheel)); Material->SetScalarParameterValue(ParamWetness,Wet); WorkshopWheelMaterials.Add(Material); WorkshopMaterialWheels.Add(Wheel); }
			}
		}
	}
	PushedMud.Reset();
}

void UGTBodyComponent::ComputeWheelGeometry(USkeletalMeshComponent* Mesh)
{
	// The wheels' hubs in the skeleton's rest pose (component space = car space, the panels' own), and the drawn radius (the
	// wheel class's default: the Chaos radius is what the sinkage shrinks).
	const UChaosWheeledVehicleMovementComponent* Move = GetOwner() ? GetOwner()->FindComponentByClass<UChaosWheeledVehicleMovementComponent>() : nullptr;
	const USkeletalMesh* Asset = Mesh ? Mesh->GetSkeletalMeshAsset() : nullptr;
	if (!Move || !Asset)
	{
		return;
	}
	const FReferenceSkeleton& Skeleton = Asset->GetRefSkeleton();
	double FrontX = 0.0, RearX = 0.0, HubZ = 0.0, Radius = 0.0, Base = 0.0;
	int32 Front = 0, Rear = 0, Count = 0;
	for (const FChaosWheelSetup& Setup : Move->WheelSetups)
	{
		const int32 Bone = Skeleton.FindBoneIndex(Setup.BoneName);
		if (Bone == INDEX_NONE)
		{
			continue;
		}
		const FVector Hub = FAnimationRuntime::GetComponentSpaceTransformRefPose(Skeleton, Bone).GetLocation();
		const float DrawnRadius = Setup.WheelClass ? GetDefault<UChaosVehicleWheel>(Setup.WheelClass)->WheelRadius : 38.f;
		(Hub.X >= 0.0 ? FrontX : RearX) += Hub.X;
		(Hub.X >= 0.0 ? Front : Rear) += 1;
		HubZ += Hub.Z;
		Radius += DrawnRadius;
		Base += Hub.Z - DrawnRadius;
		++Count;
	}
	if (Count == 0 || Front == 0 || Rear == 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: no wheel bones front and rear in %s; the mud keeps its default wheel geometry"), *GetNameSafe(Asset));
		return;
	}
	WheelGeom = FVector4(FrontX / Front, RearX / Rear, HubZ / Count, Radius / Count);
	MudBaseZ = static_cast<float>(Base / Count);
	UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: MR2 wheel geometry - axles X %.1f / %.1f, hub Z %.1f, radius %.1f, wheel bottoms Z %.1f (car space)"),
		WheelGeom.X, WheelGeom.Y, WheelGeom.Z, WheelGeom.W, MudBaseZ);
}

void UGTBodyComponent::DressTyres(USkeletalMeshComponent* Mesh)
{
	UMaterialInterface* Base = Mesh ? LoadObject<UMaterialInterface>(nullptr, TyreMaterialPath, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
	// An isolated soil study can supply its matching mud shader while retaining
	// the body's authoritative per-wheel coating and wash parameters.
	if(Mesh && GetWorld())
		for(TActorIterator<AGTLandscapeSurface> It(GetWorld());It;++It)
			if(It->TyreCoatingMaterial) { Base=It->TyreCoatingMaterial;break; }
	if (!Base)
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: M_GT_Tyre missing (run Art/setup_m1_body.bat); the wheels keep their slot's material"));
		return;
	}
	if (bWorkshopReady)
	{
		const FString Path = TEXT("/Game/GrandTour/UI/Workshop/M_GT_WorkshopTyre_") + Base->GetName();
		if (auto* Variant = LoadObject<UMaterialInterface>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet)) Base = Variant;
		else bWorkshopReady = false;
	}
	TyreMaterial = UMaterialInstanceDynamic::Create(Base, this);
	TyreMaterial->SetVectorParameterValue(ParamWheelGeom, FLinearColor(WheelGeom.X, WheelGeom.Y, WheelGeom.Z, WheelGeom.W));
	TyreMaterial->SetVectorParameterValue(ParamTyreCoat, FLinearColor(0.f, 0.f, 0.f, 0.f));
	for (const FName Slot : KeepSkeletalSlots)
	{
		const int32 Index = Mesh->GetMaterialIndex(Slot);
		if (Index != INDEX_NONE)
		{
			Mesh->SetMaterial(Index, TyreMaterial);
			++TyreSlots;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: M_GT_Tyre on %d wheel slot(s)"), TyreSlots);
}

void UGTBodyComponent::PushMud(const UGTBodyStateComponent& State)
{
	const bool bCarMud = UGTBodyStateComponent::IsCarMudEnabled();
	const float Coats[10] = {
		State.GetDirt(EGTDamageRegion::Front), State.GetDirt(EGTDamageRegion::Rear), State.GetDirt(EGTDamageRegion::Roof), State.GetDirt(EGTDamageRegion::Glass),
		State.GetDirt(EGTDamageRegion::ArchFL), State.GetDirt(EGTDamageRegion::ArchFR), State.GetDirt(EGTDamageRegion::ArchRL), State.GetDirt(EGTDamageRegion::ArchRR),
		State.GetDirt(EGTDamageRegion::SideL), State.GetDirt(EGTDamageRegion::SideR) };
	TArray<float, TInlineAllocator<32>> Now;
	Now.Add(bCarMud ? 1.f : 0.f);
	Now.Add(State.CoatLineCm);
	Now.Add(State.WashCm);
	Now.Add(State.WashAmount);
	Now.Add(State.MudWet);
	Now.Append(Coats, UE_ARRAY_COUNT(Coats));
	for (int32 Wheel = 0; Wheel < 4; ++Wheel)
	{
		Now.Add(State.GetTyreCoat(Wheel));
	}
	Now.Add(State.Wetness);
	for (int32 Wheel = 0; Wheel < 4; ++Wheel)
	{
		Now.Add(State.GetFanCoat(Wheel));
		Now.Add(State.GetFanDir(Wheel));
	}
	// A push only when something moved enough to see (MudWet dries 0.011 a second).
	bool bMoved = PushedMud.Num() != Now.Num();
	for (int32 Index = 0; !bMoved && Index < Now.Num(); ++Index)
	{
		bMoved = FMath::Abs(PushedMud[Index] - Now[Index]) > (Index == 1 || Index == 2 ? 0.5f : 0.004f);
	}
	if (!bMoved)
	{
		return;
	}
	PushedMud = TArray<float>(Now.GetData(), Now.Num());
	const FLinearColor Ends(Coats[0], Coats[1], Coats[2], Coats[3]);
	const FLinearColor Arches(Coats[4], Coats[5], Coats[6], Coats[7]);
	const FLinearColor Sides(Coats[8], Coats[9], 0.f, 0.f);
	const FLinearColor Fans(State.GetFanCoat(0), State.GetFanCoat(1), State.GetFanCoat(2), State.GetFanCoat(3));
	const FLinearColor FanSides(State.GetFanDir(0), State.GetFanDir(1), State.GetFanDir(2), State.GetFanDir(3));
	for (UMaterialInstanceDynamic* Material : PanelMaterials)
	{
		if (!Material)
		{
			continue;
		}
		Material->SetScalarParameterValue(ParamCarMud, bCarMud ? 1.f : 0.f);
		Material->SetScalarParameterValue(ParamMudLineCm, State.CoatLineCm);
		Material->SetScalarParameterValue(ParamWashCm, State.WashCm);
		Material->SetScalarParameterValue(ParamWashAmount, State.WashAmount);
		Material->SetScalarParameterValue(ParamMudWet, State.MudWet);
		Material->SetVectorParameterValue(ParamCoatEnds, Ends);
		Material->SetVectorParameterValue(ParamCoatArches, Arches);
		Material->SetVectorParameterValue(ParamCoatSides, Sides);
		Material->SetVectorParameterValue(ParamFanCoat, Fans);
		Material->SetVectorParameterValue(ParamFanDir, FanSides);
	}
	if (TyreMaterial)
	{
		TyreMaterial->SetScalarParameterValue(ParamCarMud, bCarMud ? 1.f : 0.f);
		TyreMaterial->SetScalarParameterValue(ParamMudWet, State.MudWet);
		TyreMaterial->SetScalarParameterValue(ParamWetness, State.Wetness);
		TyreMaterial->SetVectorParameterValue(ParamTyreCoat, FLinearColor(State.GetTyreCoat(0), State.GetTyreCoat(1), State.GetTyreCoat(2), State.GetTyreCoat(3)));
	}
	if (WindscreenMaterial)
	{
		WindscreenMaterial->SetScalarParameterValue(ParamCarMud, bCarMud ? 1.f : 0.f);
		WindscreenMaterial->SetScalarParameterValue(ParamMudWet, State.MudWet);
	}
}

UMaterialInstanceDynamic* UGTBodyComponent::MakePanelMaterial(FName SlotName)
{
	if (!VehicleMaterial)
	{
		return nullptr;
	}
	const FString Slot = SlotName.ToString();
	const FLinearColor Colour = Slot.Contains(TEXT("Trim")) ? TrimColour : Slot.Contains(TEXT("Interior")) ? InteriorColour : BodyColour;
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(VehicleMaterial, this);
	Material->SetVectorParameterValue(ParamBaseColor, Colour);
	Material->SetTextureParameterValue(ParamImpactTex, ImpactTexture);
	Material->SetScalarParameterValue(ParamImpactCount, 0.f);
	Material->SetScalarParameterValue(ParamDirt, 0.f);
	Material->SetScalarParameterValue(ParamWetness, 0.f);
	Material->SetScalarParameterValue(ParamSnow, 0.f);
	// MR2: the car's own geometry for the mud (set once; the state's values come every tick they move).
	Material->SetScalarParameterValue(ParamMudBaseZ, MudBaseZ);
	Material->SetVectorParameterValue(ParamWheelGeom, FLinearColor(WheelGeom.X, WheelGeom.Y, WheelGeom.Z, WheelGeom.W));
	return Material;
}

void UGTBodyComponent::AttachPanels(USkeletalMeshComponent* Mesh)
{
	IAssetRegistry& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
	Registry.ScanPathsSynchronous({ PanelFolder }, true);
	TArray<FAssetData> Assets;
	Registry.GetAssetsByPath(FName(*PanelFolder), Assets, false);
	Assets.Sort([](const FAssetData& A, const FAssetData& B) { return A.AssetName.LexicalLess(B.AssetName); });
	// Look L1 follow-up 3: the owner's panel bakes, by asset name.
	TMap<FString, FAssetData> PaintAssets;
	{
		Registry.ScanPathsSynchronous({ PaintFolder }, true);
		TArray<FAssetData> Found;
		Registry.GetAssetsByPath(FName(*PaintFolder), Found, false);
		for (const FAssetData& Data : Found)
		{
			PaintAssets.Add(Data.AssetName.ToString(), Data);
		}
	}
	TArray<FString> Painted;

	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetClassPath != UStaticMesh::StaticClass()->GetClassPathName())
		{
			continue;
		}
		const FString AssetName = Asset.AssetName.ToString();
		if (!AssetName.StartsWith(PanelPrefix))
		{
			continue;
		}
		const FString Name = AssetName.RightChop(PanelPrefix.Len());
		if (SkipPanels.ContainsByPredicate([&Name](const FString& Skip) { return Name.StartsWith(Skip); }))
		{
			continue;
		}
		UStaticMesh* StaticMesh = Cast<UStaticMesh>(Asset.GetAsset());
		if (!StaticMesh)
		{
			continue;
		}
		UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(GetOwner(), *FString::Printf(TEXT("Panel_%s"), *Name), RF_Transient);
		Component->SetStaticMesh(StaticMesh);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);   // the chassis box collides for the whole car
		const bool bDoor = DoorPanels.Contains(Name);
		FDoor Door;
		USceneComponent* Hinge = nullptr;
		if (bDoor)
		{
			// A hinge at the door's front edge on its outer skin; the panel hangs off it, offset back to the car origin.
			const FBox Bounds = StaticMesh->GetBoundingBox();
			Door.ClosedBounds = Bounds;
			Door.bLeft = Bounds.GetCenter().Y < 0.f;
			Door.bFront = Name.Contains(TEXT("Front"));
			Door.HingeLocal = FVector(Bounds.Max.X, Door.bLeft ? Bounds.Min.Y : Bounds.Max.Y, Bounds.GetCenter().Z);
			Hinge = NewObject<USceneComponent>(GetOwner(), *FString::Printf(TEXT("Hinge_%s"), *Name), RF_Transient);
			Hinge->SetupAttachment(Mesh);
			Hinge->SetRelativeLocation(Door.HingeLocal);
			Hinge->RegisterComponent();
			Component->SetupAttachment(Hinge);
			Component->SetRelativeTransform(FTransform(-Door.HingeLocal));
			if (bDoorsTargetable)
			{
				ConfigureDoorCollision(Component);
			}
		}
		else
		{
			Component->SetupAttachment(Mesh);
			Component->SetRelativeTransform(FTransform::Identity);           // panels were exported about the car origin
		}
		const FName SlotName = StaticMesh->GetStaticMaterials().Num() > 0 ? StaticMesh->GetStaticMaterials()[0].MaterialSlotName : NAME_None;
		UMaterialInstanceDynamic* Material = MakePanelMaterial(SlotName);
		FString PaintGot;
		if (ApplyPanelPaint(Name, Material, PaintAssets, PaintGot))
		{
			Painted.Add(PaintGot);
		}
		if (Material)
		{
			for (int32 Index = 0; Index < StaticMesh->GetStaticMaterials().Num(); ++Index)
			{
				Component->SetMaterial(Index, Material);
			}
		}
		Component->RegisterComponent();

		FPanel Panel;
		Panel.Name = Name;
		Panel.Region = RegionForPanel(Name, StaticMesh->GetBoundingBox());
		Panel.Index = PanelComponents.Add(Component);
		PanelMaterials.Add(Material);
		const UBodySetup* BodySetup = StaticMesh->GetBodySetup();
		Panel.bHasCollision = BodySetup && BodySetup->AggGeom.GetElementCount() > 0;
		if (!Panel.bHasCollision)
		{
			++PanelsWithoutCollision;
		}
		if (bDoor)
		{
			Panel.DoorIndex = Doors.Num();
			Door.PanelSlot = Panels.Num();
			Doors.Add(Door);
			DoorHinges.Add(Hinge);
		}
		Panels.Add(Panel);
	}
	UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: attached %d panels (%d without collision)"), Panels.Num(), PanelsWithoutCollision);
	UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: %d doors hinged: %s"), Doors.Num(), *DescribeDoors());
	UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: %d panels painted from %s (UsePaint 1): %s"), Painted.Num(), *PaintFolder,
		Painted.Num() > 0 ? *FString::Join(Painted, TEXT(", ")) : TEXT("none, every panel on BodyColour"));
}

void UGTBodyComponent::HideSkeletalSections(USkeletalMeshComponent* Mesh)
{
	const TArray<FSkeletalMaterial>& Materials = Mesh->GetSkeletalMeshAsset() ? Mesh->GetSkeletalMeshAsset()->GetMaterials() : TArray<FSkeletalMaterial>();
	for (int32 Index = 0; Index < Materials.Num(); ++Index)
	{
		if (KeepSkeletalSlots.Contains(Materials[Index].MaterialSlotName))
		{
			continue;
		}
		Mesh->ShowMaterialSection(Index, 0, false, 0);
		if (!Mesh->IsMaterialSectionShown(Index, 0))
		{
			++HiddenSkeletalSlots;
		}
	}
}

void UGTBodyComponent::BuildWindscreen(USkeletalMeshComponent* Mesh)
{
	UStaticMesh* CubeMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (!CubeMesh)
	{
		return;
	}
	Windscreen = NewObject<UStaticMeshComponent>(GetOwner(), TEXT("Windscreen"), RF_Transient);
	Windscreen->SetStaticMesh(CubeMesh);
	Windscreen->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Windscreen->SetCastShadow(false);
	Windscreen->SetupAttachment(Mesh);
	Windscreen->SetRelativeLocationAndRotation(WindscreenCentre, FRotator(WindscreenPitch, 0.f, 0.f));
	Windscreen->SetRelativeScale3D(WindscreenSize / 100.f);
	if (GlassMaterial)
	{
		WindscreenMaterial = UMaterialInstanceDynamic::Create(GlassMaterial, this);
		WindscreenMaterial->SetScalarParameterValue(ParamCrack, 0.f);
		WindscreenMaterial->SetScalarParameterValue(ParamDirt, 0.f);
		WindscreenMaterial->SetScalarParameterValue(ParamGlassSizeX, WindscreenSize.X);
		WindscreenMaterial->SetScalarParameterValue(ParamGlassSizeY, WindscreenSize.Y);
		Windscreen->SetMaterial(0, WindscreenMaterial);
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: M_GT_Glass missing (run Art/setup_m1_body.bat); windscreen is opaque"));
	}
	Windscreen->RegisterComponent();
}

void UGTBodyComponent::UpdateImpactTexture(const UGTConditionComponent& Condition)
{
	if (!ImpactTexture || !ImpactTexture->GetPlatformData() || ImpactTexture->GetPlatformData()->Mips.Num() == 0)
	{
		return;
	}
	const int32 Count = FMath::Min(Condition.Impacts.Num(), ImpactTextureWidth);
	FTexture2DMipMap& Mip = ImpactTexture->GetPlatformData()->Mips[0];
	float* Data = static_cast<float*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
	FMemory::Memzero(Data, ImpactTextureWidth * 2 * 4 * sizeof(float));
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const FGTImpactRecord& Record = Condition.Impacts[Index];
		float* Position = Data + Index * 4;                              // row 0
		float* Direction = Data + (ImpactTextureWidth + Index) * 4;      // row 1
		Position[0] = Record.LocalPosition.X;
		Position[1] = Record.LocalPosition.Y;
		Position[2] = Record.LocalPosition.Z;
		Position[3] = Record.Radius;
		Direction[0] = Record.LocalDirection.X;
		Direction[1] = Record.LocalDirection.Y;
		Direction[2] = Record.LocalDirection.Z;
		Direction[3] = Record.Depth;
	}
	Mip.BulkData.Unlock();
	ImpactTexture->UpdateResource();
	ImpactTextureCount = Count;
	for (UMaterialInstanceDynamic* Material : PanelMaterials)
	{
		if (Material)
		{
			Material->SetTextureParameterValue(ParamImpactTex, ImpactTexture);
			Material->SetScalarParameterValue(ParamImpactCount, static_cast<float>(Count));
		}
	}
}

void UGTBodyComponent::Detach(FPanel& Panel, const FVector& CarVelocity, const FTransform& CarTransform)
{
	Panel.bDetached = true;
	++DetachedCount;
	UStaticMeshComponent* Component = PanelComponents.IsValidIndex(Panel.Index) ? PanelComponents[Panel.Index].Get() : nullptr;
	if (!Component)
	{
		return;
	}
	if (!Panel.bHasCollision)
	{
		// Nothing to simulate with: the panel is simply gone.
		UE_LOG(LogTemp, Warning, TEXT("UGTBodyComponent: %s has no collision; removed instead of dropped"), *Panel.Name);
		Component->DestroyComponent();
		return;
	}
	Component->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
	Component->SetCollisionProfileName(TEXT("PhysicsActor"));
	// It starts inside the chassis box; ignoring the car (and other panels) avoids the solver
	// blasting it out through the body. It still lands on the world.
	Component->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	Component->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
	Component->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Ignore);
	Component->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Component->SetSimulatePhysics(true);
	const FVector Outward = CarTransform.TransformVectorNoScale(OutwardDirection(Panel.Region));
	Component->SetPhysicsLinearVelocity(CarVelocity + Outward * DetachSpeed + FVector(0.f, 0.f, 100.f));
	Component->SetPhysicsAngularVelocityInDegrees(FVector(90.f, 180.f, 45.f));
	UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: %s detached (%s region dead)"), *Panel.Name, RegionName(Panel.Region));
}

int32 UGTBodyComponent::ReattachAll()
{
	USkeletalMeshComponent* Mesh = GetOwner() ? GetOwner()->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
	int32 Count = 0;
	for (FPanel& Panel : Panels)
	{
		if (!Panel.bDetached)
		{
			continue;
		}
		UStaticMeshComponent* Component = PanelComponents.IsValidIndex(Panel.Index) ? PanelComponents[Panel.Index].Get() : nullptr;
		if (!Component || !IsValid(Component) || !Mesh)
		{
			continue;   // removed outright (no collision): cannot come back
		}
		Component->SetSimulatePhysics(false);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		USceneComponent* Hinge = DoorHinges.IsValidIndex(Panel.DoorIndex) ? DoorHinges[Panel.DoorIndex].Get() : nullptr;
		if (Hinge && Doors.IsValidIndex(Panel.DoorIndex))
		{
			// Back on its hinge, shut.
			FDoor& Door = Doors[Panel.DoorIndex];
			Door.Phase = 0.f;
			Door.bTargetOpen = false;
			Door.PendingDelay = -1.f;
			Hinge->SetRelativeRotation(FRotator::ZeroRotator);
			Component->AttachToComponent(Hinge, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			Component->SetRelativeTransform(FTransform(-Door.HingeLocal));
			if (bDoorsTargetable)
			{
				ConfigureDoorCollision(Component);
			}
		}
		else
		{
			Component->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			Component->SetRelativeTransform(FTransform::Identity);
		}
		Panel.bDetached = false;
		--DetachedCount;
		++Count;
	}
	if (Count > 0)
	{
		UE_LOG(LogTemp, Display, TEXT("UGTBodyComponent: %d panels back on the car"), Count);
	}
	return Count;
}

void UGTBodyComponent::Update(float DeltaSeconds, const UGTConditionComponent& Condition, const UGTBodyStateComponent& State, const FVector& CarVelocity)
{
    for(int32 I=0;I<WorkshopEquipmentMaterials.Num();++I)
    {
        const int32 Part=WorkshopEquipmentMaterialParts[I];
        const EGTDamageRegion Region=Part==0 ? EGTDamageRegion::Roof : Part==1 ? EGTDamageRegion::Front : EGTDamageRegion::SideL;
        WorkshopEquipmentMaterials[I]->SetScalarParameterValue(TEXT("Coat"),UGTBodyStateComponent::IsCarMudEnabled()?State.GetDirt(Region):0.f);
        WorkshopEquipmentMaterials[I]->SetScalarParameterValue(ParamWetness,State.Wetness);
    }
	if (bWorkshopReady && TyreMaterial)
	{
		if (auto* Car = Cast<AGTCarPawn>(GetOwner()))
		{
			const FName Id=Car->GetParts()->GetInstalled(FGameplayTag::RequestGameplayTag(TEXT("Slot.Tyres")));
			const int32 Choice=Id==TEXT("Part.TyreKnobbly") ? 2 : Id==TEXT("Part.TyreAllTerrain") ? 1 : 0;
			if(Choice!=WorkshopTyres) SetWorkshopAppearance(WorkshopPaint,WorkshopRims,Choice);
		}
	}
	for(int32 I=0;I<WorkshopWheelMaterials.Num();++I)
	{
		WorkshopWheelMaterials[I]->SetScalarParameterValue(TEXT("Coat"),UGTBodyStateComponent::IsCarMudEnabled()?State.GetTyreCoat(WorkshopMaterialWheels[I]):0.f);
		WorkshopWheelMaterials[I]->SetScalarParameterValue(ParamWetness,State.Wetness);
	}
	UpdateDoors(DeltaSeconds);
	if (Condition.ImpactsVersion != LastImpactsVersion)
	{
		LastImpactsVersion = Condition.ImpactsVersion;
		UpdateImpactTexture(Condition);
	}
	const FTransform CarTransform = GetOwner() ? GetOwner()->GetActorTransform() : FTransform::Identity;
	for (FPanel& Panel : Panels)
	{
		if (!Panel.bDetached && Panel.Region != EGTDamageRegion::None && Condition.GetRegionHealth(Panel.Region) <= 0.f)
		{
			Detach(Panel, CarVelocity, CarTransform);
		}
		UMaterialInstanceDynamic* Material = PanelMaterials.IsValidIndex(Panel.Index) ? PanelMaterials[Panel.Index].Get() : nullptr;
		if (Material)
		{
			Material->SetScalarParameterValue(ParamDirt, State.GetDirt(Panel.Region));
			Material->SetScalarParameterValue(ParamWetness, State.Wetness);
			Material->SetScalarParameterValue(ParamSnow, State.Snow);
		}
	}
	WindscreenCrack = 1.f - Condition.GetRegionHealth(EGTDamageRegion::Glass);
	if (WindscreenMaterial)
	{
		WindscreenMaterial->SetScalarParameterValue(ParamCrack, WindscreenCrack);
		WindscreenMaterial->SetScalarParameterValue(ParamDirt, State.GetDirt(EGTDamageRegion::Glass));
	}
	PushMud(State);
}

int32 UGTBodyComponent::GetSimulatingCount() const
{
	int32 Result = 0;
	for (const FPanel& Panel : Panels)
	{
		const UStaticMeshComponent* Component = PanelComponents.IsValidIndex(Panel.Index) ? PanelComponents[Panel.Index].Get() : nullptr;
		if (Panel.bDetached && Component && IsValid(Component) && Component->IsSimulatingPhysics())
		{
			++Result;
		}
	}
	return Result;
}

FString UGTBodyComponent::Describe() const
{
	FString Result = FString::Printf(TEXT("panels=%d detached=%d simulating=%d noCollision=%d hiddenSlots=%d impactTex=%d crack=%.2f:"),
		Panels.Num(), DetachedCount, GetSimulatingCount(), PanelsWithoutCollision, HiddenSkeletalSlots, ImpactTextureCount, WindscreenCrack);
	for (const FPanel& Panel : Panels)
	{
		Result += FString::Printf(TEXT(" %s/%s%s"), *Panel.Name, RegionName(Panel.Region), Panel.bDetached ? TEXT("/off") : TEXT(""));
	}
	return Result;
}

// ---- doors ---------------------------------------------------------------------------------------------

void UGTBodyComponent::ConfigureDoorCollision(UStaticMeshComponent* Component) const
{
	Component->SetCollisionObjectType(ECC_WorldDynamic);
	Component->SetCollisionResponseToAllChannels(ECR_Ignore);
	Component->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
	Component->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

void UGTBodyComponent::UpdateDoors(float DeltaSeconds)
{
	for (int32 Index = 0; Index < Doors.Num(); ++Index)
	{
		FDoor& Door = Doors[Index];
		if (Door.PendingDelay >= 0.f)
		{
			Door.PendingDelay -= DeltaSeconds;
			if (Door.PendingDelay < 0.f)
			{
				Door.bTargetOpen = Door.bPendingOpen;
			}
		}
		const float Target = Door.bTargetOpen ? 1.f : 0.f;
		if (Door.Phase == Target)
		{
			continue;
		}
		const float Step = DeltaSeconds / FMath::Max(0.05f, DoorSwingSeconds);
		Door.Phase = Target > Door.Phase ? FMath::Min(Target, Door.Phase + Step) : FMath::Max(Target, Door.Phase - Step);
		if (USceneComponent* Hinge = DoorHinges.IsValidIndex(Index) ? DoorHinges[Index].Get() : nullptr)
		{
			// Positive yaw swings a trailing point toward -Y: left doors open with +yaw, right doors with -yaw.
			Hinge->SetRelativeRotation(FRotator(0.f, (Door.bLeft ? 1.f : -1.f) * GetDoorAngle(Index), 0.f));
		}
	}
}

int32 UGTBodyComponent::FindDoor(bool bLeft, bool bFront) const
{
	for (int32 Index = 0; Index < Doors.Num(); ++Index)
	{
		if (Doors[Index].bLeft == bLeft && Doors[Index].bFront == bFront)
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

int32 UGTBodyComponent::GetDriverDoor() const
{
	bool bLeft = true;
	if (const AGTCarPawn* Car = Cast<AGTCarPawn>(GetOwner()))
	{
		bLeft = Car->DriverEyeOffset.Y <= 0.f;   // left-hand drive: the driver sits at -Y
	}
	return FindDoor(bLeft, true);
}

int32 UGTBodyComponent::DoorForComponent(const UPrimitiveComponent* Component) const
{
	if (!Component)
	{
		return INDEX_NONE;
	}
	for (int32 Index = 0; Index < Doors.Num(); ++Index)
	{
		if (GetDoorPanel(Index) == Component && !IsDoorDetached(Index))
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

int32 UGTBodyComponent::DoorAtLocalPoint(const FVector& P) const
{
	// An open doorway runs up to the roof line, not just the top of the door skin: the window opening above the
	// skin belongs to Pillars and the chassis box behind it reaches 179 cm, so looking in at the wheel still means
	// the doorway. A shut door keeps its skin outline.
	const float DoorwayTopZ = 175.f;
	for (int32 Index = 0; Index < Doors.Num(); ++Index)
	{
		const FDoor& D = Doors[Index];
		const float InnerY = FMath::Min(FMath::Abs(D.ClosedBounds.Min.Y), FMath::Abs(D.ClosedBounds.Max.Y));
		const bool bSide = D.bLeft ? P.Y < 0.f : P.Y > 0.f;
		const float TopZ = IsDoorwayClear(Index) ? FMath::Max(D.ClosedBounds.Max.Z + 2.f, DoorwayTopZ) : D.ClosedBounds.Max.Z + 2.f;
		if (bSide && FMath::Abs(P.Y) >= InnerY - 45.f
			&& P.X >= D.ClosedBounds.Min.X - 2.f && P.X <= D.ClosedBounds.Max.X + 2.f
			&& P.Z >= D.ClosedBounds.Min.Z - 2.f && P.Z <= TopZ)
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

void UGTBodyComponent::SetDoorOpen(int32 Door, bool bOpen, float Delay)
{
	if (!Doors.IsValidIndex(Door))
	{
		return;
	}
	FDoor& D = Doors[Door];
	if (Delay > 0.f)
	{
		D.PendingDelay = Delay;
		D.bPendingOpen = bOpen;
	}
	else
	{
		D.PendingDelay = -1.f;
		D.bTargetOpen = bOpen;
	}
}

bool UGTBodyComponent::IsDoorOpen(int32 Door) const
{
	return Doors.IsValidIndex(Door) && Doors[Door].bTargetOpen;
}

float UGTBodyComponent::GetDoorAngle(int32 Door) const
{
	if (!Doors.IsValidIndex(Door))
	{
		return 0.f;
	}
	const float T = FMath::Clamp(Doors[Door].Phase, 0.f, 1.f);
	return DoorOpenAngle * T * T * (3.f - 2.f * T);
}

bool UGTBodyComponent::IsDoorDetached(int32 Door) const
{
	return Doors.IsValidIndex(Door) && Panels.IsValidIndex(Doors[Door].PanelSlot) && Panels[Doors[Door].PanelSlot].bDetached;
}

bool UGTBodyComponent::IsDoorFront(int32 Door) const
{
	return Doors.IsValidIndex(Door) && Doors[Door].bFront;
}

bool UGTBodyComponent::IsDoorLeft(int32 Door) const
{
	return Doors.IsValidIndex(Door) && Doors[Door].bLeft;
}

bool UGTBodyComponent::IsDoorwayClear(int32 Door) const
{
	return Doors.IsValidIndex(Door) && (IsDoorDetached(Door) || GetDoorAngle(Door) >= DoorwayClearAngle);
}

FString UGTBodyComponent::DoorName(int32 Door) const
{
	if (!Doors.IsValidIndex(Door))
	{
		return TEXT("door");
	}
	return FString::Printf(TEXT("%s-%s door"), Doors[Door].bFront ? TEXT("front") : TEXT("rear"), Doors[Door].bLeft ? TEXT("left") : TEXT("right"));
}

FString UGTBodyComponent::DescribeDoors() const
{
	FString Result;
	for (int32 Index = 0; Index < Doors.Num(); ++Index)
	{
		const FDoor& D = Doors[Index];
		Result += FString::Printf(TEXT("%s%s hinge=(%.1f, %.1f) angle=%.1f%s%s"), Result.IsEmpty() ? TEXT("") : TEXT(" | "), *DoorName(Index),
			D.HingeLocal.X, D.HingeLocal.Y, GetDoorAngle(Index), D.bTargetOpen ? TEXT(" open") : TEXT(""), IsDoorDetached(Index) ? TEXT(" detached") : TEXT(""));
	}
	return Result.IsEmpty() ? TEXT("no doors") : Result;
}

FBox UGTBodyComponent::GetDoorClosedBounds(int32 Door) const
{
	return Doors.IsValidIndex(Door) ? Doors[Door].ClosedBounds : FBox(ForceInit);
}

FVector UGTBodyComponent::GetDoorHingeLocal(int32 Door) const
{
	return Doors.IsValidIndex(Door) ? Doors[Door].HingeLocal : FVector::ZeroVector;
}

UStaticMeshComponent* UGTBodyComponent::GetDoorPanel(int32 Door) const
{
	if (!Doors.IsValidIndex(Door) || !Panels.IsValidIndex(Doors[Door].PanelSlot))
	{
		return nullptr;
	}
	const int32 ComponentIndex = Panels[Doors[Door].PanelSlot].Index;
	return PanelComponents.IsValidIndex(ComponentIndex) ? PanelComponents[ComponentIndex].Get() : nullptr;
}

USceneComponent* UGTBodyComponent::GetDoorHinge(int32 Door) const
{
	return DoorHinges.IsValidIndex(Door) ? DoorHinges[Door].Get() : nullptr;
}

FVector UGTBodyComponent::GetExitSpotBehindDoor(int32 Door, float CapsuleRadius) const
{
	if (!Doors.IsValidIndex(Door))
	{
		return FVector::ZeroVector;
	}
	const FDoor& D = Doors[Door];
	const float OuterY = FMath::Max(FMath::Abs(D.ClosedBounds.Min.Y), FMath::Abs(D.ClosedBounds.Max.Y));
	return FVector(D.ClosedBounds.Min.X - 25.f, (D.bLeft ? -1.f : 1.f) * (OuterY + CapsuleRadius + 50.f), 0.f);
}
