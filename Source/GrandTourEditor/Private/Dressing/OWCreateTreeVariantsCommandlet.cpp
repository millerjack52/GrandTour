#include "OWCreateTreeVariantsCommandlet.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "GeometryScript/MeshRepairFunctions.h"
#include "GeometryScript/GeometryScriptTypes.h"
#include "GeometryScript/MeshAssetFunctions.h"
#include "GeometryScript/MeshBasicEditFunctions.h"
#include "GeometryScript/MeshDecompositionFunctions.h"
#include "GeometryScript/MeshMaterialFunctions.h"
#include "GeometryScript/MeshQueryFunctions.h"
#include "GeometryScript/MeshTransformFunctions.h"
#include "Materials/MaterialInterface.h"
#include "Math/RandomStream.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "PhysicsEngine/BodySetup.h"
#include "UDynamicMesh.h"
#include "UObject/SavePackage.h"

DEFINE_LOG_CATEGORY_STATIC(LogOWTreeVariants, Log, All);

namespace OWTreeVariants
{
	constexpr const TCHAR* OutDir = TEXT("/Game/OWGame/Dev/DressingLab/Trees");
	constexpr const TCHAR* MIDir = TEXT("/Game/OWGame/Dev/DressingLab/TreeMIs");

	struct FVariantSpec
	{
		const TCHAR* SourceMesh;
		const TCHAR* OutName;
		FVector Scale;
		float LeafKeepFraction;
		int32 Seed;
		const TCHAR* Species;       // matches MI_OWTrunk_<S> / MI_OWFoliage_<S>
		float BareBelowFraction;    // 0 = off; else strip ALL blobs whose center
		                            // sits below this fraction of tree height
		                            // (self-pruned mature-conifer silhouette)
		int32 NumVariations;        // >1 = emit _A/_B/_C siblings with jittered
		                            // baldness/keep/stub values (seeded, stable)
		float TrunkThicken;         // >1 = post-ScaleMesh radial growth of
		                            // trunk-material verts (user 2026-07-28:
		                            // Z-stretched tall specs read spindly);
		                            // 1 = off
		// Detail-pass kinds (user 2026-07-28: stumps, fallen/standing dead
		// trees, bushes). Unlisted in a row = value-initialized (off).
		bool bNoCanopy;             // strip ALL leaf blobs; branch stubs over
		                            // the full height (dead trees, stumps)
		float StumpCutFraction;     // >0: crop everything above this fraction
		                            // of tree height, cap the cut (stumps)
		bool bBush;                 // canopy blobs only, clustered at ground,
		                            // no trunk (shrubs; puff still applies)
	};

