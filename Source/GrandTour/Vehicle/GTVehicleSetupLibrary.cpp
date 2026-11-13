#include "Vehicle/GTVehicleSetupLibrary.h"

#include "Terrain/GTSurfacePhysMaterial.h"

#include "AnimationRuntime.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "PhysicsEngine/BoxElem.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

#include "InputMappingContext.h"

#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "InputAction.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "LandscapeEdit.h"
#include "LandscapeInfo.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeProxy.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialInterface.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "MaterialEditingLibrary.h"
#include "Materials/MaterialExpression.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "Vehicle/GTCarPawn.h"
#include "Character/GTPlayerCharacter.h"
#include "Crafting/GTRecipeDefinition.h"
#include "Economy/GTUpgradeDefinition.h"
#include "Harvest/GTLootTable.h"
#include "Parts/GTItemDefinition.h"
#include "Race/GTTourDefinition.h"
#include "Run/GTLegDefinition.h"
#include "Terrain/GTTerrainSpecAsset.h"
#include "Tools/GTToolDefinition.h"
#include "Weather/GTWeatherStateDefinition.h"
#endif

#if WITH_EDITOR
namespace
{
	UObject* MakeAsset(const FString& Folder, const TCHAR* Name, UClass* Class)
	{
		const FString PackageName = Folder / Name;
		UPackage* Package = CreatePackage(*PackageName);
		Package->FullyLoad();
		UObject* Object = FindObject<UObject>(Package, Name);
		if (!Object)
		{
			Object = NewObject<UObject>(Package, Class, Name, RF_Public | RF_Standalone);
			FAssetRegistryModule::AssetCreated(Object);
		}
		return Object;
	}

	bool SaveAsset(UObject* Object)
	{
		UPackage* Package = Object->GetOutermost();
		Package->MarkPackageDirty();
		FSavePackageArgs Args;
		Args.TopLevelFlags = RF_Public | RF_Standalone;
		const FString Filename = FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension());
		return UPackage::SavePackage(Package, Object, *Filename, Args);
	}

	UInputAction* MakeActionAsset(const FString& Folder, const TCHAR* Name, EInputActionValueType Type, int32& Saved)
	{
		UInputAction* Action = Cast<UInputAction>(MakeAsset(Folder, Name, UInputAction::StaticClass()));
		if (Action)
		{
			Action->ValueType = Type;
			Saved += SaveAsset(Action) ? 1 : 0;
		}
		return Action;
	}
}
#endif

int32 UGTVehicleSetupLibrary::CreateDrivingInputAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	UInputAction* Throttle = MakeActionAsset(Folder, TEXT("IA_Throttle"), EInputActionValueType::Axis1D, Saved);
	UInputAction* Brake = MakeActionAsset(Folder, TEXT("IA_Brake"), EInputActionValueType::Axis1D, Saved);
	UInputAction* Steer = MakeActionAsset(Folder, TEXT("IA_Steer"), EInputActionValueType::Axis1D, Saved);
	UInputAction* Handbrake = MakeActionAsset(Folder, TEXT("IA_Handbrake"), EInputActionValueType::Boolean, Saved);
	UInputAction* Look = MakeActionAsset(Folder, TEXT("IA_Look"), EInputActionValueType::Axis2D, Saved);
	UInputAction* Exit = MakeActionAsset(Folder, TEXT("IA_Exit"), EInputActionValueType::Boolean, Saved);
	UInputAction* Reel = MakeActionAsset(Folder, TEXT("IA_Reel"), EInputActionValueType::Boolean, Saved);
	UInputAction* CameraToggle = MakeActionAsset(Folder, TEXT("IA_CameraToggle"), EInputActionValueType::Boolean, Saved);
	UInputAction* DiffLock = MakeActionAsset(Folder, TEXT("IA_DiffLock"), EInputActionValueType::Boolean, Saved);
	UInputAction* LowRange = MakeActionAsset(Folder, TEXT("IA_LowRange"), EInputActionValueType::Boolean, Saved);
	UInputAction* ReleaseWinch = MakeActionAsset(Folder, TEXT("IA_ReleaseWinch"), EInputActionValueType::Boolean, Saved);
	UInputMappingContext* Context = Cast<UInputMappingContext>(MakeAsset(Folder, TEXT("IMC_Driving"), UInputMappingContext::StaticClass()));
	if (!Throttle || !Brake || !Steer || !Handbrake || !Look || !Exit || !Reel || !CameraToggle || !DiffLock || !LowRange || !ReleaseWinch || !Context)
	{
		return Saved;
	}
	Context->UnmapAll();
	AGTCarPawn::BuildDrivingMappings(Context, Throttle, Brake, Steer, Handbrake, Look, Exit, Reel, CameraToggle, DiffLock, LowRange, ReleaseWinch);
	Saved += SaveAsset(Context) ? 1 : 0;
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateOnFootInputAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	UInputAction* Move = MakeActionAsset(Folder, TEXT("IA_Move"), EInputActionValueType::Axis2D, Saved);
	UInputAction* LookMouse = MakeActionAsset(Folder, TEXT("IA_LookMouse"), EInputActionValueType::Axis2D, Saved);
	UInputAction* LookStick = MakeActionAsset(Folder, TEXT("IA_LookStick"), EInputActionValueType::Axis2D, Saved);
	UInputAction* Sprint = MakeActionAsset(Folder, TEXT("IA_Sprint"), EInputActionValueType::Boolean, Saved);
	UInputAction* Interact = MakeActionAsset(Folder, TEXT("IA_Interact"), EInputActionValueType::Boolean, Saved);
	UInputAction* ToolNext = MakeActionAsset(Folder, TEXT("IA_ToolNext"), EInputActionValueType::Boolean, Saved);
	UInputAction* ToolPrev = MakeActionAsset(Folder, TEXT("IA_ToolPrev"), EInputActionValueType::Boolean, Saved);
	UInputAction* Inventory = MakeActionAsset(Folder, TEXT("IA_Inventory"), EInputActionValueType::Boolean, Saved);
	UInputAction* DropHook = MakeActionAsset(Folder, TEXT("IA_DropHook"), EInputActionValueType::Boolean, Saved);
	UInputAction* ToggleHeadBob = MakeActionAsset(Folder, TEXT("IA_ToggleHeadBob"), EInputActionValueType::Boolean, Saved);
	UInputAction* Transfer = MakeActionAsset(Folder, TEXT("IA_Transfer"), EInputActionValueType::Boolean, Saved);
	UInputAction* Jump = MakeActionAsset(Folder, TEXT("IA_Jump"), EInputActionValueType::Boolean, Saved);
	UInputMappingContext* Context = Cast<UInputMappingContext>(MakeAsset(Folder, TEXT("IMC_OnFoot"), UInputMappingContext::StaticClass()));
	if (!Move || !LookMouse || !LookStick || !Sprint || !Interact || !ToolNext || !ToolPrev || !Inventory || !DropHook || !ToggleHeadBob || !Transfer || !Jump || !Context)
	{
		return Saved;
	}
	Context->UnmapAll();
	AGTPlayerCharacter::BuildOnFootMappings(Context, Move, LookMouse, LookStick, Sprint, Interact, ToolNext, ToolPrev, Inventory, DropHook, ToggleHeadBob, Transfer, Jump);
	Saved += SaveAsset(Context) ? 1 : 0;
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateToolAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (const UGTToolDefinition::FDefault& Row : UGTToolDefinition::DefaultTools())
	{
		UGTToolDefinition* Tool = Cast<UGTToolDefinition>(MakeAsset(Folder, Row.AssetName, UGTToolDefinition::StaticClass()));
		if (Tool)
		{
			Tool->ApplyDefault(Row);
			Saved += SaveAsset(Tool) ? 1 : 0;
		}
	}
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::GetMappingCount(const UInputMappingContext* Context)
{
	return Context ? Context->GetMappings().Num() : 0;
}

