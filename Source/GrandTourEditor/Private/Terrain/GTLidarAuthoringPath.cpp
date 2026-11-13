#include "GTLidarAuthoringPath.h"
#include "Components/SplineComponent.h"

AGTLidarAuthoringPath::AGTLidarAuthoringPath()
{
    bIsEditorOnlyActor=true;
    ControlPoints=CreateDefaultSubobject<USplineComponent>(TEXT("DesignPoints"));
    SetRootComponent(ControlPoints);
    ControlPoints->SetDrawDebug(true);
}
