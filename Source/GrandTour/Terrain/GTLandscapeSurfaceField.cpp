#include "Terrain/GTLandscapeSurfaceField.h"
#include "Terrain/GTMudRunnerUpdate.h"
#include "Core/GTPerfProbe.h"

namespace GTLandscapeField
{
    float Hash(int32 X, int32 Y, uint32 Seed = 0)
    {
        uint32 H = uint32(X) * 374761393u + uint32(Y) * 668265263u + Seed * 2246822519u;
        H = (H ^ (H >> 13)) * 1274126177u;
        return float((H ^ (H >> 16)) & 0x00ffffffu) / 16777215.f;
    }
    float Noise(FVector2D P)
    {
        const int32 X = FMath::FloorToInt(P.X), Y = FMath::FloorToInt(P.Y);
        const float U = FMath::SmoothStep(0.f, 1.f, float(P.X-X));
        const float V = FMath::SmoothStep(0.f, 1.f, float(P.Y-Y));
        return FMath::Lerp(FMath::Lerp(Hash(X,Y), Hash(X+1,Y), U), FMath::Lerp(Hash(X,Y+1), Hash(X+1,Y+1), U), V);
    }
    // Deliberately sculpted cross-sections: a low sheared sheet, a folded slab, a torn wedge.
    // U runs along the disturbance and V outwards. Broad asymmetric crowns avoid cone/sausage profiles.
    float Slab(FVector2D Q, int32 Form)
    {
        const float U=float(Q.X), V=float(Q.Y);
        const float Shear=U+.28f*V;
        const float End=FMath::Abs(Shear)+.12f*V;
        const float Outline=FMath::Max(End,FMath::Abs(V)+.24f*FMath::Max(0.f,U));
        const float Edge=1.f-FMath::SmoothStep(.68f,1.f,Outline);
        if (Edge<=0.f) return 0.f;
        if (Form==0)
            return Edge*FMath::Clamp(.62f-.35f*V+.12f*U,.12f,1.f);
        if (Form==1)
        {
            const float Fold=1.f-FMath::SmoothStep(.12f,.42f,FMath::Abs(V+.23f+.15f*U));
            const float Tear=FMath::SmoothStep(.05f,.22f,FMath::Abs(U-.28f)-.16f*V);
            return Edge*(.35f+.6f*Fold)*FMath::Lerp(.3f,1.f,Tear);
        }
        const float Notch=FMath::SmoothStep(.08f,.32f,FMath::Abs(U+.3f*V+.2f));
        return Edge*FMath::Clamp(.7f-.28f*U-.2f*V,.1f,1.f)*FMath::Lerp(.18f,1.f,Notch);
    }
    float BankHeight(FVector2D P, FVector2D Heading, float Outside, float Width, float Cohesion, float Scale, int32 Row)
    {
        const float S=float(FVector2D::DotProduct(P,Heading));
        const float Spacing=68.f*Scale;
        const int32 Segment=FMath::FloorToInt(S/Spacing);
        // Key opposite banks independently, keeping deposits stable on repeated passes.
        float Height=0.f;
        for (int32 I=-2;I<=2;++I)
        {
            const int32 K=Segment+I;
            if (Hash(K,Row,81)<.18f) continue;
            const float AlongCentre=(K+.15f+.7f*Hash(K,Row,83))*Spacing;
            const float AcrossCentre=Width*FMath::Lerp(.22f,.67f,Hash(K,Row,89));
            const float Length=Spacing*FMath::Lerp(.55f,1.35f,Hash(K,Row,97));
            const float Breadth=Width*FMath::Lerp(.32f,.66f,Hash(K,Row,101));
            const FVector2D Q((S-AlongCentre)/Length,(Outside-AcrossCentre)/Breadth);
            const float H=Slab(Q,int32(Hash(K,Row,103)*2.999f));
            const float Crown=FMath::Lerp(3.f,11.f,Hash(K,Row,107))*FMath::Lerp(.7f,1.f,Cohesion);
            Height=FMath::Max(Height,H*Crown);
        }
        // Thin squeezed material connects some slabs; it cannot build a tall uninterrupted ridge.
        const float Smear=(1.f-FMath::SmoothStep(0.f,Width,Outside))*.65f;
        return FMath::Max(Height,Smear)*FMath::SmoothStep(0.f,FGTLandscapeSurfaceField::CellCm,Outside);
    }
    FIntPoint TileOf(FIntPoint C)
    {
        return FIntPoint(FMath::FloorToInt(double(C.X) / FGTLandscapeSurfaceField::TileCells),
            FMath::FloorToInt(double(C.Y) / FGTLandscapeSurfaceField::TileCells));
    }
    int32 Index(FIntPoint C, FIntPoint T)
    {
        return (C.Y - T.Y * FGTLandscapeSurfaceField::TileCells) * FGTLandscapeSurfaceField::TileCells
            + C.X - T.X * FGTLandscapeSurfaceField::TileCells;
    }
    FGTLandscapeSurfaceCell Blend(const FGTLandscapeSurfaceCell& A, const FGTLandscapeSurfaceCell& B, float T)
    {
        FGTLandscapeSurfaceCell R;
        R.DeltaCm = FMath::Lerp(A.DeltaCm, B.DeltaCm, T);
        R.SlideCm = FMath::Lerp(A.SlideCm, B.SlideCm, T);
        R.Track = FMath::Lerp(A.Track, B.Track, T);
        R.Fresh = FMath::Lerp(A.Fresh, B.Fresh, T);
        R.Turbidity = FMath::Lerp(A.Turbidity, B.Turbidity, T);
        return R;
    }
}

