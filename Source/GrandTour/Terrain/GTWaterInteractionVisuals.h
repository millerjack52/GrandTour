#pragma once
#include "CoreMinimal.h"

/** Cosmetic response only. Never feed these values into water mass, buoyancy or traction. */
namespace GTWaterInteractionVisuals
{
constexpr float VehicleWaveStartDepthM=.025f;
inline FVector2D FilterWakeVelocity(FVector2D Previous,FVector2D Measured,float Dt)
{
	// Filter vectors, not chassis yaw: this also crosses zero correctly in reverse.
	return FMath::Lerp(Previous,Measured,1-FMath::Exp(-FMath::Max(0.f,Dt)/.14f));
}
inline float WakeImmersionM(float HullImmersionM,float MeanWetTyreDepthM,float WetTyreFraction)
{
	// Tyres displace water before the keel reaches it. Partial entry has a smaller
	// pressure footprint; this is only an input to the visual reconstruction.
	const float Tyres=FMath::Min(.20f,FMath::Max(0.f,MeanWetTyreDepthM)*.65f)
		*FMath::Sqrt(FMath::Clamp(WetTyreFraction,0.f,1.f));
	return FMath::Max(FMath::Max(0.f,HullImmersionM),Tyres);
}
inline float Activity(float SpeedMps, float DepthM, float StartSpeed, float FullSpeed, float StartDepth, float FullDepth)
{
	const float Speed = FMath::Clamp((SpeedMps-StartSpeed)/FMath::Max(.01f,FullSpeed-StartSpeed),0.f,1.f);
	const float Depth = FMath::Clamp((DepthM-StartDepth)/FMath::Max(.01f,FullDepth-StartDepth),0.f,1.f);
	return FMath::Sqrt(Speed*Depth);
}

inline float ExtraHeightCm(float EtaCm, float ReferenceDepthM, float Gain)
{
	// Extra relief for the physical bow/wake, bounded in shallows and at large disturbances.
	const float Bound=FMath::Min(18.f,FMath::Max(0.f,ReferenceDepthM)*35.f);
	return FMath::Clamp(EtaCm*FMath::Clamp(Gain,0.f,3.f),-Bound,Bound);
}
inline uint8 PackHeight(float Cm) { return uint8(FMath::Clamp(FMath::RoundToInt(128.f+Cm*4.f),0,255)); }
inline float UnpackHeight(uint8 B) { return (float(B)-128.f)*.25f; }

/** Fresh aeration is concentrated on the pressure front and hull shoulders.
 * This is separate from transported foam: old wakes must not whiten the whole
 * disturbed footprint. Coordinates follow relative travel, including reverse. */
inline float VehicleContactFoam(float X,float Y,float HalfLength,float HalfWidth,float Speed,float Immersion)
{
	const float A=Activity(Speed,Immersion,.35f,3.5f,VehicleWaveStartDepthM,.18f);
	if(A<=0 || X>HalfLength+300 || X<-HalfLength-500 || FMath::Abs(Y)>HalfWidth+500)return 0;
	const float Side=FMath::Abs(Y);
	auto Band=[](float D,float Width){return FMath::Exp(-.5f*FMath::Square(D/Width));};
	const float BowX=HalfLength+55-Side*Side/(2*(HalfWidth+100));
	const float Bow=Band(X-BowX,55)*(1-FMath::SmoothStep(HalfWidth+30,HalfWidth+160,Side));
	const float Along=FMath::SmoothStep(-HalfLength-100,-HalfLength+30,X)
		*(1-FMath::SmoothStep(HalfLength-50,HalfLength+50,X));
	const float Shoulder=Band(Side-HalfWidth-25,48)*Along;
	const float Behind=-HalfLength-X;
	const float ShortWake=FMath::SmoothStep(-20.f,70.f,Behind)*(1-FMath::SmoothStep(160.f,430.f,Behind));
	const float Arms=Band(Side-HalfWidth-25-FMath::Max(0.f,Behind)*.35f,60)*ShortWake;
	const float Stern=Band(Behind-55,65)*(1-FMath::SmoothStep(HalfWidth*.5f,HalfWidth+45,Side));
	return A*FMath::Clamp(FMath::Max(Bow,FMath::Max(Shoulder*.9f,FMath::Max(Arms*.75f,Stern*.55f))),0.f,1.f);
}

/** A released wave packet: radius advances while amplitude and envelope decay.
 * Centimetres throughout; sampled into the existing cosmetic field only. */
inline float TrailWaveCm(float RadiusCm,float Age,float Energy)
{
	if(Age<=0 || Age>=3.2f || RadiusCm>600)return 0;
	const float Front=45+Age*115,Width=65+Age*24;
	const float D=RadiusCm-Front;
	return FMath::Clamp(Energy,0.f,1.f)*7.f*FMath::SmoothStep(0.f,.12f,Age)
		*(1-FMath::SmoothStep(.4f,3.2f,Age))*FMath::Exp(-.5f*FMath::Square(D/Width))
		*FMath::Cos(D*(2*PI/180.f));
}

/** Low-frequency render reconstruction outside the hull. X follows relative travel;
 * the curved pressure ridge feeds two widening wake arms, not circular stamps. */
inline float VehicleWaveCm(float X,float Y,float HalfLength,float HalfWidth,float Speed,float Immersion)
{
	const float A=Activity(Speed,Immersion,.25f,3.5f,VehicleWaveStartDepthM,.18f);
	if(A<=0 || X>HalfLength+400 || X<HalfLength-1500 || FMath::Abs(Y)>1100)return 0;
	const float Side=FMath::Abs(Y);
	auto Ridge=[](float Distance,float Width){const float T=Distance/Width;return FMath::Exp(-.5f*T*T)*(1.f-.35f*T*T);};
	const float BowX=HalfLength+55-Side*Side/(2*(HalfWidth+100));
	const float Bow=Ridge(X-BowX,70)*(1-FMath::SmoothStep(HalfWidth+20,HalfWidth+210,Side));
	const float Behind=HalfLength-X;
	const float Spread=FMath::Lerp(.65f,.38f,FMath::Clamp(Speed/6.f,0.f,1.f));
	const float ArmY=HalfWidth+40+FMath::Max(0.f,Behind)*Spread;
	// Only the pressure region stays attached. Released trail packets retain
	// their world-space direction, rather than swinging the old wake on a turn.
	const float Tail=FMath::SmoothStep(0.f,160.f,Behind)*(1-FMath::SmoothStep(2*HalfLength+160,2*HalfLength+500,Behind))*FMath::Exp(-FMath::Max(0.f,Behind)/1100);
	const float Wake=Tail*(.85f*Ridge(Side-ArmY,60+FMath::Max(0.f,Behind)*.05f)
		+.32f*Ridge(Side-ArmY-170,75)+.14f*Ridge(Side-ArmY-330,85));
	const float Stern=Ridge(X+HalfLength+70,85)*.28f
		*(1-FMath::SmoothStep(HalfWidth*.65f,HalfWidth+110,Side));
	return A*FMath::Min(30.f,Immersion*120)*(Bow+Wake+Stern);
}
}
