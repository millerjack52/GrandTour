#include "Core/GTPerfProbe.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogGTPerf,Log,All);

namespace GTPerf
{
    int32 GLogSpikes=0;

    namespace
    {
        FAutoConsoleVariableRef CVarLogSpikes(TEXT("gt.Perf.LogSpikes"),GLogSpikes,
            TEXT("PF1 hitch probes: 1 logs every probed call above 2 ms (duration, work count, frame) and accumulates per-worker calls/mean/max; 2 accumulates without the log lines; 0 (default) is off."),ECVF_Default);

        constexpr double LogThresholdMs=2.0;     // single calls above this are logged and kept as spike events
        constexpr double IntervalThresholdMs=4.0; // the spike-interval analysis counts calls above this
        constexpr int32 MaxSpikes=40000,MaxFrames=200000;

        struct FWorker{int64 Calls=0;int64 WorkTotal=0;double TotalMs=0,MaxMs=0;};
        struct FSpike{FName Name;double T;uint64 Frame;float Ms;int32 Work;};
        struct FFrame{uint64 Frame;float DtMs;float EndIntervalMs;FName Worst;float WorstMs;int32 Probes;};

        TMap<FName,FWorker> Workers;
        TArray<FSpike> Spikes;
        TArray<FFrame> Frames;
        double T0=0,LastFrameEnd=0;
        FName FrameWorst;float FrameWorstMs=0;int32 FrameProbes=0;
        bool bHooked=false;

        void OnEndFrame()
        {
            if(GLogSpikes==0){LastFrameEnd=0;return;}
            const double Now=FPlatformTime::Seconds();
            // The cap wait belongs to the preceding logical frame. End-to-end timing
            // mixes that wait with this frame's work, producing false capped-frame jitter.
            // Retain both: engine delta can be overridden by fixed-step simulation and
            // neither series measures swapchain presentation.
            if(LastFrameEnd>0 && Frames.Num()<MaxFrames)
                Frames.Add({GFrameCounter,float(FApp::GetDeltaTime()*1000.),float((Now-LastFrameEnd)*1000.),FrameWorst,FrameWorstMs,FrameProbes});
            LastFrameEnd=Now;FrameWorst=NAME_None;FrameWorstMs=0;FrameProbes=0;
        }

        void Reset()
        {
            Workers.Reset();Spikes.Reset();Frames.Reset();T0=FPlatformTime::Seconds();LastFrameEnd=0;FrameWorst=NAME_None;FrameWorstMs=0;FrameProbes=0;
        }

        double Percentile(TArray<float> V,double Q)
        {
            if(V.IsEmpty())return 0;
            V.Sort();const double F=(V.Num()-1)*Q;const int32 I=int32(F);
            return V[I]+(V[FMath::Min(I+1,V.Num()-1)]-V[I])*(F-I);
        }

        FString Json(const FString& S){return S.ReplaceCharWithEscapedChar();}