bool UGTVehicleSetupLibrary::ConnectMaterialCustomData(UMaterialExpression* Expression, const FString& OutputName, int32 Index)
{
#if WITH_EDITOR
	if (!Expression)
	{
		return false;
	}
	return UMaterialEditingLibrary::ConnectMaterialProperty(Expression, OutputName, Index == 0 ? MP_CustomData0 : MP_CustomData1);
#else
	return false;
#endif
}

bool UGTVehicleSetupLibrary::ConnectMaterialPixelDepthOffset(UMaterialExpression* Expression, const FString& OutputName)
{
#if WITH_EDITOR
	if (!Expression)
	{
		return false;
	}
	return UMaterialEditingLibrary::ConnectMaterialProperty(Expression, OutputName, MP_PixelDepthOffset);
#else
	return false;
#endif
}

int32 UGTVehicleSetupLibrary::RemoveBodiesByBonePrefix(UPhysicsAsset* PhysicsAsset, const FString& BonePrefix)
{
	if (!PhysicsAsset)
	{
		return 0;
	}
	PhysicsAsset->Modify();

	TSet<FName> RemovedBones;
	for (int32 Index = PhysicsAsset->SkeletalBodySetups.Num() - 1; Index >= 0; --Index)
	{
		const USkeletalBodySetup* Body = PhysicsAsset->SkeletalBodySetups[Index];
		if (Body && Body->BoneName.ToString().StartsWith(BonePrefix))
		{
			RemovedBones.Add(Body->BoneName);
			PhysicsAsset->SkeletalBodySetups.RemoveAt(Index);
		}
	}
	if (RemovedBones.Num() == 0)
	{
		return 0;
	}

	for (int32 Index = PhysicsAsset->ConstraintSetup.Num() - 1; Index >= 0; --Index)
	{
		const UPhysicsConstraintTemplate* Constraint = PhysicsAsset->ConstraintSetup[Index];
		if (!Constraint
			|| RemovedBones.Contains(Constraint->DefaultInstance.ConstraintBone1)
			|| RemovedBones.Contains(Constraint->DefaultInstance.ConstraintBone2))
		{
			PhysicsAsset->ConstraintSetup.RemoveAt(Index);
		}
	}

	PhysicsAsset->UpdateBodySetupIndexMap();
	PhysicsAsset->UpdateBoundsBodiesArray();
	PhysicsAsset->MarkPackageDirty();
	return RemovedBones.Num();
}

