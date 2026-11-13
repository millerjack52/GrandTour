#pragma once
#include "CoreMinimal.h"
#include "Stats/Stats.h"

/**
 * PF1: game-thread hitch instrumentation (docs/LIDAR_PLACE_PLAN.md PF1).
 *
 * Every periodic worker that could stall a frame wraps its body in GT_PERF_SCOPE. Each scope is a cycle stat in STATGROUP_GTPerf (stat GTPerf, Insights with -trace=cpu) and, while gt.Perf.LogSpikes is
 * non-zero, a wall-clock probe: gt.Perf.LogSpikes 1 logs every single call above 2 ms (LogGTPerf, with its duration, the work count and the frame number) and keeps per-worker call counts, mean, max and
 * every call above 2 ms; 2 keeps the same numbers without the log lines; 0 (default) costs one integer test per scope. A frame hook records the game-thread time of every frame while a probe is on.
 *   gt.Perf.Reset           clears the counters and the frame series.
 *   gt.Perf.Dump <label>    logs a per-worker table and writes Saved/Profiling/gt_perf_<label>.json (workers, the spikes with the frame times around them, the slowest frames).
 */
DECLARE_STATS_GROUP(TEXT("GrandTour Perf"), STATGROUP_GTPerf, STATCAT_Advanced);

namespace GTPerf
{
    GRANDTOUR_API extern int32 GLogSpikes;
    GRANDTOUR_API void Record(const TCHAR* Name, double Ms, int32 Work);
    GRANDTOUR_API void HookFrames();

    /** Times its scope when gt.Perf.LogSpikes is on (game thread only). Work is whatever the worker counts: cells sampled, instances changed, blocks uploaded. */
    struct FScope
    {
        const TCHAR* Name;
        double Start=0;
        int32 Work=0;
        bool bOn;
        explicit FScope(const TCHAR* InName):Name(InName),bOn(GLogSpikes!=0 && IsInGameThread())
        {
            if(bOn){HookFrames();Start=FPlatformTime::Seconds();}
        }
        ~FScope(){if(bOn)Record(Name,(FPlatformTime::Seconds()-Start)*1000.,Work);}
    };
}

#define GT_PERF_SCOPE(Var,Label) \
    DECLARE_SCOPE_CYCLE_COUNTER(TEXT(Label),STAT_GTPerf_##Var,STATGROUP_GTPerf); \
    GTPerf::FScope Var(TEXT(Label))
