#include "UI/SGTWorkshop.h"
#include "UI/GTWorkshopComponent.h"
#include "Core/GTPlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Input/Reply.h"

void SGTWorkshop::Construct(const FArguments&, UGTWorkshopComponent* InWorkshop) { Workshop=InWorkshop; }
void SGTWorkshop::Tick(const FGeometry& Geometry, double Time, float Delta)
{
    SLeafWidget::Tick(Geometry,Time,Delta);
    if(Workshop.IsValid()) Workshop->UpdateCamera(Delta);
}
int32 SGTWorkshop::OnPaint(const FPaintArgs&,const FGeometry& Geo,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle&,bool) const
{
    const auto* Work=Workshop.Get();
    if(!Work || !Work->IsOpen()) return Layer;
    const FVector2D Size=Geo.GetLocalSize();
    const float Scale=FMath::Min(Size.X/1280.f,Size.Y/720.f);
    const float W=Size.X/Scale, H=Size.Y/Scale;
    const FLinearColor Orange(FColor(235,111,36)), Paper(FColor(235,231,220)), Ink(FColor(21,22,23)), Muted(FColor(170,170,161));
    const FSlateBrush* Brush=FCoreStyle::Get().GetBrush("WhiteBrush");
    Hits.Reset();
    auto Box=[&](float X,float Y,float Width,float Height,FLinearColor Colour)
    {
        FSlateDrawElement::MakeBox(Out,Layer++,Geo.ToPaintGeometry(FVector2D(Width*Scale,Height*Scale),FSlateLayoutTransform(FVector2D(X*Scale,Y*Scale))),Brush,ESlateDrawEffect::None,Colour);
    };
    auto Text=[&](const FString& Value,float X,float Y,int32 Point,FLinearColor Colour,bool Bold=false)
    {
        FSlateDrawElement::MakeText(Out,Layer++,Geo.ToPaintGeometry(FVector2D(FMath::Max(W-X,1.f),FMath::Max(H-Y,1.f)),FSlateLayoutTransform(Scale,FVector2D(X*Scale,Y*Scale))),Value,FCoreStyle::GetDefaultFontStyle(Bold ? "Bold" : "Regular",Point),ESlateDrawEffect::None,Colour);
    };
    auto Line=[&](FVector2D A,FVector2D B,FLinearColor Colour,float Thickness=1.f)
    {
        TArray<FVector2D> Points{A*Scale,B*Scale};
        FSlateDrawElement::MakeLines(Out,Layer++,Geo.ToPaintGeometry(),Points,ESlateDrawEffect::None,Colour,true,Thickness*Scale);
    };
    auto Ring=[&](FVector2D Centre,float Radius,FLinearColor Colour,float Thickness=1.5f)
    {
        TArray<FVector2D> Points;
        for(int32 I=0;I<=40;++I) { const float A=I*2.f*PI/40.f; Points.Add((Centre+FVector2D(FMath::Cos(A),FMath::Sin(A))*Radius)*Scale); }
        FSlateDrawElement::MakeLines(Out,Layer++,Geo.ToPaintGeometry(),Points,ESlateDrawEffect::None,Colour,true,Thickness*Scale);
    };
    auto Hit=[&](float X,float Y,float Width,float Height,int32 Action)
    {
        FHit Item{FSlateRect(X*Scale,Y*Scale,(X+Width)*Scale,(Y+Height)*Scale),Action}; Hits.Add(Item);
        return Item.Rect.ContainsPoint(Mouse);
    };

    // Cropped title blocks recall programme titles; paper labels belong to the studio board.
    Box(28,26,186,34,Ink); Box(28,26,5,34,Orange);
    Text(TEXT("GRAND TOUR"),43,30,18,Paper,true);
    Box(28,65,116,24,Orange); Text(TEXT("WORKSHOP"),38,67,12,Ink,true);
    Box(W-270,26,242,60,FLinearColor(.012f,.012f,.012f,.88f));
    Text(Work->VehicleName(),W-255,32,17,Paper,true);
    Text(Work->bComparing ? TEXT("COMPARING / FITTED") : Work->HasPendingChange() ? TEXT("PREVIEW / NOT FITTED") : Work->SelectedPart>=0 ? TEXT("CURRENTLY FITTED") : TEXT("WALK AROUND"),W-255,59,10,Work->SelectedPart>=0 ? Orange : Muted,true);

    FVector2D SelectedPoint(0,0);
    const TCHAR* PartNames[]={TEXT("PAINT"),TEXT("WHEELS"),TEXT("TYRES"),TEXT("SUSPENSION"),TEXT("EQUIPMENT"),TEXT("ENGINE KIT"),TEXT("DRIVE LAYOUT")};
    for(int32 I=0;I<7;++I)
    {
        if(!Work->PartAvailable(I)) continue;
        FVector2D Screen;
        if(!Work->Controller()->ProjectWorldLocationToScreen(Work->Hotspot(I),Screen,true)) continue;
        // Projection is in viewport pixels; the widget's desktop scale can differ on HiDPI displays.
        int32 VX=0,VY=0; Work->Controller()->GetViewportSize(VX,VY);
        FVector2D P(Screen.X*Size.X/FMath::Max(VX,1)/Scale,Screen.Y*Size.Y/FMath::Max(VY,1)/Scale);
        if(P.X<30 || P.X>W-30 || P.Y<105 || P.Y>H-80) continue;
        const bool Selected=Work->SelectedPart==I;
        if(Selected) SelectedPoint=P;
        Ring(P,Selected ? 13.f : 8.f,Selected ? Orange : Paper,Selected ? 2.5f : 1.5f);
        Box(P.X-2,P.Y-2,4,4,Selected ? Orange : Paper);
        // Paint labels rise above the bonnet; wheel labels sit below the contact points.
        const float LabelWidth=I==6 ? 126.f : I>=3 ? 112.f : 81.f;
        const bool LabelAbove=I==0 || I>=3;
        const FVector2D Label=P+FVector2D(I==6 ? -185.f : I==5 ? -185.f : I==0 ? -66.f : I>=3 ? -56.f : -34.f,I==6 ? 72.f : I==5 ? -8.f : I==0 ? -56.f : I>=3 ? -64.f : 34.f);
        Line(P+FVector2D(0,LabelAbove ? -13.f : 13.f),Label+FVector2D(LabelWidth*.5f,LabelAbove ? 24.f : 0.f),Selected ? Orange : Paper);
        const bool Hover=Hit(Label.X-3,Label.Y-3,LabelWidth+6,30,I);
        Hit(P.X-19,P.Y-19,38,38,I);
        Box(Label.X+3,Label.Y+3,LabelWidth,24,FLinearColor(0,0,0,.35f));
        Box(Label.X,Label.Y,LabelWidth,24,Selected || Hover ? Orange : Paper);
        Text(PartNames[I],Label.X+9,Label.Y+3,11,Ink,true);
        if(Selected && I>0) Ring(P,35.f,Orange,1.4f);
    }

    if(Work->SelectedPart>=0)
    {
        const int32 Count=Work->OptionCount();
        const float SplitHeight=Work->ShowAWDSplit() ? 64.f : 0.f;
        const float CardW=304.f, CardH=174.f+Count*35.f+(Work->SelectedPart>=5 ? 34.f : 0.f)+SplitHeight;
        const float X=W-CardW-28, Y=H-CardH-82;
        if(SelectedPoint.X>0) { Line(SelectedPoint+FVector2D(16,0),FVector2D(X-18,Y+25),Orange); Line(FVector2D(X-18,Y+25),FVector2D(X,Y+25),Orange); }
        Hit(X,Y,CardW,CardH,99); // card whitespace consumes clicks instead of orbiting
        Box(X+5,Y+5,CardW,CardH,FLinearColor(0,0,0,.35f));
        Box(X,Y,CardW,CardH,FLinearColor(.009f,.01f,.011f,.97f));
        Box(X,Y,4,CardH,Orange);
        Text(Work->SelectedPart==0 ? TEXT("BODY PAINT") : Work->SelectedPart==1 ? TEXT("WHEEL DESIGN") : Work->SelectedPart==2 ? TEXT("TYRE SET") : Work->SelectedPart==3 ? TEXT("SUSPENSION") : Work->SelectedPart==6 ? TEXT("DRIVE LAYOUT") : Work->SelectedPart==5 ? TEXT("ENGINE PACKAGE") : TEXT("BOLT-ON EQUIPMENT"),X+17,Y+13,19,Paper,true);
        Text(Work->SelectedPart==0 ? TEXT("A change of character.") : Work->SelectedPart==1 ? TEXT("Choose your rims.") : Work->SelectedPart==2 ? TEXT("Choose your footing.") : Work->SelectedPart==3 ? TEXT("Set the stance. Find your ride.") : Work->SelectedPart==6 ? TEXT("Choose which wheels do the work.") : Work->SelectedPart==5 ? TEXT("Choose your engine and gearing.") : TEXT("Add or remove each part."),X+17,Y+42,11,Muted);
        for(int32 I=0;I<Count;++I)
        {
            const float RY=Y+66+I*35.f;
            const bool Selected=I==Work->SelectedOption;
            const bool Hover=Hit(X+15,RY,CardW-30,30,10+I);
            Box(X+15,RY,CardW-30,30,Selected ? Paper : Hover ? FLinearColor(.12f,.12f,.115f) : FLinearColor(.055f,.055f,.052f));
            if(Work->SelectedPart<2)
            {
                Box(X+22,RY+6,18,18,Work->SelectedPart==0 ? UGTWorkshopComponent::PaintColour(I) : UGTWorkshopComponent::RimColour(I));
                Text(Work->OptionName(I),X+49,RY+5,12,Selected ? Ink : Paper,Selected);
            }
            else Text(Work->OptionName(I),X+25,RY+5,12,Selected ? Ink : Paper,Selected);
            if(Selected) Box(X+15,RY,3,30,Orange);
        }
        const float DY=Y+69+Count*35.f;
        if(Work->ShowAWDSplit())
        {
            const int32 Front=Work->DisplayFrontPercent();
            Box(X+15,DY,32,25,FLinearColor(.16f,.16f,.15f));
            Box(X+257,DY,32,25,FLinearColor(.16f,.16f,.15f));
            Hit(X+15,DY,32,25,40); Hit(X+257,DY,32,25,41);
            Text(TEXT("<"),X+25,DY+2,12,Paper,true); Text(TEXT(">"),X+267,DY+2,12,Paper,true);
            Text(FString::Printf(TEXT("%d%% FRONT / %d%% REAR"),Front,100-Front),X+58,DY+3,11,Paper,true);
            Box(X+16,DY+31,272,5,Muted); Box(X+16,DY+31,272*Front*.01f,5,Orange);
            Text(TEXT("LEFT  More rear       RIGHT  More front"),X+19,DY+43,9,Muted);
        }
        Text(Work->Detail(),X+17,DY+SplitHeight,9,Muted);
        const bool Fit=Work->CanFit();
        const float BY=Y+CardH-39;
        const bool HoverFit=Hit(X+15,BY,92,27,30);
        Box(X+15,BY,92,27,Fit ? Orange : FLinearColor(.10f,.10f,.10f));
        Text(Work->SelectedPart==4 ? TEXT("ENTER / APPLY") : TEXT("ENTER / FIT"),X+21,BY+5,9,Fit ? Ink : Muted,true);
        const bool HoverCompare=Hit(X+113,BY,105,27,31);
        Box(X+113,BY,105,27,Work->bComparing || HoverCompare ? FLinearColor(.2f,.2f,.18f) : FLinearColor(.07f,.07f,.065f));
        Text(TEXT("HOLD COMPARE"),X+119,BY+5,9,Paper,true);
        Hit(X+223,BY,67,27,32); Text(TEXT("CANCEL"),X+231,BY+5,9,Paper,true);
        if(!Work->Message.IsEmpty()) Text(Work->Message,X+16,Y+CardH+8,10,Orange);
        else if(!Fit) Text(Work->FitReason(),X+16,Y+CardH+8,9,Paper);
    }
    else
    {
        Box(28,H-120,300,36,FLinearColor(0,0,0,.75f));
        Text(Work->Message.IsEmpty() ? TEXT("Pick a part. Make it yours.") : Work->Message,42,H-112,13,Paper);
    }
    Box(0,H-48,W,48,FLinearColor(.009f,.009f,.009f,.86f));
    Text(Work->ShowAWDSplit() ? TEXT("DRAG  Orbit   WHEEL  Zoom   TAB  Parts   UP/DOWN  Choices   LEFT/RIGHT  Split   SPACE  Compare") : TEXT("DRAG  Orbit     WHEEL  Zoom     TAB  Parts     ARROWS  Choices     SPACE  Compare"),28,H-31,10,Paper);
    const bool BackHover=Hit(W-165,H-43,145,38,33);
    Text(TEXT("U  BACK TO DRIVE"),W-164,H-31,10,BackHover ? Orange : Paper,true);
    return Layer;
}

