#pragma once

#include "Widgets/SLeafWidget.h"

class UGTWorkshopComponent;

/** Small contextual board over the live vehicle, with no persistent category rail. */
class SGTWorkshop : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SGTWorkshop) {} SLATE_END_ARGS()
    void Construct(const FArguments&, UGTWorkshopComponent* InWorkshop);
    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(1280,720); }
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual void Tick(const FGeometry&, double, float Delta) override;
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry&, const FSlateRect&, FSlateWindowElementList&, int32, const FWidgetStyle&, bool) const override;
    virtual FReply OnMouseButtonDown(const FGeometry&, const FPointerEvent&) override;
    virtual FReply OnMouseButtonUp(const FGeometry&, const FPointerEvent&) override;
    virtual FReply OnMouseMove(const FGeometry&, const FPointerEvent&) override;
    virtual FReply OnMouseWheel(const FGeometry&, const FPointerEvent&) override;
    virtual void OnMouseCaptureLost(const FCaptureLostEvent&) override;
    virtual FReply OnKeyDown(const FGeometry&, const FKeyEvent&) override;
    virtual FReply OnKeyUp(const FGeometry&, const FKeyEvent&) override;
    virtual void OnFocusLost(const FFocusEvent&) override;
private:
    struct FHit { FSlateRect Rect; int32 Action; };
    TWeakObjectPtr<UGTWorkshopComponent> Workshop;
    mutable TArray<FHit> Hits;
    FVector2D Mouse = FVector2D(-1000,-1000);
    bool bDragging = false;
    bool bPointerCompare = false;
};