FVector2D FGTLandscapeSurfaceField::Centre(FIntPoint C)
{
    return FVector2D((C.X + .5) * CellCm, (C.Y + .5) * CellCm);
}

float FGTLandscapeSurfaceField::RestHeight(FVector2D World, float Thickness) const
{
    if (Thickness <= .01f) return 0.f;
    if (AuthoredHeightAt) return AuthoredHeightAt(World, Thickness);
    const FLinearColor Style = ShapeAt ? ShapeAt(World) : FLinearColor(.35f,.5f,1.f,1.f);
    const float Cohesion = Style.G;
    World /= Style.A;
    // Clustered fragments: independently varied outline, crown, aspect and height.
    // World-stable warping breaks the cellular placement without moving wheel paths.
    const FVector2D Warped = World + FVector2D(
        GTLandscapeField::Noise(World/93.f)-.5f,
        GTLandscapeField::Noise(World/87.f+FVector2D(37,19))-.5f)*35.f;
    float Clod = 0.f;
    for (int32 Layer=0; Layer<2; ++Layer)
    {
        // Tyre-scale fragments inside larger disturbed sheets, not metre-wide shallow domes.
        const float Spacing = Layer ? 32.f : 75.f;
        const FVector2D P = Warped/Spacing;
        const int32 X=FMath::FloorToInt(P.X), Y=FMath::FloorToInt(P.Y);
        for (int32 J=-1; J<=1; ++J)
            for (int32 I=-1; I<=1; ++I)
            {
                const int32 A=X+I, B=Y+J;
                const uint32 Seed = Layer*17;
                const FVector2D Centre(A+.1+.8*GTLandscapeField::Hash(A,B,Seed+2), B+.1+.8*GTLandscapeField::Hash(A,B,Seed+3));
                const float Cluster = FMath::SmoothStep(.28f,.72f,GTLandscapeField::Noise(Centre*Spacing/260.f));
                const float Density = FMath::Lerp(.18f,.98f,Cluster)*FMath::Lerp(.8f,1.25f,Cohesion);
                if (GTLandscapeField::Hash(A,B,Seed+1) > Density) continue;
                const FVector2D D = (P-Centre)*Spacing;
                const float Angle = GTLandscapeField::Hash(A,B,Seed+4)*2.f*PI;
                const float U = float(D.X)*FMath::Cos(Angle)+float(D.Y)*FMath::Sin(Angle);
                const float V = -float(D.X)*FMath::Sin(Angle)+float(D.Y)*FMath::Cos(Angle);
                const float Size = GTLandscapeField::Hash(A,B,Seed+5);
                const float Radius = (Layer ? FMath::Lerp(8.f,19.f,Size)
                                           : FMath::Lerp(18.f,38.f,Size))*FMath::Lerp(.8f,1.2f,Cohesion);
                const float Qx = U/Radius, Qy = V/(Radius*FMath::Lerp(.45f,1.f,GTLandscapeField::Hash(A,B,Seed+6)));
                const float Shape = GTLandscapeField::Hash(A,B,Seed+8);
                const float Box = FMath::Max(FMath::Abs(Qx),FMath::Abs(Qy));
                const float Diamond = (FMath::Abs(Qx)+FMath::Abs(Qy))*.8f;
                const float Edge = FMath::Lerp(Box,Diamond,Shape)
                    + .16f*(GTLandscapeField::Noise(Warped/14.f)-.5f);
                const float Bevel = 1.f-FMath::SmoothStep(FMath::Lerp(.72f,.88f,Shape)-Cohesion*.2f,1.f,Edge);
                const float TiltX = FMath::Lerp(-.55f,.55f,GTLandscapeField::Hash(A,B,Seed+9));
                const float TiltY = FMath::Lerp(-.4f,.4f,GTLandscapeField::Hash(A,B,Seed+10));
                const float Crown = FMath::Clamp(1.f+TiltX*Qx+TiltY*Qy,.25f,1.4f);
                // Some fragments split across a fracture; others remain a single torn slab.
                const float Split = Radius*Style.A>30.f && GTLandscapeField::Hash(A,B,Seed+11) > .3f+Cohesion*.45f
                    ? FMath::Lerp(.12f+Cohesion*.3f,1.f,FMath::SmoothStep(.04f,.27f,FMath::Abs(Qx+.4f*Qy-.15f))) : 1.f;
                // Sub-grid fragments are low embedded crumbs, not one-vertex spikes. Keep tall crowns
                // only where the field can represent several samples across their width.
                const float Resolved=FMath::SmoothStep(8.f,24.f,Radius*Style.A);
                const float Height = (Layer ? FMath::Lerp(3.f,11.f,GTLandscapeField::Hash(A,B,Seed+7))
                                           : FMath::Lerp(8.f,24.f,GTLandscapeField::Hash(A,B,Seed+7)))*Resolved;
                const float Fragment=Bevel*Crown*Height*Split;
                const float Slumped=GTLandscapeField::Slab(FVector2D(Qx,Qy),int32(Shape*2.999f))*Height;
                Clod = FMath::Max(Clod,FMath::Lerp(Fragment,Slumped,FMath::SmoothStep(.3f,.8f,Cohesion)));
            }
    }
    const float Hollow = FMath::SmoothStep(.61f,.85f,GTLandscapeField::Noise(World/145.f))*7.f;
    float Height = -3.f-Hollow+Clod + .65f*(GTLandscapeField::Noise(World/19.f)-.5f);
    const float Crust = FMath::SmoothStep(.55f,.6f,Cohesion)*(1.f-Style.R);
    if (Crust > .5f)
    {
        // Dried cohesive soil forms connected plates separated by narrow fissures.
        // Difference of nearest feature distances makes polygon boundaries, not isolated mounds.
        const FVector2D P = World/55.f;
        const int32 X=FMath::FloorToInt(P.X), Y=FMath::FloorToInt(P.Y);
        float Nearest=MAX_flt, Second=MAX_flt;
        for (int32 J=-1; J<=1; ++J)
            for (int32 I=-1; I<=1; ++I)
            {
                const FVector2D Seed(X+I+.2+.6*GTLandscapeField::Hash(X+I,Y+J,43),Y+J+.2+.6*GTLandscapeField::Hash(X+I,Y+J,51));
                const float D=float((P-Seed).Size());
                if (D<Nearest) { Second=Nearest; Nearest=D; }
                else Second=FMath::Min(Second,D);
            }
        const float Fissure=1.f-FMath::SmoothStep(.025f,.16f,Second-Nearest);
        const float Plate=1.8f*(GTLandscapeField::Noise(World/120.f)-.5f)+Clod*.2f-Fissure*3.f;
        Height=FMath::Lerp(Height,Plate,Crust);
    }
    // Compress tall crowns smoothly rather than clipping them all into identical flat caps.
    const float Bounded = Height > 0.f ? 12.f*(1.f-FMath::Exp(-Height/12.f)) : FMath::Max(Height,-FMath::Min(Thickness,12.f));
    return FMath::Clamp(Bounded*Style.B,-Thickness,12.f)*FMath::SmoothStep(0.f,8.f,Thickness);
}

