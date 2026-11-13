#include "Terrain/GTGroundedDressing.h"
#include "Terrain/GTLandscapeSurface.h"
#include "Components/MeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
void AGTGroundedDressing::BeginPlay()
{
 Super::BeginPlay();
 if(!GroundSurface)return;
 TArray<UMeshComponent*> Meshes;GetComponents(Meshes);
 for(UMeshComponent* Mesh:Meshes)
 {
  // Collision-bearing wood/rocks must not move visually away from their body.
  if(Mesh->GetCollisionEnabled()!=ECollisionEnabled::NoCollision)continue;
  for(int32 I=0;I<Mesh->GetNumMaterials();++I)
   if(UMaterialInstanceDynamic* M=Mesh->CreateDynamicMaterialInstance(I))GroundSurface->RegisterResearchMaterial(M);
 }
}