FReply SGTWorkshop::OnMouseButtonDown(const FGeometry& Geo,const FPointerEvent& Event)
{
    auto* Work=Workshop.Get(); if(!Work) return FReply::Unhandled();
    Mouse=Geo.AbsoluteToLocal(Event.GetScreenSpacePosition());
    if(Event.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        for(int32 I=Hits.Num()-1;I>=0;--I) if(Hits[I].Rect.ContainsPoint(Mouse))
        {
            const int32 Action=Hits[I].Action;
            if(Action<7) Work->SelectPart(Action);
            else if(Action>=10 && Action<20) Work->Preview(Action-10);
            else if(Action==30) Work->Fit();
            else if(Action==31) { Work->Compare(true); bPointerCompare=true; return FReply::Handled().CaptureMouse(SharedThis(this)); }
            else if(Action==32) Work->Cancel();
            else if(Action==33) Work->Close();
            else if(Action==40) Work->AdjustAWDSplit(-1);
            else if(Action==41) Work->AdjustAWDSplit(1);
            return FReply::Handled();
        }
    }
    if(Event.GetEffectingButton()==EKeys::LeftMouseButton || Event.GetEffectingButton()==EKeys::RightMouseButton)
    { bDragging=true; return FReply::Handled().CaptureMouse(SharedThis(this)); }
    return FReply::Handled();
}
FReply SGTWorkshop::OnMouseMove(const FGeometry& Geo,const FPointerEvent& Event)
{
    const FVector2D Position=Geo.AbsoluteToLocal(Event.GetScreenSpacePosition());
    if(bDragging && Workshop.IsValid()) Workshop->Orbit(Position.X-Mouse.X,Position.Y-Mouse.Y);
    Mouse=Position; return FReply::Handled();
}
FReply SGTWorkshop::OnMouseButtonUp(const FGeometry&,const FPointerEvent&)
{
    bDragging=false;
    if(bPointerCompare && Workshop.IsValid()) Workshop->Compare(false);
    bPointerCompare=false; return FReply::Handled().ReleaseMouseCapture();
}
FReply SGTWorkshop::OnMouseWheel(const FGeometry&,const FPointerEvent& Event)
{ if(Workshop.IsValid()) Workshop->Zoom(Event.GetWheelDelta()); return FReply::Handled(); }
void SGTWorkshop::OnMouseCaptureLost(const FCaptureLostEvent&)
{ bDragging=false; bPointerCompare=false; if(Workshop.IsValid()) Workshop->Compare(false); }
void SGTWorkshop::OnFocusLost(const FFocusEvent& Event)
{ if(Workshop.IsValid()) Workshop->Compare(false); SLeafWidget::OnFocusLost(Event); }
FReply SGTWorkshop::OnKeyDown(const FGeometry&,const FKeyEvent& Event)
{
    auto* Work=Workshop.Get(); if(!Work) return FReply::Unhandled();
    const FKey Key=Event.GetKey();
    if(Key==EKeys::Escape || Key==EKeys::Gamepad_FaceButton_Right)
    { if(Work->SelectedPart>=0) Work->Cancel(); else Work->Close(); }
    else if(Key==EKeys::U) Work->Close();
    else if(Key==EKeys::Tab || Key==EKeys::Gamepad_RightShoulder) Work->SelectPart(Work->NextPart());
    else if(Key==EKeys::SpaceBar && !Event.IsRepeat()) Work->Compare(true);
    else if(Key==EKeys::Enter || Key==EKeys::Gamepad_FaceButton_Bottom) Work->Fit();
    else if(Work->ShowAWDSplit() && (Key==EKeys::Left || Key==EKeys::Gamepad_DPad_Left)) Work->AdjustAWDSplit(-1);
    else if(Work->ShowAWDSplit() && (Key==EKeys::Right || Key==EKeys::Gamepad_DPad_Right)) Work->AdjustAWDSplit(1);
    else if(Key==EKeys::Down || Key==EKeys::Right || Key==EKeys::Gamepad_DPad_Down)
    { if(Work->OptionCount()) Work->Preview((Work->SelectedOption+1)%Work->OptionCount()); }
    else if(Key==EKeys::Up || Key==EKeys::Left || Key==EKeys::Gamepad_DPad_Up)
    { if(Work->OptionCount()) Work->Preview((Work->SelectedOption+Work->OptionCount()-1)%Work->OptionCount()); }
    return FReply::Handled(); // driving/debug keys must not leak into the pawn
}
FReply SGTWorkshop::OnKeyUp(const FGeometry&,const FKeyEvent& Event)
{ if(Event.GetKey()==EKeys::SpaceBar && Workshop.IsValid()) Workshop->Compare(false); return FReply::Handled(); }