void FGTLandscapeSurfaceField::Focus(FVector2D World, TFunctionRef<FLinearColor(FVector2D)> Paint)
{
    WindowTile = FIntPoint(FMath::FloorToInt(World.X / TileCm) - 1, FMath::FloorToInt(World.Y / TileCm) - 1);
    for (int32 Y = 0; Y < 3; ++Y)
        for (int32 X = 0; X < 3; ++X)
        {
            FTile& Tile = Tiles.FindOrAdd(WindowTile + FIntPoint(X, Y));
            if (Tile.Cells.IsEmpty())
            {
                const FIntPoint Key = WindowTile + FIntPoint(X,Y);
                if (PrefetchRow >= 0 && PrefetchKey == Key)
                {
                    // The tile is half-built by the prefetch: finish its remaining rows and take it.
                    InitTileRows(Key, PrefetchCells, PrefetchRow, TileCells, Paint);
                    Tile.Cells = MoveTemp(PrefetchCells);PrefetchRow = -1;
                }
                else
                {
                    Tile.Cells.SetNum(TileCells * TileCells);
                    InitTileRows(Key, Tile.Cells, 0, TileCells, Paint);
                }
            }
            Tile.LastUse = ++Clock;
        }
    // Includes conservative map/allocation overhead, not only cell payloads. Active nine tiles never evict.
    constexpr int64 TileBytes = (sizeof(FGTLandscapeSurfaceCell) + 32) * TileCells * TileCells + 1024;
    while (int64(Tiles.Num()) * TileBytes > CacheBudgetBytes)
    {
        FIntPoint Oldest = FIntPoint::ZeroValue; uint64 OldestUse = MAX_uint64; bool bFound = false;
        for (const auto& Pair : Tiles)
        {
            const FIntPoint D = Pair.Key - WindowTile;
            if (D.X >= 0 && D.X < 3 && D.Y >= 0 && D.Y < 3) continue;
            if (Pair.Value.LastUse < OldestUse) { Oldest = Pair.Key; OldestUse = Pair.Value.LastUse; bFound = true; }
        }
        if (!bFound) break;
        Tiles.Remove(Oldest); ++Evictions;
    }
}

void FGTLandscapeSurfaceField::InitTileRows(FIntPoint Key, TArray<FGTLandscapeSurfaceCell>& Cells, int32 From, int32 To, TFunctionRef<FLinearColor(FVector2D)> Paint) const
{
    const FIntPoint First = Key*TileCells;
    for (int32 J=From; J<To; ++J)
        for (int32 I=0; I<TileCells; ++I)
        {
            const FVector2D P = Centre(First+FIntPoint(I,J));
            Cells[J*TileCells+I].DeltaCm = RestHeight(P,Paint(P).R);
        }
}

