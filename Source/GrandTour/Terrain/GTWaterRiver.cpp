#include "Terrain/GTWaterField.h"

bool FGTWaterField::SetRiverReference(const TArray<float>& H, const TArray<float>& X, const TArray<float>& Y, bool bPrescribedMean)
{
	const int32 N = NumCells();
	if (!IsValid() || N > 16384 || H.Num() != N || X.Num() != N || Y.Num() != N) return false;
	for (int32 I = 0; I < N; ++I)
	{
		if (!FMath::IsFinite(H[I]) || H[I] < 0 || !FMath::IsFinite(X[I]) || !FMath::IsFinite(Y[I])) return false;
		const int32 Col = I % SizeX, Row = I / SizeX;
		if (!bPrescribedMean && Col > 0 && Row > 0 && Col < SizeX-1 && Row < SizeY-1 &&
			FMath::Abs(X[I] + Y[I] - X[I-1] - Y[I-SizeX]) > 1.e-6f) return false;
		if (Col == SizeX-1 && X[I] != 0) return false;
		if (Row == SizeY-1 && Y[I] != 0) return false;
		if (Col < SizeX-1 && (H[I] == 0 || H[I+1] == 0) && X[I] != 0) return false;
		if (Row < SizeY-1 && (H[I] == 0 || H[I+SizeX] == 0) && Y[I] != 0) return false;
	}
	bRiverPrescribedMean=bPrescribedMean;
	RiverDepthM = H; RiverFluxX = X; RiverFluxY = Y;
	RiverWaveX.Init(0, N); RiverWaveY.Init(0, N);
	RiverNextX.Init(0, N); RiverNextY.Init(0, N); RiverOutScale.Init(1, N);
	RiverWetCells.Reset();RiverEdgeCells.SetNum(N);RiverMeanU.Init(0,N);RiverMeanV.Init(0,N);
	const float CellM=CellCm*.01f;
	for(int32 I=0;I<N;++I)
	{
		const int32 Col=I%SizeX,Row=I/SizeX;
		if(H[I]>0) RiverWetCells.Add(I);
		RiverEdgeCells[I]=FMath::Min(FMath::Min(Col,SizeX-1-Col),FMath::Min(Row,SizeY-1-Row));
		if(Col+1<SizeX) RiverMeanU[I]=X[I]/FMath::Max(CellM*FMath::Min(H[I],H[I+1]),1.e-6f);
		if(Row+1<SizeY) RiverMeanV[I]=Y[I]/FMath::Max(CellM*FMath::Min(H[I],H[I+SizeX]),1.e-6f);
	}
	RiverBlendDt=-1;RiverBlendWidth=-1;
	bOpenEnds = false;
	ResetRiverReference();
	return true;
}