bool UGTVehicleSetupLibrary::SetBoxBody(UPhysicsAsset* PhysicsAsset, const USkeletalMesh* SkeletalMesh, FName BoneName,
                                        FVector CenterCS, FVector SizeCS)
{
	if (!PhysicsAsset || !SkeletalMesh)
	{
		return false;
	}
	const int32 BodyIndex = PhysicsAsset->FindBodyIndex(BoneName);
	const FReferenceSkeleton& RefSkeleton = SkeletalMesh->GetRefSkeleton();
	const int32 BoneIndex = RefSkeleton.FindBoneIndex(BoneName);
	if (BodyIndex == INDEX_NONE || BoneIndex == INDEX_NONE)
	{
		return false;
	}
	USkeletalBodySetup* Body = PhysicsAsset->SkeletalBodySetups[BodyIndex];
	if (!Body)
	{
		return false;
	}

	const FTransform BoneCS = FAnimationRuntime::GetComponentSpaceTransform(RefSkeleton, RefSkeleton.GetRefBonePose(), BoneIndex);
	FKBoxElem Box(SizeCS.X, SizeCS.Y, SizeCS.Z);
	Box.Center = BoneCS.InverseTransformPosition(CenterCS);
	Box.Rotation = BoneCS.GetRotation().Inverse().Rotator();

	PhysicsAsset->Modify();
	Body->Modify();
	Body->AggGeom.EmptyElements();
	Body->AggGeom.BoxElems.Add(Box);
	Body->InvalidatePhysicsData();
	Body->CreatePhysicsMeshes();
	PhysicsAsset->UpdateBoundsBodiesArray();
	PhysicsAsset->MarkPackageDirty();
	return true;
}

bool UGTVehicleSetupLibrary::SetCompoundBoxBody(UPhysicsAsset* PhysicsAsset, const USkeletalMesh* SkeletalMesh,
                                               FName BoneName, const TArray<FVector>& CentersCS, const TArray<FVector>& SizesCS)
{
	if (!PhysicsAsset || !SkeletalMesh || CentersCS.IsEmpty() || CentersCS.Num() != SizesCS.Num())
	{
		return false;
	}
	for (int32 Index = 0; Index < CentersCS.Num(); ++Index)
	{
		if (CentersCS[Index].ContainsNaN() || SizesCS[Index].ContainsNaN() || SizesCS[Index].GetMin() <= 0.f)
		{
			return false;
		}
	}
	const int32 BodyIndex = PhysicsAsset->FindBodyIndex(BoneName);
	const FReferenceSkeleton& RefSkeleton = SkeletalMesh->GetRefSkeleton();
	const int32 BoneIndex = RefSkeleton.FindBoneIndex(BoneName);
	if (BodyIndex == INDEX_NONE || BoneIndex == INDEX_NONE || !PhysicsAsset->SkeletalBodySetups[BodyIndex])
	{
		return false;
	}
	USkeletalBodySetup* Body = PhysicsAsset->SkeletalBodySetups[BodyIndex];
	const FTransform BoneCS = FAnimationRuntime::GetComponentSpaceTransform(RefSkeleton, RefSkeleton.GetRefBonePose(), BoneIndex);
	PhysicsAsset->Modify();
	Body->Modify();
	Body->AggGeom.EmptyElements();
	for (int32 Index = 0; Index < CentersCS.Num(); ++Index)
	{
		const FVector& Size = SizesCS[Index];
		FKBoxElem Box(Size.X, Size.Y, Size.Z);
		Box.Center = BoneCS.InverseTransformPosition(CentersCS[Index]);
		Box.Rotation = BoneCS.GetRotation().Inverse().Rotator();
		Body->AggGeom.BoxElems.Add(Box);
	}
	Body->InvalidatePhysicsData();
	Body->CreatePhysicsMeshes();
	PhysicsAsset->UpdateBoundsBodiesArray();
	PhysicsAsset->MarkPackageDirty();
	return true;
}

namespace
{
	UWorld* WorldFrom(UObject* WorldContextObject)
	{
		return GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::LogAndReturnNull) : nullptr;
	}

	void LabelActor(AActor* Actor, const FString& Label)
	{
#if WITH_EDITOR
		if (Actor && !Label.IsEmpty())
		{
			Actor->SetActorLabel(Label);
		}
#endif
	}
}

AActor* UGTVehicleSetupLibrary::SpawnStaticMeshActor(UObject* WorldContextObject, UStaticMesh* Mesh, FTransform Transform,
                                                     const FString& Label)
{
	UWorld* World = WorldFrom(WorldContextObject);
	if (!World || !Mesh)
	{
		return nullptr;
	}
	AStaticMeshActor* Actor = World->SpawnActorDeferred<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Transform);
	if (!Actor)
	{
		return nullptr;
	}
	Actor->GetStaticMeshComponent()->SetStaticMesh(Mesh);
	Actor->FinishSpawning(Transform);
	LabelActor(Actor, Label);
	return Actor;
}

AActor* UGTVehicleSetupLibrary::SpawnActorOfClass(UObject* WorldContextObject, TSubclassOf<AActor> ActorClass, FTransform Transform,
                                                  const FString& Label)
{
	UWorld* World = WorldFrom(WorldContextObject);
	if (!World || !ActorClass)
	{
		return nullptr;
	}
	AActor* Actor = World->SpawnActor<AActor>(ActorClass, Transform);
	LabelActor(Actor, Label);
	return Actor;
}