	const FVariantSpec Specs[] = {
		// Nanite-enabled passthrough copies of the vendor bases (perf fix
		// 2026-07-27: 60.1M LOD0 tris across ~4250 single-LOD non-Nanite
		// trees tanked the frame). Full canopy, no jitter - just conversion.
		{ TEXT("/Game/3DAssets/SM_Beech.SM_Beech"), TEXT("SM_OWBeech"),
		  FVector(1.0, 1.0, 1.0), 1.0f, 7001, TEXT("Beech"), 0.0f, 1, 1.0f },
		{ TEXT("/Game/3DAssets/SM_Birch.SM_Birch"), TEXT("SM_OWBirch"),
		  FVector(1.0, 1.0, 1.0), 1.0f, 7002, TEXT("Birch"), 0.0f, 1, 1.0f },
		// Passthrough fir keeps vendor shape but gets a mild thicken: PCG Z
		// jitter now reaches 1.7 (size-up round, user 2026-07-28).
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFirTree"),
		  FVector(1.0, 1.0, 1.0), 1.0f, 7003, TEXT("FirTree"), 0.0f, 1, 1.10f },
		// Tall-fir family up one size class (user 2026-07-28: bigger trees,
		// thicker trunks - both bare and full).
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFir_TallSparse"),
		  FVector(1.45, 1.45, 1.80), 0.55f, 7011, TEXT("FirTree"), 0.0f, 2, 1.25f },
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFir_AncientSparse"),
		  FVector(1.85, 1.85, 2.20), 0.40f, 7012, TEXT("FirTree"), 0.0f, 2, 1.35f },
		{ TEXT("/Game/3DAssets/SM_Birch.SM_Birch"), TEXT("SM_OWBirch_Sparse"),
		  FVector(1.10, 1.10, 1.20), 0.60f, 7013, TEXT("Birch"), 0.0f, 2, 1.10f },
		// Bare-trunk family (user reference 2026-07-27): canopy only in the
		// top portion, thinned, on tall self-pruned trunks.
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFir_BareTall"),
		  FVector(1.55, 1.55, 1.95), 0.75f, 7014, TEXT("FirTree"), 0.45f, 3, 1.30f },
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFir_BareGiant"),
		  FVector(2.00, 2.00, 2.45), 0.60f, 7015, TEXT("FirTree"), 0.52f, 3, 1.40f },
		// Detail pass (user 2026-07-28): fallen/standing dead firs, stumps,
		// blob bushes. Dead = no canopy, branch stubs full height.
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFir_Dead"),
		  FVector(1.25, 1.25, 1.40), 0.15f, 7016, TEXT("FirTree"), 0.0f, 2, 1.30f,
		  /*bNoCanopy*/true },
		{ TEXT("/Game/3DAssets/SM_FirTree.SM_FirTree"), TEXT("SM_OWFir_Stump"),
		  FVector(1.30, 1.30, 1.00), 0.15f, 7017, TEXT("FirTree"), 0.0f, 2, 1.40f,
		  /*bNoCanopy*/true, /*StumpCutFraction*/0.06f },
		{ TEXT("/Game/3DAssets/SM_Beech.SM_Beech"), TEXT("SM_OWBeech_Stump"),
		  FVector(1.15, 1.15, 1.00), 0.15f, 7018, TEXT("Beech"), 0.0f, 2, 1.25f,
		  /*bNoCanopy*/true, /*StumpCutFraction*/0.06f },
		{ TEXT("/Game/3DAssets/SM_Beech.SM_Beech"), TEXT("SM_OWBush_Beech"),
		  FVector(0.85, 0.85, 0.75), 0.15f, 7019, TEXT("Beech"), 0.0f, 2, 1.0f,
		  /*bNoCanopy*/false, /*StumpCutFraction*/0.0f, /*bBush*/true },
		{ TEXT("/Game/3DAssets/SM_Birch.SM_Birch"), TEXT("SM_OWBush_Birch"),
		  FVector(0.80, 0.80, 0.70), 0.15f, 7020, TEXT("Birch"), 0.0f, 2, 1.0f,
		  /*bNoCanopy*/false, /*StumpCutFraction*/0.0f, /*bBush*/true },
	};

	// Per-variation jitter (user request 2026-07-27: trees of the same type
	// should differ a little - baldness height, canopy fullness, stub length).
	struct FResolvedVariant
	{
		FString OutName;
		float LeafKeep;
		float BareBelow;
		double StubMultiplier;
		int32 Seed;
	};

	TArray<FResolvedVariant> ResolveVariations(const FVariantSpec& Spec)
	{
		TArray<FResolvedVariant> Out;
		const int32 Count = FMath::Max(1, Spec.NumVariations);
		for (int32 i = 0; i < Count; ++i)
		{
			FResolvedVariant V;
			V.OutName = (Count == 1) ? Spec.OutName
				: FString::Printf(TEXT("%s_%c"), Spec.OutName, TCHAR('A' + i));
			V.Seed = Spec.Seed + i * 17;
			if (Count == 1)
			{
				// Single-variation specs (e.g. Nanite passthrough copies) are
				// exact: no jitter, no clamp trim (keep 1.0 must mean ALL).
				V.LeafKeep = FMath::Clamp(Spec.LeafKeepFraction, 0.15f, 1.0f);
				V.BareBelow = Spec.BareBelowFraction;
				V.StubMultiplier = 1.15;
			}
			else
			{
				FRandomStream Jitter(Spec.Seed * 97 + i * 131);
				V.LeafKeep = FMath::Clamp(
					Spec.LeafKeepFraction + float(Jitter.FRandRange(-0.08, 0.08)), 0.15f, 0.95f);
				V.BareBelow = (Spec.BareBelowFraction > 0.0f)
					? FMath::Clamp(Spec.BareBelowFraction + float(Jitter.FRandRange(-0.04, 0.04)), 0.2f, 0.7f)
					: 0.0f;
				V.StubMultiplier = Jitter.FRandRange(1.08, 1.28);
			}
			Out.Add(V);
		}
		return Out;
	}

	UStaticMesh* GetOrCreateMeshAsset(const FString& PackagePath, bool& bOutCreated)
	{
		bOutCreated = false;
		const FString AssetName = FPackageName::GetLongPackageAssetName(PackagePath);
		if (UStaticMesh* Existing = LoadObject<UStaticMesh>(nullptr, *(PackagePath + TEXT(".") + AssetName)))
		{
			Existing->Modify();
			return Existing;
		}
		UPackage* Package = CreatePackage(*PackagePath);
		UStaticMesh* Asset = NewObject<UStaticMesh>(Package, FName(*AssetName), RF_Public | RF_Standalone);
		FAssetRegistryModule::AssetCreated(Asset);
		bOutCreated = true;
		return Asset;
	}

	bool SaveMeshPackage(UObject* Asset)
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

	int32 FirstTriangleMaterialID(UDynamicMesh* Mesh)
	{
		FGeometryScriptIndexList TriList;
		bool bHasGaps = false;
		UGeometryScriptLibrary_MeshQueryFunctions::GetAllTriangleIDs(Mesh, TriList, bHasGaps);
		if (!TriList.List.IsValid() || TriList.List->Num() == 0)
		{
			return INDEX_NONE;
		}
		bool bValid = false;
		const int32 MatID = UGeometryScriptLibrary_MeshMaterialFunctions::GetTriangleMaterialID(
			Mesh, (*TriList.List)[0], bValid);
		return bValid ? MatID : INDEX_NONE;
	}

	// Bare-zone branch removal (user feedback 2026-07-27): branches share the
	// trunk material and its connected island, so blob-stripping leaves them.
	// Heuristic: the trunk CORE never exceeds its base radius (trees taper),
	// while branches protrude far beyond it. Measure base radius from the
	// bottom 2% of the trunk (no branches at ground level), then delete every
	// trunk-island triangle in the bare zone whose centroid lies outside
	// 1.15x that radius; fill the resulting stump holes.
	int32 PruneBareBranches(UDynamicMesh* TrunkComp, const FBox& FullBox, double BareZ,
		double CoreRadiusMultiplier)
	{
		using namespace UE::Geometry;
		const double H = FMath::Max(FullBox.Max.Z - FullBox.Min.Z, 1.0);
		const double BaseSlabTop = FullBox.Min.Z + 0.02 * H;

		FVector2d Center = FVector2d::Zero();
		double RBase = 0.0;
		int32 BaseVerts = 0;
		TrunkComp->ProcessMesh([&](const FDynamicMesh3& M)
		{
			for (const int32 Vid : M.VertexIndicesItr())
			{
				const FVector3d P = M.GetVertex(Vid);
				if (P.Z <= BaseSlabTop)
				{
					Center += FVector2d(P.X, P.Y);
					++BaseVerts;
				}
			}
			if (BaseVerts > 0)
			{
				Center /= double(BaseVerts);
				for (const int32 Vid : M.VertexIndicesItr())
				{
					const FVector3d P = M.GetVertex(Vid);
					if (P.Z <= BaseSlabTop)
					{
						RBase = FMath::Max(RBase, FVector2d::Distance(FVector2d(P.X, P.Y), Center));
					}
				}
			}
		});
		if (BaseVerts < 3 || RBase <= 0.0)
		{
			RBase = 0.05 * H;   // degenerate base: conservative core estimate
		}
		const double CoreRadius = RBase * CoreRadiusMultiplier;

		int32 Removed = 0;
		TrunkComp->EditMesh([&](FDynamicMesh3& M)
		{
			TArray<int32> ToRemove;
			for (const int32 Tid : M.TriangleIndicesItr())
			{
				const FVector3d C = M.GetTriCentroid(Tid);
				if (C.Z < BareZ && FVector2d::Distance(FVector2d(C.X, C.Y), Center) > CoreRadius)
				{
					ToRemove.Add(Tid);
				}
			}
			for (const int32 Tid : ToRemove)
			{
				M.RemoveTriangle(Tid);
			}
			Removed = ToRemove.Num();
		});
		if (Removed > 0)
		{
			FGeometryScriptFillHolesOptions FillOptions;
			int32 NumFilled = 0;
			int32 NumFailed = 0;
			UGeometryScriptLibrary_MeshRepairFunctions::FillAllMeshHoles(
				TrunkComp, FillOptions, NumFilled, NumFailed);
		}
		return Removed;
	}

	// Trunk thickening (user 2026-07-28): the tall fir specs stretch Z more
	// than XY (up to 1.70/2.00) and PCG height jitter adds 0.75-1.45 Z on
	// top, so trunks read spindly. Radially scale TRUNK-material verts about
	// a vertical axis through the trunk base center (same bottom-2%-slab
	// measurement as PruneBareBranches; runs post-ScaleMesh). Full Factor
	// inside the base radius - the tapering core is always thinner than the
	// base, so the whole trunk thickens - fading to 1.0 by 3x base radius so
	// branch attachments follow smoothly but branches do not translate
	// outward wholesale.
	bool ThickenTrunk(UDynamicMesh* Mesh, int32 TrunkMatID, double Factor,
		int32& OutMovedVerts, double& OutRBaseBefore, double& OutRBaseAfter)
	{
		using namespace UE::Geometry;
		OutMovedVerts = 0;
		OutRBaseBefore = 0.0;
		OutRBaseAfter = 0.0;
		Mesh->EditMesh([&](FDynamicMesh3& M)
		{
			const FDynamicMeshMaterialAttribute* MatID =
				(M.HasAttributes() && M.Attributes()->HasMaterialID())
					? M.Attributes()->GetMaterialID() : nullptr;
			if (!MatID)
			{
				return;
			}
			TSet<int32> TrunkVerts;
			double MinZ = TNumericLimits<double>::Max();
			double MaxZ = -TNumericLimits<double>::Max();
			for (const int32 Tid : M.TriangleIndicesItr())
			{
				if (MatID->GetValue(Tid) != TrunkMatID)
				{
					continue;
				}
				const FIndex3i Tri = M.GetTriangle(Tid);
				for (const int32 Vid : { Tri.A, Tri.B, Tri.C })
				{
					TrunkVerts.Add(Vid);
					const double Z = M.GetVertex(Vid).Z;
					MinZ = FMath::Min(MinZ, Z);
					MaxZ = FMath::Max(MaxZ, Z);
				}
			}
			if (TrunkVerts.Num() < 3)
			{
				return;
			}
			const double BaseSlabTop = MinZ + 0.02 * FMath::Max(MaxZ - MinZ, 1.0);
			FVector2d Center = FVector2d::Zero();
			int32 BaseVerts = 0;
			for (const int32 Vid : TrunkVerts)
			{
				const FVector3d P = M.GetVertex(Vid);
				if (P.Z <= BaseSlabTop)
				{
					Center += FVector2d(P.X, P.Y);
					++BaseVerts;
				}
			}
			if (BaseVerts < 3)
			{
				return;
			}
			Center /= double(BaseVerts);
			double RBase = 0.0;
			for (const int32 Vid : TrunkVerts)
			{
				const FVector3d P = M.GetVertex(Vid);
				if (P.Z <= BaseSlabTop)
				{
					RBase = FMath::Max(RBase, FVector2d::Distance(FVector2d(P.X, P.Y), Center));
				}
			}
			if (RBase <= 0.0)
			{
				return;
			}
			OutRBaseBefore = RBase;
			const double FadeEnd = 3.0 * RBase;
			for (const int32 Vid : TrunkVerts)
			{
				const FVector3d P = M.GetVertex(Vid);
				const FVector2d Radial(P.X - Center.X, P.Y - Center.Y);
				const double R = Radial.Length();
				if (R <= 0.0 || R >= FadeEnd)
				{
					continue;
				}
				const double Fade = (R <= RBase)
					? 1.0 : 1.0 - FMath::SmoothStep(RBase, FadeEnd, R);
				const double Scale = 1.0 + (Factor - 1.0) * Fade;
				if (Scale <= 1.0001)
				{
					continue;
				}
				M.SetVertex(Vid, FVector3d(
					Center.X + Radial.X * Scale, Center.Y + Radial.Y * Scale, P.Z));
				++OutMovedVerts;
			}
			for (const int32 Vid : TrunkVerts)
			{
				const FVector3d P = M.GetVertex(Vid);
				if (P.Z <= BaseSlabTop)
				{
					OutRBaseAfter = FMath::Max(OutRBaseAfter,
						FVector2d::Distance(FVector2d(P.X, P.Y), Center));
				}
			}
		});
		return OutMovedVerts > 0;
	}

	// The vendor foliage material builds canopy volume at RENDER time: its WPO
	// puffs each leaf card outward by (UV0*2-1) transformed tangent->world
	// TWICE (pseudo-random per-face rotation), scaled by LeavesSize - the
	// "fluffyness" block in MM_Foliage. Spawned trees run with
	// bEvaluateWorldPositionOffset=false (the Nanite wind/perf fix), which
	// deleted that puff and left swiss-cheese canopies (attribution rounds
	// 1-4, 2026-07-27: assets clean placed, erosion healed live by toggling
	// WPO back on). Bake the same deterministic offset into the mesh instead:
	// structure lives in geometry, only motion stays material. Trees rendered
	// WITH WPO evaluation (placed actors wearing these meshes) double-puff -
	// spawned-forest usage assumes descriptor WPO stays off.
	int32 BakeLeafPuff(UDynamicMesh* Mesh, int32 TrunkMatID, double LeavesSize)
	{
		int32 Displaced = 0;
		Mesh->EditMesh([&](FDynamicMesh3& M)
		{
			if (!M.HasAttributes() || M.Attributes()->PrimaryUV() == nullptr)
			{
				return;
			}
			const UE::Geometry::FDynamicMeshUVOverlay* UV = M.Attributes()->PrimaryUV();
			const UE::Geometry::FDynamicMeshMaterialAttribute* MatID =
				M.Attributes()->HasMaterialID() ? M.Attributes()->GetMaterialID() : nullptr;
			TMap<int32, FVector3d> Offsets;
			for (const int32 Tid : M.TriangleIndicesItr())
			{
				if (MatID && MatID->GetValue(Tid) == TrunkMatID)
				{
					continue;
				}
				if (!UV->IsSetTriangle(Tid))
				{
					continue;
				}
				const UE::Geometry::FIndex3i Tri = M.GetTriangle(Tid);
				const UE::Geometry::FIndex3i UVTri = UV->GetTriangle(Tid);
				const FVector3d P0 = M.GetVertex(Tri.A);
				const FVector3d P1 = M.GetVertex(Tri.B);
				const FVector3d P2 = M.GetVertex(Tri.C);
				const FVector2f T0 = UV->GetElement(UVTri.A);
				const FVector2f T1 = UV->GetElement(UVTri.B);
				const FVector2f T2 = UV->GetElement(UVTri.C);
				const FVector2d D1(T1.X - T0.X, T1.Y - T0.Y);
				const FVector2d D2(T2.X - T0.X, T2.Y - T0.Y);
				const double Det = D1.X * D2.Y - D2.X * D1.Y;
				if (FMath::Abs(Det) < 1e-12)
				{
					continue;
				}
				const FVector3d E1 = P1 - P0;
				const FVector3d E2 = P2 - P0;
				FVector3d T = (E1 * D2.Y - E2 * D1.Y) / Det;
				FVector3d B = (E2 * D1.X - E1 * D2.X) / Det;
				if (!T.Normalize() || !B.Normalize())
				{
					continue;
				}
				const FVector3d N = M.GetTriNormal(Tid);
				const FVector2f CornerUVs[3] = { T0, T1, T2 };
				const int32 Vids[3] = { Tri.A, Tri.B, Tri.C };
				for (int32 Corner = 0; Corner < 3; ++Corner)
				{
					if (Offsets.Contains(Vids[Corner]))
					{
						continue;
					}
					const FVector3d V0(
						CornerUVs[Corner].X * 2.0 - 1.0,
						CornerUVs[Corner].Y * 2.0 - 1.0, 0.0);
					const FVector3d W1 = T * V0.X + B * V0.Y + N * V0.Z;
					const FVector3d W2 = T * W1.X + B * W1.Y + N * W1.Z;
					Offsets.Add(Vids[Corner], W2 * LeavesSize);
				}
			}
			for (const TPair<int32, FVector3d>& KV : Offsets)
			{
				M.SetVertex(KV.Key, M.GetVertex(KV.Key) + KV.Value);
			}
			Displaced = Offsets.Num();
		});
		return Displaced;
	}

	// Leg dressing LD4 (docs/LEG_DRESSING_PLAN.md, "Tree variants"): one trunk capsule per tree, dead tree and stump,
	// none on a bush, and CollisionTraceFlag = UseSimpleAsComplex so the canopy's triangles never block a trace.
	// Measured on the finished mesh (after scale, thicken and puff), mesh space, Z = 0 at the pivot (ground contact):
	//  - the trunk: every trunk-material triangle, cut by horizontal planes; a plane's crossings are its edge
	//    crossings. The axis is anchored low, at 20 cm (a quarter of a short trunk's top), where only the trunk
	//    crosses: centre = median X / median Y, radius = median distance. Each plane above takes the crossings within
	//    1.5x the anchor radius of the plane below's centre as the trunk ring (so a branch crossing the same plane -
	//    the passthrough fir has them below 1 m - moves neither centre nor radius), its mean as the centre, the ring's
	//    median distance as the radius;
	//  - radius: the ring at 1 m above the ground, or at half the trunk's top for a trunk shorter than 2 m (the Fir
	//    stumps stand 10 cm proud of the ground);
	//  - base: the trunk's lowest point (the vendor trees bury a root flare 50-120 cm below the pivot);
	//  - top (trees, dead trees): the first branch - the lowest plane, scanning up in 10 cm steps from the radius
	//    plane, with a crossing beyond 1.5x that radius from the plane's ring centre - or half the tree's height above
	//    the ground, whichever is lower; (stumps) the trunk's top, the cut;
	//  - the capsule: vertical, centred on the radius plane's ring centre in XY, from base to top (UE's sphyl Length is
	//    the straight part: top - base - 2 radius, at least 0).
	struct FCapsuleResult
	{
		FString Name;
		FString Kind;              // tree, dead, stump, bush
		int32 Capsules = 0;        // after save, read back from the body setup
		int32 Shapes = 0;          // every simple element
		int32 PrevShapes = -1;     // the body setup before this run (-1: a new asset)
		FString PrevFlag;
		FString Flag;
		double Radius = 0.0;
		double Length = 0.0;
		FVector Centre = FVector::ZeroVector;
		double BaseZ = 0.0;
		double TopZ = 0.0;
		double AnchorZ = 0.0;
		double AnchorRadius = 0.0;
		int32 AnchorPoints = 0;
		double SampleZ = 0.0;
		int32 SamplePoints = 0;    // every crossing at the radius plane
		int32 SampleRing = 0;      // the trunk ring's share of them
		double FirstBranchZ = -1.0;   // -1: none found below the half-height cap
		double TreeTopZ = 0.0;
		bool bFallbackRadius = false;
	};
	TArray<FCapsuleResult> GCapsules;

	const TCHAR* TraceFlagName(ECollisionTraceFlag Flag)
	{
		switch (Flag)
		{
		case CTF_UseDefault: return TEXT("UseDefault");
		case CTF_UseSimpleAndComplex: return TEXT("UseSimpleAndComplex");
		case CTF_UseSimpleAsComplex: return TEXT("UseSimpleAsComplex");
		case CTF_UseComplexAsSimple: return TEXT("UseComplexAsSimple");
		default: return TEXT("?");
		}
	}

	double MedianOf(TArray<double>& Values)
	{
		Values.Sort();
		return Values[Values.Num() / 2];
	}

	/** Every crossing of the trunk triangles' edges with the plane at height Z. */
	void TrunkCrossings(const TArray<FVector3d>& TrunkTris, double Z, TArray<FVector2d>& OutPoints)
	{
		OutPoints.Reset();
		for (int32 T = 0; T + 2 < TrunkTris.Num(); T += 3)
		{
			const FVector3d* P = &TrunkTris[T];
			for (int32 E = 0; E < 3; ++E)
			{
				const FVector3d& A = P[E];
				const FVector3d& B = P[(E + 1) % 3];
				if ((A.Z - Z) * (B.Z - Z) < 0.0)
				{
					const double Alpha = (Z - A.Z) / (B.Z - A.Z);
					OutPoints.Add(FVector2d(A.X + (B.X - A.X) * Alpha, A.Y + (B.Y - A.Y) * Alpha));
				}
			}
		}
	}

	/** The anchor plane (only the trunk crosses it): centre = median X / median Y, radius = median distance. */
	bool AnchorSection(const TArray<FVector2d>& Points, FVector2d& OutCentre, double& OutRadius)
	{
		if (Points.Num() < 3)
		{
			return false;
		}
		TArray<double> Xs, Ys, Dists;
		for (const FVector2d& Point : Points)
		{
			Xs.Add(Point.X);
			Ys.Add(Point.Y);
		}
		OutCentre = FVector2d(MedianOf(Xs), MedianOf(Ys));
		for (const FVector2d& Point : Points)
		{
			Dists.Add(FVector2d::Distance(Point, OutCentre));
		}
		OutRadius = MedianOf(Dists);
		return OutRadius > 0.0;
	}

	/**
	 * A plane above the anchor: the trunk ring is the crossings within Reach of the centre (starting at Guess, the
	 * ring's mean the new centre, three passes); radius = the ring's median distance; MaxDist = the farthest crossing.
	 */
	bool RingSection(const TArray<FVector2d>& Points, const FVector2d& Guess, double Reach, FVector2d& OutCentre,
		double& OutRadius, double& OutMaxDist, int32& OutRing)
	{
		OutCentre = Guess;
		TArray<const FVector2d*> Ring;
		for (int32 Pass = 0; Pass < 4; ++Pass)
		{
			Ring.Reset();
			for (const FVector2d& Point : Points)
			{
				if (FVector2d::Distance(Point, OutCentre) <= Reach)
				{
					Ring.Add(&Point);
				}
			}
			if (Ring.Num() < 3)
			{
				return false;
			}
			if (Pass == 3)
			{
				break;
			}
			FVector2d Sum(0.0, 0.0);
			for (const FVector2d* Point : Ring)
			{
				Sum += *Point;
			}
			OutCentre = Sum / Ring.Num();
		}
		TArray<double> Dists;
		for (const FVector2d* Point : Ring)
		{
			Dists.Add(FVector2d::Distance(*Point, OutCentre));
		}
		OutRadius = MedianOf(Dists);
		OutMaxDist = 0.0;
		for (const FVector2d& Point : Points)
		{
			OutMaxDist = FMath::Max(OutMaxDist, FVector2d::Distance(Point, OutCentre));
		}
		OutRing = Ring.Num();
		return OutRadius > 0.0;
	}

	/** Fills Result's capsule numbers from the finished mesh (see the block comment above). False when there is no trunk. */
	bool MeasureTrunkCapsule(UDynamicMesh* Mesh, int32 TrunkMatID, bool bStump, FCapsuleResult& Result)
	{
		TArray<FVector3d> TrunkTris;
		double TreeTop = -TNumericLimits<double>::Max();
		Mesh->ProcessMesh([&](const UE::Geometry::FDynamicMesh3& M)
		{
			const UE::Geometry::FDynamicMeshMaterialAttribute* MatID =
				(M.HasAttributes() && M.Attributes()->HasMaterialID()) ? M.Attributes()->GetMaterialID() : nullptr;
			for (const int32 Tid : M.TriangleIndicesItr())
			{
				FVector3d A, B, C;
				M.GetTriVertices(Tid, A, B, C);
				TreeTop = FMath::Max(TreeTop, FMath::Max3(A.Z, B.Z, C.Z));
				if (MatID && MatID->GetValue(Tid) == TrunkMatID)
				{
					TrunkTris.Add(A);
					TrunkTris.Add(B);
					TrunkTris.Add(C);
				}
			}
		});
		if (TrunkTris.Num() < 3)
		{
			return false;
		}
		double TrunkMin = TNumericLimits<double>::Max();
		double TrunkMax = -TNumericLimits<double>::Max();
		for (const FVector3d& P : TrunkTris)
		{
			TrunkMin = FMath::Min(TrunkMin, P.Z);
			TrunkMax = FMath::Max(TrunkMax, P.Z);
		}
		Result.TreeTopZ = TreeTop;
		Result.BaseZ = TrunkMin;
		const double TrunkTop = FMath::Max(TrunkMax, 1.0);
		const double AnchorZ = FMath::Min(20.0, 0.25 * TrunkTop);
		const double SampleZ = FMath::Min(100.0, 0.5 * TrunkTop);
		Result.AnchorZ = AnchorZ;
		Result.SampleZ = SampleZ;

		TArray<FVector2d> Points;
		TrunkCrossings(TrunkTris, AnchorZ, Points);
		Result.AnchorPoints = Points.Num();
		FVector2d AnchorCentre(0.0, 0.0);
		double AnchorRadius = 0.0;
		FVector2d Centre(0.0, 0.0);
		double Radius = 0.0;
		bool bMeasured = false;
		if (AnchorSection(Points, AnchorCentre, AnchorRadius))
		{
			Result.AnchorRadius = AnchorRadius;
			// Follow the axis up to the radius plane in 10 cm steps (a leaning trunk walks off a fixed centre).
			FVector2d Follow = AnchorCentre;
			bMeasured = true;
			for (double Z = FMath::Min(AnchorZ + 10.0, SampleZ); bMeasured; Z = FMath::Min(Z + 10.0, SampleZ))
			{
				TrunkCrossings(TrunkTris, Z, Points);
				double MaxDist = 0.0;
				int32 RingCount = 0;
				bMeasured = RingSection(Points, Follow, 1.5 * AnchorRadius, Centre, Radius, MaxDist, RingCount);
				Follow = Centre;
				if (Z >= SampleZ)
				{
					Result.SamplePoints = Points.Num();
					Result.SampleRing = RingCount;
					break;
				}
			}
		}
		if (!bMeasured)
		{
			// No trunk ring (a degenerate trunk): the plan's LD5 default, 0.05 x the height, on the pivot.
			Radius = 0.05 * FMath::Max(TreeTop, 1.0);
			Centre = FVector2d(0.0, 0.0);
			Result.bFallbackRadius = true;
		}
		double Top = 0.0;
		if (bStump)
		{
			Top = TrunkMax;
		}
		else
		{
			const double HalfHeight = 0.5 * TreeTop;
			Top = HalfHeight;
			FVector2d Follow = Centre;
			for (double Z = SampleZ + 10.0; Z < HalfHeight && !Result.bFallbackRadius; Z += 10.0)
			{
				TrunkCrossings(TrunkTris, Z, Points);
				FVector2d PlaneCentre;
				double PlaneRadius = 0.0;
				double PlaneMax = 0.0;
				int32 RingCount = 0;
				if (!RingSection(Points, Follow, 1.5 * Radius, PlaneCentre, PlaneRadius, PlaneMax, RingCount))
				{
					continue;
				}
				Follow = PlaneCentre;
				if (PlaneMax > 1.5 * Radius)
				{
					Result.FirstBranchZ = Z;
					Top = Z;
					break;
				}
			}
		}
		Result.Radius = Radius;
		Result.TopZ = Top;
		Result.Length = FMath::Max(0.0, (Top - TrunkMin) - 2.0 * Radius);
		Result.Centre = FVector(Centre.X, Centre.Y, 0.5 * (TrunkMin + Top));
		return true;
	}

	bool BuildVariant(const FVariantSpec& Spec, const FResolvedVariant& V)
	{
		UStaticMesh* Source = LoadObject<UStaticMesh>(nullptr, Spec.SourceMesh);
		if (!Source)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("missing source mesh %s"), Spec.SourceMesh);
			return false;
		}

		// Which section/material index is the trunk? Match by material name.
		int32 TrunkMatID = 0;
		const TArray<FStaticMaterial>& SourceMats = Source->GetStaticMaterials();
		for (int32 i = 0; i < SourceMats.Num(); ++i)
		{
			const UMaterialInterface* M = SourceMats[i].MaterialInterface;
			if (M && M->GetName().Contains(TEXT("Trunk")))
			{
				TrunkMatID = i;
				break;
			}
		}

		UDynamicMesh* Full = NewObject<UDynamicMesh>();
		EGeometryScriptOutcomePins Outcome = EGeometryScriptOutcomePins::Failure;
		UGeometryScriptLibrary_StaticMeshFunctions::CopyMeshFromStaticMesh(
			Source, Full, FGeometryScriptCopyMeshFromAssetOptions(),
			FGeometryScriptMeshReadLOD(), Outcome);
		if (Outcome != EGeometryScriptOutcomePins::Success)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("CopyMeshFromStaticMesh failed for %s"), Spec.SourceMesh);
			return false;
		}

		const FBox FullBox = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(Full);
		const double TreeHeight = FMath::Max(FullBox.Max.Z - FullBox.Min.Z, 1.0);

		UDynamicMeshPool* Pool = NewObject<UDynamicMeshPool>();
		TArray<UDynamicMesh*> Components;
		UGeometryScriptLibrary_MeshDecompositionFunctions::SplitMeshByComponents(Full, Components, Pool);

		TArray<UDynamicMesh*> Trunk;
		TArray<UDynamicMesh*> Blobs;
		int32 BareStripped = 0;
		for (UDynamicMesh* Comp : Components)
		{
			if (FirstTriangleMaterialID(Comp) == TrunkMatID)
			{
				Trunk.Add(Comp);
				continue;
			}
			if (V.BareBelow > 0.0f)
			{
				const FBox BlobBox = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(Comp);
				const double HeightFrac = (BlobBox.GetCenter().Z - FullBox.Min.Z) / TreeHeight;
				if (HeightFrac < V.BareBelow)
				{
					++BareStripped;
					continue;
				}
			}
			Blobs.Add(Comp);
		}
		if (!Spec.bBush && Trunk.Num() == 0)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: unexpected split (trunk=%d blobs=%d)"),
				*V.OutName, Trunk.Num(), Blobs.Num());
			return false;
		}
		if ((Spec.bBush || !Spec.bNoCanopy) && Blobs.Num() == 0)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: no leaf blobs to work with"), *V.OutName);
			return false;
		}

		int32 KeepCount = 0;
		TArray<UDynamicMesh*> Kept;
		if (!Spec.bNoCanopy && !Spec.bBush)
		{
			// Crown blob (highest bbox top) is always kept for silhouette.
			Blobs.Sort([](UDynamicMesh& A, UDynamicMesh& B)
			{
				const FBox BoxA = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(&A);
				const FBox BoxB = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(&B);
				return BoxA.Max.Z > BoxB.Max.Z;
			});
			KeepCount = FMath::Clamp(
				FMath::CeilToInt32(V.LeafKeep * Blobs.Num()), 1, Blobs.Num());
			Kept.Add(Blobs[0]);
			TArray<UDynamicMesh*> Rest(Blobs.GetData() + 1, Blobs.Num() - 1);
			FRandomStream Rand(V.Seed);
			for (int32 i = Rest.Num() - 1; i > 0; --i)
			{
				Rest.Swap(i, Rand.RandRange(0, i));
			}
			for (int32 i = 0; i < Rest.Num() && Kept.Num() < KeepCount; ++i)
			{
				Kept.Add(Rest[i]);
			}
		}

		UDynamicMesh* Out = NewObject<UDynamicMesh>();
		int32 BranchTrisRemoved = 0;
		if (!Spec.bBush)
		{
			for (UDynamicMesh* Comp : Trunk)
			{
				// Dead/stump kinds prune branches over the FULL height
				// (stubby self-pruned look everywhere, no canopy to hide in).
				if (V.BareBelow > 0.0f || Spec.bNoCanopy)
				{
					const double BareZ = Spec.bNoCanopy
						? FullBox.Max.Z + 1.0
						: FullBox.Min.Z + V.BareBelow * TreeHeight;
					BranchTrisRemoved += PruneBareBranches(
						Comp, FullBox, BareZ, V.StubMultiplier);
				}
				UGeometryScriptLibrary_MeshBasicEditFunctions::AppendMesh(Out, Comp, FTransform::Identity);
			}
			for (UDynamicMesh* Comp : Kept)
			{
				UGeometryScriptLibrary_MeshBasicEditFunctions::AppendMesh(Out, Comp, FTransform::Identity);
			}
		}
		else
		{
			// Bush: 4 seeded-random canopy blobs re-clustered at the origin,
			// slightly sunk - a shrub in the same painterly language as the
			// canopies. No trunk, no prune; the puff bake still applies.
			FRandomStream BushRand(V.Seed);
			TArray<UDynamicMesh*> BushBlobs = Blobs;
			for (int32 i = BushBlobs.Num() - 1; i > 0; --i)
			{
				BushBlobs.Swap(i, BushRand.RandRange(0, i));
			}
			const int32 Count = FMath::Min(4, BushBlobs.Num());
			double Ring = 0.0;
			for (int32 i = 0; i < Count; ++i)
			{
				const FBox B = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(BushBlobs[i]);
				Ring = FMath::Max(Ring, B.GetExtent().GetMax());
			}
			for (int32 i = 0; i < Count; ++i)
			{
				const FBox B = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(BushBlobs[i]);
				const double Ang = 2.0 * PI * i / Count + BushRand.FRandRange(-0.4, 0.4);
				const FVector Target(
					(i == 0) ? 0.0 : FMath::Cos(Ang) * Ring * 0.85,
					(i == 0) ? 0.0 : FMath::Sin(Ang) * Ring * 0.85,
					B.GetExtent().Z * 0.8);
				UGeometryScriptLibrary_MeshBasicEditFunctions::AppendMesh(
					Out, BushBlobs[i], FTransform(Target - B.GetCenter()));
			}
			KeepCount = Count;
			const FBox BushBox = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(Out);
			if (BushBox.GetSize().Z > 0.5 * TreeHeight || BushBox.GetSize().Z <= 0.0)
			{
				UE_LOG(LogOWTreeVariants, Error,
					TEXT("%s: bush cluster sanity failed (height %.0f of tree %.0f)"),
					*V.OutName, BushBox.GetSize().Z, TreeHeight);
				return false;
			}
		}

		// Stump: crop everything above the cut, cap the hole. Runs pre-scale
		// (tree space); gate = nothing may survive above the cut plane.
		// CutZ is PIVOT-relative (Z=0 = spawn ground contact), NOT mesh-min-
		// relative: the vendor fir extends ~190 units below its pivot (buried
		// root flare), so a min-based cut put the whole stump underground
		// (paid 2026-07-28, first stump run). Removal tests the tris' MAX
		// vertex Z - centroid tests let big base triangles poke past the cut.
		if (Spec.StumpCutFraction > 0.0f)
		{
			const double CutZ = double(Spec.StumpCutFraction) * TreeHeight;
			int32 CutTris = 0;
			Out->EditMesh([&](UE::Geometry::FDynamicMesh3& M)
			{
				TArray<int32> ToRemove;
				for (const int32 Tid : M.TriangleIndicesItr())
				{
					FVector3d VA, VB, VC;
					M.GetTriVertices(Tid, VA, VB, VC);
					if (FMath::Max3(VA.Z, VB.Z, VC.Z) > CutZ)
					{
						ToRemove.Add(Tid);
					}
				}
				for (const int32 Tid : ToRemove)
				{
					M.RemoveTriangle(Tid);
				}
				CutTris = ToRemove.Num();
			});
			FGeometryScriptFillHolesOptions StumpFill;
			int32 StumpFilled = 0;
			int32 StumpFailed = 0;
			UGeometryScriptLibrary_MeshRepairFunctions::FillAllMeshHoles(
				Out, StumpFill, StumpFilled, StumpFailed);
			const FBox StumpBox = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(Out);
			if (CutTris == 0 || StumpBox.Max.Z > CutZ + 1.0)
			{
				UE_LOG(LogOWTreeVariants, Error,
					TEXT("%s: stump cut no-oped (%d tris cut, top %.1f vs cut %.1f)"),
					*V.OutName, CutTris, StumpBox.Max.Z, CutZ);
				return false;
			}
		}

		UGeometryScriptLibrary_MeshTransformFunctions::ScaleMesh(Out, Spec.Scale, FVector::ZeroVector);

		int32 TrunkVertsMoved = 0;
		double RBaseBefore = 0.0;
		double RBaseAfter = 0.0;
		if (Spec.TrunkThicken > 1.0f)
		{
			ThickenTrunk(Out, TrunkMatID, Spec.TrunkThicken,
				TrunkVertsMoved, RBaseBefore, RBaseAfter);
			// Hard gate (puff-gate doctrine): a silent no-op re-opens the
			// spindly-trunk defect. Base radius must grow to ~the requested
			// factor - every base-slab vert sits at r <= RBase = full push.
			if (TrunkVertsMoved == 0
				|| RBaseAfter < RBaseBefore * (1.0 + 0.9 * (Spec.TrunkThicken - 1.0)))
			{
				UE_LOG(LogOWTreeVariants, Error,
					TEXT("%s: trunk thicken x%.2f no-oped (%d verts moved, Rbase %.1f -> %.1f)"),
					*V.OutName, Spec.TrunkThicken, TrunkVertsMoved, RBaseBefore, RBaseAfter);
				return false;
			}
		}

		// MIs load early: the puff bake needs the species' LeavesSize value.
		UMaterialInterface* TrunkMI = LoadObject<UMaterialInterface>(nullptr,
			*(FString(MIDir) / FString::Printf(TEXT("MI_OWTrunk_%s.MI_OWTrunk_%s"), Spec.Species, Spec.Species)));
		UMaterialInterface* FoliageMI = LoadObject<UMaterialInterface>(nullptr,
			*(FString(MIDir) / FString::Printf(TEXT("MI_OWFoliage_%s.MI_OWFoliage_%s"), Spec.Species, Spec.Species)));
		if (!TrunkMI || !FoliageMI)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: missing MI_OW* materials for %s (run ClaudeSetupFoliageMIs.py)"),
				*V.OutName, Spec.Species);
			return false;
		}

		// Bake AFTER ScaleMesh: the material applies the puff post-scale
		// (magnitude LeavesSize x instance ObjectScale only - never the
		// asset-baked Spec.Scale), so the baked equivalent must too.
		// The puff only exists where the material's isFluffy static switch is
		// on. Fir MIs run isFluffy=false (needle strips, tiled UVs) - baking
		// there explodes stems into giant shards (paid 2026-07-28, first puff
		// cycle) and is also why fir never swiss-cheesed under WPO-off.
		bool bIsFluffy = true;
		FGuid FluffyGuid;
		FoliageMI->GetStaticSwitchParameterValue(
			FHashedMaterialParameterInfo(FMaterialParameterInfo(TEXT("isFluffy"))),
			bIsFluffy, FluffyGuid);
		float LeavesSize = 0.0f;
		if (!FoliageMI->GetScalarParameterValue(
				FHashedMaterialParameterInfo(FMaterialParameterInfo(TEXT("LeavesSize"))), LeavesSize)
			|| LeavesSize <= 0.0f)
		{
			LeavesSize = 25.0f;   // MM_Foliage master default
		}
		int32 PuffedVerts = 0;
		FVector Growth = FVector::ZeroVector;
		// bNoCanopy kinds carry zero foliage tris - the puff hard-gate would
		// (correctly) fire on them, so skip the bake outright.
		if (bIsFluffy && !Spec.bNoCanopy)
		{
			const FBox PrePuffBox = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(Out);
			PuffedVerts = BakeLeafPuff(Out, TrunkMatID, LeavesSize);
			const FBox PostPuffBox = UGeometryScriptLibrary_MeshQueryFunctions::GetMeshBoundingBox(Out);
			Growth = PostPuffBox.GetSize() - PrePuffBox.GetSize();
			// Gate at 0.25x: a real no-op is 0 verts / +0.0 bounds (voxel
			// round 1 signature). Pre-scaled specs (AncientSparse 1.6-1.85x)
			// legitimately grow the box by less than half a LeavesSize.
			if (PuffedVerts == 0 || Growth.GetMax() < 0.25 * LeavesSize)
			{
				// Hard gate: a silent no-op here re-opens the swiss-cheese
				// defect (voxel round 1 taught us exit codes lie).
				UE_LOG(LogOWTreeVariants, Error,
					TEXT("%s: leaf puff bake no-oped (%d verts, bounds growth %.1f vs LeavesSize %.1f)"),
					*V.OutName, PuffedVerts, Growth.GetMax(), LeavesSize);
				return false;
			}
		}
		else
		{
			UE_LOG(LogOWTreeVariants, Display,
				TEXT("%s: isFluffy=false on %s - no puff baked (correct for needle foliage)"),
				*V.OutName, *FoliageMI->GetName());
		}

		// LD4: the trunk capsule, measured on the finished geometry.
		FCapsuleResult Capsule;
		Capsule.Name = V.OutName;
		Capsule.Kind = Spec.bBush ? TEXT("bush") : (Spec.StumpCutFraction > 0.0f ? TEXT("stump") : (Spec.bNoCanopy ? TEXT("dead") : TEXT("tree")));
		if (!Spec.bBush && !MeasureTrunkCapsule(Out, TrunkMatID, Spec.StumpCutFraction > 0.0f, Capsule))
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: no trunk triangles to size the capsule from"), *V.OutName);
			return false;
		}

		bool bCreated = false;
		UStaticMesh* Target = GetOrCreateMeshAsset(FString(OutDir) / V.OutName, bCreated);
		if (const UBodySetup* Prev = bCreated ? nullptr : Target->GetBodySetup())
		{
			Capsule.PrevShapes = Prev->AggGeom.GetElementCount();
			Capsule.PrevFlag = TraceFlagName(Prev->CollisionTraceFlag);
		}

		// One-pass mutation (materials via options), then one build, one save.
		FGeometryScriptCopyMeshToAssetOptions Options;
		Options.bEnableRecomputeNormals = false;   // painterly normals contract
		Options.bEnableRecomputeTangents = false;
		Options.bReplaceMaterials = true;
		// Material ID order matches source slot order (MIs loaded pre-bake).
		for (int32 i = 0; i < SourceMats.Num(); ++i)
		{
			Options.NewMaterials.Add(i == TrunkMatID ? TrunkMI : FoliageMI);
		}

		Outcome = EGeometryScriptOutcomePins::Failure;
		UGeometryScriptLibrary_StaticMeshFunctions::CopyMeshToStaticMesh(
			Out, Target, Options, FGeometryScriptMeshWriteLOD(), Outcome, /*bUseSectionMaterials=*/true);
		if (Outcome != EGeometryScriptOutcomePins::Success)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: CopyMeshToStaticMesh failed"), *V.OutName);
			return false;
		}
		if (Target->GetNumSourceModels() > 0)
		{
			Target->GetSourceModel(0).BuildSettings.bRecomputeNormals = false;
			Target->GetSourceModel(0).BuildSettings.bGenerateLightmapUVs = false;
		}
		// Nanite on every tree mesh (cluster culling + auto LOD; the masked
		// two-sided SSS foliage material is Nanite-compatible in 5.8).
		// ShapePreservation=Voxelize: default decimation ERODES alpha-tested
		// leaf cards into swiss-cheese blobs at distance (paid 2026-07-27,
		// "trees look shit" round); voxelization preserves perceived canopy
		// volume instead - distant blobs render solid, on-style for painterly.
		FMeshNaniteSettings NaniteSettings = Target->GetNaniteSettings();
		NaniteSettings.bEnabled = true;
		NaniteSettings.ShapePreservation = ENaniteShapePreservation::Voxelize;
		Target->SetNaniteSettings(NaniteSettings);

		TArray<FText> BuildErrors;
		Target->Build(/*bSilent=*/true, &BuildErrors);
		for (const FText& Err : BuildErrors)
		{
			UE_LOG(LogOWTreeVariants, Warning, TEXT("%s build: %s"), Spec.OutName, *Err.ToString());
		}
		if (!Target->GetRenderData() || Target->GetRenderData()->LODResources.Num() == 0
			|| Target->GetRenderData()->LODResources[0].GetNumTriangles() <= 0)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: no renderable triangles after Build"), *V.OutName);
			return false;
		}

		// LD4: simple collision only - the trunk capsule (none on a bush), and traces use it as the complex shape too,
		// so a canopy triangle never blocks anything. After Build, so nothing the build does replaces it.
		Target->CreateBodySetup();
		if (UBodySetup* Body = Target->GetBodySetup())
		{
			Body->Modify();
			Body->RemoveSimpleCollision();
			if (!Spec.bBush)
			{
				FKSphylElem Sphyl(static_cast<float>(Capsule.Radius), static_cast<float>(Capsule.Length));
				Sphyl.Center = Capsule.Centre;
				Sphyl.Rotation = FRotator::ZeroRotator;   // a sphyl's axis is its local Z: upright
				Body->AggGeom.SphylElems.Add(Sphyl);
			}
			Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
			Body->InvalidatePhysicsData();
			Body->CreatePhysicsMeshes();
		}
		else
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: no body setup to put the collision on"), *V.OutName);
			return false;
		}

		if (!SaveMeshPackage(Target))
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("%s: save failed"), *V.OutName);
			return false;
		}
		// LD4 check, read back from the saved asset's body setup.
		if (const UBodySetup* Saved = Target->GetBodySetup())
		{
			Capsule.Capsules = Saved->AggGeom.SphylElems.Num();
			Capsule.Shapes = Saved->AggGeom.GetElementCount();
			Capsule.Flag = TraceFlagName(Saved->CollisionTraceFlag);
		}
		UE_LOG(LogOWTreeVariants, Display,
			TEXT("LD4 capsule %s: %s, %d capsule(s) of %d shape(s), %s (was %d shape(s), %s); radius %.1f, length %.1f, centre (%.1f, %.1f, %.1f), base %.1f, top %.1f (anchor z %.1f r %.1f from %d crossings; radius at z %.1f from a %d-crossing ring of %d%s, first branch %s, tree top %.1f)"),
			*Capsule.Name, *Capsule.Kind, Capsule.Capsules, Capsule.Shapes, *Capsule.Flag, Capsule.PrevShapes,
			Capsule.PrevFlag.IsEmpty() ? TEXT("new") : *Capsule.PrevFlag, Capsule.Radius, Capsule.Length,
			Capsule.Centre.X, Capsule.Centre.Y, Capsule.Centre.Z, Capsule.BaseZ, Capsule.TopZ, Capsule.AnchorZ,
			Capsule.AnchorRadius, Capsule.AnchorPoints, Capsule.SampleZ, Capsule.SampleRing,
			Capsule.SamplePoints, Capsule.bFallbackRadius ? TEXT(", FALLBACK 0.05 x height") : TEXT(""),
			Capsule.FirstBranchZ >= 0.0 ? *FString::Printf(TEXT("%.0f"), Capsule.FirstBranchZ) : TEXT("none below half height"),
			Capsule.TreeTopZ);
		GCapsules.Add(Capsule);
		const FString TrunkNote = (Spec.TrunkThicken > 1.0f)
			? FString::Printf(TEXT(", trunk x%.2f (%d verts, Rbase %.1f->%.1f)"),
				Spec.TrunkThicken, TrunkVertsMoved, RBaseBefore, RBaseAfter)
			: FString();
		UE_LOG(LogOWTreeVariants, Display,
			TEXT("%s %s: %d/%d blobs kept (keep %.2f, bare<%.2f, stub x%.2f: %d stripped, %d branch tris pruned), %d tris, puff %d verts @%.0f (+%.0f bounds)%s."),
			*V.OutName, bCreated ? TEXT("created") : TEXT("rebuilt"),
			KeepCount, Blobs.Num(), V.LeafKeep, V.BareBelow, V.StubMultiplier,
			BareStripped, BranchTrisRemoved,
			int32(Target->GetRenderData()->LODResources[0].GetNumTriangles()),
			PuffedVerts, LeavesSize, Growth.GetMax(), *TrunkNote);
		return true;
	}

	// ---- Leg dressing LD7, cut step 1 (docs/LEG_DRESSING_PLAN.md LD7): Nanite passthrough copies of the soft-class pack
	// meshes. The GT graphs draw soft classes as plain ISMs (the LD5 proxy swap), and a plain ISM never engages a
	// non-Nanite mesh's authored LODs (one LOD per component, map-sized bounds: MF1's finding, 2026-07-28), which is how
	// the pack bushes and cover plants were drawn. The copies are the vendor meshes unchanged (geometry, materials, LODs' source) with Nanite on
	// (ShapePreservation Voxelize, as the tree passthrough copies), into /Game/GrandTour/Dressing/Nanite; the vendor
	// assets are never edited. -run=OWCreateTreeVariants -GTNanitePack makes only these.
	constexpr const TCHAR* NanitePackDir = TEXT("/Game/GrandTour/Dressing/Nanite");

	bool BuildNanitePackCopy(const FString& SourcePath, const FString& OutName)
	{
		UStaticMesh* Source = LoadObject<UStaticMesh>(nullptr, *SourcePath);
		if (!Source)
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("LD7 nanite copy: missing source %s"), *SourcePath);
			return false;
		}
		const FString PackagePath = FString::Printf(TEXT("%s/%s"), NanitePackDir, *OutName);
		UStaticMesh* Target = LoadObject<UStaticMesh>(nullptr, *(PackagePath + TEXT(".") + OutName));
		const bool bCreated = Target == nullptr;
		if (!Target)
		{
			UPackage* Package = CreatePackage(*PackagePath);
			Target = DuplicateObject<UStaticMesh>(Source, Package, FName(*OutName));
			if (!Target)
			{
				UE_LOG(LogOWTreeVariants, Error, TEXT("LD7 nanite copy: DuplicateObject failed for %s"), *SourcePath);
				return false;
			}
			Target->SetFlags(RF_Public | RF_Standalone);
			FAssetRegistryModule::AssetCreated(Target);
		}
		Target->Modify();
		const int32 SourceTris = (Source->GetRenderData() && Source->GetRenderData()->LODResources.Num() > 0) ? Source->GetRenderData()->LODResources[0].GetNumTriangles() : -1;
		const bool bSourceNanite = Source->IsNaniteEnabled();
		FMeshNaniteSettings NaniteSettings = Target->GetNaniteSettings();
		NaniteSettings.bEnabled = true;
		NaniteSettings.ShapePreservation = ENaniteShapePreservation::Voxelize;
		Target->SetNaniteSettings(NaniteSettings);
		TArray<FText> BuildErrors;
		Target->Build(/*bSilent=*/true, &BuildErrors);
		for (const FText& Err : BuildErrors)
		{
			UE_LOG(LogOWTreeVariants, Warning, TEXT("%s build: %s"), *OutName, *Err.ToString());
		}
		if (!Target->GetRenderData() || Target->GetRenderData()->LODResources.Num() == 0 || !Target->IsNaniteEnabled())
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("LD7 nanite copy %s: no render data or Nanite off after Build"), *OutName);
			return false;
		}
		if (!SaveMeshPackage(Target))
		{
			UE_LOG(LogOWTreeVariants, Error, TEXT("LD7 nanite copy %s: save failed"), *OutName);
			return false;
		}
		UE_LOG(LogOWTreeVariants, Display, TEXT("LD7 nanite copy %s %s from %s: source Nanite %d, %d LOD(s), LOD0 %d tris; copy Nanite %d, %d material(s)"),
			*OutName, bCreated ? TEXT("created") : TEXT("rebuilt"), *SourcePath, bSourceNanite ? 1 : 0, Source->GetNumLODs(), SourceTris,
			Target->IsNaniteEnabled() ? 1 : 0, Target->GetStaticMaterials().Num());
		return true;
	}

	int32 BuildNanitePackCopies()
	{
		const TCHAR* Dir = TEXT("/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes");
		int32 Failed = 0;
		int32 Made = 0;
		for (int32 i = 1; i <= 5; ++i)
		{
			const FString Name = FString::Printf(TEXT("SM_BirchBush_%02d_Summer"), i);
			Failed += BuildNanitePackCopy(FString::Printf(TEXT("%s/Trees/Trees_Summer/%s.%s"), Dir, *Name, *Name), TEXT("SM_GTN_") + Name) ? 0 : 1;
			++Made;
		}
		for (int32 i = 1; i <= 4; ++i)
		{
			const FString Name = FString::Printf(TEXT("SM_CoverPlant_%02d_Summer"), i);
			Failed += BuildNanitePackCopy(FString::Printf(TEXT("%s/CoverPlants/CoverPlants_Summer/%s.%s"), Dir, *Name, *Name), TEXT("SM_GTN_") + Name) ? 0 : 1;
			++Made;
		}
		UE_LOG(LogOWTreeVariants, Display, TEXT("LD7 nanite copies done: %d meshes, %d failed."), Made, Failed);
		return Failed == 0 ? 0 : 1;
	}
} // namespace OWTreeVariants