int32 FGTWaterField::CopyRiverOverlap(const FGTWaterField& Old)
{
	if(!HasRiverReference() || !Old.HasRiverReference() || CellCm!=Old.CellCm || AxisX!=Old.AxisX) return 0;
	const FVector2D Offset=Old.ToFieldCm(OriginCm)/CellCm;
	const int32 OX=FMath::RoundToInt(Offset.X),OY=FMath::RoundToInt(Offset.Y);
	if(FMath::Abs(Offset.X-OX)>.001 || FMath::Abs(Offset.Y-OY)>.001) return 0;
	int32 Copied=0;double Before=0,After=0;
	for(int32 I=0;I<Old.NumCells();++I) Before+=Old.DepthM[I]-Old.RiverDepthM[I];
	for(int32 I=0;I<NumCells();++I)
	{
		const int32 X=I%SizeX,Y=I/SizeX,OXI=X+OX,OYI=Y+OY;
		if(OXI<0 || OYI<0 || OXI>=Old.SizeX || OYI>=Old.SizeY) continue;
		const int32 J=OYI*Old.SizeX+OXI;
		if(RiverDepthM[I]<=0 || Old.RiverDepthM[J]<=0) continue;
		DepthM[I]=FMath::Max(0.f,RiverDepthM[I]+Old.DepthM[J]-Old.RiverDepthM[J]);
		After+=DepthM[I]-RiverDepthM[I];
		LidM[I]=Old.LidM[J];LidNextM[I]=Old.LidNextM[J];
		if(bRiverVisuals && Old.RiverDetail.IsValidIndex(J))
		{RiverDetail[I]=Old.RiverDetail[J];RiverDetailLid[I]=Old.RiverDetailLid[J];}
		if(LidM[I]>0) LidCells.Add(I);
		if(Old.LidDirty[J]) { LidDirty[I]=1;LidDirtyCells.Add(I); }
		if(X+1<SizeX && OXI+1<Old.SizeX && RiverDepthM[I+1]>0)
		{ RiverWaveX[I]=Old.RiverWaveX[J];FluxX[I]=RiverFluxX[I]+Old.FluxX[J]-Old.RiverFluxX[J]; }
		if(Y+1<SizeY && OYI+1<Old.SizeY && RiverDepthM[I+SizeX]>0)
		{ RiverWaveY[I]=Old.RiverWaveY[J];FluxY[I]=RiverFluxY[I]+Old.FluxY[J]-Old.RiverFluxY[J]; }
		++Copied;
	}
	Accumulator=Old.Accumulator;WindPhase=Old.WindPhase;WindCarry=Old.WindCarry;RainCarry=Old.RainCarry;Rng=Old.Rng;
	RiverBoundaryM3=Old.RiverBoundaryM3;
	RiverDetailCarry=Old.RiverDetailCarry;
	RiverWindowDiscardM3=Old.RiverWindowDiscardM3+(Before-After)*FMath::Square(CellCm*.01);
	UpdateDerived();return Copied;
}

void FGTWaterField::ResetRiverReference()
{
	if (!HasRiverReference()) return;
	DepthM = RiverDepthM; FluxX = RiverFluxX; FluxY = RiverFluxY;
	RiverWaveX.Init(0, NumCells()); RiverWaveY.Init(0, NumCells());
	RiverDetailCarry=0;
	if(bRiverVisuals){RiverDetail.Init(FVector2f::ZeroVector,NumCells());RiverDetailNext=RiverDetail;RiverDetailLid.Init(0,NumCells());}
	else{RiverDetail.Reset();RiverDetailNext.Reset();RiverDetailLid.Reset();}
	ClearLids(); Accumulator = 0; RiverBoundaryM3 = 0;
	UpdateDerived();
}

