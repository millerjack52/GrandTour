#include "Terrain/GTMudRunnerClod.h"
#include "Components/StaticMeshComponent.h"
#include "PhysicsEngine/PhysicsConstraintComponent.h"
AGTMudRunnerClod::AGTMudRunnerClod()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostPhysics;
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));SetRootComponent(Body);
    Body->SetMobility(EComponentMobility::Movable);Body->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Body->BodyInstance.bUseCCD=true;
    Anchor=CreateDefaultSubobject<UPhysicsConstraintComponent>(TEXT("NativeFixedRoot"));
    Anchor->SetupAttachment(Body);
    Anchor->SetLinearXLimit(ELinearConstraintMotion::LCM_Locked,0);
    Anchor->SetLinearYLimit(ELinearConstraintMotion::LCM_Locked,0);
    Anchor->SetLinearZLimit(ELinearConstraintMotion::LCM_Locked,0);
    Anchor->SetAngularSwing1Limit(EAngularConstraintMotion::ACM_Locked,0);
    Anchor->SetAngularSwing2Limit(EAngularConstraintMotion::ACM_Locked,0);
    Anchor->SetAngularTwistLimit(EAngularConstraintMotion::ACM_Locked,0);
}
void AGTMudRunnerClod::BeginPlay()
{
    Super::BeginPlay();
    // Media.zip plants/mud_chunk_a,b: mass 10/20 kg, b damping 1/1.
    Body->SetMassOverrideInKg(NAME_None,bLarge?20:10,true);
    // The source allows 0.5m penetration on these buried clods. Chaos does not
    // expose that Havok contact allowance. While fixed, exclude the static bed
    // and other buried clods; vehicle bodies and suspension queries still block.
    Body->SetCollisionObjectType(ECC_Destructible);
    Body->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Ignore);
    Body->SetCollisionResponseToChannel(ECC_Destructible,ECR_Ignore);
    if(bLarge){Body->SetLinearDamping(1);Body->SetAngularDamping(1);}
    Body->SetSimulatePhysics(true);
    Anchor->SetConstrainedComponents(Body,NAME_None,nullptr,NAME_None);
}
void AGTMudRunnerClod::Tick(float Dt)
{
    Super::Tick(Dt);if(bReleased)return;
    FVector Force,Torque;Anchor->GetConstraintForce(Force,Torque);
    // 0x14087cbb3 stores BreakOffThreshold=100 directly in hkpBreakableConstraintData.
    // Chaos reports force in kg*cm/s². Compare its integrated linear reaction in N*s.
    // Constraint solving/convex hull and frame integration remain Chaos adapters.
    if(Force.Size()*.01*Dt>100)
    {
        Anchor->BreakConstraint();bReleased=true;
        Body->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);Body->SetCollisionResponseToChannel(ECC_Destructible,ECR_Block);
        Body->WakeAllRigidBodies();SetActorTickEnabled(false);
    }
}
void AGTMudRunnerClod::ReviewImpulse(FVector J)
{
    if(J.Size()>100)
    {
        Anchor->BreakConstraint();bReleased=true;SetActorTickEnabled(false);
        Body->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);Body->SetCollisionResponseToChannel(ECC_Destructible,ECR_Block);
    }
    Body->AddImpulse(J*100,NAME_None,false);
}