int32 UOWCreateTreeVariantsCommandlet::Main(const FString& Params)
{
	using namespace OWTreeVariants;
	if (FParse::Param(*Params, TEXT("GTNanitePack")))
	{
		return BuildNanitePackCopies();
	}

	int32 Total = 0;
	int32 Failed = 0;
	for (const FVariantSpec& Spec : Specs)
	{
		for (const FResolvedVariant& V : ResolveVariations(Spec))
		{
			++Total;
			if (!BuildVariant(Spec, V))
			{
				++Failed;
			}
		}
	}
	UE_LOG(LogOWTreeVariants, Display, TEXT("OWCreateTreeVariants done: %d meshes, %d failed."),
		Total, Failed);

	// LD4 check: every tree, dead tree and stump exactly one capsule (and nothing else), every bush none; all of them
	// UseSimpleAsComplex. Written to docs/landscape_migration/ld4_variant_capsules.json as well as the log.
	int32 Solid = 0, SolidOk = 0, Bushes = 0, BushesOk = 0;
	FString Json = TEXT("{\n \"variants\": [\n");
	for (int32 i = 0; i < GCapsules.Num(); ++i)
	{
		const FCapsuleResult& C = GCapsules[i];
		const bool bSimpleAsComplex = C.Flag == TEXT("UseSimpleAsComplex");
		bool bOk = false;
		if (C.Kind == TEXT("bush"))
		{
			++Bushes;
			bOk = C.Shapes == 0 && bSimpleAsComplex;
			BushesOk += bOk ? 1 : 0;
		}
		else
		{
			++Solid;
			bOk = C.Capsules == 1 && C.Shapes == 1 && bSimpleAsComplex && C.Radius > 0.0;
			SolidOk += bOk ? 1 : 0;
		}
		Json += FString::Printf(TEXT("  {\"name\": \"%s\", \"kind\": \"%s\", \"ok\": %s, \"capsules\": %d, \"shapes\": %d, \"trace_flag\": \"%s\", \"prev_shapes\": %d, \"prev_trace_flag\": \"%s\", \"radius\": %.2f, \"length\": %.2f, \"centre\": [%.2f, %.2f, %.2f], \"base_z\": %.2f, \"top_z\": %.2f, \"anchor_z\": %.2f, \"anchor_radius\": %.2f, \"sample_z\": %.2f, \"sample_crossings\": %d, \"sample_ring\": %d, \"fallback_radius\": %s, \"first_branch_z\": %.1f, \"tree_top_z\": %.2f}%s\n"),
			*C.Name, *C.Kind, bOk ? TEXT("true") : TEXT("false"), C.Capsules, C.Shapes, *C.Flag, C.PrevShapes, *C.PrevFlag,
			C.Radius, C.Length, C.Centre.X, C.Centre.Y, C.Centre.Z, C.BaseZ, C.TopZ, C.AnchorZ, C.AnchorRadius, C.SampleZ, C.SamplePoints, C.SampleRing,
			C.bFallbackRadius ? TEXT("true") : TEXT("false"), C.FirstBranchZ, C.TreeTopZ, i + 1 < GCapsules.Num() ? TEXT(",") : TEXT(""));
	}
	const bool bCapsulesOk = Solid > 0 && SolidOk == Solid && BushesOk == Bushes && GCapsules.Num() == Total;
	Json += FString::Printf(TEXT(" ],\n \"solid\": %d, \"solid_ok\": %d, \"bushes\": %d, \"bushes_ok\": %d, \"meshes\": %d, \"failed\": %d, \"ok\": %s\n}\n"),
		Solid, SolidOk, Bushes, BushesOk, Total, Failed, (bCapsulesOk && Failed == 0) ? TEXT("true") : TEXT("false"));
	const FString ReportPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("docs/landscape_migration/ld4_variant_capsules.json"));
	FFileHelper::SaveStringToFile(Json, *ReportPath);
	UE_LOG(LogOWTreeVariants, Display,
		TEXT("LD4 capsule check: %d/%d trees, dead trees and stumps with exactly 1 capsule; %d/%d bushes with no shapes; all UseSimpleAsComplex: %s -> %s"),
		SolidOk, Solid, BushesOk, Bushes, bCapsulesOk ? TEXT("PASS") : TEXT("FAIL"), *ReportPath);
	return (Failed == 0 && bCapsulesOk) ? 0 : 1;
}
