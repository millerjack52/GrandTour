#include "OWCreateBiomePCGCommandlet.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Data/PCGDifferenceData.h"
#include "Elements/PCGAttributeFilter.h"
#include "Elements/PCGAttributeNoise.h"
#include "Elements/PCGBoundsModifier.h"
#include "Elements/PCGDataFromActor.h"
#include "Elements/PCGDifferenceElement.h"
#include "Elements/PCGDensityFilter.h"
#include "Elements/PCGDistance.h"
#include "Elements/PCGNormalToDensity.h"
#include "Elements/PCGProjectionElement.h"
#include "Elements/PCGSplineSampler.h"
#include "Elements/PCGStaticMeshSpawner.h"
#include "Elements/PCGSurfaceSampler.h"
#include "Elements/PCGTransformPoints.h"
#include "Elements/PCGTypedGetter.h"
#include "Engine/StaticMesh.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"
#include "MeshSelectors/PCGMeshSelectorWeighted.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "PCGGraph.h"
#include "PCGPoint.h"   // EPCGPointProperties - the A2 preset gate reads $Scale.Y
#include "PhysicsEngine/BodySetup.h"
#include "SceneTypes.h"
#include "UObject/SavePackage.h"

DEFINE_LOG_CATEGORY_STATIC(LogOWCreateBiomePCG, Log, All);

namespace OWBiomePCG
{
	constexpr const TCHAR* AssetDir = TEXT("/Game/OWGame/Dev/DressingLab");
	constexpr const TCHAR* PreviewDir = TEXT("/Game/OWGame/Dev/WorldPreview");
	constexpr const TCHAR* ConeMesh = TEXT("/Engine/BasicShapes/Cone.Cone");
	constexpr const TCHAR* CylinderMesh = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");

	// ANGRY MESH Meadow Pack (AM2, Docs/MeadowPackIntegrationPlan.md) -
	// vendor assets, referenced only, never edited. Summer set this cycle;
	// the Summer rock meshes live under Rocks/Rocks_Moss.
	constexpr const TCHAR* PackMeshDir =
		TEXT("/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes");

	FString PackMesh(const TCHAR* SubDir, const TCHAR* Name)
	{
		return FString::Printf(TEXT("%s/%s/%s.%s"), PackMeshDir, SubDir, Name, Name);
	}

	FString PackRock(int32 Index)
	{
		const FString Name = FString::Printf(TEXT("SM_Rock_%02d_Summer"), Index);
		return PackMesh(TEXT("Rocks/Rocks_Moss"), *Name);
	}

	// ---- Leg dressing LD4 (docs/LEG_DRESSING_PLAN.md): the GrandTour graph variants ----
	// -Variant=GT builds PCG_GT_Forest/Meadow/Scree/Alpine/Brush into /Game/GrandTour/Dressing/PCG from the same
	// builders. Everything GT adds is behind GVariantGT, so without the switch the OW graphs come out as before:
	//  - a physical class on every spawner (collision profile + a component tag the runtime reads);
	//  - tree size classes on every Forest and Alpine tree stream (SpawnTrees);
	//  - forest understorey (soft brush under every forest layer) and the Thicket brush graph.
	bool GVariantGT = false;
	/** LD7 cut step 1's A/B: -GTSoftHISM leaves the GT soft classes on the HISM the pack rule gives (plain ISM otherwise). */
	bool GSoftHISM = false;
	constexpr const TCHAR* GTAssetDir = TEXT("/Game/GrandTour/Dressing/PCG");

	/** The graph's package: /Game/OWGame/Dev/DressingLab/PCG_OW<Biome>, or with -Variant=GT /Game/GrandTour/Dressing/PCG/PCG_GT_<Biome>. */
	FString GraphPath(const TCHAR* Biome)
	{
		return GVariantGT ? FString::Printf(TEXT("%s/PCG_GT_%s"), GTAssetDir, Biome)
			: FString(AssetDir) + TEXT("/PCG_OW") + Biome;
	}

	/** LD4's physical classes (the "Spawner classes" table). Unset: an OW spawner (only an error in GT mode). */
	enum class EVegClass : uint8
	{
		Unset,
		Solid,          // mature / veteran / dead trees, stumps, logs, rocks, boulders: BlockAll, GTVeg.Solid
		SoftBrush,      // bushes, cover plants: NoCollision, GTVeg.Soft.Brush
		SoftSapling,    // tree variants at size class Sapling: NoCollision, GTVeg.Soft.Sapling
		SoftYoung,      // tree variants at size class Young: NoCollision, GTVeg.Soft.Young
		None,           // flowers, grass tufts, mushrooms, ground cover: NoCollision, no tag
	};

	const TCHAR* VegClassTag(EVegClass Class)
	{
		switch (Class)
		{
		case EVegClass::Solid: return TEXT("GTVeg.Solid");
		case EVegClass::SoftBrush: return TEXT("GTVeg.Soft.Brush");
		case EVegClass::SoftSapling: return TEXT("GTVeg.Soft.Sapling");
		case EVegClass::SoftYoung: return TEXT("GTVeg.Soft.Young");
		default: return nullptr;
		}
	}

	const TCHAR* VegClassName(EVegClass Class)
	{
		switch (Class)
		{
		case EVegClass::Solid: return TEXT("Solid");
		case EVegClass::SoftBrush: return TEXT("Soft.Brush");
		case EVegClass::SoftSapling: return TEXT("Soft.Sapling");
		case EVegClass::SoftYoung: return TEXT("Soft.Young");
		case EVegClass::None: return TEXT("None");
		default: return TEXT("Unset");
		}
	}

	/** GT mode's report (docs/landscape_migration/ld4_gt_graphs.json): each spawner's class and meshes, per graph. */
	FString GReportGraph;
	TMap<FString, TArray<FString>> GReportSpawners;
	TMap<FString, bool> GSimpleCollision;          // mesh path -> has simple collision (cached)
	TArray<FString> GNoSimpleCollision;           // Solid meshes that had none, given NoCollision (unique)
	int32 GUnsetSpawners = 0;

	/** A Solid mesh blocks only with simple collision to block with (the LD4 rule; vendor assets are never edited). */
	bool HasSimpleCollision(const FString& MeshPath)
	{
		if (const bool* Known = GSimpleCollision.Find(MeshPath))
		{
			return *Known;
		}
		const UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
		const UBodySetup* Body = Mesh ? Mesh->GetBodySetup() : nullptr;
		const bool bHas = Body && Body->AggGeom.GetElementCount() > 0;
		GSimpleCollision.Add(MeshPath, bHas);
		if (!bHas)
		{
			UE_LOG(LogOWCreateBiomePCG, Warning, TEXT("LD4 Solid mesh without simple collision (given NoCollision): %s (%s, trace flag %d)"),
				*MeshPath, Mesh ? TEXT("loaded") : TEXT("NOT FOUND"), Body ? static_cast<int32>(Body->CollisionTraceFlag) : -1);
		}
		return bHas;
	}

	/** GT mode: the entry's collision profile and component tag from its class. */
	void ApplyVegClass(FPCGSoftISMComponentDescriptor& Descriptor, const FString& MeshPath, EVegClass Class, FString& OutNote)
	{
		FName Profile = TEXT("NoCollision");
		if (Class == EVegClass::Solid)
		{
			if (HasSimpleCollision(MeshPath))
			{
				Profile = TEXT("BlockAll");
			}
			else
			{
				GNoSimpleCollision.AddUnique(MeshPath);
			}
		}
		Descriptor.BodyInstance.SetCollisionProfileName(Profile);
		Descriptor.ComponentTags.Reset();
		if (const TCHAR* Tag = VegClassTag(Class))
		{
			Descriptor.ComponentTags.Add(FName(Tag));
		}
		OutNote = FString::Printf(TEXT("%s:%s"), *FPackageName::ObjectPathToObjectName(MeshPath), *Profile.ToString());
	}

	UPCGGraph* GetOrCreateGraph(const FString& PackagePath, bool& bOutCreated)
	{
		bOutCreated = false;
		const FString AssetName = FPackageName::GetLongPackageAssetName(PackagePath);
		if (UPCGGraph* Existing = LoadObject<UPCGGraph>(nullptr, *(PackagePath + TEXT(".") + AssetName)))
		{
			// Rebuild in place so PCG components in maps keep their reference.
			Existing->Modify();
			TArray<UPCGNode*> Stale = Existing->GetNodes();
			Existing->RemoveNodes(Stale);
			return Existing;
		}
		UPackage* Package = CreatePackage(*PackagePath);
		UPCGGraph* Graph = NewObject<UPCGGraph>(Package, FName(*AssetName), RF_Public | RF_Standalone);
		FAssetRegistryModule::AssetCreated(Graph);
		bOutCreated = true;
		return Graph;
	}

