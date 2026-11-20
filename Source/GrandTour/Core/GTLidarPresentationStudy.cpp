#include "Engine/Engine.h"
#include "Core/GTPlayerController.h"
#include "UI/GTWorkshopComponent.h"
#include "Vehicle/GTCarPawn.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SlateRenderer.h"
#include "RHI.h"
#include "DynamicRHI.h"
#include "RHIResources.h"
#include "UnrealClient.h"

#if PLATFORM_WINDOWS && !UE_BUILD_SHIPPING
#include "Windows/WindowsHWrapper.h"
#include "Windows/AllowWindowsPlatformTypes.h"
THIRD_PARTY_INCLUDES_START
#include <dxgi1_2.h>
THIRD_PARTY_INCLUDES_END
#include "Windows/HideWindowsPlatformTypes.h"

namespace
{
	struct FPresentedFrame
	{
		uint64 EngineFrame;
		int64 QueryTime, SyncTime;
		uint32 Submitted, Presented, PresentRefresh, SyncRefresh;
		int32 Width, Height;
		HRESULT Status;
		bool Foreground;
		bool Driving;
		double Speed;
		double QueryUs;
		FName Section;
	};
	TWeakObjectPtr<UWorld> ActiveWorld;
	TArray<FPresentedFrame> Samples;
	FDelegateHandle EndHandle;
	FString Filename;
	int64 Frequency = 0;
	FName ActiveSection;

	void Finish()
	{
		FCoreDelegates::OnEndFrame.Remove(EndHandle);
		EndHandle.Reset();
		FString Table = TEXT("engine_frame,query_qpc,sync_qpc,qpc_frequency,submitted,presented,present_refresh,sync_refresh,width,height,result,foreground,query_us,section,driving,speed_mps\n");
		Table.Reserve(Samples.Num() * 100);
		for (const auto& S : Samples)
		{
			Table += FString::Printf(TEXT("%llu,%lld,%lld,%lld,%u,%u,%u,%u,%d,%d,%d,%d,%.1f,%s,%d,%.3f\n"),
				S.EngineFrame,S.QueryTime,S.SyncTime,Frequency,S.Submitted,S.Presented,S.PresentRefresh,S.SyncRefresh,
				S.Width,S.Height,S.Status,S.Foreground ? 1 : 0,S.QueryUs,*S.Section.ToString(),S.Driving,S.Speed);
		}
		const bool bSaved = FFileHelper::SaveStringToFile(Table, *Filename, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
		UE_LOG(LogTemp, Display, TEXT("GT_LIDAR_PRESENT saved=%d rows=%d file=%s"), bSaved, Samples.Num(), *Filename);
		Samples.Empty();
		ActiveWorld.Reset();
	}

	void Observe()
	{
		if (!ActiveWorld.IsValid() || Samples.Num() >= 65536)
		{
			Finish();
			return;
		}
		UGameViewportClient* Client = ActiveWorld->GetGameViewport();
		if (!Client || !Client->Viewport || !Client->GetWindow().IsValid() || !FSlateApplication::IsInitialized())
		{
			return;
		}
		auto* View = static_cast<FRHIViewport*>(FSlateApplication::Get().GetRenderer()->GetViewportResource(*Client->GetWindow()));
		auto* Chain = View ? static_cast<IDXGISwapChain*>(View->GetNativeSwapChain()) : nullptr;
		if (!Chain)
		{
			return;
		}
		LARGE_INTEGER Start{}, End{};
		::QueryPerformanceCounter(&Start);
		DXGI_FRAME_STATISTICS Stats{};
		const HRESULT Status = Chain->GetFrameStatistics(&Stats);
		UINT Submitted = 0;
		Chain->GetLastPresentCount(&Submitted);
		DXGI_SWAP_CHAIN_DESC Desc{};
		Chain->GetDesc(&Desc);
		const FIntPoint Size = Client->Viewport->GetSizeXY();
		const HWND Active = ::GetForegroundWindow();
		const bool bForeground = Desc.OutputWindow && Active && ::GetAncestor(Desc.OutputWindow, GA_ROOT) == ::GetAncestor(Active, GA_ROOT);
		const auto* PC = Cast<AGTPlayerController>(ActiveWorld->GetFirstPlayerController());
		const auto* Car = PC ? PC->GetCar() : nullptr;
		const bool bDriving = Car && PC->GetPawn() == Car && !ActiveWorld->IsPaused() &&
			(!PC->GetWorkshop() || !PC->GetWorkshop()->IsOpen());
		const double Speed = Car ? Car->GetVelocity().Size() * .01 : 0;
		::QueryPerformanceCounter(&End);
		Samples.Add({GFrameCounter,Start.QuadPart,Stats.SyncQPCTime.QuadPart,Submitted,Stats.PresentCount,Stats.PresentRefreshCount,
			Stats.SyncRefreshCount,Size.X,Size.Y,Status,bForeground,bDriving,Speed,1.e6 * (End.QuadPart - Start.QuadPart) / Frequency,ActiveSection});
	}

	void PresentationCommand(const TArray<FString>& Args, UWorld* World)
	{
		if (Args.Num() == 2 && Args[0] == TEXT("mark") && EndHandle.IsValid() && ActiveWorld.Get() == World)
		{
			if (Args[1].Len() <= 32 && !Args[1].IsEmpty() && !Args[1].Contains(TEXT(",")) &&
				!Args[1].Contains(TEXT("\n")) && !Args[1].Contains(TEXT("\r"))) ActiveSection = FName(*Args[1]);
			return;
		}
		if (Args.Num() == 1 && Args[0] == TEXT("stop") && EndHandle.IsValid() && ActiveWorld.Get() == World)
		{
			Finish();
			return;
		}
		if (EndHandle.IsValid() || Args.Num() != 2 || Args[0] != TEXT("start") || Args[1].IsEmpty() ||
			Args[1].Len() > 64 || !World || World->WorldType != EWorldType::Game ||
			UGameplayStatics::GetCurrentLevelName(World, true) != TEXT("L_LidarStudy") || RHIGetInterfaceType() != ERHIInterfaceType::D3D12)
		{
			return;
		}
		for (TCHAR C : Args[1])
		{
			if (!FChar::IsAlnum(C) && C != TEXT('_') && C != TEXT('-')) return;
		}
		const FString Dir = FPaths::ProjectSavedDir() / TEXT("LidarPresentation");
		Filename = Dir / (Args[1] + TEXT(".csv"));
		if (IFileManager::Get().FileExists(*Filename) || !IFileManager::Get().MakeDirectory(*Dir, true))
		{
			UE_LOG(LogTemp, Error, TEXT("GT_LIDAR_PRESENT unavailable output %s"), *Filename);
			return;
		}
		LARGE_INTEGER Clock{};
		::QueryPerformanceFrequency(&Clock);
		Frequency = Clock.QuadPart;
		ActiveSection = NAME_None;
		ActiveWorld = World;
		Samples.Reset();
		Samples.Reserve(4096);
		EndHandle = FCoreDelegates::OnEndFrame.AddStatic(&Observe);
	}
	FAutoConsoleCommandWithWorldAndArgs Presentation(
		TEXT("gt.Lidar.Present"), TEXT("Record foreground and DXGI display statistics for a LiDAR driving study. Use start <label>, mark <section> or stop."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(PresentationCommand));
}
#endif