        void Dump(const TArray<FString>& Args)
        {
            const FString Label=Args.Num()?Args[0]:TEXT("run");
            const double Elapsed=FPlatformTime::Seconds()-T0;
            TArray<float> Dt;for(const FFrame& F:Frames)Dt.Add(F.DtMs);
            double Sum=0;for(float V:Dt)Sum+=V;
            const double Mean=Dt.Num()?Sum/Dt.Num():0,P50=Percentile(Dt,.5),P95=Percentile(Dt,.95),P99=Percentile(Dt,.99);
            float Max=0;for(float V:Dt)Max=FMath::Max(Max,V);
            FString Out=FString::Printf(TEXT("{\n \"schema_version\":2,\n \"frame_time_method\":\"engine_logical_delta_not_presentation\",\n \"timing_note\":\"Logical delta may be overridden by fixed-step simulation; prior-frame work appears in the next logical interval. End intervals retain wall time but mix variable work and cap waits.\",\n \"label\":\"%s\",\n \"elapsed_s\":%.2f,\n \"frames\":%d,\n \"frame_ms\":{\"mean\":%.3f,\"p50\":%.3f,\"p95\":%.3f,\"p99\":%.3f,\"max\":%.3f},\n"),
                *Json(Label),Elapsed,Dt.Num(),Mean,P50,P95,P99,Max);
            TArray<float> EndDt;double EndSum=0;float EndMax=0;
            for(const FFrame& F:Frames){EndDt.Add(F.EndIntervalMs);EndSum+=F.EndIntervalMs;EndMax=FMath::Max(EndMax,F.EndIntervalMs);}
            Out+=FString::Printf(TEXT(" \"end_frame_interval_ms\":{\"mean\":%.3f,\"p95\":%.3f,\"p99\":%.3f,\"max\":%.3f},\n \"log_threshold_ms\":%.1f,\n \"interval_threshold_ms\":%.1f,\n \"workers\":{\n"),
                EndDt.Num()?EndSum/EndDt.Num():0,Percentile(EndDt,.95),Percentile(EndDt,.99),EndMax,LogThresholdMs,IntervalThresholdMs);
            TArray<FName> Names;Workers.GetKeys(Names);Names.Sort([](const FName& A,const FName& B){return A.LexicalLess(B);});
            UE_LOG(LogGTPerf,Display,TEXT("GTPERF_DUMP label=%s elapsed_s=%.1f frames=%d logical_frame_ms mean=%.2f p50=%.2f p95=%.2f p99=%.2f max=%.2f"),*Label,Elapsed,Dt.Num(),Mean,P50,P95,P99,Max);
            UE_LOG(LogGTPerf,Display,TEXT("GTPERF_TABLE worker calls mean_ms max_ms over2ms over4ms interval_s(mean/min/max) work_total"));
            for(int32 N=0;N<Names.Num();++N)
            {
                const FName Name=Names[N];const FWorker& W=Workers[Name];
                TArray<double> Times;int32 Over2=0;
                for(const FSpike& S:Spikes)if(S.Name==Name){++Over2;if(S.Ms>IntervalThresholdMs)Times.Add(S.T);}
                const int32 Over4=Times.Num();
                double IMean=0,IMin=0,IMax=0;
                if(Times.Num()>1)
                {
                    IMin=DBL_MAX;for(int32 I=1;I<Times.Num();++I){const double D=Times[I]-Times[I-1];IMean+=D;IMin=FMath::Min(IMin,D);IMax=FMath::Max(IMax,D);}
                    IMean/=Times.Num()-1;
                }
                FString TimesJson;for(int32 I=0;I<Times.Num();++I)TimesJson+=FString::Printf(TEXT("%s%.3f"),I?TEXT(","):TEXT(""),Times[I]);
                Out+=FString::Printf(TEXT("  \"%s\":{\"calls\":%lld,\"mean_ms\":%.4f,\"max_ms\":%.3f,\"total_ms\":%.2f,\"work_total\":%lld,\"over_2ms\":%d,\"over_4ms\":%d,\"interval_s\":{\"mean\":%.3f,\"min\":%.3f,\"max\":%.3f},\"over_4ms_times_s\":[%s]}%s\n"),
                    *Json(Name.ToString()),W.Calls,W.Calls?W.TotalMs/W.Calls:0.,W.MaxMs,W.TotalMs,W.WorkTotal,Over2,Over4,IMean,IMin,IMax,*TimesJson,N+1<Names.Num()?TEXT(","):TEXT(""));
                UE_LOG(LogGTPerf,Display,TEXT("GTPERF_ROW %s calls=%lld mean_ms=%.4f max_ms=%.3f over2=%d over4=%d interval_s=%.2f/%.2f/%.2f work=%lld"),*Name.ToString(),W.Calls,W.Calls?W.TotalMs/W.Calls:0.,W.MaxMs,Over2,Over4,IMean,IMin,IMax,W.WorkTotal);
            }
            Out+=TEXT(" },\n \"spikes\":[\n");
            // Every call above the log threshold, with the frame times of the frames around it (frame index into the series by game frame number).
            TMap<uint64,int32> FrameIndex;for(int32 I=0;I<Frames.Num();++I)FrameIndex.Add(Frames[I].Frame,I);
            for(int32 N=0;N<Spikes.Num();++N)
            {
                const FSpike& S=Spikes[N];FString Around;
                if(const int32* Ix=FrameIndex.Find(S.Frame))
                    for(int32 K=-2;K<=3;++K)if(Frames.IsValidIndex(*Ix+K))Around+=FString::Printf(TEXT("%s%.1f"),Around.IsEmpty()?TEXT(""):TEXT(","),Frames[*Ix+K].DtMs);
                Out+=FString::Printf(TEXT("  {\"worker\":\"%s\",\"t_s\":%.3f,\"frame\":%llu,\"ms\":%.3f,\"work\":%d,\"frame_ms_minus2_to_plus3\":[%s]}%s\n"),*Json(S.Name.ToString()),S.T,S.Frame,S.Ms,S.Work,*Around,N+1<Spikes.Num()?TEXT(","):TEXT(""));
            }
            Out+=TEXT(" ],\n \"slowest_frames\":[\n");
            TArray<int32> Order;for(int32 I=0;I<Frames.Num();++I)Order.Add(I);
            Order.Sort([](int32 A,int32 B){return Frames[A].DtMs>Frames[B].DtMs;});
            const int32 Top=FMath::Min(40,Order.Num());
            for(int32 N=0;N<Top;++N)
            {
                const FFrame& F=Frames[Order[N]];
                Out+=FString::Printf(TEXT("  {\"frame\":%llu,\"dt_ms\":%.2f,\"end_interval_ms\":%.2f,\"worst_probe\":\"%s\",\"worst_probe_ms\":%.3f,\"probes\":%d}%s\n"),F.Frame,F.DtMs,F.EndIntervalMs,*Json(F.Worst.ToString()),F.WorstMs,F.Probes,N+1<Top?TEXT(","):TEXT(""));
            }
            Out+=TEXT(" ]\n}\n");
            const FString Path=FPaths::ProjectSavedDir()/TEXT("Profiling")/FString::Printf(TEXT("gt_perf_%s.json"),*Label);
            IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
            FFileHelper::SaveStringToFile(Out,*Path);
            UE_LOG(LogGTPerf,Display,TEXT("GTPERF_FILE %s"),*Path);
        }