	bool SaveAssetPackage(UObject* Asset)
	{
		UPackage* Package = Asset->GetOutermost();
		Package->MarkPackageDirty();
		const FString FileName = FPackageName::LongPackageNameToFilename(
			Package->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SaveArgs.SaveFlags = SAVE_NoError;
		return UPackage::SavePackage(Package, Asset, *FileName, SaveArgs);
	}

	template <typename TSettings>
	TSettings* AddNode(UPCGGraph* Graph, UPCGNode*& OutNode, int32 X, int32 Y)
	{
		UPCGSettings* Raw = nullptr;
		OutNode = Graph->AddNodeOfType(TSettings::StaticClass(), Raw);
		check(OutNode && Raw);
		OutNode->SetNodePosition(X, Y);
		return CastChecked<TSettings>(Raw);
	}

	UPCGNode* MakeLandscapeGetter(UPCGGraph* Graph)
	{
		UPCGNode* Node = nullptr;
		UPCGGetLandscapeSettings* S = AddNode<UPCGGetLandscapeSettings>(Graph, Node, -1400, 0);
		S->ActorSelector.ActorFilter = EPCGActorFilter::AllWorldActors;
		S->ActorSelector.ActorSelection = EPCGActorSelection::ByClass;
		// MUST be set explicitly: PostLoad only defaults this for non-ByClass
		// selectors, so a null class saves as null and matches NOTHING.
		S->ActorSelector.ActorSelectionClass = ALandscapeProxy::StaticClass();
		S->ActorSelector.bSelectMultiple = true;
		S->ActorSelector.bMustOverlapSelf = false;   // the whole python saga, one line
		return Node;
	}

	UPCGNode* MakeSampler(UPCGGraph* Graph, UPCGNode* Land, float PointsPerM2, int32 X, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGSurfaceSamplerSettings* S = AddNode<UPCGSurfaceSamplerSettings>(Graph, Node, X, Y);
		S->PointsPerSquaredMeter = PointsPerM2;
		// Canvas graduation (2026-07-30): bounded. Samplers clip to the
		// owning PCG actor's bounds - the lab volume covers the whole lab
		// landscape (behavior unchanged there); on L_OWWorldCanvas the
		// user places sized work volumes, so Generate can never try to
		// dress all 65km2 at once.
		S->bUnbounded = false;
		Graph->AddEdge(Land, TEXT("Out"), Node, TEXT("Surface"));
		return Node;
	}

	// Output pin: "InsideFilter"
	UPCGNode* MakeWeightFilter(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		FName LayerName, double Threshold, int32 X, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGAttributeFilteringSettings* S = AddNode<UPCGAttributeFilteringSettings>(Graph, Node, X, Y);
		S->Operator = EPCGAttributeFilterOperator::Greater;
		S->TargetAttribute.SetAttributeName(LayerName);
		S->bUseConstantThreshold = true;
		S->AttributeTypes.Type = EPCGMetadataTypes::Double;
		S->AttributeTypes.DoubleValue = Threshold;
		Graph->AddEdge(Prev, PrevPin, Node, TEXT("In"));
		return Node;
	}

	// D2.5 brush-opacity band: keep points whose painted weight sits in
	// (Lo, Hi]. Two chained attribute filters; output pin "InsideFilter".
	UPCGNode* MakeWeightBand(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		FName LayerName, double Lo, double Hi, int32 X, int32 Y)
	{
		UPCGNode* Above = MakeWeightFilter(Graph, Prev, PrevPin, LayerName, Lo, X, Y);
		UPCGNode* Node = nullptr;
		UPCGAttributeFilteringSettings* S = AddNode<UPCGAttributeFilteringSettings>(Graph, Node, X + 200, Y);
		S->Operator = EPCGAttributeFilterOperator::Lesser;
		S->TargetAttribute.SetAttributeName(LayerName);
		S->bUseConstantThreshold = true;
		S->AttributeTypes.Type = EPCGMetadataTypes::Double;
		S->AttributeTypes.DoubleValue = Hi;
		Graph->AddEdge(Above, TEXT("InsideFilter"), Node, TEXT("In"));
		return Node;
	}

	UPCGNode* MakeSlopeBand(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		float Lo, float Hi, int32 X, int32 Y)
	{
		UPCGNode* N2DNode = nullptr;
		AddNode<UPCGNormalToDensitySettings>(Graph, N2DNode, X, Y);
		Graph->AddEdge(Prev, PrevPin, N2DNode, TEXT("In"));

		UPCGNode* FiltNode = nullptr;
		UPCGDensityFilterSettings* Filt = AddNode<UPCGDensityFilterSettings>(Graph, FiltNode, X + 250, Y);
		Filt->LowerBound = Lo;
		Filt->UpperBound = Hi;
		Graph->AddEdge(N2DNode, TEXT("Out"), FiltNode, TEXT("In"));
		return FiltNode;
	}

	// bAbsoluteRotation=true REPLACES the sampled point rotation instead of
	// adding to it: landscape surface points arrive normal-aligned, so trees
	// with additive jitter lean with the slope. Absolute pitch/roll +/-6 +
	// yaw 0-360 keeps trees straight up with a slight natural lean
	// (user 2026-07-28). Logs/stones stay additive - deadfall SHOULD follow
	// the ground.
	UPCGNode* MakeTransform(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		const FVector& ScaleMin, const FVector& ScaleMax, bool bUniform,
		const FRotator& RotMin, const FRotator& RotMax, int32 X, int32 Y,
		bool bAbsoluteRotation = false)
	{
		UPCGNode* Node = nullptr;
		UPCGTransformPointsSettings* S = AddNode<UPCGTransformPointsSettings>(Graph, Node, X, Y);
		S->ScaleMin = ScaleMin;
		S->ScaleMax = ScaleMax;
		S->bUniformScale = bUniform;
		S->RotationMin = RotMin;
		S->RotationMax = RotMax;
		S->bAbsoluteRotation = bAbsoluteRotation;
		Graph->AddEdge(Prev, PrevPin, Node, TEXT("In"));
		return Node;
	}

	// D3: every stream subtracts actors tagged OWDressing.Exclude (volumes,
	// road ribbons, POI footprints - anything with primitive bounds). With no
	// tagged actors in the level the getter yields nothing and the Difference
	// is a pass-through, so the graphs behave exactly as before D3.
	UPCGNode* MakeExclusionGetter(UPCGGraph* Graph)
	{
		UPCGNode* Node = nullptr;
		UPCGDataFromActorSettings* S = AddNode<UPCGDataFromActorSettings>(Graph, Node, -1400, 900);
		S->Mode = EPCGGetDataFromActorMode::ParseActorComponents;
		S->ActorSelector.ActorFilter = EPCGActorFilter::AllWorldActors;
		S->ActorSelector.ActorSelection = EPCGActorSelection::ByTag;
		S->ActorSelector.ActorSelectionTag = TEXT("OWDressing.Exclude");
		S->ActorSelector.bSelectMultiple = true;
		S->ActorSelector.bMustOverlapSelf = false;
		return Node;
	}

	// Difference(Binary) zeroes the density of points inside excluded bounds;
	// the inverted 0-0.01 filter then removes ONLY those exact-zero points.
	// (A plain keep-above-threshold cull would eat legitimate low-density
	// points - e.g. seed-adjacent grove trees, whose distance-density is ~0 -
	// so exclusion must also run BEFORE any distance-density stage.)
	// Takes MULTIPLE exclusion sources: the Differences pin implicitly
	// unions everything wired into it (engine-documented behavior), so the
	// tag getter and the road corridors ride one Difference node.
	UPCGNode* MakeExcluded(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		const TArray<UPCGNode*>& Excl, int32 X, int32 Y)
	{
		UPCGNode* DiffNode = nullptr;
		UPCGDifferenceSettings* Diff = AddNode<UPCGDifferenceSettings>(Graph, DiffNode, X, Y);
		Diff->DensityFunction = EPCGDifferenceDensityFunction::Binary;
		Graph->AddEdge(Prev, PrevPin, DiffNode, TEXT("Source"));
		for (UPCGNode* ExclNode : Excl)
		{
			Graph->AddEdge(ExclNode, TEXT("Out"), DiffNode, TEXT("Differences"));
		}

		UPCGNode* CullNode = nullptr;
		UPCGDensityFilterSettings* Cull = AddNode<UPCGDensityFilterSettings>(Graph, CullNode, X + 200, Y);
		Cull->LowerBound = 0.0f;
		Cull->UpperBound = 0.01f;
		Cull->bInvertFilter = true;
		Graph->AddEdge(DiffNode, TEXT("Out"), CullNode, TEXT("In"));
		return CullNode;
	}

	FString TreeMeshPath(const TCHAR* Name)
	{
		return FString::Printf(TEXT("/Game/OWGame/Dev/DressingLab/Trees/%s.%s"), Name, Name);
	}

	struct FMeshEntry
	{
		FString MeshPath;
		int32 Weight = 1;
		FString MaterialPath;    // empty = keep mesh materials
		FString TreeSpecies;     // set = override per-slot with MI_OWTrunk/Foliage_<S>
		FString FoliageMISuffix; // e.g. "_ToneWarm" - foliage slot only, per-tree tone
		int8 CastShadow = -1;    // -1 = spawner default; 0/1 force per entry
	};

	// Vendor tree meshes keep their own slots; we dress them in the OW-owned
	// tintable MIs by matching each slot's material NAME (Trunk vs foliage) -
	// blind index-ordered overrides would risk trunks wearing leaves.
	void AddSpeciesOverrides(FPCGSoftISMComponentDescriptor& Descriptor,
		const FString& MeshPath, const FString& Species, const FString& FoliageSuffix)
	{
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
		if (!Mesh)
		{
			UE_LOG(LogOWCreateBiomePCG, Warning, TEXT("species override: cannot load %s"), *MeshPath);
			return;
		}
		const FString MIRoot = TEXT("/Game/OWGame/Dev/DressingLab/TreeMIs");
		for (const FStaticMaterial& Slot : Mesh->GetStaticMaterials())
		{
			const bool bTrunk = Slot.MaterialInterface
				&& Slot.MaterialInterface->GetName().Contains(TEXT("Trunk"));
			const FString Kind = bTrunk ? TEXT("Trunk") : TEXT("Foliage");
			const FString Suffix = bTrunk ? FString() : FoliageSuffix;
			const FString MIName = FString::Printf(TEXT("MI_OW%s_%s%s"), *Kind, *Species, *Suffix);
			Descriptor.OverrideMaterials.Add(TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
				FString::Printf(TEXT("%s/%s.%s"), *MIRoot, *MIName, *MIName))));
		}
	}

	// Leg dressing LD8a (docs/LEG_DRESSING_PLAN.md): the GT variant's summer leaves. Art/dressing/retint_summer.py apply makes
	// the summer copies (MI_GT_Leaf_*_Summer in /Game/GrandTour/Dressing/Materials; its palette table is the one place the
	// colours live) and writes Art/dressing/retint_summer_map.txt, one "<mesh> <slot material> <summer copy>" line each. A GT
	// spawner entry whose slot material (its override, else the mesh's own) has a line wears the copy through
	// OverrideMaterials. No file: no retint (the OW autumn MIs), with a warning. The OW graphs never read it.
	/** LD8b: the WPO disable distance on the GT bushes and cover plants (cm). A dial. */
	constexpr int32 GTSmallPlantWPODisableCm = 5000;

	TMap<FString, TMap<FString, FString>> GSummerMap;
	bool GSummerMapLoaded = false;
	int32 GSummerSlots = 0;

	const TMap<FString, TMap<FString, FString>>& SummerMap()
	{
		if (!GSummerMapLoaded)
		{
			GSummerMapLoaded = true;
			const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Art/dressing/retint_summer_map.txt"));
			TArray<FString> Lines;
			if (!FFileHelper::LoadFileToStringArray(Lines, *Path))
			{
				UE_LOG(LogOWCreateBiomePCG, Warning, TEXT("LD8a: no %s - the GT graphs keep the OW (autumn) leaf materials; run Art/dressing/retint_summer.bat apply"), *Path);
				return GSummerMap;
			}
			int32 Count = 0;
			for (const FString& Line : Lines)
			{
				TArray<FString> Parts;
				Line.TrimStartAndEnd().ParseIntoArrayWS(Parts);
				if (Parts.Num() == 3 && !Parts[0].StartsWith(TEXT("#")))
				{
					GSummerMap.FindOrAdd(Parts[0]).Add(Parts[1], Parts[2]);
					++Count;
				}
			}
			UE_LOG(LogOWCreateBiomePCG, Display, TEXT("LD8a: %d summer leaf line(s) for %d mesh(es) from %s"), Count, GSummerMap.Num(), *Path);
		}
		return GSummerMap;
	}

	/** GT only: swap each slot material that has a summer copy for this mesh; returns the slots swapped. */
	int32 ApplySummerLeaves(FPCGSoftISMComponentDescriptor& Descriptor, const FString& MeshPath)
	{
		const TMap<FString, FString>* PerMesh = SummerMap().Find(MeshPath);
		UStaticMesh* Mesh = PerMesh ? LoadObject<UStaticMesh>(nullptr, *MeshPath) : nullptr;
		if (!Mesh)
		{
			return 0;
		}
		const TArray<FStaticMaterial>& Slots = Mesh->GetStaticMaterials();
		TArray<TSoftObjectPtr<UMaterialInterface>> Out;
		int32 Swapped = 0;
		for (int32 i = 0; i < Slots.Num(); ++i)
		{
			const bool bOverride = Descriptor.OverrideMaterials.IsValidIndex(i) && !Descriptor.OverrideMaterials[i].IsNull();
			const FSoftObjectPath Current = bOverride ? Descriptor.OverrideMaterials[i].ToSoftObjectPath() : FSoftObjectPath(Slots[i].MaterialInterface);
			if (const FString* Summer = PerMesh->Find(Current.ToString()))
			{
				Out.Add(TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(*Summer)));
				++Swapped;
			}
			else
			{
				Out.Add(TSoftObjectPtr<UMaterialInterface>(Current));
			}
		}
		if (Swapped > 0)
		{
			Descriptor.OverrideMaterials = Out;
			GSummerSlots += Swapped;
		}
		return Swapped;
	}

	// D4 budget table: preview props never cast shadows, never collide.
	// Trees are the exception (user 2026-07-27): they DO cast shadows -
	// safe with VSM because WPO evaluation is off (pages stay cached).
	// LD4: VegClass is the spawner's physical class; only -Variant=GT reads it (an OW spawner stays NoCollision, untagged).
	void MakeSpawner(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		const TArray<FMeshEntry>& Entries, int32 X, int32 Y,
		bool bCastShadow = false, bool bWindWPO = false,
		int32 CullStart = 0, int32 CullEnd = 0, EVegClass VegClass = EVegClass::Unset)
	{
		UPCGNode* Node = nullptr;
		UPCGStaticMeshSpawnerSettings* S = AddNode<UPCGStaticMeshSpawnerSettings>(Graph, Node, X, Y);
		S->SetMeshSelectorType(UPCGMeshSelectorWeighted::StaticClass());
		UPCGMeshSelectorWeighted* Selector = CastChecked<UPCGMeshSelectorWeighted>(S->MeshSelectorParameters);
		FString GTNotes;
		if (GVariantGT && VegClass == EVegClass::Unset)
		{
			++GUnsetSpawners;
			UE_LOG(LogOWCreateBiomePCG, Error, TEXT("LD4: a spawner in %s has no physical class"), *GReportGraph);
		}
		for (const FMeshEntry& Entry : Entries)
		{
			FPCGMeshSelectorWeightedEntry& E = Selector->MeshEntries.Emplace_GetRef(
				TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(Entry.MeshPath)), Entry.Weight);
			E.Descriptor.bCastShadow =
				Entry.CastShadow >= 0 ? Entry.CastShadow != 0 : bCastShadow;
			E.Descriptor.BodyInstance.SetCollisionProfileName(TEXT("NoCollision"));
			if (GVariantGT)
			{
				FString Note;
				ApplyVegClass(E.Descriptor, Entry.MeshPath, VegClass, Note);
				GTNotes += (GTNotes.IsEmpty() ? TEXT("") : TEXT(" ")) + Note;
			}
			E.Descriptor.InstanceStartCullDistance = CullStart;
			E.Descriptor.InstanceEndCullDistance = CullEnd;
			// MF1 (2026-07-28): pack meshes are non-Nanite with 4 authored
			// LODs that a plain ISM never engages (one LOD per component,
			// forest-sized bounds) - MF0 measured Shadow Depths 13.7ms avg
			// from LOD0 oaks in VSM. HISM restores per-instance LOD + culls.
			// Painterly Nanite trees stay on the default component.
			if (Entry.MeshPath.StartsWith(TEXT("/Game/ANGRY_MESH")))
			{
				E.Descriptor.ComponentClass =
					UHierarchicalInstancedStaticMeshComponent::StaticClass();
			}
			// LD5 (proxy swap, revised 2026-09-27): UGTVegetationSubsystem bends a soft instance by hiding it in its
			// component, and on a HISM every such update rebuilds the cluster tree. GT soft classes are always a plain ISM.
			if (GVariantGT && (VegClass == EVegClass::SoftBrush || VegClass == EVegClass::SoftSapling || VegClass == EVegClass::SoftYoung))
			{
				E.Descriptor.ComponentClass = GSoftHISM ? UHierarchicalInstancedStaticMeshComponent::StaticClass() : UInstancedStaticMeshComponent::StaticClass();
			}
			if (GVariantGT)
			{
				const UClass* ComponentClass = E.Descriptor.ComponentClass.Get();
				GTNotes += FString::Printf(TEXT(":%s"), ComponentClass && ComponentClass->IsChildOf(UHierarchicalInstancedStaticMeshComponent::StaticClass()) ? TEXT("HISM") : TEXT("ISM"));
			}
			// Vendor foliage wind was WORLD-SPACE WPO: it swam whole canopies at
			// distance and blocked Nanite cluster caching, so tree WPO ran fully
			// OFF (paid 2026-07-27, 3 rounds; the 40m disable-distance fence
			// failed - one huge ISM spans the map, wrong granularity). The OW
			// masters (ClaudeAuthorOWFoliageMaster.py, 2026-07-28) replaced that
			// with bounded height-based sway that fades out by material camera
			// distance, so trees re-enable evaluation via bWindWPO. Shadow
			// invalidation stays Static: VSM pages keep caching (the shadow-perf
			// win) and the <=25cm sway never reads in shadow.
			E.Descriptor.bEvaluateWorldPositionOffset = bWindWPO;
			E.Descriptor.WorldPositionOffsetDisableDistance = 0;
			if (GVariantGT)
			{
				// Leg dressing LD8b (docs/LEG_DRESSING_PLAN.md): the small plants (Soft.Brush, Soft.Sapling, unclassed) stay out
				// of Lumen and the distance fields; Soft.Young and Solid keep both. Bushes and cover plants stop their wind at
				// 50 m (the LD8a profile: Lumen DiffuseIndirectAndAO and ShadowDepths grew most).
				if (VegClass == EVegClass::SoftBrush || VegClass == EVegClass::SoftSapling || VegClass == EVegClass::None)
				{
					E.Descriptor.bAffectDistanceFieldLighting = false;
					E.Descriptor.bAffectDynamicIndirectLighting = false;
					GTNotes += TEXT(":noLumenDF");
				}
				if (Entry.MeshPath.Contains(TEXT("Bush")) || Entry.MeshPath.Contains(TEXT("CoverPlant")))
				{
					E.Descriptor.WorldPositionOffsetDisableDistance = GTSmallPlantWPODisableCm;
					GTNotes += FString::Printf(TEXT(":wpo%dcm"), GTSmallPlantWPODisableCm);
				}
			}
			if (bWindWPO)
			{
				E.Descriptor.ShadowCacheInvalidationBehavior =
					EShadowCacheInvalidationBehavior::Static;
			}
			if (!Entry.TreeSpecies.IsEmpty())
			{
				AddSpeciesOverrides(E.Descriptor, Entry.MeshPath, Entry.TreeSpecies,
					Entry.FoliageMISuffix);
			}
			else if (!Entry.MaterialPath.IsEmpty())
			{
				E.Descriptor.OverrideMaterials.Add(
					TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(Entry.MaterialPath)));
			}
			if (GVariantGT && ApplySummerLeaves(E.Descriptor, Entry.MeshPath) > 0)
			{
				GTNotes += TEXT(":summer");
			}
		}
		Graph->AddEdge(Prev, PrevPin, Node, TEXT("In"));
		if (GVariantGT)
		{
			GReportSpawners.FindOrAdd(GReportGraph).Add(FString::Printf(TEXT("%s [%s] %s"),
				VegClassName(VegClass), VegClassTag(VegClass) ? VegClassTag(VegClass) : TEXT("no tag"), *GTNotes));
		}
	}

	// ---- LD4 GT-mode stream helpers ----

	/** A transform node with every switch explicit (MakeTransform leaves bAbsoluteScale at its multiply default). */
	UPCGNode* MakeTransformEx(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		const FVector& ScaleMin, const FVector& ScaleMax, bool bUniform, bool bAbsoluteScale,
		const FRotator& RotMin, const FRotator& RotMax, bool bAbsoluteRotation, int32 Seed, int32 X, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGTransformPointsSettings* S = AddNode<UPCGTransformPointsSettings>(Graph, Node, X, Y);
		S->ScaleMin = ScaleMin;
		S->ScaleMax = ScaleMax;
		S->bUniformScale = bUniform;
		S->bAbsoluteScale = bAbsoluteScale;
		S->RotationMin = RotMin;
		S->RotationMax = RotMax;
		S->bAbsoluteRotation = bAbsoluteRotation;
		S->Seed = Seed;
		Graph->AddEdge(Prev, PrevPin, Node, TEXT("In"));
		return Node;
	}

	/**
	 * LD4 size class scale: SET the point's scale to a uniform U(Lo, Hi) (bAbsoluteScale - the transform node multiplies
	 * by default), keeping its rotation, then MULTIPLY Z by U(1.0, 1.15) (the Z jitter). Two nodes; returns the second.
	 */
	UPCGNode* MakeSizeScale(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin, double Lo, double Hi,
		const FRotator& RotMin, const FRotator& RotMax, bool bAbsoluteRotation, int32 Seed, int32 X, int32 Y)
	{
		UPCGNode* Size = MakeTransformEx(Graph, Prev, PrevPin, FVector(Lo), FVector(Hi), /*bUniform=*/true,
			/*bAbsoluteScale=*/true, RotMin, RotMax, bAbsoluteRotation, Seed, X, Y);
		return MakeTransformEx(Graph, Size, TEXT("Out"), FVector(1.0, 1.0, 1.0), FVector(1.0, 1.0, 1.15),
			/*bUniform=*/false, /*bAbsoluteScale=*/false, FRotator::ZeroRotator, FRotator::ZeroRotator,
			/*bAbsoluteRotation=*/false, Seed + 1, X + 200, Y);
	}

	/** Saplings and young trees use only the non-giant, non-ancient, non-dead variants. */
	TArray<FMeshEntry> SmallTreeEntries(const TArray<FMeshEntry>& Entries)
	{
		TArray<FMeshEntry> Out;
		for (const FMeshEntry& Entry : Entries)
		{
			if (!Entry.MeshPath.Contains(TEXT("Giant")) && !Entry.MeshPath.Contains(TEXT("Ancient"))
				&& !Entry.MeshPath.Contains(TEXT("Dead")))
			{
				Out.Add(Entry);
			}
		}
		return Out;
	}

	// LD4 size class shares, scales and seeds (the "Tree size classes" table).
	constexpr float SaplingMaxDensity = 0.18f;
	constexpr float YoungMaxDensity = 0.40f;
	constexpr double SaplingScaleLo = 0.25, SaplingScaleHi = 0.45;
	constexpr double YoungScaleLo = 0.45, YoungScaleHi = 0.80;
	constexpr int32 SizeNoiseSeed = 1801;
	constexpr int32 SaplingScaleSeed = 1811;
	constexpr int32 YoungScaleSeed = 1821;

	/**
	 * A tree stream's spawn. OW: the spawner, exactly as before. GT (LD4 size classes): after the stream's own transform
	 * an attribute noise sets $Density to U(0,1) and three density bands split the points - Sapling 0-0.18 (uniform
	 * 0.25-0.45, Z x 1.0-1.15, Soft.Sapling), Young 0.18-0.40 (0.45-0.80, Z x 1.0-1.15, Soft.Young), Mature 0.40-1 (the
	 * stream's own scale, Solid) - saplings and young trees drawing only on the non-giant, non-ancient, non-dead entries.
	 */
	void SpawnTrees(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		const TArray<FMeshEntry>& Entries, int32 X, int32 Y,
		bool bCastShadow, bool bWindWPO, int32 CullStart = 0, int32 CullEnd = 0)
	{
		if (!GVariantGT)
		{
			MakeSpawner(Graph, Prev, PrevPin, Entries, X, Y, bCastShadow, bWindWPO, CullStart, CullEnd);
			return;
		}
		UPCGNode* NoiseNode = nullptr;
		UPCGAttributeNoiseSettings* Noise = AddNode<UPCGAttributeNoiseSettings>(Graph, NoiseNode, X, Y);
		Noise->InputSource.SetPointProperty(EPCGPointProperties::Density);
		Noise->OutputTarget.SetPointProperty(EPCGPointProperties::Density);
		Noise->Mode = EPCGAttributeNoiseMode::Set;
		Noise->NoiseMin = 0.f;
		Noise->NoiseMax = 1.f;
		Noise->Seed = SizeNoiseSeed;
		Graph->AddEdge(Prev, PrevPin, NoiseNode, TEXT("In"));

		auto Band = [Graph, NoiseNode](float Lo, float Hi, int32 BX, int32 BY)
		{
			UPCGNode* FiltNode = nullptr;
			UPCGDensityFilterSettings* Filt = AddNode<UPCGDensityFilterSettings>(Graph, FiltNode, BX, BY);
			Filt->LowerBound = Lo;
			Filt->UpperBound = Hi;
			Graph->AddEdge(NoiseNode, TEXT("Out"), FiltNode, TEXT("In"));
			return FiltNode;
		};
		const TArray<FMeshEntry> Small = SmallTreeEntries(Entries);
		const FRotator Zero = FRotator::ZeroRotator;

		UPCGNode* Sapling = Band(0.f, SaplingMaxDensity, X + 250, Y - 150);
		UPCGNode* SaplingXf = MakeSizeScale(Graph, Sapling, TEXT("Out"), SaplingScaleLo, SaplingScaleHi,
			Zero, Zero, /*bAbsoluteRotation=*/false, SaplingScaleSeed, X + 500, Y - 150);
		MakeSpawner(Graph, SaplingXf, TEXT("Out"), Small, X + 950, Y - 150, bCastShadow, bWindWPO,
			CullStart, CullEnd, EVegClass::SoftSapling);

		UPCGNode* Young = Band(SaplingMaxDensity, YoungMaxDensity, X + 250, Y);
		UPCGNode* YoungXf = MakeSizeScale(Graph, Young, TEXT("Out"), YoungScaleLo, YoungScaleHi,
			Zero, Zero, /*bAbsoluteRotation=*/false, YoungScaleSeed, X + 500, Y);
		MakeSpawner(Graph, YoungXf, TEXT("Out"), Small, X + 950, Y, bCastShadow, bWindWPO,
			CullStart, CullEnd, EVegClass::SoftYoung);

		UPCGNode* Mature = Band(YoungMaxDensity, 1.f, X + 250, Y + 150);
		MakeSpawner(Graph, Mature, TEXT("Out"), Entries, X + 950, Y + 150, bCastShadow, bWindWPO,
			CullStart, CullEnd, EVegClass::Solid);
	}

	// LD4 soft-brush palettes (the "Spawner classes" table): bushes and cover plants.
	FString OwnTree(const TCHAR* Name)
	{
		return FString::Printf(TEXT("/Game/OWGame/Dev/DressingLab/Trees/%s.%s"), Name, Name);
	}

	// LD7 cut step 1: the GT variant's soft pack meshes are the Nanite passthrough copies (OWCreateTreeVariants
	// -GTNanitePack, /Game/GrandTour/Dressing/Nanite/SM_GTN_<name>); the OW graphs keep the vendor meshes.
	FString SoftPackMesh(const TCHAR* SubDir, const FString& Name)
	{
		if (GVariantGT)
		{
			return FString::Printf(TEXT("/Game/GrandTour/Dressing/Nanite/SM_GTN_%s.SM_GTN_%s"), *Name, *Name);
		}
		return PackMesh(SubDir, *Name);
	}

	TArray<FMeshEntry> BushEntries()
	{
		TArray<FMeshEntry> Out = {
			{OwnTree(TEXT("SM_OWBush_Beech_A")), 1}, {OwnTree(TEXT("SM_OWBush_Beech_B")), 1},
			{OwnTree(TEXT("SM_OWBush_Birch_A")), 1}, {OwnTree(TEXT("SM_OWBush_Birch_B")), 1},
		};
		for (int32 i = 1; i <= 5; ++i)
		{
			Out.Add({SoftPackMesh(TEXT("Trees/Trees_Summer"), FString::Printf(TEXT("SM_BirchBush_%02d_Summer"), i)), 1});
		}
		return Out;
	}

	TArray<FMeshEntry> CoverPlantEntries()
	{
		TArray<FMeshEntry> Out;
		for (int32 i = 1; i <= 4; ++i)
		{
			Out.Add({SoftPackMesh(TEXT("CoverPlants/CoverPlants_Summer"), FString::Printf(TEXT("SM_CoverPlant_%02d_Summer"), i)), 1});
		}
		return Out;
	}

	// Bushes: the meadow bush recipe (upright, slight lean, gentle sway, no shadows, 100-130 m cull). Cover plants: the
	// pack grass types' scale (0.75-1.2, ClaudeHookupMeadowPack.py's forest-floor rows) and the meadow grass cull.
	constexpr double BushLeanDeg = 4.0;
	constexpr int32 BushCullStart = 10000, BushCullEnd = 13000;
	constexpr double CoverScaleLo = 0.75, CoverScaleHi = 1.2;
	constexpr int32 CoverCullStart = 6000, CoverCullEnd = 8000;
	constexpr float SoftSlopeLo = 0.8f, SoftSlopeHi = 1.0f;

	/**
	 * One LD4 soft stream: sampler -> the layer's weight (above Lo, or within Lo..Hi when Hi > 0) -> slope band 0.8-1.0
	 * -> the exclusions -> uniform scale U(ScaleLo, ScaleHi) with a slight absolute lean (bSizeClass: the size-class
	 * scale, SET not multiplied, and the Z jitter) -> the spawner with Class.
	 */
	// The GT soft brush streams (bushes and cover plants: the forest understorey and the Thicket brush) at this share of
	// their LD4 densities. A dial; 1 = LD4's numbers. LD7 cut step 5 set 0.5 for no measured gain; LD8a
	// (docs/LEG_DRESSING_PLAN.md) put it back to 1.
	constexpr float GTBrushDensityScale = 1.0f;

	void MakeSoftStream(UPCGGraph* Graph, UPCGNode* Land, const TArray<UPCGNode*>& Excl, FName Layer,
		double Lo, double Hi, float PointsPerM2, double ScaleLo, double ScaleHi, bool bSizeClass,
		const TArray<FMeshEntry>& Entries, EVegClass Class, bool bCastShadow, bool bWindWPO,
		int32 CullStart, int32 CullEnd, int32 Seed, int32 Y)
	{
		if (GVariantGT && Class == EVegClass::SoftBrush)
		{
			PointsPerM2 *= GTBrushDensityScale;
		}
		UPCGNode* Pts = MakeSampler(Graph, Land, PointsPerM2, -1100, Y);
		UPCGNode* F = (Hi > 0.0)
			? MakeWeightBand(Graph, Pts, TEXT("Out"), Layer, Lo, Hi, -880, Y)
			: MakeWeightFilter(Graph, Pts, TEXT("Out"), Layer, Lo, -850, Y);
		UPCGNode* Slope = MakeSlopeBand(Graph, F, TEXT("InsideFilter"), SoftSlopeLo, SoftSlopeHi, -600, Y);
		UPCGNode* NotEx = MakeExcluded(Graph, Slope, TEXT("Out"), Excl, -320, Y + 60);
		const double Lean = bSizeClass ? 6.0 : BushLeanDeg;
		const FRotator RotMin(-Lean, 0.0, -Lean);
		const FRotator RotMax(Lean, 360.0, Lean);
		UPCGNode* Xf = bSizeClass
			? MakeSizeScale(Graph, NotEx, TEXT("Out"), ScaleLo, ScaleHi, RotMin, RotMax, /*bAbsoluteRotation=*/true, Seed, -60, Y)
			: MakeTransformEx(Graph, NotEx, TEXT("Out"), FVector(ScaleLo), FVector(ScaleHi), /*bUniform=*/true,
				/*bAbsoluteScale=*/false, RotMin, RotMax, /*bAbsoluteRotation=*/true, Seed, -60, Y);
		MakeSpawner(Graph, Xf, TEXT("Out"), Entries, 400, Y, bCastShadow, bWindWPO, CullStart, CullEnd, Class);
	}

	// Road-corridor exclusion for the BIOME graphs (user 2026-07-30: trees
	// grew from the road bed). Declared here because the biome builders
	// precede the road spline machinery it reuses; see the definition
	// (below MakeProjectToLandscape) for the design notes.
	TArray<UPCGNode*> MakeRoadExclusions(UPCGGraph* Graph, UPCGNode* Land);

	bool BuildForestGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(GraphPath(TEXT("Forest")), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };
		Excl.Append(MakeRoadExclusions(Graph, Land));

		// trees: candidates -> painted OW_Forest -> flat -> not excluded -> near a grove seed
		UPCGNode* Cand = MakeSampler(Graph, Land, 0.01f, -1100, 0);
		UPCGNode* CandF = MakeWeightFilter(Graph, Cand, TEXT("Out"), TEXT("OW_Forest"), 0.5, -850, 0);
		UPCGNode* FlatPre = MakeSlopeBand(Graph, CandF, TEXT("InsideFilter"), 0.86f, 1.0f, -600, 0);
		UPCGNode* Flat = MakeExcluded(Graph, FlatPre, TEXT("Out"), Excl, -520, 60);

		UPCGNode* Seeds = MakeSampler(Graph, Land, 0.00033f, -1100, 300);
		UPCGNode* SeedsF = MakeWeightFilter(Graph, Seeds, TEXT("Out"), TEXT("OW_Forest"), 0.5, -850, 300);

		UPCGNode* DistNode = nullptr;
		UPCGDistanceSettings* Dist = AddNode<UPCGDistanceSettings>(Graph, DistNode, -300, 100);
		Dist->bSetDensity = true;                  // 0 at seed -> 1 at MaximumDistance
		Dist->MaximumDistance = 4500.0;
		Graph->AddEdge(Flat, TEXT("Out"), DistNode, TEXT("Source"));
		Graph->AddEdge(SeedsF, TEXT("InsideFilter"), DistNode, TEXT("Target"));

		UPCGNode* GroveNode = nullptr;
		UPCGDensityFilterSettings* Grove = AddNode<UPCGDensityFilterSettings>(Graph, GroveNode, -50, 100);
		Grove->LowerBound = 0.0f;
		Grove->UpperBound = 0.55f;                 // keep points near seeds = groves
		Graph->AddEdge(DistNode, TEXT("Out"), GroveNode, TEXT("In"));

		// Kasyanik trees (vendor meshes + OW tintable MIs) with sparse-fir
		// variants from OWCreateTreeVariants. Trees are real-size meshes now,
		// so jitter is modest (the old cones needed 8-28x oversizing).
		// Per-tree variation: wider height jitter, warm/cool tone MIs on the
		// same meshes (weighted so ~half the trees carry a tone shift), and
		// the _A/_B/_C jittered-baldness mesh siblings.
		UPCGNode* Trees = MakeTransform(Graph, GroveNode, TEXT("Out"),
			FVector(1.0, 1.0, 1.0), FVector(1.5, 1.5, 1.7), /*bUniform=*/false,
			FRotator(/*Pitch*/-6.0, /*Yaw*/0.0, /*Roll*/-6.0), FRotator(6.0, 360.0, 6.0), 200, 100,
			/*bAbsoluteRotation=*/true);
		const TCHAR* TreesDir = TEXT("/Game/OWGame/Dev/DressingLab/Trees");
		auto Own = [TreesDir](const TCHAR* Name)
		{
			return FString::Printf(TEXT("%s/%s.%s"), TreesDir, Name, Name);
		};
		SpawnTrees(Graph, Trees, TEXT("Out"), {
			{Own(TEXT("SM_OWBeech")), 22, FString(), TEXT("Beech")},
			{Own(TEXT("SM_OWBeech")), 12, FString(), TEXT("Beech"), TEXT("_ToneWarm")},
			{Own(TEXT("SM_OWBeech")), 8, FString(), TEXT("Beech"), TEXT("_ToneCool")},
			{Own(TEXT("SM_OWBirch")), 14, FString(), TEXT("Birch")},
			{Own(TEXT("SM_OWBirch")), 8, FString(), TEXT("Birch"), TEXT("_ToneWarm")},
			{Own(TEXT("SM_OWBirch")), 6, FString(), TEXT("Birch"), TEXT("_ToneCool")},
			{Own(TEXT("SM_OWFirTree")), 7, FString(), TEXT("FirTree")},
			{Own(TEXT("SM_OWFirTree")), 3, FString(), TEXT("FirTree"), TEXT("_ToneWarm")},
			{Own(TEXT("SM_OWFirTree")), 3, FString(), TEXT("FirTree"), TEXT("_ToneCool")},
			{Own(TEXT("SM_OWFir_TallSparse_A")), 3},
			{Own(TEXT("SM_OWFir_TallSparse_B")), 3},
			{Own(TEXT("SM_OWFir_BareTall_A")), 2},
			{Own(TEXT("SM_OWFir_BareTall_B")), 2},
			{Own(TEXT("SM_OWFir_BareTall_C")), 2},
			{Own(TEXT("SM_OWFir_AncientSparse_A")), 2},
			{Own(TEXT("SM_OWFir_AncientSparse_B")), 1},
			{Own(TEXT("SM_OWFir_BareGiant_A")), 1},
			{Own(TEXT("SM_OWFir_BareGiant_B")), 1},
			{Own(TEXT("SM_OWFir_BareGiant_C")), 1},
			// standing dead firs scattered through the living forest
			{Own(TEXT("SM_OWFir_Dead_A")), 2},
			{Own(TEXT("SM_OWFir_Dead_B")), 1},
		}, 450, 100, /*bCastShadow=*/true, /*bWindWPO=*/true);   // LD4 GT: size classes

		// deadfall: real fallen dead firs (detail pass 2026-07-28 - replaces
		// the cylinder placeholder), laid down, ground-following (additive).
		UPCGNode* Logs = MakeSampler(Graph, Land, 0.0004f, -1100, 600);
		UPCGNode* LogsF = MakeWeightFilter(Graph, Logs, TEXT("Out"), TEXT("OW_Forest"), 0.5, -850, 600);
		UPCGNode* LogsX = MakeExcluded(Graph, LogsF, TEXT("InsideFilter"), Excl, -750, 660);
		UPCGNode* LogsT = MakeTransform(Graph, LogsX, TEXT("Out"),
			FVector(0.5), FVector(0.9), /*bUniform=*/true,
			FRotator(84.0, 0.0, 0.0), FRotator(96.0, 360.0, 0.0), -600, 600);
		MakeSpawner(Graph, LogsT, TEXT("Out"), {
			{Own(TEXT("SM_OWFir_Dead_A")), 2},
			{Own(TEXT("SM_OWFir_Dead_B")), 1},
		}, -350, 600, /*bCastShadow=*/true, /*bWindWPO=*/false, 0, 0, EVegClass::Solid);

		// stumps: upright, sparse, mixed species
		UPCGNode* Stumps = MakeSampler(Graph, Land, 0.0006f, -1100, 800);
		UPCGNode* StumpsF = MakeWeightFilter(Graph, Stumps, TEXT("Out"), TEXT("OW_Forest"), 0.3, -850, 800);
		UPCGNode* StumpsX = MakeExcluded(Graph, StumpsF, TEXT("InsideFilter"), Excl, -750, 860);
		UPCGNode* StumpsT = MakeTransform(Graph, StumpsX, TEXT("Out"),
			FVector(0.8), FVector(1.3), /*bUniform=*/true,
			FRotator(-3.0, 0.0, -3.0), FRotator(3.0, 360.0, 3.0), -600, 800,
			/*bAbsoluteRotation=*/true);
		// AM2: pack stumps join at weight 2, ours stay at 1.
		MakeSpawner(Graph, StumpsT, TEXT("Out"), {
			{Own(TEXT("SM_OWFir_Stump_A")), 1},
			{Own(TEXT("SM_OWFir_Stump_B")), 1},
			{Own(TEXT("SM_OWBeech_Stump_A")), 1},
			{Own(TEXT("SM_OWBeech_Stump_B")), 1},
			{PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_01_Summer")), 2},
			{PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_02_Summer")), 2},
		}, -350, 800, /*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/7000, /*CullEnd=*/9000, EVegClass::Solid);

		// forest-floor boulders: sparse mossless rocks, ground-following
		UPCGNode* Rocks = MakeSampler(Graph, Land, 0.0005f, -1100, 1000);
		UPCGNode* RocksF = MakeWeightFilter(Graph, Rocks, TEXT("Out"), TEXT("OW_Forest"), 0.3, -850, 1000);
		UPCGNode* RocksX = MakeExcluded(Graph, RocksF, TEXT("InsideFilter"), Excl, -750, 1060);
		UPCGNode* RocksT = MakeTransform(Graph, RocksX, TEXT("Out"),
			FVector(0.9), FVector(2.2), /*bUniform=*/true,
			FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -600, 1000);
		MakeSpawner(Graph, RocksT, TEXT("Out"), {
			{PackRock(4), 1}, {PackRock(6), 1}, {PackRock(8), 1},
		}, -350, 1000, /*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::Solid);

		// AM2 ground props: the pack logs are modeled LYING DOWN, so they are
		// a separate ground-following scatter (additive rotation, yaw only) -
		// NOT part of the pitched dead-fir deadfall stream above; both streams
		// coexist (tall fallen firs + mossy ground logs). Logs never cast
		// shadows (grass/prop budget policy - fallen TREES do, pack logs are
		// small props).
		UPCGNode* GLogs = MakeSampler(Graph, Land, 0.0004f, -1100, 1100);
		UPCGNode* GLogsF = MakeWeightFilter(Graph, GLogs, TEXT("Out"), TEXT("OW_Forest"), 0.3, -850, 1100);
		UPCGNode* GLogsX = MakeExcluded(Graph, GLogsF, TEXT("InsideFilter"), Excl, -750, 1160);
		UPCGNode* GLogsT = MakeTransform(Graph, GLogsX, TEXT("Out"),
			FVector(0.9), FVector(1.3), /*bUniform=*/true,
			FRotator(0.0, 0.0, 0.0), FRotator(0.0, 360.0, 0.0), -600, 1100);
		MakeSpawner(Graph, GLogsT, TEXT("Out"), {
			{PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Log_01_Summer")), 1},
			{PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Log_02_Summer")), 1},
		}, -350, 1100, /*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/7000, /*CullEnd=*/9000, EVegClass::Solid);

		// D2.5 species TYPE layers (user paints WHICH forest): pure-species
		// palettes on OW_ForestBeech/Birch/Fir. No grove-seed stage - the
		// brush is the grove. Brush opacity maps to density in two tiers:
		// full sampler above 0.55 weight, ~35% sampler in the 0.15-0.55 band
		// (proportional response approximated with proven node machinery
		// only). Weight-blended paint keeps mixed-vs-type overlap sane: full
		// type paint zeroes OW_Forest in place; partial blends spawn mixed +
		// extra species = a transition zone, by design.
		const TArray<FMeshEntry> BeechPalette = {
			{Own(TEXT("SM_OWBeech")), 22, FString(), TEXT("Beech")},
			{Own(TEXT("SM_OWBeech")), 12, FString(), TEXT("Beech"), TEXT("_ToneWarm")},
			{Own(TEXT("SM_OWBeech")), 8, FString(), TEXT("Beech"), TEXT("_ToneCool")},
		};
		const TArray<FMeshEntry> BirchPalette = {
			{Own(TEXT("SM_OWBirch")), 14, FString(), TEXT("Birch")},
			{Own(TEXT("SM_OWBirch")), 8, FString(), TEXT("Birch"), TEXT("_ToneWarm")},
			{Own(TEXT("SM_OWBirch")), 6, FString(), TEXT("Birch"), TEXT("_ToneCool")},
			{Own(TEXT("SM_OWBirch_Sparse_A")), 4},
			{Own(TEXT("SM_OWBirch_Sparse_B")), 4},
		};
		const TArray<FMeshEntry> FirPalette = {
			{Own(TEXT("SM_OWFirTree")), 14, FString(), TEXT("FirTree")},
			{Own(TEXT("SM_OWFirTree")), 6, FString(), TEXT("FirTree"), TEXT("_ToneWarm")},
			{Own(TEXT("SM_OWFirTree")), 6, FString(), TEXT("FirTree"), TEXT("_ToneCool")},
			{Own(TEXT("SM_OWFir_TallSparse_A")), 4},
			{Own(TEXT("SM_OWFir_TallSparse_B")), 4},
			{Own(TEXT("SM_OWFir_BareTall_A")), 3},
			{Own(TEXT("SM_OWFir_BareTall_B")), 3},
			{Own(TEXT("SM_OWFir_BareTall_C")), 3},
			{Own(TEXT("SM_OWFir_AncientSparse_A")), 2},
			{Own(TEXT("SM_OWFir_AncientSparse_B")), 2},
			{Own(TEXT("SM_OWFir_BareGiant_A")), 1},
			{Own(TEXT("SM_OWFir_BareGiant_B")), 1},
			{Own(TEXT("SM_OWFir_BareGiant_C")), 1},
			{Own(TEXT("SM_OWFir_Dead_A")), 2},
			{Own(TEXT("SM_OWFir_Dead_B")), 1},
		};
		// Pack-oak type layer (user 2026-07-28): pure ANGRY MESH oaks wearing
		// their own pack materials (no MI overrides - mixing the pack style
		// into the painterly palettes stays a user decision, see the AM5
		// birch face-off flag). Ivy variants at low weight for variety.
		auto Oak = [](const TCHAR* Name)
		{
			return PackMesh(TEXT("Trees/Trees_Summer"), Name);
		};
		// MF1 shadow budget (2026-07-28): MF0 attribution measured oak Shadow
		// Depths at 13.7ms avg (29.5 -> 11.7ms GPU with sg.ShadowQuality 0) -
		// only the three biggest oak variants (01/02/03 + ivy twins) keep
		// cast-shadow; the smaller half of the palette goes shadowless.
		const TArray<FMeshEntry> OakPalette = {
			{Oak(TEXT("SM_OakTree_01_Summer")), 2},
			{Oak(TEXT("SM_OakTree_02_Summer")), 2},
			{Oak(TEXT("SM_OakTree_03_Summer")), 2},
			{Oak(TEXT("SM_OakTree_04_Summer")), 2, FString(), FString(), FString(), 0},
			{Oak(TEXT("SM_OakTree_05_Summer")), 2, FString(), FString(), FString(), 0},
			{Oak(TEXT("SM_OakTree_06_Summer")), 2, FString(), FString(), FString(), 0},
			{Oak(TEXT("SM_OakTree_07_Summer")), 2, FString(), FString(), FString(), 0},
			{Oak(TEXT("SM_OakTree_01_Summer_Ivy")), 1},
			{Oak(TEXT("SM_OakTree_02_Summer_Ivy")), 1},
			{Oak(TEXT("SM_OakTree_04_Summer_Ivy")), 1, FString(), FString(), FString(), 0},
		};

		// bFirStumps: fir forests get fir stumps, deciduous forests beech
		// stumps (fallen dead firs are generic enough to share).
		// bPackForest: pure pack-tree forests get pack stumps + lying-down
		// pack ground logs INSTEAD of the pitched painterly fir deadfall
		// (fir corpses in a pack-oak wood would be a style seam).
		// DensityScale multiplies every tier sampler: broad pack oak
		// canopies close over at half painterly-forest spacing, and the
		// full ladder tanked frames (user 2026-07-28).
		struct FTypeLayer
		{
			FName Layer;
			const TArray<FMeshEntry>* Palette;
			bool bFirStumps;
			bool bPackForest;
			float DensityScale;
		};
		// Oak 0.35: 0.5 still tanked frames (user 2026-07-28). Live knob:
		// Scripts/ClaudeTuneMeadowLook.py oak_density_scale - keep in sync.
		const FTypeLayer TypeLayers[] = {
			{ TEXT("OW_ForestBeech"), &BeechPalette, false, false, 1.0f },
			{ TEXT("OW_ForestBirch"), &BirchPalette, false, false, 1.0f },
			{ TEXT("OW_ForestFir"), &FirPalette, true, false, 1.0f },
			{ TEXT("OW_ForestOak"), &OakPalette, false, true, 0.35f },
		};
		// Brush-opacity density ladder (heavy tier added on user request
		// 2026-07-28 "even higher density": max-strength paint doubles the
		// standard forest density). Hi < 0 = open-ended top tier.
		struct FDensityTier { double Lo; double Hi; float Sampler; };
		const FDensityTier Tiers[] = {
			{ 0.85, -1.0, 0.02f },     // heavy: 2x forest density
			{ 0.55, 0.85, 0.01f },     // dense: standard forest density
			{ 0.15, 0.55, 0.0035f },   // sparse: ~35% scatter
		};
		int32 Y = 1200;
		for (const FTypeLayer& Type : TypeLayers)
		{
			// Pack trees are authored at display size - the painterly
			// size-up jitter (to 1.5/1.7) inflated canopy overdraw on oaks,
			// so pack forests get a gentler spread around 1.0.
			const FVector TreeScaleMin = Type.bPackForest
				? FVector(0.9, 0.9, 0.9) : FVector(1.0, 1.0, 1.0);
			const FVector TreeScaleMax = Type.bPackForest
				? FVector(1.3, 1.3, 1.4) : FVector(1.5, 1.5, 1.7);
			int32 TierY = Y;
			for (const FDensityTier& Tier : Tiers)
			{
				UPCGNode* Pts = MakeSampler(Graph, Land,
					Tier.Sampler * Type.DensityScale, -1100, TierY);
				UPCGNode* F = (Tier.Hi < 0.0)
					? MakeWeightFilter(Graph, Pts, TEXT("Out"), Type.Layer, Tier.Lo, -850, TierY)
					: MakeWeightBand(Graph, Pts, TEXT("Out"), Type.Layer, Tier.Lo, Tier.Hi, -880, TierY);
				UPCGNode* Slope = MakeSlopeBand(Graph, F, TEXT("InsideFilter"), 0.86f, 1.0f, -600, TierY);
				UPCGNode* NotEx = MakeExcluded(Graph, Slope, TEXT("Out"), Excl, -320, TierY + 60);
				UPCGNode* Xf = MakeTransform(Graph, NotEx, TEXT("Out"),
					TreeScaleMin, TreeScaleMax, /*bUniform=*/false,
					FRotator(-6.0, 0.0, -6.0), FRotator(6.0, 360.0, 6.0), -60, TierY,
					/*bAbsoluteRotation=*/true);
				// MF1 cull table: pack oaks 200m/250m per-instance culls;
				// painterly Nanite trees uncapped (silhouette trees).
				SpawnTrees(Graph, Xf, TEXT("Out"), *Type.Palette, 200, TierY,
					/*bCastShadow=*/true, /*bWindWPO=*/true,
					Type.bPackForest ? 20000 : 0, Type.bPackForest ? 25000 : 0);   // LD4 GT: size classes
				TierY += 300;
			}

			// type deadfall, same recipe as the mixed stream - except pack
			// forests, which scatter the pack's lying-down ground logs
			// (additive ground-following, yaw only, no shadows) instead.
			UPCGNode* TLogs = MakeSampler(Graph, Land, 0.0004f, -1100, TierY);
			UPCGNode* TLogsF = MakeWeightFilter(Graph, TLogs, TEXT("Out"), Type.Layer, 0.3, -850, TierY);
			UPCGNode* TLogsX = MakeExcluded(Graph, TLogsF, TEXT("InsideFilter"), Excl, -750, TierY + 60);
			if (Type.bPackForest)
			{
				UPCGNode* TLogsT = MakeTransform(Graph, TLogsX, TEXT("Out"),
					FVector(0.9), FVector(1.3), /*bUniform=*/true,
					FRotator(0.0, 0.0, 0.0), FRotator(0.0, 360.0, 0.0), -600, TierY);
				MakeSpawner(Graph, TLogsT, TEXT("Out"), {
					{PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Log_01_Summer")), 1},
					{PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Log_02_Summer")), 1},
				}, -350, TierY, /*bCastShadow=*/false, /*bWindWPO=*/false,
					/*CullStart=*/7000, /*CullEnd=*/9000, EVegClass::Solid);
			}
			else
			{
				UPCGNode* TLogsT = MakeTransform(Graph, TLogsX, TEXT("Out"),
					FVector(0.5), FVector(0.9), /*bUniform=*/true,
					FRotator(84.0, 0.0, 0.0), FRotator(96.0, 360.0, 0.0), -600, TierY);
				MakeSpawner(Graph, TLogsT, TEXT("Out"), {
					{Own(TEXT("SM_OWFir_Dead_A")), 2},
					{Own(TEXT("SM_OWFir_Dead_B")), 1},
				}, -350, TierY, /*bCastShadow=*/true, /*bWindWPO=*/false, 0, 0, EVegClass::Solid);
			}

			UPCGNode* TStumps = MakeSampler(Graph, Land, 0.0006f, -1100, TierY + 300);
			UPCGNode* TStumpsF = MakeWeightFilter(Graph, TStumps, TEXT("Out"), Type.Layer, 0.3, -850, TierY + 300);
			UPCGNode* TStumpsX = MakeExcluded(Graph, TStumpsF, TEXT("InsideFilter"), Excl, -750, TierY + 360);
			UPCGNode* TStumpsT = MakeTransform(Graph, TStumpsX, TEXT("Out"),
				FVector(0.8), FVector(1.3), /*bUniform=*/true,
				FRotator(-3.0, 0.0, -3.0), FRotator(3.0, 360.0, 3.0), -600, TierY + 300,
				/*bAbsoluteRotation=*/true);
			// AM2: pack stumps at weight 2 here too, ours stay at 1. Pack
			// forests carry pack stumps ONLY.
			MakeSpawner(Graph, TStumpsT, TEXT("Out"),
				Type.bPackForest
					? TArray<FMeshEntry>{ {PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_01_Summer")), 1},
					                      {PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_02_Summer")), 1} }
					: Type.bFirStumps
					? TArray<FMeshEntry>{ {Own(TEXT("SM_OWFir_Stump_A")), 1},
					                      {Own(TEXT("SM_OWFir_Stump_B")), 1},
					                      {PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_01_Summer")), 2},
					                      {PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_02_Summer")), 2} }
					: TArray<FMeshEntry>{ {Own(TEXT("SM_OWBeech_Stump_A")), 1},
					                      {Own(TEXT("SM_OWBeech_Stump_B")), 1},
					                      {PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_01_Summer")), 2},
					                      {PackMesh(TEXT("Props/Props_Summer"), TEXT("SM_Stump_02_Summer")), 2} },
				-350, TierY + 300, /*bCastShadow=*/false, /*bWindWPO=*/false,
				/*CullStart=*/7000, /*CullEnd=*/9000, EVegClass::Solid);

			Y += 2000;
		}

		// LD4 GT: forest understorey - soft brush under every forest layer's weight above 0.5: bushes at 0.02/m2
		// (0.7-1.3) and cover plants at 0.04/m2, each through the exclusions and the 0.8-1.0 slope band.
		if (GVariantGT)
		{
			const TCHAR* ForestLayers[] = {
				TEXT("OW_Forest"), TEXT("OW_ForestBeech"), TEXT("OW_ForestBirch"), TEXT("OW_ForestFir"), TEXT("OW_ForestOak") };
			int32 UY = Y;
			int32 Seed = 1901;
			for (const TCHAR* Layer : ForestLayers)
			{
				MakeSoftStream(Graph, Land, Excl, Layer, 0.5, -1.0, 0.02f, 0.7, 1.3, /*bSizeClass=*/false,
					BushEntries(), EVegClass::SoftBrush, /*bCastShadow=*/false, /*bWindWPO=*/true,
					BushCullStart, BushCullEnd, Seed++, UY);
				MakeSoftStream(Graph, Land, Excl, Layer, 0.5, -1.0, 0.04f, CoverScaleLo, CoverScaleHi, /*bSizeClass=*/false,
					CoverPlantEntries(), EVegClass::SoftBrush, /*bCastShadow=*/false, /*bWindWPO=*/true,
					CoverCullStart, CoverCullEnd, Seed++, UY + 300);
				UY += 600;
			}
		}

		return SaveAssetPackage(Graph);
	}

	bool BuildMeadowGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(GraphPath(TEXT("Meadow")), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };
		Excl.Append(MakeRoadExclusions(Graph, Land));
		UPCGNode* Pts = MakeSampler(Graph, Land, 0.0015f, -1100, 0);
		UPCGNode* PtsF = MakeWeightFilter(Graph, Pts, TEXT("Out"), TEXT("OW_Meadow"), 0.5, -850, 0);
		UPCGNode* Flat = MakeSlopeBand(Graph, PtsF, TEXT("InsideFilter"), 0.7f, 1.0f, -600, 0);
		UPCGNode* FlatX = MakeExcluded(Graph, Flat, TEXT("Out"), Excl, -350, 60);
		UPCGNode* Xf = MakeTransform(Graph, FlatX, TEXT("Out"),
			FVector(0.25), FVector(0.7), /*bUniform=*/true,
			FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -100, 0);
		// AM2: pack rocks replace the MW stones (scale 0.25-0.7 unchanged).
		MakeSpawner(Graph, Xf, TEXT("Out"),
			{ {PackRock(1), 1}, {PackRock(2), 1}, {PackRock(3), 1} }, 150, 0,
			/*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::Solid);

		// bushes: pack birch bushes replace the OW blob shrubs (AM2; the
		// SM_OWBush_* meshes stay on disk as stock). Upright with slight
		// lean, gentle sway (bWindWPO), no shadows. 0.0004 = perf cut
		// 2026-07-28; live knob in ClaudeTuneMeadowLook.py - keep in sync.
		// MF2: each meadow TYPE gets its own bush sampler - lush reads as
		// shrubby hero meadow (0.0006), dry is near-bare scrubland
		// (0.00008). Same palette/transform recipe, different densities;
		// the tune script rank-matches the three samplers by saved density
		// (lush > standard > dry) - keep the ordering distinct.
		struct FBushStream { const TCHAR* Layer; float Sampler; int32 Y; };
		const FBushStream BushStreams[] = {
			{ TEXT("OW_Meadow"),     0.0004f,  400 },
			{ TEXT("OW_MeadowLush"), 0.0006f,  700 },
			{ TEXT("OW_MeadowDry"),  0.00008f, 1000 },
		};
		for (const FBushStream& Stream : BushStreams)
		{
			UPCGNode* Bush = MakeSampler(Graph, Land, Stream.Sampler, -1100, Stream.Y);
			UPCGNode* BushF = MakeWeightFilter(Graph, Bush, TEXT("Out"), Stream.Layer, 0.3, -850, Stream.Y);
			UPCGNode* BushX = MakeExcluded(Graph, BushF, TEXT("InsideFilter"), Excl, -650, Stream.Y + 60);
			UPCGNode* BushT = MakeTransform(Graph, BushX, TEXT("Out"),
				FVector(0.8), FVector(1.4), /*bUniform=*/true,
				FRotator(-4.0, 0.0, -4.0), FRotator(4.0, 360.0, 4.0), -300, Stream.Y,
				/*bAbsoluteRotation=*/true);
			MakeSpawner(Graph, BushT, TEXT("Out"), {
				{SoftPackMesh(TEXT("Trees/Trees_Summer"), TEXT("SM_BirchBush_01_Summer")), 1},
				{SoftPackMesh(TEXT("Trees/Trees_Summer"), TEXT("SM_BirchBush_02_Summer")), 1},
				{SoftPackMesh(TEXT("Trees/Trees_Summer"), TEXT("SM_BirchBush_03_Summer")), 1},
				{SoftPackMesh(TEXT("Trees/Trees_Summer"), TEXT("SM_BirchBush_04_Summer")), 1},
				{SoftPackMesh(TEXT("Trees/Trees_Summer"), TEXT("SM_BirchBush_05_Summer")), 1},
			}, -50, Stream.Y, /*bCastShadow=*/false, /*bWindWPO=*/true,
				/*CullStart=*/10000, /*CullEnd=*/13000, EVegClass::SoftBrush);
		}

		// MF2: dry meadow reads as scrubland - it also gets the small-rock
		// scatter at the standard meadow recipe, filtered on OW_MeadowDry.
		UPCGNode* DryPts = MakeSampler(Graph, Land, 0.0015f, -1100, 1300);
		UPCGNode* DryF = MakeWeightFilter(Graph, DryPts, TEXT("Out"), TEXT("OW_MeadowDry"), 0.5, -850, 1300);
		UPCGNode* DryFlat = MakeSlopeBand(Graph, DryF, TEXT("InsideFilter"), 0.7f, 1.0f, -600, 1300);
		UPCGNode* DryX = MakeExcluded(Graph, DryFlat, TEXT("Out"), Excl, -350, 1360);
		UPCGNode* DryXf = MakeTransform(Graph, DryX, TEXT("Out"),
			FVector(0.25), FVector(0.7), /*bUniform=*/true,
			FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -100, 1300);
		MakeSpawner(Graph, DryXf, TEXT("Out"),
			{ {PackRock(1), 1}, {PackRock(2), 1}, {PackRock(3), 1} }, 150, 1300,
			/*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::Solid);

		// RV3 (Docs/RVTGroundRoundPlan.md): GroundCoverRVT dab feathering.
		// Flat RVT-tinted cards that melt grass edges into the ground -
		// they REQUIRE the RVT to be live (RV0-2) or they render untinted.
		// Standard + lush meadows only; dry reads as scrubland (rocks carry
		// it). Ground-following additive yaw like the pack ground logs.
		// Live knob: ClaudeTuneMeadowLook.py dab_points_per_m2 - in sync.
		struct FDabStream { const TCHAR* Layer; int32 Y; };
		const FDabStream DabStreams[] = {
			{ TEXT("OW_Meadow"),     1600 },
			{ TEXT("OW_MeadowLush"), 1900 },
		};
		for (const FDabStream& Dab : DabStreams)
		{
			UPCGNode* Pts2 = MakeSampler(Graph, Land, 0.0003f, -1100, Dab.Y);
			UPCGNode* F = MakeWeightFilter(Graph, Pts2, TEXT("Out"), Dab.Layer, 0.3, -850, Dab.Y);
			UPCGNode* X = MakeExcluded(Graph, F, TEXT("InsideFilter"), Excl, -650, Dab.Y + 60);
			UPCGNode* T = MakeTransform(Graph, X, TEXT("Out"),
				FVector(0.8), FVector(1.4), /*bUniform=*/true,
				FRotator(0.0, 0.0, 0.0), FRotator(0.0, 360.0, 0.0), -300, Dab.Y);
			MakeSpawner(Graph, T, TEXT("Out"), {
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_01")), 2},
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_02")), 2},
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_03")), 2},
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_04")), 2},
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_01")), 1},
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_03")), 1},
				{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_05")), 1},
			}, -50, Dab.Y, /*bCastShadow=*/false, /*bWindWPO=*/false,
				/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::None);
		}
		return SaveAssetPackage(Graph);
	}

	bool BuildScreeGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(GraphPath(TEXT("Scree")), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };
		Excl.Append(MakeRoadExclusions(Graph, Land));
		UPCGNode* Pts = MakeSampler(Graph, Land, 0.008f, -1100, 0);

		// AM2: pack rocks 01..08 replace the MW stones in branches A/B.
		auto TumbleAndSpawn = [Graph](UPCGNode* Prev, const TCHAR* PrevPin, int32 Y)
		{
			UPCGNode* Xf = MakeTransform(Graph, Prev, PrevPin,
				FVector(0.5), FVector(2.2), /*bUniform=*/true,
				FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -300, Y);
			TArray<FMeshEntry> Entries;
			for (int32 Rock = 1; Rock <= 8; ++Rock) { Entries.Add({PackRock(Rock), 1}); }
			MakeSpawner(Graph, Xf, TEXT("Out"), Entries, -50, Y,
				/*bCastShadow=*/false, /*bWindWPO=*/false,
				/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::Solid);
		};

		// branch A: painted scree
		UPCGNode* AF = MakeWeightFilter(Graph, Pts, TEXT("Out"), TEXT("OW_Scree"), 0.3, -850, 0);
		UPCGNode* AX = MakeExcluded(Graph, AF, TEXT("InsideFilter"), Excl, -650, 60);
		TumbleAndSpawn(AX, TEXT("Out"), 0);

		// branch B: any steep face (39-65 deg), painted or not
		UPCGNode* BSlope = MakeSlopeBand(Graph, Pts, TEXT("Out"), 0.42f, 0.78f, -850, 350);
		UPCGNode* BX = MakeExcluded(Graph, BSlope, TEXT("Out"), Excl, -650, 410);
		TumbleAndSpawn(BX, TEXT("Out"), 350);

		// branch C (detail pass 2026-07-28): CLIFF faces (60-78 deg) get
		// sparse LARGE embedded boulders - big rocks cast shadows or float.
		UPCGNode* CliffPts = MakeSampler(Graph, Land, 0.0008f, -1100, 700);
		UPCGNode* CSlope = MakeSlopeBand(Graph, CliffPts, TEXT("Out"), 0.20f, 0.50f, -850, 700);
		UPCGNode* CX = MakeExcluded(Graph, CSlope, TEXT("Out"), Excl, -650, 760);
		UPCGNode* CXf = MakeTransform(Graph, CX, TEXT("Out"),
			FVector(3.5), FVector(7.5), /*bUniform=*/true,
			FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -300, 700);
		// AM2: the four big cliff rocks (09..12) replace the MW stones here.
		TArray<FMeshEntry> BigRocks;
		for (int32 Rock = 9; Rock <= 12; ++Rock) { BigRocks.Add({PackRock(Rock), 1}); }
		MakeSpawner(Graph, CXf, TEXT("Out"), BigRocks, -50, 700, /*bCastShadow=*/true, /*bWindWPO=*/false, 0, 0, EVegClass::Solid);

		return SaveAssetPackage(Graph);
	}

	// RL2 v2 (Docs/RoadLookRoundPlan.md, user 2026-07-29 "different roads
	// get different things"): per-TYPE dressing keyed off which road BP
	// the user drags. BP_OWRoad_Dusty/Gravel are sibling DUPLICATES of
	// BP_OWRoad (ClaudeCreateOWRoadBP.py) - NOT children, because the
	// ByClass getter is IsA-based (PCGActorSelector.cpp:100) and child
	// classes would also match the parent getter = double dressing.
	// Recipes per RoadDressingRoundPlan RD3: mud = churned verge dabs +
	// occasional on-road planks; dusty = dry-grass verge, almost no dabs;
	// gravel = double stones, nothing else.
	// SPLINE-ANCHORED (2026-07-29 rework, paid): the first version sampled
	// the WHOLE landscape and band-filtered by Distance-to-road - that
	// design is FAIL-OPEN: when the Distance node's Target pin resolves
	// empty it passes sources through untouched (PCGDistance.cpp:195,
	// bOutputToAttribute-gated) and the world gets dressed instead of the
	// road. Points are now GENERATED FROM the road spline (center-line
	// samples -> local lateral offset -> project to landscape), so every
	// failure mode yields NOTHING, never everything.
	// Spacing = one point per SpacingCm of road PER SIDE (0 = no stream);
	// per-token spacings kept DISTINCT - the tune script rank-matches
	// spline samplers by saved increment (bush-stream doctrine).
	// Fences stay HAND-PLACED by the user (hand-authored boundary).
	struct FRoadTypeRecipe
	{
		const TCHAR* ClassPath;
		float StoneSpacingCm;      // verge band 250-545cm, SM_Rock_02/04
		float TuftSpacingCm;       // verge band, SM_Grass_01_Summer_03
		float OnRoadSpacingCm;     // +/-150cm on the surface, GroundCoverRVT
		float VergeDabSpacingCm;   // verge band, GroundCoverRVT (churned mud)
		float OnRoadRockSpacingCm; // slightly-sunk GroundCoverRVT_Rock cards ON the bed
	};
	constexpr FRoadTypeRecipe RoadRecipes[] = {
		{ TEXT("/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad.BP_OWRoad_C"),
			700.0f, 250.0f, 1200.0f, 500.0f, 900.0f },
		{ TEXT("/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad_Dusty.BP_OWRoad_Dusty_C"),
			1000.0f, 80.0f, 2500.0f, 0.0f, 1800.0f },
		{ TEXT("/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad_Gravel.BP_OWRoad_Gravel_C"),
			350.0f, 0.0f, 0.0f, 0.0f, 400.0f },
	};

	UPCGNode* MakeRoadSplineGetter(UPCGGraph* Graph, UClass* RoadClass, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGGetSplineSettings* S = AddNode<UPCGGetSplineSettings>(Graph, Node, -1400, Y);
		S->ActorSelector.ActorFilter = EPCGActorFilter::AllWorldActors;
		S->ActorSelector.ActorSelection = EPCGActorSelection::ByClass;
		// ByClass pitfall: PostLoad's default-class fallback fires only for
		// non-ByClass selectors - the class MUST be set explicitly.
		S->ActorSelector.ActorSelectionClass = RoadClass;
		S->ActorSelector.bSelectMultiple = true;
		S->ActorSelector.bMustOverlapSelf = false;
		return Node;
	}

	// Center-line points along every road spline, one per IncrementCm,
	// jittered along the spline by up to half an increment (dressing wants
	// the hand-scattered read; exclusion corridors pass bJitter=false for
	// gap-free deterministic coverage).
	UPCGNode* MakeSplineCenterSampler(UPCGGraph* Graph, UPCGNode* Splines,
		float IncrementCm, int32 X, int32 Y, bool bJitter = true)
	{
		UPCGNode* Node = nullptr;
		UPCGSplineSamplerSettings* S = AddNode<UPCGSplineSamplerSettings>(Graph, Node, X, Y);
		S->SamplerParams.Dimension = EPCGSplineSamplingDimension::OnSpline;
		S->SamplerParams.Mode = EPCGSplineSamplingMode::Distance;
		S->SamplerParams.DistanceIncrement = IncrementCm;
		S->SamplerParams.MaxRandomOffsetNormalized = bJitter ? 1.0f : 0.0f;
		S->SamplerParams.bUnbounded = true;
		Graph->AddEdge(Splines, TEXT("Out"), Node, TEXT("Spline"));
		return Node;
	}

	// Lateral local-space offset off the center line: spline-sampled
	// points face along the spline (transform forward = tangent), so a
	// LOCAL +/-Y offset (bAbsoluteOffset=false) is "toward the road edge".
	UPCGNode* MakeLateralOffset(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		float MinY, float MaxY, int32 X, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGTransformPointsSettings* S = AddNode<UPCGTransformPointsSettings>(Graph, Node, X, Y);
		S->OffsetMin = FVector(0.0, MinY, 0.0);
		S->OffsetMax = FVector(0.0, MaxY, 0.0);
		S->bAbsoluteOffset = false;
		Graph->AddEdge(Prev, PrevPin, Node, TEXT("In"));
		return Node;
	}

	// Drop offset points onto the landscape (positions + landscape-normal
	// rotations, FPCGProjectionParams defaults). Caller wires the In
	// edge(s) - both verge sides feed one projection node.
	UPCGNode* MakeProjectToLandscape(UPCGGraph* Graph, UPCGNode* Land, int32 X, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGProjectionSettings* S = AddNode<UPCGProjectionSettings>(Graph, Node, X, Y);
		S->bForceCollapseToPoint = true;
		Graph->AddEdge(Land, TEXT("Out"), Node, TEXT("Projection Target"));
		return Node;
	}

	// Biome-graph road exclusion (user 2026-07-30: trees grew from the road
	// bed). The road BPs canNOT simply carry the OWDressing.Exclude tag -
	// the road graph's own on-road plank stream runs through MakeExcluded
	// too and would self-erase. Instead each biome graph gets per-road-class
	// corridor data: unjittered center-line samples with Set bounds of
	// half-length 200 (= the sample increment, so coverage is contiguous) x
	// half-width 200 (= the road half-width, no margin - user 2026-07-30:
	// exclude the road bed itself only, verge-adjacent spawns are fine) x
	// half-height 500 (samples sit at spline height, the proud road mesh
	// rides ~20cm over terrain; roads follow terrain so a short band is
	// enough). Spline-sampled points face along the tangent, so local Y IS
	// across the road. SLOPE FIX (2026-07-30 same day): corridor samples
	// are PROJECTED to the landscape before the bounds inflate - at spline
	// height the corridor could chord above the terrain on slopes and slip
	// past the +/-500 Z band while trees spawned on the bed below. Every
	// failure mode is a no-op for dressing: no roads in the level or a
	// missing BP class yields empty Differences inputs = the D3
	// pass-through, exactly like the tag getter.
	constexpr float RoadExclusionSampleCm = 200.0f;
	const FVector RoadExclusionHalfExtents(200.0, 200.0, 500.0);

	TArray<UPCGNode*> MakeRoadExclusions(UPCGGraph* Graph, UPCGNode* Land)
	{
		TArray<UPCGNode*> Nodes;
		int32 Y = 1500;
		for (const FRoadTypeRecipe& Recipe : RoadRecipes)
		{
			UClass* RoadClass = LoadClass<AActor>(nullptr, Recipe.ClassPath);
			if (!RoadClass)
			{
				UE_LOG(LogOWCreateBiomePCG, Warning,
					TEXT("road exclusion: class %s missing - biome graph "
					     "builds without that road type."), Recipe.ClassPath);
				continue;
			}
			UPCGNode* Splines = MakeRoadSplineGetter(Graph, RoadClass, Y);
			UPCGNode* Center = MakeSplineCenterSampler(Graph, Splines,
				RoadExclusionSampleCm, -1150, Y, /*bJitter=*/false);
			UPCGNode* Proj = MakeProjectToLandscape(Graph, Land, -1050, Y);
			Graph->AddEdge(Center, TEXT("Out"), Proj, TEXT("In"));
			UPCGNode* BoundsNode = nullptr;
			UPCGBoundsModifierSettings* Bounds =
				AddNode<UPCGBoundsModifierSettings>(Graph, BoundsNode, -950, Y);
			Bounds->Mode = EPCGBoundsModifierMode::Set;
			Bounds->BoundsMin = -RoadExclusionHalfExtents;
			Bounds->BoundsMax = RoadExclusionHalfExtents;
			Graph->AddEdge(Proj, TEXT("Out"), BoundsNode, TEXT("In"));
			Nodes.Add(BoundsNode);
			Y += 150;
		}
		return Nodes;
	}

	// SPLINE SCALE LEAKS INTO POINT SCALE (paid 2026-08-02). Some splines carry
	// authored data in their control-point scale (a width/depth pair measured
	// at (2048, 150, 1) on every point); road and cliff splines are (1,1,1),
	// which is why a chain can behave for years and then blow up the first
	// time it is pointed at a spline that is not unit scale. The PCG spline
	// sampler bakes that scale into every sampled point, and TWO things
	// downstream read it:
	//   1. UPCGTransformPointsSettings MULTIPLIES by default (bAbsoluteScale is
	//      false, PCGTransformPoints.cpp:232) - a 0.9-1.3 grass tuft spawned at
	//      measured scale 1855-2843.
	//   2. A point's WORLD bounds are its local bounds TIMES its scale - so a
	//      +/-1100 corridor became +/-2,252,800cm (22km) and an exclusion built
	//      on it erased biome dressing across the whole map. That one is
	//      invisible in a screenshot; it only shows up as "why is there no
	//      forest anywhere".
	// Fix: flatten spline samples back to unit scale IMMEDIATELY after
	// sampling, before anything reads scale or bounds. Offsets are unaffected
	// either way - a local offset is rotated but NOT scaled
	// (PCGTransformPoints.cpp:213 builds its transform from rotation only).
	// If the scale is real data, read it as an attribute first; do not simply
	// stop normalising.
	UPCGNode* MakeUnitScale(UPCGGraph* Graph, UPCGNode* Prev, const TCHAR* PrevPin,
		int32 X, int32 Y)
	{
		UPCGNode* Node = nullptr;
		UPCGTransformPointsSettings* S = AddNode<UPCGTransformPointsSettings>(Graph, Node, X, Y);
		S->ScaleMin = FVector(1.0);
		S->ScaleMax = FVector(1.0);
		S->bAbsoluteScale = true;  // SET the scale, never multiply the spline's
		Graph->AddEdge(Prev, PrevPin, Node, TEXT("In"));
		return Node;
	}

	bool BuildRoadGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(FString(AssetDir) + TEXT("/PCG_OWRoad"), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		// Tag getter ONLY - never the road corridors: the on-road plank
		// stream lives inside its own corridor and would self-erase.
		const TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };

		// Road geometry: width 400 -> half-width 200; verge band 250-545cm
		// from the center line, both sides. Densities are per m2 of the
		// WHOLE landscape pre-filter; in-band density is the same number.
		// Live knobs: ClaudeTuneMeadowLook.py road_* - keep in sync.
		// User verdict 2026-07-29 ("planks should sit across it, like in
		// the demo"): the on-road stream is PLANKS ONLY, laid ACROSS the
		// path - the churned verge edge carries the small rocks. Planks'
		// long axis is X (ClaudeProbePlankAxisReport.json), and
		// spline-sampled points face along the tangent, so across = +90
		// yaw, jittered +/-12 for the hand-laid read.
		constexpr float PlankCrossYawDeg = 90.0f;
		const TArray<FMeshEntry> PlankPalette = {
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_01")), 1},
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_02")), 1},
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_03")), 1},
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Plank_04")), 1},
		};
		const TArray<FMeshEntry> RockDabPalette = {
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_01")), 1},
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_03")), 1},
			{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_05")), 1},
		};

		// Ground-following flat rock cards: additive yaw only.
		auto SpawnRockDabs = [&](UPCGNode* Band, int32 Y)
		{
			UPCGNode* T = MakeTransform(Graph, Band, TEXT("Out"),
				FVector(0.8), FVector(1.2), /*bUniform=*/true,
				FRotator(0.0, 0.0, 0.0), FRotator(0.0, 360.0, 0.0), -100, Y);
			MakeSpawner(Graph, T, TEXT("Out"), RockDabPalette, 150, Y,
				/*bCastShadow=*/false, /*bWindWPO=*/false,
				/*CullStart=*/8000, /*CullEnd=*/10000);
		};

		// Verge band 250-545cm off center (road half-width 200 + margin);
		// on-road accents stay within +/-150cm (inside the dissolve edge).
		// SLOPE FIX (user 2026-07-30, two rounds): (1) spline height is
		// NOT the road surface on slopes - the spline chords ABOVE the
		// terrain between control points, so on-road streams PROJECT to
		// the landscape like the verge does. (2) There is NO proud road
		// mesh in the display path - BP_OWRoad draws into the RVT and the
		// LANDSCAPE displays the composite ("roads melt into the ground",
		// ClaudeCreateOWRoadBP.py recipe), so the terrain surface IS the
		// road surface. A +18..+22 "proud bed" lift floated everything by
		// exactly that much (user round 2). Correct anchoring = the meadow
		// dab recipe: projected, ZERO lift for planks, cards sunk -8..-2
		// so they just poke out of the bed.
		auto VergeChain = [&](UPCGNode* Roads, float SpacingCm, int32 StreamY) -> UPCGNode*
		{
			UPCGNode* Center = MakeSplineCenterSampler(Graph, Roads, SpacingCm, -1100, StreamY);
			UPCGNode* Right = MakeLateralOffset(Graph, Center, TEXT("Out"), 250.0f, 545.0f, -880, StreamY);
			UPCGNode* Left = MakeLateralOffset(Graph, Center, TEXT("Out"), -545.0f, -250.0f, -880, StreamY + 80);
			UPCGNode* Proj = MakeProjectToLandscape(Graph, Land, -660, StreamY);
			Graph->AddEdge(Right, TEXT("Out"), Proj, TEXT("In"));
			Graph->AddEdge(Left, TEXT("Out"), Proj, TEXT("In"));
			return MakeExcluded(Graph, Proj, TEXT("Out"), Excl, -440, StreamY + 60);
		};

		int32 Y = 0;
		for (const FRoadTypeRecipe& Recipe : RoadRecipes)
		{
			UClass* RoadClass = LoadClass<AActor>(nullptr, Recipe.ClassPath);
			if (!RoadClass)
			{
				UE_LOG(LogOWCreateBiomePCG, Error,
					TEXT("road BP class failed to load (%s) - run "
					     "ClaudeCreateOWRoadBP.py first."), Recipe.ClassPath);
				return false;
			}
			UPCGNode* Roads = MakeRoadSplineGetter(Graph, RoadClass, Y - 300);

			// Verge stones: sparse small pack rocks, tumbled, shadowless.
			if (Recipe.StoneSpacingCm > 0.0f)
			{
				UPCGNode* Stones = VergeChain(Roads, Recipe.StoneSpacingCm, Y);
				UPCGNode* StoneT = MakeTransform(Graph, Stones, TEXT("Out"),
					FVector(0.3), FVector(0.6), /*bUniform=*/true,
					FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -100, Y);
				MakeSpawner(Graph, StoneT, TEXT("Out"), {
					{PackRock(2), 1}, {PackRock(4), 1},
				}, 150, Y, /*bCastShadow=*/false, /*bWindWPO=*/false,
					/*CullStart=*/8000, /*CullEnd=*/10000);
			}

			// Dry tufts in the band: upright, additive yaw, grass budget.
			if (Recipe.TuftSpacingCm > 0.0f)
			{
				UPCGNode* Tufts = VergeChain(Roads, Recipe.TuftSpacingCm, Y + 300);
				UPCGNode* TuftT = MakeTransform(Graph, Tufts, TEXT("Out"),
					FVector(0.7), FVector(1.2), /*bUniform=*/true,
					FRotator(0.0, 0.0, 0.0), FRotator(0.0, 360.0, 0.0), -100, Y + 300);
				MakeSpawner(Graph, TuftT, TEXT("Out"), {
					{PackMesh(TEXT("Grass/Grass_Summer"), TEXT("SM_Grass_01_Summer_03")), 1},
				}, 150, Y + 300, /*bCastShadow=*/false, /*bWindWPO=*/false,
					/*CullStart=*/5000, /*CullEnd=*/6500);
			}

			// On-road planks: laid ACROSS the path near the center line
			// (demo boardwalk-over-mud read), RVT-tinted to the road
			// color. Projected to terrain + lifted to the proud bed
			// (slope fix above).
			if (Recipe.OnRoadSpacingCm > 0.0f)
			{
				UPCGNode* Center = MakeSplineCenterSampler(Graph, Roads, Recipe.OnRoadSpacingCm, -1100, Y + 600);
				UPCGNode* OnRoad = MakeLateralOffset(Graph, Center, TEXT("Out"), -40.0f, 40.0f, -880, Y + 600);
				UPCGNode* OnRoadProj = MakeProjectToLandscape(Graph, Land, -770, Y + 600);
				Graph->AddEdge(OnRoad, TEXT("Out"), OnRoadProj, TEXT("In"));
				UPCGNode* OnRoadX = MakeExcluded(Graph, OnRoadProj, TEXT("Out"), Excl, -660, Y + 660);
				UPCGNode* PlankT = nullptr;
				UPCGTransformPointsSettings* PT =
					AddNode<UPCGTransformPointsSettings>(Graph, PlankT, -100, Y + 600);
				PT->OffsetMin = FVector::ZeroVector;
				PT->OffsetMax = FVector::ZeroVector;
				PT->bAbsoluteOffset = false;
				PT->ScaleMin = FVector(0.9);
				PT->ScaleMax = FVector(1.2);
				PT->bUniformScale = true;
				PT->RotationMin = FRotator(0.0, PlankCrossYawDeg - 12.0, 0.0);
				PT->RotationMax = FRotator(0.0, PlankCrossYawDeg + 12.0, 0.0);
				Graph->AddEdge(OnRoadX, TEXT("Out"), PlankT, TEXT("In"));
				MakeSpawner(Graph, PlankT, TEXT("Out"), PlankPalette, 150, Y + 600,
					/*bCastShadow=*/false, /*bWindWPO=*/false,
					/*CullStart=*/8000, /*CullEnd=*/10000);
			}

			// Churned verge dabs (mud): small rock cards, verge band.
			if (Recipe.VergeDabSpacingCm > 0.0f)
			{
				UPCGNode* Dabs = VergeChain(Roads, Recipe.VergeDabSpacingCm, Y + 900);
				SpawnRockDabs(Dabs, Y + 900);
			}

			// On-road embedded rocks (user 2026-07-30, v2: the SM_Rock_01/03
			// pack rocks read as boulders on the road - screenshot round):
			// the four GroundCoverRVT_Rock cards instead, RVT-tinted to the
			// road color like the planks, projected to the landscape and
			// sunk -8..-2cm below the composite road surface (see the slope
			// fix note above) so they only just poke out. Yaw-only
			// rotation - tumbling flat cards flips them sideways. Lateral
			// +/-170 stays inside the 200 half-width. TOKEN DOCTRINE: this
			// palette (Rocks 01/02/03/04) shares meshes with the mud verge
			// dabs (01/03/05); the tune script matches this stream by the
			// palette-unique "GroundCoverRVT_Rock_04", the verge dabs by
			// "GroundCoverRVT_Rock_05", planks by "GroundCoverRVT_Plank" -
			// keep membership so each token stays unambiguous.
			if (Recipe.OnRoadRockSpacingCm > 0.0f)
			{
				UPCGNode* Center = MakeSplineCenterSampler(Graph, Roads,
					Recipe.OnRoadRockSpacingCm, -1100, Y + 1200);
				UPCGNode* Lateral = MakeLateralOffset(Graph, Center, TEXT("Out"),
					-170.0f, 170.0f, -960, Y + 1200);
				UPCGNode* CardProj = MakeProjectToLandscape(Graph, Land, -900, Y + 1260);
				Graph->AddEdge(Lateral, TEXT("Out"), CardProj, TEXT("In"));
				UPCGNode* Scatter = nullptr;
				UPCGTransformPointsSettings* S =
					AddNode<UPCGTransformPointsSettings>(Graph, Scatter, -880, Y + 1200);
				S->OffsetMin = FVector(0.0, 0.0, -8.0);
				S->OffsetMax = FVector(0.0, 0.0, -2.0);
				S->bAbsoluteOffset = false;
				S->ScaleMin = FVector(0.8);
				S->ScaleMax = FVector(1.2);
				S->bUniformScale = true;
				S->RotationMin = FRotator(0.0, 0.0, 0.0);
				S->RotationMax = FRotator(0.0, 360.0, 0.0);
				Graph->AddEdge(CardProj, TEXT("Out"), Scatter, TEXT("In"));
				UPCGNode* RocksX = MakeExcluded(Graph, Scatter, TEXT("Out"), Excl, -660, Y + 1260);
				MakeSpawner(Graph, RocksX, TEXT("Out"), {
					{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_01")), 1},
					{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_02")), 1},
					{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_03")), 1},
					{PackMesh(TEXT("GroundCoverRVT"), TEXT("SM_GroundCoverRVT_Rock_04")), 1},
				}, -350, Y + 1200, /*bCastShadow=*/false, /*bWindWPO=*/false,
					/*CullStart=*/8000, /*CullEnd=*/10000);
			}

			Y += 1600;
		}

		return SaveAssetPackage(Graph);
	}
	// RC round (user 2026-07-30): spline-authored rock faces. The user
	// draws BP_OWCliffWall splines (bare spline actor,
	// ClaudeCreateOWCliffBP.py); rows generate AT SPLINE HEIGHT by
	// deliberate user choice ("more control than the road") - the spline
	// IS the wall in 3D, so NO landscape projection on the wall rows
	// (only the foot debris grounds). Rows: base giants (Rocks 09-12,
	// deep-sunk), upper course (offset up+back, smaller), rim caps
	// (Rocks 05-08 on top), grounded foot scatter. Spacings DISTINCT for
	// future tune-knob rank matching. Big rows cast shadows, no culls
	// (silhouette geometry, branch-C precedent); foot debris shadowless
	// + culled. Every stream still respects OWDressing.Exclude.
	bool BuildCliffGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(FString(AssetDir) + TEXT("/PCG_OWCliff"), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		const TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };

		UClass* CliffClass = LoadClass<AActor>(nullptr,
			TEXT("/Game/OWGame/Dev/DressingLab/Cliffs/BP_OWCliffWall.BP_OWCliffWall_C"));
		if (!CliffClass)
		{
			UE_LOG(LogOWCreateBiomePCG, Error,
				TEXT("BP_OWCliffWall failed to load - run ClaudeCreateOWCliffBP.py first."));
			return false;
		}
		UPCGNode* Walls = MakeRoadSplineGetter(Graph, CliffClass, -300);

		TArray<FMeshEntry> Giants, Caps, Debris;
		for (int32 Rock = 9; Rock <= 12; ++Rock) { Giants.Add({PackRock(Rock), 1}); }
		for (int32 Rock = 5; Rock <= 8; ++Rock) { Caps.Add({PackRock(Rock), 1}); }
		Debris = { {PackRock(4), 1}, {PackRock(6), 1}, {PackRock(8), 1} };

		// (label, spacing cm, local offset min/max, scale min/max, palette,
		// shadows, cull) - offsets are spline-local: X along, Y back, Z up.
		struct FCliffRow
		{
			const TCHAR* Label;
			float SpacingCm;
			FVector OffMin, OffMax;
			float ScaleMin, ScaleMax;
			const TArray<FMeshEntry>* Palette;
			bool bShadow;
			int32 CullStart, CullEnd;
			bool bProject;
		};
		const FCliffRow Rows[] = {
			{ TEXT("base"), 900.0f, FVector(0, -80, -250), FVector(0, 80, -80),
				3.0f, 6.0f, &Giants, true, 0, 0, false },
			{ TEXT("upper"), 1100.0f, FVector(0, 60, 250), FVector(0, 260, 550),
				2.0f, 4.0f, &Giants, true, 0, 0, false },
			{ TEXT("rim"), 700.0f, FVector(0, 100, 550), FVector(0, 420, 850),
				1.0f, 2.2f, &Caps, true, 20000, 25000, false },
			{ TEXT("foot"), 400.0f, FVector(0, -260, 0), FVector(0, 260, 0),
				0.5f, 1.4f, &Debris, false, 8000, 10000, true },
		};
		int32 Y = 0;
		for (const FCliffRow& Row : Rows)
		{
			UPCGNode* Center = MakeSplineCenterSampler(Graph, Walls, Row.SpacingCm, -1100, Y);
			UPCGNode* Off = nullptr;
			UPCGTransformPointsSettings* O =
				AddNode<UPCGTransformPointsSettings>(Graph, Off, -900, Y);
			O->OffsetMin = Row.OffMin;
			O->OffsetMax = Row.OffMax;
			O->bAbsoluteOffset = false;
			Graph->AddEdge(Center, TEXT("Out"), Off, TEXT("In"));
			UPCGNode* Placed = Off;
			if (Row.bProject)
			{
				UPCGNode* Proj = MakeProjectToLandscape(Graph, Land, -760, Y);
				Graph->AddEdge(Off, TEXT("Out"), Proj, TEXT("In"));
				Placed = Proj;
			}
			UPCGNode* NotEx = MakeExcluded(Graph, Placed, TEXT("Out"), Excl, -620, Y + 60);
			// Yaw jitter only +/-14: the long axis stays along the spline
			// so rocks read as a coursed wall, not a tumble; roll/pitch
			// jitter breaks the repetition.
			UPCGNode* Xf = MakeTransform(Graph, NotEx, TEXT("Out"),
				FVector(Row.ScaleMin), FVector(Row.ScaleMax), /*bUniform=*/true,
				FRotator(-8.0, -14.0, -8.0), FRotator(8.0, 14.0, 8.0), -380, Y);
			MakeSpawner(Graph, Xf, TEXT("Out"), *Row.Palette, -150, Y,
				Row.bShadow, /*bWindWPO=*/false, Row.CullStart, Row.CullEnd);
			Y += 300;
		}
		return SaveAssetPackage(Graph);
	}
	// RC-A alpine round (user 2026-07-30): high-altitude dressing on the
	// two new paint layers. OW_Alpine = hardy rocky meadow (boulders
	// denser than meadow + sparse DWARF firs at ~15% forest density,
	// smaller scale band); OW_Snow = snowfield (very sparse bare/dead
	// firs + a few surface rocks, nothing else - clean snow read, user
	// call: zero grass). Treeline woods stay the user's OW_ForestFir
	// paint. All streams excluded + slope-banded like the biome peers.
	bool BuildAlpineGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(GraphPath(TEXT("Alpine")), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };
		Excl.Append(MakeRoadExclusions(Graph, Land));
		const TCHAR* TreesDir = TEXT("/Game/OWGame/Dev/DressingLab/Trees");
		auto Own = [TreesDir](const TCHAR* Name)
		{
			return FString::Printf(TEXT("%s/%s.%s"), TreesDir, Name, Name);
		};

		// alpine boulders: denser than meadow rocks, same tumble recipe
		UPCGNode* Rocks = MakeSampler(Graph, Land, 0.0025f, -1100, 0);
		UPCGNode* RocksF = MakeWeightFilter(Graph, Rocks, TEXT("Out"), TEXT("OW_Alpine"), 0.3, -850, 0);
		UPCGNode* RocksS = MakeSlopeBand(Graph, RocksF, TEXT("InsideFilter"), 0.6f, 1.0f, -650, 0);
		UPCGNode* RocksX = MakeExcluded(Graph, RocksS, TEXT("Out"), Excl, -420, 60);
		UPCGNode* RocksT = MakeTransform(Graph, RocksX, TEXT("Out"),
			FVector(0.5), FVector(1.6), /*bUniform=*/true,
			FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -200, 0);
		MakeSpawner(Graph, RocksT, TEXT("Out"), {
			{PackRock(2), 1}, {PackRock(4), 1}, {PackRock(6), 1}, {PackRock(8), 1},
		}, 50, 0, /*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::Solid);

		// dwarf firs: sparse, plumb, smaller than forest firs
		UPCGNode* Firs = MakeSampler(Graph, Land, 0.0015f, -1100, 300);
		UPCGNode* FirsF = MakeWeightFilter(Graph, Firs, TEXT("Out"), TEXT("OW_Alpine"), 0.5, -850, 300);
		UPCGNode* FirsS = MakeSlopeBand(Graph, FirsF, TEXT("InsideFilter"), 0.86f, 1.0f, -650, 300);
		UPCGNode* FirsX = MakeExcluded(Graph, FirsS, TEXT("Out"), Excl, -420, 360);
		UPCGNode* FirsT = MakeTransform(Graph, FirsX, TEXT("Out"),
			FVector(0.7, 0.7, 0.7), FVector(1.1, 1.1, 1.2), /*bUniform=*/false,
			FRotator(-6.0, 0.0, -6.0), FRotator(6.0, 360.0, 6.0), -200, 300,
			/*bAbsoluteRotation=*/true);
		SpawnTrees(Graph, FirsT, TEXT("Out"), {
			{Own(TEXT("SM_OWFirTree")), 4, FString(), TEXT("FirTree")},
			{Own(TEXT("SM_OWFir_TallSparse_A")), 3},
			{Own(TEXT("SM_OWFir_TallSparse_B")), 3},
			{Own(TEXT("SM_OWFir_BareTall_A")), 2},
			{Own(TEXT("SM_OWFir_BareTall_B")), 2},
			{Own(TEXT("SM_OWFir_Dead_A")), 1},
		}, 50, 300, /*bCastShadow=*/true, /*bWindWPO=*/true);   // LD4 GT: size classes

		// snowfield: very sparse bare/dead firs
		UPCGNode* Dead = MakeSampler(Graph, Land, 0.0004f, -1100, 600);
		UPCGNode* DeadF = MakeWeightFilter(Graph, Dead, TEXT("Out"), TEXT("OW_Snow"), 0.5, -850, 600);
		UPCGNode* DeadS = MakeSlopeBand(Graph, DeadF, TEXT("InsideFilter"), 0.86f, 1.0f, -650, 600);
		UPCGNode* DeadX = MakeExcluded(Graph, DeadS, TEXT("Out"), Excl, -420, 660);
		UPCGNode* DeadT = MakeTransform(Graph, DeadX, TEXT("Out"),
			FVector(0.8), FVector(1.2), /*bUniform=*/true,
			FRotator(-6.0, 0.0, -6.0), FRotator(6.0, 360.0, 6.0), -200, 600,
			/*bAbsoluteRotation=*/true);
		SpawnTrees(Graph, DeadT, TEXT("Out"), {
			{Own(TEXT("SM_OWFir_BareTall_A")), 1},
			{Own(TEXT("SM_OWFir_BareTall_B")), 1},
			{Own(TEXT("SM_OWFir_BareTall_C")), 1},
			{Own(TEXT("SM_OWFir_Dead_A")), 2},
			{Own(TEXT("SM_OWFir_Dead_B")), 1},
		}, 50, 600, /*bCastShadow=*/true, /*bWindWPO=*/true);   // LD4 GT: size classes

		// snow surface rocks: sparse, part-buried read via tumble
		UPCGNode* SRocks = MakeSampler(Graph, Land, 0.0008f, -1100, 900);
		UPCGNode* SRocksF = MakeWeightFilter(Graph, SRocks, TEXT("Out"), TEXT("OW_Snow"), 0.3, -850, 900);
		UPCGNode* SRocksX = MakeExcluded(Graph, SRocksF, TEXT("InsideFilter"), Excl, -420, 960);
		UPCGNode* SRocksT = MakeTransform(Graph, SRocksX, TEXT("Out"),
			FVector(1.0), FVector(2.5), /*bUniform=*/true,
			FRotator(-180.0, 0.0, -180.0), FRotator(180.0, 360.0, 180.0), -200, 900);
		MakeSpawner(Graph, SRocksT, TEXT("Out"), {
			{PackRock(5), 1}, {PackRock(6), 1}, {PackRock(7), 1}, {PackRock(8), 1},
		}, 50, 900, /*bCastShadow=*/false, /*bWindWPO=*/false,
			/*CullStart=*/8000, /*CullEnd=*/10000, EVegClass::Solid);

		return SaveAssetPackage(Graph);
	}

	/**
	 * LD4 PCG_GT_Brush (GT only): dense soft vegetation on GrandTour's Thicket layer (the forest-edge ring and the
	 * riparian brush), every stream through the same exclusions as the other graphs and the 0.8-1.0 slope band:
	 *   bushes weight > 0.5 at 0.08/m2 and 0.2-0.5 at 0.03/m2 (0.7-1.4, Soft.Brush); saplings > 0.4 at 0.03/m2
	 *   (0.25-0.45, Soft.Sapling) and young trees > 0.6 at 0.004/m2 (LD5 v2; was 0.008) (0.45-0.8, Soft.Young), both the size-class scale
	 *   with the Z jitter on the non-giant, non-ancient, non-dead forest entries; cover plants > 0.3 at 0.10/m2 (Soft.Brush).
	 */
	bool BuildBrushGraph(bool& bOutCreated)
	{
		UPCGGraph* Graph = GetOrCreateGraph(GraphPath(TEXT("Brush")), bOutCreated);
		if (!Graph) { return false; }
		UPCGNode* Land = MakeLandscapeGetter(Graph);
		TArray<UPCGNode*> Excl = { MakeExclusionGetter(Graph) };
		Excl.Append(MakeRoadExclusions(Graph, Land));
		const FName Thicket(TEXT("Thicket"));
		// The mixed forest palette (BuildForestGraph's tree stream), cut to the small-tree entries.
		const TArray<FMeshEntry> Trees = SmallTreeEntries({
			{OwnTree(TEXT("SM_OWBeech")), 22, FString(), TEXT("Beech")},
			{OwnTree(TEXT("SM_OWBeech")), 12, FString(), TEXT("Beech"), TEXT("_ToneWarm")},
			{OwnTree(TEXT("SM_OWBeech")), 8, FString(), TEXT("Beech"), TEXT("_ToneCool")},
			{OwnTree(TEXT("SM_OWBirch")), 14, FString(), TEXT("Birch")},
			{OwnTree(TEXT("SM_OWBirch")), 8, FString(), TEXT("Birch"), TEXT("_ToneWarm")},
			{OwnTree(TEXT("SM_OWBirch")), 6, FString(), TEXT("Birch"), TEXT("_ToneCool")},
			{OwnTree(TEXT("SM_OWFirTree")), 7, FString(), TEXT("FirTree")},
			{OwnTree(TEXT("SM_OWFirTree")), 3, FString(), TEXT("FirTree"), TEXT("_ToneWarm")},
			{OwnTree(TEXT("SM_OWFirTree")), 3, FString(), TEXT("FirTree"), TEXT("_ToneCool")},
			{OwnTree(TEXT("SM_OWFir_TallSparse_A")), 3},
			{OwnTree(TEXT("SM_OWFir_TallSparse_B")), 3},
			{OwnTree(TEXT("SM_OWFir_BareTall_A")), 2},
			{OwnTree(TEXT("SM_OWFir_BareTall_B")), 2},
			{OwnTree(TEXT("SM_OWFir_BareTall_C")), 2},
			{OwnTree(TEXT("SM_OWFir_AncientSparse_A")), 2},
			{OwnTree(TEXT("SM_OWFir_AncientSparse_B")), 1},
			{OwnTree(TEXT("SM_OWFir_BareGiant_A")), 1},
			{OwnTree(TEXT("SM_OWFir_BareGiant_B")), 1},
			{OwnTree(TEXT("SM_OWFir_BareGiant_C")), 1},
			{OwnTree(TEXT("SM_OWFir_Dead_A")), 2},
			{OwnTree(TEXT("SM_OWFir_Dead_B")), 1},
		});
		MakeSoftStream(Graph, Land, Excl, Thicket, 0.5, -1.0, 0.08f, 0.7, 1.4, /*bSizeClass=*/false,
			BushEntries(), EVegClass::SoftBrush, /*bCastShadow=*/false, /*bWindWPO=*/true,
			BushCullStart, BushCullEnd, 2001, 0);
		MakeSoftStream(Graph, Land, Excl, Thicket, 0.2, 0.5, 0.03f, 0.7, 1.4, /*bSizeClass=*/false,
			BushEntries(), EVegClass::SoftBrush, /*bCastShadow=*/false, /*bWindWPO=*/true,
			BushCullStart, BushCullEnd, 2011, 300);
		MakeSoftStream(Graph, Land, Excl, Thicket, 0.4, -1.0, 0.03f, SaplingScaleLo, SaplingScaleHi, /*bSizeClass=*/true,
			Trees, EVegClass::SoftSapling, /*bCastShadow=*/true, /*bWindWPO=*/true, 0, 0, 2021, 600);
		MakeSoftStream(Graph, Land, Excl, Thicket, 0.6, -1.0, 0.004f, YoungScaleLo, YoungScaleHi, /*bSizeClass=*/true,
			Trees, EVegClass::SoftYoung, /*bCastShadow=*/true, /*bWindWPO=*/true, 0, 0, 2031, 900);
		MakeSoftStream(Graph, Land, Excl, Thicket, 0.3, -1.0, 0.10f, CoverScaleLo, CoverScaleHi, /*bSizeClass=*/false,
			CoverPlantEntries(), EVegClass::SoftBrush, /*bCastShadow=*/false, /*bWindWPO=*/true,
			CoverCullStart, CoverCullEnd, 2041, 1200);
		return SaveAssetPackage(Graph);
	}
} // namespace OWBiomePCG

int32 UOWCreateBiomePCGCommandlet::Main(const FString& Params)
{
	using namespace OWBiomePCG;

	int32 Created = 0;
	int32 Failed = 0;
	bool bCreated = false;

	// LD4: -Variant=GT builds the GrandTour graph variants instead (PCG_GT_*, /Game/GrandTour/Dressing/PCG).
	FString Variant;
	FParse::Value(*Params, TEXT("Variant="), Variant);
	GVariantGT = Variant.Equals(TEXT("GT"), ESearchCase::IgnoreCase);
	GSoftHISM = GVariantGT && FParse::Param(*Params, TEXT("GTSoftHISM"));
	if (GSoftHISM)
	{
		UE_LOG(LogOWCreateBiomePCG, Warning, TEXT("LD7 A/B: -GTSoftHISM - the GT soft classes are HISM in this build (the LD5 proxy swap wants plain ISM)"));
	}
	if (!Variant.IsEmpty() && !GVariantGT)
	{
		UE_LOG(LogOWCreateBiomePCG, Error, TEXT("unknown -Variant=%s (only GT)"), *Variant);
		return 1;
	}

	struct FBuilder { const TCHAR* Name; bool (*Build)(bool&); };
	const FBuilder OWBuilders[] = {
		{ TEXT("PCG_OWForest"), &BuildForestGraph },
		{ TEXT("PCG_OWMeadow"), &BuildMeadowGraph },
		{ TEXT("PCG_OWScree"), &BuildScreeGraph },
		{ TEXT("PCG_OWRoad"), &BuildRoadGraph },
		{ TEXT("PCG_OWCliff"), &BuildCliffGraph },
		{ TEXT("PCG_OWAlpine"), &BuildAlpineGraph },
	};
	const FBuilder GTBuilders[] = {
		{ TEXT("PCG_GT_Forest"), &BuildForestGraph },
		{ TEXT("PCG_GT_Meadow"), &BuildMeadowGraph },
		{ TEXT("PCG_GT_Scree"), &BuildScreeGraph },
		{ TEXT("PCG_GT_Alpine"), &BuildAlpineGraph },
		{ TEXT("PCG_GT_Brush"), &BuildBrushGraph },
	};
	const TArrayView<const FBuilder> Builders = GVariantGT
		? TArrayView<const FBuilder>(GTBuilders, UE_ARRAY_COUNT(GTBuilders))
		: TArrayView<const FBuilder>(OWBuilders, UE_ARRAY_COUNT(OWBuilders));
	const int32 NumGraphs = Builders.Num();

	for (const FBuilder& Builder : Builders)
	{
		GReportGraph = Builder.Name;
		if (Builder.Build(bCreated))
		{
			Created += bCreated ? 1 : 0;
			UE_LOG(LogOWCreateBiomePCG, Display, TEXT("%s %s and saved."),
				Builder.Name, bCreated ? TEXT("created") : TEXT("rebuilt"));
		}
		else
		{
			++Failed;
			UE_LOG(LogOWCreateBiomePCG, Error, TEXT("%s FAILED to build/save."), Builder.Name);
		}
	}

	UE_LOG(LogOWCreateBiomePCG, Display,
		TEXT("OWCreateBiomePCG done: %d graphs (%d new, %d rebuilt), %d failed."),
		NumGraphs, Created, NumGraphs - Created - Failed, Failed);

	if (GVariantGT)
	{
		// LD4 report: each GT graph's spawners (class, tag, mesh:profile), and the Solid meshes that had no simple
		// collision and so were given NoCollision.
		auto Quote = [](const FString& Text) { return TEXT("\"") + Text.ReplaceCharWithEscapedChar() + TEXT("\""); };
		FString Json = TEXT("{\n \"variant\": \"GT\",\n \"graphs\": {\n");
		int32 G = 0;
		for (const FBuilder& Builder : Builders)
		{
			const TArray<FString>* Spawners = GReportSpawners.Find(Builder.Name);
			Json += FString::Printf(TEXT("  %s: ["), *Quote(Builder.Name));
			for (int32 i = 0; Spawners && i < Spawners->Num(); ++i)
			{
				Json += FString::Printf(TEXT("%s\n   %s"), i ? TEXT(",") : TEXT(""), *Quote((*Spawners)[i]));
			}
			Json += FString::Printf(TEXT("\n  ]%s\n"), ++G < Builders.Num() ? TEXT(",") : TEXT(""));
			UE_LOG(LogOWCreateBiomePCG, Display, TEXT("LD4 %s: %d spawners"), Builder.Name, Spawners ? Spawners->Num() : 0);
		}
		Json += TEXT(" },\n \"solid_without_simple_collision\": [");
		for (int32 i = 0; i < GNoSimpleCollision.Num(); ++i)
		{
			Json += FString::Printf(TEXT("%s\n  %s"), i ? TEXT(",") : TEXT(""), *Quote(GNoSimpleCollision[i]));
		}
		Json += FString::Printf(TEXT("\n ],\n \"summer_leaf_slots\": %d,\n \"unset_spawners\": %d,\n \"failed\": %d,\n \"ok\": %s\n}\n"),
			GSummerSlots, GUnsetSpawners, Failed, (GUnsetSpawners == 0 && Failed == 0) ? TEXT("true") : TEXT("false"));
		UE_LOG(LogOWCreateBiomePCG, Display, TEXT("LD8a GT graphs: %d spawner-entry slot(s) wear a summer leaf copy"), GSummerSlots);
		const FString ReportPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("docs/landscape_migration/ld4_gt_graphs.json"));
		FFileHelper::SaveStringToFile(Json, *ReportPath);
		UE_LOG(LogOWCreateBiomePCG, Display, TEXT("LD4 GT graphs: %d Solid mesh(es) without simple collision given NoCollision, %d spawner(s) without a class -> %s"),
			GNoSimpleCollision.Num(), GUnsetSpawners, *ReportPath);
		for (const FString& Mesh : GNoSimpleCollision)
		{
			UE_LOG(LogOWCreateBiomePCG, Display, TEXT("LD4 no simple collision: %s"), *Mesh);
		}
		if (GUnsetSpawners > 0)
		{
			return 1;
		}
	}
	return Failed == 0 ? 0 : 1;
}