void FGTWaterField::RiverSubStep(float Dt)
{
	// Linearized shallow-water disturbances about the authored mean. No gravitational acceleration from the
	// mean slope: that pressure/friction balance belongs to the bake. Only eta + solid occupancy accelerates waves.
	// Both height and wave momentum advect with the mean; finite-volume height transfers remain conservative.
	const float C = CellCm * .01f, Area = C*C;
	const float Damping=FMath::Exp(-RiverWaveDamping*Dt);
	// The authored mean never changes within a window. Cache its face velocities and one
	// absorption coefficient per distance-to-edge, rather than dividing/exponentiating per cell.
	if(RiverBlendDt!=Dt || RiverBlendWidth!=RiverAbsorbWidthM)
	{
		RiverEdgeBlend.SetNum(FMath::Min(SizeX,SizeY)/2+1);
		for(int32 E=0;E<RiverEdgeBlend.Num();++E)
		{
			const float Ramp=FMath::Clamp(1.f-E*C/FMath::Max(C,RiverAbsorbWidthM),0.f,1.f);
			RiverEdgeBlend[E]=E==0?1.f:1.f-FMath::Exp(-6.f*Ramp*Ramp*Dt);
		}
		RiverBlendDt=Dt;RiverBlendWidth=RiverAbsorbWidthM;
	}
	auto FaceH = [&](int32 I, int32 J) { return FMath::Min(RiverDepthM[I], RiverDepthM[J]); };
	auto Advect = [&](const TArray<float>& Q, int32 I, float U, float V)
	{
		const int32 X = I % SizeX, Y = I / SizeX;
		const float Left = X>0 ? Q[I-1] : Q[I], Right = X+1<SizeX ? Q[I+1] : Q[I];
		const float Down = Y>0 ? Q[I-SizeX] : Q[I], Up = Y+1<SizeY ? Q[I+SizeX] : Q[I];
		return Q[I] - Dt/C*(FMath::Max(U,0.f)*(Q[I]-Left) + FMath::Min(U,0.f)*(Right-Q[I])
			+ FMath::Max(V,0.f)*(Q[I]-Down) + FMath::Min(V,0.f)*(Up-Q[I]));
	};
	for (int32 I:RiverWetCells)
	{
		const int32 X=I%SizeX, Y=I/SizeX;
		const float Eta = DepthM[I]-RiverDepthM[I]+LidM[I];
		auto Face = [&](int32 J, float RefQ, const TArray<float>& Wave, bool Along, float& Next, float& Total)
		{
			const float H=FaceH(I,J);
			if (H<=0) { Next=0; Total=0; return; }
			const float U=Along?RiverMeanU[I]:RiverMeanV[I];
			// Cross transport is sampled at this cell; it is only momentum advection, never a water source.
			const float Cross = Along?RiverMeanV[I]:RiverMeanU[I];
			const float EtaJ=DepthM[J]-RiverDepthM[J]+LidM[J];
			Next=(Advect(Wave,I,Along?U:Cross,Along?Cross:U)+Dt*9.81f*H*(Eta-EtaJ))
				*Damping;
			const int32 Donor=U>=0 ? I : J;
			Total=RefQ + U*C*(DepthM[Donor]-RiverDepthM[Donor]) + Next;
		};
		if (X+1<SizeX) Face(I+1,RiverFluxX[I],RiverWaveX,true,RiverNextX[I],FluxX[I]);
		else { RiverNextX[I]=0; FluxX[I]=0; }
		if (Y+1<SizeY) Face(I+SizeX,RiverFluxY[I],RiverWaveY,false,RiverNextY[I],FluxY[I]);
		else { RiverNextY[I]=0; FluxY[I]=0; }
	}
	// Two passes: a donor's limiter scales every outgoing face once, independent of traversal order.
	for (int32 I:RiverWetCells)
	{
		const int32 X=I%SizeX,Y=I/SizeX;
		const float Out=FMath::Max(FluxX[I],0.f)+FMath::Max(FluxY[I],0.f)
			+(X>0?FMath::Max(-FluxX[I-1],0.f):0)+(Y>0?FMath::Max(-FluxY[I-SizeX],0.f):0);
		RiverOutScale[I]=Out>0 ? FMath::Min(1.f,DepthM[I]*Area/(Dt*Out)) : 1.f;
	}
	for (int32 I:RiverWetCells)
	{
		const int32 X=I%SizeX,Y=I/SizeX;
		auto Limit = [&](int32 J,float& Q,float& Wave)
		{
			const float K=RiverOutScale[Q>=0?I:J];
			if(K<.99999f) { ++FluxClamps; Wave*=K; Q*=K; }
		};
		if(X+1<SizeX) Limit(I+1,FluxX[I],RiverNextX[I]);
		if(Y+1<SizeY) Limit(I+SizeX,FluxY[I],RiverNextY[I]);
	}
	for (int32 I:RiverWetCells)
	{
		const int32 X=I%SizeX,Y=I/SizeX;
		float Net=(X>0?FluxX[I-1]:0)+(Y>0?FluxY[I-SizeX]:0)-FluxX[I]-FluxY[I];
		// The resampled mean is prescribed, not re-solved on each moving window. Evolve its
		// conservative perturbation only; otherwise interpolation residuals pump the lake/river.
		if(bRiverPrescribedMean) Net-=(X>0?RiverFluxX[I-1]:0)+(Y>0?RiverFluxY[I-SizeX]:0)-RiverFluxX[I]-RiverFluxY[I];
		DepthM[I]=FMath::Max(0.f,DepthM[I]+Dt*Net/Area);
		// Only the outer band exchanges disturbance volume with the unmodelled river. Count it explicitly.
		const float Blend=RiverEdgeBlend[RiverEdgeCells[I]];
		const float Change=(RiverDepthM[I]-DepthM[I])*Blend;
		DepthM[I]+=Change; RiverBoundaryM3+=static_cast<double>(Change)*Area;
		RiverNextX[I]*=1.f-Blend; RiverNextY[I]*=1.f-Blend;
	}
	Swap(RiverWaveX,RiverNextX); Swap(RiverWaveY,RiverNextY);
}