void FGTLandscapeSurfaceField::Prefetch(FVector2D World, TFunctionRef<FLinearColor(FVector2D)> Paint, double Deadline)
{
    if (PrefetchRow < 0)
    {
        const FIntPoint Here(FMath::FloorToInt(World.X / TileCm), FMath::FloorToInt(World.Y / TileCm));
        double BestD = DBL_MAX;bool bFound = false;FIntPoint Best = FIntPoint::ZeroValue;
        for (int32 Y = -2; Y <= 2; ++Y)
            for (int32 X = -2; X <= 2; ++X)
            {
                const FIntPoint K = Here + FIntPoint(X, Y);
                const FTile* T = Tiles.Find(K);
                if (T && !T->Cells.IsEmpty()) continue;
                const double D = FVector2D::DistSquared((FVector2D(K.X, K.Y) + FVector2D(.5, .5)) * TileCm, World);
                if (D < BestD) { BestD = D;Best = K;bFound = true; }
            }
        if (!bFound) return;
        PrefetchKey = Best;PrefetchCells.SetNum(TileCells * TileCells);PrefetchRow = 0;
    }
    while (PrefetchRow < TileCells)
    {
        InitTileRows(PrefetchKey, PrefetchCells, PrefetchRow, PrefetchRow + 1, Paint);++PrefetchRow;
        if (FPlatformTime::Seconds() >= Deadline) break;
    }
    if (PrefetchRow >= TileCells)
    {
        FTile& T = Tiles.FindOrAdd(PrefetchKey);
        if (T.Cells.IsEmpty()) T.Cells = MoveTemp(PrefetchCells);
        T.LastUse = ++Clock;PrefetchRow = -1;
    }
}

bool FGTLandscapeSurfaceField::IsActive(FIntPoint Cell) const
{
    const FIntPoint D = GTLandscapeField::TileOf(Cell) - WindowTile;
    return D.X >= 0 && D.X < 3 && D.Y >= 0 && D.Y < 3;
}

FGTLandscapeSurfaceCell* FGTLandscapeSurfaceField::Edit(FIntPoint Cell)
{
    if (!IsActive(Cell)) return nullptr;
    const FIntPoint Key = GTLandscapeField::TileOf(Cell);
    FTile* T = Tiles.Find(Key);
    return T ? &T->Cells[GTLandscapeField::Index(Cell, Key)] : nullptr;
}

FGTLandscapeSurfaceCell FGTLandscapeSurfaceField::Read(FIntPoint Cell) const
{
    const FIntPoint Key = GTLandscapeField::TileOf(Cell);
    const FTile* T = Tiles.Find(Key);
    return T ? T->Cells[GTLandscapeField::Index(Cell, Key)] : FGTLandscapeSurfaceCell();
}

FGTLandscapeSurfaceCell FGTLandscapeSurfaceField::Sample(FVector2D World) const
{
    const FVector2D P = World / CellCm - FVector2D(.5, .5);
    const FIntPoint C(FMath::FloorToInt(P.X), FMath::FloorToInt(P.Y));
    return GTLandscapeField::Blend(
        GTLandscapeField::Blend(Read(C), Read(C + FIntPoint(1, 0)), float(P.X - C.X)),
        GTLandscapeField::Blend(Read(C + FIntPoint(0, 1)), Read(C + FIntPoint(1, 1)), float(P.X - C.X)), float(P.Y - C.Y));
}

float FGTLandscapeSurfaceField::WaterDepth(float Delta, const FLinearColor& P)
{
    return P.R > 0.f ? FMath::Min(WaterFillLimitCm, FMath::Max(0.f, FMath::Min(0.f, P.G) - Delta)) : 0.f;
}

void FGTLandscapeSurfaceField::MarkChanged(FIntPoint Cell, bool bDecay)
{
    const FIntPoint Key=GTLandscapeField::TileOf(Cell);
    if (auto* T=Tiles.Find(Key))
    {
        const int32 Index=GTLandscapeField::Index(Cell,Key);
        const int32 Block=(Index/TileCells/UploadBlockCells)*BlocksPerSide+(Index%TileCells/UploadBlockCells);
        T->DirtyBlocks |= uint64(1)<<Block;
        T->ContactDirtyBlocks |= uint64(1)<<Block;
        T->BedBlockRevision[Block]=GeometryRevision+1;
        if (bDecay) T->DecayingCells.Add(Index);
    }
}

void FGTLandscapeSurfaceField::BedChangesSince(uint64 Revision,TArray<FBox2D>& Regions) const
{
    Regions.Reset();
    for(const auto& Tile:Tiles)
        for(int32 B=0;B<BlocksPerSide*BlocksPerSide;++B)
            if(Tile.Value.BedBlockRevision[B]>Revision)
            {
                const FIntPoint Min=Tile.Key*TileCells+FIntPoint(B%BlocksPerSide,B/BlocksPerSide)*UploadBlockCells;
                // One fine-cell halo covers bilinear sampling at the block boundary.
                Regions.Add(FBox2D(FVector2D(Min-FIntPoint(1,1))*CellCm,
                    FVector2D(Min+FIntPoint(UploadBlockCells+1,UploadBlockCells+1))*CellCm));
            }
}

