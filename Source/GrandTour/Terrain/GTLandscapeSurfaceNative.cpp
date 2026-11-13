#include "Terrain/GTLandscapeSurfaceField.h"
#include "Terrain/GTMudRunnerUpdate.h"

void FGTLandscapeSurfaceField::StampNative(FVector2D Start,FVector2D End,FVector2D Heading,
    float Width,float Depth,TFunctionRef<FLinearColor(FVector2D)> Paint,float Plane,float MaxCut,FWheelWork Work)
{
    if(!FMath::IsFinite(Width) || Width<=0 || !FMath::IsFinite(Depth) || Depth<=0) return;
    if(FVector2D::Distance(Start,End)>200)Start=End;
    Heading=Heading.GetSafeNormal();if(Heading.IsNearlyZero())Heading=FVector2D(1,0);
    const FVector2D Side(-Heading.Y,Heading.X),Move=End-Start;
    const float HalfWidth=FMath::Clamp(Width*.5f,5.f,50.f);
    const float Reach=HalfWidth+65.f;
    FPushContact PushContact;
    const FIntPoint Lo(FMath::FloorToInt((FMath::Min(Start.X,End.X)-Reach)/CellCm),FMath::FloorToInt((FMath::Min(Start.Y,End.Y)-Reach)/CellCm));
    const FIntPoint Hi(FMath::CeilToInt((FMath::Max(Start.X,End.X)+Reach)/CellCm),FMath::CeilToInt((FMath::Max(Start.Y,End.Y)+Reach)/CellCm));
    // Contact-raster bridge, not a recovered native wheel mesh: a swept tyre oval
    // supplies ConvertExtrudes' surface-minus-contact-depth difference.
    for(int32 Y=Lo.Y;Y<=Hi.Y;++Y)for(int32 X=Lo.X;X<=Hi.X;++X)
    {
        const FIntPoint Key(X,Y);auto* C=Edit(Key);if(!C)continue;
        const FVector2D P=Centre(Key);const auto Mask=Paint(P);if(Mask.R<=.01f || (NativeUpdateAt && !NativeUpdateAt(P)))continue;
        const double T=Move.SizeSquared()>.01 ? FMath::Clamp(FVector2D::DotProduct(P-Start,Move)/Move.SizeSquared(),0.,1.) : 0.;
        const FVector2D D=P-(Start+Move*T);
        const float Across=float(FVector2D::DotProduct(D,Side)),Along=float(FVector2D::DotProduct(D,Heading));
        const float Ellipse=FMath::Square(Across/(HalfWidth+6.25f))+FMath::Square(Along/24.f);
        const float Coverage=FMath::Clamp((1.f-Ellipse)*2.f,0.f,1.f);
        if(Coverage<=0)
        {
            // Host footprint adapter: broken shoulders and a slip-dependent toe/heel.
            // Native evidence establishes separate push geometry, RED/MAX compositing
            // and a later GB-only pass; these Chaos contact weights are not its mesh.
            const float Lateral=FMath::Abs(Across)-HalfWidth;
            const float Shoulder=FMath::Max(0.f,1.f-FMath::Abs(Lateral-18.f)/28.f)
                *FMath::Max(0.f,1.f-FMath::Abs(Along)/32.f);
            const float Slip=Work.Enabled ? FMath::Clamp(Work.Slip,0.f,1.f) : 0.f;
            const float Bow=FMath::Max(0.f,1.f-FMath::Abs(Along-(Slip>.5f ? -32.f : 32.f))/28.f)
                *FMath::Max(0.f,1.f-FMath::Abs(Across)/(HalfWidth+10.f))
                *(Work.Enabled ? FMath::Max(Slip,Work.Motion) : .25f);
            const float Weight=FMath::Max(Shoulder,Bow);if(Weight<=0)continue;
            if(NativeBaseAlpha && NativeBaseAlpha(P)<=.75f)continue;
            const float Rest=RestHeight(P,Mask.R);
            const float Cohesion=ShapeAt ? FMath::Clamp(ShapeAt(P).G,0.f,1.f) : .7f;
            const float Ceiling=FMath::Min(LipCapCm,Rest+FMath::Lerp(6.f,13.f,Cohesion));
            const float Room=FMath::Max(0.f,Ceiling-C->DeltaCm)*Weight;
            if(Room>0)
            {
                const FVector2D Flow=(Side*(Across<0 ? -.8f : .8f)+Heading*(Bow*(1.f-2.f*Slip))).GetSafeNormal();
                PushContact.Receivers.Add({Key,Room,Ceiling,FVector2f(Flow)});
            }
            continue;
        }
        NativeContactCells.Add(Key); // includes settled tyres that no longer excavate
        const float Contact=Plane==MAX_flt ? RestHeight(P,Mask.R)-Depth : Plane;
        const float Cut=FMath::Min(FMath::Max(0.f,C->DeltaCm-FMath::Max(-Mask.R,Contact)),MaxCut)*Coverage;
        if(Cut<=0)continue;
        // ConvertExtrudes_004: max((mudHeight-contactHeight)/2.04,0).
        float& Aux=NativeAux.FindOrAdd(Key);Aux=FMath::Max(Aux,Cut/204.f);
        PushContact.Sources.Add(Key);
    }
    if(!PushContact.Sources.IsEmpty() && !PushContact.Receivers.IsEmpty())NativePushContacts.Add(MoveTemp(PushContact));
}