int32 UGTVehicleSetupLibrary::EnableHitEvents(UPhysicsAsset* PhysicsAsset)
{
	if (!PhysicsAsset)
	{
		return 0;
	}
	PhysicsAsset->Modify();
	int32 Count = 0;
	for (USkeletalBodySetup* Body : PhysicsAsset->SkeletalBodySetups)
	{
		if (Body)
		{
			Body->Modify();
			Body->DefaultInstance.SetInstanceNotifyRBCollision(true);
			++Count;
		}
	}
	PhysicsAsset->MarkPackageDirty();
	return Count;
}

bool UGTVehicleSetupLibrary::SetSurfaceTag(UGTSurfacePhysMaterial* Material, FName TagName)
{
	if (!Material)
	{
		return false;
	}
	const FGameplayTag Tag = FGameplayTag::RequestGameplayTag(TagName, /*ErrorIfNotFound*/ false);
	if (!Tag.IsValid())
	{
		return false;
	}
	Material->Modify();
	Material->SurfaceTag = Tag;
	Material->MarkPackageDirty();
	return true;
}

int32 UGTVehicleSetupLibrary::DestroyActorsWithLabelPrefix(UObject* WorldContextObject, const FString& Prefix)
{
	UWorld* World = WorldFrom(WorldContextObject);
	if (!World || Prefix.IsEmpty())
	{
		return 0;
	}
	TArray<AActor*> Doomed;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
#if WITH_EDITOR
		if (It->GetActorLabel().StartsWith(Prefix))
		{
			Doomed.Add(*It);
		}
#endif
	}
	for (AActor* Actor : Doomed)
	{
		World->DestroyActor(Actor);
	}
	return Doomed.Num();
}

TArray<FString> UGTVehicleSetupLibrary::DescribeBodies(const UPhysicsAsset* PhysicsAsset)
{
	TArray<FString> Lines;
	if (!PhysicsAsset)
	{
		return Lines;
	}
	for (const USkeletalBodySetup* Body : PhysicsAsset->SkeletalBodySetups)
	{
		if (!Body)
		{
			continue;
		}
		Lines.Add(FString::Printf(TEXT("%s physicsType=%d boxes=%d spheres=%d capsules=%d convex=%d"),
			*Body->BoneName.ToString(), static_cast<int32>(Body->PhysicsType),
			Body->AggGeom.BoxElems.Num(), Body->AggGeom.SphereElems.Num(),
			Body->AggGeom.SphylElems.Num(), Body->AggGeom.ConvexElems.Num()));
	}
	Lines.Add(FString::Printf(TEXT("constraints=%d"), PhysicsAsset->ConstraintSetup.Num()));
	return Lines;
}

