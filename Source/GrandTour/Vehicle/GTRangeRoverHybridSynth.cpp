#include "Vehicle/GTRangeRoverHybridSynth.h"
#include "Vehicle/GTRangeRoverH2Coefficients.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/MemoryReader.h"
#include <cmath>

TSharedPtr<const FGTHybridBank, ESPMode::ThreadSafe> FGTHybridBank::Load()
{
    TArray<uint8> Bytes;
    if (!FFileHelper::LoadFileToArray(Bytes, *(FPaths::ProjectContentDir()/TEXT("Audio/RangeRoverHybridH2/loops.gth2")))) return nullptr;
    if (Bytes.Num() < 16) return nullptr;
    FMemoryReader Reader(Bytes);
    uint32 Magic, Version, Rate, Count;
    Reader << Magic << Version << Rate << Count;
    if (Magic != 0x32485447 || Version != 1 || Rate != 48000 || Count != 4) return nullptr;
    auto Result = MakeShared<FGTHybridBank, ESPMode::ThreadSafe>();
    constexpr float Roots[4] = {790,960,1890,2180};
    for (int32 I=0; I<4; ++I)
    {
        if (Reader.TotalSize()-Reader.Tell()<8) return nullptr;
        float Root; uint32 Frames;
        Reader << Root << Frames;
        if (Root!=Roots[I] || Frames<2 || Frames>48000*20 || Reader.TotalSize()-Reader.Tell()<int64(Frames)*8) return nullptr;
        auto& Loop=Result->Loops[I]; Loop.RootRpm=Root;
        Loop.Samples.SetNumUninitialized(Frames*2);
        Reader.Serialize(Loop.Samples.GetData(), Frames*8);
        for (float Value : Loop.Samples) if (!FMath::IsFinite(Value) || FMath::Abs(Value)>8.f) return nullptr;
    }
    if (Reader.IsError() || Reader.Tell()!=Reader.TotalSize()) return nullptr;
    return Result;
}

namespace
{
    double Filter(double X, const double* C, double* Z)
    {
        const double Y=C[0]*X+Z[0];
        Z[0]=C[1]*X-C[4]*Y+Z[1]; Z[1]=C[2]*X-C[5]*Y;
        return Y;
    }
    double SafeTarget(float X, double Default, double Min, double Max)
    { return FMath::IsFinite(X) ? FMath::Clamp(double(X),Min,Max) : Default; }
}

FGTRangeRoverHybridSynth::FGTRangeRoverHybridSynth(TSharedPtr<const FGTHybridBank, ESPMode::ThreadSafe> InBank) : Bank(MoveTemp(InBank)) {}

