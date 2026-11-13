#include "Look/GTRenderOptimisationLibrary.h"
#include "Engine/SkeletalMesh.h"
#include "SkeletalMeshReductionSettings.h"

TArray<float> UGTRenderOptimisationLibrary::GetSkeletalLODScreenSizes(USkeletalMesh* Mesh)
{
	TArray<float> Result;
#if WITH_EDITOR
	if (Mesh)
	{
		for (int32 Index = 0; Index < Mesh->GetLODNum(); ++Index)
		{
			const FSkeletalMeshLODInfo* Info = Mesh->GetLODInfo(Index);
			if (!Info) return {};
			Result.Add(Info->ScreenSize.Default);
		}
	}
#endif
	return Result;
}

bool UGTRenderOptimisationLibrary::ConfigureGeneratedFarLOD(USkeletalMesh* Mesh, int32 LODIndex, int32 MaxVertices, float ScreenSize)
{
#if WITH_EDITOR
	if (!Mesh || LODIndex < 3 || LODIndex != Mesh->GetLODNum() - 1 ||
		MaxVertices < 8000 || MaxVertices > 50000 || !FMath::IsFinite(ScreenSize) || ScreenSize <= 0.f)
	{
		return false;
	}
	FSkeletalMeshLODInfo* Info = Mesh->GetLODInfo(LODIndex);
	const FSkeletalMeshLODInfo* Previous = Mesh->GetLODInfo(LODIndex - 1);
	if (!Info || !Previous || !Info->bHasBeenSimplified || ScreenSize >= Previous->ScreenSize.Default)
	{
		return false;
	}
	Mesh->Modify();
	Info->ScreenSize.Default = ScreenSize;
	FSkeletalMeshOptimizationSettings& Reduction = Info->ReductionSettings;
	Reduction.BaseLOD = LODIndex - 1;
	Reduction.TerminationCriterion = SMTC_AbsNumOfVerts;
	Reduction.MaxNumOfVerts = static_cast<uint32>(MaxVertices);
	Reduction.bEnforceBoneBoundaries = true;
	Reduction.bRecalcNormals = false;
	Reduction.bImproveTrianglesForCloth = false;
	return true;
#else
	return false;
#endif
}