        FAutoConsoleCommand CmdReset(TEXT("gt.Perf.Reset"),TEXT("PF1: clear the hitch probe counters and frame series."),FConsoleCommandDelegate::CreateStatic(&Reset));
        FAutoConsoleCommand CmdDump(TEXT("gt.Perf.Dump"),TEXT("PF1: gt.Perf.Dump <label> logs the per-worker table and writes Saved/Profiling/gt_perf_<label>.json."),FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args){Dump(Args);}));
    }

    void HookFrames()
    {
        if(bHooked)return;
        bHooked=true;T0=FPlatformTime::Seconds();
        FCoreDelegates::OnEndFrame.AddStatic(&OnEndFrame);
    }

    void Record(const TCHAR* NameText,double Ms,int32 Work)
    {
        const FName Name(NameText);
        FWorker& W=Workers.FindOrAdd(Name);
        ++W.Calls;W.TotalMs+=Ms;W.MaxMs=FMath::Max(W.MaxMs,Ms);W.WorkTotal+=Work;
        ++FrameProbes;
        if(Ms>FrameWorstMs){FrameWorstMs=float(Ms);FrameWorst=Name;}
        if(Ms>LogThresholdMs)
        {
            if(Spikes.Num()<MaxSpikes)Spikes.Add({Name,FPlatformTime::Seconds()-T0,GFrameCounter,float(Ms),Work});
            if(GLogSpikes==1)UE_LOG(LogGTPerf,Warning,TEXT("GTPERF_SPIKE %s %.2f ms work=%d frame=%llu"),NameText,Ms,Work,GFrameCounter);
        }
    }
}