void FGTRangeRoverHybridSynth::Render(int16* Out, int32 Frames)
{
    if (Frames<=0) return;
    if (!Bank) { FMemory::Memzero(Out, Frames*2*sizeof(int16)); return; }
    const double R=SafeTarget(TargetRpm.load(),800,700,5000);
    const double T=SafeTarget(TargetThrottle.load(),0,0,1);
    const double G=SafeTarget(TargetGain.load(),0,0,1);
    const double RpmAlpha=1-std::exp(-1.0/(.015*48000));
    const double Attack=1-std::exp(-1.0/(.045*48000)), Release=1-std::exp(-1.0/(.14*48000));
    const double GateAlpha=1-std::exp(-1.0/(.025*48000));
    const double TopAlpha=1-std::exp(-2*PI*2500/48000), BottomAlpha=1-std::exp(-2*PI*220/48000);
    constexpr double CylinderGains[8]={1.05,.91,1.04,.98,.94,1.06,.92,1};
    for (int32 I=0; I<Frames; ++I)
    {
        Rpm+=RpmAlpha*(R-Rpm); Throttle+=(T>Throttle?Attack:Release)*(T-Throttle); Gain+=GateAlpha*(G-Gain);
        int32 Lower=0;
        while (Lower<3 && Rpm>=Bank->Loops[Lower+1].RootRpm) ++Lower;
        int32 Upper=FMath::Min(Lower+1,3);
        if (Rpm<=Bank->Loops[0].RootRpm) Lower=Upper=0;
        double W0=1,W1=0;
        if (Lower!=Upper)
        {
            double M=FMath::Clamp(std::log(Rpm/Bank->Loops[Lower].RootRpm)/std::log(Bank->Loops[Upper].RootRpm/Bank->Loops[Lower].RootRpm),0.0,1.0);
            M=M*M*(3-2*M); W0=std::cos(M*PI/2); W1=std::sin(M*PI/2);
        }
        double Recorded[2]={};
        for (int32 B=0; B<4; ++B)
        {
            const auto& Loop=Bank->Loops[B]; const int32 Length=Loop.Samples.Num()/2;
            const int32 A=int32(Position[B]), Next=(A+1)%Length;
            const double Fraction=Position[B]-A, Weight=B==Lower?W0:(B==Upper?W1:0);
            for (int32 C=0; C<2; ++C) Recorded[C]+=Weight*(Loop.Samples[A*2+C]*(1-Fraction)+Loop.Samples[Next*2+C]*Fraction);
            Position[B]+=Rpm/Loop.RootRpm;
            while (Position[B]>=Length) Position[B]-=Length;
        }
        // Algebraic form of the exact H2 bipolar combustion pulse: four decaying exponentials.
        // Eight voices cover the maximum simultaneous 16 ms pulses at 5000 RPM.
        const double Step=Rpm/15/48000; Phase+=Step;
        if (Phase>=1)
        {
            Phase-=1; auto& Pulse=Pulses[Event%8];
            const double Age=Phase/Step/48000, AttackTime=.00023-.00014*Throttle, Decay=.00125-.00045*Throttle, Tail=.0032;
            const double Rates[4]={1/Decay,1/Tail,1/Decay+1/AttackTime,1/Tail+1/AttackTime};
            const double A=(.13+.83*std::pow(Throttle,.7))*CylinderGains[Event%8];
            const double Levels[4]={A,-A*Decay/Tail,-A,A*Decay/Tail};
            for (int32 J=0; J<4; ++J) { Pulse.Value[J]=Levels[J]*std::exp(-Age*Rates[J]); Pulse.Multiplier[J]=std::exp(-Rates[J]/48000); }
            Pulse.Remaining=768; Event=(Event+1)%8;
        }
        double Support=0;
        for (auto& Pulse : Pulses) if (Pulse.Remaining>0)
        {
            for (int32 J=0; J<4; ++J) { Support+=Pulse.Value[J]; Pulse.Value[J]*=Pulse.Multiplier[J]; }
            --Pulse.Remaining;
        }
        for (int32 J=0; J<4; ++J) Support=Filter(Support,H2SupportFilter[J],SupportState[J]);
        const double Cutoff=600+5600*std::pow(Throttle,.7), Alpha=1-std::exp(-2*PI*Cutoff/48000);
        const double Level=(.27+.73*std::sqrt(Throttle))*(.70+.30*std::sqrt(Rpm/5000));
        const double PresenceGain=1.7*std::pow(Throttle,.8);
        for (int32 C=0; C<2; ++C)
        {
            Low1[C]+=Alpha*(Recorded[C]-Low1[C]); Low2[C]+=Alpha*(Low1[C]-Low2[C]);
            PresenceTop[C]+=TopAlpha*(Low2[C]-PresenceTop[C]); PresenceBottom[C]+=BottomAlpha*(Low2[C]-PresenceBottom[C]);
            const double Colored=Level*(Low2[C]+PresenceGain*(PresenceTop[C]-PresenceBottom[C]));
            const double X=(Filter(Colored,H2HighPass[0],HighPassState[C])+H2SupportGain*Support)*H2MasterGain*Gain;
            Out[I*2+C]=int16(FMath::Clamp(X,-1.0,1.0)*32767);
        }
    }
    RenderedFrames.fetch_add(Frames,std::memory_order_relaxed);
}