int32 UGTVehicleSetupLibrary::CreateWeatherStateAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (const UGTWeatherStateDefinition::FDefault& Row : UGTWeatherStateDefinition::DefaultStates())
	{
		UGTWeatherStateDefinition* State = Cast<UGTWeatherStateDefinition>(MakeAsset(Folder, Row.AssetName, UGTWeatherStateDefinition::StaticClass()));
		if (State)
		{
			State->ApplyDefault(Row);
			Saved += SaveAsset(State) ? 1 : 0;
		}
	}
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateLootTableAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (const UGTLootTable::FDefault& Row : UGTLootTable::DefaultTables())
	{
		UGTLootTable* Table = Cast<UGTLootTable>(MakeAsset(Folder, Row.AssetName, UGTLootTable::StaticClass()));
		if (Table)
		{
			Table->ApplyDefault(Row);
			Saved += SaveAsset(Table) ? 1 : 0;
		}
	}
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateLegAssets(const FString& Folder, const FString& WeatherFolder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (int32 Index = 0; Index < UGTLegDefinition::DefaultLegCount(); ++Index)
	{
		UGTLegDefinition* Leg = Cast<UGTLegDefinition>(MakeAsset(Folder, *UGTLegDefinition::DefaultAssetName(Index), UGTLegDefinition::StaticClass()));
		if (!Leg)
		{
			continue;
		}
		Leg->ApplyDefault(Index);
		const FString Weather = Leg->StartWeatherName.ToString();
		Leg->StartWeather = LoadObject<UGTWeatherStateDefinition>(nullptr, *FString::Printf(TEXT("%s/DA_Weather_%s.DA_Weather_%s"), *WeatherFolder, *Weather, *Weather));
		Saved += SaveAsset(Leg) ? 1 : 0;
	}
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateTourAssets(const FString& Folder, const FString& LegFolder)
{
#if WITH_EDITOR
	UGTTourDefinition* Tour = Cast<UGTTourDefinition>(MakeAsset(Folder, TEXT("DA_Tour_01"), UGTTourDefinition::StaticClass()));
	if (!Tour)
	{
		return 0;
	}
	Tour->ApplyDefaultTour01(LegFolder);
	return SaveAsset(Tour) ? 1 : 0;
#else
	return 0;
#endif
}

// ---- terrain (M6) ------------------------------------------------------------------------------------

FGTTerrainSpec UGTVehicleSetupLibrary::MakeHideTerrainSpec()
{
	return GTTerrain::HideSpec();
}

int32 UGTVehicleSetupLibrary::CreateTerrainSpecAssets(const FString& Folder, bool bOverwrite)
{
#if WITH_EDITOR
	const FString Name = TEXT("DA_Terrain_Hide");
	const FString Path = FString::Printf(TEXT("%s/%s.%s"), *Folder, *Name, *Name);
	if (!bOverwrite && LoadObject<UGTTerrainSpecAsset>(nullptr, *Path))
	{
		UE_LOG(LogTemp, Display, TEXT("CreateTerrainSpecAssets: %s exists, kept (the user's edits stand)"), *Path);
		return 1;
	}
	UGTTerrainSpecAsset* Asset = Cast<UGTTerrainSpecAsset>(MakeAsset(Folder, *Name, UGTTerrainSpecAsset::StaticClass()));
	if (!Asset)
	{
		return 0;
	}
	Asset->DisplayName = TEXT("The Hide");
	Asset->Spec = GTTerrain::HideSpec();
	return SaveAsset(Asset) ? 1 : 0;
#else
	return 0;
#endif
}

FGTTerrainSpec UGTVehicleSetupLibrary::MakeProvingTerrainSpec()
{
	return GTTerrain::ProvingSpec();
}

int32 UGTVehicleSetupLibrary::CreateProvingTerrainSpecAsset(const FString& Folder, bool bOverwrite)
{
#if WITH_EDITOR
	const FString Name = TEXT("DA_Terrain_Proving");
	const FString Path = FString::Printf(TEXT("%s/%s.%s"), *Folder, *Name, *Name);
	if (!bOverwrite && LoadObject<UGTTerrainSpecAsset>(nullptr, *Path))
	{
		UE_LOG(LogTemp, Display, TEXT("CreateProvingTerrainSpecAsset: %s exists, kept (the user's edits stand)"), *Path);
		return 1;
	}
	UGTTerrainSpecAsset* Asset = Cast<UGTTerrainSpecAsset>(MakeAsset(Folder, *Name, UGTTerrainSpecAsset::StaticClass()));
	if (!Asset)
	{
		return 0;
	}
	Asset->DisplayName = TEXT("The Proving Ground");
	Asset->Spec = GTTerrain::ProvingSpec();
	return SaveAsset(Asset) ? 1 : 0;
#else
	return 0;
#endif
}

float UGTVehicleSetupLibrary::SampleTerrainHeightCm(const FGTTerrainSpec& Spec, float XCm, float YCm)
{
	return GTTerrain::SampleHeightCm(Spec, XCm, YCm);
}

float UGTVehicleSetupLibrary::TerrainRouteDistanceM(const FGTTerrainSpec& Spec, float XCm, float YCm, float& OutArcM)
{
	const FGTRouteHit Hit = GTTerrain::RouteAtCm(Spec, XCm, YCm);
	OutArcM = Hit.ArcM;
	return Hit.DistanceM;
}

FVector UGTVehicleSetupLibrary::TerrainRoutePointCm(const FGTTerrainSpec& Spec, float ArcM, float& OutYaw)
{
	const FVector2D Point = GTTerrain::PointOnPolyline(Spec.RouteM, ArcM, OutYaw);
	const float XCm = Point.X * 100.f;
	const float YCm = Point.Y * 100.f;
	return FVector(XCm, YCm, GTTerrain::SampleHeightCm(Spec, XCm, YCm));
}

int32 UGTVehicleSetupLibrary::TerrainLayerAt(const FGTTerrainSpec& Spec, float XCm, float YCm)
{
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	return GTTerrain::LayerAt(Spec, Profiles, XCm / 100.f, YCm / 100.f);
}

float UGTVehicleSetupLibrary::TerrainSlopeDegrees(const FGTTerrainSpec& Spec, float XCm, float YCm)
{
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	return GTTerrain::SlopeDegrees(Spec, Profiles, XCm / 100.f, YCm / 100.f);
}

float UGTVehicleSetupLibrary::TerrainRouteLengthM(const FGTTerrainSpec& Spec)
{
	return GTTerrain::PolylineLengthM(Spec.RouteM);
}

EGTRouteSectionKind UGTVehicleSetupLibrary::TerrainSectionKindAt(const FGTTerrainSpec& Spec, float ArcM)
{
	return GTTerrain::SectionKindAt(Spec, ArcM);
}

float UGTVehicleSetupLibrary::TerrainCamberDegreesAt(const FGTTerrainSpec& Spec, float ArcM)
{
	return GTTerrain::CamberDegreesAt(Spec, ArcM);
}

float UGTVehicleSetupLibrary::TerrainFordWaterLevelCm(const FGTTerrainSpec& Spec, int32 SectionIndex)
{
	if (!Spec.Sections.IsValidIndex(SectionIndex) || Spec.Sections[SectionIndex].Kind != EGTRouteSectionKind::Ford)
	{
		return 0.f;
	}
	const FGTTerrainProfiles Profiles = GTTerrain::BuildProfiles(Spec);
	return GTTerrain::FordWaterLevelM(Spec, Profiles, Spec.Sections[SectionIndex]) * 100.f;
}

FVector UGTVehicleSetupLibrary::TerrainAltRoutePointCm(const FGTTerrainSpec& Spec, int32 AltIndex, float ArcM, float& OutYaw)
{
	OutYaw = 0.f;
	if (!Spec.AltRoutes.IsValidIndex(AltIndex))
	{
		return FVector::ZeroVector;
	}
	const FVector2D Point = GTTerrain::PointOnPolyline(Spec.AltRoutes[AltIndex].PointsM, ArcM, OutYaw);
	const float XCm = Point.X * 100.f;
	const float YCm = Point.Y * 100.f;
	return FVector(XCm, YCm, GTTerrain::SampleHeightCm(Spec, XCm, YCm));
}

float UGTVehicleSetupLibrary::TerrainAltRouteLengthM(const FGTTerrainSpec& Spec, int32 AltIndex)
{
	return Spec.AltRoutes.IsValidIndex(AltIndex) ? GTTerrain::PolylineLengthM(Spec.AltRoutes[AltIndex].PointsM) : 0.f;
}

AActor* UGTVehicleSetupLibrary::BuildLegLandscape(UWorld* World, const FGTTerrainSpec& Spec, UMaterialInterface* Material, const FString& LayerInfoFolder, const FString& SurfaceFolder, const FString& Label)
{
#if WITH_EDITOR
	if (!World)
	{
		return nullptr;
	}
	// One layer info asset per surface, pointing at the surface's physical material (what the wheels read). Leg dressing
	// LD1: then one per biome layer (GTTerrain::BiomeLayers), LI_<Layer> in the same folder with LayerName exactly the
	// rule's layer (OW_Meadow, Thicket, ...) and the off-road layer's physical material, so biome ground drives as the
	// Scrub it splits always has. A spec without biomes makes the same six as before.
	TArray<FName> LayerNames;
	GTTerrain::WeightLayerNames(Spec, LayerNames);
	const int32 OffRoadLayer = FMath::Clamp(Spec.OffRoadLayer, 0, GTTerrain::LayerCount - 1);
	TArray<ULandscapeLayerInfoObject*> LayerInfos;
	for (int32 Layer = 0; Layer < LayerNames.Num(); ++Layer)
	{
		const FString Name = FString::Printf(TEXT("LI_%s"), *LayerNames[Layer].ToString());
		const TCHAR* Phys = GTTerrain::PhysName(Layer < GTTerrain::LayerCount ? Layer : OffRoadLayer);
		ULandscapeLayerInfoObject* Info = Cast<ULandscapeLayerInfoObject>(MakeAsset(LayerInfoFolder, *Name, ULandscapeLayerInfoObject::StaticClass()));
		if (!Info)
		{
			UE_LOG(LogTemp, Error, TEXT("BuildLegLandscape: could not make %s"), *Name);
			return nullptr;
		}
		Info->LayerName = LayerNames[Layer];
		Info->PhysMaterial = LoadObject<UPhysicalMaterial>(nullptr, *FString::Printf(TEXT("%s/PM_%s.PM_%s"), *SurfaceFolder, Phys, Phys));
		if (!Info->PhysMaterial)
		{
			UE_LOG(LogTemp, Warning, TEXT("BuildLegLandscape: no PM_%s under %s (run setup_m1_track.bat); the layer will have no surface"), Phys, *SurfaceFolder);
		}
		SaveAsset(Info);
		LayerInfos.Add(Info);
	}

	TArray<uint16> Heights;
	TArray<TArray<uint8>> Weights;
	GTTerrain::Generate(Spec, Heights, Weights);
	const int32 Verts = GTTerrain::VertsPerSide(Spec);
	if (Weights.Num() != LayerInfos.Num())
	{
		UE_LOG(LogTemp, Error, TEXT("BuildLegLandscape: %d weight layers generated for %d layer infos"), Weights.Num(), LayerInfos.Num());
		return nullptr;
	}

	TArray<FLandscapeImportLayerInfo> ImportLayers;
	for (int32 Layer = 0; Layer < LayerInfos.Num(); ++Layer)
	{
		FLandscapeImportLayerInfo Import(LayerInfos[Layer]->LayerName);
		Import.LayerInfo = LayerInfos[Layer];
		Import.LayerData = Weights[Layer];
		ImportLayers.Add(MoveTemp(Import));
	}
	TMap<FGuid, TArray<uint16>> HeightDataPerLayers;
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayerDataPerLayers;
	HeightDataPerLayers.Add(FGuid(), Heights);
	MaterialLayerDataPerLayers.Add(FGuid(), MoveTemp(ImportLayers));

	// The same sequence as the editor's New Landscape button (LandscapeEditorDetailCustomization_NewLandscape.cpp).
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ALandscape* Landscape = World->SpawnActor<ALandscape>(ALandscape::StaticClass(), FVector(Spec.OriginXCm, Spec.OriginYCm, 0.f), FRotator::ZeroRotator, Params);
	if (!Landscape)
	{
		return nullptr;
	}
	Landscape->LandscapeMaterial = Material;
	Landscape->bUseDynamicMaterialInstance = true;   // the components wear dynamic instances at runtime. Section 30 handed them the mud patches' field textures for the holes under the mud; since stage D the hole is the patch's box alone (MPC_TrackPaint), so nothing is bound, but the flag is one line and stage E may want a parameter per patch back
	Landscape->SetActorRelativeScale3D(FVector(Spec.QuadSizeCm, Spec.QuadSizeCm, Spec.ZScale));
	Landscape->StaticLightingLOD = FMath::DivideAndRoundUp(FMath::CeilLogTwo((Verts * Verts) / (2048 * 2048) + 1), (uint32)2);
	Landscape->Import(FGuid::NewGuid(), 0, 0, Verts - 1, Verts - 1, Spec.SubsectionsPerComponent, Spec.QuadsPerSubsection, HeightDataPerLayers, TEXT(""), MaterialLayerDataPerLayers,
		ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
	ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
	if (!LandscapeInfo)
	{
		UE_LOG(LogTemp, Error, TEXT("BuildLegLandscape: no landscape info after the import"));
		return Landscape;
	}
	Landscape->SetActorLabel(Label.IsEmpty() ? TEXT("Landscape") : Label);
	LandscapeInfo->UpdateLayerInfoMap(Landscape);
	for (ULandscapeLayerInfoObject* Info : LayerInfos)
	{
		Landscape->AddTargetLayer(Info->GetLayerName(), FLandscapeTargetLayerSettings(Info));
		const int32 LayerInfoIndex = LandscapeInfo->GetLayerInfoIndex(Info->GetLayerName());
		if (LayerInfoIndex != INDEX_NONE)
		{
			LandscapeInfo->Layers[LayerInfoIndex].LayerInfoObj = Info;
		}
	}
	// Import put the weights into the default edit layer and asked for a layers merge to produce the final weightmaps;
	// that merge runs on the GPU and never happens under -NullRHI, so the components come out with no final weight
	// allocations at all (heights survive: Import wrote those directly). Write the final weightmaps here on the CPU
	// through the edit data interface with no edit layer set (an invalid guid means the final data), one layer at a
	// time without re-normalising, since the generator already made every vertex's four weights sum to 255. When the
	// level is opened in the editor the merge regenerates the same final data from the default layer.
	{
		FLandscapeEditDataInterface FinalEdit(LandscapeInfo, FGuid(), /*bInUploadTextureChangesToGPU*/ false);
		for (int32 Layer = 0; Layer < LayerInfos.Num(); ++Layer)
		{
			FinalEdit.SetAlphaData(LayerInfos[Layer], 0, 0, Verts - 1, Verts - 1, Weights[Layer].GetData(), /*Stride*/ 0, ELandscapeLayerPaintingRestriction::None, /*bWeightAdjust*/ false, /*bTotalWeightAdjust*/ false);
		}
		FinalEdit.Flush();
	}
	// The edit interface only patches texture regions; the weightmap textures it allocated still need the import's
	// PostEditChange to build their platform data and hash their source, or the game loads them with no mips at all.
	{
		TSet<UTexture2D*> WeightmapTextures;
		for (ULandscapeComponent* Component : Landscape->LandscapeComponents)
		{
			for (UTexture2D* Texture : Component->GetWeightmapTextures())
			{
				if (Texture)
				{
					WeightmapTextures.Add(Texture);
				}
			}
		}
		for (UTexture2D* Texture : WeightmapTextures)
		{
			Texture->PostEditChange();
		}
		UE_LOG(LogTemp, Display, TEXT("BuildLegLandscape: %d weightmap textures finalised"), WeightmapTextures.Num());
	}
	// A headless commandlet never ticks, so the per-component material instances (the ones that carry the weight
	// layers into the layer blend) must be built here or the saved landscape draws the base material's preview weights.
	Landscape->UpdateAllComponentMaterialInstances(/*bInInvalidateCombinationMaterials*/ true);
	int32 Instances = 0;
	for (const ULandscapeComponent* Component : Landscape->LandscapeComponents)
	{
		Instances += Component && Component->MaterialInstances.Num() > 0 && Component->MaterialInstances[0] ? 1 : 0;
	}
	UE_LOG(LogTemp, Display, TEXT("BuildLegLandscape: material instances on %d/%d components"), Instances, Landscape->LandscapeComponents.Num());
	// What one component carries, so a black landscape can be traced: the material's layer names, the allocations, the
	// weightmap textures and a few of their source bytes, and the instance's static terrain layer parameters.
	if (ULandscapeComponent* Component = Landscape->LandscapeComponents.Num() > 0 ? Landscape->LandscapeComponents[Landscape->LandscapeComponents.Num() / 2] : nullptr)
	{
		FString Names;
		for (const FName& Name : ALandscapeProxy::GetLayersFromMaterial(Material))
		{
			Names += FString::Printf(TEXT(" %s"), *Name.ToString());
		}
		FString Allocations;
		for (const FWeightmapLayerAllocationInfo& Allocation : Component->GetWeightmapLayerAllocations())
		{
			Allocations += FString::Printf(TEXT(" %s@tex%d.ch%d"), Allocation.LayerInfo ? *Allocation.LayerInfo->LayerName.ToString() : TEXT("null"), Allocation.WeightmapTextureIndex, Allocation.WeightmapTextureChannel);
		}
		FString Textures;
		for (UTexture2D* Texture : Component->GetWeightmapTextures())
		{
			if (!Texture)
			{
				Textures += TEXT(" null");
				continue;
			}
			const int32 SizeX = Texture->Source.GetSizeX();
			const FColor* Data = reinterpret_cast<const FColor*>(Texture->Source.LockMipReadOnly(0));
			const FColor Centre = Data ? Data[(SizeX / 2) * SizeX + SizeX / 2] : FColor::Black;
			Texture->Source.UnlockMip(0);
			Textures += FString::Printf(TEXT(" %s(%dx%d centre %d,%d,%d,%d)"), *Texture->GetName(), SizeX, Texture->Source.GetSizeY(), Centre.R, Centre.G, Centre.B, Centre.A);
		}
		FString ParamText;
		if (Component->MaterialInstances.Num() > 0 && Component->MaterialInstances[0])
		{
			// The component's instance carries the weightmap textures and masks; its parent (the layer combination
			// instance) carries the static terrain layer parameters; that one's parent is the landscape material.
			UMaterialInstanceConstant* Instance = Component->MaterialInstances[0];
			UTexture* Weightmap0 = nullptr;
			Instance->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Weightmap0")), Weightmap0);
			ParamText += FString::Printf(TEXT("Weightmap0=%s"), *GetNameSafe(Weightmap0));
			for (UMaterialInstanceConstant* Parent = Cast<UMaterialInstanceConstant>(Instance->Parent); Parent; Parent = Cast<UMaterialInstanceConstant>(Parent->Parent))
			{
				const FStaticParameterSet& Set = Parent->GetStaticParameters();
				ParamText += FString::Printf(TEXT(" | %s static:"), *Parent->GetName());
				for (const FStaticTerrainLayerWeightParameter& Param : Set.EditorOnly.TerrainLayerWeightParameters)
				{
					ParamText += FString::Printf(TEXT(" %s=%d"), *Param.LayerName.ToString(), Param.WeightmapIndex);
				}
				ParamText += FString::Printf(TEXT(" (parent %s)"), *GetNameSafe(Parent->Parent));
			}
		}
		UE_LOG(LogTemp, Display, TEXT("BuildLegLandscape: material layers [%s]; component %s allocations [%s]; textures [%s]; instance params [%s]"),
			*Names.TrimStart(), *Component->GetName(), *Allocations.TrimStart(), *Textures.TrimStart(), *ParamText.TrimStart());
	}
	// Height range for the log, so a flat or clipped import shows up.
	uint16 MinH = 65535;
	uint16 MaxH = 0;
	for (const uint16 H : Heights)
	{
		MinH = FMath::Min(MinH, H);
		MaxH = FMath::Max(MaxH, H);
	}
	UE_LOG(LogTemp, Display, TEXT("BuildLegLandscape: %s %dx%d verts, %d components, quad %.0f cm, heights %.1f..%.1f m, %d layers"), *Label, Verts, Verts,
		Spec.ComponentsPerSide * Spec.ComponentsPerSide, Spec.QuadSizeCm, (MinH - 32768) / 128.f * Spec.ZScale / 100.f, (MaxH - 32768) / 128.f * Spec.ZScale / 100.f, LayerInfos.Num());
	return Landscape;
#else
	return nullptr;
#endif
}

int32 UGTVehicleSetupLibrary::CreateItemAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (const GTItemDefaults::FResource& Row : GTItemDefaults::Resources())
	{
		if (UGTItemDefinition* Item = Cast<UGTItemDefinition>(MakeAsset(Folder, *GTItemDefaults::AssetName(Row.Id), UGTItemDefinition::StaticClass())))
		{
			GTItemDefaults::Apply(Item, Row);
			Saved += SaveAsset(Item) ? 1 : 0;
		}
	}
	for (const GTItemDefaults::FPart& Row : GTItemDefaults::Parts())
	{
		if (UGTPartDefinition* Part = Cast<UGTPartDefinition>(MakeAsset(Folder, *GTItemDefaults::AssetName(Row.Id), UGTPartDefinition::StaticClass())))
		{
			GTItemDefaults::Apply(Part, Row);
			Saved += SaveAsset(Part) ? 1 : 0;
		}
	}
	for (const GTItemDefaults::FConsumable& Row : GTItemDefaults::Consumables())
	{
		if (UGTConsumableDefinition* Item = Cast<UGTConsumableDefinition>(MakeAsset(Folder, *GTItemDefaults::AssetName(Row.Id), UGTConsumableDefinition::StaticClass())))
		{
			GTItemDefaults::Apply(Item, Row);
			Saved += SaveAsset(Item) ? 1 : 0;
		}
	}
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateRecipeAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (const UGTRecipeDefinition::FDefault& Row : UGTRecipeDefinition::DefaultRecipes())
	{
		if (UGTRecipeDefinition* Recipe = Cast<UGTRecipeDefinition>(MakeAsset(Folder, Row.AssetName, UGTRecipeDefinition::StaticClass())))
		{
			Recipe->ApplyDefault(Row);
			Saved += SaveAsset(Recipe) ? 1 : 0;
		}
	}
	return Saved;
#else
	return 0;
#endif
}

int32 UGTVehicleSetupLibrary::CreateUpgradeAssets(const FString& Folder)
{
#if WITH_EDITOR
	int32 Saved = 0;
	for (const UGTUpgradeDefinition::FDefault& Row : UGTUpgradeDefinition::DefaultUpgrades())
	{
		if (UGTUpgradeDefinition* Upgrade = Cast<UGTUpgradeDefinition>(MakeAsset(Folder, Row.AssetName, UGTUpgradeDefinition::StaticClass())))
		{
			Upgrade->ApplyDefault(Row);
			Saved += SaveAsset(Upgrade) ? 1 : 0;
		}
	}
	return Saved;
#else
	return 0;
#endif
}