void FGTLandscapeSurfaceField::StepNative()
{
    if(NativeAux.IsEmpty()){NativePushContacts.Reset();NativeContactCells.Reset();return;}
    TSet<FIntPoint> Affected;
    // The original 5x5 loop has zero weights at radius >=2; keep all offsets
    // explicitly to retain that geometry and sample the previous state everywhere.
    constexpr int32 Stride=4; // 25 cm / existing 6.25 cm field cell.
    for(const auto& P:NativeAux)for(int32 Y=-2;Y<=2;++Y)for(int32 X=-2;X<=2;++X)
        Affected.Add(P.Key+FIntPoint(X*Stride,Y*Stride));
    struct FPending {FIntPoint Key;FLinearColor Value;};TArray<FPending> Pending;
    for(const FIntPoint Key:Affected)
    {
        const auto* C=Edit(Key);if(!C)continue;
        if(NativeUpdateAt && !NativeUpdateAt(Centre(Key)))continue;
        const float Gate=NativeBaseAlpha ? NativeBaseAlpha(Centre(Key)) : 1.f;
        if(Gate<=.75f)continue;
        const float R=GTMudRunnerUpdate::EncodeHeight(C->DeltaCm);
        float Received=0;
        for(int32 Y=-2;Y<=2;++Y)for(int32 X=-2;X<=2;++X)
        {
            if(X==0 && Y==0)continue;
            const FIntPoint N=Key+FIntPoint(X*Stride,Y*Stride);
            const float Aux=NativeAux.FindRef(N);if(Aux<=0)continue;
            Received+=GTMudRunnerUpdate::Incoming(R,GTMudRunnerUpdate::EncodeHeight(Read(N).DeltaCm),Aux,float(X),float(Y));
        }
        const FLinearColor Packed(R,C->SlideCm.X/22.5f+.5f,C->SlideCm.Y/22.5f+.5f,C->Track);
        Pending.Add({Key,GTMudRunnerUpdate::Update(Packed,NativeAux.FindRef(Key),Received,Gate)});
    }
    bool bGeometryChanged=false;
    TMap<FIntPoint,float> Removed;
    float IncomingSum=0;
    for(const auto& P:Pending)
    {
        auto* C=Edit(P.Key);if(!C)continue;
        const float Previous=C->DeltaCm;
        const FVector2f PreviousSlide=C->SlideCm;
        const float PreviousTrack=C->Track;
        // Keep fractional state in the host float field. Original target-format
        // quantization/cadence is not asserted here; quantization is tested separately.
        C->DeltaCm=FMath::Min(LipCapCm,GTMudRunnerUpdate::DecodeHeight(P.Value.R));
        C->SlideCm=FVector2f((P.Value.G-.5f)*22.5f,(P.Value.B-.5f)*22.5f);
        C->Track=FMath::Clamp(P.Value.A,0.f,1.f);
        const float Change=C->DeltaCm-Previous;
        if(FMath::Abs(Change)>1.e-4f)
        {
            C->Fresh=1.f;C->Turbidity=FMath::Min(1.f,C->Turbidity+FMath::Abs(Change)/10.f);
            if(Change<0){ExcavatedCm3-=Change*CellCm*CellCm;Removed.Add(P.Key,-Change);}
            else {DepositedCm3+=Change*CellCm*CellCm;IncomingSum+=Change;}
            MarkChanged(P.Key,true);++NativeUpdateCells;
            bGeometryChanged=true;
        }
        else if(!PreviousSlide.Equals(C->SlideCm,1.e-5f) || FMath::Abs(PreviousTrack-C->Track)>1.e-5f)
        {MarkChanged(P.Key,true);bGeometryChanged=true;}
    }
    // Update's own incoming transport already spent part of the removed volume.
    // The remaining contact budget prevents overlap/repeated stationary stamps
    // from creating soil. Native shaders themselves do not guarantee conservation.
    float RemovedSum=0;for(const auto& P:Removed)RemovedSum+=P.Value;
    const float AvailableFraction=RemovedSum>0 ? FMath::Clamp(1.f-IncomingSum/RemovedSum,0.f,1.f) : 0.f;
    TMap<FIntPoint,float> Raised;
    for(const auto& Contact:NativePushContacts)
    {
        float Budget=0;
        for(const auto Key:Contact.Sources)
            if(float* Amount=Removed.Find(Key)){Budget+=*Amount*AvailableFraction;*Amount=0;}
        if(Budget<=1.e-5f)continue;
        float Capacity=0;
        for(const auto& Receiver:Contact.Receivers)
            if(!NativeContactCells.Contains(Receiver.Key) && IsActive(Receiver.Key))
                Capacity+=FMath::Min3(Receiver.Capacity,FMath::Max(0.f,Receiver.Ceiling-Read(Receiver.Key).DeltaCm),FMath::Max(0.f,1.6f-Raised.FindRef(Receiver.Key)));
        if(Capacity<=0)continue;
        const float Fraction=FMath::Min(1.f,Budget/Capacity);
        for(const auto& Receiver:Contact.Receivers)
        {
            if(NativeContactCells.Contains(Receiver.Key))continue; // never fill another loaded tyre
            auto* C=Edit(Receiver.Key);if(!C)continue;
            const float Raise=FMath::Min3(Receiver.Capacity,FMath::Max(0.f,Receiver.Ceiling-C->DeltaCm),FMath::Max(0.f,1.6f-Raised.FindRef(Receiver.Key)))*Fraction;
            if(Raise<=1.e-5f)continue;
            const float Point=GTMudRunnerUpdate::EncodeHeight(C->DeltaCm);
            // 0x1408ed250's absent-reference mode supplies strength=0. The native
            // shader caps rises at 2/255; 0x1408f1148..1303 writes RED with MAX.
            const float Candidate=GTMudRunnerUpdate::Push(Point,Point,
                GTMudRunnerUpdate::EncodeHeight(FMath::Min(LipCapCm,C->DeltaCm+Raise)),0.f,0.f);
            const float Next=GTMudRunnerUpdate::DecodeHeight(FMath::Max(Point,Candidate));
            const float Actual=FMath::Max(0.f,Next-C->DeltaCm);if(Actual<=1.e-5f)continue;
            C->DeltaCm=Next;Raised.FindOrAdd(Receiver.Key)+=Actual;
            // Separate GB writer, as in 0x1408f13bb..1492. Host displacement
            // magnitude; keep the recovered encoded +/-11.25cm representable range.
            C->SlideCm+=Receiver.Direction*(Actual*.65f);
            C->SlideCm.X=FMath::Clamp(C->SlideCm.X,-11.25f,11.25f);
            C->SlideCm.Y=FMath::Clamp(C->SlideCm.Y,-11.25f,11.25f);
            C->Fresh=1;C->Turbidity=FMath::Min(1.f,C->Turbidity+Actual/10.f);
            C->Track=FMath::Max(C->Track,.15f);
            DepositedCm3+=Actual*CellCm*CellCm;++NativePushCells;
            MarkChanged(Receiver.Key,true);bGeometryChanged=true;
        }
    }
    // Publish the batch after marking its blocks. Water-bed and shadow consumers
    // compare this revision; texture dirtiness alone does not notify them.
    if(bGeometryChanged)++GeometryRevision;
    NativeAux.Reset();
    NativePushContacts.Reset();
    NativeContactCells.Reset();
}