void FGTLandscapeSurfaceField::Step(float Dt)
{
    GT_PERF_SCOPE(PerfFieldStep,"SurfaceField.Step");
    if(bNativeShaderUpdates){GT_PERF_SCOPE(PerfFieldNative,"SurfaceField.StepNative");PerfFieldNative.Work=NativeAux.Num();StepNative();}
    LastDecayCells=0;++DecayFrame;
    // CL2: clay ruts hold their state. Each decaying cell's step (1 - decay) is scaled by (1 - clay at its centre), so clay 1 never
    // recovers and clay .5 recovers at half rate; a cell this clayey is dropped from the set where it stands rather than revisited
    // every frame for ever. Without a ClayAt function the loop below is the original one.
    const bool bClay=static_cast<bool>(ClayAt);
    constexpr float FrozenClay=.98f;
    for (int32 Y = 0; Y < 3; ++Y)
        for (int32 X = 0; X < 3; ++X)
            if (FTile* T = Tiles.Find(WindowTile + FIntPoint(X, Y)))
            {
                // PF1: with bSliceDecay a tile is decayed every ninth frame, once, over the whole time since its last decay (the exponential decay composes, so the sum of the frames is the same decay).
                T->DecayAccum += FMath::Max(0.f, Dt);
                if (bSliceDecay && ((DecayFrame + uint32(Y * 3 + X)) % 9) != 0) continue;
                const float TileDt = T->DecayAccum;T->DecayAccum = 0.f;
                const float FreshDecay = FMath::Exp(-TileDt / 6.f);
                const float MudDecay = FMath::Exp(-TileDt / 45.f);
                for (auto It=T->DecayingCells.CreateIterator();It;++It)
                {
                    const int32 Index=*It;
                    auto& C=T->Cells[Index];
                    float Fresh=FreshDecay,Turbid=MudDecay;
                    if (bClay)
                    {
                        const FIntPoint Key=WindowTile+FIntPoint(X,Y);
                        const float Clay=FMath::Clamp(ClayAt(Centre(FIntPoint(Key.X*TileCells+Index%TileCells,Key.Y*TileCells+Index/TileCells))),0.f,1.f);
                        if (Clay>=FrozenClay) { It.RemoveCurrent();continue; }
                        Fresh=1.f-(1.f-FreshDecay)*(1.f-Clay);Turbid=1.f-(1.f-MudDecay)*(1.f-Clay);
                    }
                    C.Fresh*=Fresh;C.Turbidity*=Turbid;++LastDecayCells;
                    // Below half-float cosmetic significance, stop revisiting a settled cell.
                    if (C.Fresh<.001f && C.Turbidity<.001f) { C.Fresh=C.Turbidity=0;It.RemoveCurrent(); }
                    const int32 Block=(Index/TileCells/UploadBlockCells)*BlocksPerSide+(Index%TileCells/UploadBlockCells);
                    T->DirtyBlocks |= uint64(1)<<Block;
                }
            }
    PerfFieldStep.Work=LastDecayCells;
    // No diffusion: settling must not enlarge a tyre-width rut into a moat.
}

void FGTLandscapeSurfaceField::Pack(FIntRect Cells, TFunctionRef<FLinearColor(FVector2D)> Paint,
    TFunctionRef<FVector2f(FVector2D)> Appearance, TArray<FFloat16Color>& Ground, TArray<FFloat16Color>& Water) const
{
    Ground.SetNumUninitialized(Cells.Area());Water.SetNumUninitialized(Cells.Area());
    int32 I=0;
    for (int32 Y=Cells.Min.Y;Y<Cells.Max.Y;++Y)
        for (int32 X=Cells.Min.X;X<Cells.Max.X;++X,++I)
        {
            const FIntPoint Key(X,Y);const auto C=Read(Key);const auto P=Paint(Centre(Key));
            const float Delta=P.R>.01f ? FMath::Clamp(C.DeltaCm,-P.R,LipCapCm) : 0.f;
            const FVector2f Style=Appearance(Centre(Key));
            Ground[I]=FFloat16Color(FLinearColor(Delta,C.SlideCm.X,C.SlideCm.Y,C.Track));
            Water[I]=FFloat16Color(FLinearColor(WaterDepth(Delta,P),P.R>.01f ? Style.X : 0.f,C.Fresh,Style.Y>0.f ? -Style.Y : C.Turbidity));
        }
}

void FGTLandscapeSurfaceField::Stamp(FVector2D Start, FVector2D End, FVector2D Heading,
    float Width, float Depth, TFunctionRef<FLinearColor(FVector2D)> Paint, float ContactPlaneCm, float MaxCutCm)
{
    StampWorked(Start,End,Heading,Width,Depth,Paint,ContactPlaneCm,MaxCutCm,{});
}

