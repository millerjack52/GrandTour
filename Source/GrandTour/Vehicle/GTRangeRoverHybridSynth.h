#pragma once
#include "CoreMinimal.h"
#include <atomic>

/** Immutable, calibrated H2 recording bank. Loaded on the game thread before playback. */
struct FGTHybridBank
{
    struct FLoop { double RootRpm = 0; TArray<float> Samples; };
    FLoop Loops[4];
    static TSharedPtr<const FGTHybridBank, ESPMode::ThreadSafe> Load();
};

/** Audio-thread-owned state. Only Targets and diagnostics cross threads; no allocations in Render. */
class FGTRangeRoverHybridSynth
{
public:
    explicit FGTRangeRoverHybridSynth(TSharedPtr<const FGTHybridBank, ESPMode::ThreadSafe> InBank);
    std::atomic<float> TargetRpm{800}, TargetThrottle{0}, TargetGain{0};
    std::atomic<uint64> RenderedFrames{0};
    void Render(int16* Out, int32 Frames);
    double GetSmoothedRpmForTest() const { return Rpm; }
private:
    TSharedPtr<const FGTHybridBank, ESPMode::ThreadSafe> Bank;
    double Position[4] = {}, Rpm = 800, Throttle = 0, Gain = 0, Phase = 0;
    double Low1[2] = {}, Low2[2] = {}, PresenceTop[2] = {}, PresenceBottom[2] = {};
    double HighPassState[2][2] = {}, SupportState[4][2] = {};
    struct FPulse { double Value[4] = {}, Multiplier[4] = {}; int32 Remaining = 0; };
    FPulse Pulses[8];
    int32 Event = 0;
};
