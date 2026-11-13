#include "Terrain/GTRoadWaterMesh.h"
#include "ProceduralMeshComponent.h"
AGTRoadWaterMesh::AGTRoadWaterMesh()
{
    Mesh=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("RoadPool"));SetRootComponent(Mesh);
    Mesh->SetMobility(EComponentMobility::Static);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetCastShadow(false);Mesh->bAffectDistanceFieldLighting=false;
}