void FGTLandscapeSurfaceField::StampWorked(FVector2D Start, FVector2D End, FVector2D Heading,
    float Width, float Depth, TFunctionRef<FLinearColor(FVector2D)> Paint, float ContactPlaneCm, float MaxCutCm, FWheelWork Work)
{
    if(bNativeShaderUpdates && (!NativeUpdateAt || NativeUpdateAt((Start+End)*.5))) { StampNative(Start,End,Heading,Width,Depth,Paint,ContactPlaneCm,MaxCutCm,Work); return; }
    if (!FMath::IsFinite(Depth) || Depth <= 0.f || !FMath::IsFinite(Width) || Width <= 0.f) return;
    if (FVector2D::Distance(Start, End) > 200.f) Start = End; // teleports / lost wheel contact
    Heading = Heading.GetSafeNormal();
    if (Heading.IsNearlyZero()) Heading = FVector2D(1, 0);
    const FVector2D Side(-Heading.Y, Heading.X);
    const float HalfWidth = FMath::Clamp(Width * .5f, 5.f, 50.f);
    // Deposits spread outwards in low sheets; pressure feathers into the yielding shoulders.
    constexpr float MaxLipWidth = 90.f;
    const FVector2D Move = End - Start;
    const double MoveSq = Move.SizeSquared();
    const float Reach = HalfWidth + MaxLipWidth + 25.f;
    const FIntPoint Lo(FMath::FloorToInt((FMath::Min(Start.X, End.X) - Reach) / CellCm),
        FMath::FloorToInt((FMath::Min(Start.Y, End.Y) - Reach) / CellCm));
    const FIntPoint Hi(FMath::FloorToInt((FMath::Max(Start.X, End.X) + Reach) / CellCm),
        FMath::FloorToInt((FMath::Max(Start.Y, End.Y) + Reach) / CellCm));
    struct FCandidate { FIntPoint Cell; float Amount; float Lateral; };
    const bool bPressure=ContactPlaneCm!=MAX_flt && FMath::IsFinite(ContactPlaneCm);
    TArray<FCandidate> Cuts, Lips;
    double CutSum = 0., Capacity = 0.;
    for (int32 Y = Lo.Y; Y <= Hi.Y; ++Y)
        for (int32 X = Lo.X; X <= Hi.X; ++X)
        {
            const FIntPoint Key(X, Y);
            auto* C = Edit(Key);
            if (!C) continue;
            const FVector2D P = Centre(Key);
            const FLinearColor Mask = Paint(P);
            const float Thickness = FMath::Clamp(Mask.R, 0.f, 124.f);
            if (Thickness <= .01f) continue;
            const FLinearColor Style = ShapeAt ? ShapeAt(P) : FLinearColor(.35f,.5f,1.f,1.f);
            const float Cohesion = Style.G;
            const float LipWidth = (Work.Granular ? 68.f : FMath::Lerp(24.f,MaxLipWidth,Cohesion))*FMath::Lerp(.4f,1.f,FMath::SmoothStep(2.f,25.f,Thickness));
            const double T = MoveSq > .01 ? FMath::Clamp(FVector2D::DotProduct(P - Start, Move) / MoveSq, 0., 1.) : 0.;
            const FVector2D D = P - (Start + Move * T);
            const float Across = float(FVector2D::DotProduct(D, Side));
            const float Along = float(FVector2D::DotProduct(D, Heading));
            if (Along < -45.f || Along > 95.f) continue;
            // Cell coverage feather stays INSIDE the tyre. Repeated stamps cannot grow a shoulder.
            const float EdgeInset = FMath::Lerp(.5f,6.f,GTLandscapeField::Noise(P/23.f+FVector2D(11,47)))*FMath::Lerp(1.f,.25f,Cohesion);
            float Coverage = FMath::Abs(Along)<=20.f
                ? FMath::SmoothStep(0.f,FMath::Max(CellCm,HalfWidth*.35f),HalfWidth - EdgeInset - FMath::Abs(Across)) : 0.f;
            if(bPressure)
            {
                // Rounded swept footprint, not a rectangular cutter. Feather the toe and
                // heel as well as the sides; the deformation follows actual travel.
                const float Ellipse=FMath::Square(Across/(HalfWidth+18.f))+FMath::Square(Along/24.f);
                Coverage=1.f-FMath::SmoothStep(.35f,1.f,Ellipse);
            }
            if (Coverage > 0.f)
            {
                // A bounded, world-stable compressed floor: repeats do not accumulate noise or widen cuts.
                const float Yield = FMath::SmoothStep(.23f,.76f,GTLandscapeField::Noise(P/83.f));
                const float BrokenFloor = FMath::Lerp(FMath::Lerp(.6f,.82f,Cohesion),1.f,Yield)
                    * FMath::Lerp(.88f,1.f,GTLandscapeField::Noise(P/17.f));
                const float Rest = RestHeight(P,Thickness);
                // Compress relative to this piece of bog, never plane all crowns and hollows
                // to a common negative world height. The finite mineral base still stops cuts.
                // The pressure plane already contains the load equilibrium. Applying the
                // authored rest-shape depth limit as well leaves high clumps propping up
                // a loaded tyre before the soil reaches that equilibrium.
                const float Floor=bPressure ? -Thickness : FMath::Max(-Thickness,Rest-Depth*BrokenFloor);
                // Loaded tyres crush the high points they actually press against. Hollows
                // below the contact plane are not excavated merely to copy the rest shape.
                // The authored stamping path (no contact plane) remains deterministic.
                const float CurvedPlane=ContactPlaneCm+14.f*FMath::Square(Across/(HalfWidth+18.f))+6.f*FMath::Square(Along/24.f);
                const float Target=bPressure
                    ? FMath::Lerp(C->DeltaCm,FMath::Max(Floor,CurvedPlane),Coverage)
                    : FMath::Lerp(Rest,Floor,Coverage);
                const float Cut = FMath::Min(FMath::Max(0.f,C->DeltaCm-Target),FMath::Max(0.f,MaxCutCm)*Coverage);
                if (Cut > 0.f) { Cuts.Add({Key, Cut, Across}); CutSum += Cut; }
                if(bPressure)
                {
                    // A rolling tyre smears crushed crowns into the low pockets of
                    // its bed. Transport is paid for by the same excavated volume;
                    // this cannot fill a hollow without adjacent soil being displaced.
                    const float BedRoom=FMath::Max(0.f,ContactPlaneCm-1.5f-C->DeltaCm)*Coverage*.65f;
                    if(BedRoom>0.f) { Lips.Add({Key,BedRoom,Across});Capacity+=BedRoom; }
                }
                if (Coverage>C->Track) { C->Track=Coverage;MarkChanged(Key); }
            }
            else if ((FMath::Abs(Across) >= HalfWidth && FMath::Abs(Across) < HalfWidth + LipWidth)
                || (Along>20.f && Along<80.f && FMath::Abs(Across)<HalfWidth)
                || (Work.Enabled && Along< -20.f && Along> -40.f && FMath::Abs(Across)<HalfWidth))
            {
                // Existing ruts do not receive lips: crossing/repeat passes retain their narrow shape.
                if (!bPressure && C->Track > .01f) continue;
                const int32 BankKey=FMath::FloorToInt(float(FVector2D::DotProduct(Start,Side))/180.f)+(Across<0.f?-7919:7919);
                const float SlabHeight=FMath::Abs(Across)>=HalfWidth
                    ? GTLandscapeField::BankHeight(P,Heading,FMath::Abs(Across)-HalfWidth,LipWidth,Cohesion,Style.A,BankKey)
                    : GTLandscapeField::Slab(FVector2D((Along-48.f)/32.f,Across/HalfWidth),0)*7.f;
                // Independent authored slabs on each side replace the continuous extruded bank.
                const float Rest = RestHeight(P,Thickness);
                float Ceiling = FMath::Min(LipCapCm, Rest + SlabHeight*FMath::SmoothStep(0.f,10.f,Thickness));
                if(bPressure)
                {
                    // Soil flows into nearby low space, including old tracks. Trampled
                    // shoulders can be refilled, but never rebuild a tall procedural wall.
                    const float Crown=Work.Granular ? 5.f*FMath::Lerp(.65f,1.f,GTLandscapeField::Noise(P/85.f)) : Work.Enabled
                        ? FMath::Lerp(1.5f,7.f,Cohesion)*FMath::Lerp(.35f,1.f,GTLandscapeField::Noise(P/29.f+FVector2D(19,73)))
                        : FMath::Lerp(1.5f,4.f,Cohesion);
                    Ceiling=FMath::Min(LipCapCm,Rest+Crown);
                    // Deposited shoulders carry a light worked-soil mark (.15), not
                    // a compressed tyre bed. Treating that mark as a rut removes
                    // transport capacity after the first stamp and hardens the bog.
                    if(C->Track>.78f) Ceiling=FMath::Min(Ceiling,Rest);
                }
                // Share volume with adjacent slabs ahead/behind the contact. Restricting deposits to
                // the cut's short slice normalizes every slice into the same continuous ribbon.
                const float Transport=(1.f-FMath::SmoothStep(25.f,95.f,FMath::Max(Along,0.f)))
                    *(1.f-FMath::SmoothStep(10.f,45.f,FMath::Max(-Along,0.f)));
                const float NearEdge=bPressure ? FMath::Exp(-FMath::Max(0.f,FMath::Abs(Across)-HalfWidth)/30.f) : 1.f;
                // Rolling pushes a low bow in front of the contact. Positive drive slip
                // shears material backwards as the tread pushes against the ground.
                // World-space clod breakup varies each bank without accumulating random cuts.
                float WorkWeight=1.f;
                if(bPressure && Work.Enabled)
                {
                    const float Toe=FMath::SmoothStep(10.f,32.f,Along)*(1.f-FMath::SmoothStep(48.f,80.f,Along));
                    const float Heel=FMath::SmoothStep(2.f,28.f,-Along);
                    const float CentreWeight=1.f-FMath::SmoothStep(HalfWidth,HalfWidth+25.f,FMath::Abs(Across));
                    const float Broken=FMath::Lerp(.25f,1.f,GTLandscapeField::Noise(P/31.f+FVector2D(61,13)));
                    WorkWeight=FMath::Clamp((.35f+Toe*CentreWeight*Work.Motion*2.5f*(1.f-Work.Slip)
                        +Heel*Work.Slip*2.f)*Broken,0.f,1.f);
                    WorkWeight*=1.f-.95f*Work.Slip*FMath::SmoothStep(0.f,20.f,Along);
                }
                const float Room = FMath::Max(0.f, Ceiling - C->DeltaCm)*Transport*NearEdge*WorkWeight;
                if (Room > 0.f) { Lips.Add({Key, Room, Across}); Capacity += Room; }
            }
        }
    if (CutSum <= 0. || Capacity <= 0.) return;
    const double Moved = FMath::Min(CutSum, Capacity);
    for (const auto& Cut : Cuts)
    {
        auto* C = Edit(Cut.Cell);
        C->DeltaCm -= float(Cut.Amount * Moved / CutSum);
        C->Fresh = C->Turbidity = 1.f;
        MarkChanged(Cut.Cell,true);
        const float Slide=bPressure ? FMath::Clamp(C->SlideCm.Size()+float(Cut.Amount*Moved/CutSum)*.25f,.5f,8.f)
            : FMath::Min(8.f,-C->DeltaCm*.3f);
        C->SlideCm = FVector2f(Side * (Cut.Lateral < 0.f ? -1.f : 1.f) * Slide);
    }
    for (const auto& Lip : Lips)
    {
        auto* C = Edit(Lip.Cell);
        C->DeltaCm += float(Lip.Amount * Moved / Capacity);
        if(bPressure)
        {
            const float Slide=FMath::Min(8.f,C->SlideCm.Size()+float(Lip.Amount*Moved/Capacity)*.25f);
            const FVector2D Flow=Work.Enabled
                ? (Side*(Lip.Lateral<0.f?-1.f:1.f)*.65f+Heading*(Work.Motion*(1.f-Work.Slip)-Work.Slip)).GetSafeNormal()
                : Side*(Lip.Lateral<0.f?-1.f:1.f);
            C->SlideCm=FVector2f(Flow*Slide);
            C->Track=FMath::Max(C->Track,.15f);
        }
        C->Fresh = 1.f;
        MarkChanged(Lip.Cell,true);
    }
    if(bPressure && Work.Enabled)
    {
        // Local yielding of freshly deposited wet banks, never a full terrain sweep.
        // Only transfer into a lower neighbour outside the loaded footprint. Transfers
        // are bounded by this stamp's time-scaled cut allowance and conserve soil.
        for(const auto& Lip : Lips)
        {
            auto* From=Edit(Lip.Cell);const FVector2D P=Centre(Lip.Cell);
            const float Wet=ShapeAt ? FMath::Clamp(ShapeAt(P).R,0.f,1.f) : .5f;
            const float Cohesion=ShapeAt ? FMath::Clamp(ShapeAt(P).G,0.f,1.f) : .5f;
            FIntPoint Lowest=Lip.Cell;float Low=From->DeltaCm;
            for(const FIntPoint Offset : {FIntPoint(1,0),FIntPoint(-1,0),FIntPoint(0,1),FIntPoint(0,-1)})
            {
                const FIntPoint Key=Lip.Cell+Offset;const FVector2D Q=Centre(Key);
                const auto* To=IsActive(Key) ? Edit(Key) : nullptr;
                if(!To || Paint(Q).R<=.01f) continue;
                const double T=MoveSq>.01 ? FMath::Clamp(FVector2D::DotProduct(Q-Start,Move)/MoveSq,0.,1.) : 0.;
                const FVector2D D=Q-(Start+Move*T);
                const float Ellipse=FMath::Square(FVector2D::DotProduct(D,Side)/(HalfWidth+18.f))+FMath::Square(FVector2D::DotProduct(D,Heading)/24.f);
                if(Ellipse<1.05f) continue;
                if(To->DeltaCm<Low) { Low=To->DeltaCm;Lowest=Key; }
            }
            const float Repose=CellCm*(Work.Granular ? .62f : FMath::Lerp(.85f,.28f,Wet)*(1.f+.35f*Cohesion));
            const float Mobility=Work.Granular ? 1.f : Wet;
            const float Transfer=FMath::Min(FMath::Max(0.f,(From->DeltaCm-Low-Repose)*.25f),FMath::Min(MaxCutCm,.8f)*(Work.Granular ? .65f : .2f)*Mobility);
            if(Transfer<=0.f || Lowest==Lip.Cell) continue;
            auto* To=Edit(Lowest);From->DeltaCm-=Transfer;To->DeltaCm+=Transfer;
            To->Fresh=1.f;MarkChanged(Lip.Cell,true);MarkChanged(Lowest,true);
            ExcavatedCm3+=Transfer*CellCm*CellCm;DepositedCm3+=Transfer*CellCm*CellCm;
        }
    }
    ++GeometryRevision;
    ExcavatedCm3 += Moved * CellCm * CellCm;
    DepositedCm3 += Moved * CellCm * CellCm;
}
