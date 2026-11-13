#pragma once
#include "CoreMinimal.h"
#include <atomic>

struct FGTWheelTraction;
enum class EGTGroundSound : uint8 { Tarmac, Gravel, Dirt, Grass, Mud, Sand, Snow, Water, Count };
constexpr int32 GTGroundSoundCount = int32(EGTGroundSound::Count);

/** Cosmetic wheel-contact mix. No physics values are written by ground audio. */
struct FGTGroundAudioMix
{
    float Roll[GTGroundSoundCount][2] = {};
    float Scrub[GTGroundSoundCount][2] = {};
    float Speed = 0;
    float BodySpeed = 0;
    float Bump = 0;
    int32 Contacts = 0;
    static EGTGroundSound Classify(const FGTWheelTraction& Wheel, bool bPhysicalGravel);
    static const TCHAR* Name(EGTGroundSound Kind);
    void AddWheel(const FGTWheelTraction& Wheel, bool bPhysicalGravel, float Side, float GroundSpeedCmS,
                  float LateralSlipCmS, int32 WheelCount);
    float Activity() const;
    EGTGroundSound Dominant() const;
};

struct FGTGroundRecordingBank
{
    TArray<float> Clips[13];
    static TSharedPtr<const FGTGroundRecordingBank, ESPMode::ThreadSafe> Load();
};

/** Recorded rolling, body rumble and event voices. Independent of engine RPM. */
class FGTGroundAudioSynth
{
public:
    FGTGroundAudioSynth();
    void SetTargets(const FGTGroundAudioMix& Mix, float Volume);
    /** Add stereo PCM to an existing engine buffer; zero targets leave that buffer unchanged after fade. */
    void MixInto(int16* Out, int32 Frames);
    bool IsReady() const { return Bank.IsValid(); }
    std::atomic<uint64> RenderedFrames{0}, BumpEvents{0}, SkidEvents{0};
private:
    TSharedPtr<const FGTGroundRecordingBank, ESPMode::ThreadSafe> Bank;
    std::atomic<float> TargetRoll[GTGroundSoundCount][2], TargetScrub[GTGroundSoundCount][2];
    std::atomic<float> TargetSpeed{0}, TargetBodySpeed{0}, TargetVolume{0}, PendingBump{0};
    float RollState[GTGroundSoundCount][2]={}, ScrubState[GTGroundSoundCount][2]={};
    double Positions[4]={0,144000,0,0};
    int32 SkidFrame=-1, BumpFrame=-1, BumpClip=5, BumpCooldown=0;
    float BumpGain=0, SkidGain=0;
    bool bSkidArmed=true;
    float Volume=0, Speed=0, BodySpeed=0;
    float RollingTone[2]={};
};
